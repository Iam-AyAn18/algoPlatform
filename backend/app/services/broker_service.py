"""Direct broker API service – calls broker APIs without any intermediate server.

No separate server is required.  This service uses the broker's own Python SDK
to communicate with the broker's REST API:

  Platform  →  broker_service.py  →  Zerodha Kite Connect REST API
                                  →  Groww REST API

Supported brokers
─────────────────
  zerodha   Zerodha Kite Connect (kiteconnect library, https://developers.kite.trade)
  groww     Groww Developer API (https://groww.in/open-api) – OAuth2 access token
  paper     No real broker; paper trading only (default)

How Zerodha authentication works
─────────────────────────────────
  1. Get an API key + API secret from https://developers.kite.trade (one-time).
  2. Each trading day: visit the login URL returned by /broker/login-url,
     log in, and the platform will exchange the request_token for an access_token.
  3. The access_token is stored in BrokerSettings and is valid until midnight IST.

How Groww authentication works
───────────────────────────────
  1. Register your app at https://groww.in/open-api to get a client_id (api_key)
     and client_secret (api_secret).
  2. Each session: visit the login URL returned by /broker/login-url,
     authorise the app, and the platform will exchange the auth_code for an
     access_token using POST /broker/exchange-token.
  3. The access_token is stored in BrokerSettings.
"""
from __future__ import annotations

import logging
from typing import Optional, List, Any, Dict

from app.models.schemas import OHLCBar, QuoteResponse

logger = logging.getLogger(__name__)

# ── Groww API constants ───────────────────────────────────────────────────────

_GROWW_BASE = "https://groww.in"
_GROWW_API = "https://api.groww.in"


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
        logger.warning("kiteconnect not installed – Zerodha integration disabled")
        return None
    except Exception as exc:
        logger.error("Failed to create Kite client: %s", exc)
        return None


def _kite_instrument(exchange: str, symbol: str) -> str:
    """Format instrument string for Kite API e.g. 'NSE:RELIANCE'."""
    return f"{exchange.upper()}:{symbol.upper()}"


# ── Groww helpers ─────────────────────────────────────────────────────────────

def _groww_headers(access_token: str) -> Dict[str, str]:
    """Build authorization headers for Groww API calls."""
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# ── Live quote ────────────────────────────────────────────────────────────────

def get_quote_via_broker(
    symbol: str,
    exchange: str,
    broker_name: str,
    api_key: str,
    access_token: str,
) -> Optional[QuoteResponse]:
    """Fetch a live quote directly from the broker API (no intermediary server)."""
    if broker_name == "zerodha":
        return _get_zerodha_quote(symbol, exchange, api_key, access_token)
    if broker_name == "groww":
        return _get_groww_quote(symbol, exchange, access_token)
    return None


def _get_zerodha_quote(
    symbol: str,
    exchange: str,
    api_key: str,
    access_token: str,
) -> Optional[QuoteResponse]:
    """Fetch a live quote directly from Zerodha Kite."""
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


def _get_groww_quote(
    symbol: str,
    exchange: str,
    access_token: str,
) -> Optional[QuoteResponse]:
    """Fetch a live quote from the Groww API."""
    if not access_token:
        return None
    try:
        import requests
        # Groww live market data endpoint
        resp = requests.get(
            f"{_GROWW_API}/v1/live-data/quote",
            params={"exchange": exchange.upper(), "tradingsymbol": symbol.upper()},
            headers=_groww_headers(access_token),
            timeout=10,
        )
        resp.raise_for_status()
        d = resp.json()
        # Groww quote response fields
        ltp = float(d.get("ltp") or d.get("lastPrice") or 0)
        prev_close = float(d.get("previousClose") or d.get("prevClose") or 0)
        open_ = float(d.get("open") or prev_close)
        high = float(d.get("dayHigh") or d.get("high") or ltp)
        low = float(d.get("dayLow") or d.get("low") or ltp)
        volume = int(d.get("totalTradedVolume") or d.get("volume") or 0)
        change = ltp - prev_close
        change_pct = float(d.get("netChange") or ((change / prev_close * 100) if prev_close else 0.0))
        return QuoteResponse(
            symbol=symbol.upper(),
            exchange=exchange.upper(),
            name=d.get("companyName", symbol.upper()),
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
        logger.warning("Groww quote fetch failed for %s: %s", symbol, exc)
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

    Groww does not provide a public historical data API; historical data for
    Groww accounts is sourced from the NSE India public API (handled by the
    caller's fallback chain in market_data.py / backtest_service.py).
    """
    if broker_name == "zerodha":
        return _get_zerodha_historical(symbol, exchange, start_date, end_date, interval, api_key, access_token)
    return []


def _get_zerodha_historical(
    symbol: str,
    exchange: str,
    start_date: str,
    end_date: str,
    interval: str,
    api_key: str,
    access_token: str,
) -> List[OHLCBar]:
    """Fetch OHLCV bars directly from Zerodha Kite.

    Requires looking up the instrument token from Kite's instruments dump.
    Falls back to an empty list when the lookup fails (NSE API is the fallback).
    """
    kite = _get_kite(api_key, access_token)
    if kite is None:
        return []
    try:
        import datetime

        # Look up instrument token for this symbol
        instruments = kite.instruments(exchange.upper())
        token = None
        for inst in instruments:
            if (
                inst.get("tradingsymbol", "").upper() == symbol.upper()
                and inst.get("segment", "").upper() == exchange.upper()
            ):
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
    if broker_name == "zerodha":
        return _place_zerodha_order(
            symbol, exchange, action, quantity, product, price_type,
            price, trigger_price, strategy_tag, api_key, access_token,
        )
    if broker_name == "groww":
        return _place_groww_order(
            symbol, exchange, action, quantity, product, price_type,
            price, trigger_price, strategy_tag, access_token,
        )
    return {"status": "error", "message": f"Broker '{broker_name}' not supported for real orders"}


def _place_zerodha_order(
    symbol: str,
    exchange: str,
    action: str,
    quantity: int,
    product: str,
    price_type: str,
    price: float,
    trigger_price: float,
    strategy_tag: str,
    api_key: str,
    access_token: str,
) -> Dict[str, Any]:
    kite = _get_kite(api_key, access_token)
    if kite is None:
        return {"status": "error", "message": "Kite client unavailable – check API key and access token"}

    try:
        from kiteconnect import KiteConnect  # type: ignore

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

        transaction_type = (
            KiteConnect.TRANSACTION_TYPE_BUY if action.upper() == "BUY"
            else KiteConnect.TRANSACTION_TYPE_SELL
        )

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


def _place_groww_order(
    symbol: str,
    exchange: str,
    action: str,
    quantity: int,
    product: str,
    price_type: str,
    price: float,
    trigger_price: float,
    strategy_tag: str,
    access_token: str,
) -> Dict[str, Any]:
    """Place an order via the Groww trading API."""
    if not access_token:
        return {"status": "error", "message": "Groww access token not configured"}
    try:
        import requests

        # Map order type to Groww's expected values
        order_type_map = {
            "MARKET": "MARKET",
            "LIMIT": "LIMIT",
            "SL": "SL",
            "SL-M": "SL_M",
        }
        groww_order_type = order_type_map.get(price_type.upper(), "MARKET")

        # Map product type to Groww's expected values
        product_map = {
            "CNC": "CNC",
            "MIS": "INTRADAY",
            "NRML": "MARGIN",
        }
        groww_product = product_map.get(product.upper(), "CNC")

        payload: Dict[str, Any] = {
            "exchange": exchange.upper(),
            "tradingSymbol": symbol.upper(),
            "transactionType": action.upper(),
            "quantity": quantity,
            "product": groww_product,
            "orderType": groww_order_type,
        }
        if price and groww_order_type in ("LIMIT", "SL"):
            payload["price"] = price
        if trigger_price and groww_order_type in ("SL", "SL_M"):
            payload["triggerPrice"] = trigger_price

        resp = requests.post(
            f"{_GROWW_API}/v1/order/",
            json=payload,
            headers=_groww_headers(access_token),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        order_id = data.get("orderId") or data.get("order_id") or data.get("data", {}).get("orderId")
        return {"status": "success", "data": {"orderid": order_id}}
    except Exception as exc:
        logger.error("Groww order placement failed: %s", exc)
        return {"status": "error", "message": str(exc)}


# ── Broker account info ───────────────────────────────────────────────────────

def get_broker_funds(broker_name: str, api_key: str, access_token: str) -> Optional[Dict[str, Any]]:
    """Return available funds/margin from the broker account."""
    if broker_name == "zerodha":
        return _get_zerodha_funds(api_key, access_token)
    if broker_name == "groww":
        return _get_groww_funds(access_token)
    return None


def _get_zerodha_funds(api_key: str, access_token: str) -> Optional[Dict[str, Any]]:
    kite = _get_kite(api_key, access_token)
    if kite is None:
        return None
    try:
        margins = kite.margins()
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


def _get_groww_funds(access_token: str) -> Optional[Dict[str, Any]]:
    if not access_token:
        return None
    try:
        import requests
        resp = requests.get(
            f"{_GROWW_API}/v1/user/fund-details",
            headers=_groww_headers(access_token),
            timeout=10,
        )
        resp.raise_for_status()
        d = resp.json()
        # Normalize Groww's fund response to the common format
        equity_data = d.get("equityFundDetails") or d.get("data") or d
        available_cash = equity_data.get("availableBalance") or equity_data.get("availablecash") or 0
        return {
            "status": "success",
            "data": {
                "availablecash": str(available_cash),
                "utiliseddebits": str(equity_data.get("usedMargin") or 0),
                "collateral": str(equity_data.get("collateral") or 0),
                "m2munrealized": str(equity_data.get("unrealisedPnl") or 0),
                "m2mrealized": str(equity_data.get("realisedPnl") or 0),
            },
        }
    except Exception as exc:
        logger.warning("Groww funds fetch failed: %s", exc)
        return None


def get_broker_positions(broker_name: str, api_key: str, access_token: str) -> Optional[Dict[str, Any]]:
    """Return current positions from the broker."""
    if broker_name == "zerodha":
        return _get_zerodha_positions(api_key, access_token)
    if broker_name == "groww":
        return _get_groww_positions(access_token)
    return None


def _get_zerodha_positions(api_key: str, access_token: str) -> Optional[Dict[str, Any]]:
    kite = _get_kite(api_key, access_token)
    if kite is None:
        return None
    try:
        return {"status": "success", "data": kite.positions()}
    except Exception as exc:
        logger.warning("Kite positions fetch failed: %s", exc)
        return None


def _get_groww_positions(access_token: str) -> Optional[Dict[str, Any]]:
    if not access_token:
        return None
    try:
        import requests
        resp = requests.get(
            f"{_GROWW_API}/v1/portfolio/holdings",
            headers=_groww_headers(access_token),
            timeout=10,
        )
        resp.raise_for_status()
        return {"status": "success", "data": resp.json()}
    except Exception as exc:
        logger.warning("Groww positions fetch failed: %s", exc)
        return None


def get_broker_orders(broker_name: str, api_key: str, access_token: str) -> Optional[Dict[str, Any]]:
    """Return order book from the broker."""
    if broker_name == "zerodha":
        return _get_zerodha_orders(api_key, access_token)
    if broker_name == "groww":
        return _get_groww_orders(access_token)
    return None


def _get_zerodha_orders(api_key: str, access_token: str) -> Optional[Dict[str, Any]]:
    kite = _get_kite(api_key, access_token)
    if kite is None:
        return None
    try:
        return {"status": "success", "data": kite.orders()}
    except Exception as exc:
        logger.warning("Kite orders fetch failed: %s", exc)
        return None


def _get_groww_orders(access_token: str) -> Optional[Dict[str, Any]]:
    if not access_token:
        return None
    try:
        import requests
        resp = requests.get(
            f"{_GROWW_API}/v1/order/list",
            headers=_groww_headers(access_token),
            timeout=10,
        )
        resp.raise_for_status()
        return {"status": "success", "data": resp.json()}
    except Exception as exc:
        logger.warning("Groww orders fetch failed: %s", exc)
        return None


def test_broker_connection(broker_name: str, api_key: str, access_token: str) -> bool:
    """Return True if the broker credentials are valid and the API is reachable."""
    if broker_name == "zerodha":
        kite = _get_kite(api_key, access_token)
        if kite is None:
            return False
        try:
            kite.profile()
            return True
        except Exception:
            return False
    if broker_name == "groww":
        if not access_token:
            return False
        try:
            import requests
            resp = requests.get(
                f"{_GROWW_API}/v1/user/profile",
                headers=_groww_headers(access_token),
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False
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


# ── Groww OAuth helpers ───────────────────────────────────────────────────────

def get_groww_login_url(client_id: str, redirect_uri: str = "") -> str:
    """Return the Groww OAuth authorisation URL.

    The user must visit this URL, authorise the app, and will be redirected
    to the redirect_uri with an ``?auth_code=...`` (or ``?code=...``) parameter.
    They should then call POST /broker/exchange-token with that code.
    """
    if not client_id:
        return ""
    # Use a default redirect URI pointing to the platform's callback if none provided
    if not redirect_uri:
        redirect_uri = "http://localhost:8000/broker/groww-callback"
    import urllib.parse
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        # "trading" is the standard scope for order placement and account access.
        # Groww may extend this to granular scopes in future API versions.
        "scope": "trading",
    })
    return f"{_GROWW_BASE}/oauth2/authorize?{params}"


def exchange_groww_auth_code(client_id: str, client_secret: str, auth_code: str) -> Optional[str]:
    """Exchange a Groww OAuth auth_code for an access_token.

    Returns the access_token string on success, None on failure.
    """
    if not client_id or not client_secret or not auth_code:
        return None
    try:
        import requests
        resp = requests.post(
            f"{_GROWW_API}/oauth2/token",
            json={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": auth_code,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("access_token")
    except Exception as exc:
        logger.error("Groww token exchange failed: %s", exc)
        return None
