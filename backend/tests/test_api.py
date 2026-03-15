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


# ── Quote Cache ───────────────────────────────────────────────────────────────

def test_quote_cache_ttl():
    """Cached quotes are returned within TTL and evicted after expiry."""
    import datetime
    from app.services.market_data import (
        _set_cached_quote, _get_cached_quote, clear_quote_cache,
        QUOTE_CACHE_TTL_SECONDS,
    )
    from app.models.schemas import QuoteResponse

    clear_quote_cache()

    dummy = QuoteResponse(
        symbol="CACHE_TEST", exchange="NSE", name="Cache Test", price=100.0,
        open=99.0, high=101.0, low=98.0, prev_close=99.0,
        change=1.0, change_pct=1.0, volume=1000,
    )
    _set_cached_quote("CACHE_TEST", "NSE", dummy)

    # Should hit cache
    cached = _get_cached_quote("CACHE_TEST", "NSE")
    assert cached is not None
    assert cached.symbol == "CACHE_TEST"

    # Expire via time-travel: manually set old timestamp
    from app.services import market_data as md
    import threading
    key = "CACHE_TEST:NSE"
    with md._cache_lock:
        quote, _ = md._quote_cache[key]
        old_time = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - \
                   datetime.timedelta(seconds=QUOTE_CACHE_TTL_SECONDS + 1)
        md._quote_cache[key] = (quote, old_time)

    # Should be evicted now
    assert _get_cached_quote("CACHE_TEST", "NSE") is None

    clear_quote_cache()


# ── SL Order ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sl_order_rejected_without_trigger(client):
    """SL orders without trigger_price should be REJECTED."""
    payload = {
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "side": "SELL",
        "order_type": "SL",
        "quantity": 1,
        # no trigger_price
    }
    resp = await client.post("/orders/", json=payload)
    assert resp.status_code == 201
    assert resp.json()["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_sl_order_field_in_response(client):
    """OrderResponse includes trigger_price field."""
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
    assert "trigger_price" in data  # field present even if None


# ── Portfolio Reset ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_portfolio_reset(client):
    """POST /portfolio/reset returns a clean portfolio at initial capital."""
    resp = await client.post("/portfolio/reset")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cash"] == data["initial_capital"]
    assert data["positions"] == []
    assert data["invested"] == 0.0


# ── New Strategies ────────────────────────────────────────────────────────────

def test_bollinger_bands_signal_logic():
    """Bollinger Bands signal correctly detects price below lower band."""
    import pandas as pd
    import numpy as np
    import app.services.strategy_service as ss

    # Tightly clustered prices (small std) followed by a drop below the lower BB
    rng = np.random.default_rng(42)
    base = 200 + rng.normal(0, 0.2, 59)   # tiny variance → narrow bands
    prices = np.concatenate([base, [185.0]])  # last price is well below lower band
    dates = pd.date_range("2023-01-01", periods=len(prices), freq="B")
    df = pd.DataFrame({"close": prices, "open": prices, "high": prices, "low": prices, "volume": 1000}, index=dates)

    original = ss._df_from_bars
    ss._df_from_bars = lambda sym, exch, period="6mo": df

    result = ss.bollinger_bands_signal("TEST", "NSE", period=20, std_dev=2.0)
    ss._df_from_bars = original

    assert result.signal == "BUY"   # price dropped below lower band
    assert result.strategy == "BOLLINGER_BANDS"
    assert 0.0 <= result.confidence <= 1.0


def test_stochastic_signal_logic():
    """Stochastic signal returns a valid StrategySignal shape."""
    import pandas as pd
    import numpy as np
    import app.services.strategy_service as ss

    n = 60
    np.random.seed(7)
    prices = np.cumsum(np.random.randn(n)) + 200
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    df = pd.DataFrame({"close": prices, "open": prices, "high": prices * 1.01, "low": prices * 0.99, "volume": 1000}, index=dates)

    original = ss._df_from_bars
    ss._df_from_bars = lambda sym, exch, period="6mo": df

    result = ss.stochastic_signal("TEST", "NSE")
    ss._df_from_bars = original

    assert result.signal in ("BUY", "SELL", "HOLD")
    assert result.strategy == "STOCHASTIC"
    assert 0.0 <= result.confidence <= 1.0


@pytest.mark.asyncio
async def test_list_strategies_includes_new(client):
    """GET /strategies/ includes BOLLINGER_BANDS and STOCHASTIC."""
    resp = await client.get("/strategies/")
    assert resp.status_code == 200
    strategies = resp.json()
    assert "BOLLINGER_BANDS" in strategies
    assert "STOCHASTIC" in strategies


def test_backtest_bollinger_bands():
    """Backtest runs end-to-end with BOLLINGER_BANDS strategy."""
    from app.services.backtest_service import run_backtest
    from app.models.schemas import BacktestRequest
    import pandas as pd
    import numpy as np
    import app.services.backtest_service as bs

    n = 200
    np.random.seed(10)
    prices = np.cumsum(np.random.randn(n) * 3) + 300
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    df = pd.DataFrame({
        "open": prices, "high": prices * 1.01, "low": prices * 0.99,
        "close": prices, "volume": 10000,
    }, index=dates)

    original = bs._fetch_df
    bs._fetch_df = lambda sym, exch, start, end: df

    req = BacktestRequest(
        symbol="TEST", exchange="NSE", strategy="BOLLINGER_BANDS",
        start_date="2022-01-01", end_date="2022-12-31", initial_capital=100_000,
        params={"period": 20, "std_dev": 2.0},
    )
    result = run_backtest(req)
    bs._fetch_df = original

    assert result.final_value > 0
    assert result.strategy == "BOLLINGER_BANDS"
    assert len(result.equity_curve) > 0


def test_backtest_stochastic():
    """Backtest runs end-to-end with STOCHASTIC strategy."""
    from app.services.backtest_service import run_backtest
    from app.models.schemas import BacktestRequest
    import pandas as pd
    import numpy as np
    import app.services.backtest_service as bs

    n = 200
    np.random.seed(11)
    prices = np.cumsum(np.random.randn(n) * 2) + 400
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    df = pd.DataFrame({
        "open": prices, "high": prices * 1.01, "low": prices * 0.99,
        "close": prices, "volume": 10000,
    }, index=dates)

    original = bs._fetch_df
    bs._fetch_df = lambda sym, exch, start, end: df

    req = BacktestRequest(
        symbol="TEST", exchange="NSE", strategy="STOCHASTIC",
        start_date="2022-01-01", end_date="2022-12-31", initial_capital=100_000,
        params={"k_period": 14, "d_period": 3},
    )
    result = run_backtest(req)
    bs._fetch_df = original

    assert result.final_value > 0
    assert result.strategy == "STOCHASTIC"
