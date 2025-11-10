from typing import Any, List, Optional
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy import or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

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
    in_stock: Optional[bool] = None,
) -> Any:
    """
    Retrieve products with optional filtering
    """
    query = select(models.Product).options(selectinload(models.Product.images))
    
    # Apply filters
    filters = []
    if code:
        filters.append(models.Product.code.ilike(f"%{code}%"))
    if name:
        filters.append(models.Product.name.ilike(f"%{name}%"))
    if category:
        filters.append(models.Product.category.ilike(f"%{category}%"))
    if in_stock is not None:
        if in_stock:
            filters.append(models.Product.quantity_available > 0)
        else:
            filters.append(models.Product.quantity_available <= 0)
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    products = result.scalars().unique().all()
    
    # Convert to response format with images
    products_list = []
    for product in products:
        # Build product dict excluding relationship objects
        product_dict = {
            'id': product.id,
            'code': product.code,
            'name': product.name,
            'description': product.description,
            'category': product.category,
            'unit': product.unit,
            'quantity_available': product.quantity_available,
            'colors': product.colors,
            'created_at': product.created_at,
            'updated_at': product.updated_at,
            'images': [img.image_url for img in product.images] if product.images else []
        }
        products_list.append(schemas.Product(**product_dict))
    
    return products_list


@router.post("/", response_model=schemas.Product)
async def create_product(
    *,
    db: AsyncSession = Depends(get_db),
    code: str = Form(..., min_length=1, description="کد محصول"),
    name: str = Form(..., min_length=1, description="نام محصول"),
    category: str = Form(..., min_length=1, description="دسته‌بندی محصول"),
    unit: str = Form(..., min_length=1, description="واحد اندازه‌گیری"),
    quantity_available: float = Form(default=0, ge=0, description="موجودی موجود"),
    description: Optional[str] = Form(None, description="توضیحات محصول"),
    colors: Optional[str] = Form(None, description="رنگ‌ها"),
    images: Optional[List[UploadFile]] = File(None, description="عکس‌های محصول"),
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    ایجاد محصول جدید (فقط برای admin یا warehouse)
    Create new product (admin or warehouse only)
    
    فیلدهای اجباری:
    - code: کد محصول (string)
    - name: نام محصول (string)
    - category: دسته‌بندی محصول (string) - مثال: "ساتن"، "کتان"، "ابریشم"
    - unit: واحد اندازه‌گیری (string) - مثال: "متر"، "یارد"، "طاقه"
    - images: فایل‌های عکس محصول (اختیاری)
    
    Required fields:
    - code: Product code (string)
    - name: Product name (string)
    - category: Product category (string) - example: "ساتن", "کتان", "ابریشم"
    - unit: Measurement unit (string) - example: "متر", "یارد", "طاقه"
    - images: Image files (optional)
    """
    # Check if product with this code exists
    result = await db.execute(select(models.Product).where(models.Product.code == code))
    existing_product = result.scalars().first()
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="محصولی با این کد قبلاً ثبت شده است",  # A product with this code already exists
        )
    
    # Create new product
    product = models.Product(
        code=code,
        name=name,
        category=category,
        unit=unit,
        quantity_available=quantity_available,
        description=description,
        colors=colors,
    )
    db.add(product)
    await db.flush()  # Flush to get the product ID
    
    # Process images if provided
    if images:
        product_upload_dir = os.path.join(settings.UPLOADS_DIR, "products")
        os.makedirs(product_upload_dir, exist_ok=True)
        
        for idx, image_file in enumerate(images):
            try:
                # Check file size
                file_size = 0
                contents = await image_file.read()
                file_size = len(contents)
                await image_file.seek(0)
                
                if file_size > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"حجم عکس شماره {idx + 1} بیش از حد مجاز است",
                    )
                
                # Check file extension
                file_ext = os.path.splitext(image_file.filename)[1].lower() if image_file.filename else '.jpg'
                if file_ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"نوع فایل عکس شماره {idx + 1} مجاز نیست. فقط فایل‌های تصویری مجاز هستند",
                    )
                
                # Save file
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                safe_filename = f"{product.code}_{timestamp}_{idx}{file_ext}"
                file_path = os.path.join(product_upload_dir, safe_filename)
                
                with open(file_path, "wb") as f:
                    f.write(contents)
                
                # Create ProductImage record
                relative_path = f"/uploads/products/{safe_filename}"
                product_image = models.ProductImage(
                    product_id=product.id,
                    image_url=relative_path
                )
                db.add(product_image)
            except HTTPException:
                raise
            except Exception as e:
                # If image processing fails, log and continue
                print(f"Error processing image {idx + 1}: {e}")
                continue
    
    await db.commit()
    
    # Reload product with images using selectinload to ensure relationship is loaded
    result = await db.execute(
        select(models.Product)
        .options(selectinload(models.Product.images))
        .where(models.Product.id == product.id)
    )
    product_with_images = result.scalars().unique().first()
    
    # Convert to response format with images
    product_dict = {
        'id': product_with_images.id,
        'code': product_with_images.code,
        'name': product_with_images.name,
        'description': product_with_images.description,
        'category': product_with_images.category,
        'unit': product_with_images.unit,
        'quantity_available': product_with_images.quantity_available,
        'colors': product_with_images.colors,
        'created_at': product_with_images.created_at,
        'updated_at': product_with_images.updated_at,
        'images': [img.image_url for img in product_with_images.images] if product_with_images.images else []
    }
    
    return schemas.Product(**product_dict)


@router.get("/{product_id}", response_model=schemas.Product)
async def read_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get a specific product by id
    """
    result = await db.execute(
        select(models.Product)
        .options(selectinload(models.Product.images))
        .where(models.Product.id == product_id)
    )
    product = result.scalars().unique().first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="محصول یافت نشد",  # Product not found
        )
    
    # Convert to response format with images
    product_dict = {
        'id': product.id,
        'code': product.code,
        'name': product.name,
        'description': product.description,
        'category': product.category,
        'unit': product.unit,
        'quantity_available': product.quantity_available,
        'colors': product.colors,
        'created_at': product.created_at,
        'updated_at': product.updated_at,
        'images': [img.image_url for img in product.images] if product.images else []
    }
    
    return schemas.Product(**product_dict)


@router.put("/{product_id}", response_model=schemas.Product)
async def update_product(
    *,
    db: AsyncSession = Depends(get_db),
    product_id: int,
    code: Optional[str] = Form(None, description="کد محصول"),
    name: Optional[str] = Form(None, description="نام محصول"),
    category: Optional[str] = Form(None, description="دسته‌بندی محصول"),
    unit: Optional[str] = Form(None, description="واحد اندازه‌گیری"),
    quantity_available: Optional[float] = Form(None, ge=0, description="موجودی موجود"),
    description: Optional[str] = Form(None, description="توضیحات محصول"),
    colors: Optional[str] = Form(None, description="رنگ‌ها"),
    images: Optional[List[UploadFile]] = File(None, description="عکس‌های جدید محصول (اضافه می‌شوند به عکس‌های موجود)"),
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    ویرایش محصول (فقط برای admin یا warehouse)
    Update a product (admin or warehouse only)
    
    همه فیلدها اختیاری هستند. فقط فیلدهایی که ارسال می‌شوند به‌روزرسانی می‌شوند.
    عکس‌های جدید به عکس‌های موجود اضافه می‌شوند.
    
    All fields are optional. Only sent fields will be updated.
    New images will be added to existing images.
    """
    result = await db.execute(
        select(models.Product)
        .options(selectinload(models.Product.images))
        .where(models.Product.id == product_id)
    )
    product = result.scalars().unique().first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="محصول یافت نشد",  # Product not found
        )
    
    # Update product attributes if provided
    if code is not None:
        # Check if code is already used by another product
        if code != product.code:
            existing_result = await db.execute(select(models.Product).where(models.Product.code == code))
            existing_product = existing_result.scalars().first()
            if existing_product and existing_product.id != product.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="محصولی با این کد قبلاً ثبت شده است",
                )
        product.code = code
    
    if name is not None:
        product.name = name
    if category is not None:
        product.category = category
    if unit is not None:
        product.unit = unit
    if quantity_available is not None:
        product.quantity_available = quantity_available
    if description is not None:
        product.description = description
    if colors is not None:
        product.colors = colors
    
    db.add(product)
    await db.flush()  # Flush to ensure product is saved before adding images
    
    # Process new images if provided
    if images:
        product_upload_dir = os.path.join(settings.UPLOADS_DIR, "products")
        os.makedirs(product_upload_dir, exist_ok=True)
        
        # Get current number of images to use as starting index
        current_images_count = len(product.images) if product.images else 0
        
        for idx, image_file in enumerate(images):
            try:
                # Check file size
                file_size = 0
                contents = await image_file.read()
                file_size = len(contents)
                await image_file.seek(0)
                
                if file_size > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"حجم عکس شماره {idx + 1} بیش از حد مجاز است",
                    )
                
                # Check file extension
                file_ext = os.path.splitext(image_file.filename)[1].lower() if image_file.filename else '.jpg'
                if file_ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"نوع فایل عکس شماره {idx + 1} مجاز نیست. فقط فایل‌های تصویری مجاز هستند",
                    )
                
                # Save file
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                safe_filename = f"{product.code}_{timestamp}_{current_images_count + idx}{file_ext}"
                file_path = os.path.join(product_upload_dir, safe_filename)
                
                with open(file_path, "wb") as f:
                    f.write(contents)
                
                # Create ProductImage record
                relative_path = f"/uploads/products/{safe_filename}"
                product_image = models.ProductImage(
                    product_id=product.id,
                    image_url=relative_path
                )
                db.add(product_image)
            except HTTPException:
                raise
            except Exception as e:
                # If image processing fails, log and continue
                print(f"Error processing image {idx + 1}: {e}")
                continue
    
    await db.commit()
    
    # Reload product with images using selectinload to ensure relationship is loaded
    result = await db.execute(
        select(models.Product)
        .options(selectinload(models.Product.images))
        .where(models.Product.id == product.id)
    )
    product_with_images = result.scalars().unique().first()
    
    # Convert to response format with images
    product_dict = {
        'id': product_with_images.id,
        'code': product_with_images.code,
        'name': product_with_images.name,
        'description': product_with_images.description,
        'category': product_with_images.category,
        'unit': product_with_images.unit,
        'quantity_available': product_with_images.quantity_available,
        'colors': product_with_images.colors,
        'created_at': product_with_images.created_at,
        'updated_at': product_with_images.updated_at,
        'images': [img.image_url for img in product_with_images.images] if product_with_images.images else []
    }
    
    return schemas.Product(**product_dict)


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
    result = await db.execute(
        select(models.Product)
        .options(selectinload(models.Product.images))
        .where(models.Product.id == product_id)
    )
    product = result.scalars().unique().first()
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
    
    # Delete image files before deleting product (cascade will handle ProductImage records)
    if product.images:
        for img in product.images:
            if img.image_url:
                file_path_parts = img.image_url.lstrip("/").split("/")
                if len(file_path_parts) >= 3 and file_path_parts[0] == "uploads" and file_path_parts[1] == "products":
                    filename = "/".join(file_path_parts[2:])
                    full_path = os.path.join(settings.UPLOADS_DIR, "products", filename)
                    if os.path.exists(full_path) and os.path.isfile(full_path):
                        try:
                            os.remove(full_path)
                        except Exception as e:
                            print(f"Error deleting image file: {e}")
    
    # Convert to response format with images before deleting
    product_dict = {
        'id': product.id,
        'code': product.code,
        'name': product.name,
        'description': product.description,
        'category': product.category,
        'unit': product.unit,
        'quantity_available': product.quantity_available,
        'colors': product.colors,
        'created_at': product.created_at,
        'updated_at': product.updated_at,
        'images': [img.image_url for img in product.images] if product.images else []
    }
    
    await db.delete(product)
    await db.commit()
    
    return schemas.Product(**product_dict)

