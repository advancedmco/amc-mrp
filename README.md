# AMC MRP System

## Overview

The Advanced Machine Co. Manufacturing Resource Planning (MRP) system is a comprehensive solution for managing manufacturing operations, integrating with QuickBooks Online, and generating essential business documents. The system handles the complete workflow from customer purchase orders through work order completion and invoicing.

## System Architecture

### Core Components

#### 1. **Document Generation Services** (`python-app` container)
- **Location:** `WORKING/` directory
- **Purpose:** Backend document generation engines
- **Components:**
  - `cocGenerate.py` - Certificate of Completion Generator
  - `poGenerate.py` - Purchase Order Generator
  - `test_coc.py`, `test_po.py` - Test scripts
- **Docker Service:** `python-app`
- **Dependencies:** MySQL connector, python-docx, pypandoc

#### 2. **Web Dashboard** (`web-app` container)
- **Location:** `web/` directory  
- **Purpose:** User interface for managing work orders and generating documents
- **Components:**
  - `app.py` - Main Flask application with dashboard logic
  - `run.py` - Application launcher
  - `templates/` - HTML templates (base.html, dashboard.html)
- **Docker Service:** `web-app`
- **Access:** http://localhost:5000
- **Dependencies:** Flask, MySQL connector, document generators

#### 3. **Database Layer** (`mysql` container)
- **Location:** Database schemas in `WORKING/`
- **Purpose:** Data storage for work orders, BOMs, certificates, vendor info
- **Components:**
  - `DDL.sql` - Database schema definition
  - `testdata.sql` - Sample data for development
- **Docker Service:** `mysql`
- **Access:** localhost:3307 (external), mysql:3306 (internal)
- **Credentials:** amc/Workbench.lavender.chrome

#### 4. **Document Templates**
- **Location:** `DevAssets/`
- **Components:**
  - `COC Template.docx` - Certificate of Completion template
  - `PO Template.docx` - Purchase Order template
- **Purpose:** Base templates for automated document generation

## Business Workflow

### Customer Order Processing
1. **Customer PO Received** → Creates Work Order with unique sequential number
2. **BOM Creation** → Defines processes: raw material, plating, heat treatment, grinding
3. **Vendor Assignment** → Each process linked to vendors from QuickBooks
4. **Internal PO Generation** → Created for vendor operations as needed
5. **Work Order Tracking** → Status tracking through manufacturing phases
6. **COC Generation** → Certificate of Completion for military clients after job completion
7. **QuickBooks Integration** → Invoice creation and payment tracking

### Document Types

#### Certificates of Completion (COCs)
- **Required for:** Military clients
- **Generated:** After invoice creation in QuickBooks Online
- **Contains:** Part number, description, customer PO, final quantity, date
- **Storage:** Database logging for historical archival

#### Purchase Orders (Internal)
- **Purpose:** Secondary operations with external vendors
- **Generated from:** Work order pages in web dashboard
- **Contains:** Part details, material specs, vendor info, certification requirements
- **Process:** Multi-line text field for work requirements

#### Bill of Materials (BOMs)
- **Structure:** One part number/name per BOM
- **Processes:** Multiple vendor operations per BOM
- **Cost Tracking:** Links to QuickBooks bills for actual vs estimated costs
- **Future Use:** Historical cost data for better estimating

## File Structure

```
amc-mrp/
├── README.md                          # This file - project overview
├── README-Docker.md                   # Docker environment documentation
├── docker-compose.yml                 # Container orchestration
├── example.env                        # Environment variables template
│
├── DevAssets/                         # Templates and configuration
│   ├── COC Template.docx              # Certificate template
│   ├── PO Template.docx               # Purchase order template
│   ├── pythondocker/
│   │   ├── Dockerfile                 # Python app container config
│   │   └── requirements.txt           # Python dependencies
│   ├── webappdocker/
│   │   └── requirements.txt           # Web app dependencies
│   ├── Database/
│   │   └── dockerfile                 # Database container config
│   ├── WebApp/
│   │   ├── requirements.txt           # Web app requirements
│   │   └── Brand Logo Light@0.75x.png # Branding assets
│   ├── ERdiagrams/                    # Database design diagrams
│   │   ├── ER.8.12.pdf
│   │   ├── ERdiagram.mwb
│   │   └── ERdiagram.mwb.bak
│   └── Example Docs/                  # Business requirements & examples
│       ├── ai dev instructions.txt    # Development guidelines
│       ├── master explanation.txt     # System overview
│       ├── example certificates of completion/
│       ├── example customer POs/
│       ├── example internal POs/
│       └── example invoices and packing slips/
│
├── WORKING/                           # Python application source
│   ├── cocGenerate.py                 # COC generation engine
│   ├── poGenerate.py                  # PO generation engine
│   ├── test_coc.py                    # COC testing script
│   ├── test_po.py                     # PO testing script
│   ├── DDL.sql                        # Database schema
│   ├── data.sql                       # Historical sample data
│   └── testdata.sql                   # Current test data
│
└── web/                               # Web application
    ├── app.py                         # Flask application
    ├── run.py                         # Web server launcher
    ├── README.md                      # Web app specific docs
    └── templates/
        ├── base.html                  # Base template
        └── dashboard.html             # Main dashboard
```

## Output File Management

### Current Output Strategy
- **Generated Documents:** Saved to `/app/WORKING/CACHE` inside containers
- **Host Mapping:** `./output` directory (created automatically)
- **Web Downloads:** Accessible through Flask download routes
- **File Types:** PDF documents for COCs and POs

### Download Workflow
1. User generates document through web dashboard
2. Document service creates file in output directory
3. Database logs document metadata for historical tracking
4. Web app provides secure download link
5. Files remain available for future access

## Development Environment

### Prerequisites
- Docker Desktop installed and running
- Docker Compose v3.8 or higher

### Quick Start
```bash
# Start the complete environment
docker-compose up -d

# Access web dashboard
open http://localhost:5000

# Access Python container for testing
docker-compose exec python-app bash

# Run COC generation test
docker-compose exec python-app python test_coc.py

# View logs
docker-compose logs -f web-app
docker-compose logs -f python-app
```

### Database Access
```bash
# Connect from host
mysql -h localhost -P 3307 -u amc -p amcmrp
# Password: Workbench.lavender.chrome

# Connect from Python container
docker-compose exec python-app mysql -h mysql -u amc -p amcmrp
```

## Development Guidelines

### Code Standards
- Always check `DevAssets/Example Docs/ai dev instructions.txt` for current rules
- Ensure Docker Compose is running for all development
- Use existing Docker environments for testing
- Clean up temporary artifacts and scripts
- Update requirements.txt files when adding dependencies
- Avoid rebuilding containers when possible - use runtime package installation

### Testing Strategy
- Fresh database on each startup (no persistent volumes in development)
- Test data automatically loaded from `WORKING/testdata.sql`
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
- **Database Connection:** Check MySQL health status with `docker-compose ps`
- **PDF Generation:** Verify pandoc and LaTeX installation in containers
- **File Permissions:** Ensure output directory is writable
- **Port Conflicts:** Default ports 3307 (MySQL) and 5000 (Web)

### Getting Help
```bash
# Check service health
docker-compose ps

# View detailed logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]

# Reset environment
docker-compose down && docker-compose up -d
```

For detailed Docker environment information, see [README-Docker.md](README-Docker.md).
