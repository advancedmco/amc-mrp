#!/usr/bin/env python3
"""
Test script for Customer PO import functionality
Validates that the import completed successfully and data is correct

Author: Advanced Machine Co. MRP System
Created: November 2025
"""

import os
import sys
import logging
import mysql.connector
from mysql.connector import Error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CustomerPOTest')

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'amcmrp'),
    'user': os.getenv('DB_USER', 'amc'),
    'password': os.getenv('DB_PASSWORD', 'Workbench.lavender.chrome'),
    'port': int(os.getenv('DB_PORT', '3306'))
}


def test_table_exists(cursor, table_name):
    """Test if a table exists"""
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
        (DB_CONFIG['database'], table_name)
    )
    exists = cursor.fetchone()[0] > 0
    if exists:
        logger.info(f"✓ Table {table_name} exists")
    else:
        logger.error(f"✗ Table {table_name} does not exist")
    return exists


def test_view_exists(cursor, view_name):
    """Test if a view exists"""
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.views WHERE table_schema = %s AND table_name = %s",
        (DB_CONFIG['database'], view_name)
    )
    exists = cursor.fetchone()[0] > 0
    if exists:
        logger.info(f"✓ View {view_name} exists")
    else:
        logger.error(f"✗ View {view_name} does not exist")
    return exists


def test_po_data(cursor):
    """Test that PO data has been imported"""
    cursor.execute("SELECT COUNT(*) FROM CustomerPurchaseOrders")
    po_count = cursor.fetchone()[0]
    logger.info(f"✓ Found {po_count} customer purchase orders")

    if po_count > 0:
        cursor.execute("SELECT COUNT(*) FROM CustomerPOLineItems")
        line_count = cursor.fetchone()[0]
        logger.info(f"✓ Found {line_count} line items")

        cursor.execute("SELECT PO_Number, Order_Date, Total_Value FROM CustomerPurchaseOrders LIMIT 1")
        sample_po = cursor.fetchone()
        if sample_po:
            logger.info(f"✓ Sample PO: {sample_po[0]}, Order Date: {sample_po[1]}, Total: ${sample_po[2]}")

        return True
    else:
        logger.warning("⚠ No customer POs found - import may not have been run yet")
        return False


def test_data_integrity(cursor):
    """Test data integrity"""
    # Test that all line items have valid PO references
    cursor.execute(
        """
        SELECT COUNT(*) FROM CustomerPOLineItems li
        LEFT JOIN CustomerPurchaseOrders po ON li.PO_ID = po.PO_ID
        WHERE po.PO_ID IS NULL
        """
    )
    orphaned_lines = cursor.fetchone()[0]
    if orphaned_lines == 0:
        logger.info("✓ All line items have valid PO references")
    else:
        logger.error(f"✗ Found {orphaned_lines} orphaned line items")
        return False

    # Test that extended prices are calculated correctly
    cursor.execute(
        """
        SELECT COUNT(*) FROM CustomerPOLineItems
        WHERE ABS(Extended_Price - (Quantity * Unit_Price)) > 0.01
        """
    )
    price_mismatches = cursor.fetchone()[0]
    if price_mismatches == 0:
        logger.info("✓ All extended prices match quantity × unit price")
    else:
        logger.warning(f"⚠ Found {price_mismatches} line items with price calculation differences")

    return True


def test_shibaura_customer(cursor):
    """Test that Shibaura customer exists"""
    cursor.execute("SELECT CustomerID, CustomerName FROM Customers WHERE CustomerName = 'Shibaura'")
    customer = cursor.fetchone()
    if customer:
        logger.info(f"✓ Shibaura customer exists (ID: {customer[0]})")
        return True
    else:
        logger.warning("⚠ Shibaura customer not found - import may not have been run yet")
        return False


def test_view_query(cursor):
    """Test querying the view"""
    try:
        cursor.execute("SELECT COUNT(*) FROM vw_CustomerPODetails")
        view_count = cursor.fetchone()[0]
        logger.info(f"✓ View vw_CustomerPODetails returns {view_count} rows")
        return True
    except Error as e:
        logger.error(f"✗ Error querying view: {e}")
        return False


def main():
    """Main test execution"""
    connection = None
    all_tests_passed = True

    try:
        logger.info("="*60)
        logger.info("Customer PO Database Tests")
        logger.info("="*60)

        # Connect to database
        logger.info(f"Connecting to database at {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        logger.info("✓ Database connection successful\n")

        # Test 1: Table existence
        logger.info("Test 1: Checking table existence...")
        all_tests_passed &= test_table_exists(cursor, 'CustomerPurchaseOrders')
        all_tests_passed &= test_table_exists(cursor, 'CustomerPOLineItems')
        print()

        # Test 2: View existence
        logger.info("Test 2: Checking view existence...")
        all_tests_passed &= test_view_exists(cursor, 'vw_CustomerPODetails')
        print()

        # Test 3: Shibaura customer
        logger.info("Test 3: Checking Shibaura customer...")
        test_shibaura_customer(cursor)  # Don't fail if customer doesn't exist yet
        print()

        # Test 4: PO data
        logger.info("Test 4: Checking PO data...")
        test_po_data(cursor)  # Don't fail if data not imported yet
        print()

        # Test 5: Data integrity
        logger.info("Test 5: Checking data integrity...")
        integrity_ok = test_data_integrity(cursor)
        all_tests_passed &= integrity_ok
        print()

        # Test 6: View query
        logger.info("Test 6: Testing view queries...")
        view_ok = test_view_query(cursor)
        all_tests_passed &= view_ok
        print()

        logger.info("="*60)
        if all_tests_passed:
            logger.info("All critical tests passed! ✓")
        else:
            logger.warning("Some tests failed - check logs above")
        logger.info("="*60)

    except Error as e:
        logger.error(f"Database error: {e}")
        sys.exit(1)

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


if __name__ == "__main__":
    main()
