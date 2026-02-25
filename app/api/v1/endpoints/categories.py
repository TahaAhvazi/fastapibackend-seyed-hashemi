from typing import Any, List, Optional
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import models, schemas
from app.api import deps
from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.get("/", response_model=List[schemas.Category])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    visible: Optional[bool] = None,
) -> Any:
    query = select(models.Category)
    if visible is not None:
        query = query.where(models.Category.visible == visible)
    result = await db.execute(query)
    categories = result.scalars().all()
    return categories


@router.post("/", response_model=schemas.Category)
async def create_category(
    *,
    db: AsyncSession = Depends(get_db),
    name: str = Form(..., min_length=1, description="نام دسته‌بندی"),
    description: Optional[str] = Form(None, description="توضیحات"),
    visible: bool = Form(default=True, description="قابل نمایش در سایت"),
    image: Optional[UploadFile] = File(None, description="عکس دسته‌بندی"),
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_or_content_manager_user),
) -> Any:
    existing = await db.execute(select(models.Category).where(models.Category.name == name))
    if existing.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="دسته‌بندی با این نام وجود دارد")

    image_url: Optional[str] = None
    if image:
        category_upload_dir = os.path.join(settings.UPLOADS_DIR, "categories")
        os.makedirs(category_upload_dir, exist_ok=True)
        contents = await image.read()
        await image.seek(0)
        file_ext = os.path.splitext(image.filename)[1].lower() if image.filename else ".jpg"
        if file_ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="نوع فایل تصویر مجاز نیست")
        if len(contents) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="حجم تصویر بیش از حد مجاز است")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        safe_filename = f"cat_{timestamp}{file_ext}"
        file_path = os.path.join(category_upload_dir, safe_filename)
        with open(file_path, "wb") as f:
            f.write(contents)
        image_url = f"/uploads/categories/{safe_filename}"

    category = models.Category(
        name=name,
        description=description,
        visible=visible,
        image_url=image_url,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.put("/{category_id}", response_model=schemas.Category)
async def update_category(
    *,
    db: AsyncSession = Depends(get_db),
    category_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    visible: Optional[bool] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_or_content_manager_user),
) -> Any:
    result = await db.execute(select(models.Category).where(models.Category.id == category_id))
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="دسته‌بندی یافت نشد")

    if name is not None:
        # unique check
        existing = await db.execute(select(models.Category).where(models.Category.name == name, models.Category.id != category_id))
        if existing.scalars().first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="نام دسته‌بندی تکراری است")
        category.name = name
    if description is not None:
        category.description = description
    if visible is not None:
        category.visible = visible

    if image:
        # delete old file if exists
        if category.image_url:
            parts = category.image_url.lstrip("/").split("/")
            if len(parts) >= 3 and parts[0] == "uploads" and parts[1] == "categories":
                filename = "/".join(parts[2:])
                full_path = os.path.join(settings.UPLOADS_DIR, "categories", filename)
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    try:
                        os.remove(full_path)
                    except Exception as e:
                        print(f"Error deleting category image file: {e}")
        # save new
        category_upload_dir = os.path.join(settings.UPLOADS_DIR, "categories")
        os.makedirs(category_upload_dir, exist_ok=True)
        contents = await image.read()
        await image.seek(0)
        file_ext = os.path.splitext(image.filename)[1].lower() if image.filename else ".jpg"
        if file_ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="نوع فایل تصویر مجاز نیست")
        if len(contents) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="حجم تصویر بیش از حد مجاز است")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        safe_filename = f"cat_{timestamp}{file_ext}"
        file_path = os.path.join(category_upload_dir, safe_filename)
        with open(file_path, "wb") as f:
            f.write(contents)
        category.image_url = f"/uploads/categories/{safe_filename}"

    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_200_OK)
async def delete_category(
    *,
    db: AsyncSession = Depends(get_db),
    category_id: int,
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_or_content_manager_user),
) -> Any:
    result = await db.execute(select(models.Category).where(models.Category.id == category_id))
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="دسته‌بندی یافت نشد")
    # delete file if exists
    if category.image_url:
        parts = category.image_url.lstrip("/").split("/")
        if len(parts) >= 3 and parts[0] == "uploads" and parts[1] == "categories":
            filename = "/".join(parts[2:])
            full_path = os.path.join(settings.UPLOADS_DIR, "categories", filename)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    print(f"Error deleting category image file: {e}")
    await db.delete(category)
    await db.commit()
    return {"detail": "deleted"}


