import os
from typing import Any, List, Optional
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app import models, schemas
from app.api import deps
from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


# ==================== Slider Management ====================

@router.get("/sliders", response_model=List[schemas.Slider])
async def get_sliders(
    db: AsyncSession = Depends(get_db),
    is_active: Optional[bool] = None,
) -> Any:
    """
    دریافت لیست اسلایدرها
    Get list of sliders
    """
    query = select(models.Slider)
    
    if is_active is not None:
        query = query.where(models.Slider.is_active == is_active)
    
    query = query.order_by(models.Slider.display_order, models.Slider.created_at.desc())
    result = await db.execute(query)
    sliders = result.scalars().all()
    return sliders


@router.post("/sliders", response_model=schemas.Slider, status_code=status.HTTP_201_CREATED)
async def create_slider(
    *,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    link: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_active: bool = Form(True),
    display_order: int = Form(0),
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    ایجاد اسلایدر جدید با آپلود عکس
    Create new slider with image upload
    """
    # Check file size
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="حجم فایل بیش از حد مجاز است",
        )
    
    # Check file extension (only images)
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_image_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
    if file_ext not in allowed_image_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فقط فایل‌های تصویری مجاز هستند",
        )
    
    # Create slider directory
    slider_dir = os.path.join(settings.UPLOADS_DIR, "slider")
    os.makedirs(slider_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(slider_dir, safe_filename)
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Create slider record
    image_url = f"/uploads/slider/{safe_filename}"
    slider = models.Slider(
        title=title,
        image_url=image_url,
        link=link,
        description=description,
        is_active=is_active,
        display_order=display_order,
    )
    db.add(slider)
    await db.commit()
    await db.refresh(slider)
    return slider


@router.put("/sliders/{slider_id}", response_model=schemas.Slider)
async def update_slider(
    *,
    slider_id: int,
    db: AsyncSession = Depends(get_db),
    slider_in: schemas.SliderUpdate,
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    به‌روزرسانی اسلایدر
    Update slider
    """
    result = await db.execute(select(models.Slider).where(models.Slider.id == slider_id))
    slider = result.scalars().first()
    if not slider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="اسلایدر یافت نشد",
        )
    
    update_data = slider_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(slider, field, value)
    
    await db.commit()
    await db.refresh(slider)
    return slider


@router.put("/sliders/{slider_id}/image", response_model=schemas.Slider)
async def update_slider_image(
    *,
    slider_id: int,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    به‌روزرسانی عکس اسلایدر
    Update slider image
    """
    result = await db.execute(select(models.Slider).where(models.Slider.id == slider_id))
    slider = result.scalars().first()
    if not slider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="اسلایدر یافت نشد",
        )
    
    # Check file size
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="حجم فایل بیش از حد مجاز است",
        )
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_image_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
    if file_ext not in allowed_image_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فقط فایل‌های تصویری مجاز هستند",
        )
    
    # Delete old image if exists
    if slider.image_url:
        old_file_path = os.path.join(settings.UPLOADS_DIR, slider.image_url.replace("/uploads/", ""))
        if os.path.exists(old_file_path):
            try:
                os.remove(old_file_path)
            except Exception as e:
                print(f"Error deleting old image: {e}")
    
    # Create slider directory
    slider_dir = os.path.join(settings.UPLOADS_DIR, "slider")
    os.makedirs(slider_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(slider_dir, safe_filename)
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Update slider
    slider.image_url = f"/uploads/slider/{safe_filename}"
    await db.commit()
    await db.refresh(slider)
    return slider


@router.delete("/sliders/{slider_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_slider(
    *,
    slider_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> None:
    """
    حذف اسلایدر
    Delete slider
    """
    result = await db.execute(select(models.Slider).where(models.Slider.id == slider_id))
    slider = result.scalars().first()
    if not slider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="اسلایدر یافت نشد",
        )
    
    # Delete image file
    if slider.image_url:
        file_path = os.path.join(settings.UPLOADS_DIR, slider.image_url.replace("/uploads/", ""))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error deleting image file: {e}")
    
    await db.delete(slider)
    await db.commit()


# ==================== Article Management ====================

@router.get("/articles", response_model=List[schemas.Article])
async def get_articles(
    db: AsyncSession = Depends(get_db),
    is_published: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    دریافت لیست مقالات
    Get list of articles
    """
    query = select(models.Article)
    
    if is_published is not None:
        query = query.where(models.Article.is_published == is_published)
    
    query = query.order_by(desc(models.Article.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    articles = result.scalars().all()
    return articles


@router.post("/articles", response_model=schemas.Article, status_code=status.HTTP_201_CREATED)
async def create_article(
    *,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    slug: str = Form(...),
    content: str = Form(...),
    excerpt: Optional[str] = Form(None),
    is_published: bool = Form(False),
    cover_image: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(deps.get_current_admin_or_content_manager_user),
) -> Any:
    """
    ایجاد مقاله جدید
    Create new article
    """
    # Check if slug already exists
    result = await db.execute(select(models.Article).where(models.Article.slug == slug))
    existing_article = result.scalars().first()
    if existing_article:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="مقاله‌ای با این slug قبلاً ثبت شده است",
        )
    
    cover_image_url = None
    
    # Handle cover image upload if provided
    if cover_image:
        contents = await cover_image.read()
        file_size = len(contents)
        await cover_image.seek(0)
        
        if file_size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="حجم فایل بیش از حد مجاز است",
            )
        
        # Check file extension
        file_ext = os.path.splitext(cover_image.filename)[1].lower()
        allowed_image_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
        if file_ext not in allowed_image_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فقط فایل‌های تصویری مجاز هستند",
            )
        
        # Create articles directory
        articles_dir = os.path.join(settings.UPLOADS_DIR, "articles")
        os.makedirs(articles_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{cover_image.filename}"
        file_path = os.path.join(articles_dir, safe_filename)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(contents)
        
        cover_image_url = f"/uploads/articles/{safe_filename}"
    
    # Create article
    article = models.Article(
        title=title,
        slug=slug,
        content=content,
        excerpt=excerpt,
        cover_image_url=cover_image_url,
        is_published=is_published,
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article


@router.get("/articles/{article_id}", response_model=schemas.Article)
async def get_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    دریافت مقاله با ID
    Get article by ID
    """
    result = await db.execute(select(models.Article).where(models.Article.id == article_id))
    article = result.scalars().first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مقاله یافت نشد",
        )
    
    # Increment views count
    article.views_count += 1
    await db.commit()
    await db.refresh(article)
    return article


@router.get("/articles/slug/{slug}", response_model=schemas.Article)
async def get_article_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    دریافت مقاله با slug
    Get article by slug
    """
    result = await db.execute(select(models.Article).where(models.Article.slug == slug))
    article = result.scalars().first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مقاله یافت نشد",
        )
    
    # Increment views count
    article.views_count += 1
    await db.commit()
    await db.refresh(article)
    return article


@router.put("/articles/{article_id}", response_model=schemas.Article)
async def update_article(
    *,
    article_id: int,
    db: AsyncSession = Depends(get_db),
    title: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    excerpt: Optional[str] = Form(None),
    is_published: Optional[bool] = Form(None),
    cover_image: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(deps.get_current_admin_or_content_manager_user),
) -> Any:
    """
    به‌روزرسانی مقاله
    Update article
    """
    result = await db.execute(select(models.Article).where(models.Article.id == article_id))
    article = result.scalars().first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مقاله یافت نشد",
        )
    
    # Check slug uniqueness if changed
    if slug and slug != article.slug:
        result = await db.execute(select(models.Article).where(models.Article.slug == slug))
        existing_article = result.scalars().first()
        if existing_article:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="مقاله‌ای با این slug قبلاً ثبت شده است",
            )
        article.slug = slug
    
    # Update fields
    if title is not None:
        article.title = title
    if content is not None:
        article.content = content
    if excerpt is not None:
        article.excerpt = excerpt
    if is_published is not None:
        article.is_published = is_published
    
    # Handle cover image update if provided
    if cover_image:
        contents = await cover_image.read()
        file_size = len(contents)
        await cover_image.seek(0)
        
        if file_size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="حجم فایل بیش از حد مجاز است",
            )
        
        # Check file extension
        file_ext = os.path.splitext(cover_image.filename)[1].lower()
        allowed_image_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
        if file_ext not in allowed_image_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فقط فایل‌های تصویری مجاز هستند",
            )
        
        # Delete old cover image if exists
        if article.cover_image_url:
            old_file_path = os.path.join(settings.UPLOADS_DIR, article.cover_image_url.replace("/uploads/", ""))
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except Exception as e:
                    print(f"Error deleting old cover image: {e}")
        
        # Create articles directory
        articles_dir = os.path.join(settings.UPLOADS_DIR, "articles")
        os.makedirs(articles_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{cover_image.filename}"
        file_path = os.path.join(articles_dir, safe_filename)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(contents)
        
        article.cover_image_url = f"/uploads/articles/{safe_filename}"
    
    await db.commit()
    await db.refresh(article)
    return article


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_article(
    *,
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_content_manager_user),
) -> None:
    """
    حذف مقاله
    Delete article
    """
    result = await db.execute(select(models.Article).where(models.Article.id == article_id))
    article = result.scalars().first()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مقاله یافت نشد",
        )
    
    # Delete cover image if exists
    if article.cover_image_url:
        file_path = os.path.join(settings.UPLOADS_DIR, article.cover_image_url.replace("/uploads/", ""))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error deleting cover image: {e}")
    
    await db.delete(article)
    await db.commit()


# ==================== Main Picture Management ====================

MAIN_PICTURE_KEY = "main_picture"


@router.post("/main-picture", status_code=status.HTTP_201_CREATED)
async def upload_main_picture(
    *,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    آپلود عکس اصلی سایت
    Upload main picture
    """
    # Check file size
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="حجم فایل بیش از حد مجاز است",
        )
    
    # Check file extension (only images)
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_image_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
    if file_ext not in allowed_image_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فقط فایل‌های تصویری مجاز هستند",
        )
    
    # Create main-picture directory
    main_picture_dir = os.path.join(settings.UPLOADS_DIR, "main-picture")
    os.makedirs(main_picture_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(main_picture_dir, safe_filename)
    
    # Check if main picture already exists
    result = await db.execute(
        select(models.SiteSettings).where(models.SiteSettings.key == MAIN_PICTURE_KEY)
    )
    existing_setting = result.scalars().first()
    
    # Delete old image if exists
    if existing_setting and existing_setting.value:
        old_file_path = os.path.join(settings.UPLOADS_DIR, existing_setting.value.replace("/uploads/", ""))
        if os.path.exists(old_file_path):
            try:
                os.remove(old_file_path)
            except Exception as e:
                print(f"Error deleting old main picture: {e}")
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Save or update setting
    image_url = f"/uploads/main-picture/{safe_filename}"
    if existing_setting:
        existing_setting.value = image_url
        await db.commit()
        await db.refresh(existing_setting)
        return {"message": "عکس اصلی با موفقیت به‌روزرسانی شد", "image_url": image_url}
    else:
        new_setting = models.SiteSettings(key=MAIN_PICTURE_KEY, value=image_url)
        db.add(new_setting)
        await db.commit()
        await db.refresh(new_setting)
        return {"message": "عکس اصلی با موفقیت آپلود شد", "image_url": image_url}


@router.get("/main-picture")
async def get_main_picture(
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    دریافت عکس اصلی سایت
    Get main picture
    """
    result = await db.execute(
        select(models.SiteSettings).where(models.SiteSettings.key == MAIN_PICTURE_KEY)
    )
    setting = result.scalars().first()
    
    if not setting or not setting.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="عکس اصلی یافت نشد",
        )
    
    return {"image_url": setting.value}


@router.delete("/main-picture", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_main_picture(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> None:
    """
    حذف عکس اصلی سایت
    Delete main picture
    """
    result = await db.execute(
        select(models.SiteSettings).where(models.SiteSettings.key == MAIN_PICTURE_KEY)
    )
    setting = result.scalars().first()
    
    if not setting or not setting.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="عکس اصلی یافت نشد",
        )
    
    # Delete image file
    file_path = os.path.join(settings.UPLOADS_DIR, setting.value.replace("/uploads/", ""))
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error deleting main picture file: {e}")
    
    # Delete setting
    await db.delete(setting)
    await db.commit()

