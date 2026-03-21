"""SQLAlchemy ORM models for persisted data."""
import datetime
from sqlalchemy import String, Float, Integer, DateTime, Enum, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.core.database import Base


class OrderSide(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    PENDING_APPROVAL = "PENDING_APPROVAL"  # Action Center: awaiting manual approval


class OrderType(str, enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"      # Stop-Loss: triggered when market price crosses trigger_price


class OrderMode(str, enum.Enum):
    PAPER = "PAPER"   # Simulated paper trade (default)
    REAL = "REAL"     # Real order via direct broker API (e.g. Zerodha Kite Connect)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str] = mapped_column(String(5), default="NSE")
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), default=OrderType.MARKET)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=True)           # limit price (LIMIT orders)
    trigger_price: Mapped[float] = mapped_column(Float, nullable=True)   # stop trigger (SL orders)
    executed_price: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING)
    mode: Mapped[OrderMode] = mapped_column(Enum(OrderMode), default=OrderMode.PAPER)
    strategy: Mapped[str] = mapped_column(String(50), nullable=True)
    broker_order_id: Mapped[str] = mapped_column(String(100), nullable=True)  # real broker order ID
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )
    executed_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    exchange: Mapped[str] = mapped_column(String(5), default="NSE")
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    avg_buy_price: Mapped[float] = mapped_column(Float, default=0.0)
    realised_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None), onupdate=datetime.datetime.utcnow
    )


class Portfolio(Base):
    """Single-row table that stores overall account state."""
    __tablename__ = "portfolio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    cash: Mapped[float] = mapped_column(Float, nullable=False)
    initial_capital: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )


class Watchlist(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    exchange: Mapped[str] = mapped_column(String(5), default="NSE")
    added_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )


class BrokerSettings(Base):
    """Stores direct broker connection credentials (single-row table, id=1).

    No intermediate server required – the platform calls the broker API directly
    using the credentials stored here.

    Supported brokers:
      zerodha  – Zerodha Kite Connect (api_key + api_secret + access_token)
      groww    – Groww Developer API (api_key=client_id, api_secret=client_secret, access_token)
      paper    – No real broker; all trades are simulated
    """
    __tablename__ = "broker_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    # Which broker to connect to: "zerodha" | "paper"
    broker_name: Mapped[str] = mapped_column(String(30), default="paper")
    # Zerodha Kite API key (from https://developers.kite.trade)
    api_key: Mapped[str] = mapped_column(String(200), default="")
    # Zerodha Kite API secret (used to exchange request_token → access_token)
    api_secret: Mapped[str] = mapped_column(String(200), default="")
    # Daily access token – must be refreshed each trading day
    access_token: Mapped[str] = mapped_column(String(500), default="")
    # Zerodha user ID (e.g. "AB1234") – for display purposes
    user_id: Mapped[str] = mapped_column(String(50), default="")
    # Trading mode: "paper" = simulate only, "semi_auto" = queue for approval,
    # "auto" = execute real orders immediately via the broker
    trade_mode: Mapped[str] = mapped_column(String(20), default="paper")
    # Default product type for real orders: CNC (delivery), MIS (intraday), NRML (F&O)
    default_product: Mapped[str] = mapped_column(String(10), default="CNC")
    connected: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )


class WebhookSignal(Base):
    """Records incoming webhook signals from TradingView / external platforms."""
    __tablename__ = "webhook_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(50), default="webhook")  # e.g. "tradingview"
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange: Mapped[str] = mapped_column(String(5), default="NSE")
    action: Mapped[str] = mapped_column(String(10), nullable=False)   # BUY / SELL / EXIT
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[float] = mapped_column(Float, nullable=True)
    strategy: Mapped[str] = mapped_column(String(100), nullable=True)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=True)     # full JSON
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    order_id: Mapped[int] = mapped_column(Integer, nullable=True)     # linked Order.id
    received_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )

