# MySQL Database for AMC MRP
FROM mysql:8.0

# Set environment variables
ENV MYSQL_ROOT_PASSWORD=toor

# Copy initialization scripts
# These will be executed in alphabetical order when the container starts
COPY DDL.sql /docker-entrypoint-initdb.d/01-schema.sql
COPY test_data/testdata.sql /docker-entrypoint-initdb.d/02-data.sql

# Expose MySQL port
EXPOSE 3306

# Health check
HEALTHCHECK --interval=10s --timeout=20s --retries=10 --start-period=40s \
    CMD mysqladmin ping -h localhost -u root -p${MYSQL_ROOT_PASSWORD} || exit 1
