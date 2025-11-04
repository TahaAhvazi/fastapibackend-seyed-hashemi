from typing import Any, List, Optional
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy import or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import models, schemas
from app.api import deps
from app.core.config import settings
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
    # Ignore image_url if provided - images should be uploaded separately via /products/{id}/image endpoint
    product_data = product_in.model_dump(exclude={"image_url"})
    product = models.Product(**product_data)
    product.image_url = None  # Always set to None on creation
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
    # Ignore image_url if provided - images should be uploaded separately via /products/{id}/image endpoint
    update_data = product_in.model_dump(exclude_unset=True, exclude={"image_url"})
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


@router.post("/{product_id}/image", response_model=schemas.Product)
async def upload_product_image(
    *,
    db: AsyncSession = Depends(get_db),
    product_id: int,
    file: UploadFile = File(...),
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    Upload an image for a product (admin or warehouse only)
    """
    # Check if product exists
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    product = result.scalars().first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="محصول یافت نشد",  # Product not found
        )
    
    # Check file size
    file_size = 0
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="حجم فایل بیش از حد مجاز است",  # File size exceeds the limit
        )
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نوع فایل مجاز نیست. فقط فایل‌های تصویری مجاز هستند",  # File type not allowed. Only image files are allowed
        )
    
    # Delete old image if exists
    if product.image_url:
        file_path_parts = product.image_url.lstrip("/").split("/")
        if len(file_path_parts) >= 3 and file_path_parts[0] == "uploads" and file_path_parts[1] == "products":
            old_filename = "/".join(file_path_parts[2:])
            old_full_path = os.path.join(settings.UPLOADS_DIR, "products", old_filename)
            if os.path.exists(old_full_path) and os.path.isfile(old_full_path):
                try:
                    os.remove(old_full_path)
                except Exception as e:
                    print(f"Error deleting old image file: {e}")
    
    # Create uploads directory if it doesn't exist
    product_upload_dir = os.path.join(settings.UPLOADS_DIR, "products")
    os.makedirs(product_upload_dir, exist_ok=True)
    
    # Save file with timestamp and product code
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{product.code}_{timestamp}{file_ext}"
    file_path = os.path.join(product_upload_dir, safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Update product image_url
    relative_path = f"/uploads/products/{safe_filename}"
    product.image_url = relative_path
    
    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    return product


@router.delete("/{product_id}/image", response_model=schemas.Product)
async def delete_product_image(
    *,
    db: AsyncSession = Depends(get_db),
    product_id: int,
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    Delete product image (admin or warehouse only)
    """
    # Check if product exists
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    product = result.scalars().first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="محصول یافت نشد",  # Product not found
        )
    
    # Delete the image file if it exists
    if product.image_url:
        # Extract filename from image_url (format: /uploads/products/filename.ext)
        # Remove leading slash and split
        file_path_parts = product.image_url.lstrip("/").split("/")
        if len(file_path_parts) >= 3 and file_path_parts[0] == "uploads" and file_path_parts[1] == "products":
            filename = "/".join(file_path_parts[2:])
            full_path = os.path.join(settings.UPLOADS_DIR, "products", filename)
            
            if os.path.exists(full_path) and os.path.isfile(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    # Log error but don't fail the request
                    print(f"Error deleting image file: {e}")
    
    # Clear image_url from product
    product.image_url = None
    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    return product