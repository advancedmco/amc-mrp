# AMC MRP System

Manufacturing Resource Planning system for Advanced Machine Co. with QuickBooks Online integration, document generation, and web dashboard for managing work orders and manufacturing operations.

## Quick Start

```bash
# Start all services
docker compose up -d

# Access web dashboard
open http://localhost:5001

# View logs
docker compose logs -f web-app
docker compose logs -f gen-app

# Stop services
docker compose down
```

## System Architecture

### Services

**MySQL Database (`mysql`)**
- Port: 3307 (host) → 3306 (container)
- Database: amcmrp
- Credentials: amc / Workbench.lavender.chrome
- Features: Fresh database on each startup, auto-loads DDL.sql and testdata.sql

**Document Generator (`generator`)**
- Container: mrp-generator
- Purpose: Backend document generation (COCs and POs)
- Components: cocGenerate.py, poGenerate.py
- Dependencies: pandoc, LaTeX, LibreOffice, python-docx

**Web Dashboard (`frontend`)**
- Container: mrp-frontend
- Port: 5001
- URL: http://localhost:5001
- Purpose: User interface for work orders and document generation
- Components: Flask application with dashboard and templates

**MRP Backend (`mrp-backend`)**
- Container: mrp-backend
- Port: 5002
- Purpose: QuickBooks integration daemon (token management, data sync)
- Features: Hourly cache updates, fuzzy search indexing

## Project Structure

```
amc-mrp/
├── backend/          # QuickBooks integration daemon
├── frontend/         # Web dashboard (Flask)
├── filegen/          # Document generators (COC, PO)
├── database/         # SQL schema and test data
├── DevAssets/        # Examples and development docs
└── docker-compose.yml
```

## Business Workflow

1. **Customer PO Received** → Create Work Order with unique sequential number
2. **BOM Creation** → Define processes (raw material, plating, heat treatment, grinding)
3. **Vendor Assignment** → Link processes to QuickBooks vendors
4. **Internal PO Generation** → Create vendor POs for operations
5. **Work Order Tracking** → Monitor through manufacturing phases
6. **COC Generation** → Certificate of Completion for military clients
7. **QuickBooks Integration** → Invoice creation and payment tracking

## Environment Configuration

Required variables in `.env`:

```bash
# Database
DB_HOST=mysql
DB_NAME=amcmrp
DB_USER=amc
DB_PASSWORD=Workbench.lavender.chrome

# QuickBooks
QUICKBOOKS_CLIENT_ID=your_client_id
QUICKBOOKS_CLIENT_SECRET=your_client_secret
QUICKBOOKS_SANDBOX_BASE_URL=https://sandbox-quickbooks.api.intuit.com
QUICKBOOKS_COMPANY_ID=your_company_id

# Flask
FLASK_SECRET_KEY=your_secret_key
PRODUCTION_URI=https://mrp.inge.st
```

## Common Commands

### Database Access
```bash
# From host
mysql -h localhost -P 3307 -u amc -p amcmrp
# Password: Workbench.lavender.chrome

# From gen-app container
docker compose exec gen-app mysql -h mysql -u amc -p amcmrp

# From MySQL container
docker compose exec mysql mysql -u amc -p amcmrp
```

### Document Generation
```bash
# Access generator container
docker compose exec gen-app bash

# Run COC test
docker compose exec gen-app python src/test_coc.py

# Run PO test
docker compose exec gen-app python src/test_po.py
```

### Development Workflow
```bash
# Restart specific service
docker compose restart web-app

# View service status
docker compose ps

# Reset environment (fresh database)
docker compose down && docker compose up -d

# Check dependency installation
docker compose exec gen-app pip list
```

## Development Features

**Live Code Reloading**
- Changes to files are immediately available in containers
- No rebuild needed for code changes
- Mounted volumes: backend/, frontend/, filegen/

**Fresh Database**
- Database recreated on each startup (tmpfs storage)
- Always starts with clean schema from DDL.sql
- Test data loaded from testdata.sql
- Perfect for development and testing

**PDF Generation**
- Full pandoc and LaTeX support
- LibreOffice for DOCX to PDF conversion
- Generated files saved to respective CACHE directories
- Accessible from both container and host

## QuickBooks Integration

### Current Status
Backend daemon service with OAuth token management and data synchronization.

### Features
- Token refresh automation to prevent expiration
- Hourly cache updates for vendors, customers, products
- Fuzzy search indexing for quick lookups
- REST API for web dashboard integration

### Integration Points
- Customer data for work order creation
- Vendor information for BOM assignments
- Product/service codes for invoice line items
- Cost tracking through QuickBooks bill integration

## Troubleshooting

### Database Connection Issues
```bash
# Check MySQL health
docker compose ps

# View MySQL logs
docker compose logs mysql

# Test connection from gen-app
docker compose exec gen-app python -c "import mysql.connector; print('OK')"
```

### PDF Generation Issues
```bash
# Test pandoc
docker compose exec gen-app pandoc --version

# Test LaTeX
docker compose exec gen-app xelatex --version

# Test LibreOffice
docker compose exec gen-app libreoffice --version
```

### Service Not Starting
```bash
# Check all service logs
docker compose logs

# Rebuild specific service
docker compose build --no-cache web-app

# Check Docker resources
docker system df
```

### Port Conflicts
Default ports: 3307 (MySQL), 5001 (Web), 5002 (Backend)
Modify in docker-compose.yml if conflicts occur.

## Security Notes

### Development Environment
- Default credentials are used (DO NOT use in production)
- No persistent database volumes (fresh DB each startup)
- Local network access only
- File paths validated before downloads

### Production Recommendations
- Change all default passwords
- Use .env files (never commit to git)
- Add persistent database volumes
- Configure SSL/TLS
- Implement user authentication and authorization
- Enable audit logging
- Set up regular database backups
- Use secrets management (e.g., Docker secrets, Vault)

## Document Generation Requirements

- **COCs:** Required for military clients only
- **Internal POs:** Must link to work orders and BOMs
- All documents logged in database for retrieval
- Templates stored in filegen/file_templates/
- PDF output required for all document types
- Generated files cached in service-specific CACHE directories

## Support

### Getting Help
```bash
# Check service health
docker compose ps

# View detailed logs
docker compose logs [service-name]

# Follow live logs
docker compose logs -f [service-name]

# Complete restart
docker compose down && docker compose up -d
```

### Common Issues
- **Database connection errors:** Verify MySQL is healthy, check credentials
- **Missing dependencies:** Rebuild container or check requirements.txt
- **PDF generation fails:** Verify pandoc/LaTeX installation
- **File permission errors:** Check volume mount permissions
- **Service crash loops:** Check logs for specific error messages
