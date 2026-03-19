# AlgoPlatform – Indian Stock Exchange Algo Trading Platform

An open-source **algorithmic trading platform** for NSE & BSE with **paper trading**, **live market data**, **strategy signals**, a **backtesting engine**, and **direct Zerodha Kite Connect integration** (no intermediate server required).

> **Paper trading** = virtual money only. Start with ₹10 Lakh, trade at real prices. No real money involved unless you connect a real Zerodha account.

---

## 📚 Documentation

| Doc | What it covers |
|---|---|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | System design, data-flow diagrams, every file explained, DB schema |
| **[docs/TRADING_GUIDE.md](docs/TRADING_GUIDE.md)** | How to trade step-by-step with `curl` examples |
| **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** | Every API endpoint with full request/response examples |
| **[docs/SCREENSHOTS.md](docs/SCREENSHOTS.md)** | Annotated screenshots of every UI screen |

---

## ✨ Features

| Feature | Details |
|---|---|
| 📈 Live Market Data | Real-time NSE/BSE quotes via NSE India API (no Yahoo Finance) |
| 📊 Interactive Price Charts | 1-year OHLCV candlestick chart powered by Recharts |
| 🛒 Paper Trading | MARKET, LIMIT & Stop-Loss orders with virtual ₹10 Lakh |
| 💼 Portfolio Tracking | Real-time P&L, unrealised/realised gains per position |
| 🔔 Watchlist | Save and monitor stocks with live auto-refreshing quotes |
| 🧠 Strategy Signals | MA Crossover, RSI, MACD, Bollinger Bands, Stochastic → BUY/SELL/HOLD |
| 🔬 Backtesting Engine | Historical simulation with Sharpe ratio, max drawdown, win rate |
| 📋 Order Book | Full trade audit trail with status tracking |
| 🤖 Algo Trading | Webhook receiver (TradingView compatible) + Action Center |
| 🏦 Zerodha Integration | Direct Kite Connect API (no separate server needed) |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1 – Backend (required)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- **REST API:** http://localhost:8000
- **Swagger UI (interactive docs):** http://localhost:8000/docs  ← *best starting point for backend devs*

### 2 – Frontend (optional but recommended)

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

---

## ⚡ 30-Second Demo (curl)

```bash
# 1. Check your starting balance (₹10 Lakh virtual cash)
curl http://localhost:8000/portfolio/

# 2. Get a live quote
curl http://localhost:8000/market/quote/RELIANCE

# 3. Get a strategy signal
curl "http://localhost:8000/strategies/signal/RELIANCE?strategy=RSI"

# 4. Place a BUY order (paper trade)
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{"symbol":"RELIANCE","side":"BUY","quantity":5}'

# 5. Check your updated portfolio
curl http://localhost:8000/portfolio/

# 6. Run a backtest
curl -X POST http://localhost:8000/backtest/ \
  -H "Content-Type: application/json" \
  -d '{"symbol":"RELIANCE","strategy":"MA_CROSSOVER","start_date":"2022-01-01","end_date":"2024-01-01","initial_capital":100000}'
```

---

## 🧪 Tests

```bash
cd backend
python -m pytest tests/ -v   # 24 tests, all should pass
```

---

## 🏗️ Architecture

```
backend/app/
├── main.py                  ← FastAPI app, router registration, startup lifecycle
├── core/
│   ├── config.py            ← Settings (pydantic-settings + .env support)
│   └── database.py          ← Async SQLite (SQLAlchemy 2.0 + aiosqlite)
├── models/
│   ├── db_models.py         ← ORM: Order, Position, Portfolio, Watchlist,
│   │                             BrokerSettings, WebhookSignal
│   └── schemas.py           ← Pydantic request/response schemas
├── services/
│   ├── market_data.py       ← Multi-source quotes (broker → NSE India → cache)
│   ├── broker_service.py    ← Zerodha Kite Connect direct API (no server needed)
│   ├── nse_history.py       ← NSE India public historical OHLCV API
│   ├── order_service.py     ← Paper trading + real order execution engine
│   ├── portfolio_service.py ← P&L computation
│   ├── strategy_service.py  ← MA / RSI / MACD / Bollinger Bands / Stochastic
│   └── backtest_service.py  ← Historical simulation engine
└── api/
    ├── market_data.py       ← GET /market/*
    ├── orders.py            ← /orders/*
    ├── portfolio.py         ← GET /portfolio/
    ├── strategies.py        ← /strategies/*
    ├── watchlist.py         ← /watchlist/*
    ├── backtest.py          ← POST /backtest/
    ├── broker.py            ← /broker/* (Zerodha auth + settings)
    └── algo.py              ← /algo/* (webhooks + Action Center)
```

**Data-flow for live quotes:**
```
Request → Fresh cache? → Yes: return immediately
                      → No:  Zerodha Kite API (if connected)
                           → NSE India API (nsepython)
                           → Stale cache (up to 1h old)
                           → 502 error
```

→ Full architecture: **[ARCHITECTURE.md](ARCHITECTURE.md)**

---

## 📡 API Endpoints

### Market Data
| Method | Endpoint | Description |
|---|---|---|
| GET | `/market/quote/{symbol}` | Live stock quote (NSE or BSE) |
| GET | `/market/quotes` | Bulk quotes for multiple symbols |
| GET | `/market/nifty50` | Live quotes for Nifty 50 stocks |
| GET | `/market/historical/{symbol}` | Historical OHLCV bars |

### Orders & Portfolio
| Method | Endpoint | Description |
|---|---|---|
| POST | `/orders/` | Place paper or real order |
| GET | `/orders/` | List order history |
| GET | `/orders/{id}` | Get single order |
| GET | `/portfolio/` | Portfolio summary + P&L |
| POST | `/portfolio/reset` | Reset portfolio to initial capital |

### Watchlist & Strategies
| Method | Endpoint | Description |
|---|---|---|
| GET | `/watchlist/` | List watchlist |
| POST | `/watchlist/` | Add symbol to watchlist |
| DELETE | `/watchlist/{symbol}` | Remove from watchlist |
| GET | `/strategies/` | List available strategies |
| GET | `/strategies/signal/{symbol}` | Get BUY/SELL/HOLD signal |
| POST | `/backtest/` | Run historical backtest |

### Broker (Zerodha)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/broker/settings` | Get broker configuration |
| PUT | `/broker/settings` | Save broker credentials |
| POST | `/broker/test-connection` | Ping broker API |
| GET | `/broker/login-url` | Get Zerodha Kite login URL |
| POST | `/broker/exchange-token` | Exchange request_token for access_token |
| GET | `/broker/funds` | Live account funds/margin |
| GET | `/broker/positions` | Live broker positions |
| GET | `/broker/orders` | Live broker order book |

### Algo Trading
| Method | Endpoint | Description |
|---|---|---|
| POST | `/algo/webhook` | Receive trading signal (TradingView etc.) |
| GET | `/algo/webhook/signals` | List received signals |
| GET | `/algo/action-center` | Orders awaiting manual approval |
| POST | `/algo/action-center/{id}/approve` | Approve and execute queued order |
| POST | `/algo/action-center/{id}/reject` | Reject queued order |
| POST | `/algo/action-center/approve-all` | Approve all pending orders |

→ Full reference with request/response examples: **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)**

---

## 🤖 Algo Trading (Webhooks)

Send trading signals from TradingView, GoCharting, or any system that can POST JSON:

```bash
# Example: TradingView alert → webhook
curl -X POST http://localhost:8000/algo/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NIFTY",
    "exchange": "NSE",
    "action": "BUY",
    "quantity": 50,
    "strategy": "MA_Crossover",
    "secret": "your-webhook-secret"
  }'
```

**Trade modes** (set in Broker Settings):

| Mode | Behaviour |
|---|---|
| `paper` | Simulated only – no real orders, no broker required |
| `semi_auto` | Signal queued in **Action Center** for manual review before execution |
| `auto` | Real order placed immediately via Zerodha Kite Connect |

---

## 🏦 Zerodha Kite Connect Integration

The platform calls the **Zerodha REST API directly** – no intermediate server needed.

```
AlgoPlatform  →  Zerodha Kite Connect REST API  (direct, via kiteconnect SDK)
```

### Setup (one-time)
1. Create an app at [developers.kite.trade](https://developers.kite.trade) → get API Key + Secret
2. In the **Broker** tab, enter your API Key, API Secret, and Client ID
3. Click **Get Login URL** → log in with Zerodha credentials

### Daily token refresh
Zerodha access tokens expire at midnight IST and must be refreshed each trading day:

```bash
# 1. Get the login URL
curl http://localhost:8000/broker/login-url

# 2. Visit the URL, log in, copy the request_token from the redirect URL

# 3. Exchange it for an access_token (stored automatically)
curl -X POST "http://localhost:8000/broker/exchange-token?request_token=XXXXX"
```

Or use the **Broker** tab in the UI – the login flow is built in.

---

## ⚙️ Configuration

Create optional `.env` files to override defaults:

```bash
# backend/.env
INITIAL_CAPITAL=1000000              # Starting virtual cash (default ₹10 Lakh)
DATABASE_URL=sqlite+aiosqlite:///./algoplatform.db
KITE_API_KEY=your_kite_api_key       # Optional env-var override
KITE_ACCESS_TOKEN=your_access_token  # Optional env-var override
```

```bash
# frontend/.env
VITE_API_URL=http://localhost:8000   # Backend URL (default: http://localhost:8000)
```

> **Tip:** Broker credentials can also be saved directly through the **Broker Settings** tab in the UI – no `.env` needed.

---

## 📊 Available Trading Strategies

| Strategy | Identifier | Description |
|---|---|---|
| Moving Average Crossover | `MA_CROSSOVER` | Fast/slow SMA crossover signal |
| Relative Strength Index | `RSI` | Overbought/oversold momentum |
| MACD | `MACD` | Trend-following momentum |
| Bollinger Bands | `BOLLINGER_BANDS` | Volatility-based mean reversion |
| Stochastic Oscillator | `STOCHASTIC` | Momentum oscillator |

```bash
# All strategies return: signal (BUY/SELL/HOLD), confidence, reasoning
curl "http://localhost:8000/strategies/signal/TCS?strategy=BOLLINGER_BANDS"
```

---

## ⚠️ Disclaimer

This platform is for **educational and paper trading purposes**. It is **not financial advice**. Past backtest results do not guarantee future returns. Use real-money trading features at your own risk.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11 · FastAPI 0.110 · SQLAlchemy 2.0 · SQLite · pydantic-settings |
| **Market Data** | NSE India API (nsepython) · Zerodha Kite Connect (kiteconnect 5.0) |
| **Analysis** | pandas · numpy · ta (technical-analysis) |
| **Frontend** | React 19 · Vite · Tailwind CSS · Recharts · Axios |
| **Testing** | pytest · pytest-asyncio · httpx (async test client) |

---

## 📁 Project Structure

```
algoPlatform/
├── README.md                    ← You are here
├── ARCHITECTURE.md              ← Detailed system design
├── backend/
│   ├── app/                     ← FastAPI application
│   ├── tests/                   ← pytest test suite (24 tests)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          ← React components (10 components)
│   │   ├── pages/               ← Dashboard page
│   │   └── api/                 ← Axios API client
│   └── package.json
└── docs/
    ├── API_REFERENCE.md
    ├── TRADING_GUIDE.md
    └── SCREENSHOTS.md
```
