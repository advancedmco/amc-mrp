# AMC MRP System

## Overview

The Advanced Machine Co. Manufacturing Resource Planning (MRP) system is a comprehensive solution for managing manufacturing operations, integrating with QuickBooks Online, and generating essential business documents. The system handles the complete workflow from customer purchase orders through work order completion and invoicing.

## System Architecture

### Core Components

#### 1. **Document Generation Services** (`gen-app` container)
- **Purpose:** Backend document generation engines
- **Components:**
  - `cocGenerate.py` - Certificate of Completion Generator
  - `poGenerate.py` - Purchase Order Generator
  - `test_coc.py`, `test_po.py` - Test scripts
- **Dependencies:** MySQL connector, python-docx, pypandoc

#### 2. **Web Dashboard** (`web-app` container)
- **Purpose:** User interface for managing work orders and generating documents
- **Components:**
  - `app.py` - Main Flask application with dashboard logic
  - `run.py` - Application launcher
  - `file_templates/` - HTML templates (base.html, dashboard.html)
- **Access:** http://localhost:5000
- **Dependencies:** Flask, MySQL connector, document generators

#### 3. **Database Layer** (`mysql` container)
- **Purpose:** Data storage for work orders, BOMs, certificates, vendor info
- **Components:**
  - `DDL.sql` - Database schema definition
  - `testdata.sql` - Sample data for development
- **Access:** localhost:3307 (external), mysql:3306 (internal)
- **Credentials:** amc/Workbench.lavender.chrome

## Business Workflow

### Customer Order Processing
1. **Customer PO Received** → Creates Work Order with unique sequential number
2. **BOM Creation** → Defines processes: raw material, plating, heat treatment, grinding
3. **Vendor Assignment** → Each process linked to vendors from QuickBooks
4. **Internal PO Generation** → Created for vendor operations as needed
5. **Work Order Tracking** → Status tracking through manufacturing phases
6. **COC Generation** → Certificate of Completion for military clients after job completion
7. **QuickBooks Integration** → Invoice creation and payment tracking

## Development Environment

### Quick Start
```bash
# Start the complete environment
docker compose up -d

# Access web dashboard
open http://localhost:5000

# Access Python container for testing
docker compose exec python-app bash

# Run COC generation test
docker compose exec gen-app python test_coc.py

# View logs
docker compose logs -f web-app
docker compose logs -f gen-app
```

### Database Access
```bash
# Connect from host
mysql -h localhost -P 3307 -u amc -p amcmrp
# Password: Workbench.lavender.chrome

# Connect from Python container
docker compose exec gen-app mysql -h mysql -u amc -p amcmrp
```

## Development Guidelines

### Code Standards
- Always check `DevAssets/ai dev instructions.txt` for current rules
- Ensure Docker Compose is running for all development
- Use existing Docker environments for testing
- Clean up temporary artifacts and scripts
- Update requirements.txt files when adding dependencies
- Avoid rebuilding containers when possible - use runtime package installation

### Testing Strategy
- Fresh database on each startup (no persistent volumes in development)
- Test data automatically loaded from `testdata.sql`
- Integration tests through web interface
- Unit tests for individual generators

### Document Generation Requirements
- COCs required for military clients only
- Internal POs must link to work orders and BOMs
- All generated documents logged in database
- Templates must remain compatible with current generation logic
- PDF output required for all document types

## QuickBooks Integration (Future)

### Planned Features
- **Daemon Service:** Token management and refresh handling
- **Data Synchronization:** Hourly cache updates for vendors, customers, products
- **Search Indexing:** Fast fuzzy search for client names, vendor names, parts
- **Invoice Creation:** Automated invoice generation with work order data
- **Product Verification:** Check/create QuickBooks products before invoicing

### Integration Points
- Customer data pulled from QuickBooks for work orders
- Vendor information for BOM process assignments  
- Product/service codes for invoice line items
- Cost tracking through QuickBooks bill integration

## Security Considerations

### Development Environment
- Default passwords used (change for production)
- No persistent database volumes (fresh DB each startup)
- Local network access only
- File download security through path validation

### Production Recommendations
- Change all default passwords
- Use environment files (.env) for sensitive data
- Add persistent database volumes
- Configure proper networking and SSL
- Implement user authentication
- Add audit logging
- Regular database backups

## Support & Troubleshooting

### Common Issues
- **Database Connection:** Check MySQL health status with `docker compose ps`
- **PDF Generation:** Verify pandoc and LaTeX installation in containers
- **File Permissions:** Ensure output directory is writable
- **Port Conflicts:** Default ports 3307 (MySQL) and 5000 (Web)

### Getting Help
```bash
# Check service health
docker compose ps

# View detailed logs
docker compose logs [service-name]

# Restart specific service
docker compose restart [service-name]

# Reset environment
docker compose down && docker compose up -d
```

For detailed Docker environment information, see [README-Docker.md](README-Docker.md).
