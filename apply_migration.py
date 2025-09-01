import asyncio
import os

async def apply_migration():
    # Apply migrations
    os.system('alembic upgrade head')
    print("Migration applied successfully!")

if __name__ == "__main__":
    asyncio.run(apply_migration())