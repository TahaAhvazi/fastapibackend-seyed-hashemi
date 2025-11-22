from typing import Any, List, Optional
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.api import deps
from app.db.session import get_db

router = APIRouter()


def calculate_order_details(cart_items: List[models.CartItem]) -> List[schemas.OrderItemDetail]:
    """محاسبه جزئیات سفارش برای لیست آیتم‌های کارت"""
    order_details = []
    for cart_item in cart_items:
        product = cart_item.product
        
        if product.is_series:
            # For series products: calculate quantity per series
            if cart_item.selected_series and len(cart_item.selected_series) > 0:
                # Count occurrences of each series number
                series_counts = Counter(cart_item.selected_series)
                total_series_count = len(cart_item.selected_series)
                quantity_per_series = cart_item.quantity / total_series_count
                
                # Create series details with actual quantities
                series_details = []
                for series_num, count in series_counts.items():
                    series_details.append(schemas.SeriesDetail(
                        series_number=series_num,
                        quantity=quantity_per_series * count,  # Total quantity for this series
                        unit=cart_item.unit
                    ))
                # Sort by series number
                series_details.sort(key=lambda x: x.series_number)
            else:
                series_details = []
            
            order_details.append(schemas.OrderItemDetail(
                product_id=product.id,
                product_name=product.name,
                product_code=product.code,
                is_series=True,
                total_quantity=cart_item.quantity,
                unit=cart_item.unit,
                price_per_unit=cart_item.price,
                total_price=cart_item.quantity * cart_item.price,
                series_details=series_details,
                color_detail=None
            ))
        else:
            # For non-series products: color detail
            color_detail = None
            if cart_item.selected_color:
                color_detail = schemas.ColorDetail(
                    color=cart_item.selected_color,
                    quantity=cart_item.quantity,
                    unit=cart_item.unit
                )
            
            order_details.append(schemas.OrderItemDetail(
                product_id=product.id,
                product_name=product.name,
                product_code=product.code,
                is_series=False,
                total_quantity=cart_item.quantity,
                unit=cart_item.unit,
                price_per_unit=cart_item.price,
                total_price=cart_item.quantity * cart_item.price,
                series_details=None,
                color_detail=color_detail
            ))
    
    return order_details


# Public endpoint - no authentication required
@router.post("/public/submit", response_model=schemas.CartResponse)
async def submit_cart(
    *,
    db: AsyncSession = Depends(get_db),
    cart_in: schemas.CartCreate,
) -> Any:
    """
    ثبت سفارش عمومی (بدون نیاز به احراز هویت)
    
    **نکات مهم:**
    - برای محصولات سری (is_series=true): فیلد `selected_series` الزامی است و باید لیست شماره سری‌ها ارسال شود
    - برای محصولات غیرسری (is_series=false): فیلد `selected_color` الزامی است و باید رنگ انتخاب شده ارسال شود
    - سیستم به صورت خودکار موجودی را بررسی می‌کند
    - در response، جزئیات کامل سفارش شامل متراژ هر سری یا رنگ برگردانده می‌شود
    
    **مثال برای محصول سری:**
    ```json
    {
      "product_id": 1,
      "quantity": 50,
      "unit": "متر",
      "price": 350000,
      "selected_series": [1, 2, 3, 4, 5]
    }
    ```
    
    **مثال برای محصول غیرسری:**
    ```json
    {
      "product_id": 2,
      "quantity": 15,
      "unit": "متر",
      "price": 280000,
      "selected_color": "قرمز"
    }
    ```
    """
    # Validate products exist and check series/color requirements
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
        
        # Check if product is available
        if not product.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"محصول {product.name} در حال حاضر موجود نیست"
            )
        
        # Validate series/color based on product type
        if product.is_series:
            # For series products, selected_series is required
            if not item.selected_series or len(item.selected_series) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"برای محصول سری {product.name}، باید سری‌های موردنظر را انتخاب کنید"
                )
            
            # Check if series_numbers exists
            if not product.series_numbers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"محصول {product.name} سری‌ای تعریف نشده است"
                )
            
            # Validate that all selected series exist in product series_numbers
            invalid_series = [s for s in item.selected_series if s not in product.series_numbers]
            if invalid_series:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"سری‌های {invalid_series} برای محصول {product.name} موجود نیستند. سری‌های موجود: {product.series_numbers}"
                )
            
            # Check inventory for selected series
            if product.series_inventory:
                # Count how many of each series are requested
                series_counts = {}
                for series_num in item.selected_series:
                    series_counts[series_num] = series_counts.get(series_num, 0) + 1
                
                # Check if we have enough inventory
                for series_num, requested_count in series_counts.items():
                    # Find the index of this series in series_numbers
                    if series_num in product.series_numbers:
                        series_index = product.series_numbers.index(series_num)
                        if series_index < len(product.series_inventory):
                            available_count = product.series_inventory[series_index]
                            if requested_count > available_count:
                                raise HTTPException(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"موجودی سری {series_num} محصول {product.name} کافی نیست. موجودی: {available_count}, درخواستی: {requested_count}"
                                )
        else:
            # For non-series products, selected_color is required
            if not item.selected_color:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"برای محصول {product.name}، باید رنگ موردنظر را انتخاب کنید"
                )
            
            # Check if available_colors exists
            if not product.available_colors or (isinstance(product.available_colors, list) and len(product.available_colors) == 0):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"محصول '{product.name}' (کد: {product.code}) رنگ‌بندی تعریف نشده است. لطفاً ابتدا رنگ‌های موجود و موجودی هر رنگ را برای این محصول تعریف کنید."
                )
            
            # Validate that selected color exists in available_colors
            if item.selected_color not in product.available_colors:
                available_colors_str = ', '.join(product.available_colors) if product.available_colors else 'هیچ رنگی تعریف نشده'
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"رنگ '{item.selected_color}' برای محصول '{product.name}' (کد: {product.code}) موجود نیست. رنگ‌های موجود: {available_colors_str}"
                )
            
            # Check inventory for selected color
            if product.color_inventory:
                color_index = product.available_colors.index(item.selected_color)
                if color_index < len(product.color_inventory):
                    available_quantity = float(product.color_inventory[color_index]) if product.color_inventory[color_index] else 0
                    if item.quantity > available_quantity:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"موجودی رنگ {item.selected_color} محصول {product.name} کافی نیست. موجودی: {available_quantity}, درخواستی: {item.quantity}"
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
            selected_series=item_data.selected_series,
            selected_color=item_data.selected_color,
        )
        db.add(item)

    await db.commit()
    await db.refresh(cart)
    
    # Reload cart with items and products to get order details
    query = select(models.Cart).options(
        selectinload(models.Cart.items).selectinload(models.CartItem.product)
    ).where(models.Cart.id == cart.id)
    result = await db.execute(query)
    cart_with_items = result.scalars().unique().first()
    
    # Calculate order details using helper function
    order_details = calculate_order_details(cart_with_items.items)

    return schemas.CartResponse(
        id=cart.id,
        message=f"سفارش شما با موفقیت ثبت شد. کد پیگیری: #{cart.id}",
        total_amount=cart.total_amount,
        order_details=order_details
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
    دریافت لیست سفارشات (فقط برای admin/accountant)
    
    هر سفارش شامل:
    - اطلاعات مشتری
    - لیست آیتم‌ها با جزئیات محصول
    - برای محصولات سری: selected_series
    - برای محصولات غیرسری: selected_color
    """
    query = select(models.Cart).options(
        selectinload(models.Cart.items).selectinload(models.CartItem.product).selectinload(models.Product.images)
    )

    # Apply filters
    filters = []
    if status:
        filters.append(models.Cart.status == status)

    if filters:
        query = query.where(*filters)

    query = query.order_by(models.Cart.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    carts = result.scalars().unique().all()
    return carts


@router.get("/{cart_id}", response_model=schemas.Cart)
async def read_cart(
    cart_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    دریافت جزئیات یک سفارش خاص (فقط برای admin/accountant)
    
    شامل:
    - اطلاعات کامل مشتری
    - لیست آیتم‌ها با جزئیات کامل محصول
    - برای محصولات سری: selected_series
    - برای محصولات غیرسری: selected_color
    """
    query = select(models.Cart).options(
        selectinload(models.Cart.items).selectinload(models.CartItem.product).selectinload(models.Product.images)
    ).where(models.Cart.id == cart_id)

    result = await db.execute(query)
    cart = result.scalars().unique().first()

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
    به‌روزرسانی وضعیت سفارش (فقط برای admin/accountant)
    
    وضعیت‌های ممکن:
    - pending: در انتظار بررسی
    - reviewed: بررسی شده
    - approved: تایید شده
    - rejected: رد شده
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
        selectinload(models.Cart.items).selectinload(models.CartItem.product).selectinload(models.Product.images)
    ).where(models.Cart.id == cart_id)
    result = await db.execute(query)
    cart_with_items = result.scalars().unique().first()

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
