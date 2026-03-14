from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schemas import PortfolioSummary
from app.services.portfolio_service import get_portfolio_summary

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("/", response_model=PortfolioSummary)
async def portfolio(db: AsyncSession = Depends(get_db)):
    """Current portfolio summary including positions and P&L."""
    return await get_portfolio_summary(db)
