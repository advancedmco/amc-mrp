# Claude Development Instructions for AMC MRP

## Critical Rules

### Always Check First
- **ALWAYS** read this file before starting any development work
- Check `general_instructions.txt` for additional rules
- Review component-specific instructions in subdirectories (backend/instructions.txt, frontend/instructions.txt, etc.)

### Docker Environment
- **ALWAYS** ensure Docker Compose is running before development
- Each service has its own Dockerfile for consistent builds
- **REBUILD** containers when dependencies or Dockerfiles change: `docker compose build`
- For code changes only, no rebuild needed (hot-reloading enabled)
- When dependencies change, update requirements.txt in the component directory and rebuild

### File Management
- **ALWAYS** edit existing files rather than creating new ones
- Clean up temporary artifacts, test scripts, and debugging files when done
- Assign files to correct folders based on their purpose:
  - `backend/` - QuickBooks integration daemon
  - `frontend/` - Web dashboard (Flask app) with integrated document generators
  - `frontend/generators/` - Document generation code (COC, PO)
  - `frontend/templates/documents/` - Document templates
  - `database/` - SQL schema and test data
  - `DevAssets/` - Examples and development documentation

### Scope Awareness
- Be aware of which component you're working in
- Changes should be scoped to the appropriate component
- Update main README.md and docker-compose.yml when adding:
  - New environment variables
  - New services or dependencies
  - New setup procedures

### Documentation Standards
- Only write **critical** information for understanding, running, and configuring
- **NEVER** include:
  - Detailed file structure trees (too dynamic in dev environment)
  - Exhaustive command references
  - Redundant information already in component READMEs
- Keep documentation concise and actionable

## Project Architecture

### Component Overview

**backend/** - QuickBooks Integration Daemon
- Maintains OAuth tokens and keeps them alive
- Caches vendors, customers, products every hour
- Provides fuzzy search API for web dashboard
- Runs as persistent daemon on port 5002
- Custom Dockerfile with Python dependencies

**frontend/** - Web Dashboard and Document Generator (Flask)
- User interface for work orders and document generation
- Integrates with backend for QuickBooks data
- Includes document generators (COC, PO) in generators/ folder
- Templates stored in templates/documents/
- Serves on port 5001
- Custom Dockerfile with pandoc, LaTeX, LibreOffice
- Contains templates and static assets

**database/** - MariaDB Database
- Schema: DDL.sql
- Test data: test_data/testdata.sql
- Fresh database on each Docker startup (tmpfs)
- No persistent volumes in development
- Custom Dockerfile extending mariadb:11

### Docker Services

**mysql** (mrp-db)
- Port: 3307 → 3306
- Credentials: amc / Workbench.lavender.chrome
- Database: amcmrp
- Build: ./database/Dockerfile

**frontend** (mrp-frontend)
- Flask web dashboard with integrated document generation
- Port: 5001 → 5000
- Source: /app (mounted from ./frontend)
- Includes: COC/PO generators, templates, web interface
- Dependencies: pandoc, LaTeX, LibreOffice, python-docx
- Build: ./frontend/Dockerfile

**backend** (mrp-backend)
- QuickBooks integration daemon
- Port: 5002
- Source: /app (mounted from ./backend)
- Build: ./backend/Dockerfile

## Development Workflow

### Starting Development Session
```bash
# Check Docker is running
docker compose ps

# Build images (first time or after Dockerfile/requirements changes)
docker compose build

# Start services
docker compose up -d

# Verify all services healthy
docker compose ps
```

### Testing Code Changes

**For Python Code (backend, frontend):**
- Code changes are live (mounted volumes)
- No container rebuild needed for code changes only
- For new dependencies:
  ```bash
  # 1. Add to appropriate requirements.txt (backend/ or frontend/)
  # 2. Rebuild the service
  docker compose build [service-name]
  # 3. Restart the service
  docker compose up -d [service-name]
  ```

**For Database Changes:**
- Edit DDL.sql or testdata.sql
- Rebuild and restart:
  ```bash
  docker compose build mysql
  docker compose down && docker compose up -d
  ```

**For Dockerfile Changes:**
- Always rebuild after modifying any Dockerfile:
  ```bash
  docker compose build [service-name]
  docker compose up -d [service-name]
  ```

### Running Tests
```bash
# COC generation test
docker compose exec frontend python generators/test_coc.py

# PO generation test
docker compose exec frontend python generators/test_po.py

# QuickBooks integration test
docker compose exec backend python test_qb_integration.py
```

### Debugging
```bash
# View live logs
docker compose logs -f [service-name]

# Access container shell
docker compose exec [service-name] bash

# Check installed packages
docker compose exec [service-name] pip list

# Test database connection
docker compose exec frontend python -c "import mysql.connector; print('OK')"

# Rebuild from scratch (no cache)
docker compose build --no-cache [service-name]
```

## Business Logic

### Work Order Flow
1. Customer PO received → Create Work Order (sequential number)
2. Create BOM with processes (raw material, plating, heat treatment, grinding)
3. Assign vendors to each process (from QuickBooks)
4. Generate internal POs for vendor operations
5. Track work order status through manufacturing
6. Generate COC for military clients after completion
7. Create invoice in QuickBooks

### Document Generation
- **COCs:** Military clients only, generated after work completion
- **Internal POs:** Link to work order and BOM, sent to vendors
- All documents logged in database
- Generated files stored in CACHE directories
- PDF output required for all documents

### QuickBooks Integration
- Single source of truth for customers, vendors, products
- Database stores supplemental data not in QuickBooks
- Daemon keeps tokens alive (check interval: minimum allowed)
- Hourly cache refresh for search performance
- Fuzzy search support for: client names, vendor names, POs, products

## Common Tasks

### Adding a New Environment Variable
1. Add to `.env` file (never commit actual values)
2. Add example to `example.env`
3. Add to appropriate service in docker-compose.yml
4. Update README.md environment section
5. Document in component-specific instructions if needed

### Adding a New Python Dependency
1. Add to appropriate requirements.txt (backend/ or frontend/)
2. Rebuild the service:
   ```bash
   docker compose build [service-name]
   docker compose up -d [service-name]
   ```
3. Verify functionality
4. Document if it affects setup or configuration

### Adding a New Document Template
1. Place template in frontend/templates/documents/
2. Update generator script in frontend/generators/ (cocGenerate.py or poGenerate.py)
3. Add environment variable if path needs configuration
4. Test generation with test scripts
5. Update database logging if needed

### Modifying Database Schema
1. Edit database/DDL.sql
2. Update database/test_data/testdata.sql if needed
3. Test with fresh database:
   ```bash
   docker compose down && docker compose up -d
   ```
4. Update affected Python code
5. Document schema changes in database/instructions.txt

## Security Considerations

### Development
- Default credentials are acceptable (documented in README)
- No persistent storage (fresh DB each startup is fine)
- Local network only

### Never Commit
- Real credentials in .env
- QuickBooks client secrets
- Production API keys
- Generated documents with real customer data

### Production Deployment (Future)
- Change all default passwords
- Use secrets management (Docker secrets, Vault)
- Add persistent database volumes
- Implement SSL/TLS
- Add authentication/authorization
- Enable audit logging

## Error Handling

### Database Connection Failures
- Check MariaDB health: `docker compose ps`
- Verify credentials in .env match docker-compose.yml
- Check network connectivity: `docker network ls`
- Review logs: `docker compose logs mysql`

### Document Generation Failures
- Verify pandoc installed: `docker compose exec frontend pandoc --version`
- Check LaTeX: `docker compose exec frontend xelatex --version`
- Verify LibreOffice: `docker compose exec frontend libreoffice --version`
- Check template file exists in frontend/templates/documents/
- Review generator logs for specific errors

### QuickBooks API Failures
- Check token expiration in backend logs
- Verify credentials in .env
- Check API rate limits
- Review test script: test_qb_integration.py

## Python Virtual Environments

### When to Use venv
- For component-specific development outside Docker
- When testing dependencies before Docker integration
- For IDE autocomplete and type checking

### Setup
Each component (backend/, frontend/) should have setup instructions in their respective README.md or instructions.txt.

General pattern:
```bash
cd [component-directory]
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Important
- venv is for local development only
- Docker containers use their own Python environments
- Don't commit venv/ directories to git
- Keep requirements.txt synchronized with Docker and venv

## Maintenance Tasks

### Cleaning Up
```bash
# Remove stopped containers
docker compose down

# Remove all volumes (fresh start)
docker compose down -v

# Clean Docker system
docker system prune

# Remove temporary test files
rm -f /tmp/test_*.py /tmp/debug_*.log
```

### Before Committing
- [ ] Remove temporary test files and scripts
- [ ] Update requirements.txt if dependencies changed
- [ ] Update README.md if functionality changed
- [ ] Verify .env not modified (or reverted to examples)
- [ ] Check docker-compose.yml for accidental changes
- [ ] Run tests to verify nothing broken
- [ ] Review component-specific instructions for updates

## Quick Reference

### Essential Commands
```bash
# Build all services
docker compose build

# Build specific service
docker compose build [service-name]

# Start everything
docker compose up -d

# Stop everything
docker compose down

# Restart one service
docker compose restart [service-name]

# View logs
docker compose logs -f [service-name]

# Access shell
docker compose exec [service-name] bash

# Run Python script
docker compose exec [service-name] python [script-path]

# Database access
mysql -h localhost -P 3307 -u amc -p amcmrp
```

### Service Names
- `mysql` - Database
- `frontend` - Web dashboard and document generator
- `backend` - QuickBooks integration

### Important Files
- `docker-compose.yml` - Service orchestration
- `.env` - Environment variables (never commit)
- `example.env` - Environment template
- `README.md` - Main documentation
- `CLAUDE.md` - This file (development instructions)
- `general_instructions.txt` - General development rules
- `[component]/Dockerfile` - Service build configuration
- `[component]/.dockerignore` - Build optimization
- `[component]/instructions.txt` - Component-specific rules

---

**Remember:** Always read this file and check for updates before starting work!
- don't add test files, artifacts, or md files to the repo unless explicitly asked. 