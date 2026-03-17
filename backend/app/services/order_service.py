"""Paper-trading and real-broker order execution engine."""
from __future__ import annotations
import datetime
import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import (
    Order, OrderSide, OrderStatus, OrderType, OrderMode,
    Portfolio, Position, BrokerSettings,
)
from app.models.schemas import OrderCreate, OrderResponse
from app.services.market_data import get_quote
from app.core.config import settings


async def _get_or_create_portfolio(db: AsyncSession) -> Portfolio:
    result = await db.execute(select(Portfolio).where(Portfolio.id == 1))
    portfolio = result.scalar_one_or_none()
    if portfolio is None:
        portfolio = Portfolio(id=1, cash=settings.initial_capital, initial_capital=settings.initial_capital)
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)
    return portfolio


async def _get_broker_settings(db: AsyncSession) -> Optional[BrokerSettings]:
    result = await db.execute(select(BrokerSettings).where(BrokerSettings.id == 1))
    return result.scalar_one_or_none()


async def place_order(order_in: OrderCreate, db: AsyncSession) -> OrderResponse:
    # Validate SL order has trigger_price
    if order_in.order_type == OrderType.SL and not order_in.trigger_price:
        order = Order(
            symbol=order_in.symbol.upper(),
            exchange=order_in.exchange.upper(),
            side=order_in.side,
            order_type=order_in.order_type,
            quantity=order_in.quantity,
            price=order_in.price,
            trigger_price=order_in.trigger_price,
            strategy=order_in.strategy,
            status=OrderStatus.REJECTED,
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)
        return OrderResponse.model_validate(order)

    # Determine trade mode from broker settings
    broker_cfg = await _get_broker_settings(db)
    trade_mode = broker_cfg.trade_mode if broker_cfg else "paper"

    # Semi-auto mode: queue order for manual approval in Action Center
    if trade_mode == "semi_auto" and order_in.use_broker:
        order = Order(
            symbol=order_in.symbol.upper(),
            exchange=order_in.exchange.upper(),
            side=order_in.side,
            order_type=order_in.order_type,
            quantity=order_in.quantity,
            price=order_in.price,
            trigger_price=order_in.trigger_price,
            strategy=order_in.strategy,
            status=OrderStatus.PENDING_APPROVAL,
            mode=OrderMode.REAL,
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)
        return OrderResponse.model_validate(order)

    # Auto mode with broker: place real order directly via the broker API
    if trade_mode == "auto" and order_in.use_broker and broker_cfg and broker_cfg.api_key and broker_cfg.access_token:
        return await _place_real_order(order_in, broker_cfg, db)

    # Default: paper trading
    return await _place_paper_order(order_in, db)


async def _place_real_order(
    order_in: OrderCreate,
    broker_cfg: BrokerSettings,
    db: AsyncSession,
) -> OrderResponse:
    """Execute a real order directly via the broker API (no intermediary server)."""
    from app.services.broker_service import place_real_order as broker_place

    price_type_map = {
        OrderType.MARKET: "MARKET",
        OrderType.LIMIT: "LIMIT",
        OrderType.SL: "SL",
    }
    result = broker_place(
        symbol=order_in.symbol,
        exchange=order_in.exchange,
        action=order_in.side.value,
        quantity=order_in.quantity,
        product=broker_cfg.default_product,
        price_type=price_type_map[order_in.order_type],
        price=order_in.price or 0.0,
        trigger_price=order_in.trigger_price or 0.0,
        strategy_tag=order_in.strategy or "",
        broker_name=broker_cfg.broker_name,
        api_key=broker_cfg.api_key,
        access_token=broker_cfg.access_token,
    )

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    if result.get("status") == "success":
        broker_order_id = str(
            result.get("data", {}).get("orderid")
            or result.get("orderid")
            or ""
        )
        order = Order(
            symbol=order_in.symbol.upper(),
            exchange=order_in.exchange.upper(),
            side=order_in.side,
            order_type=order_in.order_type,
            quantity=order_in.quantity,
            price=order_in.price,
            trigger_price=order_in.trigger_price,
            strategy=order_in.strategy,
            status=OrderStatus.EXECUTED,
            mode=OrderMode.REAL,
            broker_order_id=broker_order_id,
            executed_at=now,
        )
    else:
        order = Order(
            symbol=order_in.symbol.upper(),
            exchange=order_in.exchange.upper(),
            side=order_in.side,
            order_type=order_in.order_type,
            quantity=order_in.quantity,
            price=order_in.price,
            trigger_price=order_in.trigger_price,
            strategy=order_in.strategy,
            status=OrderStatus.REJECTED,
            mode=OrderMode.REAL,
        )

    db.add(order)
    await db.commit()
    await db.refresh(order)
    return OrderResponse.model_validate(order)


async def _place_paper_order(order_in: OrderCreate, db: AsyncSession) -> OrderResponse:
    """Execute a simulated paper-trading order."""
    portfolio = await _get_or_create_portfolio(db)

    try:
        quote = get_quote(order_in.symbol, order_in.exchange)
        market_price = quote.price
    except Exception:
        market_price = order_in.price or 0.0

    if order_in.order_type == OrderType.MARKET:
        executed_price = market_price
    elif order_in.order_type == OrderType.LIMIT:
        executed_price = order_in.price or market_price
    else:  # SL
        trigger = order_in.trigger_price
        if order_in.side == OrderSide.SELL:
            executed_price = min(market_price, trigger)
        else:
            executed_price = max(market_price, trigger)

    order = Order(
        symbol=order_in.symbol.upper(),
        exchange=order_in.exchange.upper(),
        side=order_in.side,
        order_type=order_in.order_type,
        quantity=order_in.quantity,
        price=order_in.price,
        trigger_price=order_in.trigger_price,
        strategy=order_in.strategy,
        mode=OrderMode.PAPER,
    )

    total_cost = executed_price * order_in.quantity

    if order_in.side == OrderSide.BUY:
        if portfolio.cash < total_cost:
            order.status = OrderStatus.REJECTED
            db.add(order)
            await db.commit()
            await db.refresh(order)
            return OrderResponse.model_validate(order)

        portfolio.cash -= total_cost
        await _update_position_buy(db, order_in.symbol.upper(), order_in.exchange.upper(), order_in.quantity, executed_price)

    else:  # SELL
        pos = await _get_position(db, order_in.symbol.upper())
        if pos is None or pos.quantity < order_in.quantity:
            order.status = OrderStatus.REJECTED
            db.add(order)
            await db.commit()
            await db.refresh(order)
            return OrderResponse.model_validate(order)

        realised = (executed_price - pos.avg_buy_price) * order_in.quantity
        portfolio.cash += total_cost
        pos.realised_pnl += realised
        pos.quantity -= order_in.quantity
        if pos.quantity == 0:
            pos.avg_buy_price = 0.0

    order.executed_price = round(executed_price, 2)
    order.status = OrderStatus.EXECUTED
    order.executed_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    portfolio.updated_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    db.add(order)
    await db.commit()
    await db.refresh(order)
    return OrderResponse.model_validate(order)


async def approve_action_center_order(order_id: int, db: AsyncSession) -> OrderResponse:
    """Approve a PENDING_APPROVAL order: route to real broker and execute."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise ValueError(f"Order {order_id} not found")
    if order.status != OrderStatus.PENDING_APPROVAL:
        raise ValueError(f"Order {order_id} is not pending approval (status={order.status})")

    broker_cfg = await _get_broker_settings(db)
    if not broker_cfg or not broker_cfg.api_key or not broker_cfg.access_token:
        raise ValueError("Broker not configured – cannot execute real order (API key and access token required)")

    from app.services.broker_service import place_real_order as broker_place

    price_type = "MARKET"
    if order.order_type == OrderType.LIMIT:
        price_type = "LIMIT"
    elif order.order_type == OrderType.SL:
        price_type = "SL"

    broker_result = broker_place(
        symbol=order.symbol,
        exchange=order.exchange,
        action=order.side.value,
        quantity=order.quantity,
        product=broker_cfg.default_product,
        price_type=price_type,
        price=order.price or 0.0,
        trigger_price=order.trigger_price or 0.0,
        strategy_tag=order.strategy or "",
        broker_name=broker_cfg.broker_name,
        api_key=broker_cfg.api_key,
        access_token=broker_cfg.access_token,
    )

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    if broker_result.get("status") == "success":
        order.broker_order_id = str(
            broker_result.get("data", {}).get("orderid")
            or broker_result.get("orderid")
            or ""
        )
        order.status = OrderStatus.EXECUTED
        order.executed_at = now
    else:
        order.status = OrderStatus.REJECTED

    await db.commit()
    await db.refresh(order)
    return OrderResponse.model_validate(order)


async def _get_position(db: AsyncSession, symbol: str) -> Optional[Position]:
    result = await db.execute(select(Position).where(Position.symbol == symbol))
    return result.scalar_one_or_none()


async def _update_position_buy(db: AsyncSession, symbol: str, exchange: str, qty: int, price: float):
    pos = await _get_position(db, symbol)
    if pos is None:
        pos = Position(symbol=symbol, exchange=exchange, quantity=qty, avg_buy_price=price)
    else:
        total_cost = pos.avg_buy_price * pos.quantity + price * qty
        pos.quantity += qty
        pos.avg_buy_price = total_cost / pos.quantity
    db.add(pos)
