from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.api import deps
from app.db.session import get_db

router = APIRouter()


# Public endpoint - no authentication required
@router.post("/public/submit", response_model=schemas.CartResponse)
async def submit_cart(
    *,
    db: AsyncSession = Depends(get_db),
    cart_in: schemas.CartCreate,
) -> Any:
    """
    Submit a cart order (public endpoint - no authentication required)
    """
    # Validate products exist
    for item in cart_in.items:
        product_result = await db.execute(
            select(models.Product).where(models.Product.id == item.product_id)
        )
        product = product_result.scalars().first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"محصول با شناسه {item.product_id} یافت نشد"
            )

    # Calculate total amount
    total_amount = sum(item.quantity * item.price for item in cart_in.items)

    # Create cart
    cart = models.Cart(
        customer_name=cart_in.customer_name,
        customer_phone=cart_in.customer_phone,
        customer_email=cart_in.customer_email,
        customer_address=cart_in.customer_address,
        notes=cart_in.notes,
        total_amount=total_amount,
        status=schemas.CartStatus.PENDING,
    )

    db.add(cart)
    await db.flush()  # Get the cart ID

    # Create cart items
    for item_data in cart_in.items:
        item = models.CartItem(
            cart_id=cart.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit=item_data.unit,
            price=item_data.price,
        )
        db.add(item)

    await db.commit()
    await db.refresh(cart)

    return schemas.CartResponse(
        id=cart.id,
        message=f"سفارش شما با موفقیت ثبت شد. کد پیگیری: #{cart.id}",
        total_amount=cart.total_amount
    )


# Admin/Accountant endpoints
@router.get("/", response_model=List[schemas.Cart])
async def read_carts(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: Optional[schemas.CartStatus] = None,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Retrieve cart orders (admin/accountant only)
    """
    query = select(models.Cart).options(
        selectinload(models.Cart.items).selectinload(models.CartItem.product)
    )

    # Apply filters
    filters = []
    if status:
        filters.append(models.Cart.status == status)

    if filters:
        query = query.where(*filters)

    query = query.order_by(models.Cart.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    carts = result.scalars().all()
    return carts


@router.get("/{cart_id}", response_model=schemas.Cart)
async def read_cart(
    cart_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Get a specific cart order by id (admin/accountant only)
    """
    query = select(models.Cart).options(
        selectinload(models.Cart.items).selectinload(models.CartItem.product)
    ).where(models.Cart.id == cart_id)

    result = await db.execute(query)
    cart = result.scalars().first()

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="سفارش یافت نشد"
        )

    return cart


@router.put("/{cart_id}", response_model=schemas.Cart)
async def update_cart_status(
    *,
    db: AsyncSession = Depends(get_db),
    cart_id: int,
    cart_in: schemas.CartUpdate,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Update cart status (admin/accountant only)
    """
    result = await db.execute(select(models.Cart).where(models.Cart.id == cart_id))
    cart = result.scalars().first()

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="سفارش یافت نشد"
        )

    # Update status
    cart.status = cart_in.status
    db.add(cart)
    await db.commit()
    await db.refresh(cart)

    # Reload with relationships
    query = select(models.Cart).options(
        selectinload(models.Cart.items).selectinload(models.CartItem.product)
    ).where(models.Cart.id == cart_id)
    result = await db.execute(query)
    cart_with_items = result.scalars().first()

    return cart_with_items


@router.delete("/{cart_id}")
async def delete_cart(
    cart_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Delete a cart order (admin only)
    """
    result = await db.execute(select(models.Cart).where(models.Cart.id == cart_id))
    cart = result.scalars().first()

    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="سفارش یافت نشد"
        )

    await db.delete(cart)
    await db.commit()

    return {"message": "سفارش با موفقیت حذف شد"}


@router.get("/stats/summary")
async def get_cart_stats(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Get cart statistics (admin/accountant only)
    """
    from sqlalchemy import func

    # Get counts by status
    status_counts = await db.execute(
        select(
            models.Cart.status,
            func.count(models.Cart.id).label('count')
        ).group_by(models.Cart.status)
    )
    status_stats = {row.status: row.count for row in status_counts}

    # Get total amount
    total_result = await db.execute(
        select(func.sum(models.Cart.total_amount))
    )
    total_amount = total_result.scalar() or 0

    # Get total orders
    total_orders = await db.execute(
        select(func.count(models.Cart.id))
    )
    total_count = total_orders.scalar() or 0

    return {
        "total_orders": total_count,
        "total_amount": total_amount,
        "status_breakdown": status_stats
    }
