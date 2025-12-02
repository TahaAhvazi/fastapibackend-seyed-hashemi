"""
Migration script برای:
1. اضافه کردن فیلد hashed_password به جدول customer
2. اضافه کردن فیلد customer_id به جدول cart
3. حذف مشتری‌هایی که شماره (mobile یا phone) ندارند
4. تنظیم پسورد 123456789 برای بقیه مشتری‌ها
"""
import sqlite3
import os
import sys
import io

# تنظیم encoding به UTF-8 برای Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# اضافه کردن مسیر پروژه به sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
except ImportError:
    print("Error: passlib is not installed. Please install requirements.txt")
    sys.exit(1)

# Path to database
db_path = "rancetxe.db"

if not os.path.exists(db_path):
    print(f"Error: Database file {db_path} not found!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("Starting migration...")
    
    # 1. اضافه کردن فیلد hashed_password به جدول customer
    print("Adding hashed_password field to customer table...")
    try:
        cursor.execute("ALTER TABLE customer ADD COLUMN hashed_password VARCHAR")
        print("OK: hashed_password field added")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("WARNING: hashed_password field already exists")
        else:
            raise
    
    # 2. اضافه کردن فیلد customer_id به جدول cart
    print("Adding customer_id field to cart table...")
    try:
        cursor.execute("ALTER TABLE cart ADD COLUMN customer_id INTEGER")
        # اضافه کردن foreign key constraint (SQLite محدودیت دارد، اما index می‌سازیم)
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_cart_customer_id ON cart (customer_id)")
        print("OK: customer_id field added")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print("WARNING: customer_id field already exists")
        else:
            raise
    
    # 3. پیدا کردن و حذف مشتری‌هایی که شماره ندارند
    print("Searching for customers without phone numbers...")
    cursor.execute("""
        SELECT id, first_name, last_name, mobile, phone 
        FROM customer 
        WHERE (mobile IS NULL OR mobile = '') 
        AND (phone IS NULL OR phone = '')
    """)
    customers_without_phone = cursor.fetchall()
    
    if customers_without_phone:
        print(f"WARNING: {len(customers_without_phone)} customers without phone found")
        # فقط تعداد را نمایش می‌دهیم، نه نام‌ها (به خاطر encoding)
        
        # حذف این مشتری‌ها
        cursor.execute("""
            DELETE FROM customer 
            WHERE (mobile IS NULL OR mobile = '') 
            AND (phone IS NULL OR phone = '')
        """)
        deleted_count = cursor.rowcount
        print(f"OK: {deleted_count} customers without phone deleted")
    else:
        print("OK: All customers have phone numbers")
    
    # 4. تنظیم پسورد برای بقیه مشتری‌ها
    print("Setting passwords for customers...")
    # Hash کردن پسورد با passlib (مثل security.get_password_hash)
    password = "123456789"
    hashed_password = pwd_context.hash(password)
    
    cursor.execute("""
        UPDATE customer 
        SET hashed_password = ? 
        WHERE hashed_password IS NULL 
        AND ((mobile IS NOT NULL AND mobile != '') OR (phone IS NOT NULL AND phone != ''))
    """, (hashed_password,))
    
    updated_count = cursor.rowcount
    print(f"OK: Password set for {updated_count} customers (password: 123456789)")
    
    # نمایش آمار
    cursor.execute("SELECT COUNT(*) FROM customer WHERE hashed_password IS NOT NULL")
    total_with_password = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM customer")
    total_customers = cursor.fetchone()[0]
    
    print(f"\nStatistics:")
    print(f"   - Total customers: {total_customers}")
    print(f"   - Customers with password: {total_with_password}")
    
    conn.commit()
    print("\nOK: Migration completed successfully!")
    
except Exception as e:
    conn.rollback()
    print(f"\nError in migration: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
finally:
    conn.close()

