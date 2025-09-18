from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.api import deps
from app.db.session import get_db

router = APIRouter()


@router.post("/income", response_model=schemas.IncomeReport)
async def get_income_report(
    *,
    db: AsyncSession = Depends(get_db),
    date_range: schemas.DateRangeParams,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Generate income report for a specific date range
    """
    # Handle default dates - last month if no dates provided
    today = datetime.now().date()
    if date_range.start_date and date_range.end_date:
        try:
            start_date = datetime.strptime(date_range.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(date_range.end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فرمت تاریخ نامعتبر است. از فرمت YYYY-MM-DD استفاده کنید."
            )
    else:
        # Default to last month
        end_date = today
        start_date = today - timedelta(days=30)
    
    # Get all invoices in the date range that are not cancelled
    query = select(models.Invoice).where(
        models.Invoice.created_at >= start_date,
        models.Invoice.created_at <= end_date,
        models.Invoice.status != schemas.InvoiceStatus.CANCELLED
    ).options(
        selectinload(models.Invoice.items).selectinload(models.InvoiceItem.product)
    )
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    # Calculate total revenue
    total_revenue = sum(invoice.total for invoice in invoices)
    
    # Calculate revenue by payment type
    revenue_by_payment_type = {}
    for payment_type in schemas.PaymentType:
        payment_invoices = [i for i in invoices if i.payment_type == payment_type]
        revenue_by_payment_type[payment_type.value] = sum(i.total for i in payment_invoices)
    
    # Calculate revenue by day
    revenue_by_day = {}
    for invoice in invoices:
        day = invoice.created_at.strftime("%Y-%m-%d")
        if day not in revenue_by_day:
            revenue_by_day[day] = 0
        revenue_by_day[day] += invoice.total
    
    # Sort revenue by day
    revenue_by_day = dict(sorted(revenue_by_day.items()))
    
    # Calculate total cost and profit
    total_cost = sum(
        sum(item.quantity * item.product.cost_price for item in invoice.items)
        for invoice in invoices
    )
    profit = total_revenue - total_cost
    
    # Get check status summary
    check_query = select(models.Check).where(
        models.Check.created_at >= start_date,
        models.Check.created_at <= end_date
    )
    check_result = await db.execute(check_query)
    checks = check_result.scalars().all()
    
    check_status_summary = {}
    for check_status in schemas.CheckStatus:
        status_checks = [c for c in checks if c.status == check_status]
        check_status_summary[check_status.value] = {
            "count": len(status_checks),
            "total_amount": sum(c.amount for c in status_checks)
        }
    
    period = f"{start_date.strftime('%Y-%m-%d')} تا {end_date.strftime('%Y-%m-%d')}"
    
    return {
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "profit": profit,
        "invoice_count": len(invoices),
        "period": period
    }


@router.post("/product-sales", response_model=List[schemas.ProductSalesReport])
async def get_product_sales_report(
    *,
    db: AsyncSession = Depends(get_db),
    date_range: schemas.DateRangeParams,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Generate product sales report for a specific date range
    """
    # Handle default dates - last month if no dates provided
    today = datetime.now().date()
    if date_range.start_date and date_range.end_date:
        try:
            start_date = datetime.strptime(date_range.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(date_range.end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فرمت تاریخ نامعتبر است. از فرمت YYYY-MM-DD استفاده کنید."
            )
    else:
        # Default to last month
        end_date = today
        start_date = today - timedelta(days=30)
    
    # Get all invoice items in the date range from non-cancelled invoices
    query = select(models.InvoiceItem).join(models.Invoice).join(models.Product).where(
        models.Invoice.created_at >= start_date,
        models.Invoice.created_at <= end_date,
        models.Invoice.status != schemas.InvoiceStatus.CANCELLED
    ).options(
        selectinload(models.InvoiceItem.product),
        selectinload(models.InvoiceItem.invoice)
    )
    result = await db.execute(query)
    invoice_items = result.scalars().all()
    
    # Group by product
    product_sales = {}
    for item in invoice_items:
        product_id = item.product_id
        if product_id not in product_sales:
            product_sales[product_id] = {
                "product_id": product_id,
                "product_name": item.product.name,
                "product_code": item.product.code,
                "quantity_sold": 0,
                "total_revenue": 0,
                "profit": 0
            }
        
        product_sales[product_id]["quantity_sold"] += item.quantity
        revenue = item.quantity * item.price
        cost = item.quantity * item.product.cost_price
        product_sales[product_id]["total_revenue"] += revenue
        product_sales[product_id]["profit"] += (revenue - cost)
    
    # Convert to list and sort by total revenue
    product_sales_list = list(product_sales.values())
    product_sales_list.sort(key=lambda x: x["total_revenue"], reverse=True)
    
    return product_sales_list


@router.post("/customer-sales", response_model=List[schemas.CustomerSalesReport])
async def get_customer_sales_report(
    *,
    db: AsyncSession = Depends(get_db),
    date_range: schemas.DateRangeParams,
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Generate customer sales report for a specific date range
    """
    # Handle default dates - last month if no dates provided
    today = datetime.now().date()
    if date_range.start_date and date_range.end_date:
        try:
            start_date = datetime.strptime(date_range.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(date_range.end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="فرمت تاریخ نامعتبر است. از فرمت YYYY-MM-DD استفاده کنید."
            )
    else:
        # Default to last month
        end_date = today
        start_date = today - timedelta(days=30)
    
    # Get all invoices in the date range that are not cancelled
    query = select(models.Invoice).join(models.Customer).where(
        models.Invoice.created_at >= start_date,
        models.Invoice.created_at <= end_date,
        models.Invoice.status != schemas.InvoiceStatus.CANCELLED
    ).options(
        selectinload(models.Invoice.customer).selectinload(models.Customer.bank_accounts),
        selectinload(models.Invoice.items),
        selectinload(models.Invoice.created_by_user)
    )
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    # Group by customer
    customer_sales = {}
    for invoice in invoices:
        customer_id = invoice.customer_id
        if customer_id not in customer_sales:
            customer_sales[customer_id] = {
                "customer_id": customer_id,
                "customer_name": f"{invoice.customer.first_name} {invoice.customer.last_name}",
                "total_purchases": 0,
                "invoice_count": 0,
                "last_purchase_date": None
            }
        
        customer_sales[customer_id]["total_purchases"] += invoice.total
        customer_sales[customer_id]["invoice_count"] += 1
        
        # Update last purchase date
        current_date = invoice.created_at.strftime("%Y-%m-%d")
        if not customer_sales[customer_id]["last_purchase_date"] or current_date > customer_sales[customer_id]["last_purchase_date"]:
            customer_sales[customer_id]["last_purchase_date"] = current_date
    
    # Convert to list and sort by total purchases
    customer_sales_list = list(customer_sales.values())
    customer_sales_list.sort(key=lambda x: x["total_purchases"], reverse=True)
    
    return customer_sales_list


@router.get("/dashboard", response_model=schemas.DashboardSummary)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get dashboard summary data
    """
    # Calculate date ranges
    today = datetime.now().date()
    start_of_today = datetime.combine(today, datetime.min.time())
    start_of_month = datetime(today.year, today.month, 1)
    start_of_last_month = (start_of_month - timedelta(days=1)).replace(day=1)
    end_of_last_month = start_of_month - timedelta(days=1)
    
    # Get today's revenue
    today_revenue_query = select(func.sum(models.Invoice.total)).where(
        models.Invoice.created_at >= start_of_today,
        models.Invoice.status != schemas.InvoiceStatus.CANCELLED
    )
    today_revenue_result = await db.execute(today_revenue_query)
    today_revenue = today_revenue_result.scalar() or 0
    
    # Get this month's revenue
    month_revenue_query = select(func.sum(models.Invoice.total)).where(
        models.Invoice.created_at >= start_of_month,
        models.Invoice.status != schemas.InvoiceStatus.CANCELLED
    )
    month_revenue_result = await db.execute(month_revenue_query)
    month_revenue = month_revenue_result.scalar() or 0
    
    # Get last month's revenue
    last_month_revenue_query = select(func.sum(models.Invoice.total)).where(
        models.Invoice.created_at >= start_of_last_month,
        models.Invoice.created_at <= end_of_last_month,
        models.Invoice.status != schemas.InvoiceStatus.CANCELLED
    )
    last_month_revenue_result = await db.execute(last_month_revenue_query)
    last_month_revenue = last_month_revenue_result.scalar() or 0
    
    # Calculate month-over-month growth
    if last_month_revenue > 0:
        month_growth = ((month_revenue - last_month_revenue) / last_month_revenue) * 100
    else:
        month_growth = 100 if month_revenue > 0 else 0
    
    # Get invoice status counts
    invoice_status_counts = {}
    for status in schemas.InvoiceStatus:
        status_query = select(func.count()).select_from(models.Invoice).where(models.Invoice.status == status)
        status_result = await db.execute(status_query)
        invoice_status_counts[status.value] = status_result.scalar() or 0
    
    # Get check status counts
    check_status_counts = {}
    for status in schemas.CheckStatus:
        status_query = select(func.count()).select_from(models.Check).where(models.Check.status == status)
        status_result = await db.execute(status_query)
        check_status_counts[status.value] = status_result.scalar() or 0
    
    # Get low stock products
    low_stock_query = select(models.Product).where(models.Product.quantity_available < 10).limit(5)
    low_stock_result = await db.execute(low_stock_query)
    low_stock_products = low_stock_result.scalars().all()
    
    low_stock_items = [
        {
            "id": product.id,
            "name": product.name,
            "code": product.code,
            "quantity": product.quantity_available
        }
        for product in low_stock_products
    ]
    
    # Get recent invoices
    recent_invoices_query = select(models.Invoice).options(
        selectinload(models.Invoice.customer).selectinload(models.Customer.bank_accounts),
        selectinload(models.Invoice.created_by_user)
    ).order_by(desc(models.Invoice.created_at)).limit(5)
    recent_invoices_result = await db.execute(recent_invoices_query)
    recent_invoices = recent_invoices_result.scalars().all()
    
    recent_invoice_items = [
        {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "customer_name": f"{invoice.customer.first_name} {invoice.customer.last_name}",
            "total": invoice.total,
            "status": invoice.status.value,
            "created_at": invoice.created_at.isoformat()
        }
        for invoice in recent_invoices
    ]
    
    # Get top customers this month
    top_customers_query = select(
        models.Customer,
        func.sum(models.Invoice.total).label("total_purchases")
    ).join(models.Invoice).where(
        models.Invoice.created_at >= start_of_month,
        models.Invoice.status != schemas.InvoiceStatus.CANCELLED
    ).group_by(models.Customer.id).order_by(desc("total_purchases")).limit(5)
    
    top_customers_result = await db.execute(top_customers_query)
    top_customers_data = top_customers_result.all()
    
    top_customers = [
        {
            "id": customer.id,
            "name": f"{customer.first_name} {customer.last_name}",
            "total_purchases": float(total_purchases)
        }
        for customer, total_purchases in top_customers_data
    ]
    
    # Return dashboard summary matching DashboardSummary schema
    # Get top selling products this month
    top_products_query = select(
        models.Product,
        func.sum(models.InvoiceItem.quantity).label("quantity_sold")
    ).join(
        models.InvoiceItem, models.Product.id == models.InvoiceItem.product_id
    ).join(
        models.Invoice, models.InvoiceItem.invoice_id == models.Invoice.id
    ).where(
        models.Invoice.created_at >= start_of_month,
        models.Invoice.status != schemas.InvoiceStatus.CANCELLED
    ).group_by(models.Product.id).order_by(desc("quantity_sold")).limit(5)
    
    top_products_result = await db.execute(top_products_query)
    top_products_data = top_products_result.all()
    
    top_selling_products = [
        {
            "product_id": product.id,
            "product_name": product.name,
            "quantity_sold": int(quantity_sold)
        }
        for product, quantity_sold in top_products_data
    ]
    
    # Return dashboard summary
    return {
        "total_revenue_current_month": month_revenue,
        "total_revenue_previous_month": last_month_revenue,
        "revenue_change_percentage": month_growth,
        "pending_invoices_count": invoice_status_counts.get("pending", 0),
        "checks_in_progress_count": check_status_counts.get("in_progress", 0),
        "low_stock_products_count": len(low_stock_items),
        "top_selling_products": top_selling_products,
        "recent_invoices": recent_invoice_items
    }


@router.get("/customer/{customer_id}/balance", response_model=Dict[str, Any])
async def get_customer_balance(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_admin_or_accountant_user),
) -> Any:
    """
    Get customer balance and financial summary
    """
    # Check if customer exists
    customer_result = await db.execute(select(models.Customer).where(models.Customer.id == customer_id))
    customer = customer_result.scalars().first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مشتری یافت نشد",  # Customer not found
        )
    
    # Get all invoices for this customer that are not cancelled
    invoice_query = select(models.Invoice).where(
        models.Invoice.customer_id == customer_id,
        models.Invoice.status != schemas.InvoiceStatus.CANCELLED
    )
    invoice_result = await db.execute(invoice_query)
    invoices = invoice_result.scalars().all()
    
    # Calculate total purchases
    total_purchases = sum(invoice.total for invoice in invoices)
    
    # Get all checks for this customer that are processed (passed)
    check_query = select(models.Check).where(
        models.Check.customer_id == customer_id,
        models.Check.status == schemas.CheckStatus.PROCESSED
    )
    check_result = await db.execute(check_query)
    processed_checks = check_result.scalars().all()
    
    # Calculate total paid
    total_paid = sum(check.amount for check in processed_checks)
    
    # Get checks in progress
    in_progress_check_query = select(models.Check).where(
        models.Check.customer_id == customer_id,
        models.Check.status == schemas.CheckStatus.IN_PROGRESS
    )
    in_progress_check_result = await db.execute(in_progress_check_query)
    in_progress_checks = in_progress_check_result.scalars().all()
    
    # Calculate balance
    balance = total_purchases - total_paid
    
    return {
        "customer_id": customer_id,
        "customer_name": f"{customer.first_name} {customer.last_name}",
        "total_purchases": total_purchases,
        "total_paid": total_paid,
        "balance": balance,
        "invoice_count": len(invoices),
        "checks_in_progress": [
            {
                "id": check.id,
                "check_number": check.check_number,
                "amount": check.amount,
                "due_date": check.due_date.isoformat() if check.due_date else None
            }
            for check in in_progress_checks
        ],
        "checks_in_progress_total": sum(check.amount for check in in_progress_checks)
    }