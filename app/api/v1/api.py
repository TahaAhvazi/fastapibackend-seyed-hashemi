from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, products, customers, invoices, inventory, checks, reports, uploads, carts, site_management

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(checks.router, prefix="/checks", tags=["checks"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(carts.router, prefix="/carts", tags=["carts"])
api_router.include_router(site_management.router, prefix="/site", tags=["مدیریت سایت"])