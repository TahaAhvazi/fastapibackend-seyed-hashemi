from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.api import deps
from app.db.session import get_db

router = APIRouter()


@router.get("/transactions", response_model=List[schemas.InventoryTransaction])
async def read_inventory_transactions(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    product_id: Optional[int] = None,
    reason: Optional[schemas.TransactionReason] = None,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve inventory transactions with optional filtering
    """
    query = select(models.InventoryTransaction).options(
        selectinload(models.InventoryTransaction.product),
        selectinload(models.InventoryTransaction.created_by_user)
    )
    
    # Apply filters
    if product_id:
        query = query.where(models.InventoryTransaction.product_id == product_id)
    if reason:
        query = query.where(models.InventoryTransaction.reason == reason)
    
    query = query.order_by(models.InventoryTransaction.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    transactions = result.scalars().all()
    return transactions


@router.post("/transactions", response_model=schemas.InventoryTransaction)
async def create_inventory_transaction(
    *,
    db: AsyncSession = Depends(get_db),
    transaction_in: schemas.InventoryTransactionCreate,
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    Create a new inventory transaction (admin or warehouse only)
    """
    # Check if product exists
    product_result = await db.execute(select(models.Product).where(models.Product.id == transaction_in.product_id))
    product = product_result.scalars().first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="محصول یافت نشد",  # Product not found
        )
    
    # Create transaction
    transaction = models.InventoryTransaction(
        product_id=transaction_in.product_id,
        change_quantity=transaction_in.change_quantity,
        reason=transaction_in.reason,
        reference_id=transaction_in.reference_id,
        notes=transaction_in.notes,
        created_by=current_user.id,
    )
    db.add(transaction)
    
    await db.commit()
    await db.refresh(transaction)
    return transaction


@router.get("/products/{product_id}/quantity", response_model=schemas.ProductQuantity)
async def get_product_quantity(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current quantity for a specific product
    """
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    product = result.scalars().first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="محصول یافت نشد",  # Product not found
        )
    
    # Get reserved quantity (sum of all active reservations)
    reserved_query = select(models.InventoryTransaction).where(
        models.InventoryTransaction.product_id == product_id,
        models.InventoryTransaction.reason == schemas.TransactionReason.SALE_RESERVATION,
        # We could join with Invoice and check if it's not cancelled, but for simplicity we'll count all reservations
    )
    reserved_result = await db.execute(reserved_query)
    reserved_transactions = reserved_result.scalars().all()
    reserved_quantity = sum(t.change_quantity * -1 for t in reserved_transactions)  # Convert negative to positive
    
    return {
        "product_id": product.id,
        "product_name": product.name,
        "is_available": product.is_available,
        "reserved_quantity": reserved_quantity
    }


@router.post("/reserve", response_model=List[schemas.InventoryTransaction])
async def reserve_stock(
    *,
    db: AsyncSession = Depends(get_db),
    reserve_data: schemas.ReserveStock,
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    Reserve stock for products (admin or warehouse only)
    """
    transactions = []
    
    for item in reserve_data.items:
        # Check if product exists and has enough stock
        product_result = await db.execute(select(models.Product).where(models.Product.id == item.product_id))
        product = product_result.scalars().first()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"محصول با شناسه {item.product_id} یافت نشد",  # Product with ID {item.product_id} not found
            )
        
        if not product.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"محصول {product.name} در حال حاضر موجود نیست",  # Product {product.name} is not available
            )
        
        # Create inventory transaction for reservation
        transaction = models.InventoryTransaction(
            product_id=item.product_id,
            change_quantity=-item.quantity,  # Negative for reservation
            reason=schemas.TransactionReason.SALE_RESERVATION,
            reference_id=reserve_data.reference_id,
            notes=reserve_data.notes,
            created_by=current_user.id,
        )
        db.add(transaction)
        transactions.append(transaction)
    
    await db.commit()
    
    # Refresh all transactions
    for transaction in transactions:
        await db.refresh(transaction)
    
    return transactions


@router.post("/unreserve", response_model=List[schemas.InventoryTransaction])
async def unreserve_stock(
    *,
    db: AsyncSession = Depends(get_db),
    reserve_data: schemas.ReserveStock,
    current_user: models.User = Depends(deps.get_current_admin_or_warehouse_user),
) -> Any:
    """
    Unreserve previously reserved stock (admin or warehouse only)
    """
    transactions = []
    
    for item in reserve_data.items:
        # Check if product exists
        product_result = await db.execute(select(models.Product).where(models.Product.id == item.product_id))
        product = product_result.scalars().first()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"محصول با شناسه {item.product_id} یافت نشد",  # Product with ID {item.product_id} not found
            )
        
        # Create inventory transaction for unreservation
        transaction = models.InventoryTransaction(
            product_id=item.product_id,
            change_quantity=item.quantity,  # Positive for unreservation
            reason=schemas.TransactionReason.RETURN,
            reference_id=reserve_data.reference_id,
            notes=f"لغو رزرو: {reserve_data.notes}",  # Cancel reservation: {reserve_data.notes}
            created_by=current_user.id,
        )
        db.add(transaction)
        transactions.append(transaction)
    
    await db.commit()
    
    # Refresh all transactions
    for transaction in transactions:
        await db.refresh(transaction)
    
    return transactions