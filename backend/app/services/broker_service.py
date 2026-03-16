"""OpenAlgo broker service – thin wrapper around the openalgo Python SDK.

When the user has configured an OpenAlgo host + API key (via /broker/settings),
this service provides:
  - Live stock quotes from the connected broker
  - Historical OHLCV data from the connected broker
  - Real order execution (BUY/SELL) via the broker

Without credentials the service returns None / empty, allowing callers to fall
back to the paper-trading engine and NSE India API.
"""
from __future__ import annotations

import logging
from typing import Optional, List, Any, Dict

from app.models.schemas import OHLCBar, QuoteResponse

logger = logging.getLogger(__name__)


def _get_client(host: str, api_key: str) -> Optional[Any]:
    """Build an openalgo API client; returns None if the SDK is unavailable."""
    try:
        from openalgo import api as OpenAlgoAPI  # type: ignore
        return OpenAlgoAPI(api_key=api_key, host=host)
    except ImportError:
        logger.warning("openalgo SDK not installed – broker integration disabled")
        return None
    except Exception as exc:
        logger.error("Failed to create OpenAlgo client: %s", exc)
        return None


# ── Live quote ────────────────────────────────────────────────────────────────

def get_quote_via_broker(
    symbol: str,
    exchange: str,
    host: str,
    api_key: str,
) -> Optional[QuoteResponse]:
    """Fetch a live quote via OpenAlgo (wraps the broker's real-time feed)."""
    client = _get_client(host, api_key)
    if client is None:
        return None
    try:
        result = client.quotes(symbol=symbol.upper(), exchange=exchange.upper())
        if not isinstance(result, dict) or result.get("status") != "success":
            return None
        data = result.get("data", {})
        if not data:
            return None

        ltp = float(data.get("ltp") or data.get("last_price") or 0)
        prev_close = float(data.get("prev_close") or data.get("close") or 0)
        open_ = float(data.get("open") or prev_close)
        high = float(data.get("high") or ltp)
        low = float(data.get("low") or ltp)
        volume = int(data.get("volume") or data.get("tot_vol") or 0)
        change = ltp - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        return QuoteResponse(
            symbol=symbol.upper(),
            exchange=exchange.upper(),
            name=data.get("company", symbol.upper()),
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
        logger.warning("OpenAlgo quote fetch failed for %s: %s", symbol, exc)
        return None


# ── Historical data ───────────────────────────────────────────────────────────

def get_historical_via_broker(
    symbol: str,
    exchange: str,
    start_date: str,
    end_date: str,
    interval: str,
    host: str,
    api_key: str,
) -> List[OHLCBar]:
    """Fetch OHLCV bars via OpenAlgo (wraps the broker's historical data API)."""
    client = _get_client(host, api_key)
    if client is None:
        return []
    try:
        result = client.history(
            symbol=symbol.upper(),
            exchange=exchange.upper(),
            start_date=start_date,
            end_date=end_date,
            interval=interval,
        )
        if not isinstance(result, dict) or result.get("status") != "success":
            return []
        rows = result.get("data", [])
        bars: List[OHLCBar] = []
        for row in rows:
            import datetime
            ts_raw = row.get("time") or row.get("date") or row.get("timestamp") or ""
            try:
                if isinstance(ts_raw, str):
                    # Accept YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS and similar ISO formats
                    ts = datetime.datetime.fromisoformat(ts_raw.replace("T", " ").split(" ")[0])
                elif isinstance(ts_raw, (int, float)):
                    ts = datetime.datetime.fromtimestamp(ts_raw)
                else:
                    continue
            except Exception:
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
        logger.warning("OpenAlgo historical fetch failed for %s: %s", symbol, exc)
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
    host: str,
    api_key: str,
) -> Dict[str, Any]:
    """Place a real order via OpenAlgo to the connected broker.

    Returns a dict with at minimum {"status": "success"|"error", ...}.
    """
    client = _get_client(host, api_key)
    if client is None:
        return {"status": "error", "message": "OpenAlgo SDK not available"}
    try:
        kwargs: Dict[str, Any] = {
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
            "action": action.upper(),
            "quantity": str(quantity),
            "product": product.upper(),
            "pricetype": price_type.upper(),
        }
        if price and price_type.upper() in ("LIMIT", "SL"):
            kwargs["price"] = str(price)
        if trigger_price and price_type.upper() in ("SL", "SL-M"):
            kwargs["trigger_price"] = str(trigger_price)
        if strategy_tag:
            kwargs["strategy"] = strategy_tag

        result = client.placeorder(**kwargs)
        return result if isinstance(result, dict) else {"status": "success", "data": result}
    except Exception as exc:
        logger.error("OpenAlgo order placement failed: %s", exc)
        return {"status": "error", "message": str(exc)}


# ── Broker account info ───────────────────────────────────────────────────────

def get_broker_funds(host: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Return available funds/margin from the broker account."""
    client = _get_client(host, api_key)
    if client is None:
        return None
    try:
        result = client.funds()
        return result if isinstance(result, dict) else None
    except Exception as exc:
        logger.warning("OpenAlgo funds fetch failed: %s", exc)
        return None


def get_broker_positions(host: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Return current positions from the broker."""
    client = _get_client(host, api_key)
    if client is None:
        return None
    try:
        result = client.positionbook()
        return result if isinstance(result, dict) else None
    except Exception as exc:
        logger.warning("OpenAlgo positions fetch failed: %s", exc)
        return None


def get_broker_orders(host: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Return order book from the broker."""
    client = _get_client(host, api_key)
    if client is None:
        return None
    try:
        result = client.orderbook()
        return result if isinstance(result, dict) else None
    except Exception as exc:
        logger.warning("OpenAlgo orderbook fetch failed: %s", exc)
        return None


def test_broker_connection(host: str, api_key: str) -> bool:
    """Return True if the OpenAlgo server is reachable with the given credentials."""
    client = _get_client(host, api_key)
    if client is None:
        return False
    try:
        result = client.funds()
        return isinstance(result, dict) and result.get("status") == "success"
    except Exception:
        return False
