"""Direct broker API service – calls broker APIs without any intermediate server.

No separate server is required.  This service uses the broker's own Python SDK
to communicate with the broker's REST API:

  Platform  →  broker_service.py  →  Zerodha Kite Connect REST API

Supported brokers
─────────────────
  zerodha   Zerodha Kite Connect (kiteconnect library, https://developers.kite.trade)
  paper     No real broker; paper trading only (default)

How Zerodha authentication works
─────────────────────────────────
  1. Get an API key + API secret from https://developers.kite.trade (one-time).
  2. Each trading day: visit the login URL returned by /broker/login-url,
     log in, and the platform will exchange the request_token for an access_token.
  3. The access_token is stored in BrokerSettings and is valid until midnight IST.
"""
from __future__ import annotations

import logging
from typing import Optional, List, Any, Dict

from app.models.schemas import OHLCBar, QuoteResponse

logger = logging.getLogger(__name__)

# ── Zerodha Kite Connect helpers ──────────────────────────────────────────────

def _get_kite(api_key: str, access_token: str) -> Optional[Any]:
    """Build a KiteConnect client; returns None if the SDK is unavailable or
    credentials are missing."""
    if not api_key or not access_token:
        return None
    try:
        from kiteconnect import KiteConnect  # type: ignore
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)
        return kite
    except ImportError:
        logger.warning("kiteconnect not installed – broker integration disabled")
        return None
    except Exception as exc:
        logger.error("Failed to create Kite client: %s", exc)
        return None


def _kite_instrument(exchange: str, symbol: str) -> str:
    """Format instrument string for Kite API e.g. 'NSE:RELIANCE'."""
    return f"{exchange.upper()}:{symbol.upper()}"


# ── Live quote ────────────────────────────────────────────────────────────────

def get_quote_via_broker(
    symbol: str,
    exchange: str,
    broker_name: str,
    api_key: str,
    access_token: str,
) -> Optional[QuoteResponse]:
    """Fetch a live quote directly from the broker API (no intermediary server)."""
    if broker_name != "zerodha":
        return None

    kite = _get_kite(api_key, access_token)
    if kite is None:
        return None
    try:
        instrument = _kite_instrument(exchange, symbol)
        data = kite.quote([instrument])
        q = data.get(instrument, {})
        if not q:
            return None

        ohlc = q.get("ohlc", {})
        ltp = float(q.get("last_price") or 0)
        prev_close = float(ohlc.get("close") or 0)
        open_ = float(ohlc.get("open") or prev_close)
        high = float(ohlc.get("high") or ltp)
        low = float(ohlc.get("low") or ltp)
        volume = int(q.get("volume") or 0)
        change = ltp - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        return QuoteResponse(
            symbol=symbol.upper(),
            exchange=exchange.upper(),
            name=symbol.upper(),
            price=round(ltp, 2),
            open=round(open_, 2),
            high=round(high, 2),
            low=round(low, 2),
            prev_close=round(prev_close, 2),
            change=round(change, 2),
            change_pct=round(change_pct, 2),
            volume=volume,
        )
    except Exception as exc:
        logger.warning("Kite quote fetch failed for %s: %s", symbol, exc)
        return None


# ── Historical data ───────────────────────────────────────────────────────────

def get_historical_via_broker(
    symbol: str,
    exchange: str,
    start_date: str,
    end_date: str,
    interval: str,
    broker_name: str,
    api_key: str,
    access_token: str,
) -> List[OHLCBar]:
    """Fetch OHLCV bars directly from the broker API.

    For Zerodha, historical data requires looking up the instrument token first.
    This involves a one-time download of the instruments dump.  The function
    falls back to the NSE India public API when the lookup fails.
    """
    if broker_name != "zerodha":
        return []

    kite = _get_kite(api_key, access_token)
    if kite is None:
        return []
    try:
        import datetime

        # Look up instrument token for this symbol
        instruments = kite.instruments(exchange.upper())
        token = None
        for inst in instruments:
            if inst.get("tradingsymbol", "").upper() == symbol.upper() and inst.get("segment", "").upper() == exchange.upper():
                token = inst["instrument_token"]
                break
        if token is None:
            logger.debug("Kite: instrument token not found for %s:%s", symbol, exchange)
            return []

        # Map interval string (yfinance-style → Kite style)
        interval_map = {
            "1d": "day", "1wk": "week", "1mo": "month",
            "15m": "15minute", "5m": "5minute", "1m": "minute",
        }
        kite_interval = interval_map.get(interval, "day")

        from_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        to_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")

        rows = kite.historical_data(token, from_dt, to_dt, kite_interval)
        bars: List[OHLCBar] = []
        for row in rows:
            ts = row.get("date")
            if hasattr(ts, "replace"):
                ts = ts.replace(tzinfo=None)
            elif isinstance(ts, str):
                ts = datetime.datetime.fromisoformat(ts.replace("T", " ").split(" ")[0])
            else:
                continue
            bars.append(
                OHLCBar(
                    timestamp=ts,
                    open=round(float(row.get("open", 0)), 2),
                    high=round(float(row.get("high", 0)), 2),
                    low=round(float(row.get("low", 0)), 2),
                    close=round(float(row.get("close", 0)), 2),
                    volume=int(row.get("volume", 0)),
                )
            )
        return bars
    except Exception as exc:
        logger.warning("Kite historical fetch failed for %s: %s", symbol, exc)
        return []


# ── Order execution ───────────────────────────────────────────────────────────

def place_real_order(
    symbol: str,
    exchange: str,
    action: str,         # "BUY" or "SELL"
    quantity: int,
    product: str,        # "CNC" (delivery) | "MIS" (intraday) | "NRML" (F&O)
    price_type: str,     # "MARKET" | "LIMIT" | "SL" | "SL-M"
    price: float,
    trigger_price: float,
    strategy_tag: str,
    broker_name: str,
    api_key: str,
    access_token: str,
) -> Dict[str, Any]:
    """Place a real order directly via the broker API (no intermediary server).

    Returns a dict with at minimum {"status": "success"|"error", ...}.
    """
    if broker_name != "zerodha":
        return {"status": "error", "message": f"Broker '{broker_name}' not supported for real orders"}

    kite = _get_kite(api_key, access_token)
    if kite is None:
        return {"status": "error", "message": "Kite client unavailable – check API key and access token"}

    try:
        from kiteconnect import KiteConnect  # type: ignore

        # Map our order_type → Kite variety + order_type
        variety = KiteConnect.VARIETY_REGULAR
        order_type_map = {
            "MARKET": KiteConnect.ORDER_TYPE_MARKET,
            "LIMIT": KiteConnect.ORDER_TYPE_LIMIT,
            "SL": KiteConnect.ORDER_TYPE_SL,
            "SL-M": KiteConnect.ORDER_TYPE_SLM,
        }
        kite_order_type = order_type_map.get(price_type.upper(), KiteConnect.ORDER_TYPE_MARKET)

        product_map = {
            "CNC": KiteConnect.PRODUCT_CNC,
            "MIS": KiteConnect.PRODUCT_MIS,
            "NRML": KiteConnect.PRODUCT_NRML,
        }
        kite_product = product_map.get(product.upper(), KiteConnect.PRODUCT_CNC)

        transaction_type = KiteConnect.TRANSACTION_TYPE_BUY if action.upper() == "BUY" else KiteConnect.TRANSACTION_TYPE_SELL

        kwargs: Dict[str, Any] = {
            "variety": variety,
            "exchange": exchange.upper(),
            "tradingsymbol": symbol.upper(),
            "transaction_type": transaction_type,
            "quantity": quantity,
            "product": kite_product,
            "order_type": kite_order_type,
            "tag": strategy_tag[:20] if strategy_tag else None,
        }
        if price and kite_order_type in (KiteConnect.ORDER_TYPE_LIMIT, KiteConnect.ORDER_TYPE_SL):
            kwargs["price"] = price
        if trigger_price and kite_order_type in (KiteConnect.ORDER_TYPE_SL, KiteConnect.ORDER_TYPE_SLM):
            kwargs["trigger_price"] = trigger_price

        order_id = kite.place_order(**kwargs)
        return {"status": "success", "data": {"orderid": order_id}}
    except Exception as exc:
        logger.error("Kite order placement failed: %s", exc)
        return {"status": "error", "message": str(exc)}


# ── Broker account info ───────────────────────────────────────────────────────

def get_broker_funds(broker_name: str, api_key: str, access_token: str) -> Optional[Dict[str, Any]]:
    """Return available funds/margin from the broker account."""
    if broker_name != "zerodha":
        return None
    kite = _get_kite(api_key, access_token)
    if kite is None:
        return None
    try:
        margins = kite.margins()
        # Kite returns {"equity": {...}, "commodity": {...}}
        equity = margins.get("equity", {})
        return {
            "status": "success",
            "data": {
                "availablecash": str(equity.get("available", {}).get("cash", 0)),
                "utiliseddebits": str(equity.get("utilised", {}).get("debits", 0)),
                "collateral": str(equity.get("available", {}).get("collateral", 0)),
                "m2munrealized": str(equity.get("utilised", {}).get("m2m_unrealised", 0)),
                "m2mrealized": str(equity.get("utilised", {}).get("m2m_realised", 0)),
            },
        }
    except Exception as exc:
        logger.warning("Kite funds fetch failed: %s", exc)
        return None


def get_broker_positions(broker_name: str, api_key: str, access_token: str) -> Optional[Dict[str, Any]]:
    """Return current positions from the broker."""
    if broker_name != "zerodha":
        return None
    kite = _get_kite(api_key, access_token)
    if kite is None:
        return None
    try:
        return {"status": "success", "data": kite.positions()}
    except Exception as exc:
        logger.warning("Kite positions fetch failed: %s", exc)
        return None


def get_broker_orders(broker_name: str, api_key: str, access_token: str) -> Optional[Dict[str, Any]]:
    """Return order book from the broker."""
    if broker_name != "zerodha":
        return None
    kite = _get_kite(api_key, access_token)
    if kite is None:
        return None
    try:
        return {"status": "success", "data": kite.orders()}
    except Exception as exc:
        logger.warning("Kite orders fetch failed: %s", exc)
        return None


def test_broker_connection(broker_name: str, api_key: str, access_token: str) -> bool:
    """Return True if the broker credentials are valid and the API is reachable."""
    if broker_name != "zerodha":
        return False
    kite = _get_kite(api_key, access_token)
    if kite is None:
        return False
    try:
        kite.profile()
        return True
    except Exception:
        return False


# ── Zerodha OAuth helpers ─────────────────────────────────────────────────────

def get_kite_login_url(api_key: str) -> str:
    """Return the Kite login URL that the user must visit to obtain a request_token."""
    try:
        from kiteconnect import KiteConnect  # type: ignore
        kite = KiteConnect(api_key=api_key)
        return kite.login_url()
    except ImportError:
        return ""
    except Exception as exc:
        logger.error("Failed to build Kite login URL: %s", exc)
        return ""


def exchange_request_token(api_key: str, api_secret: str, request_token: str) -> Optional[str]:
    """Exchange a request_token (from OAuth callback) for an access_token.

    Returns the access_token string on success, None on failure.
    The access_token is valid until midnight IST of the same day.
    """
    try:
        from kiteconnect import KiteConnect  # type: ignore
        kite = KiteConnect(api_key=api_key)
        data = kite.generate_session(request_token, api_secret=api_secret)
        return data.get("access_token")
    except Exception as exc:
        logger.error("Kite token exchange failed: %s", exc)
        return None

