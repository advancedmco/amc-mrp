# Migration Notes: Custom Docker Builds

## Date: November 3, 2025

## Summary

Successfully migrated the AMC MRP system from runtime-based Docker images to custom Dockerfiles for each service. Document generation capabilities have been integrated into the frontend service.

## Changes Made

### 1. Consolidated Document Generation into Frontend

**Rationale:** The frontend Flask application was already importing and using the document generators, so consolidating them into a single service eliminates unnecessary complexity.

**Changes:**
- Moved `filegen/src/*.py` → `frontend/generators/`
- Moved `filegen/file_templates/*.docx` → `frontend/templates/documents/`
- Merged `filegen/requirements.txt` into `frontend/requirements.txt`
- The old `filegen/` directory remains for reference but is no longer used

### 2. Created Custom Dockerfiles

**database/Dockerfile**
- Based on mysql:8.0
- Automatically loads DDL.sql and testdata.sql on startup
- Fresh database each time (tmpfs storage)

**backend/Dockerfile**
- Based on python:3.11-slim
- Installs Python dependencies from requirements.txt
- Runs QuickBooks integration daemon

**frontend/Dockerfile**
- Based on python:3.11-slim
- Installs system dependencies: pandoc, LaTeX, LibreOffice
- Installs Python dependencies including document generation libraries
- Runs Flask web dashboard with integrated document generation

### 3. Added Build Optimization

Created `.dockerignore` files for each component to exclude:
- Git files and directories
- Python cache and virtual environments
- IDE configuration files
- Documentation and test files
- Generated output files

### 4. Updated docker-compose.yml

- All services now use `build` instead of `image` with `command`
- Simplified service definitions
- Maintained volume mounts for hot-reloading during development
- Removed the separate `generator` service

### 5. Updated Documentation

- [README.md](README.md) - Updated all commands and service references
- [CLAUDE.md](CLAUDE.md) - Updated development workflow and architecture
- [BUILD.md](BUILD.md) - New guide for Docker build process

## Service Changes

### Before

- **mysql** - MySQL image with runtime script injection
- **generator** - Python image with apt-get install at runtime
- **frontend** - Python image with apt-get install at runtime
- **backend** - Python image with pip install at runtime

### After

- **mysql** - Custom build with schema baked in
- **frontend** - Custom build with Flask + document generators + system dependencies
- **backend** - Custom build with QuickBooks integration dependencies

## Environment Variables Updated

Frontend environment variables now point to new paths:
- `COC_TEMPLATE_PATH`: `/app/templates/documents/COC Template.docx`
- `PO_TEMPLATE_PATH`: `/app/templates/documents/PO Template.docx`
- `COC_OUTPUT_DIR`: `/app/CACHE`
- `PO_OUTPUT_DIR`: `/app/CACHE`

## Breaking Changes

### Container Names
No changes - container names remain the same:
- `mrp-db`
- `mrp-frontend`
- `mrp-backend`

### Service Names in docker-compose.yml
Changed:
- ~~`generator`~~ (removed, functionality moved to frontend)

Unchanged:
- `mysql`
- `frontend`
- `backend`

### Commands

Old way (runtime installation):
```bash
docker compose up -d  # Long startup due to apt-get/pip install
```

New way (pre-built images):
```bash
docker compose build  # Build images first
docker compose up -d  # Fast startup, dependencies already installed
```

### Test Commands

Old:
```bash
docker compose exec gen-app python src/test_coc.py
docker compose exec gen-app python src/test_po.py
```

New:
```bash
docker compose exec frontend python generators/test_coc.py
docker compose exec frontend python generators/test_po.py
```

## Benefits

1. **Faster Startup** - Dependencies pre-installed in images
2. **Consistency** - Same environment every time
3. **Better CI/CD** - Images can be built once and deployed multiple times
4. **Cleaner Architecture** - Document generation logically belongs with the web frontend
5. **Easier Debugging** - Clear separation of concerns
6. **Reproducibility** - Exact versions of system and Python packages

## Rollback Instructions

If you need to revert to the old setup:

1. Restore original docker-compose.yml from git history:
   ```bash
   git checkout HEAD~1 docker-compose.yml
   ```

2. Remove custom Dockerfiles:
   ```bash
   rm */Dockerfile
   rm */.dockerignore
   ```

3. Restart services:
   ```bash
   docker compose down
   docker compose up -d
   ```

## Testing Performed

- ✅ All services build successfully
- ✅ All services start and run
- ✅ Database initializes with schema and test data
- ✅ Frontend service running on port 5001
- ✅ Backend service running on port 5002
- ✅ Hot-reloading works for code changes
- ✅ Volume mounts working correctly

## Next Steps

1. Test document generation functionality:
   ```bash
   docker compose exec frontend python generators/test_coc.py
   docker compose exec frontend python generators/test_po.py
   ```

2. Test QuickBooks integration:
   ```bash
   docker compose exec backend python test_qb_integration.py
   ```

3. Consider removing old `filegen/` directory once confirmed everything works

4. Update any CI/CD pipelines to include build step

5. Consider pushing images to a registry for faster deployment

## Notes

- The `filegen/` directory still exists but is not used by the Docker setup
- You may want to keep it for reference or remove it after confirming the migration is successful
- All original functionality is preserved, just reorganized
- Frontend requirements.txt now includes all document generation dependencies

## Questions or Issues?

If you encounter any issues:

1. Check service logs: `docker compose logs [service-name]`
2. Rebuild from scratch: `docker compose build --no-cache`
3. Verify .env file has all required variables
4. Consult [BUILD.md](BUILD.md) for detailed build instructions
5. Review [CLAUDE.md](CLAUDE.md) for development workflow
