# راهنمای مدیریت تولید محتوا (Content Management Guide)

این مستند شامل نحوه استفاده از اندپوینت‌های جدید برای مدیریت محتوا، اعضای سازمان، ویدیوها و کمپین‌ها می‌باشد.

## نقش جدید: مدیر محتوا (Content Manager)
نقش جدید `content_manager` به سیستم اضافه شده است. مدیر سیستم (Admin) می‌تواند یوزرهایی با این نقش ایجاد کند. این نقش دسترسی‌های زیر را دارد:
- مدیریت اعضای سازمان
- مدیریت ویدیوهای محتوایی
- مدیریت مقالات (Articles)
- مدیریت کمپین‌های تبلیغاتی

---

## ۱. مدیریت اعضای سازمان (Organization Members)

### ایجاد عضو جدید (Create Member)
**Endpoint:** `POST /api/v1/content/members`
**Auth Required:** Admin or Content Manager
**Content-Type:** `multipart/form-data`

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/content/members' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@your_profile_image.jpg' \
  -F 'full_name=محمد احمدی' \
  -F 'duty=مدیر هنری'
```

### دریافت لیست اعضا (Get Members)
**Endpoint:** `GET /api/v1/content/members`

```bash
curl -X 'GET' 'http://localhost:8000/api/v1/content/members'
```

---

## ۲. مدیریت ویدیوها (Content Videos)

### آپلود ویدیو (Upload Video)
**Endpoint:** `POST /api/v1/content/videos`
**Auth Required:** Admin or Content Manager
**Content-Type:** `multipart/form-data`

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/content/videos' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@tutorial_video.mp4' \
  -F 'title=آموزش انتخاب پارچه' \
  -F 'description=در این ویدیو یاد می‌گیرید چطور بهترین پارچه را انتخاب کنید.'
```

### حذف ویدیو (Delete Video)
**Endpoint:** `DELETE /api/v1/content/videos/{video_id}`

```bash
curl -X 'DELETE' 'http://localhost:8000/api/v1/content/videos/1' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

---

## ۳. مدیریت مقالات (Articles)
دسترسی به اندپوینت‌های موجود در `/api/v1/site/articles` برای نقش `content_manager` باز شده است.

### ایجاد مقاله (Create Article)
**Endpoint:** `POST /api/v1/site/articles`

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/site/articles' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: multipart/form-data' \
  -F 'title=روندهای مد ۱۴۰۳' \
  -F 'slug=fashion-trends-1403' \
  -F 'content=متن کامل مقاله اینجا قرار می‌گیرد...' \
  -F 'is_published=true'
```

---

## ۴. مدیریت کمپین‌ها (Campaigns)

### ایجاد کمپین جدید (Create Campaign)
**Endpoint:** `POST /api/v1/content/campaigns`
**Auth Required:** Admin or Content Manager
**Content-Type:** `multipart/form-data`

در این بخش باید لیست آیدی محصولات به صورت یک رشته JSON ارسال شود.

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/content/campaigns' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@campaign_banner.jpg' \
  -F 'title=جشنواره بهاره' \
  -F 'description=تخفیف‌های ویژه محصولات بهاره' \
  -F 'product_ids=[1, 2, 5]'
```

### نمونه پاسخ JSON برای کمپین:
```json
{
  "id": 1,
  "title": "جشنواره بهاره",
  "description": "تخفیف‌های ویژه محصولات بهاره",
  "banner_url": "/uploads/campaigns/20240520_120000_banner.jpg",
  "products": [
    {
      "id": 1,
      "code": "P001",
      "name": "پارچه نخی",
      "category": "نخی",
      "unit": "متر"
    },
    {
      "id": 2,
      "code": "P002",
      "name": "پارچه کتان",
      "category": "کتان",
      "unit": "متر"
    }
  ],
  "created_at": "2024-05-20T12:00:00",
  "updated_at": "2024-05-20T12:00:00"
}
```

---

## ۵. مدیریت اطلاعات سایت (Site Info)
**Endpoint:** `POST /api/v1/content/site-info`
**Auth Required:** Admin or Content Manager
**Content-Type:** `multipart/form-data`

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/content/site-info' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: multipart/form-data' \
  -F 'about_us=درباره ما...' \
  -F 'satisfied_customers=مشتری راضی...' \
  -F 'product_info=محصول ...' \
  -F 'experience_years=سال تجربه ...' \
  -F 'buy_guide_1=راهنمای خرید1 ...' \
  -F 'buy_guide_2=راهنمای خرید2 ...' \
  -F 'buy_guide_3=راهنمای خرید3 ...' \
  -F 'buy_guide_4=راهنمای خرید4 ...' \
  -F 'phone_1=شماره تماس 1 ...' \
  -F 'phone_2=شماره تماس 2 ...' \
  -F 'phone_3=شماره تماس 3 ...' \
  -F 'phone_4=شماره تماس 4 ...' \
  -F 'phone_5=شماره تماس 5 ...' \
  -F 'address=آدرس ...' \
  -F 'working_hours=ساعات کاری ...' \
  -F 'about_rans_text_2=توضیحات 2 درباره رنس تکس ...' \
  -F 'fabric_variety_count=تعداد تنوع پارچه ...' \
  -F 'satisfied_customers_count=تعداد مشتری راضی ...' \
  -F 'our_mission=ماموریت ما ...' \
  -F 'our_vision=چشم انداز ما ...' \
  -F 'our_history_1=تاریخچه ما 1 ...' \
  -F 'our_history_2=تاریخچه ما 2 ...' \
  -F 'our_history_3=تاریخچه ما 3 ...' \
  -F 'our_history_4=تاریخچه ما 4 ...' \
  -F 'our_history_5=تاریخچه ما 5 ...' \
  -F 'instagram_link=لینک اینستگرام ...' \
  -F 'whatsapp_link=لینک واتسپ ...' \
  -F 'telegram_link=لینک تلگرام ...' \
  -F 'email=ایمیل ...'
```

خروجی شامل کلیدهایی است که به‌روز شده‌اند:
```json
{
  "updated": [
    "about_us",
    "satisfied_customers",
    "product_info",
    "experience_years",
    "buy_guide_1",
    "buy_guide_2",
    "buy_guide_3",
    "buy_guide_4",
    "phone_1",
    "phone_2",
    "phone_3",
    "phone_4",
    "phone_5",
    "address",
    "working_hours",
    "about_rans_text_2",
    "fabric_variety_count",
    "satisfied_customers_count",
    "our_mission",
    "our_vision",
    "our_history_1",
    "our_history_2",
    "our_history_3",
    "our_history_4",
    "our_history_5",
    "instagram_link",
    "whatsapp_link",
    "telegram_link",
    "email"
  ]
}
```

### دریافت اطلاعات سایت (Get Site Info)
**Endpoint:** `GET /api/v1/content/site-info`

```bash
curl -X 'GET' \
  'http://localhost:8000/api/v1/content/site-info' \
  -H 'accept: application/json'
```

نمونه پاسخ:
```json
{
  "about_us": "درباره ما...",
  "satisfied_customers": "مشتری راضی...",
  "product_info": "محصول ...",
  "experience_years": "سال تجربه ...",
  "buy_guide_1": "راهنمای خرید1 ...",
  "buy_guide_2": "راهنمای خرید2 ...",
  "buy_guide_3": "راهنمای خرید3 ...",
  "buy_guide_4": "راهنمای خرید4 ...",
  "phone_1": "شماره تماس 1 ...",
  "phone_2": "شماره تماس 2 ...",
  "phone_3": "شماره تماس 3 ...",
  "phone_4": "شماره تماس 4 ...",
  "phone_5": "شماره تماس 5 ...",
  "address": "آدرس ...",
  "working_hours": "ساعات کاری ...",
  "about_rans_text_2": "توضیحات 2 درباره رنس تکس ...",
  "fabric_variety_count": "تعداد تنوع پارچه ...",
  "satisfied_customers_count": "تعداد مشتری راضی ...",
  "our_mission": "ماموریت ما ...",
  "our_vision": "چشم انداز ما ...",
  "our_history_1": "تاریخچه ما 1 ...",
  "our_history_2": "تاریخچه ما 2 ...",
  "our_history_3": "تاریخچه ما 3 ...",
  "our_history_4": "تاریخچه ما 4 ...",
  "our_history_5": "تاریخچه ما 5 ...",
  "instagram_link": "لینک اینستگرام ...",
  "whatsapp_link": "لینک واتسپ ...",
  "telegram_link": "لینک تلگرام ...",
  "email": "ایمیل ..."
}
```

### ویرایش اطلاعات سایت (Update Site Info)
**Endpoint:** `PUT /api/v1/content/site-info`
**Auth Required:** Admin or Content Manager
**Content-Type:** `multipart/form-data`

```bash
curl -X 'PUT' \
  'http://localhost:8000/api/v1/content/site-info' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: multipart/form-data' \
  -F 'about_us=متن جدید درباره ما...' \
  -F 'phone_1=شماره جدید 1 ...' \
  -F 'instagram_link=لینک جدید اینستگرام ...'
```

خروجی:
```json
{
  "updated": ["about_us", "phone_1", "instagram_link"]
}
```

---

## ۵. مدیریت کاربران (Admin Only)
مدیر سیستم می‌تواند کاربر با نقش `content_manager` ایجاد کند.
**Endpoint:** `POST /api/v1/auth/register`
**Auth Required:** Admin
**Content-Type:** `application/json`
**Endpoint:** `POST /api/v1/users/`

```json
{
  "email": "manager@example.com",
  "password": "securepassword",
  "first_name": "علی",
  "last_name": "رضایی",
  "role": "content_manager"
}
