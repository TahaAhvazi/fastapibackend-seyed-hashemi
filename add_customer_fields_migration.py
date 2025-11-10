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
    print("Starting migration to add new customer fields...")
    
    # SQLite doesn't support ALTER COLUMN directly, so we need to recreate the table
    # Step 1: Create new table with new fields
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_new (
            id INTEGER NOT NULL PRIMARY KEY,
            person_code VARCHAR,
            person_type VARCHAR,
            first_name VARCHAR NOT NULL,
            last_name VARCHAR NOT NULL,
            company_name VARCHAR,
            address TEXT,
            phone VARCHAR,
            mobile VARCHAR,
            city VARCHAR,
            province VARCHAR,
            current_balance FLOAT NOT NULL DEFAULT 0.0,
            balance_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Step 2: Copy data from old table to new table
    cursor.execute("""
        INSERT INTO customer_new 
        (id, first_name, last_name, address, phone, city, province, 
         current_balance, balance_notes, created_at, updated_at)
        SELECT 
            id, first_name, last_name, address, phone, city, province,
            current_balance, balance_notes, created_at, updated_at
        FROM customer
    """)
    
    # Step 3: Drop old table
    cursor.execute("DROP TABLE customer")
    
    # Step 4: Rename new table to customer
    cursor.execute("ALTER TABLE customer_new RENAME TO customer")
    
    # Step 5: Recreate indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_customer_id ON customer (id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_customer_person_code ON customer (person_code)")
    
    conn.commit()
    print("Migration applied successfully!")
    print("Added fields: person_code, person_type, company_name, mobile")
    print("Changed phone field to nullable")
    
except Exception as e:
    conn.rollback()
    print(f"Error applying migration: {e}")
    raise
finally:
    conn.close()

