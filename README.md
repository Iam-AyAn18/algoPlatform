# AlgoPlatform – Indian Stock Exchange Algo Trading Platform

An open-source algorithmic trading platform built for the **Indian Stock Exchange** (NSE & BSE).  
Features **live market data**, **paper trading**, **technical analysis signals**, and a **backtesting engine** — all wrapped in a clean dark-themed React UI.

---

## ✨ Features

| Feature | Details |
|---|---|
| 📈 Live Market Data | Real-time NSE / BSE quotes via Yahoo Finance (yfinance) |
| 📊 Interactive Charts | 1-year candlestick / area chart with OHLCV data |
| 🛒 Paper Trading | Place MARKET & LIMIT orders with virtual ₹10 Lakh capital |
| 💼 Portfolio Tracking | Real-time P&L, positions, realised & unrealised gains |
| 🔔 Watchlist | Save and monitor your favourite stocks |
| 🧠 Strategy Signals | MA Crossover, RSI, and MACD buy/sell signals |
| 🔬 Backtesting Engine | Test any strategy on historical data with equity curve & stats |
| 📋 Order Book | Full trade history with status tracking |

---

## 🏗️ Architecture

```
algoPlatform/
├── backend/                  # Python FastAPI REST API
│   ├── app/
│   │   ├── api/              # Route handlers
│   │   ├── models/           # Pydantic schemas + SQLAlchemy ORM
│   │   ├── services/         # Business logic
│   │   ├── core/             # Config, DB session
│   │   └── main.py
│   ├── tests/test_api.py
│   └── requirements.txt
│
└── frontend/                 # React + Vite SPA
    └── src/
        ├── api/
        ├── components/
        └── pages/Dashboard.jsx
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# API docs at http://localhost:8000/docs
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# App at http://localhost:5173
```

---

## 🧪 Tests

```bash
cd backend
python -m pytest tests/ -v
# 11 tests covering orders, portfolio, watchlist, strategies, backtesting
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/market/quote/{symbol}` | Live stock quote |
| GET | `/market/nifty50` | Top Nifty 50 stocks |
| GET | `/market/historical/{symbol}` | Historical OHLCV bars |
| POST | `/orders/` | Place paper trade order |
| GET | `/portfolio/` | Portfolio summary & P&L |
| GET/POST | `/watchlist/` | Manage watchlist |
| GET | `/strategies/signal/{symbol}` | Strategy signal |
| POST | `/backtest/` | Run strategy backtest |

### Strategies: `MA_CROSSOVER` · `RSI` · `MACD`

---

## ⚠️ Disclaimer

Paper trading only. Not financial advice. Consult a SEBI-registered advisor for real investments.

---

## 🛠️ Tech Stack

**Backend:** Python · FastAPI · SQLAlchemy · SQLite · yfinance · pandas  
**Frontend:** React 18 · Vite · Tailwind CSS · Recharts · Lucide React
