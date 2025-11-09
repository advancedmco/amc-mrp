# MariaDB Database for AMC MRP
FROM mariadb:11

# Set environment variables
ENV MYSQL_ROOT_PASSWORD=toor

# Copy custom MariaDB configuration (optimized for tmpfs and dev)
COPY mariadb.cnf /etc/mysql/conf.d/custom.cnf

# Copy initialization scripts
# These will be executed in alphabetical order when the container starts
COPY DDL.sql /docker-entrypoint-initdb.d/01-schema.sql
COPY base_initial_data.sql /docker-entrypoint-initdb.d/02-base-data.sql

# Create log directory for MariaDB
RUN mkdir -p /var/log/mysql && \
    chown -R mysql:mysql /var/log/mysql

# Expose MySQL port
EXPOSE 3306

# Health check - wait longer for initialization to complete
# Using mariadb-admin ping is more reliable than trying to connect to a specific database
HEALTHCHECK --interval=5s --timeout=3s --retries=20 --start-period=60s \
    CMD mariadb-admin ping -h localhost -u root -p${MYSQL_ROOT_PASSWORD} --silent || exit 1
