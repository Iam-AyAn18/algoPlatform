from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List

from app.core.database import get_db
from app.models.db_models import Order
from app.models.schemas import OrderCreate, OrderResponse
from app.services.order_service import place_order

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(order_in: OrderCreate, db: AsyncSession = Depends(get_db)):
    """Place a paper or real order.

    Set ``use_broker=true`` to route through the configured OpenAlgo broker.
    Behaviour depends on the broker's ``trade_mode`` setting:
      - paper      → always paper-trade regardless of use_broker
      - semi_auto  → queue for manual approval in Action Center
      - auto       → execute real broker order immediately
    """
    return await place_order(order_in, db)


@router.get("/", response_model=List[OrderResponse])
async def list_orders(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).order_by(desc(Order.created_at)).limit(limit))
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.delete("/{order_id}", status_code=204)
async def cancel_order(order_id: int, db: AsyncSession = Depends(get_db)):
    from app.models.db_models import OrderStatus
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in (OrderStatus.PENDING, OrderStatus.PENDING_APPROVAL):
        raise HTTPException(status_code=400, detail="Only PENDING or PENDING_APPROVAL orders can be cancelled")
    order.status = OrderStatus.CANCELLED
    await db.commit()

