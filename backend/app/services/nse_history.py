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
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
    "Origin": "https://www.nseindia.com",
    "Connection": "keep-alive",
    "DNT": "1",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "X-Requested-With": "XMLHttpRequest",
}


def _prime_nse_session(sess: requests.Session) -> None:
    """Visit NSE pages to acquire the cookies required by the data APIs.
    Stops at the first failed request to avoid wasting time when there is no
    network access."""
    prime_urls = [
        _NSE_BASE,
        f"{_NSE_BASE}/get-quotes/equity?symbol=RELIANCE",
        f"{_NSE_BASE}/market-data/live-equity-market?index=NIFTY%2050",
    ]
    for url in prime_urls:
        try:
            sess.get(url, timeout=10)
            time.sleep(0.5)
        except Exception as exc:
            logger.debug("NSE session priming skipped for %s: %s", url, exc)
            break  # stop further priming if first visit fails (no network)


def _get_session() -> requests.Session:
    """Return a live NSE session (refreshed when TTL expires)."""
    global _session, _session_created_at
    with _session_lock:
        now = time.time()
        if _session is None or (_session_created_at is not None and now - _session_created_at > _SESSION_TTL):
            sess = requests.Session()
            sess.headers.update(_HEADERS)
            _prime_nse_session(sess)
            _session = sess
            _session_created_at = now
        return _session


def _to_date_str(dt: datetime.date) -> str:
    """Convert a date to NSE's DD-MM-YYYY format."""
    return dt.strftime("%d-%m-%Y")


_NSE_MAX_DAYS = 90   # NSE reliably serves up to ~90-day chunks; larger ranges get 404


def _refresh_session() -> requests.Session:
    """Force-create a brand-new NSE session with fresh cookies."""
    global _session, _session_created_at
    sess = requests.Session()
    sess.headers.update(_HEADERS)
    _prime_nse_session(sess)
    with _session_lock:
        _session = sess
        _session_created_at = time.time()
    return sess


# NSE API may return dates in any of these formats across different responses.
_NSE_DATE_FORMATS = [
    "%d-%m-%Y",        # 21-03-2024  (primary format used in query params)
    "%Y-%m-%d",        # 2024-03-21  (ISO, seen in some API versions)
    "%d-%b-%Y",        # 21-Mar-2024 (abbreviated month)
    "%d-%B-%Y",        # 21-March-2024 (full month name)
    "%Y-%m-%dT%H:%M:%S",     # 2024-03-21T00:00:00 (ISO with time)
    "%Y-%m-%dT%H:%M:%S.%f",  # 2024-03-21T00:00:00.000
]


def _parse_nse_date(raw: str) -> Optional[datetime.datetime]:
    """Try all known NSE date formats; return None if none match."""
    raw = raw.strip()
    for fmt in _NSE_DATE_FORMATS:
        try:
            return datetime.datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _fetch_nse_chunk(
    sess: requests.Session,
    symbol: str,
    start: datetime.date,
    end: datetime.date,
    series: str,
) -> List[OHLCBar]:
    """Fetch a single chunk (must be <= _NSE_MAX_DAYS) from NSE.
    Retries once with a fresh session on 401/403/404 (stale cookie)."""
    params = {
        "series": f'["{series}"]',
        "symbol": symbol.upper(),
        "dateRange": "custom",
        "from": _to_date_str(start),
        "to": _to_date_str(end),
    }
    logger.debug("NSE historical request for %s: %s → %s", symbol, _to_date_str(start), _to_date_str(end))

    for attempt in range(2):          # attempt 0 = normal, attempt 1 = fresh session
        try:
            resp = sess.get(_NSE_HIST_URL, params=params, timeout=15)
            if resp.status_code in (401, 403, 404) and attempt == 0:
                logger.debug(
                    "NSE returned %s for %s – refreshing session and retrying",
                    resp.status_code, symbol,
                )
                sess = _refresh_session()
                time.sleep(1)
                continue               # retry with new session
            resp.raise_for_status()
            payload = resp.json()
            break
        except Exception as exc:
            if attempt == 0:
                logger.debug("NSE chunk fetch failed for %s (attempt 1): %s – retrying", symbol, exc)
                sess = _refresh_session()
                time.sleep(1)
                continue
            logger.warning("NSE historical API error for %s: %s", symbol, exc)
            return []
    else:
        return []

    rows = payload.get("data", [])
    if not rows:
        logger.debug("NSE historical returned empty data for %s (%s→%s)", symbol, start, end)
        return []

    bars: List[OHLCBar] = []
    for row in rows:
        try:
            raw_date = row.get("CH_TIMESTAMP", "") or row.get("mTIMESTAMP", "")
            ts = _parse_nse_date(raw_date)
            if ts is None:
                logger.debug("Skipping NSE row with unparseable date %r for %s", raw_date, symbol)
                continue
            open_ = float(row.get("CH_OPENING_PRICE") or row.get("CH_PREV_CLS_PRICE") or 0)
            high = float(row.get("CH_TRADE_HIGH_PRICE") or open_)
            low = float(row.get("CH_TRADE_LOW_PRICE") or open_)
            close = float(row.get("CH_CLOSING_PRICE") or open_)
            volume = int(row.get("CH_TOT_TRADED_QTY") or 0)
            if close <= 0:
                continue
            bars.append(OHLCBar(
                timestamp=ts,
                open=round(open_, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=volume,
            ))
        except Exception as exc:
            logger.debug("Skipping malformed NSE row: %s – %s", row, exc)
            continue
    return bars


def fetch_nse_historical(
    symbol: str,
    start: datetime.date,
    end: datetime.date,
    series: str = "EQ",
) -> List[OHLCBar]:
    """Fetch daily OHLCV bars from NSE India's public API.

    Automatically chunks requests longer than _NSE_MAX_DAYS days because
    NSE's API returns 404 for date ranges >= 365 days.
    The end date is also capped to yesterday – NSE rejects today/future dates.

    Returns an empty list on any error (callers should handle gracefully).
    """
    # NSE rejects today and future dates – cap to yesterday.
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    if end > yesterday:
        logger.debug("NSE historical: capping end date from %s to %s (yesterday)", end, yesterday)
        end = yesterday

    if start > end:
        logger.debug("NSE historical: start %s is after end %s, returning empty", start, end)
        return []

    sess = _get_session()
    all_bars: List[OHLCBar] = []

    # Split into _NSE_MAX_DAYS-day chunks so we never hit the 404 range limit.
    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(chunk_start + datetime.timedelta(days=_NSE_MAX_DAYS), end)
        bars = _fetch_nse_chunk(sess, symbol, chunk_start, chunk_end, series)
        all_bars.extend(bars)
        chunk_start = chunk_end + datetime.timedelta(days=1)
        if chunk_start <= end:
            time.sleep(0.5)  # be polite to NSE between chunks

    if not all_bars:
        logger.debug("NSE historical returned empty data for %s", symbol)
        return []

    # NSE returns newest-first; sort chronologically.
    all_bars.sort(key=lambda b: b.timestamp)
    return all_bars


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
