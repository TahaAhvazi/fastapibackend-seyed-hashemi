# Rancetxe Backend - Invoice Workflow Guide

این راهنما برای تیم فرانت‌اند آماده شده تا جریان کاری ایجاد تا ارسال فاکتور را با نقش‌های مختلف پیاده‌سازی کند.

This guide helps the frontend team implement the invoice workflow across roles.

## Roles and Status Flow
- Admin/Accountant creates invoice → status: `warehouse_pending`
- Warehouse reserves stock → status: `accountant_pending`
- Accountant approves invoice → status: `approved`
- Warehouse ships (adds tracking/waybill info) → status: `shipped`
- Optional: Warehouse marks delivered → status: `delivered`
- Optional: Admin/Accountant can cancel at permitted states → status: `cancelled`

## Authentication
- All endpoints require an authenticated user. Roles: `admin`, `accountant`, `warehouse`.
- Role-specific endpoints are validated server-side.

## Endpoints Overview

### 1) Create Invoice (Admin/Accountant)
- Method: POST
- Path: `/api/v1/invoices/`
- Body (InvoiceCreate):
```json
{
  "customer_id": 1,
  "payment_type": "cash", // or "check" or "mixed"
  "payment_breakdown": { "cash": 1000000, "check": 500000 }, // optional for mixed
  "items": [
    { "product_id": 1, "quantity": 5, "unit": "متر", "price": 350000 },
    { "product_id": 2, "quantity": 3, "unit": "متر", "price": 280000 }
  ]
}
```
- Response: `Invoice` with `items.product`, `customer(+bank_accounts)`, `created_by_user` eagerly loaded.
- Next action (Warehouse): Reserve stock.

### 2) Reserve Stock (Warehouse/Admin)
- Method: POST
- Path: `/api/v1/invoices/{invoice_id}/reserve`
- Body: none
- Effect: checks inventory, creates reservation transactions, decrements `product.quantity_available`, sets status → `accountant_pending`.
- Next action (Accountant): Approve.

### 3) Approve Invoice (Accountant/Admin)
- Method: POST
- Path: `/api/v1/invoices/{invoice_id}/approve`
- Body: none
- Effect: status → `approved`.
- Next action (Warehouse): Ship.

### 4) Ship Invoice (Warehouse/Admin)
- Method: POST
- Path: `/api/v1/invoices/{invoice_id}/ship`
- Body (InvoiceTrackingUpdate):
```json
{
  "carrier_name": "Tipax",
  "tracking_code": "TPX-123456",
  "shipping_date": "2025-10-10",
  "number_of_packages": 3
}
```
- Effect: creates shipping inventory transactions (no further quantity change), attaches `tracking_info`, status → `shipped`.
- Next action (Warehouse, optional): Deliver.

### 5) Mark Delivered (Warehouse/Admin)
- Method: POST
- Path: `/api/v1/invoices/{invoice_id}/deliver`
- Body: none
- Effect: status → `delivered`.

### 6) Cancel Invoice (Admin/Accountant)
- Method: POST
- Path: `/api/v1/invoices/{invoice_id}/cancel`
- Body: none
- Effect: returns reserved/used stock via inventory transactions as applicable, status → `cancelled`.

## Reading Invoices

### List Invoices (auto role filtering)
- Method: GET
- Path: `/api/v1/invoices/`
- Query params: `status`, `customer_id`, `payment_type`, `created_by`, `start_date`, `end_date`, `skip`, `limit`
- Notes: Warehouse sees `warehouse_pending`, `approved`, `shipped`. Accountant sees all except `draft`.

### Get Invoice by ID
- Method: GET
- Path: `/api/v1/invoices/{invoice_id}`
- Notes: Returns `items.product`, `customer(+bank_accounts)`, `created_by_user` eagerly loaded.

## Frontend Implementation Notes
- After each action, re-fetch invoice details via GET `/api/v1/invoices/{id}` to refresh status and relations.
- Show action buttons based on both role and current `status`:
  - `warehouse_pending`: Warehouse can Reserve
  - `accountant_pending`: Accountant can Approve
  - `approved`: Warehouse can Ship (show form for tracking info)
  - `shipped`: Warehouse can Deliver (optional)
  - `cancel`: Admin/Accountant may Cancel (where allowed)
- Handle 400/403 responses to provide proper UI feedback on invalid transitions or permissions.

## Error Handling
- `400 Bad Request`: invalid state transitions or insufficient stock
- `403 Forbidden`: user lacks role permissions
- `404 Not Found`: invoice not found

## Data Loading
- Responses have relationships eagerly loaded to avoid lazy-loading issues in async contexts.

## Versioning & Base URL
- Base path: `/api/v1`

If anything changes or more sample payloads are needed, please ping the backend team.