"""Market data service – fetches live and historical data from Yahoo Finance.
NSE tickers use the .NS suffix, BSE use .BO.
"""
from __future__ import annotations
import datetime
import threading
from typing import Dict, List, Optional, Tuple

import yfinance as yf

from app.models.schemas import OHLCBar, QuoteResponse

# ── TTL Quote Cache ───────────────────────────────────────────────────────────
# Caches quotes for QUOTE_CACHE_TTL_SECONDS to avoid hammering yfinance on
# every request (e.g. watchlist page loads, portfolio P&L refreshes).
QUOTE_CACHE_TTL_SECONDS: int = 15

_quote_cache: Dict[str, Tuple[QuoteResponse, datetime.datetime]] = {}
_cache_lock = threading.Lock()


def _cache_key(symbol: str, exchange: str) -> str:
    return f"{symbol.upper()}:{exchange.upper()}"


def _get_cached_quote(symbol: str, exchange: str) -> Optional[QuoteResponse]:
    key = _cache_key(symbol, exchange)
    with _cache_lock:
        entry = _quote_cache.get(key)
        if entry is None:
            return None
        quote, cached_at = entry
        age = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - cached_at).total_seconds()
        if age > QUOTE_CACHE_TTL_SECONDS:
            del _quote_cache[key]
            return None
        return quote


def _set_cached_quote(symbol: str, exchange: str, quote: QuoteResponse) -> None:
    key = _cache_key(symbol, exchange)
    with _cache_lock:
        _quote_cache[key] = (quote, datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


def clear_quote_cache() -> None:
    """Flush the entire quote cache (useful in tests)."""
    with _cache_lock:
        _quote_cache.clear()


def _yf_symbol(symbol: str, exchange: str) -> str:
    symbol = symbol.upper().strip()
    if exchange.upper() == "BSE":
        return f"{symbol}.BO"
    return f"{symbol}.NS"


def get_quote(symbol: str, exchange: str = "NSE") -> QuoteResponse:
    cached = _get_cached_quote(symbol, exchange)
    if cached is not None:
        return cached

    ticker_sym = _yf_symbol(symbol, exchange)
    tk = yf.Ticker(ticker_sym)
    info = tk.fast_info

    try:
        prev_close = float(info.previous_close or 0)
        price = float(info.last_price or prev_close)
        open_ = float(info.open or prev_close)
        high = float(info.day_high or price)
        low = float(info.day_low or price)
        volume = int(info.three_month_average_volume or 0)
    except Exception:
        prev_close = price = open_ = high = low = 0.0
        volume = 0

    change = price - prev_close
    change_pct = (change / prev_close * 100) if prev_close else 0.0

    full_info = {}
    try:
        full_info = tk.info or {}
    except Exception:
        pass

    quote = QuoteResponse(
        symbol=symbol.upper(),
        exchange=exchange.upper(),
        name=full_info.get("longName", symbol),
        price=round(price, 2),
        open=round(open_, 2),
        high=round(high, 2),
        low=round(low, 2),
        prev_close=round(prev_close, 2),
        change=round(change, 2),
        change_pct=round(change_pct, 2),
        volume=volume,
        market_cap=full_info.get("marketCap"),
        pe_ratio=full_info.get("trailingPE"),
        week_52_high=full_info.get("fiftyTwoWeekHigh"),
        week_52_low=full_info.get("fiftyTwoWeekLow"),
    )
    _set_cached_quote(symbol, exchange, quote)
    return quote


def get_historical(
    symbol: str,
    exchange: str = "NSE",
    period: str = "1y",
    interval: str = "1d",
) -> List[OHLCBar]:
    ticker_sym = _yf_symbol(symbol, exchange)
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


# Popular NSE large-cap indices members for a default market overview
NIFTY50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "BAJFINANCE", "ASIANPAINT", "AXISBANK", "MARUTI",
    "SUNPHARMA", "TITAN", "WIPRO", "ULTRACEMCO", "NESTLEIND",
]
