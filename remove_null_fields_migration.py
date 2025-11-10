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
    print("Starting migration to remove null fields...")
    
    # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
    # Step 1: Create new table without the null fields
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_new (
            id INTEGER NOT NULL PRIMARY KEY,
            code VARCHAR NOT NULL UNIQUE,
            name VARCHAR NOT NULL,
            description TEXT,
            category VARCHAR NOT NULL,
            unit VARCHAR NOT NULL,
            quantity_available FLOAT NOT NULL DEFAULT 0,
            colors VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Step 2: Copy data from old table to new table (only existing fields)
    cursor.execute("""
        INSERT INTO product_new 
        (id, code, name, description, category, unit, 
         quantity_available, colors, created_at, updated_at)
        SELECT 
            id, code, name, description, category, unit,
            quantity_available, colors, created_at, updated_at
        FROM product
    """)
    
    # Step 3: Drop old table
    cursor.execute("DROP TABLE product")
    
    # Step 4: Rename new table to product
    cursor.execute("ALTER TABLE product_new RENAME TO product")
    
    # Step 5: Recreate indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_product_code ON product (code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_product_id ON product (id)")
    
    conn.commit()
    print("Migration applied successfully!")
    print("Removed fields: image_url, year_production, pieces_per_roll, part_number, reorder_location, purchase_price, sale_price")
    
except Exception as e:
    conn.rollback()
    print(f"Error applying migration: {e}")
    raise
finally:
    conn.close()

