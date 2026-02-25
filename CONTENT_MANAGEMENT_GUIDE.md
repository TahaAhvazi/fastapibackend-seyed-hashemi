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
