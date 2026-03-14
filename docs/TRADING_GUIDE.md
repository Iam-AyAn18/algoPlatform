# Trading Guide – How to Trade on AlgoPlatform
> Step-by-step guide with `curl` examples for every trading action.  
> All examples assume the backend is running at `http://localhost:8000`.

---

## Table of Contents
1. [Starting the Platform](#1-starting-the-platform)
2. [Check Your Starting Balance](#2-check-your-starting-balance)
3. [Find a Stock to Trade](#3-find-a-stock-to-trade)
4. [Add Stocks to Your Watchlist](#4-add-stocks-to-your-watchlist)
5. [Get a Strategy Signal Before Trading](#5-get-a-strategy-signal-before-trading)
6. [Place a BUY Order](#6-place-a-buy-order)
7. [Check Your Open Positions](#7-check-your-open-positions)
8. [Place a SELL Order](#8-place-a-sell-order)
9. [View Your Order History](#9-view-your-order-history)
10. [Run a Backtest Before Trading](#10-run-a-backtest-before-trading)
11. [Full Trading Workflow Example](#11-full-trading-workflow-example)
12. [Common Errors & Fixes](#12-common-errors--fixes)
13. [NSE Symbol Reference](#13-nse-symbol-reference)

---

## 1. Starting the Platform

```bash
# Terminal 1 – Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 – Frontend (optional, for the UI)
cd frontend
npm install
npm run dev
```

- **Backend API**: http://localhost:8000
- **Interactive API docs (Swagger UI)**: http://localhost:8000/docs
- **Frontend UI**: http://localhost:5173

> 💡 **Tip for backend devs:** You can do everything via curl or the Swagger UI at `/docs`. The frontend is optional.

---

## 2. Check Your Starting Balance

```bash
curl http://localhost:8000/portfolio/
```

**Response on first run** (₹10 Lakh starting capital):
```json
{
  "cash": 1000000.0,
  "invested": 0.0,
  "current_value": 0.0,
  "total_pnl": 0.0,
  "total_pnl_pct": 0.0,
  "initial_capital": 1000000.0,
  "positions": []
}
```

---

## 3. Find a Stock to Trade

### Get a live quote for one stock
```bash
# NSE stock (default exchange)
curl "http://localhost:8000/market/quote/RELIANCE"

# BSE stock
curl "http://localhost:8000/market/quote/TCS?exchange=BSE"
```

**Response:**
```json
{
  "symbol": "RELIANCE",
  "exchange": "NSE",
  "name": "Reliance Industries Limited",
  "price": 2847.50,
  "open": 2830.00,
  "high": 2862.00,
  "low": 2825.00,
  "prev_close": 2835.00,
  "change": 12.50,
  "change_pct": 0.44,
  "volume": 8234567,
  "market_cap": 19274820600000,
  "pe_ratio": 28.4,
  "week_52_high": 3024.90,
  "week_52_low": 2220.30
}
```

### Get quotes for multiple stocks at once
```bash
curl "http://localhost:8000/market/quotes?symbols=RELIANCE,TCS,INFY&exchange=NSE"
```

### Get the Nifty 50 market overview
```bash
curl http://localhost:8000/market/nifty50
```

### Get historical price data (for charting / analysis)
```bash
# 1 year of daily data
curl "http://localhost:8000/market/historical/RELIANCE?period=1y&interval=1d"

# 3 months of weekly data
curl "http://localhost:8000/market/historical/TCS?period=3mo&interval=1wk"

# 1 month of hourly data
curl "http://localhost:8000/market/historical/INFY?period=1mo&interval=1h"
```

**Period values:** `1d` `5d` `1mo` `3mo` `6mo` `1y` `2y` `5y`  
**Interval values:** `1m` `5m` `15m` `1h` `1d` `1wk` `1mo`

---

## 4. Add Stocks to Your Watchlist

```bash
# Add RELIANCE to watchlist
curl -X POST http://localhost:8000/watchlist/ \
  -H "Content-Type: application/json" \
  -d '{"symbol": "RELIANCE", "exchange": "NSE"}'

# Add TCS
curl -X POST http://localhost:8000/watchlist/ \
  -H "Content-Type: application/json" \
  -d '{"symbol": "TCS", "exchange": "NSE"}'

# Add HDFCBANK on BSE
curl -X POST http://localhost:8000/watchlist/ \
  -H "Content-Type: application/json" \
  -d '{"symbol": "HDFCBANK", "exchange": "BSE"}'
```

**Response (201 Created):**
```json
{
  "id": 1,
  "symbol": "RELIANCE",
  "exchange": "NSE",
  "added_at": "2024-01-15T10:30:00",
  "quote": {
    "symbol": "RELIANCE",
    "price": 2847.50,
    "change_pct": 0.44,
    ...
  }
}
```

### View your watchlist
```bash
curl http://localhost:8000/watchlist/
```

### Remove from watchlist
```bash
curl -X DELETE http://localhost:8000/watchlist/RELIANCE
```

---

## 5. Get a Strategy Signal Before Trading

Before placing an order, you can ask the platform: "Should I BUY or SELL this stock right now?"

### MA Crossover signal
```bash
curl "http://localhost:8000/strategies/signal/RELIANCE?strategy=MA_CROSSOVER&exchange=NSE"
```

### RSI signal
```bash
# Default: oversold < 30, overbought > 70
curl "http://localhost:8000/strategies/signal/TCS?strategy=RSI"

# Custom thresholds
curl "http://localhost:8000/strategies/signal/TCS?strategy=RSI&oversold=25&overbought=75"
```

### MACD signal
```bash
curl "http://localhost:8000/strategies/signal/INFY?strategy=MACD"
```

**Response:**
```json
{
  "symbol": "RELIANCE",
  "strategy": "MA_CROSSOVER",
  "signal": "BUY",
  "confidence": 0.8,
  "reason": "Golden cross: SMA20 crossed above SMA50",
  "timestamp": "2024-01-15T10:30:00"
}
```

**Signal values:**
- `BUY` → the strategy thinks this is a good time to buy
- `SELL` → the strategy thinks this is a good time to sell
- `HOLD` → neutral (RSI in 30–70 range or insufficient data)

**Confidence:** 0–1 scale
- `0.8–0.85` = fresh crossover (strong signal)
- `0.5–0.55` = existing trend (moderate signal)
- `0.0` = no signal / insufficient data

> ⚠️ **Disclaimer:** Signals are for educational purposes only. They are not financial advice.

---

## 6. Place a BUY Order

### Market Order (fills at current live price)
```bash
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "side": "BUY",
    "order_type": "MARKET",
    "quantity": 5
  }'
```

### Limit Order (fills at your specified price)
```bash
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "TCS",
    "exchange": "NSE",
    "side": "BUY",
    "order_type": "LIMIT",
    "quantity": 2,
    "price": 3500.00
  }'
```

> **Note:** LIMIT orders currently execute at the specified price immediately (no order book). In a real exchange, a limit order would wait until the market price reaches your limit price.

### Tag an order with a strategy
```bash
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "INFY",
    "exchange": "NSE",
    "side": "BUY",
    "order_type": "MARKET",
    "quantity": 10,
    "strategy": "RSI"
  }'
```

**Successful BUY response (201 Created):**
```json
{
  "id": 1,
  "symbol": "RELIANCE",
  "exchange": "NSE",
  "side": "BUY",
  "order_type": "MARKET",
  "quantity": 5,
  "price": null,
  "executed_price": 2847.50,
  "status": "EXECUTED",
  "strategy": null,
  "created_at": "2024-01-15T10:30:00",
  "executed_at": "2024-01-15T10:30:00"
}
```

**Rejected (insufficient funds) response:**
```json
{
  "id": 2,
  "symbol": "RELIANCE",
  "status": "REJECTED",
  "executed_price": null,
  ...
}
```

### How cash is deducted
After a successful BUY of 5 shares at ₹2,847.50:
```
cash deducted = 5 × 2847.50 = ₹14,237.50
new cash      = 1,000,000 - 14,237.50 = ₹985,762.50
position      = { symbol: RELIANCE, qty: 5, avg_buy_price: 2847.50 }
```

---

## 7. Check Your Open Positions

```bash
curl http://localhost:8000/portfolio/
```

**Response after buying RELIANCE and TCS:**
```json
{
  "cash": 965000.00,
  "invested": 35000.00,
  "current_value": 36250.00,
  "total_pnl": 1250.00,
  "total_pnl_pct": 0.13,
  "initial_capital": 1000000.0,
  "positions": [
    {
      "symbol": "RELIANCE",
      "exchange": "NSE",
      "quantity": 5,
      "avg_buy_price": 2847.50,
      "current_price": 2910.00,
      "unrealised_pnl": 312.50,
      "unrealised_pnl_pct": 2.19,
      "realised_pnl": 0.0,
      "total_value": 14550.00
    },
    {
      "symbol": "TCS",
      "exchange": "NSE",
      "quantity": 3,
      "avg_buy_price": 3550.00,
      "current_price": 3612.00,
      "unrealised_pnl": 186.00,
      "unrealised_pnl_pct": 1.75,
      "realised_pnl": 0.0,
      "total_value": 10836.00
    }
  ]
}
```

**P&L Explained:**
```
unrealised_pnl = (current_price - avg_buy_price) × quantity
               = (2910 - 2847.50) × 5 = ₹312.50  (paper profit, not locked in yet)

realised_pnl   = profit/loss from completed SELL trades
               = locked-in profit after selling

total_pnl      = (cash + current_value) - initial_capital
               = "if I sold everything right now, how much did I make?"
```

---

## 8. Place a SELL Order

```bash
# Sell 2 of your 5 RELIANCE shares
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "side": "SELL",
    "order_type": "MARKET",
    "quantity": 2
  }'
```

**After selling 2 shares at ₹2,910:**
```
proceeds     = 2 × 2910 = ₹5,820  (added to cash)
realised_pnl = (2910 - 2847.50) × 2 = ₹125  (locked-in profit)
remaining qty = 5 - 2 = 3 shares still held
```

**Sell ALL shares in a position:**
```bash
# Sell all 5 RELIANCE
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{"symbol": "RELIANCE", "exchange": "NSE", "side": "SELL",
       "order_type": "MARKET", "quantity": 5}'
```
When quantity reaches 0, the position row is removed from the DB.

---

## 9. View Your Order History

```bash
# Last 50 orders
curl http://localhost:8000/orders/

# Last 10 orders
curl "http://localhost:8000/orders/?limit=10"

# Get a specific order by ID
curl http://localhost:8000/orders/1

# Cancel a PENDING order (MARKET orders execute immediately, so
# only LIMIT orders that haven't filled yet can be cancelled)
curl -X DELETE http://localhost:8000/orders/3
```

**Order statuses:**
| Status | Meaning |
|---|---|
| `EXECUTED` | Order filled at `executed_price` |
| `REJECTED` | Not enough cash (BUY) or no position (SELL) |
| `PENDING` | Waiting to be filled (only possible for future order types) |
| `CANCELLED` | Manually cancelled before execution |

---

## 10. Run a Backtest Before Trading

Before committing virtual money, test your strategy on historical data:

```bash
curl -X POST http://localhost:8000/backtest/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "strategy": "MA_CROSSOVER",
    "start_date": "2022-01-01",
    "end_date": "2024-01-01",
    "initial_capital": 100000,
    "params": {
      "short_window": 20,
      "long_window": 50
    }
  }'
```

**RSI backtest:**
```bash
curl -X POST http://localhost:8000/backtest/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "TCS",
    "exchange": "NSE",
    "strategy": "RSI",
    "start_date": "2021-01-01",
    "end_date": "2024-01-01",
    "initial_capital": 100000,
    "params": { "period": 14, "oversold": 30, "overbought": 70 }
  }'
```

**MACD backtest:**
```bash
curl -X POST http://localhost:8000/backtest/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "INFY",
    "exchange": "NSE",
    "strategy": "MACD",
    "start_date": "2020-01-01",
    "end_date": "2024-01-01",
    "initial_capital": 100000,
    "params": { "fast": 12, "slow": 26, "signal_period": 9 }
  }'
```

**Backtest Response:**
```json
{
  "symbol": "RELIANCE",
  "strategy": "MA_CROSSOVER",
  "start_date": "2022-01-01",
  "end_date": "2024-01-01",
  "initial_capital": 100000.0,
  "final_value": 127450.00,
  "total_return_pct": 27.45,
  "max_drawdown_pct": 12.30,
  "sharpe_ratio": 1.42,
  "total_trades": 8,
  "winning_trades": 5,
  "win_rate_pct": 62.5,
  "trades": [
    { "date": "2022-03-14", "action": "BUY",  "price": 2410.00, "quantity": 41, "pnl": 0.0 },
    { "date": "2022-06-20", "action": "SELL", "price": 2680.00, "quantity": 41, "pnl": 11070.0 },
    ...
  ],
  "equity_curve": [
    { "date": "2022-01-03", "value": 100000.0 },
    { "date": "2022-01-04", "value": 100000.0 },
    ...
    { "date": "2024-01-01", "value": 127450.0 }
  ]
}
```

**How to read the results:**

| Metric | Good value | Explanation |
|---|---|---|
| `total_return_pct` | > 0% | Overall gain/loss vs buy-and-hold benchmark |
| `max_drawdown_pct` | < 20% | Worst peak-to-trough loss during the period |
| `sharpe_ratio` | > 1.0 | Risk-adjusted return (India risk-free = 6%) |
| `win_rate_pct` | > 50% | % of SELL trades that were profitable |

---

## 11. Full Trading Workflow Example

This is a complete trading session from scratch:

```bash
# Step 1: Check starting balance
curl http://localhost:8000/portfolio/
# → cash: ₹10,00,000

# Step 2: Research a stock
curl http://localhost:8000/market/quote/HDFCBANK

# Step 3: Backtest a strategy on it (2 years of data)
curl -X POST http://localhost:8000/backtest/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbol":"HDFCBANK","exchange":"NSE","strategy":"RSI",
    "start_date":"2022-01-01","end_date":"2024-01-01",
    "initial_capital":100000,"params":{"oversold":30,"overbought":70}
  }'
# → total_return_pct: 18.2%, sharpe_ratio: 1.1 → looks reasonable

# Step 4: Get a live signal
curl "http://localhost:8000/strategies/signal/HDFCBANK?strategy=RSI"
# → signal: "BUY", confidence: 0.6, reason: "RSI 32.1 is oversold (< 30.0)"

# Step 5: Add to watchlist to track it
curl -X POST http://localhost:8000/watchlist/ \
  -H "Content-Type: application/json" \
  -d '{"symbol":"HDFCBANK","exchange":"NSE"}'

# Step 6: Place a BUY order
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{"symbol":"HDFCBANK","exchange":"NSE","side":"BUY","order_type":"MARKET","quantity":10,"strategy":"RSI"}'
# → status: "EXECUTED", executed_price: 1654.50

# Step 7: Check your position
curl http://localhost:8000/portfolio/
# → positions: [{ symbol: HDFCBANK, qty: 10, avg_buy_price: 1654.50 }]

# Step 8: (Later) RSI goes above 70, get a SELL signal
curl "http://localhost:8000/strategies/signal/HDFCBANK?strategy=RSI"
# → signal: "SELL", confidence: 0.45, reason: "RSI 72.3 is overbought (> 70.0)"

# Step 9: Sell your position
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{"symbol":"HDFCBANK","exchange":"NSE","side":"SELL","order_type":"MARKET","quantity":10,"strategy":"RSI"}'
# → status: "EXECUTED", executed_price: 1748.00

# Step 10: Check your P&L
curl http://localhost:8000/portfolio/
# → cash increased, realised_pnl = (1748 - 1654.50) × 10 = ₹935 profit
```

---

## 12. Common Errors & Fixes

| Error | Cause | Fix |
|---|---|---|
| `"status": "REJECTED"` on BUY | Not enough cash | Check `portfolio.cash` first; buy fewer shares |
| `"status": "REJECTED"` on SELL | You don't hold this stock | Check `portfolio.positions` first |
| `502 Bad Gateway` from market endpoints | yfinance rate limited or symbol not found | Wait 30s and retry; verify symbol name |
| `400 Unknown strategy` | Typo in strategy name | Use `MA_CROSSOVER`, `RSI`, or `MACD` (case-insensitive) |
| `404 Order not found` | Wrong order ID | List orders first: `GET /orders/` |
| `400 Only PENDING orders can be cancelled` | Order already executed | MARKET orders execute immediately; nothing to cancel |
| Empty `bars: []` from historical | Symbol doesn't trade on that exchange | Try `?exchange=BSE` or verify symbol |

---

## 13. NSE Symbol Reference

Popular NSE symbols to get you started:

| Company | NSE Symbol |
|---|---|
| Reliance Industries | `RELIANCE` |
| Tata Consultancy Services | `TCS` |
| HDFC Bank | `HDFCBANK` |
| Infosys | `INFY` |
| ICICI Bank | `ICICIBANK` |
| Hindustan Unilever | `HINDUNILVR` |
| ITC | `ITC` |
| State Bank of India | `SBIN` |
| Bharti Airtel | `BHARTIARTL` |
| Kotak Mahindra Bank | `KOTAKBANK` |
| Larsen & Toubro | `LT` |
| Bajaj Finance | `BAJFINANCE` |
| Asian Paints | `ASIANPAINT` |
| Axis Bank | `AXISBANK` |
| Maruti Suzuki | `MARUTI` |
| Sun Pharmaceutical | `SUNPHARMA` |
| Titan Company | `TITAN` |
| Wipro | `WIPRO` |
| UltraTech Cement | `ULTRACEMCO` |
| Nestlé India | `NESTLEIND` |
| Adani Ports | `ADANIPORTS` |
| Power Grid Corp | `POWERGRID` |
| NTPC | `NTPC` |
| Tata Steel | `TATASTEEL` |
| HCL Technologies | `HCLTECH` |

> For BSE, use the same symbol with `?exchange=BSE`.  
> To find any NSE symbol, search on [nseindia.com](https://www.nseindia.com) — the symbol shown there is the same one to use here.
