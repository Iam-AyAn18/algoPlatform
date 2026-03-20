"""FastAPI application entry point."""
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api import market_data, orders, portfolio, strategies, watchlist, backtest
from app.api import broker, algo
from app.api import ws as ws_router


async def _get_watchlist_symbols():
    """Return the current list of watchlist symbol names from the database."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.db_models import Watchlist

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Watchlist.symbol))
        return [row[0] for row in result.all()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Restore broker credentials from DB into the market_data module-level
    # cache so that quotes can use the broker immediately on next restart.
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.db_models import BrokerSettings
        from app.services.market_data import set_broker_credentials
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(BrokerSettings).where(BrokerSettings.id == 1))
            cfg = result.scalar_one_or_none()
            if cfg and cfg.api_key and cfg.access_token:
                set_broker_credentials(cfg.broker_name, cfg.api_key, cfg.access_token)
    except Exception:
        pass  # non-fatal; paper trading will work without broker credentials

    # Start real-time background tasks.
    from app.core.database import AsyncSessionLocal
    from app.services.realtime_service import price_broadcaster, strategy_scanner

    _price_task = asyncio.create_task(
        price_broadcaster(_get_watchlist_symbols),
        name="price_broadcaster",
    )
    _strategy_task = asyncio.create_task(
        strategy_scanner(_get_watchlist_symbols, AsyncSessionLocal),
        name="strategy_scanner",
    )

    yield

    # Graceful shutdown: cancel background tasks.
    _price_task.cancel()
    _strategy_task.cancel()
    try:
        await asyncio.gather(_price_task, _strategy_task, return_exceptions=True)
    except Exception:
        pass


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "Algorithmic trading platform for the Indian Stock Exchange (NSE/BSE). "
        "Features live market data (NSE India API + direct broker API), paper trading, "
        "real broker order execution via Zerodha Kite Connect (no intermediate server required), "
        "webhook-based algo trading, Action Center, technical strategy signals, and backtesting."
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
app.include_router(ws_router.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "status": "running",
        "data_sources": "NSE India API + Zerodha Kite Connect (direct, no intermediate server, no Yahoo Finance)",
    }

