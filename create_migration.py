import asyncio
import os

async def create_migration():
    # Create initial migration
    os.system('alembic revision --autogenerate -m "initial"')
    print("Migration created successfully!")

if __name__ == "__main__":
    asyncio.run(create_migration())