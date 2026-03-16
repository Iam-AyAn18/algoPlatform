"""Backtesting engine – simulates strategy on historical data."""
from __future__ import annotations
import math
import datetime
from typing import List, Dict

import pandas as pd
import numpy as np

from app.models.schemas import BacktestRequest, BacktestResult, BacktestTrade
from app.services.nse_history import fetch_nse_historical


def _fetch_df(symbol: str, exchange: str, start: str, end: str) -> pd.DataFrame:
    """Fetch OHLCV data for backtesting.

    Priority:
      1. OpenAlgo broker historical API (when configured)
      2. NSE India public historical API
    """
    from app.core.config import settings

    start_dt = datetime.date.fromisoformat(start)
    end_dt = datetime.date.fromisoformat(end)

    # 1. OpenAlgo broker historical data
    if settings.openalgo_api_key and settings.openalgo_host:
        try:
            from app.services.broker_service import get_historical_via_broker
            bars = get_historical_via_broker(
                symbol=symbol,
                exchange=exchange,
                start_date=start,
                end_date=end,
                interval="1d",
                host=settings.openalgo_host,
                api_key=settings.openalgo_api_key,
            )
            if bars:
                return _bars_to_df(bars)
        except Exception:
            pass

    # 2. NSE India public historical API
    bars = fetch_nse_historical(symbol=symbol, start=start_dt, end=end_dt)
    if bars:
        return _bars_to_df(bars)

    return pd.DataFrame()


def _bars_to_df(bars) -> pd.DataFrame:
    """Convert a list of OHLCBar objects to a DataFrame indexed by timestamp."""
    records = [
        {
            "timestamp": b.timestamp,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
        }
        for b in bars
    ]
    df = pd.DataFrame(records)
    df = df.set_index("timestamp")
    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)
    return df


def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def _run_ma_crossover(df: pd.DataFrame, params: dict) -> pd.Series:
    short = int(params.get("short_window", 20))
    long_ = int(params.get("long_window", 50))
    sma_s = df["close"].rolling(short).mean()
    sma_l = df["close"].rolling(long_).mean()
    signal = pd.Series(0, index=df.index)
    signal[sma_s > sma_l] = 1
    signal[sma_s <= sma_l] = -1
    return signal


def _run_rsi(df: pd.DataFrame, params: dict) -> pd.Series:
    period = int(params.get("period", 14))
    oversold = float(params.get("oversold", 30))
    overbought = float(params.get("overbought", 70))
    rsi = _compute_rsi(df["close"], period)
    signal = pd.Series(0, index=df.index)
    signal[rsi < oversold] = 1
    signal[rsi > overbought] = -1
    return signal


def _run_macd(df: pd.DataFrame, params: dict) -> pd.Series:
    fast = int(params.get("fast", 12))
    slow = int(params.get("slow", 26))
    sig_period = int(params.get("signal_period", 9))
    ema_f = df["close"].ewm(span=fast, adjust=False).mean()
    ema_s = df["close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_f - ema_s
    signal_line = macd_line.ewm(span=sig_period, adjust=False).mean()
    hist = macd_line - signal_line
    signal = pd.Series(0, index=df.index)
    signal[hist > 0] = 1
    signal[hist < 0] = -1
    return signal


# ── Bollinger Bands ───────────────────────────────────────────────────────────

def _run_bollinger_bands(df: pd.DataFrame, params: dict) -> pd.Series:
    period = int(params.get("period", 20))
    std_dev = float(params.get("std_dev", 2.0))
    sma = df["close"].rolling(period).mean()
    std = df["close"].rolling(period).std(ddof=0)
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    signal = pd.Series(0, index=df.index)
    signal[df["close"] < lower] = 1    # price below lower band → BUY
    signal[df["close"] > upper] = -1   # price above upper band → SELL
    return signal


# ── Stochastic Oscillator ─────────────────────────────────────────────────────

def _run_stochastic(df: pd.DataFrame, params: dict) -> pd.Series:
    k_period = int(params.get("k_period", 14))
    d_period = int(params.get("d_period", 3))
    oversold = float(params.get("oversold", 20))
    overbought = float(params.get("overbought", 80))
    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min + 1e-9)
    d = k.rolling(d_period).mean()
    signal = pd.Series(0, index=df.index)
    signal[(k < oversold) & (k > d)] = 1    # %K in oversold and crossing above %D
    signal[(k > overbought) & (k < d)] = -1  # %K in overbought and crossing below %D
    return signal


STRATEGY_FNS = {
    "MA_CROSSOVER": _run_ma_crossover,
    "RSI": _run_rsi,
    "MACD": _run_macd,
    "BOLLINGER_BANDS": _run_bollinger_bands,
    "STOCHASTIC": _run_stochastic,
}


def run_backtest(req: BacktestRequest) -> BacktestResult:
    df = _fetch_df(req.symbol, req.exchange, req.start_date, req.end_date)
    if df.empty:
        raise ValueError(f"No data found for {req.symbol} between {req.start_date} and {req.end_date}")

    strategy_fn = STRATEGY_FNS.get(req.strategy.upper())
    if strategy_fn is None:
        raise ValueError(f"Unknown strategy '{req.strategy}'")

    signals = strategy_fn(df, req.params)

    # Simulate trades
    cash = req.initial_capital
    holding = 0
    entry_price = 0.0
    trades: List[BacktestTrade] = []
    equity_curve: List[dict] = []
    prev_signal = 0

    for i, (ts, row) in enumerate(df.iterrows()):
        price = float(row["close"])
        sig = int(signals.iloc[i]) if not pd.isna(signals.iloc[i]) else 0

        if prev_signal != 1 and sig == 1 and holding == 0:
            # BUY
            qty = int(cash // price)
            if qty > 0:
                cost = qty * price
                cash -= cost
                holding = qty
                entry_price = price
                trades.append(BacktestTrade(
                    date=ts.to_pydatetime(),
                    action="BUY",
                    price=round(price, 2),
                    quantity=qty,
                    pnl=0.0,
                ))

        elif prev_signal != -1 and sig == -1 and holding > 0:
            # SELL
            proceeds = holding * price
            pnl = (price - entry_price) * holding
            cash += proceeds
            trades.append(BacktestTrade(
                date=ts.to_pydatetime(),
                action="SELL",
                price=round(price, 2),
                quantity=holding,
                pnl=round(pnl, 2),
            ))
            holding = 0
            entry_price = 0.0

        total_value = cash + holding * price
        equity_curve.append({"date": ts.strftime("%Y-%m-%d"), "value": round(total_value, 2)})
        prev_signal = sig

    # Close any open position at last price
    if holding > 0:
        last_price = float(df["close"].iloc[-1])
        pnl = (last_price - entry_price) * holding
        cash += holding * last_price
        trades.append(BacktestTrade(
            date=df.index[-1].to_pydatetime(),
            action="SELL",
            price=round(last_price, 2),
            quantity=holding,
            pnl=round(pnl, 2),
        ))

    final_value = cash
    total_return_pct = (final_value - req.initial_capital) / req.initial_capital * 100

    winning = [t for t in trades if t.action == "SELL" and t.pnl > 0]
    sell_trades = [t for t in trades if t.action == "SELL"]
    win_rate = len(winning) / len(sell_trades) * 100 if sell_trades else 0.0

    # Max drawdown
    eq_values = [e["value"] for e in equity_curve]
    peak = eq_values[0]
    max_dd = 0.0
    for v in eq_values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Sharpe ratio (annualised, risk-free rate 6% for India)
    daily_returns = pd.Series([e["value"] for e in equity_curve]).pct_change().dropna()
    risk_free_daily = 0.06 / 252
    excess = daily_returns - risk_free_daily
    sharpe = (excess.mean() / excess.std() * math.sqrt(252)) if excess.std() != 0 else 0.0

    return BacktestResult(
        symbol=req.symbol,
        strategy=req.strategy,
        start_date=req.start_date,
        end_date=req.end_date,
        initial_capital=req.initial_capital,
        final_value=round(final_value, 2),
        total_return_pct=round(total_return_pct, 2),
        max_drawdown_pct=round(max_dd, 2),
        sharpe_ratio=round(sharpe, 3),
        total_trades=len(trades),
        winning_trades=len(winning),
        win_rate_pct=round(win_rate, 2),
        trades=trades,
        equity_curve=equity_curve,
    )


