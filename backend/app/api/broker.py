"""Broker settings API – configure OpenAlgo connection and trading mode."""
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


@router.get("/settings", response_model=BrokerSettingsResponse)
async def get_broker_settings(db: AsyncSession = Depends(get_db)):
    """Return current broker connection settings (API key is masked)."""
    cfg = await _get_or_create_settings(db)
    return BrokerSettingsResponse(
        host=cfg.host,
        api_key_masked=_mask_key(cfg.api_key),
        trade_mode=cfg.trade_mode,
        default_product=cfg.default_product,
        connected=cfg.connected,
        updated_at=cfg.updated_at,
    )


@router.put("/settings", response_model=BrokerSettingsResponse)
async def update_broker_settings(
    body: BrokerSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update broker connection settings.

    After saving, the endpoint immediately tests the connection to OpenAlgo
    and updates the ``connected`` flag accordingly.
    """
    valid_modes = {"paper", "semi_auto", "auto"}
    if body.trade_mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"trade_mode must be one of {valid_modes}")

    valid_products = {"CNC", "MIS", "NRML"}
    if body.default_product.upper() not in valid_products:
        raise HTTPException(status_code=400, detail=f"default_product must be one of {valid_products}")

    cfg = await _get_or_create_settings(db)
    cfg.host = body.host.rstrip("/")
    cfg.api_key = body.api_key
    cfg.trade_mode = body.trade_mode
    cfg.default_product = body.default_product.upper()
    cfg.updated_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    # Test connectivity
    from app.services.broker_service import test_broker_connection
    cfg.connected = test_broker_connection(cfg.host, cfg.api_key) if cfg.api_key else False

    # Also update the in-process settings so market_data picks it up immediately
    from app.core.config import settings
    settings.openalgo_host = cfg.host
    settings.openalgo_api_key = cfg.api_key

    await db.commit()
    await db.refresh(cfg)
    return BrokerSettingsResponse(
        host=cfg.host,
        api_key_masked=_mask_key(cfg.api_key),
        trade_mode=cfg.trade_mode,
        default_product=cfg.default_product,
        connected=cfg.connected,
        updated_at=cfg.updated_at,
    )


@router.post("/test-connection")
async def test_connection(db: AsyncSession = Depends(get_db)):
    """Ping the configured OpenAlgo server and return connection status."""
    cfg = await _get_or_create_settings(db)
    if not cfg.api_key:
        return {"connected": False, "message": "No API key configured"}

    from app.services.broker_service import test_broker_connection
    connected = test_broker_connection(cfg.host, cfg.api_key)
    cfg.connected = connected
    cfg.updated_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {
        "connected": connected,
        "host": cfg.host,
        "message": "Connection successful" if connected else "Connection failed – check host and API key",
    }


@router.get("/funds", response_model=BrokerFundsResponse)
async def get_funds(db: AsyncSession = Depends(get_db)):
    """Return live account funds/margin from the broker."""
    cfg = await _get_or_create_settings(db)
    if not cfg.api_key or not cfg.connected:
        raise HTTPException(status_code=503, detail="Broker not connected")

    from app.services.broker_service import get_broker_funds
    result = get_broker_funds(cfg.host, cfg.api_key)
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
    if not cfg.api_key or not cfg.connected:
        raise HTTPException(status_code=503, detail="Broker not connected")

    from app.services.broker_service import get_broker_positions
    result = get_broker_positions(cfg.host, cfg.api_key)
    if result is None:
        raise HTTPException(status_code=502, detail="Failed to fetch positions from broker")
    return result


@router.get("/orders")
async def get_broker_orders(db: AsyncSession = Depends(get_db)):
    """Return order book from the broker account."""
    cfg = await _get_or_create_settings(db)
    if not cfg.api_key or not cfg.connected:
        raise HTTPException(status_code=503, detail="Broker not connected")

    from app.services.broker_service import get_broker_orders
    result = get_broker_orders(cfg.host, cfg.api_key)
    if result is None:
        raise HTTPException(status_code=502, detail="Failed to fetch orders from broker")
    return result
