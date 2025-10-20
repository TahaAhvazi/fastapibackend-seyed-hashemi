from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.api import deps
from app.db.session import get_db
from app.schemas.check import CheckStatus

router = APIRouter()


@router.get("/", response_model=List[schemas.Customer])
async def read_customers(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    city: Optional[str] = None,
    province: Optional[str] = None,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Retrieve customers with optional filtering (admin or accountant only)
    """
    query = select(models.Customer).options(selectinload(models.Customer.bank_accounts))
    
    # Apply filters
    filters = []
    if name:
        filters.append(
            or_(
                models.Customer.first_name.ilike(f"%{name}%"),
                models.Customer.last_name.ilike(f"%{name}%")
            )
        )
    if city:
        filters.append(models.Customer.city.ilike(f"%{city}%"))
    if province:
        filters.append(models.Customer.province.ilike(f"%{province}%"))
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    customers = result.scalars().all()
    return customers


@router.post("/", response_model=schemas.Customer)
async def create_customer(
    *,
    db: AsyncSession = Depends(get_db),
    customer_in: schemas.CustomerCreate,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Create new customer (admin or accountant only)
    """
    # Create new customer
    customer = models.Customer(
        first_name=customer_in.first_name,
        last_name=customer_in.last_name,
        address=customer_in.address,
        phone=customer_in.phone,
        city=customer_in.city,
        province=customer_in.province,
    )
    db.add(customer)
    await db.flush()
    
    # Add bank accounts if provided
    if customer_in.bank_accounts:
        for bank_account_data in customer_in.bank_accounts:
            bank_account = models.BankAccount(
                customer_id=customer.id,
                **bank_account_data.dict()
            )
            db.add(bank_account)
    
    await db.commit()
    await db.refresh(customer)
    
    # Reload customer with bank_accounts to avoid lazy loading issues
    query = select(models.Customer).options(
        selectinload(models.Customer.bank_accounts)
    ).where(models.Customer.id == customer.id)
    result = await db.execute(query)
    customer_with_accounts = result.scalars().first()
    
    return customer_with_accounts


@router.get("/{customer_id}", response_model=schemas.CustomerDetail)
async def read_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Get a specific customer by id with financial details (admin or accountant only)
    """
    # Get customer with bank accounts
    query = select(models.Customer).options(
        selectinload(models.Customer.bank_accounts),
        selectinload(models.Customer.invoices),
        selectinload(models.Customer.checks)
    ).where(models.Customer.id == customer_id)
    
    result = await db.execute(query)
    customer = result.scalars().first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مشتری یافت نشد",  # Customer not found
        )
    
    # Calculate financial information
    total_purchases = sum(invoice.total for invoice in customer.invoices)
    total_paid = sum(
        invoice.total for invoice in customer.invoices 
        if invoice.status in [schemas.InvoiceStatus.DELIVERED, schemas.InvoiceStatus.SHIPPED]
    )
    balance = total_purchases - total_paid
    invoices_count = len(customer.invoices)
    checks_in_progress_count = sum(1 for check in customer.checks if check.status == CheckStatus.IN_PROGRESS)
    
    # Convert bank accounts to proper schema format
    bank_accounts = [
        schemas.BankAccount(
            id=ba.id,
            customer_id=ba.customer_id,
            bank_name=ba.bank_name,
            account_number=ba.account_number,
            iban=ba.iban
        )
        for ba in customer.bank_accounts
    ]

    # Create response with additional fields
    customer_detail = schemas.CustomerDetail(
        id=customer.id,
        first_name=customer.first_name,
        last_name=customer.last_name,
        full_name=customer.full_name,
        address=customer.address,
        phone=customer.phone,
        city=customer.city,
        province=customer.province,
        bank_accounts=bank_accounts,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        total_purchases=total_purchases,
        total_paid=total_paid,
        balance=balance,
        invoices_count=invoices_count,
        checks_in_progress_count=checks_in_progress_count
    )
    
    return customer_detail


@router.put("/{customer_id}", response_model=schemas.Customer)
async def update_customer(
    *,
    db: AsyncSession = Depends(get_db),
    customer_id: int,
    customer_in: schemas.CustomerUpdate,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Update a customer (admin or accountant only)
    """
    result = await db.execute(select(models.Customer).where(models.Customer.id == customer_id))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مشتری یافت نشد",  # Customer not found
        )
    
    # Update customer attributes
    update_data = customer_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    
    # Reload customer with bank_accounts to avoid lazy loading issues
    query = select(models.Customer).options(
        selectinload(models.Customer.bank_accounts)
    ).where(models.Customer.id == customer_id)
    result = await db.execute(query)
    customer_with_accounts = result.scalars().first()
    
    return customer_with_accounts


@router.delete("/{customer_id}", response_model=schemas.Customer)
async def delete_customer(
    *,
    db: AsyncSession = Depends(get_db),
    customer_id: int,
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Delete a customer (admin only)
    """
    # First load customer with bank_accounts to avoid lazy loading issues when returning
    query = select(models.Customer).options(
        selectinload(models.Customer.bank_accounts)
    ).where(models.Customer.id == customer_id)
    result = await db.execute(query)
    customer = result.scalars().first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مشتری یافت نشد",  # Customer not found
        )
    
    # Check if customer has invoices
    invoices_query = select(models.Invoice).where(models.Invoice.customer_id == customer_id)
    invoices_result = await db.execute(invoices_query)
    invoices = invoices_result.scalars().first()
    
    if invoices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="این مشتری دارای فاکتور است و قابل حذف نیست",  # This customer has invoices and cannot be deleted
        )
    
    await db.delete(customer)
    await db.commit()
    return customer


@router.post("/{customer_id}/bank-accounts", response_model=schemas.BankAccount)
async def add_bank_account(
    *,
    db: AsyncSession = Depends(get_db),
    customer_id: int,
    bank_account_in: schemas.BankAccountCreate,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Add a bank account to a customer (admin or accountant only)
    """
    result = await db.execute(select(models.Customer).where(models.Customer.id == customer_id))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مشتری یافت نشد",  # Customer not found
        )
    
    bank_account = models.BankAccount(
        customer_id=customer_id,
        **bank_account_in.dict()
    )
    db.add(bank_account)
    await db.commit()
    await db.refresh(bank_account)
    return bank_account


@router.delete("/{customer_id}/bank-accounts/{bank_account_id}", response_model=schemas.BankAccount)
async def delete_bank_account(
    *,
    db: AsyncSession = Depends(get_db),
    customer_id: int,
    bank_account_id: int,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Delete a bank account from a customer (admin or accountant only)
    """
    result = await db.execute(
        select(models.BankAccount).where(
            models.BankAccount.id == bank_account_id,
            models.BankAccount.customer_id == customer_id
        )
    )
    bank_account = result.scalars().first()
    if not bank_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="حساب بانکی یافت نشد",  # Bank account not found
        )
    
    await db.delete(bank_account)
    await db.commit()
    return bank_account


@router.get("/{customer_id}/balance", response_model=schemas.CustomerBalanceInfo)
async def get_customer_balance(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Get customer balance information (admin or accountant only)
    """
    result = await db.execute(select(models.Customer).where(models.Customer.id == customer_id))
    customer = result.scalars().first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مشتری یافت نشد",  # Customer not found
        )
    
    return schemas.CustomerBalanceInfo(
        current_balance=customer.current_balance,
        is_creditor=customer.is_creditor,
        is_debtor=customer.is_debtor,
        balance_status=customer.balance_status,
        balance_notes=customer.balance_notes
    )


@router.post("/{customer_id}/balance/adjust", response_model=schemas.CustomerBalanceInfo)
async def adjust_customer_balance(
    *,
    customer_id: int,
    balance_update: schemas.CustomerBalanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Adjust customer balance by adding/subtracting amount (admin or accountant only)
    """
    result = await db.execute(select(models.Customer).where(models.Customer.id == customer_id))
    customer = result.scalars().first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مشتری یافت نشد",  # Customer not found
        )
    
    # Update balance
    customer.current_balance += balance_update.balance_adjustment
    
    # Update notes if provided
    if balance_update.notes:
        if customer.balance_notes:
            customer.balance_notes += f"\n{balance_update.notes}"
        else:
            customer.balance_notes = balance_update.notes
    
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    
    return schemas.CustomerBalanceInfo(
        current_balance=customer.current_balance,
        is_creditor=customer.is_creditor,
        is_debtor=customer.is_debtor,
        balance_status=customer.balance_status,
        balance_notes=customer.balance_notes
    )


@router.post("/{customer_id}/balance/set", response_model=schemas.CustomerBalanceInfo)
async def set_customer_balance(
    *,
    customer_id: int,
    balance_set: schemas.CustomerBalanceSet,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Set customer balance to specific amount (admin or accountant only)
    """
    result = await db.execute(select(models.Customer).where(models.Customer.id == customer_id))
    customer = result.scalars().first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مشتری یافت نشد",  # Customer not found
        )
    
    # Set balance
    customer.current_balance = balance_set.new_balance
    
    # Update notes if provided
    if balance_set.notes:
        if customer.balance_notes:
            customer.balance_notes += f"\n{balance_set.notes}"
        else:
            customer.balance_notes = balance_set.notes
    
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    
    return schemas.CustomerBalanceInfo(
        current_balance=customer.current_balance,
        is_creditor=customer.is_creditor,
        is_debtor=customer.is_debtor,
        balance_status=customer.balance_status,
        balance_notes=customer.balance_notes
    )