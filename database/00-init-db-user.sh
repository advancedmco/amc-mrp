#!/bin/bash
set -e

# Database Initialization Script
# This script creates the database and user using credentials from environment variables
# Executed first by docker-entrypoint-initdb.d (00- prefix ensures execution order)

echo "Initializing database and user with environment variables..."

# Use environment variables with defaults for safety
DB_NAME="${DB_NAME:-amcmrp}"
DB_USER="${DB_USER:-amc}"
DB_PASSWORD="${DB_PASSWORD:-changeme}"

# Execute SQL commands to create database and user
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" <<-EOSQL
    -- Create database if it doesn't exist
    CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\`;

    -- Create user if it doesn't exist
    CREATE USER IF NOT EXISTS '${DB_USER}'@'%' IDENTIFIED BY '${DB_PASSWORD}';

    -- Grant all privileges on the database to the user
    GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'%';

    -- Flush privileges to ensure changes take effect
    FLUSH PRIVILEGES;

    -- Switch to the newly created database
    USE \`${DB_NAME}\`;
EOSQL

echo "Database '${DB_NAME}' and user '${DB_USER}' initialized successfully!"
