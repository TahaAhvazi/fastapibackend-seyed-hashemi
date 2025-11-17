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


def serialize_product_with_images(product: models.Product) -> dict:
    """Convert Product model to dict with images list"""
    product_dict = {
        **{k: v for k, v in product.__dict__.items() if not k.startswith('_')},
        'images': [img.image_url for img in product.images] if hasattr(product, 'images') and product.images else []
    }
    return product_dict

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
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product).selectinload(models.Product.images),
        selectinload(models.Invoice.customer).selectinload(models.Customer.bank_accounts),
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
    
    # Check if products exist and have enough stock; compute quantity from rolls if provided
    computed_quantities: List[float] = []
    for item in invoice_in.items:
        product_result = await db.execute(select(models.Product).where(models.Product.id == item.product_id))
        product = product_result.scalars().first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"محصول با شناسه {item.product_id} یافت نشد",  # Product with ID {item.product_id} not found
            )

        # Determine effective quantity based on rolls if provided
        effective_quantity = item.quantity
        
        # Check if detailed rolls are provided (highest priority)
        if getattr(item, "detailed_rolls", None) is not None and item.detailed_rolls:
            # Calculate total quantity from detailed measurements
            total_measurement = 0.0
            for roll in item.detailed_rolls:
                for piece in roll.pieces:
                    total_measurement += piece.measurement
            effective_quantity = total_measurement
            
        elif getattr(item, "rolls_count", None) is not None:
            # Use simple roll calculation
            ppr = getattr(item, "pieces_per_roll", None)
            if ppr is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"برای محاسبه تعداد بر اساس طاقه، مقدار pieces_per_roll باید در درخواست ارسال شود",
                )
            effective_quantity = float(item.rolls_count) * float(ppr)

        if effective_quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"تعداد برای محصول {product.name} باید بزرگ‌تر از ۰ باشد",
            )

        if not product.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"محصول {product.name} در حال حاضر موجود نیست",
            )

        computed_quantities.append(effective_quantity)
    
    # If payment is CHECK or MIXED, validate provided check_id (if any) belongs to this customer and is not already linked
    if invoice_in.payment_type in [schemas.PaymentType.CHECK, schemas.PaymentType.MIXED]:
        if not invoice_in.check_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="برای پرداخت چکی یا ترکیبی، وارد کردن شناسه چک الزامی است",
            )
        check_result = await db.execute(select(models.Check).where(models.Check.id == invoice_in.check_id))
        check_obj = check_result.scalars().first()
        if not check_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"چکی با شناسه {invoice_in.check_id} یافت نشد",
            )
        if check_obj.customer_id != invoice_in.customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="شناسه چک متعلق به مشتری این فاکتور نیست",
            )
        if check_obj.related_invoice_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"این چک قبلاً به فاکتور {check_obj.related_invoice_id} متصل شده است",
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
    
    # Calculate subtotal and total using effective quantities
    subtotal = sum(q * itm.price for q, itm in zip(computed_quantities, invoice_in.items))
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
    
    # Create invoice items using effective quantities
    for idx, item_data in enumerate(invoice_in.items):
        item = models.InvoiceItem(
            invoice_id=invoice.id,
            product_id=item_data.product_id,
            quantity=computed_quantities[idx] if idx < len(computed_quantities) else item_data.quantity,
            unit=item_data.unit,
            price=item_data.price,
            # Store roll-based information for detailed tracking
            rolls_count=getattr(item_data, "rolls_count", None),
            pieces_per_roll=getattr(item_data, "pieces_per_roll", None),
            detailed_rolls=[roll.model_dump() for roll in item_data.detailed_rolls] if getattr(item_data, "detailed_rolls", None) else None,
        )
        db.add(item)
    
    await db.commit()
    await db.refresh(invoice)

    # If a check is provided and valid, link it to the created invoice
    if invoice_in.payment_type in [schemas.PaymentType.CHECK, schemas.PaymentType.MIXED] and invoice_in.check_id:
        check_result = await db.execute(select(models.Check).where(models.Check.id == invoice_in.check_id))
        check_obj = check_result.scalars().first()
        if check_obj:
            check_obj.related_invoice_id = invoice.id
            db.add(check_obj)
            await db.commit()
    
    # Reload invoice with all relationships to avoid lazy loading issues
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product).selectinload(models.Product.images),
        selectinload(models.Invoice.customer).selectinload(models.Customer.bank_accounts),
        selectinload(models.Invoice.created_by_user)
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
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product).selectinload(models.Product.images),
        selectinload(models.Invoice.customer).selectinload(models.Customer.bank_accounts),
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
    reserve_update: Optional[schemas.InvoiceReserveUpdate] = None,
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    Reserve stock for an invoice and mark it as accountant_pending (warehouse only)

    If body provided, warehouse user can edit invoice items' quantity/unit/price before reservation.
    """
    # Get invoice with items
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product).selectinload(models.Product.images),
        selectinload(models.Invoice.customer).selectinload(models.Customer.bank_accounts),
        selectinload(models.Invoice.created_by_user)
    ).where(models.Invoice.id == invoice_id)
    
    result = await db.execute(query)
    invoice = result.scalars().first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="فاکتور یافت نشد",  # Invoice not found
        )
    
    # Check if invoice is in the correct status
    if invoice.status not in [schemas.InvoiceStatus.WAREHOUSE_PENDING, schemas.InvoiceStatus.ACCOUNTANT_PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فاکتور در وضعیت مناسب برای رزرو موجودی نیست",  # Invoice is not in the correct status for stock reservation
        )
    
    # Optional: apply edits before reservation
    if reserve_update and reserve_update.items:
        # Map by id for fast lookup
        invoice_items_by_id = {i.id: i for i in invoice.items}
        for edit in reserve_update.items:
            inv_item = invoice_items_by_id.get(edit.id)
            if not inv_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"آیتم فاکتور با شناسه {edit.id} یافت نشد",
                )
            # Handle detailed_rolls first (highest priority)
            if edit.detailed_rolls is not None:
                if edit.detailed_rolls:  # Non-empty list
                    # Calculate total quantity from detailed measurements
                    total_measurement = 0.0
                    for roll in edit.detailed_rolls:
                        for piece in roll.pieces:
                            if piece.measurement <= 0:
                                raise HTTPException(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"متراژ قطعه {piece.piece_number} در طاقه {roll.roll_number} باید بزرگ‌تر از ۰ باشد",
                                )
                            total_measurement += piece.measurement
                    inv_item.quantity = total_measurement
                    # Store detailed rolls information
                    inv_item.detailed_rolls = [roll.model_dump() for roll in edit.detailed_rolls]
                    # Clear simple roll info when using detailed rolls
                    inv_item.rolls_count = None
                    inv_item.pieces_per_roll = None
            elif edit.quantity is not None:
                if edit.quantity <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"تعداد برای آیتم {edit.id} باید بزرگ‌تر از ۰ باشد",
                    )
                inv_item.quantity = edit.quantity
                # Do NOT clear detailed_rolls unless explicitly provided as empty
            
            if edit.unit is not None:
                inv_item.unit = edit.unit
            if edit.price is not None:
                if edit.price < 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"قیمت برای آیتم {edit.id} نمی‌تواند منفی باشد",
                    )
                inv_item.price = edit.price
            db.add(inv_item)

        # Recalculate subtotal/total after edits
        new_subtotal = sum(i.quantity * i.price for i in invoice.items)
        invoice.subtotal = new_subtotal
        invoice.total = new_subtotal
        db.add(invoice)

    # Check product availability using possibly-updated items
    for item in invoice.items:
        if not item.product.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"محصول {item.product.name} در حال حاضر موجود نیست",  # Product {item.product.name} is not available
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
    
    # Update invoice status
    invoice.status = schemas.InvoiceStatus.ACCOUNTANT_PENDING
    db.add(invoice)
    
    await db.commit()
    
    # Re-fetch invoice with all relationships after commit
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product).selectinload(models.Product.images),
        selectinload(models.Invoice.customer).selectinload(models.Customer.bank_accounts),
        selectinload(models.Invoice.created_by_user)
    ).where(models.Invoice.id == invoice_id)
    
    result = await db.execute(query)
    invoice_with_items = result.scalars().first()
    
    return invoice_with_items


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
    
    # Reload invoice with all relationships to avoid lazy loading issues
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product).selectinload(models.Product.images),
        selectinload(models.Invoice.customer).selectinload(models.Customer.bank_accounts),
        selectinload(models.Invoice.created_by_user)
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
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product).selectinload(models.Product.images)
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
    
    # Reload invoice with all relationships to avoid lazy loading issues
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product).selectinload(models.Product.images),
        selectinload(models.Invoice.customer).selectinload(models.Customer.bank_accounts),
        selectinload(models.Invoice.created_by_user)
    ).where(models.Invoice.id == invoice_id)
    result = await db.execute(query)
    invoice_with_items = result.scalars().first()
    
    return invoice_with_items


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
    
    # Reload invoice with all relationships to avoid lazy loading issues
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product).selectinload(models.Product.images),
        selectinload(models.Invoice.customer).selectinload(models.Customer.bank_accounts),
        selectinload(models.Invoice.created_by_user)
    ).where(models.Invoice.id == invoice_id)
    result = await db.execute(query)
    invoice_with_items = result.scalars().first()
    
    return invoice_with_items


@router.post("/{invoice_id}/cancel", response_model=schemas.Invoice)
async def cancel_invoice(
    *,
    db: AsyncSession = Depends(get_db),
    invoice_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Cancel an invoice and return stock (admin or accountant only)
    """
    # Check user permissions
    if current_user.role not in [schemas.UserRole.ADMIN, schemas.UserRole.ACCOUNTANT]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"شما دسترسی لازم برای لغو فاکتور را ندارید. نقش شما: {current_user.role}. نقش‌های مجاز: admin, accountant"  # You don't have permission to cancel invoices. Your role: {current_user.role}. Allowed roles: admin, accountant
        )
    
    # Get invoice with items
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product).selectinload(models.Product.images)
    ).where(models.Invoice.id == invoice_id)
    
    result = await db.execute(query)
    invoice = result.scalars().first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="فاکتور یافت نشد",  # Invoice not found
        )
    
    # Check if invoice can be cancelled
    if invoice.status == schemas.InvoiceStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فاکتور قبلاً لغو شده است",  # Invoice is already cancelled
        )
    
    # Allow cancellation of delivered invoices (admin/accountant can override)
    # if invoice.status == schemas.InvoiceStatus.DELIVERED:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="فاکتور تحویل شده قابل لغو نیست. وضعیت فعلی: تحویل شده",  # Delivered invoice cannot be cancelled. Current status: delivered
    #     )
    
    # If stock was reserved, return it
    if invoice.status in [schemas.InvoiceStatus.WAREHOUSE_PENDING, schemas.InvoiceStatus.ACCOUNTANT_PENDING, schemas.InvoiceStatus.APPROVED, schemas.InvoiceStatus.SHIPPED, schemas.InvoiceStatus.DELIVERED]:
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
    
    # Update invoice status
    invoice.status = schemas.InvoiceStatus.CANCELLED
    db.add(invoice)
    
    await db.commit()
    await db.refresh(invoice)
    
    # Reload invoice with all relationships to avoid lazy loading issues
    query = select(models.Invoice).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product).selectinload(models.Product.images),
        selectinload(models.Invoice.customer).selectinload(models.Customer.bank_accounts),
        selectinload(models.Invoice.created_by_user)
    ).where(models.Invoice.id == invoice_id)
    result = await db.execute(query)
    invoice_with_items = result.scalars().first()
    
    return invoice_with_items


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