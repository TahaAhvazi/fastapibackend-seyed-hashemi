# Rancetxe Fabric Store Management System

A comprehensive backend system for managing a Persian fabric store, built with FastAPI and PostgreSQL.

## Features

- User authentication and role-based access control (Admin, Accountant, Warehouse)
- Product management with inventory tracking
- Customer management with bank account information
- Invoice creation and processing workflow
- Check management for payment tracking
- Comprehensive reporting system
- File upload and management

## Technology Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **PostgreSQL**: Robust relational database
- **SQLAlchemy**: SQL toolkit and ORM
- **Alembic**: Database migration tool
- **Pydantic**: Data validation and settings management
- **JWT**: Token-based authentication

## Setup Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL

### Installation

1. Clone the repository

```bash
git clone https://github.com/yourusername/rancetxe-backend.git
cd rancetxe-backend
```

2. Create and activate a virtual environment

```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Configure environment variables

Create a `.env` file in the root directory with the following variables:

```
# Database settings
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost/rancetxe

# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=60

# API settings
API_V1_STR=/api/v1
CORS_ORIGINS=["http://localhost:3000"]

# Project settings
PROJECT_NAME=Rancetxe Fabric Store Management System

# Upload settings
UPLOADS_DIR=./uploads
MAX_UPLOAD_SIZE=5242880  # 5MB
ALLOWED_EXTENSIONS=["jpg", "jpeg", "png", "pdf"]

# Initial users
FIRST_SUPERUSER_EMAIL=admin@example.com
FIRST_SUPERUSER_PASSWORD=admin
FIRST_SUPERUSER_FIRST_NAME=Admin
FIRST_SUPERUSER_LAST_NAME=User

FIRST_ACCOUNTANT_EMAIL=accountant@example.com
FIRST_ACCOUNTANT_PASSWORD=accountant
FIRST_ACCOUNTANT_FIRST_NAME=Accountant
FIRST_ACCOUNTANT_LAST_NAME=User

FIRST_WAREHOUSE_EMAIL=warehouse@example.com
FIRST_WAREHOUSE_PASSWORD=warehouse
FIRST_WAREHOUSE_FIRST_NAME=Warehouse
FIRST_WAREHOUSE_LAST_NAME=User
```

5. Create the database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create the database
CREATE DATABASE rancetxe;

# Exit PostgreSQL
\q
```

6. Run database migrations

```bash
# Generate initial migration
python create_migration.py

# Apply migrations
python apply_migration.py
```

7. Start the application

```bash
python main.py
```

The API will be available at http://localhost:8000

## API Documentation

Once the application is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

This project is licensed under the MIT License.