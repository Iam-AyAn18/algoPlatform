"""Technical analysis strategies that generate BUY/SELL/HOLD signals."""
from __future__ import annotations
import datetime
from typing import List

import pandas as pd
import numpy as np

from app.models.schemas import StrategySignal
from app.services.market_data import get_historical


def _df_from_bars(symbol: str, exchange: str, period: str = "6mo") -> pd.DataFrame:
    bars = get_historical(symbol, exchange, period=period, interval="1d")
    if not bars:
        return pd.DataFrame()
    df = pd.DataFrame([b.model_dump() for b in bars])
    df.set_index("timestamp", inplace=True)
    return df


# ── Moving Average Crossover ──────────────────────────────────────────────────

def ma_crossover_signal(
    symbol: str,
    exchange: str = "NSE",
    short_window: int = 20,
    long_window: int = 50,
) -> StrategySignal:
    df = _df_from_bars(symbol, exchange)
    if df.empty or len(df) < long_window:
        return StrategySignal(
            symbol=symbol, strategy="MA_CROSSOVER", signal="HOLD",
            confidence=0.0, reason="Insufficient data",
            timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        )

    df["sma_short"] = df["close"].rolling(short_window).mean()
    df["sma_long"] = df["close"].rolling(long_window).mean()
    last = df.iloc[-1]
    prev = df.iloc[-2]

    if prev["sma_short"] <= prev["sma_long"] and last["sma_short"] > last["sma_long"]:
        signal, confidence = "BUY", 0.8
        reason = f"Golden cross: SMA{short_window} crossed above SMA{long_window}"
    elif prev["sma_short"] >= prev["sma_long"] and last["sma_short"] < last["sma_long"]:
        signal, confidence = "SELL", 0.8
        reason = f"Death cross: SMA{short_window} crossed below SMA{long_window}"
    elif last["sma_short"] > last["sma_long"]:
        signal, confidence = "BUY", 0.5
        reason = f"SMA{short_window} ({last['sma_short']:.2f}) above SMA{long_window} ({last['sma_long']:.2f})"
    else:
        signal, confidence = "SELL", 0.5
        reason = f"SMA{short_window} ({last['sma_short']:.2f}) below SMA{long_window} ({last['sma_long']:.2f})"

    return StrategySignal(
        symbol=symbol, strategy="MA_CROSSOVER", signal=signal,
        confidence=confidence, reason=reason,
        timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
    )


# ── RSI ───────────────────────────────────────────────────────────────────────

def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def rsi_signal(
    symbol: str,
    exchange: str = "NSE",
    period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> StrategySignal:
    df = _df_from_bars(symbol, exchange)
    if df.empty or len(df) < period + 5:
        return StrategySignal(
            symbol=symbol, strategy="RSI", signal="HOLD",
            confidence=0.0, reason="Insufficient data",
            timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        )

    df["rsi"] = _compute_rsi(df["close"], period)
    rsi_val = df["rsi"].iloc[-1]

    if rsi_val < oversold:
        signal = "BUY"
        confidence = round(min((oversold - rsi_val) / oversold, 1.0), 2)
        reason = f"RSI {rsi_val:.1f} is oversold (< {oversold})"
    elif rsi_val > overbought:
        signal = "SELL"
        confidence = round(min((rsi_val - overbought) / (100 - overbought), 1.0), 2)
        reason = f"RSI {rsi_val:.1f} is overbought (> {overbought})"
    else:
        signal = "HOLD"
        confidence = 0.3
        reason = f"RSI {rsi_val:.1f} is in neutral zone"

    return StrategySignal(
        symbol=symbol, strategy="RSI", signal=signal,
        confidence=confidence, reason=reason,
        timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
    )


# ── MACD ──────────────────────────────────────────────────────────────────────

def macd_signal(
    symbol: str,
    exchange: str = "NSE",
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> StrategySignal:
    df = _df_from_bars(symbol, exchange)
    if df.empty or len(df) < slow + signal_period:
        return StrategySignal(
            symbol=symbol, strategy="MACD", signal="HOLD",
            confidence=0.0, reason="Insufficient data",
            timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        )

    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    last_hist = histogram.iloc[-1]
    prev_hist = histogram.iloc[-2]

    if prev_hist < 0 and last_hist > 0:
        sig, conf = "BUY", 0.85
        reason = "MACD histogram crossed above zero (bullish)"
    elif prev_hist > 0 and last_hist < 0:
        sig, conf = "SELL", 0.85
        reason = "MACD histogram crossed below zero (bearish)"
    elif last_hist > 0:
        sig, conf = "BUY", 0.55
        reason = f"MACD histogram positive ({last_hist:.3f})"
    else:
        sig, conf = "SELL", 0.55
        reason = f"MACD histogram negative ({last_hist:.3f})"

    return StrategySignal(
        symbol=symbol, strategy="MACD", signal=sig,
        confidence=conf, reason=reason,
        timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
    )


# ── Bollinger Bands ───────────────────────────────────────────────────────────

def bollinger_bands_signal(
    symbol: str,
    exchange: str = "NSE",
    period: int = 20,
    std_dev: float = 2.0,
) -> StrategySignal:
    """Generate signal based on Bollinger Bands.

    BUY  when price closes below the lower band (mean-reversion entry).
    SELL when price closes above the upper band (overbought / mean-reversion exit).
    HOLD when price is within the bands.
    """
    df = _df_from_bars(symbol, exchange)
    if df.empty or len(df) < period + 5:
        return StrategySignal(
            symbol=symbol, strategy="BOLLINGER_BANDS", signal="HOLD",
            confidence=0.0, reason="Insufficient data",
            timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        )

    sma = df["close"].rolling(period).mean()
    std = df["close"].rolling(period).std(ddof=0)
    upper = sma + std_dev * std
    lower = sma - std_dev * std

    last_price = df["close"].iloc[-1]
    last_upper = upper.iloc[-1]
    last_lower = lower.iloc[-1]
    last_sma = sma.iloc[-1]
    band_width = last_upper - last_lower

    if last_price < last_lower:
        dist = last_lower - last_price
        confidence = round(min(dist / (band_width / 2 + 1e-9), 1.0), 2)
        signal = "BUY"
        reason = (
            f"Price {last_price:.2f} closed below lower BB {last_lower:.2f} "
            f"(SMA{period}={last_sma:.2f}, σ×{std_dev})"
        )
    elif last_price > last_upper:
        dist = last_price - last_upper
        confidence = round(min(dist / (band_width / 2 + 1e-9), 1.0), 2)
        signal = "SELL"
        reason = (
            f"Price {last_price:.2f} closed above upper BB {last_upper:.2f} "
            f"(SMA{period}={last_sma:.2f}, σ×{std_dev})"
        )
    else:
        # Inside bands – gauge distance to midline for mild bias
        mid_dist = last_price - last_sma
        signal = "HOLD"
        confidence = 0.3
        reason = (
            f"Price {last_price:.2f} within BB [{last_lower:.2f}, {last_upper:.2f}], "
            f"SMA{period}={last_sma:.2f}"
        )

    return StrategySignal(
        symbol=symbol, strategy="BOLLINGER_BANDS", signal=signal,
        confidence=confidence, reason=reason,
        timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
    )


# ── Stochastic Oscillator ─────────────────────────────────────────────────────

def stochastic_signal(
    symbol: str,
    exchange: str = "NSE",
    k_period: int = 14,
    d_period: int = 3,
    oversold: float = 20.0,
    overbought: float = 80.0,
) -> StrategySignal:
    """%K/%D Stochastic Oscillator signal.

    BUY  when %K crosses above %D in the oversold zone.
    SELL when %K crosses below %D in the overbought zone.
    HOLD otherwise.
    """
    df = _df_from_bars(symbol, exchange)
    if df.empty or len(df) < k_period + d_period + 5:
        return StrategySignal(
            symbol=symbol, strategy="STOCHASTIC", signal="HOLD",
            confidence=0.0, reason="Insufficient data",
            timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        )

    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min + 1e-9)
    d = k.rolling(d_period).mean()

    k_last, k_prev = k.iloc[-1], k.iloc[-2]
    d_last, d_prev = d.iloc[-1], d.iloc[-2]

    if k_last < oversold and k_prev <= d_prev and k_last > d_last:
        signal = "BUY"
        confidence = round(min((oversold - k_last) / oversold, 1.0), 2)
        reason = (
            f"Stochastic %K ({k_last:.1f}) crossed above %D ({d_last:.1f}) "
            f"in oversold zone (< {oversold})"
        )
    elif k_last > overbought and k_prev >= d_prev and k_last < d_last:
        signal = "SELL"
        confidence = round(min((k_last - overbought) / (100 - overbought), 1.0), 2)
        reason = (
            f"Stochastic %K ({k_last:.1f}) crossed below %D ({d_last:.1f}) "
            f"in overbought zone (> {overbought})"
        )
    elif k_last < oversold:
        signal = "BUY"
        confidence = 0.4
        reason = f"Stochastic %K ({k_last:.1f}) is oversold (< {oversold})"
    elif k_last > overbought:
        signal = "SELL"
        confidence = 0.4
        reason = f"Stochastic %K ({k_last:.1f}) is overbought (> {overbought})"
    else:
        signal = "HOLD"
        confidence = 0.3
        reason = f"Stochastic %K ({k_last:.1f}), %D ({d_last:.1f}) in neutral zone"

    return StrategySignal(
        symbol=symbol, strategy="STOCHASTIC", signal=signal,
        confidence=confidence, reason=reason,
        timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
    )


STRATEGY_MAP = {
    "MA_CROSSOVER": ma_crossover_signal,
    "RSI": rsi_signal,
    "MACD": macd_signal,
    "BOLLINGER_BANDS": bollinger_bands_signal,
    "STOCHASTIC": stochastic_signal,
}


def get_signal(symbol: str, exchange: str, strategy: str, params: dict = None) -> StrategySignal:
    params = params or {}
    fn = STRATEGY_MAP.get(strategy.upper())
    if fn is None:
        raise ValueError(f"Unknown strategy '{strategy}'. Choose from: {list(STRATEGY_MAP)}")
    return fn(symbol, exchange, **params)
