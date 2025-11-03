# AMC MRP System

Manufacturing Resource Planning system for Advanced Machine Co. with QuickBooks Online integration, document generation, and web dashboard for managing work orders and manufacturing operations.

## Quick Start

```bash
# Build all services (first time or after Dockerfile changes)
docker compose build

# Start all services
docker compose up -d

# Access web dashboard
open http://localhost:5001

# View logs
docker compose logs -f frontend
docker compose logs -f backend

# Rebuild and restart (for testing changes)
docker compose down && docker compose build && docker compose up -d

# Stop services
docker compose down
```

## System Architecture

### Services

**MariaDB Database (`mysql`)**
- Port: 3307 (host) → 3306 (container)
- Database: amcmrp
- Credentials: amc / Workbench.lavender.chrome
- Features: Fresh database on each startup, auto-loads DDL.sql and testdata.sql
- Build: Custom Dockerfile in database/ (mariadb:11)

**Web Dashboard with Document Generator (`frontend`)**
- Container: mrp-frontend
- Port: 5001 (5000 internal)
- URL: http://localhost:5001
- Purpose: User interface for work orders and document generation
- Components: Flask application, COC/PO generators, templates
- Dependencies: pandoc, LaTeX, LibreOffice, python-docx
- Build: Custom Dockerfile in frontend/
- Hot-reloading: Source code mounted for development

**QuickBooks Integration Backend (`backend`)**
- Container: mrp-backend
- Port: 5002
- Purpose: QuickBooks OAuth and data synchronization daemon
- Features: Token management, hourly cache updates, fuzzy search API
- Build: Custom Dockerfile in backend/
- Hot-reloading: Source code mounted for development

## Project Structure

```
amc-mrp/
├── backend/                      # QuickBooks integration daemon
│   ├── Dockerfile                # Backend build configuration
│   ├── .dockerignore             # Build optimization
│   ├── requirements.txt          # Python dependencies
│   └── app.py                    # Backend service
├── frontend/                     # Web dashboard and document generator
│   ├── Dockerfile                # Frontend build configuration
│   ├── .dockerignore             # Build optimization
│   ├── requirements.txt          # Python dependencies
│   ├── generators/               # Document generation code
│   │   ├── cocGenerate.py        # Certificate of Completion
│   │   ├── poGenerate.py         # Purchase Order
│   │   ├── test_coc.py           # COC testing
│   │   └── test_po.py            # PO testing
│   ├── templates/
│   │   └── documents/            # DOCX templates
│   ├── app.py                    # Flask application
│   └── run.py                    # Application entry point
├── database/                     # Database configuration
│   ├── Dockerfile                # Database build configuration
│   ├── .dockerignore             # Build optimization
│   ├── DDL.sql                   # Database schema
│   └── test_data/
│       └── testdata.sql          # Sample data
├── DevAssets/                    # Examples and development docs
├── docker-compose.yml            # Service orchestration
├── .env                          # Environment variables (not in git)
├── example.env                   # Environment template
├── CLAUDE.md                     # Development instructions
└── README.md                     # This file
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

# From MySQL container
docker compose exec mysql mysql -u amc -p amcmrp
```

### Document Generation Testing
```bash
# Access frontend container
docker compose exec frontend bash

# Run COC test
docker compose exec frontend python generators/test_coc.py

# Run PO test
docker compose exec frontend python generators/test_po.py
```

### Development Workflow
```bash
# Restart specific service
docker compose restart frontend

# View service status
docker compose ps

# Reset environment (fresh database)
docker compose down && docker compose up -d

# Rebuild after dependency changes
docker compose build [service-name]

# Check installed packages
docker compose exec frontend pip list
docker compose exec backend pip list
```

## Development Features

**Custom Docker Builds**
- Each service has its own Dockerfile
- Optimized with .dockerignore files
- Easy to rebuild: `docker compose build`
- Dependencies baked into images for consistency

**Live Code Reloading**
- Source code mounted as volumes for hot-reloading
- No rebuild needed for code changes
- Only rebuild when dependencies or Dockerfiles change
- Mounted volumes: backend/, frontend/

**Fresh Database**
- Database recreated on each startup (tmpfs storage)
- Always starts with clean schema from DDL.sql
- Test data loaded from testdata.sql
- Perfect for development and testing

**Integrated Document Generation**
- Document generators now integrated into frontend service
- Full pandoc and LaTeX support
- LibreOffice for DOCX to PDF conversion
- Generated files saved to frontend/CACHE/
- Templates in frontend/templates/documents/

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
# Check MariaDB health
docker compose ps

# View MariaDB logs
docker compose logs mysql

# Test connection from frontend
docker compose exec frontend python -c "import mysql.connector; print('OK')"
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

# Rebuild specific service from scratch
docker compose build --no-cache [service-name]

# Rebuild all services from scratch
docker compose build --no-cache

# Check Docker resources
docker system df
```

### Port Conflicts
Default ports: 3307 (MariaDB), 5001 (Web), 5002 (Backend)
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
