import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

# Import all models
from app.db.base import Base
from app.core.config import settings


async def create_tables():
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Close engine connection
    await engine.dispose()
    
    print("All tables created successfully!")


if __name__ == "__main__":
    asyncio.run(create_tables())