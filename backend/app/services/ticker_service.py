"""Zerodha KiteTicker real-time streaming service.

Architecture
============
KiteTickerService
  Wraps the threaded KiteTicker client from the kiteconnect SDK.
  On each tick it puts raw tick data into an asyncio.Queue via
  ``asyncio.run_coroutine_threadsafe`` so the main event loop can
  consume it safely.

ticker_broadcaster(get_watchlist_symbols, get_db_session, manager)
  asyncio background task.  Checks every SETUP_CHECK_INTERVAL seconds
  whether Zerodha is configured; if so it starts (or updates) the
  KiteTicker.  While the ticker is running it drains the tick queue and
  broadcasts ``price_update`` messages to every connected WebSocket client.
  Falls back to doing nothing when Zerodha is not configured (the
  existing HTTP poll price_broadcaster in realtime_service.py handles that).

WebSocket message emitted
--------------------------
price_update:
  {"type": "price_update",
   "source": "kiteticker",
   "data": {"RELIANCE": {symbol, exchange, price, open, high, low,
                          change, change_pct, volume, prev_close, timestamp},
            ...},
   "timestamp": "<iso>"}
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

SETUP_CHECK_INTERVAL: int = 30  # seconds between broker-config re-checks
TICK_QUEUE_TIMEOUT: float = 2.0  # seconds to wait for next tick before re-checking


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ── KiteTickerService ─────────────────────────────────────────────────────────

class KiteTickerService:
    """Manages a single Zerodha KiteTicker WebSocket connection (threaded)."""

    def __init__(self) -> None:
        self._kws = None
        self._running: bool = False
        self._token_to_symbol: Dict[int, str] = {}

    # ── public interface ──────────────────────────────────────────────────────

    @property
    def running(self) -> bool:
        return self._running

    def start(
        self,
        api_key: str,
        access_token: str,
        token_to_symbol: Dict[int, str],
        loop: asyncio.AbstractEventLoop,
        tick_queue: asyncio.Queue,
    ) -> bool:
        """Start KiteTicker in a background thread.

        Returns True if the ticker was started successfully.
        """
        try:
            from kiteconnect import KiteTicker  # noqa: F401
        except ImportError:
            logger.warning("kiteconnect package not installed – KiteTicker unavailable")
            return False

        if not token_to_symbol:
            logger.debug("No instrument tokens to subscribe; ticker not started")
            return False

        if self._running:
            self.stop()

        from kiteconnect import KiteTicker

        self._token_to_symbol = dict(token_to_symbol)
        instrument_tokens = list(token_to_symbol.keys())

        kws = KiteTicker(api_key, access_token)
        self._kws = kws

        def on_ticks(ws, ticks):  # called from ticker thread
            for tick in ticks:
                asyncio.run_coroutine_threadsafe(tick_queue.put(tick), loop)

        def on_connect(ws, response):
            logger.info(
                "KiteTicker connected; subscribing %d instrument token(s)",
                len(instrument_tokens),
            )
            ws.subscribe(instrument_tokens)
            ws.set_mode(ws.MODE_FULL, instrument_tokens)

        def on_error(ws, code, reason):
            logger.error("KiteTicker error %s: %s", code, reason)

        def on_close(ws, code, reason):
            logger.info("KiteTicker closed %s: %s", code, reason)
            self._running = False

        kws.on_ticks = on_ticks
        kws.on_connect = on_connect
        kws.on_error = on_error
        kws.on_close = on_close

        kws.connect(threaded=True)
        self._running = True
        logger.info("KiteTicker started (threaded) – %d symbol(s)", len(instrument_tokens))
        return True

    def stop(self) -> None:
        if self._kws:
            try:
                self._kws.close()
            except Exception:
                pass
            self._kws = None
        self._running = False
        self._token_to_symbol = {}
        logger.info("KiteTicker stopped")

    def update_subscriptions(
        self,
        token_to_symbol: Dict[int, str],
    ) -> None:
        """Add / remove subscribed tokens while the ticker is running."""
        if not self._kws or not self._running:
            return

        new_tokens = set(token_to_symbol.keys())
        old_tokens = set(self._token_to_symbol.keys())
        to_add = new_tokens - old_tokens
        to_remove = old_tokens - new_tokens

        try:
            if to_remove:
                self._kws.unsubscribe(list(to_remove))
                logger.info("KiteTicker unsubscribed %d token(s)", len(to_remove))
            if to_add:
                self._kws.subscribe(list(to_add))
                self._kws.set_mode(self._kws.MODE_FULL, list(to_add))
                logger.info("KiteTicker subscribed %d new token(s)", len(to_add))
        except Exception as exc:
            logger.warning("Failed to update KiteTicker subscriptions: %s", exc)

        self._token_to_symbol = dict(token_to_symbol)

    def symbol_for_token(self, token: int) -> Optional[str]:
        return self._token_to_symbol.get(token)


# Singleton – one ticker connection per process.
kite_ticker = KiteTickerService()


# ── Background task ───────────────────────────────────────────────────────────

async def ticker_broadcaster(get_watchlist_symbols, get_db_session, manager) -> None:
    """Background task: stream ticks from KiteTicker → WebSocket clients.

    When Zerodha is configured and connected it starts the KiteTicker and
    broadcasts each tick as a ``price_update`` message.  When Zerodha is not
    configured it does nothing (the HTTP-poll broadcaster in
    realtime_service.py already provides price updates in that case).
    """
    tick_queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    last_setup_check: float = 0.0

    logger.info("Ticker broadcaster started")

    while True:
        try:
            now_ts = time.monotonic()

            # Periodically check broker config and (re-)start the ticker if needed.
            if now_ts - last_setup_check >= SETUP_CHECK_INTERVAL:
                last_setup_check = now_ts
                await _maybe_start_or_update_ticker(
                    get_watchlist_symbols, get_db_session, tick_queue, loop
                )

            if kite_ticker.running:
                # Drain one tick from the queue; forward to WebSocket clients.
                try:
                    tick = await asyncio.wait_for(
                        tick_queue.get(), timeout=TICK_QUEUE_TIMEOUT
                    )
                    await _broadcast_tick(tick, manager)
                except asyncio.TimeoutError:
                    pass
            else:
                # Ticker not running; sleep briefly and re-check on next iteration.
                await asyncio.sleep(5)

        except asyncio.CancelledError:
            kite_ticker.stop()
            logger.info("Ticker broadcaster cancelled")
            break
        except Exception as exc:
            logger.warning("Ticker broadcaster error: %s", exc)
            await asyncio.sleep(5)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _maybe_start_or_update_ticker(
    get_watchlist_symbols,
    get_db_session,
    tick_queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Check broker settings; start or update the KiteTicker accordingly."""
    try:
        from sqlalchemy import select
        from app.models.db_models import BrokerSettings

        async with get_db_session() as db:
            result = await db.execute(
                select(BrokerSettings).where(BrokerSettings.id == 1)
            )
            cfg = result.scalar_one_or_none()

        # Only run KiteTicker for Zerodha with a valid, connected session.
        if (
            not cfg
            or cfg.broker_name != "zerodha"
            or not cfg.api_key
            or not cfg.access_token
            or not cfg.connected
        ):
            if kite_ticker.running:
                kite_ticker.stop()
            return

        # Resolve instrument tokens for watchlist symbols.
        symbols = await get_watchlist_symbols()
        if not symbols:
            if kite_ticker.running:
                kite_ticker.stop()
            return

        token_to_symbol = await _resolve_tokens(
            cfg.api_key, cfg.access_token, symbols
        )
        if not token_to_symbol:
            logger.debug("No instrument tokens resolved for watchlist symbols")
            return

        if kite_ticker.running:
            kite_ticker.update_subscriptions(token_to_symbol)
        else:
            kite_ticker.start(
                cfg.api_key,
                cfg.access_token,
                token_to_symbol,
                loop,
                tick_queue,
            )

    except Exception as exc:
        logger.warning("Ticker setup error: %s", exc)


async def _resolve_tokens(
    api_key: str,
    access_token: str,
    symbols: list,
) -> Dict[int, str]:
    """Return a mapping of {instrument_token: symbol} for each symbol."""
    from app.services.broker_service import _kite_instrument

    loop = asyncio.get_event_loop()
    token_to_symbol: Dict[int, str] = {}

    for symbol in symbols:
        try:
            token = await loop.run_in_executor(
                None, _kite_instrument, api_key, access_token, symbol, "NSE"
            )
            if token:
                token_to_symbol[token] = symbol
        except Exception as exc:
            logger.debug("Could not resolve token for %s: %s", symbol, exc)

    return token_to_symbol


async def _broadcast_tick(tick: dict, manager) -> None:
    """Convert a raw KiteTicker tick dict to a ``price_update`` message."""
    token: int = tick.get("instrument_token", 0)
    symbol: Optional[str] = kite_ticker.symbol_for_token(token)
    if not symbol:
        return

    ohlc: dict = tick.get("ohlc") or {}
    last_price: float = tick.get("last_price") or 0.0
    prev_close: float = ohlc.get("close") or 0.0
    change: float = round(last_price - prev_close, 2) if prev_close else 0.0
    change_pct: float = round(change / prev_close * 100, 2) if prev_close else 0.0

    await manager.broadcast(
        {
            "type": "price_update",
            "source": "kiteticker",
            "data": {
                symbol: {
                    "symbol": symbol,
                    "exchange": "NSE",
                    "price": last_price,
                    "open": ohlc.get("open") or 0.0,
                    "high": ohlc.get("high") or 0.0,
                    "low": ohlc.get("low") or 0.0,
                    "prev_close": prev_close,
                    "change": change,
                    "change_pct": change_pct,
                    "volume": tick.get("volume_traded") or 0,
                    "timestamp": _now(),
                }
            },
            "timestamp": _now(),
        }
    )
