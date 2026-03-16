"""NSE India historical OHLCV data fetcher (no Yahoo Finance dependency).

Uses NSE India's public API directly with proper session/cookie management.
API endpoint:  https://www.nseindia.com/api/historical/cm/equity
               ?series=["EQ"]&symbol=RELIANCE&dateRange=custom
               &from=01-01-2023&to=31-12-2023
"""
from __future__ import annotations

import datetime
import logging
import threading
import time
from typing import List, Optional

import requests

from app.models.schemas import OHLCBar

logger = logging.getLogger(__name__)

_NSE_BASE = "https://www.nseindia.com"
_NSE_HIST_URL = f"{_NSE_BASE}/api/historical/cm/equity"

# Session is re-created when cookies expire; lock ensures thread safety.
_session: Optional[requests.Session] = None
_session_lock = threading.Lock()
_session_created_at: Optional[float] = None
_SESSION_TTL = 1800  # refresh NSE session every 30 minutes

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}


def _get_session() -> requests.Session:
    """Return a live NSE session (refreshed when TTL expires)."""
    global _session, _session_created_at
    with _session_lock:
        now = time.time()
        if _session is None or (_session_created_at and now - _session_created_at > _SESSION_TTL):
            sess = requests.Session()
            sess.headers.update(_HEADERS)
            try:
                # Prime the session: visit the main page to acquire cookies.
                sess.get(_NSE_BASE, timeout=10)
                time.sleep(0.5)
                sess.get(f"{_NSE_BASE}/get-quotes/equity?symbol=NIFTY", timeout=10)
            except Exception as exc:
                logger.debug("NSE session priming failed (non-fatal): %s", exc)
            _session = sess
            _session_created_at = now
        return _session


def _to_date_str(dt: datetime.date) -> str:
    """Convert a date to NSE's DD-MM-YYYY format."""
    return dt.strftime("%d-%m-%Y")


def fetch_nse_historical(
    symbol: str,
    start: datetime.date,
    end: datetime.date,
    series: str = "EQ",
) -> List[OHLCBar]:
    """Fetch daily OHLCV bars from NSE India's public API.

    Returns an empty list on any error (callers should handle gracefully).
    """
    sess = _get_session()
    params = {
        "series": f'["{series}"]',
        "symbol": symbol.upper(),
        "dateRange": "custom",
        "from": _to_date_str(start),
        "to": _to_date_str(end),
    }

    try:
        resp = sess.get(_NSE_HIST_URL, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        logger.warning("NSE historical API error for %s: %s", symbol, exc)
        return []

    rows = payload.get("data", [])
    if not rows:
        logger.debug("NSE historical returned empty data for %s", symbol)
        return []

    bars: List[OHLCBar] = []
    for row in rows:
        try:
            # NSE API returns date as DD-MM-YYYY in CH_TIMESTAMP
            raw_date = row.get("CH_TIMESTAMP", "")
            ts = datetime.datetime.strptime(raw_date, "%d-%m-%Y")

            open_ = float(row.get("CH_OPENING_PRICE") or row.get("CH_PREV_CLS_PRICE") or 0)
            high = float(row.get("CH_TRADE_HIGH_PRICE") or open_)
            low = float(row.get("CH_TRADE_LOW_PRICE") or open_)
            close = float(row.get("CH_CLOSING_PRICE") or open_)
            volume = int(row.get("CH_TOT_TRADED_QTY") or 0)

            if close <= 0:
                continue

            bars.append(
                OHLCBar(
                    timestamp=ts,
                    open=round(open_, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close, 2),
                    volume=volume,
                )
            )
        except Exception as exc:
            logger.debug("Skipping malformed NSE row: %s – %s", row, exc)
            continue

    # NSE returns newest-first; sort chronologically.
    bars.sort(key=lambda b: b.timestamp)
    return bars


def period_to_dates(period: str) -> tuple[datetime.date, datetime.date]:
    """Convert a yfinance-style period string (e.g. '1y', '6mo') to a (start, end) pair."""
    end = datetime.date.today()
    _MAP = {
        "1d": datetime.timedelta(days=1),
        "5d": datetime.timedelta(days=5),
        "1mo": datetime.timedelta(days=30),
        "3mo": datetime.timedelta(days=90),
        "6mo": datetime.timedelta(days=180),
        "1y": datetime.timedelta(days=365),
        "2y": datetime.timedelta(days=730),
        "5y": datetime.timedelta(days=1825),
    }
    delta = _MAP.get(period, datetime.timedelta(days=365))
    return end - delta, end
