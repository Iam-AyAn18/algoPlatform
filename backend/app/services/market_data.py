"""Market data service – fetches live and historical data from Yahoo Finance.
NSE tickers use the .NS suffix, BSE use .BO.
"""
from __future__ import annotations
import datetime
from functools import lru_cache
from typing import List, Optional

import yfinance as yf

from app.models.schemas import OHLCBar, QuoteResponse


def _yf_symbol(symbol: str, exchange: str) -> str:
    symbol = symbol.upper().strip()
    if exchange.upper() == "BSE":
        return f"{symbol}.BO"
    return f"{symbol}.NS"


def get_quote(symbol: str, exchange: str = "NSE") -> QuoteResponse:
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

    return QuoteResponse(
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
