"""Algo trading API – webhook receiver and Action Center endpoints.

Webhook endpoint: POST /algo/webhook
  Receives trading signals from TradingView, GoCharting, or any external
  system. The signal is stored and processed according to the current
  trade_mode configured in BrokerSettings:
    - paper     → paper-trade immediately
    - semi_auto → queue as PENDING_APPROVAL in Action Center
    - auto      → execute real order via OpenAlgo immediately

Action Center endpoints: GET/POST /algo/action-center
  Let the user review and approve/reject orders queued in semi-auto mode.
"""
from __future__ import annotations
import datetime
import json
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db_models import Order, OrderSide, OrderStatus, OrderType, WebhookSignal
from app.models.schemas import (
    OrderCreate, OrderResponse,
    WebhookPayload, WebhookSignalResponse,
    ActionCenterOrder,
)
from app.services.order_service import place_order, approve_action_center_order

router = APIRouter(prefix="/algo", tags=["Algo Trading"])

# Optional webhook secret configured via environment variable
_WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")


# ── Webhook receiver ──────────────────────────────────────────────────────────

@router.post("/webhook", status_code=201)
async def receive_webhook(
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    """Receive an external trading signal (TradingView / GoCharting / custom).

    The ``secret`` field in the payload is compared against the
    ``WEBHOOK_SECRET`` environment variable.  If ``WEBHOOK_SECRET`` is empty,
    authentication is disabled (suitable for local development).

    The signal is processed according to the broker's trade_mode:
      - paper:      paper-trade immediately
      - semi_auto:  queue for manual approval (Action Center)
      - auto:       execute real broker order immediately
    """
    # Optional secret authentication
    if _WEBHOOK_SECRET and payload.secret != _WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    action = payload.action.upper()
    if action not in ("BUY", "SELL", "EXIT"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action '{payload.action}'. Must be BUY, SELL, or EXIT",
        )

    # Persist the raw signal
    signal = WebhookSignal(
        source="webhook",
        symbol=payload.symbol.upper(),
        exchange=payload.exchange.upper(),
        action=action,
        quantity=payload.quantity,
        price=payload.price,
        strategy=payload.strategy,
        raw_payload=json.dumps(payload.model_dump()),
        processed=False,
    )
    db.add(signal)
    await db.commit()
    await db.refresh(signal)

    # EXIT maps to SELL
    order_side = OrderSide.BUY if action == "BUY" else OrderSide.SELL

    # Determine quantity (must be > 0)
    qty = payload.quantity
    if qty <= 0:
        qty = 1  # default to 1 share if not specified

    # Check broker settings to decide trade mode
    from sqlalchemy import select as sa_select
    from app.models.db_models import BrokerSettings
    broker_result = await db.execute(sa_select(BrokerSettings).where(BrokerSettings.id == 1))
    broker_cfg = broker_result.scalar_one_or_none()
    trade_mode = broker_cfg.trade_mode if broker_cfg else "paper"

    order_in = OrderCreate(
        symbol=payload.symbol,
        exchange=payload.exchange,
        side=order_side,
        order_type=OrderType.MARKET if not payload.price else OrderType.LIMIT,
        quantity=qty,
        price=payload.price,
        strategy=payload.strategy or "webhook",
        use_broker=(trade_mode in ("semi_auto", "auto")),
    )

    try:
        order = await place_order(order_in, db)
        signal.processed = True
        signal.order_id = order.id
        await db.commit()
        return {
            "signal_id": signal.id,
            "order_id": order.id,
            "status": order.status,
            "mode": order.mode,
            "message": f"Signal processed: {order_side.value} {qty} {payload.symbol}",
        }
    except Exception as exc:
        return {
            "signal_id": signal.id,
            "order_id": None,
            "status": "error",
            "message": str(exc),
        }


# ── Webhook signals history ───────────────────────────────────────────────────

@router.get("/webhook/signals", response_model=List[WebhookSignalResponse])
async def list_webhook_signals(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Return recent webhook signals (newest first)."""
    result = await db.execute(
        select(WebhookSignal).order_by(desc(WebhookSignal.received_at)).limit(limit)
    )
    return result.scalars().all()


# ── Action Center ─────────────────────────────────────────────────────────────

@router.get("/action-center", response_model=List[ActionCenterOrder])
async def list_pending_orders(db: AsyncSession = Depends(get_db)):
    """Return all orders queued for manual approval (PENDING_APPROVAL status)."""
    result = await db.execute(
        select(Order)
        .where(Order.status == OrderStatus.PENDING_APPROVAL)
        .order_by(Order.created_at)
    )
    return result.scalars().all()


@router.post("/action-center/{order_id}/approve", response_model=OrderResponse)
async def approve_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """Approve a queued order – routes it to the real broker for execution."""
    try:
        return await approve_action_center_order(order_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/action-center/{order_id}/reject", response_model=OrderResponse)
async def reject_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """Reject a queued order – marks it as CANCELLED."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Order is not pending approval (status={order.status})",
        )
    order.status = OrderStatus.CANCELLED
    await db.commit()
    await db.refresh(order)
    return OrderResponse.model_validate(order)


@router.post("/action-center/approve-all")
async def approve_all_pending(db: AsyncSession = Depends(get_db)):
    """Approve all pending orders in bulk."""
    result = await db.execute(
        select(Order).where(Order.status == OrderStatus.PENDING_APPROVAL)
    )
    orders = result.scalars().all()
    approved = []
    failed = []
    for order in orders:
        try:
            updated = await approve_action_center_order(order.id, db)
            approved.append(updated.id)
        except Exception as exc:
            failed.append({"id": order.id, "error": str(exc)})
    return {
        "approved": approved,
        "failed": failed,
        "message": f"Approved {len(approved)}, failed {len(failed)}",
    }
