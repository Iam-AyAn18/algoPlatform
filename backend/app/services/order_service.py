"""Paper-trading order execution engine."""
from __future__ import annotations
import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Order, OrderSide, OrderStatus, OrderType, Portfolio, Position
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


async def place_order(order_in: OrderCreate, db: AsyncSession) -> OrderResponse:
    portfolio = await _get_or_create_portfolio(db)

    # Fetch current market price
    try:
        quote = get_quote(order_in.symbol, order_in.exchange)
        market_price = quote.price
    except Exception:
        market_price = order_in.price or 0.0

    executed_price = market_price if order_in.order_type == OrderType.MARKET else (order_in.price or market_price)

    order = Order(
        symbol=order_in.symbol.upper(),
        exchange=order_in.exchange.upper(),
        side=order_in.side,
        order_type=order_in.order_type,
        quantity=order_in.quantity,
        price=order_in.price,
        strategy=order_in.strategy,
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
