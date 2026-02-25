import os
import json
from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.api import deps
from app.core.config import settings
from app.db.session import get_db

router = APIRouter()

# ==================== Organization Members ====================

@router.get("/members", response_model=List[schemas.OrganizationMember])
async def get_members(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """دریافت لیست اعضای سازمان"""
    result = await db.execute(select(models.OrganizationMember).offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/members", response_model=schemas.OrganizationMember, status_code=status.HTTP_201_CREATED)
async def create_member(
    *,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    full_name: str = Form(...),
    duty: str = Form(...),
    current_user: models.User = Depends(deps.get_current_admin_or_content_manager_user),
) -> Any:
    """ایجاد عضو جدید با آپلود عکس پروفایل"""
    contents = await file.read()
    await file.seek(0)
    
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="حجم فایل بیش از حد مجاز است")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="فرمت فایل مجاز نیست")
    
    member_dir = os.path.join(settings.UPLOADS_DIR, "members")
    os.makedirs(member_dir, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path = os.path.join(member_dir, filename)
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    image_url = f"/uploads/members/{filename}"
    member = models.OrganizationMember(
        full_name=full_name,
        duty=duty,
        profile_image_url=image_url
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member

@router.put("/members/{member_id}", response_model=schemas.OrganizationMember)
async def update_member(
    member_id: int,
    member_in: schemas.OrganizationMemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_content_manager_user),
) -> Any:
    """به‌روزرسانی اطلاعات عضو"""
    result = await db.execute(select(models.OrganizationMember).where(models.OrganizationMember.id == member_id))
    member = result.scalars().first()
    if not member:
        raise HTTPException(status_code=404, detail="عضو یافت نشد")
    
    update_data = member_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(member, field, value)
    
    await db.commit()
    await db.refresh(member)
    return member

@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_content_manager_user),
) -> None:
    """حذف عضو"""
    result = await db.execute(select(models.OrganizationMember).where(models.OrganizationMember.id == member_id))
    member = result.scalars().first()
    if not member:
        raise HTTPException(status_code=404, detail="عضو یافت نشد")
    
    if member.profile_image_url:
        file_path = os.path.join(settings.UPLOADS_DIR, member.profile_image_url.replace("/uploads/", ""))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
            
    await db.delete(member)
    await db.commit()

# ==================== Content Videos ====================

@router.get("/videos", response_model=List[schemas.ContentVideo])
async def get_videos(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """دریافت لیست ویدیوها"""
    result = await db.execute(select(models.ContentVideo).offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/videos", response_model=schemas.ContentVideo, status_code=status.HTTP_201_CREATED)
async def create_video(
    *,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: models.User = Depends(deps.get_current_admin_or_content_manager_user),
) -> Any:
    """آپلود ویدیو جدید"""
    contents = await file.read()
    await file.seek(0)
    
    # Allow larger size for videos (100MB)
    if len(contents) > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="حجم ویدیو بیش از حد مجاز (100MB) است")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".mp4", ".mov", ".avi", ".mkv"]:
        raise HTTPException(status_code=400, detail="فرمت ویدیو مجاز نیست")
    
    video_dir = os.path.join(settings.UPLOADS_DIR, "videos")
    os.makedirs(video_dir, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path = os.path.join(video_dir, filename)
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    video_url = f"/uploads/videos/{filename}"
    video = models.ContentVideo(
        title=title,
        description=description,
        video_url=video_url
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video

@router.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_content_manager_user),
) -> None:
    """حذف ویدیو"""
    result = await db.execute(select(models.ContentVideo).where(models.ContentVideo.id == video_id))
    video = result.scalars().first()
    if not video:
        raise HTTPException(status_code=404, detail="ویدیو یافت نشد")
    
    if video.video_url:
        file_path = os.path.join(settings.UPLOADS_DIR, video.video_url.replace("/uploads/", ""))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
            
    await db.delete(video)
    await db.commit()

# ==================== Campaigns ====================

@router.get("/campaigns", response_model=List[schemas.Campaign])
async def get_campaigns(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """دریافت لیست کمپین‌ها"""
    result = await db.execute(
        select(models.Campaign)
        .options(selectinload(models.Campaign.products))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

@router.post("/campaigns", response_model=schemas.Campaign, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    *,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    product_ids: str = Form("[]"),
    current_user: models.User = Depends(deps.get_current_admin_or_content_manager_user),
) -> Any:
    """ایجاد کمپین جدید با انتخاب محصولات"""
    try:
        ids = json.loads(product_ids)
    except:
        ids = []
        
    contents = await file.read()
    await file.seek(0)
    
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="حجم فایل بنر بیش از حد مجاز است")
    
    campaign_dir = os.path.join(settings.UPLOADS_DIR, "campaigns")
    os.makedirs(campaign_dir, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path = os.path.join(campaign_dir, filename)
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    banner_url = f"/uploads/campaigns/{filename}"
    
    # Get products
    result = await db.execute(select(models.Product).where(models.Product.id.in_(ids)))
    products = result.scalars().all()
    
    campaign = models.Campaign(
        title=title,
        description=description,
        banner_url=banner_url,
        products=products
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    result = await db.execute(
        select(models.Campaign)
        .options(selectinload(models.Campaign.products))
        .where(models.Campaign.id == campaign.id)
    )
    campaign_loaded = result.scalars().first()
    return campaign_loaded

# ==================== Site Info Settings ====================

@router.post("/site-info", status_code=status.HTTP_201_CREATED)
async def upsert_site_info(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_content_manager_user),
    about_us: Optional[str] = Form(None),
    satisfied_customers: Optional[str] = Form(None),
    product_info: Optional[str] = Form(None),
    experience_years: Optional[str] = Form(None),
    buy_guide_1: Optional[str] = Form(None),
    buy_guide_2: Optional[str] = Form(None),
    buy_guide_3: Optional[str] = Form(None),
    buy_guide_4: Optional[str] = Form(None),
    phone_1: Optional[str] = Form(None),
    phone_2: Optional[str] = Form(None),
    phone_3: Optional[str] = Form(None),
    phone_4: Optional[str] = Form(None),
    phone_5: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    working_hours: Optional[str] = Form(None),
    about_rans_text_2: Optional[str] = Form(None),
    fabric_variety_count: Optional[str] = Form(None),
    satisfied_customers_count: Optional[str] = Form(None),
    our_mission: Optional[str] = Form(None),
    our_vision: Optional[str] = Form(None),
    our_history_1: Optional[str] = Form(None),
    our_history_2: Optional[str] = Form(None),
    our_history_3: Optional[str] = Form(None),
    our_history_4: Optional[str] = Form(None),
    our_history_5: Optional[str] = Form(None),
    instagram_link: Optional[str] = Form(None),
    whatsapp_link: Optional[str] = Form(None),
    telegram_link: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
) -> Any:
    pairs = {
        "about_us": about_us,
        "satisfied_customers": satisfied_customers,
        "product_info": product_info,
        "experience_years": experience_years,
        "buy_guide_1": buy_guide_1,
        "buy_guide_2": buy_guide_2,
        "buy_guide_3": buy_guide_3,
        "buy_guide_4": buy_guide_4,
        "phone_1": phone_1,
        "phone_2": phone_2,
        "phone_3": phone_3,
        "phone_4": phone_4,
        "phone_5": phone_5,
        "address": address,
        "working_hours": working_hours,
        "about_rans_text_2": about_rans_text_2,
        "fabric_variety_count": fabric_variety_count,
        "satisfied_customers_count": satisfied_customers_count,
        "our_mission": our_mission,
        "our_vision": our_vision,
        "our_history_1": our_history_1,
        "our_history_2": our_history_2,
        "our_history_3": our_history_3,
        "our_history_4": our_history_4,
        "our_history_5": our_history_5,
        "instagram_link": instagram_link,
        "whatsapp_link": whatsapp_link,
        "telegram_link": telegram_link,
        "email": email,
    }
    updated_keys = []
    for key, value in pairs.items():
        if value is None:
            continue
        result = await db.execute(select(models.SiteSettings).where(models.SiteSettings.key == key))
        setting = result.scalars().first()
        if setting:
            setting.value = value
        else:
            db.add(models.SiteSettings(key=key, value=value))
        updated_keys.append(key)
    await db.commit()
    return {"updated": updated_keys}

@router.get("/site-info")
async def get_site_info(
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(models.SiteSettings))
    rows = result.scalars().all()
    return {row.key: row.value for row in rows}

@router.put("/site-info")
async def update_site_info(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_content_manager_user),
    about_us: Optional[str] = Form(None),
    satisfied_customers: Optional[str] = Form(None),
    product_info: Optional[str] = Form(None),
    experience_years: Optional[str] = Form(None),
    buy_guide_1: Optional[str] = Form(None),
    buy_guide_2: Optional[str] = Form(None),
    buy_guide_3: Optional[str] = Form(None),
    buy_guide_4: Optional[str] = Form(None),
    phone_1: Optional[str] = Form(None),
    phone_2: Optional[str] = Form(None),
    phone_3: Optional[str] = Form(None),
    phone_4: Optional[str] = Form(None),
    phone_5: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    working_hours: Optional[str] = Form(None),
    about_rans_text_2: Optional[str] = Form(None),
    fabric_variety_count: Optional[str] = Form(None),
    satisfied_customers_count: Optional[str] = Form(None),
    our_mission: Optional[str] = Form(None),
    our_vision: Optional[str] = Form(None),
    our_history_1: Optional[str] = Form(None),
    our_history_2: Optional[str] = Form(None),
    our_history_3: Optional[str] = Form(None),
    our_history_4: Optional[str] = Form(None),
    our_history_5: Optional[str] = Form(None),
    instagram_link: Optional[str] = Form(None),
    whatsapp_link: Optional[str] = Form(None),
    telegram_link: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
) -> Any:
    pairs = {
        "about_us": about_us,
        "satisfied_customers": satisfied_customers,
        "product_info": product_info,
        "experience_years": experience_years,
        "buy_guide_1": buy_guide_1,
        "buy_guide_2": buy_guide_2,
        "buy_guide_3": buy_guide_3,
        "buy_guide_4": buy_guide_4,
        "phone_1": phone_1,
        "phone_2": phone_2,
        "phone_3": phone_3,
        "phone_4": phone_4,
        "phone_5": phone_5,
        "address": address,
        "working_hours": working_hours,
        "about_rans_text_2": about_rans_text_2,
        "fabric_variety_count": fabric_variety_count,
        "satisfied_customers_count": satisfied_customers_count,
        "our_mission": our_mission,
        "our_vision": our_vision,
        "our_history_1": our_history_1,
        "our_history_2": our_history_2,
        "our_history_3": our_history_3,
        "our_history_4": our_history_4,
        "our_history_5": our_history_5,
        "instagram_link": instagram_link,
        "whatsapp_link": whatsapp_link,
        "telegram_link": telegram_link,
        "email": email,
    }
    updated_keys = []
    for key, value in pairs.items():
        if value is None:
            continue
        result = await db.execute(select(models.SiteSettings).where(models.SiteSettings.key == key))
        setting = result.scalars().first()
        if setting:
            setting.value = value
        else:
            db.add(models.SiteSettings(key=key, value=value))
        updated_keys.append(key)
    await db.commit()
    return {"updated": updated_keys}

@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_content_manager_user),
) -> None:
    """حذف کمپین"""
    result = await db.execute(select(models.Campaign).where(models.Campaign.id == campaign_id))
    campaign = result.scalars().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="کمپین یافت نشد")
    
    if campaign.banner_url:
        file_path = os.path.join(settings.UPLOADS_DIR, campaign.banner_url.replace("/uploads/", ""))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
            
    await db.delete(campaign)
    await db.commit()
