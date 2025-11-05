# MariaDB Database for AMC MRP
FROM mariadb:11

# Build argument to choose data initialization mode
# Options: test (comprehensive test data) or minimal (basic production data)
ARG DATA_MODE=test

# Copy custom MariaDB configuration (optimized for tmpfs and dev)
COPY mariadb.cnf /etc/mysql/conf.d/custom.cnf

# Copy initialization scripts
# These will be executed in alphabetical order when the container starts:
# 1. Init script creates database and user from environment variables
# 2. DDL creates schema (tables, views, triggers, indexes)
# 3. Data script loads either test data or minimal production data

COPY 00-init-db-user.sh /docker-entrypoint-initdb.d/00-init-db-user.sh
COPY DDL.sql /docker-entrypoint-initdb.d/01-schema.sql

# Copy the appropriate data file based on build argument
COPY test_data/${DATA_MODE}data.sql /docker-entrypoint-initdb.d/02-data.sql

# Make init script executable
RUN chmod +x /docker-entrypoint-initdb.d/00-init-db-user.sh

# Create log directory for MariaDB
RUN mkdir -p /var/log/mysql && \
    chown -R mysql:mysql /var/log/mysql

# Expose MySQL port
EXPOSE 3306

# Health check - wait longer for initialization to complete
# Using mariadb-admin ping is more reliable than trying to connect to a specific database
HEALTHCHECK --interval=5s --timeout=3s --retries=20 --start-period=60s \
    CMD mariadb-admin ping -h localhost -u root -p${MYSQL_ROOT_PASSWORD} --silent || exit 1
