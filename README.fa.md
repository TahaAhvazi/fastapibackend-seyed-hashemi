## راهنمای بک‌اند - سناریوی فاکتور (فارسی)

این سند برای تیم فرانت‌اند تهیه شده تا سناریوی ایجاد تا ارسال فاکتور را بر اساس نقش‌ها پیاده‌سازی کند.

### نقش‌ها و تغییر وضعیت‌ها
- ایجاد فاکتور (ادمین/حسابدار) → وضعیت: `warehouse_pending`
- رزرو موجودی (انبار) → وضعیت: `accountant_pending`
- تایید حسابداری (حسابدار) → وضعیت: `approved`
- ثبت ارسال و اطلاعات پستی/بیجک (انبار) → وضعیت: `shipped`
- ثبت تحویل (اختیاری، انبار) → وضعیت: `delivered`
- لغو (در صورت نیاز، ادمین/حسابدار) → وضعیت: `cancelled`

### احراز هویت و نقش‌ها
- همه‌ی اندپوینت‌ها نیاز به کاربر لاگین‌شده دارند.
- نقش‌ها: `admin`، `accountant`، `warehouse`.
- کنترل نقش و مجوز سمت سرور اعمال می‌شود.

### اندپوینت‌ها و استفاده در فرانت‌اند

#### 1) ایجاد فاکتور (ادمین/حسابدار)
- Method: POST
- Path: `/api/v1/invoices/`
- Body (InvoiceCreate):
```json
{
  "customer_id": 1,
  "payment_type": "cash", 
  "payment_breakdown": { "cash": 1000000, "check": 500000 },
  "items": [
    { "product_id": 1, "quantity": 5, "unit": "متر", "price": 350000 },
    { "product_id": 2, "quantity": 3, "unit": "متر", "price": 280000 }
  ]
}
```
- خروجی: شیء `Invoice` همراه با `items.product`، `customer(+bank_accounts)` و `created_by_user` (Eager Load).
- اقدام بعدی: انبار رزرو موجودی کند.

#### 2) رزرو موجودی (انبار/ادمین)
- Method: POST
- Path: `/api/v1/invoices/{invoice_id}/reserve`
- Body: ندارد
- نتیجه: بررسی و رزرو موجودی، ثبت تراکنش انبار، کاهش `product.quantity_available`، تغییر وضعیت به `accountant_pending`.
- اقدام بعدی: تایید حسابداری.

#### 3) تایید حسابداری (حسابدار/ادمین)
- Method: POST
- Path: `/api/v1/invoices/{invoice_id}/approve`
- Body: ندارد
- نتیجه: تغییر وضعیت به `approved`.
- اقدام بعدی: ارسال توسط انبار.

#### 4) ثبت ارسال (انبار/ادمین)
- Method: POST
- Path: `/api/v1/invoices/{invoice_id}/ship`
- Body (InvoiceTrackingUpdate):
```json
{
  "carrier_name": "تیپاکس",
  "tracking_code": "TPX-123456",
  "shipping_date": "2025-10-10",
  "number_of_packages": 3
}
```
- نتیجه: ثبت تراکنش ارسال در انبار (بدون تغییر تعداد، چون قبلا رزرو شده)، ذخیره `tracking_info`، تغییر وضعیت به `shipped`.
- اقدام بعدی: (اختیاری) ثبت تحویل.

#### 5) ثبت تحویل (اختیاری؛ انبار/ادمین)
- Method: POST
- Path: `/api/v1/invoices/{invoice_id}/deliver`
- Body: ندارد
- نتیجه: تغییر وضعیت به `delivered`.

#### 6) لغو فاکتور (ادمین/حسابدار)
- Method: POST
- Path: `/api/v1/invoices/{invoice_id}/cancel`
- Body: ندارد
- نتیجه: برگشت موجودی از طریق تراکنش انبار در صورت نیاز، تغییر وضعیت به `cancelled`.

### خواندن فاکتورها

#### لیست فاکتورها (با فیلتر و فیلتر خودکار نقش)
- Method: GET
- Path: `/api/v1/invoices/`
- Query: `status`, `customer_id`, `payment_type`, `created_by`, `start_date`, `end_date`, `skip`, `limit`
- نکته: نقش انبار فقط وضعیت‌های `warehouse_pending`، `approved`، `shipped` را می‌بیند. نقش حسابدار همه بجز `draft` را می‌بیند.

#### جزئیات فاکتور
- Method: GET
- Path: `/api/v1/invoices/{invoice_id}`
- نکته: روابط لازم به صورت Eager Load برمی‌گردند.

### نکات پیاده‌سازی در فرانت‌اند
- بعد از هر اکشن (ایجاد/رزرو/تایید/ارسال/تحویل/لغو)، با GET `/api/v1/invoices/{id}` جزئیات فاکتور را رفرش کنید تا وضعیت و روابط به‌روز شود.
- نمایش دکمه‌ها بر اساس نقش کاربر و `status`:
  - `warehouse_pending`: دکمه رزرو برای انبار
  - `accountant_pending`: دکمه تایید برای حسابدار
  - `approved`: دکمه ارسال برای انبار (فرم اطلاعات ارسال را نمایش دهید)
  - `shipped`: دکمه تحویل برای انبار (اختیاری)
  - لغو: برای ادمین/حسابدار در وضعیت‌های مجاز
- خطاها را مدیریت کنید:
  - `400`: انتقال وضعیت نامعتبر یا موجودی ناکافی
  - `403`: عدم دسترسی نقش
  - `404`: فاکتور یافت نشد

### نکات فنی
- همه پاسخ‌ها روابط مورد نیاز را Eager Load می‌کنند تا مشکل lazy-loading در async رخ ندهد.
- مسیر پایه API: `/api/v1`

در صورت نیاز به نمونه Payload بیشتر یا تغییرات، به تیم بک‌اند اطلاع دهید.
