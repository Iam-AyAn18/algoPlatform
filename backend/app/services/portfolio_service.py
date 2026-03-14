"""Portfolio service – computes current holdings, P&L."""
from __future__ import annotations
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Portfolio, Position
from app.models.schemas import PortfolioSummary, PositionResponse
from app.services.market_data import get_quote
from app.core.config import settings


async def get_portfolio_summary(db: AsyncSession) -> PortfolioSummary:
    # Ensure portfolio row exists
    result = await db.execute(select(Portfolio).where(Portfolio.id == 1))
    portfolio = result.scalar_one_or_none()
    if portfolio is None:
        portfolio = Portfolio(id=1, cash=settings.initial_capital, initial_capital=settings.initial_capital)
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)

    result = await db.execute(select(Position).where(Position.quantity > 0))
    positions_db = result.scalars().all()

    position_responses: List[PositionResponse] = []
    invested = 0.0
    current_value = 0.0

    for pos in positions_db:
        try:
            quote = get_quote(pos.symbol, pos.exchange)
            cur_price = quote.price
        except Exception:
            cur_price = pos.avg_buy_price

        cost = pos.avg_buy_price * pos.quantity
        val = cur_price * pos.quantity
        upnl = val - cost
        upnl_pct = (upnl / cost * 100) if cost else 0.0

        invested += cost
        current_value += val

        position_responses.append(
            PositionResponse(
                symbol=pos.symbol,
                exchange=pos.exchange,
                quantity=pos.quantity,
                avg_buy_price=round(pos.avg_buy_price, 2),
                current_price=round(cur_price, 2),
                unrealised_pnl=round(upnl, 2),
                unrealised_pnl_pct=round(upnl_pct, 2),
                realised_pnl=round(pos.realised_pnl, 2),
                total_value=round(val, 2),
            )
        )

    total_assets = portfolio.cash + current_value
    total_pnl = total_assets - portfolio.initial_capital
    total_pnl_pct = (total_pnl / portfolio.initial_capital * 100) if portfolio.initial_capital else 0.0

    return PortfolioSummary(
        cash=round(portfolio.cash, 2),
        invested=round(invested, 2),
        current_value=round(current_value, 2),
        total_pnl=round(total_pnl, 2),
        total_pnl_pct=round(total_pnl_pct, 2),
        initial_capital=portfolio.initial_capital,
        positions=position_responses,
    )
