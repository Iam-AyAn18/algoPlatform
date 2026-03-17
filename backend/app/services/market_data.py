"""Market data service – multi-source with graceful fallback.

Fetch chain for live quotes:
  1. Fresh in-memory cache  (TTL = QUOTE_CACHE_TTL_SECONDS, default 5 min)
  2. Broker API (direct – Zerodha Kite Connect, no intermediary server)
  3. NSE India API via nsepython  (primary free source, NSE stocks only)
  4. Stale cache            (return last-known price if all fetches fail)

Historical OHLCV data:
  1. Broker API direct (Zerodha Kite, when configured)
  2. NSE India public historical API (direct HTTP, no Yahoo Finance)
"""
from __future__ import annotations

import datetime
import logging
import threading
from typing import Dict, List, Optional, Tuple

from app.models.schemas import OHLCBar, QuoteResponse

logger = logging.getLogger(__name__)

# ── Cache configuration ───────────────────────────────────────────────────────

QUOTE_CACHE_TTL_SECONDS: int = 300          # 5 minutes
QUOTE_STALE_LIMIT_SECONDS: int = 3600      # 1 hour

# ── Two-tier cache ────────────────────────────────────────────────────────────

class _CacheEntry:
    __slots__ = ("quote", "cached_at")

    def __init__(self, quote: QuoteResponse, cached_at: datetime.datetime):
        self.quote = quote
        self.cached_at = cached_at


_quote_cache: Dict[str, _CacheEntry] = {}
_cache_lock = threading.Lock()

_inflight: Dict[str, threading.Event] = {}
_inflight_lock = threading.Lock()

# ── Broker settings module-level cache (avoids DB round-trip per quote) ───────

# Tuple of (broker_name, api_key, access_token) – refreshed by set_broker_credentials()
_broker_credentials: Optional[Tuple[str, str, str]] = None
_broker_creds_lock = threading.Lock()


def set_broker_credentials(broker_name: str, api_key: str, access_token: str) -> None:
    """Called by the broker API after saving settings so market_data picks them up."""
    global _broker_credentials
    with _broker_creds_lock:
        _broker_credentials = (broker_name, api_key, access_token)


def _get_broker_settings_cached() -> Optional[Tuple[str, str, str]]:
    with _broker_creds_lock:
        return _broker_credentials


def _cache_key(symbol: str, exchange: str) -> str:
    return f"{symbol.upper()}:{exchange.upper()}"


def _get_cache_entry(symbol: str, exchange: str) -> Optional[_CacheEntry]:
    key = _cache_key(symbol, exchange)
    with _cache_lock:
        return _quote_cache.get(key)


def _is_fresh(entry: _CacheEntry) -> bool:
    age = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - entry.cached_at).total_seconds()
    return age <= QUOTE_CACHE_TTL_SECONDS


def _is_usable_stale(entry: _CacheEntry) -> bool:
    age = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - entry.cached_at).total_seconds()
    return age <= QUOTE_STALE_LIMIT_SECONDS


def _set_cache(symbol: str, exchange: str, quote: QuoteResponse) -> None:
    key = _cache_key(symbol, exchange)
    with _cache_lock:
        _quote_cache[key] = _CacheEntry(
            quote=quote,
            cached_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        )


def clear_quote_cache() -> None:
    """Flush the entire quote cache (useful in tests)."""
    with _cache_lock:
        _quote_cache.clear()


# ── NSE India API (primary for NSE stocks) ────────────────────────────────────

def _fetch_from_nse(symbol: str) -> Optional[QuoteResponse]:
    """Fetch a live NSE equity quote via nsepython (wraps NSE India's public API)."""
    try:
        from nsepython import nse_eq  # lazy import – optional dependency

        data = nse_eq(symbol.upper())
        if not isinstance(data, dict):
            return None

        price_info = data.get("priceInfo", {})
        info = data.get("info", {})

        last_price = float(price_info.get("lastPrice") or price_info.get("close") or 0)
        prev_close = float(price_info.get("previousClose") or 0)
        open_ = float(price_info.get("open") or prev_close)

        intra = price_info.get("intraDayHighLow") or {}
        high = float(intra.get("max") or price_info.get("dayHigh") or last_price)
        low = float(intra.get("min") or price_info.get("dayLow") or last_price)

        week_hl = price_info.get("weekHighLow") or {}
        week_52_high = float(week_hl.get("max") or 0) or None
        week_52_low = float(week_hl.get("min") or 0) or None

        change = float(price_info.get("change") or last_price - prev_close)
        change_pct = float(price_info.get("pChange") or 0)

        volume = int(
            (data.get("marketDeptOrderBook") or {}).get("totalTradedVolume")
            or (data.get("metadata") or {}).get("totalTradedVolume")
            or 0
        )

        return QuoteResponse(
            symbol=symbol.upper(),
            exchange="NSE",
            name=info.get("companyName", symbol),
            price=round(last_price, 2),
            open=round(open_, 2),
            high=round(high, 2),
            low=round(low, 2),
            prev_close=round(prev_close, 2),
            change=round(change, 2),
            change_pct=round(change_pct, 2),
            volume=volume,
            market_cap=None,
            pe_ratio=None,
            week_52_high=week_52_high,
            week_52_low=week_52_low,
        )
    except ImportError:
        logger.debug("nsepython not installed, skipping NSE primary source")
        return None
    except Exception as exc:
        logger.warning("NSE API fetch failed for %s: %s", symbol, exc)
        return None


# ── Broker quote (optional, direct API) ──────────────────────────────────────

def _fetch_from_broker(symbol: str, exchange: str) -> Optional[QuoteResponse]:
    """Fetch directly from the configured broker API (no intermediary server)."""
    try:
        from sqlalchemy import select
        from app.models.db_models import BrokerSettings
        # Use sync fallback: read cached broker settings from module-level cache
        _bs = _get_broker_settings_cached()
        if _bs is None:
            return None
        broker_name, api_key, access_token = _bs
        if not api_key or not access_token:
            return None
        from app.services.broker_service import get_quote_via_broker
        return get_quote_via_broker(symbol, exchange, broker_name, api_key, access_token)
    except Exception as exc:
        logger.debug("Broker quote fetch skipped: %s", exc)
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def get_quote(symbol: str, exchange: str = "NSE") -> QuoteResponse:
    """Return the best available quote, with multi-level fallback.

    Priority:
      1. Fresh cache hit → return immediately
      2. Broker API (direct Zerodha Kite Connect, if configured)
      3. NSE India API
      4. Stale cache entry (up to 1 h old)
      5. Raise RuntimeError so the API layer can return 502
    """
    symbol = symbol.upper().strip()
    exchange = exchange.upper().strip()
    key = _cache_key(symbol, exchange)

    # 1. Fresh cache
    entry = _get_cache_entry(symbol, exchange)
    if entry and _is_fresh(entry):
        return entry.quote

    # In-flight deduplication
    waiter_event: Optional[threading.Event] = None
    with _inflight_lock:
        if key in _inflight:
            waiter_event = _inflight[key]
        else:
            fetch_event = threading.Event()
            _inflight[key] = fetch_event

    if waiter_event is not None:
        waiter_event.wait(timeout=15)
        entry = _get_cache_entry(symbol, exchange)
        if entry and _is_fresh(entry):
            return entry.quote
        if entry and _is_usable_stale(entry):
            return entry.quote

    try:
        quote: Optional[QuoteResponse] = None

        # 2. OpenAlgo broker API (if configured)
        quote = _fetch_from_broker(symbol, exchange)

        # 3. NSE India API (NSE only)
        if quote is None and exchange == "NSE":
            quote = _fetch_from_nse(symbol)

        if quote is not None:
            _set_cache(symbol, exchange, quote)
            return quote

        # 4. Stale cache fallback
        entry = _get_cache_entry(symbol, exchange)
        if entry and _is_usable_stale(entry):
            logger.warning("Returning stale cache for %s:%s", symbol, exchange)
            return entry.quote

        raise RuntimeError(
            f"All data sources failed for {symbol}:{exchange}. "
            "Connect a Zerodha broker account or check your network connection."
        )
    finally:
        if waiter_event is None:
            with _inflight_lock:
                _inflight.pop(key, None)
            fetch_event.set()


def get_historical(
    symbol: str,
    exchange: str = "NSE",
    period: str = "1y",
    interval: str = "1d",
) -> List[OHLCBar]:
    """Fetch OHLCV bars using the broker API or NSE India public API.

    Priority:
      1. Broker API direct (Zerodha Kite, when configured)
      2. NSE India public historical API
    """
    # 1. Direct broker historical data (Zerodha Kite)
    broker_creds = _get_broker_settings_cached()
    if broker_creds:
        broker_name, api_key, access_token = broker_creds
        if api_key and access_token:
            try:
                from app.services.broker_service import get_historical_via_broker
                from app.services.nse_history import period_to_dates
                start, end = period_to_dates(period)
                bars = get_historical_via_broker(
                    symbol=symbol,
                    exchange=exchange,
                    start_date=start.strftime("%Y-%m-%d"),
                    end_date=end.strftime("%Y-%m-%d"),
                    interval=interval,
                    broker_name=broker_name,
                    api_key=api_key,
                    access_token=access_token,
                )
                if bars:
                    return bars
            except Exception as exc:
                logger.debug("Broker historical skipped: %s", exc)

    # 2. NSE India public historical API (NSE stocks only)
    try:
        from app.services.nse_history import fetch_nse_historical, period_to_dates
        start, end = period_to_dates(period)
        bars = fetch_nse_historical(symbol=symbol, start=start, end=end)
        if bars:
            return bars
    except Exception as exc:
        logger.warning("NSE historical fetch failed for %s: %s", symbol, exc)

    return []


# Popular NSE large-cap indices members for a default market overview
NIFTY50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "BAJFINANCE", "ASIANPAINT", "AXISBANK", "MARUTI",
    "SUNPHARMA", "TITAN", "WIPRO", "ULTRACEMCO", "NESTLEIND",
]

