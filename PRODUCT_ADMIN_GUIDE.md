# راهنمای اضافه کردن محصولات در پنل ادمین

این راهنما برای برنامه‌نویس فرانت‌اند است تا بداند چطور محصولات را در پنل ادمین اضافه کند که با API سرور هماهنگ باشد.

## 📋 فهرست مطالب
1. [انواع محصولات](#انواع-محصولات)
2. [فیلدهای مشترک](#فیلدهای-مشترک)
3. [محصولات سری](#محصولات-سری)
4. [محصولات غیرسری (با رنگ‌بندی)](#محصولات-غیرسری-با-رنگ‌بندی)
5. [API Endpoint](#api-endpoint)
6. [مثال‌های کامل](#مثال‌های-کامل)

---

## انواع محصولات

محصولات به **دو دسته** تقسیم می‌شوند:

### 1️⃣ محصولات سری (`is_series = true`)
- به صورت سری فروخته می‌شوند
- مشتری نمی‌تواند رنگ انتخاب کند
- باید سری‌های موجود و موجودی هر سری را تعریف کنید

### 2️⃣ محصولات غیرسری (`is_series = false`)
- امکان انتخاب رنگ دارند
- مشتری می‌تواند رنگ موردنظر را انتخاب کند
- باید رنگ‌های موجود و موجودی هر رنگ را تعریف کنید

---

## فیلدهای مشترک

این فیلدها برای **همه محصولات** الزامی هستند:

| فیلد | نوع | الزامی | توضیحات |
|------|-----|--------|---------|
| `code` | string | ✅ بله | کد یکتای محصول (مثلاً: "P001") |
| `name` | string | ✅ بله | نام محصول |
| `category` | string | ✅ بله | دسته‌بندی (مثلاً: "ساتن"، "کتان") |
| `unit` | string | ✅ بله | واحد اندازه‌گیری (مثلاً: "متر"، "یارد"، "طاقه") |
| `is_series` | boolean | ✅ بله | آیا محصول سری است؟ (`true` یا `false`) |

**فیلدهای اختیاری مشترک:**
- `description`: توضیحات محصول
- `is_available`: موجود است؟ (پیش‌فرض: `true`)
- `visible`: نمایش در سایت؟ (پیش‌فرض: `true`)
- `shrinkage`: ابرفت
- `width`: عرض
- `usage`: کاربرد
- `season`: فصل
- `weave_type`: نوع بافت
- `colors`: رنگ‌ها (رشته متنی - فقط برای نمایش)
- `images`: فایل‌های عکس محصول

---

## محصولات سری

### فیلدهای الزامی برای محصولات سری:

| فیلد | نوع | فرمت | توضیحات |
|------|-----|------|---------|
| `is_series` | boolean | `true` | باید `true` باشد |
| `series_numbers` | JSON string | `"[1, 2, 3, 4, 5]"` | لیست شماره سری‌ها |
| `series_inventory` | JSON string | `"[10, 20, 30, 40, 50]"` | لیست موجودی هر سری |

### ⚠️ نکات مهم:
1. **تعداد سری‌ها باید با تعداد موجودی برابر باشد**
   - اگر 5 سری دارید: `series_numbers` باید 5 عدد داشته باشد
   - `series_inventory` هم باید 5 عدد داشته باشد

2. **فرمت JSON String:**
   - در Form Data باید به صورت **string** ارسال شود
   - مثال: `series_numbers = "[1, 2, 3, 4, 5]"` (نه array!)

3. **مثال:**
   ```
   series_numbers: "[1, 2, 3, 4, 5]"
   series_inventory: "[10, 20, 30, 40, 50]"
   ```
   یعنی:
   - سری 1: موجودی 10
   - سری 2: موجودی 20
   - سری 3: موجودی 30
   - سری 4: موجودی 40
   - سری 5: موجودی 50

### فیلدهای غیرمرتبط (باید null باشند):
- `available_colors`: باید `null` یا ارسال نشود
- `color_inventory`: باید `null` یا ارسال نشود

---

## محصولات غیرسری (با رنگ‌بندی)

### فیلدهای الزامی برای محصولات غیرسری:

| فیلد | نوع | فرمت | توضیحات |
|------|-----|------|---------|
| `is_series` | boolean | `false` | باید `false` باشد |
| `available_colors` | JSON string | `"[\"قرمز\", \"آبی\", \"سبز\"]"` | لیست رنگ‌های موجود |
| `color_inventory` | JSON string | `"[\"20\", \"15\", \"10\"]"` | لیست موجودی هر رنگ |

### ⚠️ نکات مهم:
1. **تعداد رنگ‌ها باید با تعداد موجودی برابر باشد**
   - اگر 3 رنگ دارید: `available_colors` باید 3 رنگ داشته باشد
   - `color_inventory` هم باید 3 عدد داشته باشد

2. **فرمت JSON String:**
   - در Form Data باید به صورت **string** ارسال شود
   - مثال: `available_colors = "[\"قرمز\", \"آبی\", \"سبز\"]"` (نه array!)

3. **مثال:**
   ```
   available_colors: "[\"قرمز\", \"آبی\", \"سبز\"]"
   color_inventory: "[\"20\", \"15\", \"10\"]"
   ```
   یعنی:
   - رنگ قرمز: موجودی 20
   - رنگ آبی: موجودی 15
   - رنگ سبز: موجودی 10

### فیلدهای غیرمرتبط (باید null باشند):
- `series_numbers`: باید `null` یا ارسال نشود
- `series_inventory`: باید `null` یا ارسال نشود

---

## API Endpoint

### ایجاد محصول جدید:
```
POST /api/v1/products/
Content-Type: multipart/form-data
Authorization: Bearer {token}
```

### به‌روزرسانی محصول:
```
PUT /api/v1/products/{product_id}
Content-Type: multipart/form-data
Authorization: Bearer {token}
```

---

## مثال‌های کامل

### مثال 1: ایجاد محصول سری

**فرم HTML:**
```html
<form enctype="multipart/form-data">
  <input name="code" value="P001" required>
  <input name="name" value="پارچه کتان سری" required>
  <input name="category" value="کتان" required>
  <input name="unit" value="متر" required>
  <input type="checkbox" name="is_series" checked> <!-- true -->
  <input name="series_numbers" value='[1, 2, 3, 4, 5]' required>
  <input name="series_inventory" value='[10, 20, 30, 40, 50]' required>
  <input type="file" name="images" multiple>
</form>
```

**JavaScript (Fetch API):**
```javascript
const formData = new FormData();
formData.append('code', 'P001');
formData.append('name', 'پارچه کتان سری');
formData.append('category', 'کتان');
formData.append('unit', 'متر');
formData.append('is_series', 'true'); // یا true
formData.append('series_numbers', JSON.stringify([1, 2, 3, 4, 5]));
formData.append('series_inventory', JSON.stringify([10, 20, 30, 40, 50]));

// برای عکس‌ها
const imageFiles = document.querySelector('input[type="file"]').files;
for (let i = 0; i < imageFiles.length; i++) {
  formData.append('images', imageFiles[i]);
}

fetch('/api/v1/products/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
```

---

### مثال 2: ایجاد محصول غیرسری

**فرم HTML:**
```html
<form enctype="multipart/form-data">
  <input name="code" value="P002" required>
  <input name="name" value="پارچه ساتن" required>
  <input name="category" value="ساتن" required>
  <input name="unit" value="متر" required>
  <!-- is_series را ارسال نکنید یا false بگذارید -->
  <input name="available_colors" value='["قرمز", "آبی", "سبز"]' required>
  <input name="color_inventory" value='["20", "15", "10"]' required>
  <input type="file" name="images" multiple>
</form>
```

**JavaScript (Fetch API):**
```javascript
const formData = new FormData();
formData.append('code', 'P002');
formData.append('name', 'پارچه ساتن');
formData.append('category', 'ساتن');
formData.append('unit', 'متر');
formData.append('is_series', 'false'); // یا false
formData.append('available_colors', JSON.stringify(['قرمز', 'آبی', 'سبز']));
formData.append('color_inventory', JSON.stringify(['20', '15', '10']));

// برای عکس‌ها
const imageFiles = document.querySelector('input[type="file"]').files;
for (let i = 0; i < imageFiles.length; i++) {
  formData.append('images', imageFiles[i]);
}

fetch('/api/v1/products/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
```

---

### مثال 3: UI Component برای سری‌ها

```javascript
// Component برای مدیریت سری‌ها
const SeriesManager = () => {
  const [seriesList, setSeriesList] = useState([
    { number: 1, inventory: 10 },
    { number: 2, inventory: 20 },
    { number: 3, inventory: 30 }
  ]);

  const handleSubmit = () => {
    const seriesNumbers = seriesList.map(s => s.number);
    const seriesInventory = seriesList.map(s => s.inventory);
    
    formData.append('series_numbers', JSON.stringify(seriesNumbers));
    formData.append('series_inventory', JSON.stringify(seriesInventory));
  };
};
```

---

### مثال 4: UI Component برای رنگ‌ها

```javascript
// Component برای مدیریت رنگ‌ها
const ColorManager = () => {
  const [colors, setColors] = useState([
    { color: 'قرمز', inventory: '20' },
    { color: 'آبی', inventory: '15' },
    { color: 'سبز', inventory: '10' }
  ]);

  const handleSubmit = () => {
    const availableColors = colors.map(c => c.color);
    const colorInventory = colors.map(c => c.inventory);
    
    formData.append('available_colors', JSON.stringify(availableColors));
    formData.append('color_inventory', JSON.stringify(colorInventory));
  };
};
```

---

## ✅ چک‌لیست اعتبارسنجی

### برای محصولات سری:
- [ ] `is_series = true`
- [ ] `series_numbers` تعریف شده و لیست معتبر است
- [ ] `series_inventory` تعریف شده و لیست معتبر است
- [ ] تعداد سری‌ها = تعداد موجودی
- [ ] `available_colors` و `color_inventory` ارسال نشده یا null هستند

### برای محصولات غیرسری:
- [ ] `is_series = false`
- [ ] `available_colors` تعریف شده و لیست معتبر است
- [ ] `color_inventory` تعریف شده و لیست معتبر است
- [ ] تعداد رنگ‌ها = تعداد موجودی
- [ ] `series_numbers` و `series_inventory` ارسال نشده یا null هستند

---

## 🔍 تست و Debug

### بررسی محصول ایجاد شده:
```bash
GET /api/v1/products/{product_id}
```

### Response برای محصول سری:
```json
{
  "id": 1,
  "code": "P001",
  "name": "پارچه کتان سری",
  "is_series": true,
  "series_numbers": [1, 2, 3, 4, 5],
  "series_inventory": [10, 20, 30, 40, 50],
  "available_colors": null,
  "color_inventory": null
}
```

### Response برای محصول غیرسری:
```json
{
  "id": 2,
  "code": "P002",
  "name": "پارچه ساتن",
  "is_series": false,
  "series_numbers": null,
  "series_inventory": null,
  "available_colors": ["قرمز", "آبی", "سبز"],
  "color_inventory": ["20", "15", "10"]
}
```

---

## ⚠️ خطاهای رایج

### خطا 1: "برای محصولات سری، series_inventory و series_numbers الزامی هستند"
**علت:** `is_series = true` اما `series_numbers` یا `series_inventory` تعریف نشده

### خطا 2: "تعداد رنگ‌ها باید با تعداد موجودی هر رنگ برابر باشد"
**علت:** تعداد عناصر `available_colors` با `color_inventory` برابر نیست

### خطا 3: "فرمت series_numbers نامعتبر است"
**علت:** JSON string معتبر نیست - باید `"[1, 2, 3]"` باشد نه `[1, 2, 3]`

---

## 📝 نکات نهایی

1. **همیشه از `JSON.stringify()` استفاده کنید** برای تبدیل array به JSON string
2. **تعداد عناصر را چک کنید** قبل از ارسال
3. **برای محصولات سری:** فقط `series_numbers` و `series_inventory` را ارسال کنید
4. **برای محصولات غیرسری:** فقط `available_colors` و `color_inventory` را ارسال کنید
5. **عکس‌ها اختیاری هستند** اما می‌توانید چند عکس ارسال کنید

---

## 📞 پشتیبانی

اگر مشکلی پیش آمد، بررسی کنید:
1. آیا `is_series` به درستی تنظیم شده؟
2. آیا JSON string‌ها معتبر هستند؟
3. آیا تعداد عناصر لیست‌ها برابر است؟
4. آیا فیلدهای غیرمرتبط null هستند؟

