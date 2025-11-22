from typing import Any, List, Optional
import os
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form, Response
from sqlalchemy import or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.api import deps
from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.post("/{product_id}/images", response_model=schemas.Product)
async def add_product_images(
    *,
    db: AsyncSession = Depends(get_db),
    product_id: int,
    images: List[UploadFile] = File(..., description="عکس‌های جدید محصول"),
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    افزودن عکس جدید به یک محصول (admin/warehouse)
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
            detail="محصول یافت نشد",
        )

    product_upload_dir = os.path.join(settings.UPLOADS_DIR, "products")
    os.makedirs(product_upload_dir, exist_ok=True)

    current_images_count = len(product.images) if product.images else 0

    for idx, image_file in enumerate(images):
        try:
            contents = await image_file.read()
            await image_file.seek(0)

            file_ext = os.path.splitext(image_file.filename)[1].lower() if image_file.filename else '.jpg'
            if file_ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"نوع فایل عکس شماره {idx + 1} مجاز نیست. فقط فایل‌های تصویری مجاز هستند",
                )

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            safe_filename = f"{product.code}_{timestamp}_{current_images_count + idx}{file_ext}"
            file_path = os.path.join(product_upload_dir, safe_filename)
            with open(file_path, "wb") as f:
                f.write(contents)

            relative_path = f"/uploads/products/{safe_filename}"
            product_image = models.ProductImage(
                product_id=product.id,
                image_url=relative_path
            )
            db.add(product_image)
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error processing image {idx + 1}: {e}")
            continue

    await db.commit()

    # Reload with images
    result = await db.execute(
        select(models.Product)
        .options(selectinload(models.Product.images))
        .where(models.Product.id == product_id)
    )
    product_with_images = result.scalars().unique().first()

    product_dict = {
        'id': product_with_images.id,
        'code': product_with_images.code,
        'name': product_with_images.name,
        'description': product_with_images.description,
        'category': product_with_images.category,
        'unit': product_with_images.unit,
        'colors': product_with_images.colors,
        'is_series': product_with_images.is_series,
        'series_inventory': product_with_images.series_inventory,
        'series_numbers': product_with_images.series_numbers,
        'available_colors': product_with_images.available_colors,
        'color_inventory': product_with_images.color_inventory,
        'created_at': product_with_images.created_at,
        'updated_at': product_with_images.updated_at,
        'images': [img.image_url for img in product_with_images.images] if product_with_images.images else []
    }
    return schemas.Product(**product_dict)


@router.delete("/{product_id}/images/{image_id}", status_code=status.HTTP_200_OK)
async def delete_product_image(
    *,
    db: AsyncSession = Depends(get_db),
    product_id: int,
    image_id: int,
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    حذف یک عکس از محصول (admin/warehouse) + حذف فایل از دیسک
    نکته: پارامتر image_id هم می‌تواند شناسه رکورد عکس باشد و هم ایندکس عکس برای همان محصول (۰ مبنا).
    """
    # Ensure product exists
    product_result = await db.execute(
        select(models.Product).where(models.Product.id == product_id)
    )
    product = product_result.scalars().first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="محصول یافت نشد")

    # Load image by id and validate ownership
    image_result_by_id = await db.execute(
        select(models.ProductImage).where(
            models.ProductImage.id == image_id,
            models.ProductImage.product_id == product_id,
        )
    )
    image = image_result_by_id.scalars().first()

    # If not found by id, try treating image_id as index (0-based) among product images ordered by id
    if not image:
        images_list_result = await db.execute(
            select(models.ProductImage).where(
                models.ProductImage.product_id == product_id
            ).order_by(models.ProductImage.id.asc())
        )
        images_list = images_list_result.scalars().all()
        if 0 <= image_id < len(images_list):
            image = images_list[image_id]

    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="عکس موردنظر یافت نشد")

    # Delete file from disk if exists
    if image.image_url:
        parts = image.image_url.lstrip("/").split("/")
        if len(parts) >= 3 and parts[0] == "uploads" and parts[1] == "products":
            filename = "/".join(parts[2:])
            full_path = os.path.join(settings.UPLOADS_DIR, "products", filename)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    # لاگ خطا ولی ادامه حذف رکورد
                    print(f"Error deleting image file: {e}")

    await db.delete(image)
    await db.commit()
    return {"detail": "deleted"}
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
        filters.append(models.Product.is_available == in_stock)
    
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
            'is_available': product.is_available,
            'shrinkage': product.shrinkage,
            'visible': product.visible,
            'width': product.width,
            'usage': product.usage,
            'season': product.season,
            'weave_type': product.weave_type,
            'colors': product.colors,
            'is_series': product.is_series,
            'series_inventory': product.series_inventory,
            'series_numbers': product.series_numbers,
            'available_colors': product.available_colors,
            'color_inventory': product.color_inventory,
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
    is_available: bool = Form(default=True, description="موجود است؟"),
    description: Optional[str] = Form(None, description="توضیحات محصول"),
    colors: Optional[str] = Form(None, description="رنگ‌ها"),
    shrinkage: Optional[str] = Form(None, description="ابرِفت"),
    visible: bool = Form(default=True, description="نمایش در سایت"),
    width: Optional[str] = Form(None, description="عرض"),
    usage: Optional[str] = Form(None, description="کاربرد"),
    season: Optional[str] = Form(None, description="فصل"),
    weave_type: Optional[str] = Form(None, description="نوع بافت"),
    is_series: bool = Form(default=False, description="آیا محصول سری است؟"),
    series_inventory: Optional[str] = Form(None, description="لیست موجودی سری (JSON string، مثلاً [10, 20, 30])"),
    series_numbers: Optional[str] = Form(None, description="لیست شماره‌های سری (JSON string، مثلاً [1, 2, 3, ..., 10])"),
    available_colors: Optional[str] = Form(None, description="لیست رنگ‌های موجود (JSON string، مثلاً [\"قرمز\", \"آبی\", \"سبز\"])"),
    color_inventory: Optional[str] = Form(None, description="لیست موجودی هر رنگ (JSON string، مثلاً [\"5\", \"10\", \"3\"])"),
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
    
    # Parse JSON strings for list fields
    series_inventory_list = None
    series_numbers_list = None
    available_colors_list = None
    color_inventory_list = None
    
    if series_inventory:
        try:
            series_inventory_list = json.loads(series_inventory)
            if not isinstance(series_inventory_list, list):
                raise ValueError("series_inventory must be a list")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"فرمت series_inventory نامعتبر است: {str(e)}"
            )
    
    if series_numbers:
        try:
            series_numbers_list = json.loads(series_numbers)
            if not isinstance(series_numbers_list, list):
                raise ValueError("series_numbers must be a list")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"فرمت series_numbers نامعتبر است: {str(e)}"
            )
    
    if available_colors:
        try:
            available_colors_list = json.loads(available_colors)
            if not isinstance(available_colors_list, list):
                raise ValueError("available_colors must be a list")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"فرمت available_colors نامعتبر است: {str(e)}"
            )
    
    if color_inventory:
        try:
            color_inventory_list = json.loads(color_inventory)
            if not isinstance(color_inventory_list, list):
                raise ValueError("color_inventory must be a list")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"فرمت color_inventory نامعتبر است: {str(e)}"
            )
    
    # Validate: if is_series is True, series fields should be provided
    if is_series:
        if not series_inventory_list or not series_numbers_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="برای محصولات سری، series_inventory و series_numbers الزامی هستند"
            )
    else:
        # For non-series products, color fields should be provided
        if available_colors_list and color_inventory_list:
            if len(available_colors_list) != len(color_inventory_list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="تعداد رنگ‌ها باید با تعداد موجودی هر رنگ برابر باشد"
                )
    
    # Create new product
    product = models.Product(
        code=code,
        name=name,
        category=category,
        unit=unit,
        is_available=is_available,
        description=description,
        colors=colors,
        shrinkage=shrinkage,
        visible=visible,
        width=width,
        usage=usage,
        season=season,
        weave_type=weave_type,
        is_series=is_series,
        series_inventory=series_inventory_list,
        series_numbers=series_numbers_list,
        available_colors=available_colors_list,
        color_inventory=color_inventory_list,
    )
    db.add(product)
    await db.flush()  # Flush to get the product ID
    
    # Process images if provided
    if images:
        product_upload_dir = os.path.join(settings.UPLOADS_DIR, "products")
        os.makedirs(product_upload_dir, exist_ok=True)
        
        for idx, image_file in enumerate(images):
            try:
                contents = await image_file.read()
                await image_file.seek(0)
                
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
        'is_available': product_with_images.is_available,
        'shrinkage': product_with_images.shrinkage,
        'visible': product_with_images.visible,
        'width': product_with_images.width,
        'usage': product_with_images.usage,
        'season': product_with_images.season,
        'weave_type': product_with_images.weave_type,
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
        'is_available': product.is_available,
        'shrinkage': product.shrinkage,
        'visible': product.visible,
        'width': product.width,
        'usage': product.usage,
        'season': product.season,
        'weave_type': product.weave_type,
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
    is_available: Optional[bool] = Form(None, description="موجود است؟"),
    description: Optional[str] = Form(None, description="توضیحات محصول"),
    colors: Optional[str] = Form(None, description="رنگ‌ها"),
    shrinkage: Optional[str] = Form(None, description="ابرِفت"),
    visible: Optional[bool] = Form(None, description="نمایش در سایت"),
    width: Optional[str] = Form(None, description="عرض"),
    usage: Optional[str] = Form(None, description="کاربرد"),
    season: Optional[str] = Form(None, description="فصل"),
    weave_type: Optional[str] = Form(None, description="نوع بافت"),
    is_series: Optional[bool] = Form(None, description="آیا محصول سری است؟"),
    series_inventory: Optional[str] = Form(None, description="لیست موجودی سری (JSON string، مثلاً [10, 20, 30])"),
    series_numbers: Optional[str] = Form(None, description="لیست شماره‌های سری (JSON string، مثلاً [1, 2, 3, ..., 10])"),
    available_colors: Optional[str] = Form(None, description="لیست رنگ‌های موجود (JSON string، مثلاً [\"قرمز\", \"آبی\", \"سبز\"])"),
    color_inventory: Optional[str] = Form(None, description="لیست موجودی هر رنگ (JSON string، مثلاً [\"5\", \"10\", \"3\"])"),
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
    if is_available is not None:
        product.is_available = is_available
    if description is not None:
        product.description = description
    if colors is not None:
        product.colors = colors
    if shrinkage is not None:
        product.shrinkage = shrinkage
    if visible is not None:
        product.visible = visible
    if width is not None:
        product.width = width
    if usage is not None:
        product.usage = usage
    if season is not None:
        product.season = season
    if weave_type is not None:
        product.weave_type = weave_type
    
    # Handle series and color fields
    if is_series is not None:
        product.is_series = is_series
    
    # Parse and update series fields
    if series_inventory is not None:
        try:
            series_inventory_list = json.loads(series_inventory)
            if not isinstance(series_inventory_list, list):
                raise ValueError("series_inventory must be a list")
            product.series_inventory = series_inventory_list
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"فرمت series_inventory نامعتبر است: {str(e)}"
            )
    
    if series_numbers is not None:
        try:
            series_numbers_list = json.loads(series_numbers)
            if not isinstance(series_numbers_list, list):
                raise ValueError("series_numbers must be a list")
            product.series_numbers = series_numbers_list
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"فرمت series_numbers نامعتبر است: {str(e)}"
            )
    
    if available_colors is not None:
        try:
            available_colors_list = json.loads(available_colors)
            if not isinstance(available_colors_list, list):
                raise ValueError("available_colors must be a list")
            product.available_colors = available_colors_list
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"فرمت available_colors نامعتبر است: {str(e)}"
            )
    
    if color_inventory is not None:
        try:
            color_inventory_list = json.loads(color_inventory)
            if not isinstance(color_inventory_list, list):
                raise ValueError("color_inventory must be a list")
            product.color_inventory = color_inventory_list
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"فرمت color_inventory نامعتبر است: {str(e)}"
            )
    
    # Validate: if is_series is True, series fields should be provided
    if product.is_series:
        if not product.series_inventory or not product.series_numbers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="برای محصولات سری، series_inventory و series_numbers الزامی هستند"
            )
    else:
        # For non-series products, validate color fields if provided
        if product.available_colors and product.color_inventory:
            if len(product.available_colors) != len(product.color_inventory):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="تعداد رنگ‌ها باید با تعداد موجودی هر رنگ برابر باشد"
                )
    
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
                contents = await image_file.read()
                await image_file.seek(0)
                
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
        'is_available': product_with_images.is_available,
        'shrinkage': product_with_images.shrinkage,
        'visible': product_with_images.visible,
        'width': product_with_images.width,
        'usage': product_with_images.usage,
        'season': product_with_images.season,
        'weave_type': product_with_images.weave_type,
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

    # Delete only the invoice items related to this product (not the invoices themselves)
    invoice_items_result = await db.execute(
        select(models.InvoiceItem).where(models.InvoiceItem.product_id == product_id)
    )
    invoice_items_to_delete = invoice_items_result.scalars().all()
    for invoice_item in invoice_items_to_delete:
        await db.delete(invoice_item)

    # Delete only the cart items related to this product (not the carts themselves)
    cart_items_result = await db.execute(
        select(models.CartItem).where(models.CartItem.product_id == product_id)
    )
    cart_items_to_delete = cart_items_result.scalars().all()
    for cart_item in cart_items_to_delete:
        await db.delete(cart_item)

    # Delete inventory transactions for this product
    inventory_result = await db.execute(
        select(models.InventoryTransaction).where(models.InventoryTransaction.product_id == product_id)
    )
    inventory_to_delete = inventory_result.scalars().all()
    for inv_tx in inventory_to_delete:
        await db.delete(inv_tx)
    
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
        'colors': product.colors,
        'created_at': product.created_at,
        'updated_at': product.updated_at,
        'images': [img.image_url for img in product.images] if product.images else []
    }
    
    await db.delete(product)
    await db.commit()
    
    return schemas.Product(**product_dict)

