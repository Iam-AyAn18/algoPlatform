"""Pydantic request/response schemas."""
from __future__ import annotations
import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from app.models.db_models import OrderSide, OrderStatus, OrderType, OrderMode


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
    # If True and broker is configured, route to real broker; otherwise paper trade
    use_broker: bool = Field(False, description="Execute via connected broker (real order)")


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
    mode: OrderMode = OrderMode.PAPER
    strategy: Optional[str]
    broker_order_id: Optional[str] = None
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


# ── Broker Settings ───────────────────────────────────────────────────────────

class BrokerSettingsUpdate(BaseModel):
    """Update direct broker credentials.

    No intermediate server is required – the platform calls the broker API
    directly using these credentials.

    Currently supported brokers
    ────────────────────────────
      zerodha  Zerodha Kite Connect (https://developers.kite.trade)
      paper    No real broker (default; paper trading only)
    """
    broker_name: str = Field("paper", description="zerodha | groww | paper")
    api_key: str = Field("", description="Broker API key (e.g. Zerodha Kite API key)")
    api_secret: str = Field(
        "",
        description="Broker API secret (used to exchange request_token for access_token)",
    )
    access_token: str = Field(
        "",
        description="Daily access token – obtained via /broker/exchange-token or entered manually",
    )
    user_id: str = Field("", description="Broker user ID (e.g. Zerodha client ID like AB1234)")
    trade_mode: str = Field(
        "paper",
        description="paper | semi_auto | auto. "
                    "paper=no real orders, semi_auto=queue for approval, auto=execute immediately",
    )
    default_product: str = Field("CNC", description="CNC | MIS | NRML")


class BrokerSettingsResponse(BaseModel):
    broker_name: str
    api_key_masked: str       # last 4 chars only for security
    api_secret_set: bool      # True if api_secret has been configured
    access_token_set: bool    # True if access_token has been configured
    user_id: str
    trade_mode: str
    default_product: str
    connected: bool
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class BrokerFundsResponse(BaseModel):
    status: str
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


# ── Webhook / Algo Trading ────────────────────────────────────────────────────

class WebhookPayload(BaseModel):
    """Flexible payload from TradingView or any external alert system."""
    symbol: str = Field(..., description="NSE/BSE ticker e.g. RELIANCE")
    exchange: str = Field("NSE", description="NSE or BSE")
    action: str = Field(..., description="BUY | SELL | EXIT")
    quantity: int = Field(0, description="Number of shares (0 = use strategy default)")
    price: Optional[float] = None
    strategy: Optional[str] = None
    # Webhook secret for basic authentication
    secret: Optional[str] = Field(None, description="Webhook secret key for authentication")


class WebhookSignalResponse(BaseModel):
    id: int
    source: str
    symbol: str
    exchange: str
    action: str
    quantity: int
    price: Optional[float]
    strategy: Optional[str]
    processed: bool
    order_id: Optional[int]
    received_at: datetime.datetime

    model_config = {"from_attributes": True}


class ActionCenterOrder(BaseModel):
    """An order pending manual approval in the Action Center."""
    id: int
    symbol: str
    exchange: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float]
    strategy: Optional[str]
    created_at: datetime.datetime

    model_config = {"from_attributes": True}

