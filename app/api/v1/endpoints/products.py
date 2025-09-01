from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import models, schemas
from app.api import deps
from app.db.session import get_db

router = APIRouter()


@router.get("/", response_model=List[schemas.Product])
async def read_products(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    code: Optional[str] = None,
    name: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
) -> Any:
    """
    Retrieve products with optional filtering
    """
    query = select(models.Product)
    
    # Apply filters
    filters = []
    if code:
        filters.append(models.Product.code.ilike(f"%{code}%"))
    if name:
        filters.append(models.Product.name.ilike(f"%{name}%"))
    if category:
        filters.append(models.Product.category.ilike(f"%{category}%"))
    if min_price is not None:
        filters.append(models.Product.sale_price >= min_price)
    if max_price is not None:
        filters.append(models.Product.sale_price <= max_price)
    if in_stock is not None:
        if in_stock:
            filters.append(models.Product.quantity_available > 0)
        else:
            filters.append(models.Product.quantity_available <= 0)
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()
    return products


@router.post("/", response_model=schemas.Product)
async def create_product(
    *,
    db: AsyncSession = Depends(get_db),
    product_in: schemas.ProductCreate,
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    Create new product (admin or warehouse only)
    """
    # Check if product with this code exists
    result = await db.execute(select(models.Product).where(models.Product.code == product_in.code))
    existing_product = result.scalars().first()
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="محصولی با این کد قبلاً ثبت شده است",  # A product with this code already exists
        )
    
    # Create new product
    product = models.Product(**product_in.dict())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("/{product_id}", response_model=schemas.Product)
async def read_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get a specific product by id
    """
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    product = result.scalars().first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="محصول یافت نشد",  # Product not found
        )
    return product


@router.put("/{product_id}", response_model=schemas.Product)
async def update_product(
    *,
    db: AsyncSession = Depends(get_db),
    product_id: int,
    product_in: schemas.ProductUpdate,
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    Update a product (admin or warehouse only)
    """
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    product = result.scalars().first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="محصول یافت نشد",  # Product not found
        )
    
    # Update product attributes
    update_data = product_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", response_model=schemas.Product)
async def delete_product(
    *,
    db: AsyncSession = Depends(get_db),
    product_id: int,
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    Delete a product (admin or warehouse only)
    """
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    product = result.scalars().first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="محصول یافت نشد",  # Product not found
        )
    
    # Check if product is used in any invoice
    invoice_items_query = select(models.InvoiceItem).where(models.InvoiceItem.product_id == product_id)
    invoice_items_result = await db.execute(invoice_items_query)
    invoice_items = invoice_items_result.scalars().first()
    
    if invoice_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="این محصول در فاکتورها استفاده شده است و قابل حذف نیست",  # This product is used in invoices and cannot be deleted
        )
    
    await db.delete(product)
    await db.commit()
    return product