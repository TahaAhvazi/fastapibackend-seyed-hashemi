# Import all the models, so that Base has them before being imported by Alembic
from app.db.base_class import Base  # noqa
from app.models.user import User  # noqa
from app.models.product import Product  # noqa
from app.models.customer import Customer, BankAccount  # noqa
from app.models.invoice import Invoice, InvoiceItem  # noqa
from app.models.inventory import InventoryTransaction  # noqa
from app.models.check import Check  # noqa