"""Market data service – multi-source with graceful fallback.

Fetch chain:
  1. Fresh in-memory cache  (TTL = QUOTE_CACHE_TTL_SECONDS, default 5 min)
  2. NSE India API via nsepython  (primary, NSE stocks only, no rate limits)
  3. Yahoo Finance via yfinance    (fallback for BSE + when NSE API is down)
  4. Stale cache                   (return last-known price if all fetches fail)

Yahoo Finance issues (429 / empty data) are mitigated by:
  - Removing the expensive tk.info / quoteSummary call that triggers 429
  - Exponential backoff retries
  - In-flight deduplication so only one goroutine fetches per symbol
"""
from __future__ import annotations

import datetime
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple

import yfinance as yf

from app.models.schemas import OHLCBar, QuoteResponse

logger = logging.getLogger(__name__)

# ── Cache configuration ───────────────────────────────────────────────────────

# Time after which the cache entry is considered stale and a fresh fetch is
# triggered.  5 minutes is a sensible default for a paper-trading app.
QUOTE_CACHE_TTL_SECONDS: int = 300          # 5 minutes

# How long to keep a stale entry as an emergency fallback when all live
# sources return errors (e.g. both NSE API and Yahoo Finance are down).
QUOTE_STALE_LIMIT_SECONDS: int = 3600      # 1 hour

# ── Two-tier cache ────────────────────────────────────────────────────────────

class _CacheEntry:
    __slots__ = ("quote", "cached_at")

    def __init__(self, quote: QuoteResponse, cached_at: datetime.datetime):
        self.quote = quote
        self.cached_at = cached_at


_quote_cache: Dict[str, _CacheEntry] = {}
_cache_lock = threading.Lock()

# Per-symbol in-flight lock: prevents thundering herd where many concurrent
# requests for the same symbol each fire a separate network call.
_inflight: Dict[str, threading.Event] = {}
_inflight_lock = threading.Lock()


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
    """Fetch a live NSE equity quote via nsepython (wraps NSE India's public API).

    Returns None on any error so the caller can fall through to yfinance.
    """
    try:
        from nsepython import nse_eq  # lazy import – optional dependency

        data = nse_eq(symbol.upper())
        if not isinstance(data, dict):
            return None

        price_info = data.get("priceInfo", {})
        info = data.get("info", {})
        metadata = data.get("securityInfo", {})

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


# ── Yahoo Finance (fallback) ──────────────────────────────────────────────────

_YF_RETRY_DELAYS = (1.0, 3.0, 7.0)   # seconds between retries


def _yf_symbol(symbol: str, exchange: str) -> str:
    symbol = symbol.upper().strip()
    if exchange.upper() == "BSE":
        return f"{symbol}.BO"
    return f"{symbol}.NS"


def _fetch_from_yfinance(symbol: str, exchange: str) -> Optional[QuoteResponse]:
    """Fetch via yfinance with exponential-backoff retry.

    Critically, we only use ``fast_info`` (lightweight endpoint) and skip the
    expensive ``tk.info`` / quoteSummary call that is the primary trigger of
    Yahoo Finance 429 errors.  Company name and fundamental ratios are omitted
    when this fallback is used.
    """
    ticker_sym = _yf_symbol(symbol, exchange)

    last_exc: Optional[Exception] = None
    for attempt, delay in enumerate((*_YF_RETRY_DELAYS, None)):
        try:
            tk = yf.Ticker(ticker_sym)
            fast = tk.fast_info

            prev_close = float(fast.previous_close or 0)
            price = float(fast.last_price or prev_close)
            open_ = float(fast.open or prev_close)
            high = float(fast.day_high or price)
            low = float(fast.day_low or price)
            volume = int(fast.three_month_average_volume or 0)

            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0.0

            return QuoteResponse(
                symbol=symbol.upper(),
                exchange=exchange.upper(),
                name=symbol.upper(),       # avoid the expensive tk.info call
                price=round(price, 2),
                open=round(open_, 2),
                high=round(high, 2),
                low=round(low, 2),
                prev_close=round(prev_close, 2),
                change=round(change, 2),
                change_pct=round(change_pct, 2),
                volume=volume,
            )
        except Exception as exc:
            last_exc = exc
            if delay is not None:
                logger.warning(
                    "yfinance attempt %d for %s failed (%s), retrying in %.1fs",
                    attempt + 1, ticker_sym, exc, delay,
                )
                time.sleep(delay)

    logger.error("yfinance failed all retries for %s: %s", ticker_sym, last_exc)
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def get_quote(symbol: str, exchange: str = "NSE") -> QuoteResponse:
    """Return the best available quote, with multi-level fallback.

    Priority:
      1. Fresh cache hit → return immediately
      2. NSE India API (NSE only)
      3. Yahoo Finance with retry
      4. Stale cache entry (up to 1 h old) with a warning flag in the name
      5. Raise RuntimeError so the API layer can return 502
    """
    symbol = symbol.upper().strip()
    exchange = exchange.upper().strip()
    key = _cache_key(symbol, exchange)

    # 1. Fresh cache
    entry = _get_cache_entry(symbol, exchange)
    if entry and _is_fresh(entry):
        return entry.quote

    # In-flight deduplication: if another thread is already fetching this
    # symbol, wait for it to finish and then serve from cache.
    waiter_event: Optional[threading.Event] = None
    with _inflight_lock:
        if key in _inflight:
            waiter_event = _inflight[key]   # we are a waiter
        else:
            # we are the fetcher – register an event for other threads to wait on
            fetch_event = threading.Event()
            _inflight[key] = fetch_event

    if waiter_event is not None:
        # We are a waiter: wait up to 15 s for the fetching thread.
        waiter_event.wait(timeout=15)
        entry = _get_cache_entry(symbol, exchange)
        if entry and _is_fresh(entry):
            return entry.quote
        if entry and _is_usable_stale(entry):
            return entry.quote
        # fetcher failed or timed out; fall through to direct fetch below

    try:
        quote: Optional[QuoteResponse] = None

        # 2. NSE India API (NSE only)
        if exchange == "NSE":
            quote = _fetch_from_nse(symbol)

        # 3. Yahoo Finance (fallback)
        if quote is None:
            quote = _fetch_from_yfinance(symbol, exchange)

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
            "Check your network connection and try again later."
        )
    finally:
        # Always signal waiting threads regardless of success/failure.
        # Only the fetcher thread registered an event; waiters have no cleanup.
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
    """Fetch OHLCV bars from Yahoo Finance (best free source for Indian EOD data)."""
    ticker_sym = _yf_symbol(symbol, exchange)

    last_exc: Optional[Exception] = None
    for attempt, delay in enumerate((*_YF_RETRY_DELAYS, None)):
        try:
            tk = yf.Ticker(ticker_sym)
            df = tk.history(period=period, interval=interval, auto_adjust=True)
            if df.empty:
                return []
            bars: List[OHLCBar] = []
            for ts, row in df.iterrows():
                bars.append(
                    OHLCBar(
                        timestamp=ts.to_pydatetime().replace(tzinfo=None),
                        open=round(float(row["Open"]), 2),
                        high=round(float(row["High"]), 2),
                        low=round(float(row["Low"]), 2),
                        close=round(float(row["Close"]), 2),
                        volume=int(row["Volume"]),
                    )
                )
            return bars
        except Exception as exc:
            last_exc = exc
            if delay is not None:
                logger.warning(
                    "yfinance historical attempt %d for %s failed, retrying in %.1fs",
                    attempt + 1, ticker_sym, delay,
                )
                time.sleep(delay)

    logger.error("yfinance historical failed all retries for %s: %s", ticker_sym, last_exc)
    return []


# Popular NSE large-cap indices members for a default market overview
NIFTY50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "BAJFINANCE", "ASIANPAINT", "AXISBANK", "MARUTI",
    "SUNPHARMA", "TITAN", "WIPRO", "ULTRACEMCO", "NESTLEIND",
]
