from typing import Any, List, Optional
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy import and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import json

from app import models, schemas
from app.api import deps
from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.get("/", response_model=List[schemas.Invoice])
async def read_invoices(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[int] = None,
    status: Optional[schemas.InvoiceStatus] = None,
    payment_type: Optional[schemas.PaymentType] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    created_by: Optional[int] = None,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve invoices with optional filtering
    """
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product),
        selectinload(models.Invoice.customer),
        selectinload(models.Invoice.created_by_user)
    )
    
    # Apply filters
    filters = []
    if customer_id:
        filters.append(models.Invoice.customer_id == customer_id)
    if status:
        filters.append(models.Invoice.status == status)
    if payment_type:
        filters.append(models.Invoice.payment_type == payment_type)
    if start_date:
        filters.append(models.Invoice.created_at >= start_date)
    if end_date:
        filters.append(models.Invoice.created_at <= end_date)
    if created_by:
        filters.append(models.Invoice.created_by == created_by)
    
    # Role-based filtering
    if current_user.role == schemas.UserRole.WAREHOUSE:
        # Warehouse users can only see pending, approved, and shipped invoices
        filters.append(models.Invoice.status.in_([
            schemas.InvoiceStatus.WAREHOUSE_PENDING,
            schemas.InvoiceStatus.APPROVED,
            schemas.InvoiceStatus.SHIPPED
        ]))
    elif current_user.role == schemas.UserRole.ACCOUNTANT:
        # Accountant users can see all invoices except draft
        filters.append(models.Invoice.status != schemas.InvoiceStatus.DRAFT)
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.order_by(models.Invoice.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    invoices = result.scalars().all()
    return invoices


@router.post("/", response_model=schemas.Invoice)
async def create_invoice(
    *,
    db: AsyncSession = Depends(get_db),
    invoice_in: schemas.InvoiceCreate,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Create new invoice (admin or accountant only)
    """
    # Check if customer exists
    customer_result = await db.execute(select(models.Customer).where(models.Customer.id == invoice_in.customer_id))
    customer = customer_result.scalars().first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مشتری یافت نشد",  # Customer not found
        )
    
    # Check if products exist and have enough stock
    for item in invoice_in.items:
        product_result = await db.execute(select(models.Product).where(models.Product.id == item.product_id))
        product = product_result.scalars().first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"محصول با شناسه {item.product_id} یافت نشد",  # Product with ID {item.product_id} not found
            )
        if product.quantity_available < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"موجودی محصول {product.name} کافی نیست",  # Not enough stock for product {product.name}
            )
    
    # Generate invoice number
    current_year = datetime.now().year
    persian_year = current_year - 621  # Approximate conversion to Persian year
    
    # Get the last invoice number for this year
    last_invoice_query = select(models.Invoice).where(
        models.Invoice.invoice_number.like(f"INV-{persian_year}-%")
    ).order_by(models.Invoice.invoice_number.desc())
    last_invoice_result = await db.execute(last_invoice_query)
    last_invoice = last_invoice_result.scalars().first()
    
    if last_invoice:
        last_number = int(last_invoice.invoice_number.split("-")[-1])
        new_number = last_number + 1
    else:
        new_number = 1
    
    invoice_number = f"INV-{persian_year}-{new_number:03d}"
    
    # Calculate subtotal and total
    subtotal = sum(item.quantity * item.price for item in invoice_in.items)
    total = subtotal  # No tax or discount for now
    
    # Create invoice
    invoice = models.Invoice(
        invoice_number=invoice_number,
        customer_id=invoice_in.customer_id,
        created_by=current_user.id,
        subtotal=subtotal,
        total=total,
        payment_type=invoice_in.payment_type,
        status=schemas.InvoiceStatus.WAREHOUSE_PENDING,
    )
    
    # Add payment breakdown for mixed payment type
    if invoice_in.payment_type == schemas.PaymentType.MIXED and invoice_in.payment_breakdown:
        invoice.payment_breakdown = invoice_in.payment_breakdown
    
    db.add(invoice)
    await db.flush()
    
    # Create invoice items
    for item_data in invoice_in.items:
        item = models.InvoiceItem(
            invoice_id=invoice.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit=item_data.unit,
            price=item_data.price,
        )
        db.add(item)
    
    await db.commit()
    await db.refresh(invoice)
    
    # Reload invoice with items to avoid lazy loading issues
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items)
    ).where(models.Invoice.id == invoice.id)
    result = await db.execute(query)
    invoice_with_items = result.scalars().first()
    
    return invoice_with_items


@router.get("/{invoice_id}", response_model=schemas.Invoice)
async def read_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get a specific invoice by id
    """
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product),
        selectinload(models.Invoice.customer),
        selectinload(models.Invoice.created_by_user)
    ).where(models.Invoice.id == invoice_id)
    
    result = await db.execute(query)
    invoice = result.scalars().first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="فاکتور یافت نشد",  # Invoice not found
        )
    
    # Role-based access control
    if current_user.role == schemas.UserRole.WAREHOUSE and invoice.status not in [
        schemas.InvoiceStatus.WAREHOUSE_PENDING,
        schemas.InvoiceStatus.APPROVED,
        schemas.InvoiceStatus.SHIPPED
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما دسترسی به این فاکتور را ندارید",  # You don't have access to this invoice
        )
    
    return invoice


@router.post("/{invoice_id}/reserve", response_model=schemas.Invoice)
async def reserve_invoice_stock(
    *,
    db: AsyncSession = Depends(get_db),
    invoice_id: int,
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    Reserve stock for an invoice and mark it as accountant_pending (warehouse only)
    """
    # Get invoice with items
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product)
    ).where(models.Invoice.id == invoice_id)
    
    result = await db.execute(query)
    invoice = result.scalars().first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="فاکتور یافت نشد",  # Invoice not found
        )
    
    # Check if invoice is in the correct status
    if invoice.status != schemas.InvoiceStatus.WAREHOUSE_PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فاکتور در وضعیت مناسب برای رزرو موجودی نیست",  # Invoice is not in the correct status for stock reservation
        )
    
    # Check stock availability and reserve
    for item in invoice.items:
        if item.product.quantity_available < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"موجودی محصول {item.product.name} کافی نیست",  # Not enough stock for product {item.product.name}
            )
        
        # Create inventory transaction for reservation
        inventory_transaction = models.InventoryTransaction(
            product_id=item.product_id,
            change_quantity=-item.quantity,  # Negative for reservation
            reason=schemas.TransactionReason.SALE_RESERVATION,
            reference_id=invoice.id,
            notes=f"رزرو برای فاکتور شماره {invoice.invoice_number}",  # Reserved for invoice number {invoice.invoice_number}
            created_by=current_user.id,
        )
        db.add(inventory_transaction)
        
        # Update product quantity
        item.product.quantity_available -= item.quantity
        db.add(item.product)
    
    # Update invoice status
    invoice.status = schemas.InvoiceStatus.ACCOUNTANT_PENDING
    db.add(invoice)
    
    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/approve", response_model=schemas.Invoice)
async def approve_invoice(
    *,
    db: AsyncSession = Depends(get_db),
    invoice_id: int,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Approve an invoice (accountant only)
    """
    result = await db.execute(select(models.Invoice).where(models.Invoice.id == invoice_id))
    invoice = result.scalars().first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="فاکتور یافت نشد",  # Invoice not found
        )
    
    # Check if invoice is in the correct status
    if invoice.status != schemas.InvoiceStatus.ACCOUNTANT_PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فاکتور در وضعیت مناسب برای تایید نیست",  # Invoice is not in the correct status for approval
        )
    
    # Update invoice status
    invoice.status = schemas.InvoiceStatus.APPROVED
    db.add(invoice)
    
    await db.commit()
    await db.refresh(invoice)
    
    # Reload invoice with items to avoid lazy loading issues
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items)
    ).where(models.Invoice.id == invoice_id)
    result = await db.execute(query)
    invoice_with_items = result.scalars().first()
    
    return invoice_with_items


@router.post("/{invoice_id}/ship", response_model=schemas.Invoice)
async def ship_invoice(
    *,
    db: AsyncSession = Depends(get_db),
    invoice_id: int,
    tracking_info: schemas.InvoiceTrackingUpdate,
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    Mark an invoice as shipped and add tracking information (warehouse only)
    """
    # Get invoice with items
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product)
    ).where(models.Invoice.id == invoice_id)
    
    result = await db.execute(query)
    invoice = result.scalars().first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="فاکتور یافت نشد",  # Invoice not found
        )
    
    # Check if invoice is in the correct status
    if invoice.status != schemas.InvoiceStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فاکتور در وضعیت مناسب برای ارسال نیست",  # Invoice is not in the correct status for shipping
        )
    
    # Update inventory - convert reservation to shipping
    for item in invoice.items:
        # Create inventory transaction for shipping
        inventory_transaction = models.InventoryTransaction(
            product_id=item.product_id,
            change_quantity=0,  # No change in quantity as it was already reserved
            reason=schemas.TransactionReason.SHIPPING,
            reference_id=invoice.id,
            notes=f"ارسال فاکتور شماره {invoice.invoice_number}",  # Shipping invoice number {invoice.invoice_number}
            created_by=current_user.id,
        )
        db.add(inventory_transaction)
    
    # Update invoice status and tracking info
    invoice.status = schemas.InvoiceStatus.SHIPPED
    invoice.tracking_info = tracking_info.dict()
    db.add(invoice)
    
    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/deliver", response_model=schemas.Invoice)
async def deliver_invoice(
    *,
    db: AsyncSession = Depends(get_db),
    invoice_id: int,
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    Mark an invoice as delivered (warehouse only)
    """
    result = await db.execute(select(models.Invoice).where(models.Invoice.id == invoice_id))
    invoice = result.scalars().first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="فاکتور یافت نشد",  # Invoice not found
        )
    
    # Check if invoice is in the correct status
    if invoice.status != schemas.InvoiceStatus.SHIPPED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فاکتور در وضعیت مناسب برای تحویل نیست",  # Invoice is not in the correct status for delivery
        )
    
    # Update invoice status
    invoice.status = schemas.InvoiceStatus.DELIVERED
    db.add(invoice)
    
    await db.commit()
    await db.refresh(invoice)
    
    # Reload invoice with items to avoid lazy loading issues
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items)
    ).where(models.Invoice.id == invoice_id)
    result = await db.execute(query)
    invoice_with_items = result.scalars().first()
    
    return invoice_with_items


@router.post("/{invoice_id}/cancel", response_model=schemas.Invoice)
async def cancel_invoice(
    *,
    db: AsyncSession = Depends(get_db),
    invoice_id: int,
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Cancel an invoice and return stock (admin only)
    """
    # Get invoice with items
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product)
    ).where(models.Invoice.id == invoice_id)
    
    result = await db.execute(query)
    invoice = result.scalars().first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="فاکتور یافت نشد",  # Invoice not found
        )
    
    # Check if invoice can be cancelled
    if invoice.status in [schemas.InvoiceStatus.DELIVERED, schemas.InvoiceStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فاکتور قابل لغو نیست",  # Invoice cannot be cancelled
        )
    
    # If stock was reserved, return it
    if invoice.status in [schemas.InvoiceStatus.WAREHOUSE_PENDING, schemas.InvoiceStatus.ACCOUNTANT_PENDING, schemas.InvoiceStatus.APPROVED]:
        for item in invoice.items:
            # Create inventory transaction for return
            inventory_transaction = models.InventoryTransaction(
                product_id=item.product_id,
                change_quantity=item.quantity,  # Positive for return
                reason=schemas.TransactionReason.RETURN,
                reference_id=invoice.id,
                notes=f"برگشت از فاکتور لغو شده {invoice.invoice_number}",  # Return from cancelled invoice {invoice.invoice_number}
                created_by=current_user.id,
            )
            db.add(inventory_transaction)
            
            # Update product quantity
            item.product.quantity_available += item.quantity
            db.add(item.product)
    
    # Update invoice status
    invoice.status = schemas.InvoiceStatus.CANCELLED
    db.add(invoice)
    
    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/attachments")
async def add_invoice_attachment(
    *,
    db: AsyncSession = Depends(get_db),
    invoice_id: int,
    file: UploadFile = File(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Add an attachment to an invoice
    """
    result = await db.execute(select(models.Invoice).where(models.Invoice.id == invoice_id))
    invoice = result.scalars().first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="فاکتور یافت نشد",  # Invoice not found
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
    invoice_upload_dir = os.path.join(settings.UPLOADS_DIR, "invoices", str(invoice_id))
    os.makedirs(invoice_upload_dir, exist_ok=True)
    
    # Save file
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(invoice_upload_dir, safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Update invoice attachments
    relative_path = f"/uploads/invoices/{invoice_id}/{safe_filename}"
    
    if not invoice.attachments:
        invoice.attachments = [relative_path]
    else:
        attachments = invoice.attachments
        attachments.append(relative_path)
        invoice.attachments = attachments
    
    db.add(invoice)
    await db.commit()
    
    return {"filename": file.filename, "path": relative_path}