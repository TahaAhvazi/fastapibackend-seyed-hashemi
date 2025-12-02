from datetime import timedelta
from typing import Any, List, Optional
from sqlalchemy import or_
from fastapi import APIRouter, Depends, HTTPException, status, Query, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.post("/auth/login", response_model=schemas.CustomerToken)
async def customer_login(
    login_data: schemas.CustomerLogin,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    لاگین مشتری با شماره تلفن/موبایل و پسورد
    پسورد پیش‌فرض: 123456789
    """
    # جستجوی مشتری با شماره موبایل یا تلفن
    result = await db.execute(
        select(models.Customer).where(
            or_(
                models.Customer.mobile == login_data.phone_number,
                models.Customer.phone == login_data.phone_number
            )
        )
    )
    customer = result.scalars().first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="شماره تلفن یا رمز عبور نادرست است",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # اگر مشتری پسورد ندارد، آن را تنظیم کن
    if not customer.hashed_password:
        customer.hashed_password = security.get_password_hash("123456789")
        await db.commit()
        await db.refresh(customer)
    
    # بررسی پسورد
    if not security.verify_password(login_data.password, customer.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="شماره تلفن یا رمز عبور نادرست است",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            customer.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
        "customer_id": customer.id,
    }


@router.get("/profile", response_model=schemas.Customer)
async def get_customer_profile(
    current_customer: models.Customer = Security(deps.get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    دریافت پروفایل مشتری
    """
    # بارگذاری روابط
    result = await db.execute(
        select(models.Customer)
        .options(selectinload(models.Customer.bank_accounts))
        .where(models.Customer.id == current_customer.id)
    )
    customer = result.scalars().unique().first()
    return customer


@router.get("/invoices", response_model=List[schemas.Invoice])
async def get_customer_invoices(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[schemas.InvoiceStatus] = None,
    current_customer: models.Customer = Security(deps.get_current_customer),
) -> Any:
    """
    دریافت فاکتورهای مشتری
    """
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product).selectinload(models.Product.images),
        selectinload(models.Invoice.customer).selectinload(models.Customer.bank_accounts),
        selectinload(models.Invoice.created_by_user),
    ).where(models.Invoice.customer_id == current_customer.id)
    
    if status:
        query = query.where(models.Invoice.status == status)
    
    query = query.order_by(models.Invoice.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    invoices = result.scalars().all()
    return invoices


@router.get("/invoices/{invoice_id}", response_model=schemas.Invoice)
async def get_customer_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_customer: models.Customer = Security(deps.get_current_customer),
) -> Any:
    """
    دریافت جزئیات یک فاکتور خاص
    """
    result = await db.execute(
        select(models.Invoice)
        .options(
            selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product).selectinload(models.Product.images),
            selectinload(models.Invoice.customer).selectinload(models.Customer.bank_accounts),
            selectinload(models.Invoice.created_by_user),
        )
        .where(
            models.Invoice.id == invoice_id,
            models.Invoice.customer_id == current_customer.id
        )
    )
    invoice = result.scalars().unique().first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="فاکتور یافت نشد",
        )
    
    return invoice


@router.get("/checks", response_model=List[schemas.Check])
async def get_customer_checks(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[schemas.CheckStatus] = None,
    current_customer: models.Customer = Security(deps.get_current_customer),
) -> Any:
    """
    دریافت چک‌های مشتری
    """
    query = select(models.Check).options(
        selectinload(models.Check.customer),
        selectinload(models.Check.related_invoice),
        selectinload(models.Check.created_by_user),
    ).where(models.Check.customer_id == current_customer.id)
    
    if status:
        query = query.where(models.Check.status == status)
    
    query = query.order_by(models.Check.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    checks = result.scalars().all()
    
    # Convert to response format
    response_checks = []
    for check in checks:
        check_dict = {
            "id": check.id,
            "check_number": check.check_number,
            "customer_id": check.customer_id,
            "amount": check.amount,
            "issue_date": check.issue_date,
            "due_date": check.due_date,
            "status": check.status,
            "related_invoice_id": check.related_invoice_id,
            "attachments": check.attachments,
            "created_by": check.created_by,
            "created_at": check.created_at,
            "updated_at": check.updated_at,
            "customer": {
                "id": check.customer.id,
                "first_name": check.customer.first_name,
                "last_name": check.customer.last_name,
                "full_name": check.customer.full_name,
                "phone": check.customer.phone,
                "mobile": check.customer.mobile,
                "city": check.customer.city,
                "province": check.customer.province,
                "address": check.customer.address
            } if check.customer else None,
            "related_invoice": {
                "id": check.related_invoice.id,
                "invoice_number": check.related_invoice.invoice_number,
                "customer_id": check.related_invoice.customer_id,
                "total": check.related_invoice.total,
                "status": check.related_invoice.status,
                "payment_type": check.related_invoice.payment_type
            } if check.related_invoice else None,
            "created_by_user": schemas.User.model_validate(check.created_by_user) if check.created_by_user else None
        }
        response_checks.append(check_dict)
    
    return response_checks


@router.get("/balance", response_model=schemas.CustomerBalanceInfo)
async def get_customer_balance(
    current_customer: models.Customer = Security(deps.get_current_customer),
) -> Any:
    """
    دریافت موجودی و تراز حساب مشتری
    """
    return {
        "current_balance": current_customer.current_balance,
        "is_creditor": current_customer.is_creditor,
        "is_debtor": current_customer.is_debtor,
        "balance_status": current_customer.balance_status,
        "balance_notes": current_customer.balance_notes,
    }


@router.get("/products", response_model=List[schemas.Product])
async def get_products(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    current_customer: models.Customer = Security(deps.get_current_customer),
) -> Any:
    """
    دریافت لیست محصولات (فقط محصولات قابل مشاهده)
    """
    query = select(models.Product).options(
        selectinload(models.Product.images)
    ).where(models.Product.visible == True, models.Product.is_available == True)
    
    if category:
        query = query.where(models.Product.category == category)
    
    if search:
        query = query.where(
            or_(
                models.Product.name.contains(search),
                models.Product.code.contains(search),
                models.Product.description.contains(search)
            )
        )
    
    query = query.order_by(models.Product.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()
    return products


@router.get("/products/{product_id}", response_model=schemas.Product)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_customer: models.Customer = Security(deps.get_current_customer),
) -> Any:
    """
    دریافت جزئیات یک محصول
    """
    result = await db.execute(
        select(models.Product)
        .options(selectinload(models.Product.images))
        .where(
            models.Product.id == product_id,
            models.Product.visible == True,
            models.Product.is_available == True
        )
    )
    product = result.scalars().unique().first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="محصول یافت نشد",
        )
    
    return product


@router.get("/cart")
async def get_customer_cart(
    db: AsyncSession = Depends(get_db),
    current_customer: models.Customer = Security(deps.get_current_customer),
) -> Any:
    """
    دریافت سبد خرید مشتری
    """
    result = await db.execute(
        select(models.Cart)
        .options(
            selectinload(models.Cart.items).selectinload(models.CartItem.product).selectinload(models.Product.images)
        )
        .where(models.Cart.customer_id == current_customer.id)
    )
    cart = result.scalars().unique().first()
    
    if not cart:
        # ایجاد سبد خرید جدید اگر وجود نداشته باشد
        cart = models.Cart(
            customer_id=current_customer.id,
            customer_name=current_customer.full_name,
            customer_phone=current_customer.mobile or current_customer.phone or "",
            customer_address=current_customer.address,
            total_amount=0.0
        )
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
        # بارگذاری مجدد با items
        result = await db.execute(
            select(models.Cart)
            .options(
                selectinload(models.Cart.items).selectinload(models.CartItem.product).selectinload(models.Product.images)
            )
            .where(models.Cart.id == cart.id)
        )
        cart = result.scalars().unique().first()
    
    # محاسبه جزئیات سفارش
    from app.api.v1.endpoints.carts import calculate_order_details
    order_details = calculate_order_details(cart.items) if cart.items else []
    
    total_price = sum(item.quantity * item.price for item in cart.items) if cart.items else 0.0
    
    return {
        "id": cart.id,
        "customer_id": cart.customer_id,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name,
                "product_code": item.product.code,
                "quantity": item.quantity,
                "unit": item.unit,
                "price": item.price,
                "total_price": item.total_price,
                "selected_series": item.selected_series,
                "selected_color": item.selected_color,
                "product": item.product,
            }
            for item in cart.items
        ] if cart.items else [],
        "order_details": order_details,
        "total_amount": total_price,
        "created_at": cart.created_at,
        "updated_at": cart.updated_at,
    }


@router.post("/cart/items", response_model=schemas.CartItem)
async def add_item_to_cart(
    item_in: schemas.CartItemCreate,
    db: AsyncSession = Depends(get_db),
    current_customer: models.Customer = Security(deps.get_current_customer),
) -> Any:
    """
    افزودن آیتم به سبد خرید
    """
    # بررسی وجود سبد خرید
    result = await db.execute(
        select(models.Cart).where(models.Cart.customer_id == current_customer.id)
    )
    cart = result.scalars().first()
    
    if not cart:
        cart = models.Cart(
            customer_id=current_customer.id,
            customer_name=current_customer.full_name,
            customer_phone=current_customer.mobile or current_customer.phone or "",
            customer_address=current_customer.address,
            total_amount=0.0
        )
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
    
    # بررسی وجود محصول
    product_result = await db.execute(
        select(models.Product)
        .options(selectinload(models.Product.images))
        .where(models.Product.id == item_in.product_id)
    )
    product = product_result.scalars().unique().first()
    
    if not product or not product.is_available or not product.visible:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="محصول یافت نشد یا در دسترس نیست",
        )
    
    # بررسی موجودی
    if product.is_series:
        if not item_in.selected_series:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="برای محصولات سری، انتخاب سری الزامی است",
            )
        # بررسی موجودی سری‌ها
        if not product.series_inventory or not product.series_numbers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="محصول سری موجودی ندارد",
            )
        # بررسی موجودی هر سری
        for series_num in item_in.selected_series:
            if series_num not in product.series_numbers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"سری {series_num} موجود نیست",
                )
    else:
        if not item_in.selected_color:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="برای محصولات غیرسری، انتخاب رنگ الزامی است",
            )
        # بررسی موجودی رنگ
        if not product.color_inventory or not product.available_colors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="محصول رنگ موجودی ندارد",
            )
        if item_in.selected_color not in product.available_colors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"رنگ {item_in.selected_color} موجود نیست",
            )
    
    # ایجاد یا به‌روزرسانی آیتم سبد خرید
    cart_item = models.CartItem(
        cart_id=cart.id,
        product_id=item_in.product_id,
        quantity=item_in.quantity,
        unit=item_in.unit or product.unit,
        price=item_in.price,
        selected_series=item_in.selected_series,
        selected_color=item_in.selected_color,
    )
    db.add(cart_item)
    await db.commit()
    await db.refresh(cart_item)
    
    # بارگذاری محصول
    result = await db.execute(
        select(models.CartItem)
        .options(selectinload(models.CartItem.product).selectinload(models.Product.images))
        .where(models.CartItem.id == cart_item.id)
    )
    cart_item_with_product = result.scalars().unique().first()
    
    return cart_item_with_product


@router.put("/cart/items/{item_id}", response_model=schemas.CartItem)
async def update_cart_item(
    item_id: int,
    item_in: schemas.CartItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_customer: models.Customer = Security(deps.get_current_customer),
) -> Any:
    """
    به‌روزرسانی آیتم سبد خرید
    """
    # بررسی مالکیت سبد خرید
    result = await db.execute(
        select(models.Cart).where(models.Cart.customer_id == current_customer.id)
    )
    cart = result.scalars().first()
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="سبد خرید یافت نشد",
        )
    
    # بررسی آیتم
    item_result = await db.execute(
        select(models.CartItem)
        .options(selectinload(models.CartItem.product))
        .where(
            models.CartItem.id == item_id,
            models.CartItem.cart_id == cart.id
        )
    )
    cart_item = item_result.scalars().unique().first()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="آیتم سبد خرید یافت نشد",
        )
    
    # به‌روزرسانی
    if item_in.quantity is not None:
        cart_item.quantity = item_in.quantity
    if item_in.price is not None:
        cart_item.price = item_in.price
    if item_in.selected_series is not None:
        cart_item.selected_series = item_in.selected_series
    if item_in.selected_color is not None:
        cart_item.selected_color = item_in.selected_color
    
    await db.commit()
    await db.refresh(cart_item)
    
    return cart_item


@router.delete("/cart/items/{item_id}")
async def delete_cart_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_customer: models.Customer = Security(deps.get_current_customer),
) -> Any:
    """
    حذف آیتم از سبد خرید
    """
    # بررسی مالکیت سبد خرید
    result = await db.execute(
        select(models.Cart).where(models.Cart.customer_id == current_customer.id)
    )
    cart = result.scalars().first()
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="سبد خرید یافت نشد",
        )
    
    # بررسی آیتم
    item_result = await db.execute(
        select(models.CartItem).where(
            models.CartItem.id == item_id,
            models.CartItem.cart_id == cart.id
        )
    )
    cart_item = item_result.scalars().first()
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="آیتم سبد خرید یافت نشد",
        )
    
    await db.delete(cart_item)
    await db.commit()
    
    return {"message": "آیتم با موفقیت حذف شد"}


@router.delete("/cart")
async def clear_cart(
    db: AsyncSession = Depends(get_db),
    current_customer: models.Customer = Security(deps.get_current_customer),
) -> Any:
    """
    پاک کردن تمام سبد خرید
    """
    result = await db.execute(
        select(models.Cart)
        .options(selectinload(models.Cart.items))
        .where(models.Cart.customer_id == current_customer.id)
    )
    cart = result.scalars().unique().first()
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="سبد خرید یافت نشد",
        )
    
    # حذف تمام آیتم‌ها
    for item in cart.items:
        await db.delete(item)
    
    await db.commit()
    
    return {"message": "سبد خرید با موفقیت پاک شد"}

