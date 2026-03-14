"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api import market_data, orders, portfolio, strategies, watchlist, backtest


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Algorithmic trading platform for the Indian Stock Exchange (NSE/BSE). "
                "Features live market data, paper trading, strategies, and backtesting.",
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


@app.get("/", tags=["Health"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "status": "running",
    }
