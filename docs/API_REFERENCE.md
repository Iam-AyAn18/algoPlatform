# API Reference
> Complete list of every endpoint with request/response examples.  
> Base URL: `http://localhost:8000`  
> Interactive docs: `http://localhost:8000/docs` (Swagger UI)

---

## Table of Contents
- [Health](#health)
- [Market Data](#market-data)
- [Orders](#orders)
- [Portfolio](#portfolio)
- [Watchlist](#watchlist)
- [Strategies](#strategies)
- [Backtest](#backtest)

---

## Health

### `GET /`
Health check.

```bash
curl http://localhost:8000/
```
```json
{
  "app": "AlgoPlatform - Indian Stock Exchange",
  "version": "1.0.0",
  "docs": "/docs",
  "status": "running"
}
```

---

## Market Data

### `GET /market/quote/{symbol}`
Live quote for a single stock.

| Query Param | Type | Default | Description |
|---|---|---|---|
| `exchange` | string | `NSE` | `NSE` or `BSE` |

```bash
curl "http://localhost:8000/market/quote/RELIANCE?exchange=NSE"
```
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

---

### `GET /market/quotes`
Live quotes for multiple stocks in one call.

| Query Param | Type | Required | Description |
|---|---|---|---|
| `symbols` | string | ✅ | Comma-separated symbols |
| `exchange` | string | | `NSE` (default) or `BSE` |

```bash
curl "http://localhost:8000/market/quotes?symbols=RELIANCE,TCS,INFY"
```
Returns: `array of QuoteResponse` (same structure as single quote)

---

### `GET /market/nifty50`
Live quotes for a curated Nifty 50 sample (top 10 stocks by market cap).

```bash
curl http://localhost:8000/market/nifty50
```
Returns: `array of QuoteResponse`

---

### `GET /market/historical/{symbol}`
Historical OHLCV bars for charting or analysis.

| Query Param | Type | Default | Description |
|---|---|---|---|
| `exchange` | string | `NSE` | `NSE` or `BSE` |
| `period` | string | `1y` | `1d` `5d` `1mo` `3mo` `6mo` `1y` `2y` `5y` |
| `interval` | string | `1d` | `1m` `5m` `15m` `1h` `1d` `1wk` `1mo` |

```bash
curl "http://localhost:8000/market/historical/TCS?period=3mo&interval=1d"
```
```json
{
  "symbol": "TCS",
  "exchange": "NSE",
  "interval": "1d",
  "bars": [
    {
      "timestamp": "2023-10-16T00:00:00",
      "open": 3548.10,
      "high": 3580.00,
      "low": 3530.45,
      "close": 3562.30,
      "volume": 1234567
    },
    ...
  ]
}
```

---

## Orders

### `POST /orders/`
Place a new paper trading order.

**Request body:**
```json
{
  "symbol": "RELIANCE",          // required – NSE/BSE ticker
  "exchange": "NSE",             // optional – "NSE" (default) or "BSE"
  "side": "BUY",                 // required – "BUY" or "SELL"
  "order_type": "MARKET",        // optional – "MARKET" (default) or "LIMIT"
  "quantity": 5,                 // required – must be > 0
  "price": null,                 // optional – required only for LIMIT orders
  "strategy": "MA_CROSSOVER"     // optional – tag for tracking
}
```

```bash
# Market BUY
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{"symbol":"RELIANCE","side":"BUY","quantity":5}'

# Limit SELL
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{"symbol":"RELIANCE","side":"SELL","order_type":"LIMIT","quantity":2,"price":2900.00}'
```

**Response (201 Created):**
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

**Possible `status` values:**
- `EXECUTED` – order filled successfully
- `REJECTED` – insufficient cash (BUY) or no/insufficient position (SELL)

---

### `GET /orders/`
List recent orders (newest first).

| Query Param | Type | Default | Max | Description |
|---|---|---|---|---|
| `limit` | int | `50` | `200` | Number of orders to return |

```bash
curl "http://localhost:8000/orders/?limit=20"
```
Returns: `array of OrderResponse`

---

### `GET /orders/{order_id}`
Get a specific order by ID.

```bash
curl http://localhost:8000/orders/1
```
Returns: `OrderResponse`

**Error (404):**
```json
{"detail": "Order not found"}
```

---

### `DELETE /orders/{order_id}`
Cancel a PENDING order.

```bash
curl -X DELETE http://localhost:8000/orders/3
```
Returns: `204 No Content` on success.

**Error (400) – if order is not PENDING:**
```json
{"detail": "Only PENDING orders can be cancelled"}
```

---

## Portfolio

### `GET /portfolio/`
Full portfolio summary including all open positions with live P&L.

```bash
curl http://localhost:8000/portfolio/
```
```json
{
  "cash": 985762.50,
  "invested": 14237.50,
  "current_value": 14550.00,
  "total_pnl": 312.50,
  "total_pnl_pct": 0.03,
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
    }
  ]
}
```

**Field explanations:**

| Field | Formula |
|---|---|
| `cash` | Available cash to trade |
| `invested` | `Σ (avg_buy_price × quantity)` for all positions |
| `current_value` | `Σ (current_price × quantity)` (live prices) |
| `total_pnl` | `(cash + current_value) - initial_capital` |
| `total_pnl_pct` | `total_pnl / initial_capital × 100` |
| `unrealised_pnl` | `(current_price - avg_buy_price) × quantity` |
| `realised_pnl` | Cumulative profit from completed SELL trades |

---

## Watchlist

### `GET /watchlist/`
Get all watchlist items, each enriched with a live quote.

```bash
curl http://localhost:8000/watchlist/
```
```json
[
  {
    "id": 1,
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "added_at": "2024-01-15T10:00:00",
    "quote": {
      "symbol": "RELIANCE",
      "price": 2847.50,
      "change_pct": 0.44,
      ...
    }
  }
]
```

---

### `POST /watchlist/`
Add a symbol to the watchlist.

```bash
curl -X POST http://localhost:8000/watchlist/ \
  -H "Content-Type: application/json" \
  -d '{"symbol": "TCS", "exchange": "NSE"}'
```
Returns: `WatchlistItem` (201 Created)

**Error (409) – duplicate:**
```json
{"detail": "Symbol already in watchlist"}
```

---

### `DELETE /watchlist/{symbol}`
Remove a symbol from the watchlist.

```bash
curl -X DELETE http://localhost:8000/watchlist/TCS
```
Returns: `204 No Content`

---

## Strategies

### `GET /strategies/`
List all available strategy names.

```bash
curl http://localhost:8000/strategies/
```
```json
["MA_CROSSOVER", "RSI", "MACD"]
```

---

### `GET /strategies/signal/{symbol}`
Generate a live trading signal.

| Query Param | Type | Default | Description |
|---|---|---|---|
| `exchange` | string | `NSE` | Exchange |
| `strategy` | string | `MA_CROSSOVER` | Strategy to use |
| `short_window` | int | `20` | MA Crossover: short SMA period |
| `long_window` | int | `50` | MA Crossover: long SMA period |
| `period` | int | `14` | RSI: lookback period |
| `oversold` | float | `30.0` | RSI: oversold threshold |
| `overbought` | float | `70.0` | RSI: overbought threshold |
| `fast` | int | `12` | MACD: fast EMA period |
| `slow` | int | `26` | MACD: slow EMA period |
| `signal_period` | int | `9` | MACD: signal EMA period |

```bash
# MA Crossover with custom windows
curl "http://localhost:8000/strategies/signal/RELIANCE?strategy=MA_CROSSOVER&short_window=10&long_window=30"

# RSI
curl "http://localhost:8000/strategies/signal/TCS?strategy=RSI"

# MACD with custom params
curl "http://localhost:8000/strategies/signal/INFY?strategy=MACD&fast=8&slow=21&signal_period=5"
```

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

**Error (400) – unknown strategy:**
```json
{"detail": "Unknown strategy 'INVALID'. Choose from: ['MA_CROSSOVER', 'RSI', 'MACD']"}
```

---

## Backtest

### `POST /backtest/`
Simulate a strategy on historical data.

**Request body:**
```json
{
  "symbol": "RELIANCE",       // required
  "exchange": "NSE",          // optional, default "NSE"
  "strategy": "MA_CROSSOVER", // required: MA_CROSSOVER | RSI | MACD
  "start_date": "2022-01-01", // required: YYYY-MM-DD
  "end_date": "2024-01-01",   // required: YYYY-MM-DD
  "initial_capital": 100000,  // optional, default 100,000
  "params": {                 // optional strategy-specific params
    "short_window": 20,
    "long_window": 50
  }
}
```

**`params` options per strategy:**

| Strategy | Param | Default | Description |
|---|---|---|---|
| `MA_CROSSOVER` | `short_window` | `20` | Short SMA period |
| `MA_CROSSOVER` | `long_window` | `50` | Long SMA period |
| `RSI` | `period` | `14` | RSI lookback |
| `RSI` | `oversold` | `30` | Buy threshold |
| `RSI` | `overbought` | `70` | Sell threshold |
| `MACD` | `fast` | `12` | Fast EMA |
| `MACD` | `slow` | `26` | Slow EMA |
| `MACD` | `signal_period` | `9` | Signal EMA |

```bash
curl -X POST http://localhost:8000/backtest/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "RELIANCE",
    "strategy": "MA_CROSSOVER",
    "start_date": "2022-01-01",
    "end_date": "2024-01-01",
    "initial_capital": 100000,
    "params": {"short_window": 20, "long_window": 50}
  }'
```

**Response:**
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
    {
      "date": "2022-03-14T00:00:00",
      "action": "BUY",
      "price": 2410.00,
      "quantity": 41,
      "pnl": 0.0
    },
    {
      "date": "2022-06-20T00:00:00",
      "action": "SELL",
      "price": 2680.00,
      "quantity": 41,
      "pnl": 11070.0
    }
  ],
  "equity_curve": [
    { "date": "2022-01-03", "value": 100000.0 },
    { "date": "2022-01-04", "value": 100000.0 },
    ...
    { "date": "2024-01-01", "value": 127450.0 }
  ]
}
```

---

## Error Response Format

All errors follow FastAPI's standard format:
```json
{
  "detail": "Human-readable error message"
}
```

| HTTP Status | Meaning |
|---|---|
| `400` | Bad request (invalid strategy, can't cancel executed order) |
| `404` | Resource not found (order ID doesn't exist) |
| `409` | Conflict (symbol already in watchlist) |
| `502` | Upstream error (yfinance failed to fetch data) |

---

## Running the Test Suite

```bash
cd backend
python -m pytest tests/ -v

# With output
python -m pytest tests/ -v -s

# Single test
python -m pytest tests/test_api.py::test_place_buy_order -v
```
