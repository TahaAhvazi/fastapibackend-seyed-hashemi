"""
اسکریپت برای تنظیم پسورد همه مشتری‌ها به 123456789
(فقط برای مشتری‌هایی که شماره دارند)
"""
import asyncio
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core import security
from app.db.session import AsyncSessionLocal
from app import models


async def set_customer_passwords():
    """تنظیم پسورد مشتری‌هایی که شماره دارند به 123456789"""
    async with AsyncSessionLocal() as db:
        try:
            # دریافت مشتری‌هایی که شماره دارند اما پسورد ندارند
            result = await db.execute(
                select(models.Customer).where(
                    models.Customer.hashed_password.is_(None),
                    or_(
                        models.Customer.mobile.isnot(None),
                        models.Customer.phone.isnot(None)
                    )
                )
            )
            customers = result.scalars().all()
            
            hashed_password = security.get_password_hash("123456789")
            updated_count = 0
            
            for customer in customers:
                # بررسی اینکه واقعاً شماره دارد
                if customer.mobile or customer.phone:
                    customer.hashed_password = hashed_password
                    updated_count += 1
            
            await db.commit()
            print(f"✅ پسورد {updated_count} مشتری تنظیم شد (پسورد: 123456789)")
            
        except Exception as e:
            await db.rollback()
            print(f"❌ خطا: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(set_customer_passwords())

