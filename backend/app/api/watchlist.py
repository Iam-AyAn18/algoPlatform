from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List

from app.core.database import get_db
from app.models.db_models import Watchlist
from app.models.schemas import WatchlistAdd, WatchlistItem
from app.services.market_data import get_quote

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


@router.get("/", response_model=List[WatchlistItem])
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Watchlist))
    items = result.scalars().all()
    out = []
    for item in items:
        try:
            quote = get_quote(item.symbol, item.exchange)
        except Exception:
            quote = None
        out.append(WatchlistItem(
            id=item.id,
            symbol=item.symbol,
            exchange=item.exchange,
            added_at=item.added_at,
            quote=quote,
        ))
    return out


@router.post("/", response_model=WatchlistItem, status_code=201)
async def add_to_watchlist(item: WatchlistAdd, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Watchlist).where(Watchlist.symbol == item.symbol.upper()))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Symbol already in watchlist")
    wl = Watchlist(symbol=item.symbol.upper(), exchange=item.exchange.upper())
    db.add(wl)
    await db.commit()
    await db.refresh(wl)
    try:
        quote = get_quote(wl.symbol, wl.exchange)
    except Exception:
        quote = None
    return WatchlistItem(id=wl.id, symbol=wl.symbol, exchange=wl.exchange, added_at=wl.added_at, quote=quote)


@router.delete("/{symbol}", status_code=204)
async def remove_from_watchlist(symbol: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Watchlist).where(Watchlist.symbol == symbol.upper()))
    await db.commit()
