from fastapi import APIRouter, HTTPException, Query
from typing import List

from app.models.schemas import StrategySignal
from app.services.strategy_service import get_signal, STRATEGY_MAP

router = APIRouter(prefix="/strategies", tags=["Strategies"])


@router.get("/", response_model=List[str])
def list_strategies():
    """Available trading strategies."""
    return list(STRATEGY_MAP.keys())


@router.get("/signal/{symbol}", response_model=StrategySignal)
def signal(
    symbol: str,
    exchange: str = Query("NSE"),
    strategy: str = Query("MA_CROSSOVER", description="MA_CROSSOVER | RSI | MACD"),
    short_window: int = Query(20),
    long_window: int = Query(50),
    period: int = Query(14),
    oversold: float = Query(30.0),
    overbought: float = Query(70.0),
    fast: int = Query(12),
    slow: int = Query(26),
    signal_period: int = Query(9),
):
    """Generate a live trading signal for a stock."""
    params = dict(
        short_window=short_window,
        long_window=long_window,
        period=period,
        oversold=oversold,
        overbought=overbought,
        fast=fast,
        slow=slow,
        signal_period=signal_period,
    )
    try:
        return get_signal(symbol, exchange, strategy, params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
