"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api import market_data, orders, portfolio, strategies, watchlist, backtest
from app.api import broker, algo


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Restore broker settings from DB into the in-process settings object
    # so that market_data can use them immediately on next restart.
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.db_models import BrokerSettings
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(BrokerSettings).where(BrokerSettings.id == 1))
            cfg = result.scalar_one_or_none()
            if cfg and cfg.api_key:
                settings.openalgo_host = cfg.host
                settings.openalgo_api_key = cfg.api_key
    except Exception:
        pass  # non-fatal; defaults from config/env will be used
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "Algorithmic trading platform for the Indian Stock Exchange (NSE/BSE). "
        "Features live market data (NSE India API + OpenAlgo broker), paper trading, "
        "real broker order execution, webhook-based algo trading, Action Center, "
        "technical strategy signals, and backtesting."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_data.router)
app.include_router(orders.router)
app.include_router(portfolio.router)
app.include_router(strategies.router)
app.include_router(watchlist.router)
app.include_router(backtest.router)
app.include_router(broker.router)
app.include_router(algo.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "status": "running",
        "data_sources": "NSE India API + OpenAlgo broker (no Yahoo Finance)",
    }

