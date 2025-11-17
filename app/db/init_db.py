import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.product import Product
from app.models.customer import Customer, BankAccount
from app.models.invoice import Invoice, InvoiceItem
from app.models.check import Check
from app.core.security import get_password_hash
from app.schemas.user import UserRole
from app.schemas.invoice import InvoiceStatus, PaymentType
from app.schemas.check import CheckStatus


async def init_db() -> None:
    """Create initial admin, accountant, and warehouse users if they don't exist"""
    async with AsyncSessionLocal() as db:
        # Check if admin exists
        result = await db.execute(select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL))
        user = result.scalars().first()
        
        if not user:
            await _create_initial_users(db)
            await _create_seed_data(db)
            await db.commit()


async def _create_initial_users(db: AsyncSession) -> None:
    """Create admin, accountant and warehouse users"""
    # Create admin user
    admin_user = User(
        email=settings.FIRST_SUPERUSER_EMAIL,
        hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
        first_name=settings.FIRST_SUPERUSER_FIRST_NAME,
        last_name=settings.FIRST_SUPERUSER_LAST_NAME,
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin_user)
    
    # Create accountant user
    accountant_user = User(
        email=settings.FIRST_ACCOUNTANT_EMAIL,
        hashed_password=get_password_hash(settings.FIRST_ACCOUNTANT_PASSWORD),
        first_name=settings.FIRST_ACCOUNTANT_FIRST_NAME,
        last_name=settings.FIRST_ACCOUNTANT_LAST_NAME,
        role=UserRole.ACCOUNTANT,
        is_active=True,
    )
    db.add(accountant_user)
    
    # Create warehouse user
    warehouse_user = User(
        email=settings.FIRST_WAREHOUSE_EMAIL,
        hashed_password=get_password_hash(settings.FIRST_WAREHOUSE_PASSWORD),
        first_name=settings.FIRST_WAREHOUSE_FIRST_NAME,
        last_name=settings.FIRST_WAREHOUSE_LAST_NAME,
        role=UserRole.WAREHOUSE,
        is_active=True,
    )
    db.add(warehouse_user)
    
    await db.flush()
    return admin_user, accountant_user, warehouse_user


async def _create_seed_data(db: AsyncSession) -> None:
    """Create seed data for demo purposes"""
    # Get users for reference
    result = await db.execute(select(User))
    users = result.scalars().all()
    admin_user = next((u for u in users if u.role == UserRole.ADMIN), None)
    
    # Create products
    products = [
        Product(
            code="P001",
            name="پارچه مخمل سلطنتی",  # Royal Velvet Fabric
            description="پارچه مخمل با کیفیت عالی، مناسب برای مبلمان و پرده",  # High quality velvet fabric for furniture and curtains
            image_url="/uploads/velvet.jpg",
            year_production=1401,
            category="مخمل",  # Velvet
            unit="متر",  # Meter
            pieces_per_roll=50,
            is_available=True,
            colors="قرمز، آبی، سبز",  # Red, Blue, Green
            part_number="VLV-001",
            reorder_location="تهران، بازار",  # Tehran, Bazaar
            purchase_price=250000,
            sale_price=350000,
        ),
        Product(
            code="P002",
            name="پارچه کتان طبیعی",  # Natural Linen Fabric
            description="پارچه کتان ۱۰۰٪ طبیعی با بافت زیبا",  # 100% natural linen fabric with beautiful texture
            image_url="/uploads/linen.jpg",
            year_production=1401,
            category="کتان",  # Linen
            unit="متر",  # Meter
            pieces_per_roll=100,
            is_available=True,
            colors="کرم، قهوه‌ای، طبیعی",  # Cream, Brown, Natural
            part_number="LNN-002",
            reorder_location="اصفهان، چهارباغ",  # Isfahan, Chahar Bagh
            purchase_price=180000,
            sale_price=280000,
        ),
        Product(
            code="P003",
            name="پارچه ابریشم خالص",  # Pure Silk Fabric
            description="ابریشم خالص با کیفیت عالی، مناسب برای لباس مجلسی",  # High quality pure silk for formal dresses
            image_url="/uploads/silk.jpg",
            year_production=1400,
            category="ابریشم",  # Silk
            unit="متر",  # Meter
            pieces_per_roll=30,
            is_available=True,
            colors="طلایی، نقره‌ای، صورتی",  # Gold, Silver, Pink
            part_number="SLK-003",
            reorder_location="یزد، بازار سنتی",  # Yazd, Traditional Bazaar
            purchase_price=500000,
            sale_price=750000,
        ),
        Product(
            code="P004",
            name="پارچه نخی گلدار",  # Floral Cotton Fabric
            description="پارچه نخی با طرح گل‌های زیبا، مناسب برای پیراهن و لباس تابستانی",  # Cotton fabric with beautiful floral patterns for summer dresses
            image_url="/uploads/cotton.jpg",
            year_production=1401,
            category="نخی",  # Cotton
            unit="متر",  # Meter
            pieces_per_roll=80,
            is_available=True,
            colors="سفید با گل‌های رنگی",  # White with colorful flowers
            part_number="CTN-004",
            reorder_location="مشهد، خیابان خسروی",  # Mashhad, Khosravi Street
            purchase_price=120000,
            sale_price=180000,
        ),
        Product(
            code="P005",
            name="پارچه ترمه یزد",  # Yazd Termeh Fabric
            description="پارچه ترمه اصیل یزد با طرح‌های سنتی",  # Authentic Yazd Termeh fabric with traditional patterns
            image_url="/uploads/termeh.jpg",
            year_production=1399,
            category="ترمه",  # Termeh
            unit="متر",  # Meter
            pieces_per_roll=20,
            is_available=True,
            colors="قرمز، سبز، آبی با نقوش سنتی",  # Red, Green, Blue with traditional patterns
            part_number="TRM-005",
            reorder_location="یزد، میدان امیرچخماق",  # Yazd, Amir Chakhmaq Square
            purchase_price=800000,
            sale_price=1200000,
        ),
    ]
    
    for product in products:
        db.add(product)
    
    await db.flush()
    
    # Create customers
    customers = [
        Customer(
            first_name="علی",  # Ali
            last_name="محمدی",  # Mohammadi
            address="تهران، خیابان ولیعصر، کوچه بهار، پلاک ۱۲",  # Tehran, Valiasr St, Bahar Alley, No. 12
            phone="09121234567",
            city="تهران",  # Tehran
            province="تهران",  # Tehran
        ),
        Customer(
            first_name="فاطمه",  # Fatemeh
            last_name="حسینی",  # Hosseini
            address="اصفهان، خیابان چهارباغ، کوچه گلستان، پلاک ۵",  # Isfahan, Chahar Bagh St, Golestan Alley, No. 5
            phone="09132345678",
            city="اصفهان",  # Isfahan
            province="اصفهان",  # Isfahan
        ),
        Customer(
            first_name="محمد",  # Mohammad
            last_name="رضایی",  # Rezaei
            address="مشهد، بلوار وکیل آباد، خیابان هفتم، پلاک ۲۳",  # Mashhad, Vakil Abad Blvd, 7th St, No. 23
            phone="09153456789",
            city="مشهد",  # Mashhad
            province="خراسان رضوی",  # Khorasan Razavi
        ),
    ]
    
    for customer in customers:
        db.add(customer)
    
    await db.flush()
    
    # Add bank accounts for customers
    bank_accounts = [
        BankAccount(
            customer_id=customers[0].id,
            bank_name="بانک ملی",  # Bank Melli
            account_number="0123456789",
            iban="IR123456789012345678901234",
        ),
        BankAccount(
            customer_id=customers[1].id,
            bank_name="بانک ملت",  # Bank Mellat
            account_number="9876543210",
            iban="IR987654321098765432109876",
        ),
        BankAccount(
            customer_id=customers[2].id,
            bank_name="بانک پارسیان",  # Bank Parsian
            account_number="5432109876",
            iban="IR543210987654321098765432",
        ),
    ]
    
    for bank_account in bank_accounts:
        db.add(bank_account)
    
    await db.flush()
    
    # Create invoices
    invoices = [
        Invoice(
            invoice_number="INV-1401-001",
            customer_id=customers[0].id,
            created_by=admin_user.id,
            subtotal=1750000,
            total=1750000,
            payment_type=PaymentType.CASH,
            status=InvoiceStatus.DELIVERED,
            tracking_info={
                "carrier_name": "پست پیشتاز",  # Express Post
                "tracking_code": "EXP12345678",
                "shipping_date": "1401-06-15",
                "number_of_packages": 2
            },
        ),
        Invoice(
            invoice_number="INV-1401-002",
            customer_id=customers[1].id,
            created_by=admin_user.id,
            subtotal=2800000,
            total=2800000,
            payment_type=PaymentType.CHECK,
            status=InvoiceStatus.APPROVED,
        ),
        Invoice(
            invoice_number="INV-1401-003",
            customer_id=customers[2].id,
            created_by=admin_user.id,
            subtotal=1200000,
            total=1200000,
            payment_type=PaymentType.MIXED,
            payment_breakdown={
                "cash": 500000,
                "check": 700000
            },
            status=InvoiceStatus.WAREHOUSE_PENDING,
        ),
    ]
    
    for invoice in invoices:
        db.add(invoice)
    
    await db.flush()
    
    # Create invoice items
    invoice_items = [
        InvoiceItem(
            invoice_id=invoices[0].id,
            product_id=products[0].id,
            quantity=5,
            unit="متر",  # Meter
            price=350000,
        ),
        InvoiceItem(
            invoice_id=invoices[1].id,
            product_id=products[1].id,
            quantity=10,
            unit="متر",  # Meter
            price=280000,
        ),
        InvoiceItem(
            invoice_id=invoices[2].id,
            product_id=products[2].id,
            quantity=1,
            unit="متر",  # Meter
            price=750000,
        ),
        InvoiceItem(
            invoice_id=invoices[2].id,
            product_id=products[3].id,
            quantity=2.5,
            unit="متر",  # Meter
            price=180000,
        ),
    ]
    
    for item in invoice_items:
        db.add(item)
    
    await db.flush()
    
    # Create checks
    checks = [
        Check(
            check_number="12345678",
            customer_id=customers[1].id,
            amount=2800000,
            issue_date="1401-06-10",
            due_date="1401-09-10",
            status=CheckStatus.IN_PROGRESS,
            related_invoice_id=invoices[1].id,
            created_by=admin_user.id,
        ),
        Check(
            check_number="87654321",
            customer_id=customers[2].id,
            amount=700000,
            issue_date="1401-06-12",
            due_date="1401-08-12",
            status=CheckStatus.IN_PROGRESS,
            related_invoice_id=invoices[2].id,
            created_by=admin_user.id,
        ),
    ]
    
    for check in checks:
        db.add(check)