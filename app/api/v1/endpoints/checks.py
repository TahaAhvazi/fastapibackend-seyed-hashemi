from typing import Any, List, Optional
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.api import deps
from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.get("/", response_model=List[schemas.Check])
async def read_checks(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[int] = None,
    status: Optional[schemas.CheckStatus] = None,
    due_date_from: Optional[str] = None,
    due_date_to: Optional[str] = None,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Retrieve checks with optional filtering
    """
    query = select(models.Check).options(
        selectinload(models.Check.customer),
        selectinload(models.Check.invoice),
        selectinload(models.Check.created_by_user)
    )
    
    # Apply filters
    if customer_id:
        query = query.where(models.Check.customer_id == customer_id)
    if status:
        query = query.where(models.Check.status == status)
    if due_date_from:
        query = query.where(models.Check.due_date >= due_date_from)
    if due_date_to:
        query = query.where(models.Check.due_date <= due_date_to)
    
    query = query.order_by(models.Check.due_date.asc()).offset(skip).limit(limit)
    result = await db.execute(query)
    checks = result.scalars().all()
    return checks


@router.post("/", response_model=schemas.Check)
async def create_check(
    *,
    db: AsyncSession = Depends(get_db),
    check_in: schemas.CheckCreate,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Create new check (admin or accountant only)
    """
    # Check if customer exists
    customer_result = await db.execute(select(models.Customer).where(models.Customer.id == check_in.customer_id))
    customer = customer_result.scalars().first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مشتری یافت نشد",  # Customer not found
        )
    
    # Check if invoice exists if provided
    if check_in.related_invoice_id:
        invoice_result = await db.execute(select(models.Invoice).where(models.Invoice.id == check_in.related_invoice_id))
        invoice = invoice_result.scalars().first()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="فاکتور یافت نشد",  # Invoice not found
            )
        
        # Check if invoice belongs to the same customer
        if invoice.customer_id != check_in.customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فاکتور متعلق به این مشتری نیست",  # Invoice does not belong to this customer
            )
    
    # Create check
    check = models.Check(
        check_number=check_in.check_number,
        customer_id=check_in.customer_id,
        amount=check_in.amount,
        issue_date=check_in.issue_date,
        due_date=check_in.due_date,
        status=check_in.status,
        related_invoice_id=check_in.related_invoice_id,
        created_by=current_user.id,
    )
    
    db.add(check)
    await db.commit()
    await db.refresh(check)
    return check


@router.get("/{check_id}", response_model=schemas.Check)
async def read_check(
    check_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Get a specific check by id
    """
    query = select(models.Check).options(
        selectinload(models.Check.customer),
        selectinload(models.Check.invoice),
        selectinload(models.Check.created_by_user)
    ).where(models.Check.id == check_id)
    
    result = await db.execute(query)
    check = result.scalars().first()
    
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="چک یافت نشد",  # Check not found
        )
    
    return check


@router.put("/{check_id}", response_model=schemas.Check)
async def update_check(
    *,
    db: AsyncSession = Depends(get_db),
    check_id: int,
    check_in: schemas.CheckUpdate,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Update a check (admin or accountant only)
    """
    result = await db.execute(select(models.Check).where(models.Check.id == check_id))
    check = result.scalars().first()
    
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="چک یافت نشد",  # Check not found
        )
    
    # Check if related invoice exists and belongs to the same customer if provided
    if check_in.related_invoice_id:
        invoice_result = await db.execute(select(models.Invoice).where(models.Invoice.id == check_in.related_invoice_id))
        invoice = invoice_result.scalars().first()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="فاکتور یافت نشد",  # Invoice not found
            )
        
        # Check if invoice belongs to the same customer
        if invoice.customer_id != check.customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فاکتور متعلق به این مشتری نیست",  # Invoice does not belong to this customer
            )
    
    # Update check fields
    update_data = check_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(check, field, value)
    
    db.add(check)
    await db.commit()
    await db.refresh(check)
    return check


@router.delete("/{check_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_check(
    *,
    db: AsyncSession = Depends(get_db),
    check_id: int,
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Delete a check (admin only)
    """
    result = await db.execute(select(models.Check).where(models.Check.id == check_id))
    check = result.scalars().first()
    
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="چک یافت نشد",  # Check not found
        )
    
    await db.delete(check)
    await db.commit()


@router.post("/{check_id}/status", response_model=schemas.Check)
async def update_check_status(
    *,
    db: AsyncSession = Depends(get_db),
    check_id: int,
    status: schemas.CheckStatus,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Update check status (admin or accountant only)
    """
    result = await db.execute(select(models.Check).where(models.Check.id == check_id))
    check = result.scalars().first()
    
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="چک یافت نشد",  # Check not found
        )
    
    check.status = status
    db.add(check)
    await db.commit()
    await db.refresh(check)
    return check


@router.post("/{check_id}/attachments")
async def add_check_attachment(
    *,
    db: AsyncSession = Depends(get_db),
    check_id: int,
    file: UploadFile = File(...),
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Add an attachment to a check
    """
    result = await db.execute(select(models.Check).where(models.Check.id == check_id))
    check = result.scalars().first()
    
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="چک یافت نشد",  # Check not found
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
            detail="نوع فایل مجاز نیست",  # File type not allowed
        )
    
    # Create uploads directory if it doesn't exist
    check_upload_dir = os.path.join(settings.UPLOADS_DIR, "checks", str(check_id))
    os.makedirs(check_upload_dir, exist_ok=True)
    
    # Save file
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(check_upload_dir, safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Update check attachments
    relative_path = f"/uploads/checks/{check_id}/{safe_filename}"
    
    if not check.attachments:
        check.attachments = [relative_path]
    else:
        attachments = check.attachments
        attachments.append(relative_path)
        check.attachments = attachments
    
    db.add(check)
    await db.commit()
    
    return {"filename": file.filename, "path": relative_path}