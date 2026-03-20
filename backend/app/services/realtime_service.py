"""Real-time service: WebSocket connection manager + background tasks.

Architecture
============
ConnectionManager
  Keeps a set of active WebSocket connections and broadcasts JSON messages
  to all of them.  Dead connections are pruned automatically on each send.

price_broadcaster(get_watchlist_symbols)
  asyncio background task.  Every PRICE_POLL_INTERVAL seconds it fetches
  live quotes for the watchlist + top Nifty-50 symbols and broadcasts a
  ``price_update`` message to every connected WebSocket client.

strategy_scanner(get_watchlist_symbols, get_db_session)
  asyncio background task.  Every STRATEGY_SCAN_INTERVAL seconds it runs
  MA-Crossover signals on watchlist symbols.  When a BUY or SELL fires it
  broadcasts a ``strategy_signal`` message.  If the broker is in AUTO mode
  it also places a paper/real order automatically.

WebSocket message envelope
--------------------------
price_update:
  {"type": "price_update",
   "data": {"RELIANCE": {symbol, exchange, price, open, high, low,
                         change, change_pct, volume, prev_close, timestamp},
            ...},
   "timestamp": "<iso>"}

strategy_signal:
  {"type": "strategy_signal",
   "data": {symbol, exchange, strategy, signal, confidence, price},
   "timestamp": "<iso>"}

connection_ack:
  {"type": "connection_ack", "message": "...", "timestamp": "<iso>"}
"""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
from typing import Any, Dict, List, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# ── Tunable constants ─────────────────────────────────────────────────────────

PRICE_POLL_INTERVAL: int = 5       # seconds between price refreshes
STRATEGY_SCAN_INTERVAL: int = 60   # seconds between strategy scans
MAX_STRATEGY_SYMBOLS: int = 5      # max watchlist symbols per scan cycle


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ── Connection Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    """Thread-safe (asyncio) WebSocket connection pool with fan-out broadcast."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    # -- connection lifecycle -------------------------------------------------

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        logger.info("WS client connected. Total: %d", len(self._connections))
        await self._send_single(websocket, {
            "type": "connection_ack",
            "message": "Connected to AlgoPlatform real-time feed",
            "poll_interval_seconds": PRICE_POLL_INTERVAL,
            "timestamp": _now(),
        })

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        logger.info("WS client disconnected. Total: %d", len(self._connections))

    # -- properties -----------------------------------------------------------

    @property
    def num_connections(self) -> int:
        return len(self._connections)

    # -- messaging ------------------------------------------------------------

    async def _send_single(self, ws: WebSocket, data: Dict[str, Any]) -> bool:
        """Send *data* as JSON to one client.  Returns False on failure."""
        try:
            await ws.send_text(json.dumps(data, default=str))
            return True
        except Exception:
            return False

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Fan-out *message* to every connected client; prune dead sockets."""
        if not self._connections:
            return
        dead: Set[WebSocket] = set()
        for ws in list(self._connections):
            ok = await self._send_single(ws, message)
            if not ok:
                dead.add(ws)
        self._connections -= dead


# Singleton – shared between the WS endpoint and all background tasks.
manager = ConnectionManager()


# ── Background task: price broadcaster ───────────────────────────────────────

async def price_broadcaster(get_watchlist_symbols) -> None:
    """Continuously poll live prices and push ``price_update`` events.

    Args:
        get_watchlist_symbols: async callable that returns List[str] of NSE
            ticker symbols currently in the user's watchlist.
    """
    from app.services.market_data import get_quote, NIFTY50_SYMBOLS

    logger.info("Price broadcaster started (interval=%ds)", PRICE_POLL_INTERVAL)
    while True:
        try:
            await asyncio.sleep(PRICE_POLL_INTERVAL)

            # Skip work when no clients are connected.
            if manager.num_connections == 0:
                continue

            # Build symbol list: watchlist first, then Nifty-50 top-10 as filler.
            try:
                wl_symbols: List[str] = await get_watchlist_symbols()
            except Exception:
                wl_symbols = []

            # Deduplicate while preserving order (dict trick).
            symbols: List[str] = list(
                dict.fromkeys(wl_symbols + NIFTY50_SYMBOLS[:10])
            )

            loop = asyncio.get_event_loop()
            prices: Dict[str, Any] = {}

            for symbol in symbols:
                try:
                    quote = await loop.run_in_executor(
                        None, get_quote, symbol, "NSE"
                    )
                    prices[symbol] = {
                        "symbol": quote.symbol,
                        "exchange": quote.exchange,
                        "price": quote.price,
                        "open": quote.open,
                        "high": quote.high,
                        "low": quote.low,
                        "prev_close": quote.prev_close,
                        "change": quote.change,
                        "change_pct": quote.change_pct,
                        "volume": quote.volume,
                        "timestamp": _now(),
                    }
                except Exception as exc:
                    logger.debug("Price fetch skipped for %s: %s", symbol, exc)

            if prices:
                await manager.broadcast({
                    "type": "price_update",
                    "data": prices,
                    "timestamp": _now(),
                })
                logger.info(
                    "Price update broadcast – %d symbol(s): %s",
                    len(prices),
                    ", ".join(prices.keys()),
                )

        except asyncio.CancelledError:
            logger.info("Price broadcaster cancelled")
            break
        except Exception as exc:
            logger.warning("Price broadcaster error: %s", exc)


# ── Background task: strategy scanner + auto-trader ──────────────────────────

async def strategy_scanner(get_watchlist_symbols, get_db_session) -> None:
    """Periodically run strategy signals; broadcast alerts; auto-trade in AUTO mode.

    Args:
        get_watchlist_symbols: async callable → List[str] of NSE ticker symbols.
        get_db_session: callable → async context manager yielding an
            ``AsyncSession`` (i.e. ``AsyncSessionLocal``).
    """
    logger.info("Strategy scanner started (interval=%ds)", STRATEGY_SCAN_INTERVAL)
    while True:
        try:
            await asyncio.sleep(STRATEGY_SCAN_INTERVAL)

            try:
                symbols = await get_watchlist_symbols()
            except Exception:
                symbols = []

            if not symbols:
                continue

            # Fetch current trade mode once per cycle.
            try:
                trade_mode = await _get_trade_mode(get_db_session)
            except Exception:
                trade_mode = "paper"

            loop = asyncio.get_event_loop()

            for symbol in symbols[:MAX_STRATEGY_SYMBOLS]:
                try:
                    from app.services.strategy_service import ma_crossover_signal
                    sig = await loop.run_in_executor(
                        None, ma_crossover_signal, symbol, "NSE"
                    )
                    if sig.signal in ("BUY", "SELL"):
                        # Broadcast signal to UI clients.
                        await manager.broadcast({
                            "type": "strategy_signal",
                            "data": {
                                "symbol": symbol,
                                "exchange": "NSE",
                                "strategy": sig.strategy,
                                "signal": sig.signal,
                                "confidence": sig.confidence,
                                "reason": sig.reason,
                            },
                            "timestamp": _now(),
                        })
                        logger.info(
                            "Strategy signal: %s %s (conf=%.2f)",
                            sig.signal, symbol, sig.confidence,
                        )

                        # Auto-trade when broker is in AUTO mode.
                        if trade_mode == "auto":
                            await _auto_place_order(symbol, sig, get_db_session)

                except Exception as exc:
                    logger.debug("Strategy scan failed for %s: %s", symbol, exc)

        except asyncio.CancelledError:
            logger.info("Strategy scanner cancelled")
            break
        except Exception as exc:
            logger.warning("Strategy scanner error: %s", exc)


# ── Helpers for strategy scanner ─────────────────────────────────────────────

async def _get_trade_mode(get_db_session) -> str:
    from sqlalchemy import select
    from app.models.db_models import BrokerSettings

    async with get_db_session() as db:
        result = await db.execute(
            select(BrokerSettings).where(BrokerSettings.id == 1)
        )
        cfg = result.scalar_one_or_none()
        return cfg.trade_mode if cfg else "paper"


async def _auto_place_order(symbol: str, sig, get_db_session) -> None:
    """Place a market order automatically when in AUTO trade mode."""
    try:
        from app.services.order_service import place_order
        from app.models.schemas import OrderCreate
        from app.models.db_models import OrderSide, OrderType

        side = OrderSide.BUY if sig.signal == "BUY" else OrderSide.SELL
        req = OrderCreate(
            symbol=symbol,
            exchange="NSE",
            side=side,
            order_type=OrderType.MARKET,
            quantity=1,
            strategy=sig.strategy,
            use_broker=True,  # Respect broker routing (paper/real)
        )
        async with get_db_session() as db:
            await place_order(req, db)
        logger.info(
            "Auto-placed %s order for %s (strategy=%s)",
            sig.signal, symbol, sig.strategy,
        )
    except Exception as exc:
        logger.warning("Auto-order failed for %s: %s", symbol, exc)
