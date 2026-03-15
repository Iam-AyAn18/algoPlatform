from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db
from app.core.config import settings
from app.models.db_models import Portfolio, Position
from app.models.schemas import PortfolioSummary
from app.services.portfolio_service import get_portfolio_summary

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("/", response_model=PortfolioSummary)
async def portfolio(db: AsyncSession = Depends(get_db)):
    """Current portfolio summary including positions and P&L."""
    return await get_portfolio_summary(db)


@router.post("/reset", response_model=PortfolioSummary)
async def reset_portfolio(db: AsyncSession = Depends(get_db)):
    """Reset the paper-trading account: wipe all positions and restore initial capital."""
    # Delete all positions
    await db.execute(delete(Position))

    # Reset or recreate the portfolio row
    result = await db.execute(select(Portfolio).where(Portfolio.id == 1))
    port = result.scalar_one_or_none()
    if port is None:
        port = Portfolio(id=1, cash=settings.initial_capital, initial_capital=settings.initial_capital)
        db.add(port)
    else:
        import datetime
        port.cash = settings.initial_capital
        port.initial_capital = settings.initial_capital
        port.updated_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    await db.commit()
    return await get_portfolio_summary(db)
