#!/bin/bash
# Database Setup Validation Script
# This script validates your database configuration before starting

set -e

echo "=========================================="
echo "AMC MRP Database Setup Validator"
echo "=========================================="
echo ""

# Check if .env exists
echo "✓ Checking for .env file..."
if [ ! -f ".env" ]; then
    echo "❌ ERROR: .env file not found"
    echo "   Run: cp example.env .env"
    echo "   Then edit .env with your credentials"
    exit 1
fi
echo "✓ .env file found"
echo ""

# Load environment variables
set -a
source .env
set +a

# Check required variables
echo "✓ Checking required environment variables..."

check_var() {
    var_name=$1
    var_value=${!var_name}

    if [ -z "$var_value" ]; then
        echo "❌ ERROR: $var_name is not set"
        exit 1
    fi

    # Check if it's still the example value
    case $var_name in
        DB_PASSWORD)
            if [ "$var_value" = "secure_password_here" ]; then
                echo "⚠️  WARNING: $var_name is still set to example value"
                echo "   Please update with a secure password"
            else
                echo "✓ $var_name is set"
            fi
            ;;
        QUICKBOOKS_CLIENT_ID)
            if [ "$var_value" = "your_50_char_client_id_here" ]; then
                echo "⚠️  WARNING: $var_name is still set to example value"
            else
                echo "✓ $var_name is set"
            fi
            ;;
        QUICKBOOKS_CLIENT_SECRET)
            if [ "$var_value" = "your_40_char_client_secret_here" ]; then
                echo "⚠️  WARNING: $var_name is still set to example value"
            else
                echo "✓ $var_name is set"
            fi
            ;;
        FLASK_SECRET_KEY)
            if [ "$var_value" = "your_flask_secret_key_change_this_in_production" ]; then
                echo "⚠️  WARNING: $var_name is still set to example value"
            else
                echo "✓ $var_name is set"
            fi
            ;;
        *)
            echo "✓ $var_name is set"
            ;;
    esac
}

# Check required database variables
check_var "MYSQL_ROOT_PASSWORD"
check_var "DB_NAME"
check_var "DB_USER"
check_var "DB_PASSWORD"
check_var "DB_HOST"

echo ""

# Check optional variables
echo "✓ Checking optional variables..."
DATA_MODE=${DATA_MODE:-test}
echo "✓ DATA_MODE: $DATA_MODE"

if [ "$DATA_MODE" != "test" ] && [ "$DATA_MODE" != "minimal" ]; then
    echo "⚠️  WARNING: DATA_MODE should be 'test' or 'minimal', got '$DATA_MODE'"
    echo "   Defaulting to 'test'"
fi

echo ""

# Check database files
echo "✓ Checking database initialization files..."

check_file() {
    file_path=$1
    file_desc=$2

    if [ ! -f "$file_path" ]; then
        echo "❌ ERROR: $file_desc not found at $file_path"
        exit 1
    fi
    echo "✓ $file_desc found"
}

check_file "database/00-init-db-user.sh" "Init script"
check_file "database/DDL.sql" "Schema definition"
check_file "database/test_data/testdata.sql" "Test data"
check_file "database/test_data/minimaldata.sql" "Minimal data"
check_file "database/Dockerfile" "Database Dockerfile"
check_file "database/mariadb.cnf" "MariaDB config"

echo ""

# Check init script is executable
echo "✓ Checking init script permissions..."
if [ ! -x "database/00-init-db-user.sh" ]; then
    echo "⚠️  WARNING: Init script is not executable"
    echo "   This is OK - Dockerfile sets permissions during build"
else
    echo "✓ Init script is executable"
fi

echo ""

# Validate SQL syntax (basic check)
echo "✓ Checking SQL file syntax..."

check_sql() {
    file=$1
    name=$2

    # Check for common SQL syntax issues
    if grep -q "Workbench.lavender.chrome" "$file"; then
        echo "❌ ERROR: $name contains hardcoded password"
        echo "   This should have been removed"
        exit 1
    fi

    # Check for proper USE statement in DDL
    if [ "$name" = "DDL.sql" ]; then
        if ! grep -q "USE amcmrp;" "$file"; then
            echo "❌ ERROR: $name missing 'USE amcmrp;' statement"
            exit 1
        fi
    fi

    echo "✓ $name syntax OK"
}

check_sql "database/DDL.sql" "DDL.sql"
check_sql "database/test_data/testdata.sql" "testdata.sql"
check_sql "database/test_data/minimaldata.sql" "minimaldata.sql"

echo ""

# Check docker-compose.yml
echo "✓ Checking docker-compose.yml..."
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ ERROR: docker-compose.yml not found"
    exit 1
fi

# Check that docker-compose references the DATA_MODE arg
if ! grep -q "DATA_MODE" docker-compose.yml; then
    echo "⚠️  WARNING: docker-compose.yml doesn't reference DATA_MODE"
else
    echo "✓ docker-compose.yml has DATA_MODE configuration"
fi

echo ""
echo "=========================================="
echo "✓ Validation Complete!"
echo "=========================================="
echo ""
echo "Your database configuration looks good!"
echo ""
echo "To start the database:"
echo "  docker compose up mysql"
echo ""
echo "To start with minimal data instead of test data:"
echo "  DATA_MODE=minimal docker compose up --build mysql"
echo ""
echo "To start all services:"
echo "  docker compose up"
echo ""
echo "To rebuild after changes:"
echo "  docker compose down"
echo "  docker compose up --build"
echo ""
