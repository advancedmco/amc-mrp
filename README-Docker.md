# AMC MRP Docker Environment

This Docker Compose setup provides a complete development environment for the Advanced Machine Co. MRP system with MySQL database and Python application services.

## Prerequisites

- Docker Desktop installed and running
- Docker Compose v3.8 or higher

## Quick Start

1. **Clone/Navigate to the project directory:**
   ```bash
   cd /path/to/amc-mrp
   ```

2. **Start the environment:**
   ```bash
   docker compose up -d
   ```

3. **Access the Python container:**
   ```bash
   docker compose exec python-app bash
   ```

4. **Run the COC test script:**
   ```bash
   # Inside the Python container
   python test_coc.py
   ```

## Services

### MySQL Database (`mysql`)
- **Image:** mysql:8.0
- **Port:** 3306 (exposed to host)
- **Database:** amcmrp
- **User:** amc / amcpassword
- **Root Password:** rootpassword
- **Features:**
  - Fresh database on each startup (no persistent volumes)
  - Automatically loads DDL.sql and data.sql on initialization
  - Health checks ensure database is ready before Python app starts

### Python Application (`python-app`)
- **Base Image:** python:3.11-slim (pre-built, no custom Dockerfile needed)
- **Dependencies:** Runtime installation from DevAssets/pythondocker/requirements.txt
- **Includes:** pandoc, texlive-xetex for PDF generation (installed at startup)
- **Working Directory:** /app/WORKING
- **Features:**
  - Live code mounting for development
  - Pre-configured environment variables for database connection
  - COC template and output directory mounted
  - Dependencies installed automatically on container start

## Environment Variables

The following environment variables are automatically configured:

### Database Connection
- `DB_HOST`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_PORT`

## Common Commands

### Start Services
```bash
# Start all services in background
docker compose up -d

# Start with logs visible
docker compose up

# Start specific service
docker compose up mysql
```

### Stop Services
```bash
# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v
```

### Development Workflow
```bash
# Access Python container shell
docker compose exec python-app bash

# Run COC generator test
docker compose exec python-app python test_coc.py

# Run specific Python script
docker compose exec python-app python cocGenerate.py

# View logs
docker compose logs python-app
docker compose logs mysql

# Follow logs
docker compose logs -f python-app
```

### Database Access
```bash
# Connect to MySQL from host
mysql -h localhost -P 3306 -u amc -pamcpassword amcmrp

# Connect from within Python container
docker compose exec python-app mysql -h mysql -u amc -pamcpassword amcmrp

# Access MySQL container directly
docker compose exec mysql mysql -u amc -pamcpassword amcmrp
```

## Development Features

### Live Code Reloading
- Changes to files in `./WORKING/` are immediately available in the container
- No need to rebuild the container for code changes

### Fresh Database
- Database is recreated on each `docker compose up`
- Always starts with clean schema and sample data
- Perfect for development and testing

### PDF Generation
- Full pandoc and LaTeX support for high-quality PDF generation
- Generated files saved to `./output/` directory
- Accessible from both container and host

## Troubleshooting

### Database Connection Issues
```bash
# Check if MySQL is healthy
docker compose ps

# View MySQL logs
docker compose logs mysql

# Test database connection
docker compose exec python-app python -c "import mysql.connector; print('MySQL connector available')"
```

### Python Dependencies
```bash
# Rebuild Python container if requirements change
docker compose build python-app

# Check installed packages
docker compose exec python-app pip list
```

### PDF Generation Issues
```bash
# Test pandoc installation
docker compose exec python-app pandoc --version

# Test LaTeX installation
docker compose exec python-app xelatex --version
```

### File Permissions
```bash
# Fix output directory permissions
sudo chown -R $USER:$USER ./output
```

## Production Considerations

For production deployment:
1. Change default passwords in docker compose.yml
2. Use environment files (.env) for sensitive data
3. Add persistent volumes for database if needed
4. Configure proper networking and security
5. Add monitoring and logging services

## Extending the Environment

### Adding a Web Interface
Uncomment the `web-app` service in docker compose.yml and create the corresponding web application.

### Adding More Services
Add additional services to docker compose.yml following the same pattern:
- Use the `amc-mrp-network` network
- Add appropriate `depends_on` relationships
- Mount necessary volumes
- Configure environment variables

## Support

For issues with the Docker environment:
1. Check service logs: `docker compose logs [service-name]`
2. Verify file permissions and paths
3. Ensure Docker Desktop has sufficient resources allocated
4. Try rebuilding containers: `docker compose build --no-cache`
