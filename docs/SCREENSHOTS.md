# UI Screenshots & Screen Guide

This document describes every screen in the AlgoPlatform UI with annotated diagrams.

> **Backend dev note:** The UI is a React SPA at `http://localhost:5173`.  
> You don't need the frontend at all — use `http://localhost:8000/docs` (Swagger UI) instead.  
> But this guide helps you understand what each part of the frontend calls from your API.

---

## How to View the UI

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

The backend must also be running at `http://localhost:8000`.

---

## Screen 1 – Dashboard (Default View)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 📈 AlgoPlatform  [NSE · BSE · Paper Trading]                                │
│ [Dashboard] [Portfolio] [Orders] [Strategies] [Backtest]                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Market Overview  Nifty 50 Highlights                              🔄         │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│ │RELIANCE  │ │TCS       │ │HDFCBANK  │ │INFY      │ │ICICIBANK │           │
│ │NSE       │ │NSE       │ │NSE       │ │NSE       │ │NSE       │           │
│ │₹2,847.50 │ │₹3,562.30 │ │₹1,654.20 │ │₹1,892.45 │ │₹1,056.80 │           │
│ │▲ +0.44%  │ │▼ -0.12%  │ │▲ +1.20%  │ │▲ +0.87%  │ │▼ -0.33%  │           │
│ │O:2830 H:2862│        │          │          │          │           │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│ (10 stock tiles total, scrollable)                                           │
├───────────────────────────────────────────┬──────────────────────────────────┤
│ RELIANCE – Price Chart                    │ Watchlist                    🔄  │
│                                           │ ┌────────────────────────────┐  │
│  ₹3,000 ┤                         ╱╲     │ │ + Add symbol  [NSE ▼]  [+] │  │
│  ₹2,800 ┤           ╱╲          ╱   ╲    │ └────────────────────────────┘  │
│  ₹2,600 ┤       ╱╲╱  ╲        ╱      \  │ ┌────────────────────────────┐  │
│  ₹2,400 ┤      ╱      ╲      ╱        \ │ │ RELIANCE  NSE              │  │
│          Jan  Mar  May  Jul  Sep  Nov    │ │ ₹2,847  ▲ +0.44%       🗑️ │  │
│                                           │ ├────────────────────────────┤  │
│  ↑ Green line if current > start price   │ │ TCS      NSE              │  │
│  ↓ Red line if current < start price     │ │ ₹3,562  ▼ -0.12%       🗑️ │  │
│                                           │ └────────────────────────────┘  │
│                                           ├────────────────────────────────┤  │
│                                           │ Place Order                    │  │
│                                           │ Symbol [RELIANCE    ]          │  │
│                                           │ Exchange [NSE ▼]               │  │
│                                           │ Side [BUY] [SELL]              │  │
│                                           │ Type [MARKET ▼]                │  │
│                                           │ Quantity [5        ]           │  │
│                                           │ Strategy [MA_CROSSOVER]        │  │
│                                           │ [   Place BUY Order   ]        │  │
├───────────────────────────────────────────┴────────────────────────────────┤  │
│ Order Book                                                              🔄  │  │
│ ID │ Symbol   │ Side │ Type   │ Qty │ Price    │ Status   │ Strategy   │Time│  │
│  1 │ RELIANCE │ BUY  │ MARKET │   5 │ ₹2,847.50│ EXECUTED │ MA_CROSSOVER│...│  │
│  2 │ TCS      │ BUY  │ MARKET │   2 │ ₹3,562.30│ EXECUTED │ —          │...│  │
└──────────────────────────────────────────────────────────────────────────────┘
```

**What each part calls:**
- Market overview tiles → `GET /market/nifty50`
- Clicking a tile → `GET /market/historical/{symbol}` (updates chart)
- Price chart → `GET /market/historical/{symbol}?period=1y&interval=1d`
- Watchlist → `GET /watchlist/` (on load + refresh)
- Add to watchlist → `POST /watchlist/`
- Remove → `DELETE /watchlist/{symbol}`
- Order form submit → `POST /orders/`
- Order book → `GET /orders/?limit=50`

---

## Screen 2 – Portfolio Tab

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 📈 AlgoPlatform                                                              │
│ [Dashboard] [Portfolio*] [Orders] [Strategies] [Backtest]                   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Portfolio Summary                                                       🔄  │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────┐ │
│ │ Available Cash   │ │ Invested         │ │ Current Value    │ │ Total P&L│ │
│ │ ₹9,85,762.50    │ │ ₹14,237.50      │ │ ₹14,550.00      │ │ ₹312.50  │ │
│ │                  │ │                  │ │                  │ │ ▲ +0.03% │ │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────┘ │
│                                                                              │
│ Symbol   │ Qty │ Avg Buy   │ CMP       │ Unrealised P&L    │ Realised P&L │ Value    │
│──────────┼─────┼───────────┼───────────┼───────────────────┼──────────────┼──────────│
│ RELIANCE │   5 │ ₹2,847.50 │ ₹2,910.00 │ +₹312.50 (+2.19%) │ ₹0.00       │ ₹14,550 │
│ TCS      │   3 │ ₹3,550.00 │ ₹3,612.00 │ +₹186.00 (+1.75%) │ ₹125.00     │ ₹10,836 │
│                                                                              │
│ ← Green P&L = profit   Red P&L = loss                                       │
└──────────────────────────────────────────────────────────────────────────────┘
```

**API call:** `GET /portfolio/`

**Key fields:**
- **Avg Buy** = `avg_buy_price` from the positions table (weighted average of all buys)
- **CMP** = Current Market Price (live from yfinance)
- **Unrealised P&L** = profit/loss if you sold right now
- **Realised P&L** = profit/loss already locked in from past SELL trades

---

## Screen 3 – Orders Tab

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 📈 AlgoPlatform                                                              │
│ [Dashboard] [Portfolio] [Orders*] [Strategies] [Backtest]                   │
├─────────────────────────┬────────────────────────────────────────────────────┤
│ Place Order             │ Order Book                                    🔄   │
│                         │                                                    │
│ Symbol                  │ ID │ Sym   │ Side│ Type  │ Qty│ Price   │ Status  │
│ [INFY         ]         │  3 │ INFY  │ BUY │MARKET │  10│₹1,892.45│EXECUTED │
│                         │  2 │ TCS   │ BUY │MARKET │   3│₹3,562.30│EXECUTED │
│ Exchange [NSE ▼]        │  1 │RELIANC│ BUY │MARKET │   5│₹2,847.50│EXECUTED │
│                         │                                                    │
│ Side                    │ ← Newest orders appear first                       │
│  [  BUY  ] [ SELL ]     │                                                    │
│  (green)   (red)        │ Status badge colours:                              │
│                         │   EXECUTED  → green badge                          │
│ Order Type [MARKET ▼]   │   REJECTED  → red badge                           │
│                         │   CANCELLED → grey badge                           │
│ Quantity [10     ]      │   PENDING   → yellow badge                        │
│                         │                                                    │
│ Strategy Tag (optional) │                                                    │
│ [RSI             ]      │                                                    │
│                         │                                                    │
│ [ Place BUY Order ]     │                                                    │
│ (green button)          │                                                    │
└─────────────────────────┴────────────────────────────────────────────────────┘
```

**API calls:**
- Order form submit → `POST /orders/`
- Order list → `GET /orders/?limit=50`
- After order is placed, the order book auto-refreshes

---

## Screen 4 – Strategies Tab

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 📈 AlgoPlatform                                                              │
│ [Dashboard] [Portfolio] [Orders] [Strategies*] [Backtest]                   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Strategy Signals                                                             │
│                                                                              │
│  [INFY      ]  [NSE ▼]  [MA Crossover ▼]  [⚡ Get Signal]                  │
│                                                                              │
│ ┌───────────────────────────────────────────────────────────────────────┐   │
│ │ ↗  MA_CROSSOVER · INFY                                               │   │
│ │                                                                       │   │
│ │    BUY                                          Confidence            │   │
│ │    (big green text)                             80%                   │   │
│ │                                                                       │   │
│ │  Golden cross: SMA20 crossed above SMA50                             │   │
│ │  15/01/2024, 10:30:00 am                                             │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
│  ↑ Card border is green for BUY, red for SELL, yellow for HOLD              │
│                                                                              │
│  Example SELL signal:                                                        │
│ ┌───────────────────────────────────────────────────────────────────────┐   │
│ │ ↘  RSI · TATASTEEL                                                   │   │
│ │                                                                       │   │
│ │    SELL                                         Confidence            │   │
│ │    (big red text)                               45%                   │   │
│ │                                                                       │   │
│ │  RSI 74.2 is overbought (> 70.0)                                     │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

**API call:** `GET /strategies/signal/{symbol}?strategy=MA_CROSSOVER&exchange=NSE`

**Signal card colours:**
- **Green** border + `BUY` text = bullish signal
- **Red** border + `SELL` text = bearish signal
- **Yellow** border + `HOLD` text = neutral

**How to act on a signal:** Signals don't auto-place orders. Use the signal as input, then go to the **Orders** tab to place the trade manually (or use curl).

---

## Screen 5 – Backtest Tab

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 📈 AlgoPlatform                                                              │
│ [Dashboard] [Portfolio] [Orders] [Strategies] [Backtest*]                   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Backtesting Engine                                                           │
│                                                                              │
│ Symbol    Exchange   Strategy         Start Date   End Date   Capital       │
│ [RELIANCE] [NSE ▼]  [MA Crossover ▼] [2022-01-01] [2024-01-01] [₹100,000] │
│                                                                              │
│ [▶ Run Backtest]   ← shows spinner while loading                            │
│                                                                              │
│ ──── Results (appear after running) ─────────────────────────────────────── │
│                                                                              │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│ │ Final Value  │ │ Total Return │ │ Sharpe Ratio │ │ Max Drawdown │        │
│ │ ₹1,27,450   │ │ +27.45%      │ │ 1.42         │ │ -12.30%      │        │
│ │              │ │ (green)      │ │              │ │ (red)        │        │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘        │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│ │ Total Trades │ │ Win Rate     │ │Winning Trades│ │ Strategy     │        │
│ │      8       │ │   62.5%      │ │      5       │ │ MA_CROSSOVER │        │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                                              │
│ Equity Curve                                                                 │
│  ₹130k ┤                                     ╱╲   ╱                        │
│  ₹120k ┤                         ╱╲          ╱  ╲╱                         │
│  ₹110k ┤              ╱╲╱       ╱  ╲        ╱                              │
│  ₹100k ┤─────────────╱          ╲  ╱╲──────╱                               │
│         Jan'22  Apr'22  Jul'22  Oct'22  Jan'23  Apr'23  Jan'24              │
│  ↑ Green shaded area under the curve                                        │
│                                                                              │
│ Trades (8 total)                                                             │
│ Date       │ Action │ Price    │ Qty │ P&L                                  │
│ 14/03/2022 │ BUY    │ ₹2,410   │  41 │  —                                   │
│ 20/06/2022 │ SELL   │ ₹2,680   │  41 │ +₹11,070  (green)                   │
│ 05/09/2022 │ BUY    │ ₹2,540   │  43 │  —                                   │
│ 12/12/2022 │ SELL   │ ₹2,490   │  43 │ -₹2,150   (red)                     │
│ ...                                                                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

**API call:** `POST /backtest/`

**How to interpret results:**
```
Final Value    > Initial Capital  → strategy was profitable
Total Return   > 0%               → made money
Sharpe Ratio   > 1.0              → good risk-adjusted return
Max Drawdown   < 20%              → acceptable risk (< 10% is excellent)
Win Rate       > 50%              → more winning trades than losing
```

---

## Swagger UI (Best Tool for Backend Devs)

The FastAPI auto-generated docs at `http://localhost:8000/docs` let you:
- See every endpoint with full documentation
- Try any endpoint directly in the browser with a form
- See the exact request/response schemas

```
http://localhost:8000/docs
┌──────────────────────────────────────────────────────────────────┐
│ AlgoPlatform - Indian Stock Exchange                             │
│                                                                  │
│ ▶ Market Data                                                    │
│   GET  /market/quote/{symbol}   Get live quote                  │
│   GET  /market/quotes           Bulk quotes                     │
│   GET  /market/nifty50          Nifty 50 overview               │
│   GET  /market/historical/{symbol}  Historical bars             │
│                                                                  │
│ ▶ Orders                                                         │
│   POST   /orders/               Place order                     │
│   GET    /orders/               List orders                     │
│   GET    /orders/{order_id}     Get order                       │
│   DELETE /orders/{order_id}     Cancel order                    │
│                                                                  │
│ ▶ Portfolio                                                      │
│   GET /portfolio/               Portfolio summary               │
│                                                                  │
│ ▶ Strategies                                                     │
│   GET /strategies/              List strategies                 │
│   GET /strategies/signal/{symbol}  Get signal                   │
│                                                                  │
│ ▶ Watchlist                                                      │
│   GET    /watchlist/            Get watchlist                   │
│   POST   /watchlist/            Add to watchlist                │
│   DELETE /watchlist/{symbol}    Remove from watchlist           │
│                                                                  │
│ ▶ Backtest                                                       │
│   POST /backtest/               Run backtest                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## Toast Notifications (Frontend)

After order actions, a notification appears in the top-right corner:

```
┌─────────────────────────────────────┐
│ ✅ Order executed @ ₹2,847.50        │   ← BUY/SELL success (green)
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ ❌ Order rejected – insufficient     │   ← Rejection (red)
│    funds or no position              │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ ✅ Added RELIANCE to watchlist       │   ← Watchlist add (green)
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ ✅ Backtest complete!                │   ← Backtest done (green)
└─────────────────────────────────────┘
```

---

## Colour Coding Reference

| Colour | Meaning |
|---|---|
| 🟢 Green | Positive (profit, BUY, success) |
| 🔴 Red | Negative (loss, SELL, error, rejection) |
| 🟡 Yellow | Neutral (HOLD, PENDING) |
| ⚫ Grey | Cancelled, N/A |
| 🔵 Dark background | All panels use `bg-gray-900` / `bg-gray-800` (dark theme) |

---

## Navigation Summary

```
Tab          │ What you see                    │ Main API calls
─────────────┼─────────────────────────────────┼──────────────────────────────
Dashboard    │ Market overview + chart +        │ GET /market/nifty50
             │ watchlist + quick order form +   │ GET /market/historical/{sym}
             │ order history                    │ GET /watchlist/
             │                                 │ POST /orders/
             │                                 │ GET /orders/
─────────────┼─────────────────────────────────┼──────────────────────────────
Portfolio    │ Summary cards + holdings table   │ GET /portfolio/
─────────────┼─────────────────────────────────┼──────────────────────────────
Orders       │ Order form + full order history  │ POST /orders/
             │                                 │ GET /orders/
─────────────┼─────────────────────────────────┼──────────────────────────────
Strategies   │ Strategy signal generator        │ GET /strategies/signal/{sym}
─────────────┼─────────────────────────────────┼──────────────────────────────
Backtest     │ Historical simulation form +     │ POST /backtest/
             │ equity curve + trade log         │
```
