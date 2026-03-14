"""Backend tests for AlgoPlatform."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import init_db, engine, Base


@pytest_asyncio.fixture(autouse=True, scope="module")
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── Health ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert "AlgoPlatform" in data["app"]


# ── Orders ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_place_buy_order(client):
    payload = {
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 1,
    }
    resp = await client.post("/orders/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["symbol"] == "RELIANCE"
    assert data["side"] == "BUY"
    # EXECUTED or REJECTED depending on whether yfinance has data in test env
    assert data["status"] in ("EXECUTED", "REJECTED")


@pytest.mark.asyncio
async def test_list_orders(client):
    resp = await client.get("/orders/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_place_sell_rejected_no_position(client):
    """Selling a stock not in portfolio should be REJECTED."""
    payload = {
        "symbol": "XYZ999FAKE",
        "exchange": "NSE",
        "side": "SELL",
        "order_type": "MARKET",
        "quantity": 10,
    }
    resp = await client.post("/orders/", json=payload)
    assert resp.status_code == 201
    assert resp.json()["status"] == "REJECTED"


# ── Portfolio ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_portfolio(client):
    resp = await client.get("/portfolio/")
    assert resp.status_code == 200
    data = resp.json()
    assert "cash" in data
    assert "initial_capital" in data
    assert "positions" in data
    assert data["initial_capital"] > 0


# ── Strategies ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_strategies(client):
    resp = await client.get("/strategies/")
    assert resp.status_code == 200
    strategies = resp.json()
    assert "MA_CROSSOVER" in strategies
    assert "RSI" in strategies
    assert "MACD" in strategies


@pytest.mark.asyncio
async def test_strategy_signal_invalid(client):
    resp = await client.get("/strategies/signal/RELIANCE?strategy=INVALID_STRAT")
    assert resp.status_code == 400


# ── Watchlist ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_watchlist_add_and_list(client):
    # Add
    resp = await client.post("/watchlist/", json={"symbol": "TCS", "exchange": "NSE"})
    assert resp.status_code == 201
    assert resp.json()["symbol"] == "TCS"

    # List
    resp = await client.get("/watchlist/")
    assert resp.status_code == 200
    symbols = [item["symbol"] for item in resp.json()]
    assert "TCS" in symbols

    # Duplicate
    resp2 = await client.post("/watchlist/", json={"symbol": "TCS", "exchange": "NSE"})
    assert resp2.status_code == 409

    # Remove
    resp3 = await client.delete("/watchlist/TCS")
    assert resp3.status_code == 204


# ── Backtest (unit-level, uses strategy service directly) ─────────────────────

def test_ma_crossover_signal_logic():
    """MA crossover signal returns a valid StrategySignal shape."""
    from app.services.strategy_service import ma_crossover_signal
    import pandas as pd
    import numpy as np

    # Monkey-patch _df_from_bars to return synthetic data
    import app.services.strategy_service as ss

    n = 100
    prices = np.cumsum(np.random.randn(n)) + 200
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    df = pd.DataFrame({"close": prices, "open": prices, "high": prices, "low": prices, "volume": 1000}, index=dates)

    original = ss._df_from_bars
    ss._df_from_bars = lambda sym, exch, period="6mo": df

    result = ma_crossover_signal("TEST", "NSE", short_window=5, long_window=10)
    ss._df_from_bars = original

    assert result.signal in ("BUY", "SELL", "HOLD")
    assert 0.0 <= result.confidence <= 1.0
    assert result.strategy == "MA_CROSSOVER"


def test_rsi_signal_logic():
    """RSI signal detects oversold/overbought conditions correctly."""
    import pandas as pd
    import numpy as np
    import app.services.strategy_service as ss

    n = 60
    # Sharply declining prices → RSI should be low (oversold)
    prices = np.linspace(300, 100, n)
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    df = pd.DataFrame({"close": prices, "open": prices, "high": prices, "low": prices, "volume": 1000}, index=dates)

    original = ss._df_from_bars
    ss._df_from_bars = lambda sym, exch, period="6mo": df

    result = ss.rsi_signal("TEST", "NSE")
    ss._df_from_bars = original

    assert result.signal == "BUY"  # oversold
    assert result.strategy == "RSI"


def test_backtest_service():
    """Backtest service correctly computes return on synthetic data."""
    from app.services.backtest_service import run_backtest, _fetch_df
    from app.models.schemas import BacktestRequest
    import pandas as pd
    import numpy as np
    import app.services.backtest_service as bs

    n = 200
    np.random.seed(42)
    prices = np.cumsum(np.random.randn(n) * 2) + 500
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    df = pd.DataFrame({
        "open": prices, "high": prices * 1.01, "low": prices * 0.99,
        "close": prices, "volume": 10000,
    }, index=dates)

    original = bs._fetch_df
    bs._fetch_df = lambda sym, exch, start, end: df

    req = BacktestRequest(
        symbol="TEST",
        exchange="NSE",
        strategy="MA_CROSSOVER",
        start_date="2022-01-01",
        end_date="2022-12-31",
        initial_capital=100_000,
        params={"short_window": 5, "long_window": 20},
    )
    result = run_backtest(req)
    bs._fetch_df = original

    assert result.initial_capital == 100_000
    assert result.final_value > 0
    assert result.total_trades >= 0
    assert isinstance(result.equity_curve, list)
    assert len(result.equity_curve) > 0
