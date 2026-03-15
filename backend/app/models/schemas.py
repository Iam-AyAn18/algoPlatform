"""Pydantic request/response schemas."""
from __future__ import annotations
import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.db_models import OrderSide, OrderStatus, OrderType


# ── Market Data ──────────────────────────────────────────────────────────────

class QuoteResponse(BaseModel):
    symbol: str
    exchange: str
    name: str
    price: float
    open: float
    high: float
    low: float
    prev_close: float
    change: float
    change_pct: float
    volume: int
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None


class OHLCBar(BaseModel):
    timestamp: datetime.datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoricalResponse(BaseModel):
    symbol: str
    exchange: str
    interval: str
    bars: List[OHLCBar]


# ── Orders ────────────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    symbol: str = Field(..., description="NSE/BSE ticker e.g. RELIANCE")
    exchange: str = Field("NSE", description="NSE or BSE")
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: int = Field(..., gt=0)
    price: Optional[float] = Field(None, description="Required for LIMIT orders")
    trigger_price: Optional[float] = Field(
        None, description="Required for SL orders – order executes when market price crosses this level"
    )
    strategy: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    symbol: str
    exchange: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float]
    trigger_price: Optional[float]
    executed_price: Optional[float]
    status: OrderStatus
    strategy: Optional[str]
    created_at: datetime.datetime
    executed_at: Optional[datetime.datetime]

    model_config = {"from_attributes": True}


# ── Portfolio / Positions ─────────────────────────────────────────────────────

class PositionResponse(BaseModel):
    symbol: str
    exchange: str
    quantity: int
    avg_buy_price: float
    current_price: float
    unrealised_pnl: float
    unrealised_pnl_pct: float
    realised_pnl: float
    total_value: float

    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    cash: float
    invested: float
    current_value: float
    total_pnl: float
    total_pnl_pct: float
    initial_capital: float
    positions: List[PositionResponse]


# ── Watchlist ─────────────────────────────────────────────────────────────────

class WatchlistAdd(BaseModel):
    symbol: str
    exchange: str = "NSE"


class WatchlistItem(BaseModel):
    id: int
    symbol: str
    exchange: str
    added_at: datetime.datetime
    quote: Optional[QuoteResponse] = None

    model_config = {"from_attributes": True}


# ── Strategies ────────────────────────────────────────────────────────────────

class StrategySignal(BaseModel):
    symbol: str
    strategy: str
    signal: str        # BUY / SELL / HOLD
    confidence: float  # 0-1
    reason: str
    timestamp: datetime.datetime


# ── Backtest ──────────────────────────────────────────────────────────────────

class BacktestRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    strategy: str = Field(
        ...,
        description="MA_CROSSOVER | RSI | MACD | BOLLINGER_BANDS | STOCHASTIC",
    )
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    initial_capital: float = 100_000.0
    params: dict = Field(default_factory=dict)


class BacktestTrade(BaseModel):
    date: datetime.datetime
    action: str
    price: float
    quantity: int
    pnl: float


class BacktestResult(BaseModel):
    symbol: str
    strategy: str
    start_date: str
    end_date: str
    initial_capital: float
    final_value: float
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    total_trades: int
    winning_trades: int
    win_rate_pct: float
    trades: List[BacktestTrade]
    equity_curve: List[dict]
