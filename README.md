# AlgoPlatform – Indian Stock Exchange Algo Trading Platform

An open-source **algorithmic trading platform** for NSE & BSE with **paper trading**, **live market data**, **strategy signals**, and a **backtesting engine**.

> **Paper trading** = virtual money only. Start with ₹10 Lakh, trade at real prices. No real money involved.

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
| 📈 Live Market Data | Real-time NSE/BSE quotes via Yahoo Finance |
| 📊 Price Charts | 1-year interactive OHLCV chart |
| 🛒 Paper Trading | MARKET & LIMIT orders with virtual ₹10 Lakh |
| 💼 Portfolio Tracking | Real-time P&L, unrealised/realised gains |
| 🔔 Watchlist | Save and monitor stocks with live quotes |
| 🧠 Strategy Signals | MA Crossover, RSI, MACD → BUY/SELL/HOLD |
| 🔬 Backtesting | Historical simulation with Sharpe, drawdown, win rate |
| 📋 Order Book | Full trade audit trail |

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

### 2 – Frontend (optional)

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

---

## ⚡ 30-Second Demo (curl)

```bash
# 1. Check your balance (₹10 Lakh)
curl http://localhost:8000/portfolio/

# 2. Get a live quote
curl http://localhost:8000/market/quote/RELIANCE

# 3. Get a strategy signal
curl "http://localhost:8000/strategies/signal/RELIANCE?strategy=RSI"

# 4. Place a BUY order
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{"symbol":"RELIANCE","side":"BUY","quantity":5}'

# 5. Check your position
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
python -m pytest tests/ -v   # 11 tests, all should pass
```

---

## 🏗️ Architecture

```
backend/app/
├── main.py              ← FastAPI app + router registration
├── core/
│   ├── config.py        ← Settings (pydantic-settings + .env)
│   └── database.py      ← Async SQLite (SQLAlchemy 2.0)
├── models/
│   ├── db_models.py     ← ORM: orders, positions, portfolio, watchlist
│   └── schemas.py       ← Pydantic request/response schemas
├── services/
│   ├── market_data.py   ← yfinance wrapper (quotes + history)
│   ├── order_service.py ← Paper trading engine
│   ├── portfolio_service.py ← P&L computation
│   ├── strategy_service.py  ← MA / RSI / MACD signals
│   └── backtest_service.py  ← Historical simulation
└── api/
    ├── market_data.py   ← GET /market/*
    ├── orders.py        ← /orders/*
    ├── portfolio.py     ← GET /portfolio/
    ├── strategies.py    ← /strategies/*
    ├── watchlist.py     ← /watchlist/*
    └── backtest.py      ← POST /backtest/
```

→ Full architecture: **[ARCHITECTURE.md](ARCHITECTURE.md)**

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/market/quote/{symbol}` | Live stock quote |
| GET | `/market/nifty50` | Top Nifty 50 stocks |
| GET | `/market/historical/{symbol}` | Historical OHLCV bars |
| POST | `/orders/` | Place paper trade |
| GET | `/orders/` | List order history |
| GET | `/portfolio/` | Portfolio + P&L |
| GET/POST/DELETE | `/watchlist/` | Manage watchlist |
| GET | `/strategies/signal/{symbol}` | Trading signal |
| POST | `/backtest/` | Run strategy backtest |

→ Full reference: **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)**

---

## ⚙️ Configuration

```bash
# backend/.env
INITIAL_CAPITAL=1000000        # Starting virtual cash (default ₹10 Lakh)
DATABASE_URL=sqlite+aiosqlite:///./algoplatform.db

# frontend/.env
VITE_API_URL=http://localhost:8000
```

---

## ⚠️ Disclaimer

Paper trading only. Not financial advice. Past backtest results don't guarantee future returns.

---

## 🛠️ Tech Stack

| | Technology |
|---|---|
| **Backend** | Python · FastAPI · SQLAlchemy 2.0 · SQLite · pydantic-settings |
| **Market Data** | yfinance (Yahoo Finance) · NSE `.NS` / BSE `.BO` |
| **Analysis** | pandas · numpy |
| **Frontend** | React 18 · Vite · Tailwind CSS · Recharts · Axios |
