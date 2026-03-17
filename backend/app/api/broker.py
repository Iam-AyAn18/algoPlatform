"""Broker settings API – configure direct broker API credentials.

No intermediate server required.  The platform calls the broker's REST API
directly using the Zerodha Kite Connect SDK.

Authentication flow (Zerodha)
──────────────────────────────
  1. Save your API key + API secret via PUT /broker/settings
  2. Call GET /broker/login-url → visit the returned URL in your browser
  3. After logging in you are redirected to your callback URL with a
     ?request_token=... parameter.  Paste that token into
     POST /broker/exchange-token  to get a daily access_token.
  4. The access_token is stored automatically and is valid until midnight IST.
"""
from __future__ import annotations
import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db_models import BrokerSettings
from app.models.schemas import BrokerSettingsUpdate, BrokerSettingsResponse, BrokerFundsResponse

router = APIRouter(prefix="/broker", tags=["Broker"])


async def _get_or_create_settings(db: AsyncSession) -> BrokerSettings:
    result = await db.execute(select(BrokerSettings).where(BrokerSettings.id == 1))
    cfg = result.scalar_one_or_none()
    if cfg is None:
        cfg = BrokerSettings(id=1)
        db.add(cfg)
        await db.commit()
        await db.refresh(cfg)
    return cfg


def _mask_key(api_key: str) -> str:
    """Show only the last 4 characters of the API key."""
    if not api_key:
        return ""
    if len(api_key) <= 4:
        return "*" * len(api_key)
    return "*" * (len(api_key) - 4) + api_key[-4:]


def _cfg_to_response(cfg: BrokerSettings) -> BrokerSettingsResponse:
    return BrokerSettingsResponse(
        broker_name=cfg.broker_name,
        api_key_masked=_mask_key(cfg.api_key),
        api_secret_set=bool(cfg.api_secret),
        access_token_set=bool(cfg.access_token),
        user_id=cfg.user_id,
        trade_mode=cfg.trade_mode,
        default_product=cfg.default_product,
        connected=cfg.connected,
        updated_at=cfg.updated_at,
    )


@router.get("/settings", response_model=BrokerSettingsResponse)
async def get_broker_settings(db: AsyncSession = Depends(get_db)):
    """Return current broker connection settings (sensitive fields are masked)."""
    cfg = await _get_or_create_settings(db)
    return _cfg_to_response(cfg)


@router.put("/settings", response_model=BrokerSettingsResponse)
async def update_broker_settings(
    body: BrokerSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Save broker credentials.

    After saving, the endpoint tests the connection (using the access_token if
    present) and updates the ``connected`` flag.

    Empty strings for api_secret and access_token are **ignored** so existing
    values are preserved when you only want to change the trade_mode, for example.
    """
    valid_brokers = {"zerodha", "paper"}
    if body.broker_name not in valid_brokers:
        raise HTTPException(status_code=400, detail=f"broker_name must be one of {valid_brokers}")

    valid_modes = {"paper", "semi_auto", "auto"}
    if body.trade_mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"trade_mode must be one of {valid_modes}")

    valid_products = {"CNC", "MIS", "NRML"}
    if body.default_product.upper() not in valid_products:
        raise HTTPException(status_code=400, detail=f"default_product must be one of {valid_products}")

    cfg = await _get_or_create_settings(db)
    cfg.broker_name = body.broker_name
    if body.api_key:
        cfg.api_key = body.api_key
    if body.api_secret:
        cfg.api_secret = body.api_secret
    if body.access_token:
        cfg.access_token = body.access_token
    if body.user_id:
        cfg.user_id = body.user_id
    cfg.trade_mode = body.trade_mode
    cfg.default_product = body.default_product.upper()
    cfg.updated_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    # Test connection if we have the required credentials
    from app.services.broker_service import test_broker_connection
    cfg.connected = test_broker_connection(cfg.broker_name, cfg.api_key, cfg.access_token)

    # Push new credentials into the market_data module-level cache
    from app.services.market_data import set_broker_credentials
    set_broker_credentials(cfg.broker_name, cfg.api_key, cfg.access_token)

    await db.commit()
    await db.refresh(cfg)
    return _cfg_to_response(cfg)


@router.post("/test-connection")
async def test_connection(db: AsyncSession = Depends(get_db)):
    """Ping the broker API with the stored credentials and return connection status."""
    cfg = await _get_or_create_settings(db)
    if not cfg.api_key or not cfg.access_token:
        return {"connected": False, "message": "API key or access token not configured"}

    from app.services.broker_service import test_broker_connection
    connected = test_broker_connection(cfg.broker_name, cfg.api_key, cfg.access_token)
    cfg.connected = connected
    cfg.updated_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {
        "connected": connected,
        "broker": cfg.broker_name,
        "message": "Connection successful" if connected else "Connection failed – check API key and access token",
    }


# ── Zerodha Kite login flow ───────────────────────────────────────────────────

@router.get("/login-url")
async def get_login_url(db: AsyncSession = Depends(get_db)):
    """Return the Zerodha Kite login URL.

    The user must visit this URL in their browser, log in, and the page will
    redirect them to the callback URL with a ``?request_token=...`` parameter.
    They should then call POST /broker/exchange-token with that token.
    """
    cfg = await _get_or_create_settings(db)
    if cfg.broker_name != "zerodha":
        raise HTTPException(status_code=400, detail="Login URL is only available for the Zerodha broker")
    if not cfg.api_key:
        raise HTTPException(status_code=400, detail="API key not configured – save your Kite API key first")

    from app.services.broker_service import get_kite_login_url
    url = get_kite_login_url(cfg.api_key)
    if not url:
        raise HTTPException(status_code=503, detail="Failed to generate Kite login URL – is kiteconnect installed?")
    return {
        "login_url": url,
        "instructions": (
            "1. Visit the URL above in your browser and log in with your Zerodha credentials. "
            "2. After login you are redirected to your app's redirect URL with a request_token parameter. "
            "3. Copy the request_token value and call POST /broker/exchange-token with it."
        ),
    }


@router.post("/exchange-token")
async def exchange_token(
    request_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a Kite request_token for a daily access_token.

    The request_token comes from the ``?request_token=...`` query parameter
    after the Zerodha login redirect.  The access_token is stored automatically
    and is valid until midnight IST.
    """
    cfg = await _get_or_create_settings(db)
    if cfg.broker_name != "zerodha":
        raise HTTPException(status_code=400, detail="Token exchange is only available for the Zerodha broker")
    if not cfg.api_key or not cfg.api_secret:
        raise HTTPException(status_code=400, detail="API key and API secret must be configured first")

    from app.services.broker_service import exchange_request_token
    access_token = exchange_request_token(cfg.api_key, cfg.api_secret, request_token)
    if not access_token:
        raise HTTPException(
            status_code=400,
            detail="Token exchange failed – ensure the request_token is correct and not expired",
        )

    cfg.access_token = access_token
    cfg.connected = True
    cfg.updated_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    # Push into market_data module-level cache immediately
    from app.services.market_data import set_broker_credentials
    set_broker_credentials(cfg.broker_name, cfg.api_key, cfg.access_token)

    await db.commit()
    await db.refresh(cfg)
    return {
        "connected": True,
        "message": "Access token saved. Broker is now connected for today's session.",
    }


# ── Live broker account data ──────────────────────────────────────────────────

@router.get("/funds", response_model=BrokerFundsResponse)
async def get_funds(db: AsyncSession = Depends(get_db)):
    """Return live account funds/margin from the broker."""
    cfg = await _get_or_create_settings(db)
    if not cfg.connected:
        raise HTTPException(status_code=503, detail="Broker not connected – complete the login flow first")

    from app.services.broker_service import get_broker_funds
    result = get_broker_funds(cfg.broker_name, cfg.api_key, cfg.access_token)
    if result is None:
        raise HTTPException(status_code=502, detail="Failed to fetch funds from broker")
    return BrokerFundsResponse(
        status=result.get("status", "error"),
        data=result.get("data"),
        message=result.get("message"),
    )


@router.get("/positions")
async def get_broker_positions(db: AsyncSession = Depends(get_db)):
    """Return current positions from the broker account."""
    cfg = await _get_or_create_settings(db)
    if not cfg.connected:
        raise HTTPException(status_code=503, detail="Broker not connected")

    from app.services.broker_service import get_broker_positions
    result = get_broker_positions(cfg.broker_name, cfg.api_key, cfg.access_token)
    if result is None:
        raise HTTPException(status_code=502, detail="Failed to fetch positions from broker")
    return result


@router.get("/orders")
async def get_broker_orders(db: AsyncSession = Depends(get_db)):
    """Return order book from the broker account."""
    cfg = await _get_or_create_settings(db)
    if not cfg.connected:
        raise HTTPException(status_code=503, detail="Broker not connected")

    from app.services.broker_service import get_broker_orders
    result = get_broker_orders(cfg.broker_name, cfg.api_key, cfg.access_token)
    if result is None:
        raise HTTPException(status_code=502, detail="Failed to fetch orders from broker")
    return result

