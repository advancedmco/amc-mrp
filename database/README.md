# Database Initialization

This directory contains the database initialization scripts for the AMC MRP system.

## Overview

The database uses MariaDB 11 and initializes automatically when the Docker container starts. The initialization process is designed with best practices:

- **Separation of Concerns**: Schema (DDL) is separate from data initialization
- **Environment-Driven**: All credentials come from environment variables
- **Flexible Data Loading**: Choose between comprehensive test data or minimal production data
- **Simple and Adjustable**: Easy to modify and maintain

## Initialization Process

When the database container starts, scripts in `/docker-entrypoint-initdb.d/` execute in alphabetical order:

1. **00-init-db-user.sh** - Creates database and user from environment variables
2. **01-schema.sql** (DDL.sql) - Creates all tables, views, triggers, and indexes
3. **02-data.sql** - Loads initial data (test or minimal, based on build argument)

## File Structure

```
database/
├── 00-init-db-user.sh        # Creates DB and user with env vars
├── DDL.sql                    # Schema definition (tables, views, triggers)
├── mariadb.cnf               # MariaDB optimization settings
├── Dockerfile                # Database container build
├── test_data/
│   ├── testdata.sql         # Comprehensive test data for development
│   └── minimaldata.sql      # Minimal data for production
└── README.md                 # This file
```

## Environment Variables

Configure these in your `.env` file:

### Required Variables

```env
# Database root password (used for initial setup)
MYSQL_ROOT_PASSWORD=toor

# Application database credentials
DB_NAME=amcmrp
DB_USER=amc
DB_PASSWORD=your_secure_password
DB_HOST=mysql
```

### Optional Variables

```env
# Data initialization mode: 'test' or 'minimal'
DATA_MODE=test
```

## Data Initialization Modes

### Test Mode (Default)

Use for **development and testing**:

```env
DATA_MODE=test
```

Loads `testdata.sql` with comprehensive sample data:
- 14 aerospace/defense customers (Boeing, Lockheed Martin, etc.)
- 10 manufacturing service vendors
- 25+ military/aerospace parts with FSN numbers
- 30+ work orders in various production stages
- Realistic data for dashboard testing

### Minimal Mode

Use for **production environments**:

```env
DATA_MODE=minimal
```

Loads `minimaldata.sql` with basic starter data:
- 4 sample customers
- 4 sample vendors
- 3 sample parts
- Clean slate for real production data

## Quick Start

### 1. Set Up Environment

Copy the example environment file and configure your credentials:

```bash
cp example.env .env
# Edit .env with your credentials
```

### 2. Start the Database

For development (with test data):

```bash
docker compose up mysql
```

For production (with minimal data):

```bash
DATA_MODE=minimal docker compose up mysql
```

### 3. Verify Initialization

Check that the database is healthy:

```bash
docker compose ps
```

The `mrp-db` container should show as "healthy".

### 4. Connect to Database

From your host machine:

```bash
mysql -h 127.0.0.1 -P 3307 -u amc -p
# Enter your DB_PASSWORD when prompted
```

From within Docker network:

```bash
docker compose exec mysql mariadb -u amc -p amcmrp
```

## Schema Overview

### Core Tables

- **Customers** - Customer information with QuickBooks integration
- **Vendors** - Vendor details for outsourcing and purchasing
- **Parts** - Part master data with FSN numbers and specifications
- **WorkOrders** - Active work orders with status tracking
- **BOM** - Bill of Materials for each work order
- **BOMProcesses** - Individual manufacturing processes

### Logging Tables

- **WorkOrderStatusHistory** - Audit trail of work order status changes
- **PurchaseOrdersLog** - Record of generated purchase orders
- **CertificatesLog** - Record of generated certificates of conformance

### Operational Tables

- **ProductionStages** - Track work order progress through production

### Views

- **vw_WorkOrderSummary** - Consolidated work order information
- **vw_BOMDetails** - Detailed BOM with process and vendor information

### Triggers

- **trg_workorder_status_history** - Automatically logs status changes

## Customizing Data

### Modifying Test Data

Edit `test_data/testdata.sql` to add or modify sample data for development:

```sql
-- Add your custom test data
INSERT INTO Customers (CustomerName, QuickBooksID) VALUES
('Your Test Customer', 999);
```

### Modifying Minimal Data

Edit `test_data/minimaldata.sql` for production starter data:

```sql
-- Add your production initial data
INSERT INTO Customers (CustomerName, QuickBooksID) VALUES
('Your Real Customer', 100);
```

### Modifying Schema

Edit `DDL.sql` to change table structures:

```sql
-- Add a new column
ALTER TABLE Parts ADD COLUMN NewField VARCHAR(50);
```

**Note**: Schema changes require rebuilding the container:

```bash
docker compose down
docker compose up --build
```

## Rebuilding the Database

To completely rebuild with new data or schema:

```bash
# Stop and remove the container
docker compose down

# Rebuild with new configuration
docker compose up --build mysql
```

Since the database uses tmpfs (in-memory storage), all data resets on container restart.

## Database Configuration

The `mariadb.cnf` file contains optimizations for:

- **tmpfs storage** - Fast in-memory database
- **Development use** - Reduced fsync for speed
- **Small memory footprint** - 128MB buffer pool
- **UTF-8 support** - utf8mb4 character set

## Troubleshooting

### Container Won't Start

Check environment variables:

```bash
docker compose config
```

Verify all required variables are set in `.env`.

### Health Check Failing

Check the logs:

```bash
docker compose logs mysql
```

Ensure `MYSQL_ROOT_PASSWORD` matches in both the environment and health check.

### Permission Denied on Init Script

Ensure the script is executable:

```bash
chmod +x database/00-init-db-user.sh
```

The Dockerfile automatically sets this, but manual builds may need it.

### Wrong Data Loaded

Check your `DATA_MODE` setting:

```bash
docker compose config | grep DATA_MODE
```

Rebuild if you changed the mode:

```bash
docker compose down
docker compose up --build
```

## Security Best Practices

1. **Never commit `.env`** - Contains sensitive credentials
2. **Use strong passwords** - Change default passwords in production
3. **Restrict network access** - Use firewalls to limit database port access
4. **Use secrets management** - Consider Docker secrets or vault systems for production
5. **Regular backups** - Although tmpfs is ephemeral, production systems need backups

## Advanced Usage

### Using Persistent Storage

To persist data between restarts, add a volume to `docker-compose.yml`:

```yaml
services:
  mysql:
    volumes:
      - mysql-data:/var/lib/mysql

volumes:
  mysql-data:
    driver: local
```

**Note**: This conflicts with tmpfs. Remove tmpfs section if using persistent volumes.

### Running Migrations

For schema updates on existing databases:

1. Create a migration script in `database/migrations/`
2. Run it manually or integrate with a migration tool:

```bash
docker compose exec mysql mariadb -u amc -p amcmrp < migrations/001_add_column.sql
```

### Exporting Data

Export current data for backup or migration:

```bash
docker compose exec mysql mariadb-dump -u amc -p amcmrp > backup.sql
```

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review logs: `docker compose logs mysql`
3. Verify environment variables: `docker compose config`
4. Consult the main project README.md
