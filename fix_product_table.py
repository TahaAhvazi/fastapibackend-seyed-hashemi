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
    # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
    print("Starting migration...")
    
    # Step 1: Create new table with nullable purchase_price and sale_price
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_new (
            id INTEGER NOT NULL PRIMARY KEY,
            code VARCHAR NOT NULL UNIQUE,
            name VARCHAR NOT NULL,
            description TEXT,
            image_url VARCHAR,
            year_production INTEGER,
            category VARCHAR NOT NULL,
            unit VARCHAR NOT NULL,
            pieces_per_roll INTEGER,
            quantity_available FLOAT NOT NULL DEFAULT 0,
            colors VARCHAR,
            part_number VARCHAR,
            reorder_location VARCHAR,
            purchase_price FLOAT,
            sale_price FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Step 2: Copy data from old table to new table
    cursor.execute("""
        INSERT INTO product_new 
        (id, code, name, description, image_url, year_production, category, unit, 
         pieces_per_roll, quantity_available, colors, part_number, reorder_location, 
         purchase_price, sale_price, created_at, updated_at)
        SELECT 
            id, code, name, description, image_url, year_production, category, unit,
            pieces_per_roll, quantity_available, colors, part_number, reorder_location,
            purchase_price, sale_price, created_at, updated_at
        FROM product
    """)
    
    # Step 3: Drop old table
    cursor.execute("DROP TABLE product")
    
    # Step 4: Rename new table to product
    cursor.execute("ALTER TABLE product_new RENAME TO product")
    
    # Step 5: Recreate indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_product_code ON product (code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_product_id ON product (id)")
    
    # Step 6: Create product_images table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_images (
            id INTEGER NOT NULL PRIMARY KEY,
            product_id INTEGER NOT NULL,
            image_url VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES product (id) ON DELETE CASCADE
        )
    """)
    
    # Step 7: Create indexes for product_images
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_product_images_id ON product_images (id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_product_images_product_id ON product_images (product_id)")
    
    conn.commit()
    print("Migration applied successfully!")
    print("Product table recreated with nullable purchase_price and sale_price")
    
except Exception as e:
    conn.rollback()
    print(f"Error applying migration: {e}")
    raise
finally:
    conn.close()

