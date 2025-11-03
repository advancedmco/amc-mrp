# Docker Build Guide

## Overview

The AMC MRP system now uses custom Dockerfiles for each service, providing consistent, reproducible builds with all dependencies baked in.

## Architecture

### Services with Custom Builds

1. **database/** - MySQL 8.0 with schema and test data
2. **frontend/** - Flask web dashboard with integrated document generators
3. **backend/** - QuickBooks integration daemon

Each service has:
- `Dockerfile` - Build configuration
- `.dockerignore` - Build optimization (excludes unnecessary files)
- `requirements.txt` - Python dependencies (where applicable)

## Quick Start

```bash
# First time setup
docker compose build
docker compose up -d

# Verify services are running
docker compose ps
```

## Common Build Scenarios

### Building All Services

```bash
# With cache (faster)
docker compose build

# Without cache (clean build)
docker compose build --no-cache
```

### Building Specific Service

```bash
# Build just frontend
docker compose build frontend

# Build just backend
docker compose build backend

# Build just database
docker compose build mysql
```

### Rebuild After Changes

**Code changes only (Python files):**
- No rebuild needed - changes are live via mounted volumes

**Dependency changes (requirements.txt):**
```bash
docker compose build [service-name]
docker compose up -d [service-name]
```

**Dockerfile changes:**
```bash
docker compose build [service-name]
docker compose up -d [service-name]
```

**Database schema changes (DDL.sql):**
```bash
docker compose build mysql
docker compose down && docker compose up -d
```

## Build Optimization

### .dockerignore Files

Each component has a `.dockerignore` file that excludes:
- Git files and directories
- Python cache and virtual environments
- IDE configuration
- Documentation files
- Test files
- Generated files

This reduces build context size and speeds up builds.

### Layer Caching

Dockerfiles are structured to maximize layer caching:
1. Base image pulled first
2. Dependencies installed (requirements.txt)
3. Application code copied last

This means changing code doesn't require reinstalling dependencies.

## Troubleshooting

### Build Fails with "Context Too Large"

Check your `.dockerignore` files are present and properly excluding unnecessary files.

### Dependencies Not Updating

Force a clean rebuild:
```bash
docker compose build --no-cache [service-name]
```

### Service Won't Start After Build

Check logs for errors:
```bash
docker compose logs [service-name]
```

Verify the Dockerfile syntax and all required files are present.

### Out of Disk Space

Clean up old images and containers:
```bash
docker system prune -a
```

## Development Workflow

1. **Make code changes** - Edit files in backend/, frontend/, or database/
2. **Test changes** - For code only, no rebuild needed (hot-reload)
3. **Add dependencies** - Update requirements.txt and rebuild service
4. **Modify Dockerfile** - Rebuild service after Dockerfile changes
5. **Commit changes** - Include Dockerfile and requirements.txt updates

## Best Practices

- **Always commit Dockerfile changes** with the code that requires them
- **Update .dockerignore** when adding new directories that shouldn't be in the build context
- **Test builds locally** before committing Dockerfile changes
- **Use specific versions** in requirements.txt for reproducibility
- **Keep Dockerfiles simple** - complex logic belongs in setup scripts

## Build Times

Approximate build times on typical hardware:

- **database**: ~30 seconds (cached), ~60 seconds (clean)
- **backend**: ~1 minute (cached), ~2 minutes (clean)
- **frontend**: ~5 minutes (cached), ~8 minutes (clean)
  - Frontend is slower due to LaTeX and LibreOffice installation

## CI/CD Integration (Future)

When setting up CI/CD pipelines:

```bash
# In CI/CD pipeline
docker compose build --no-cache
docker compose up -d
docker compose exec frontend python generators/test_coc.py
docker compose exec backend python test_qb_integration.py
```

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Dockerfile Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- Main project README: [README.md](README.md)
- Development instructions: [CLAUDE.md](CLAUDE.md)
