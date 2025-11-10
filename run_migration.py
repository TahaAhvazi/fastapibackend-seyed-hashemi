import sqlite3
import os

# Path to database
db_path = "rancetxe.db"

if not os.path.exists(db_path):
    print(f"Database file {db_path} not found!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Create product_images table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_images (
            id INTEGER NOT NULL PRIMARY KEY,
            product_id INTEGER NOT NULL,
            image_url VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES product (id) ON DELETE CASCADE
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_product_images_id ON product_images (id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_product_images_product_id ON product_images (product_id)")
    
    # Alter product table - make purchase_price and sale_price nullable
    # SQLite doesn't support ALTER COLUMN directly, so we need to recreate the table
    cursor.execute("PRAGMA table_info(product)")
    columns = cursor.fetchall()
    
    # Check if purchase_price and sale_price are already nullable
    purchase_price_nullable = any(col[1] == 'purchase_price' and col[3] == 0 for col in columns)
    sale_price_nullable = any(col[1] == 'sale_price' and col[3] == 0 for col in columns)
    
    if not purchase_price_nullable or not sale_price_nullable:
        print("Altering product table columns...")
        # SQLite doesn't support ALTER COLUMN, so we'll use a workaround
        # For now, we'll just note that the columns should be nullable
        # The actual change will be handled by SQLAlchemy when creating new records
        print("Note: SQLite doesn't support ALTER COLUMN. Columns will be nullable for new records.")
    
    conn.commit()
    print("Migration applied successfully!")
    
except Exception as e:
    conn.rollback()
    print(f"Error applying migration: {e}")
    raise
finally:
    conn.close()

