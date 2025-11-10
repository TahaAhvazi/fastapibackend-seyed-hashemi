from typing import Any, List, Optional
import pandas as pd
import io
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy import or_, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.api import deps
from app.db.session import get_db
from app.schemas.check import CheckStatus

router = APIRouter()


@router.get("/", response_model=schemas.PaginatedCustomerResponse)
async def read_customers(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="شماره صفحه (از 1 شروع می‌شود)"),
    per_page: int = Query(20, ge=1, le=100, description="تعداد آیتم در هر صفحه (پیش‌فرض 20)"),
    name: Optional[str] = None,
    city: Optional[str] = None,
    province: Optional[str] = None,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    دریافت لیست مشتری‌ها با صفحه‌بندی (admin یا accountant)
    Retrieve customers with pagination (admin or accountant only)
    
    پیش‌فرض: 20 مشتری در هر صفحه
    Default: 20 customers per page
    """
    # Build base query
    query = select(models.Customer).options(selectinload(models.Customer.bank_accounts))
    count_query = select(func.count(models.Customer.id))
    
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
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page  # Ceiling division
    offset = (page - 1) * per_page
    
    # Apply pagination
    query = query.offset(offset).limit(per_page)
    
    # Execute query
    result = await db.execute(query)
    customers = result.scalars().all()
    
    # Return paginated response
    return schemas.PaginatedCustomerResponse(
        items=customers,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


@router.get("/search", response_model=List[schemas.Customer])
async def search_customers(
    db: AsyncSession = Depends(get_db),
    q: str = Query(..., min_length=1, description="عبارت جستجو (نام، نام خانوادگی، شماره تلفن یا موبایل)"),
    limit: int = Query(50, ge=1, le=100, description="حداکثر تعداد نتایج"),
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    جستجوی سریع مشتری‌ها بر اساس نام یا شماره تلفن
    Quick search customers by name or phone number
    
    جستجو در فیلدهای:
    - نام (first_name)
    - نام خانوادگی (last_name)
    - شماره تلفن (phone)
    - شماره موبایل (mobile)
    - کد شخص (person_code)
    
    Search in fields:
    - First name
    - Last name
    - Phone number
    - Mobile number
    - Person code
    
    مثال: اگر "رضا" جستجو کنید، تمام مشتری‌هایی که در نام یا نام خانوادگی‌شان "رضا" دارند را نشان می‌دهد
    Example: If you search "رضا", all customers with "رضا" in their first or last name will be shown
    """
    # Clean search query (remove spaces for phone numbers)
    search_term = q.strip()
    search_term_no_space = search_term.replace(" ", "")
    
    # Build query with multiple search conditions
    query = select(models.Customer).options(selectinload(models.Customer.bank_accounts))
    
    # Search in multiple fields
    search_filters = [
        models.Customer.first_name.ilike(f"%{search_term}%"),
        models.Customer.last_name.ilike(f"%{search_term}%"),
        models.Customer.person_code.ilike(f"%{search_term}%"),
    ]
    
    # Add phone search only if search term contains digits
    if search_term_no_space and any(c.isdigit() for c in search_term_no_space):
        search_filters.extend([
            models.Customer.phone.ilike(f"%{search_term_no_space}%"),
            models.Customer.mobile.ilike(f"%{search_term_no_space}%"),
        ])
    
    query = query.where(or_(*search_filters))
    query = query.limit(limit)
    
    # Execute query
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
    # Create new customer with all fields
    customer_data = customer_in.model_dump(exclude={'bank_accounts'}, exclude_unset=True)
    customer = models.Customer(**customer_data)
    db.add(customer)
    await db.flush()
    
    # Add bank accounts if provided
    if customer_in.bank_accounts:
        for bank_account_data in customer_in.bank_accounts:
            bank_account = models.BankAccount(
                customer_id=customer.id,
                **bank_account_data.model_dump()
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

    # Create CustomerDetail from customer model with all fields
    customer_detail = schemas.CustomerDetail(
        **schemas.Customer.model_validate(customer).model_dump(),
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
    # exclude_unset=True: only include fields that were explicitly set
    # exclude_none=False: allow setting fields to None explicitly
    update_data = customer_in.model_dump(exclude_unset=True, exclude_none=False)
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


@router.delete("/delete-all", response_model=dict)
async def delete_all_customers(
    *,
    db: AsyncSession = Depends(get_db),
    confirm: bool = Query(False, description="برای تایید حذف تمام مشتری‌ها باید true ارسال شود"),
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    حذف تمام مشتری‌هایی که هیچ فاکتور یا چکی ندارند (فقط برای ادمین)
    Delete all customers without invoices or checks (admin only)
    
    ⚠️ هشدار: این عملیات غیرقابل بازگشت است. فقط مشتری‌هایی که هیچ فاکتور یا چکی ندارند حذف می‌شوند.
    برای تایید، باید پارامتر confirm=true ارسال شود.
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="برای حذف تمام مشتری‌ها، باید پارامتر confirm=true ارسال شود",
        )
    
    # Get all customers
    customers_result = await db.execute(select(models.Customer))
    customers = customers_result.scalars().all()
    total_customers = len(customers)
    
    deleted_count = 0
    skipped_count = 0
    
    # Check each customer individually and delete only those without invoices or checks
    for customer in customers:
        # Check if customer has invoices
        invoices_query = select(models.Invoice).where(models.Invoice.customer_id == customer.id)
        invoices_result = await db.execute(invoices_query)
        has_invoices = invoices_result.scalars().first() is not None
        
        # Check if customer has checks
        checks_query = select(models.Check).where(models.Check.customer_id == customer.id)
        checks_result = await db.execute(checks_query)
        has_checks = checks_result.scalars().first() is not None
        
        # Only delete if customer has no invoices and no checks
        if not has_invoices and not has_checks:
            await db.delete(customer)
            deleted_count += 1
        else:
            skipped_count += 1
    
    await db.commit()
    
    return {
        "message": f"{deleted_count} مشتری حذف شد. {skipped_count} مشتری به دلیل داشتن فاکتور یا چک حذف نشد.",
        "deleted_count": deleted_count,
        "skipped_count": skipped_count,
        "total_customers": total_customers
    }


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
        **bank_account_in.model_dump()
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

@router.post("/import-excel", response_model=dict)
async def import_customers_from_excel(
    *,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    وارد کردن مشتری‌ها از فایل Excel
    Import customers from Excel file
    """
    # Check file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نام فایل مشخص نیست",
        )
    
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ['xls', 'xlsx']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="فقط فایل‌های Excel (.xls, .xlsx) مجاز هستند",
        )
    
    try:
        # Read Excel file
        contents = await file.read()
        if file_ext == 'xlsx':
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl', header=0)
        else:  # xls
            df = pd.read_excel(io.BytesIO(contents), engine='xlrd', header=0)
        
        # Column names mapping (based on Excel headers)
        column_names = [
            "گروه شخص",           # 0
            "کد شخص",             # 1
            "نوع شخصیت",          # 2
            "پیشوند",             # 3
            "نام / نام شرکت",     # 4
            "نام خانوادگی / مدیر عامل",  # 5
            "تاریخ تولد",         # 6
            "معرف",               # 7
            "تلفن 1",             # 8
            "موبایل",             # 9
            "نام شرکت",            # 10
            "نوع مودی",           # 11
            "کد شهر",             # 12
            "آدرس",               # 13
            "توضیحات",            # 14
            "ارز",                # 15
            "نرخ ارز",            # 16
            "ماهیت اول دوره",     # 17
            "مانده",              # 18
            "اعتبار",             # 19
            "فاكس",               # 20
            "شماره اقتصادی",     # 21
            "شماره ثبت"           # 22
        ]
        
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        # Process each row
        for idx, row in df.iterrows():
            try:
                # Try to get column values by index (in case column names don't match)
                # Column indices: 0=گروه شخص, 1=کد شخص, 2=نوع شخصیت, 3=پیشوند, 4=نام, 5=نام خانوادگی
                # 8=تلفن 1, 9=موبایل, 13=آدرس, 18=مانده
                
                person_code = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) and len(row) > 1 else None
                person_type = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) and len(row) > 2 else None
                first_name = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) and len(row) > 4 else ""
                last_name = str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) and len(row) > 5 else ""
                phone = str(row.iloc[8]).strip() if pd.notna(row.iloc[8]) and len(row) > 8 else None
                mobile = str(row.iloc[9]).strip() if pd.notna(row.iloc[9]) and len(row) > 9 else None
                address = str(row.iloc[13]).strip() if pd.notna(row.iloc[13]) and len(row) > 13 else None
                balance_str = str(row.iloc[18]).strip() if pd.notna(row.iloc[18]) and len(row) > 18 else "0"
                
                if not first_name and not last_name:
                    skipped_count += 1
                    continue
                
                # Parse balance
                balance = 0.0
                if balance_str and balance_str != "nan":
                    balance_str = balance_str.replace(" ", "")
                    if balance_str.startswith("-1"):
                        try:
                            balance = -float(balance_str.replace("-1", ""))
                        except:
                            balance = 0.0
                    else:
                        try:
                            balance = float(balance_str)
                        except:
                            balance = 0.0
                
                # Clean phone numbers
                if phone and phone != "nan":
                    phone = re.sub(r'[^\d]', '', phone)
                    if not phone:
                        phone = None
                else:
                    phone = None
                
                if mobile and mobile != "nan":
                    mobile = re.sub(r'[^\d]', '', mobile)
                    if not mobile:
                        mobile = None
                else:
                    mobile = None
                
                # Extract city from address
                city = None
                if address and address != "nan":
                    common_cities = ["تهران", "اصفهان", "مشهد", "شیراز", "اهواز", "کرمانشاه", "زاهدان", "فسا", "اندیمشک", "شهر قدس", "زابل"]
                    for c in common_cities:
                        if c in address:
                            city = c
                            break
                
                # Extract only the first 23 Excel columns into a dictionary using actual column names
                excel_data = {}
                for col_idx in range(min(len(df.columns), len(column_names))):
                    col_name = column_names[col_idx]
                    col_value = row.iloc[col_idx] if col_idx < len(row) else None
                    if pd.notna(col_value):
                        col_value_str = str(col_value).strip()
                        if col_value_str and col_value_str != "nan":
                            excel_data[col_name] = col_value_str
                        else:
                            excel_data[col_name] = None
                    else:
                        excel_data[col_name] = None
                
                # Check if customer exists
                if person_code and person_code != "nan":
                    existing_result = await db.execute(
                        select(models.Customer).where(models.Customer.person_code == person_code)
                    )
                    existing_customer = existing_result.scalars().first()
                    if existing_customer:
                        existing_customer.person_type = person_type if person_type and person_type != "nan" else existing_customer.person_type
                        existing_customer.first_name = first_name or existing_customer.first_name
                        existing_customer.last_name = last_name or existing_customer.last_name
                        existing_customer.phone = phone or existing_customer.phone
                        existing_customer.mobile = mobile or existing_customer.mobile
                        existing_customer.address = address or existing_customer.address
                        existing_customer.city = city or existing_customer.city
                        existing_customer.current_balance = balance
                        existing_customer.excel_data = excel_data  # Update Excel data
                        db.add(existing_customer)
                        updated_count += 1
                        continue
                
                # Create new customer
                customer = models.Customer(
                    person_code=person_code if person_code and person_code != "nan" else None,
                    person_type=person_type if person_type and person_type != "nan" else None,
                    first_name=first_name or "نامشخص",
                    last_name=last_name or "نامشخص",
                    phone=phone,
                    mobile=mobile,
                    address=address if address and address != "nan" else None,
                    city=city,
                    current_balance=balance,
                    excel_data=excel_data,  # Store all Excel columns
                )
                db.add(customer)
                imported_count += 1
                
            except Exception as e:
                errors.append(f"خطا در ردیف {idx + 2}: {str(e)}")
                skipped_count += 1
                continue
        
        await db.commit()
        
        return {
            "message": "وارد کردن اطلاعات با موفقیت انجام شد",
            "imported": imported_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": errors[:10] if errors else []
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"خطا در خواندن فایل Excel: {str(e)}",
        )


@router.post("/cleanup-excel-data", response_model=dict)
async def cleanup_excel_data(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    پاکسازی excel_data و حذف ستون‌های اضافی (فقط 23 ستون اول نگه داشته می‌شود)
    Cleanup excel_data and remove extra columns (only keep first 23 columns)
    """
    # Column names (only first 23)
    column_names = [
        "گروه شخص",           # 0
        "کد شخص",             # 1
        "نوع شخصیت",          # 2
        "پیشوند",             # 3
        "نام / نام شرکت",     # 4
        "نام خانوادگی / مدیر عامل",  # 5
        "تاریخ تولد",         # 6
        "معرف",               # 7
        "تلفن 1",             # 8
        "موبایل",             # 9
        "نام شرکت",            # 10
        "نوع مودی",           # 11
        "کد شهر",             # 12
        "آدرس",               # 13
        "توضیحات",            # 14
        "ارز",                # 15
        "نرخ ارز",            # 16
        "ماهیت اول دوره",     # 17
        "مانده",              # 18
        "اعتبار",             # 19
        "فاكس",               # 20
        "شماره اقتصادی",     # 21
        "شماره ثبت"           # 22
    ]
    
    # Get all customers
    customers_result = await db.execute(select(models.Customer))
    customers = customers_result.scalars().all()
    
    updated_count = 0
    
    for customer in customers:
        if customer.excel_data:
            # Create a new dictionary with only the 23 standard columns
            cleaned_data = {}
            for col_name in column_names:
                if col_name in customer.excel_data:
                    cleaned_data[col_name] = customer.excel_data[col_name]
                else:
                    cleaned_data[col_name] = None
            
            customer.excel_data = cleaned_data
            db.add(customer)
            updated_count += 1
    
    await db.commit()
    
    return {
        "message": f"excel_data برای {updated_count} مشتری پاکسازی شد",
        "updated_count": updated_count
    }
