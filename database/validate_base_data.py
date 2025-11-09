#!/usr/bin/env python3
"""
Base Data Validation Script
Validates that all base initial data is loaded correctly and all constraints are satisfied

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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('BaseDataValidator')

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'amcmrp'),
    'user': os.getenv('DB_USER', 'amc'),
    'password': os.getenv('DB_PASSWORD', 'Workbench.lavender.chrome'),
    'port': int(os.getenv('DB_PORT', '3306'))
}

# Expected record counts from base_initial_data.sql
EXPECTED_COUNTS = {
    'Customers': 5,
    'Vendors': 11,
    'Parts': 10,
    'CustomerPurchaseOrders': 3,
    'CustomerPOLineItems': 6,
    'WorkOrders': 3,
    'BOM': 3,
    'BOMProcesses': 15,
    'PurchaseOrdersLog': 2,
    'CertificatesLog': 1,
    'WorkOrderStatusHistory': 7,
    'ProductionStages': 6
}


def connect_database():
    """Connect to the database"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        logger.info(f"✓ Connected to database at {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        return connection
    except Error as e:
        logger.error(f"✗ Database connection failed: {e}")
        sys.exit(1)


def test_table_counts(cursor):
    """Validate record counts in all tables"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Validating Table Record Counts")
    logger.info("="*60)

    all_passed = True

    for table, expected_count in EXPECTED_COUNTS.items():
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        actual_count = cursor.fetchone()[0]

        if actual_count == expected_count:
            logger.info(f"✓ {table}: {actual_count} records (expected {expected_count})")
        elif actual_count > expected_count:
            logger.warning(f"⚠ {table}: {actual_count} records (expected {expected_count}) - Additional data loaded")
        else:
            logger.error(f"✗ {table}: {actual_count} records (expected {expected_count}) - MISSING DATA")
            all_passed = False

    return all_passed


def test_foreign_key_integrity(cursor):
    """Validate foreign key integrity"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Validating Foreign Key Integrity")
    logger.info("="*60)

    all_passed = True
    tests = []

    # Test CustomerPurchaseOrders -> Customers
    tests.append((
        "CustomerPurchaseOrders -> Customers",
        """
        SELECT COUNT(*) FROM CustomerPurchaseOrders cpo
        LEFT JOIN Customers c ON cpo.CustomerID = c.CustomerID
        WHERE cpo.CustomerID IS NOT NULL AND c.CustomerID IS NULL
        """
    ))

    # Test CustomerPOLineItems -> CustomerPurchaseOrders
    tests.append((
        "CustomerPOLineItems -> CustomerPurchaseOrders",
        """
        SELECT COUNT(*) FROM CustomerPOLineItems li
        LEFT JOIN CustomerPurchaseOrders cpo ON li.PO_ID = cpo.PO_ID
        WHERE cpo.PO_ID IS NULL
        """
    ))

    # Test WorkOrders -> Customers
    tests.append((
        "WorkOrders -> Customers",
        """
        SELECT COUNT(*) FROM WorkOrders wo
        LEFT JOIN Customers c ON wo.CustomerID = c.CustomerID
        WHERE c.CustomerID IS NULL
        """
    ))

    # Test WorkOrders -> Parts
    tests.append((
        "WorkOrders -> Parts",
        """
        SELECT COUNT(*) FROM WorkOrders wo
        LEFT JOIN Parts p ON wo.PartID = p.PartID
        WHERE p.PartID IS NULL
        """
    ))

    # Test BOM -> WorkOrders
    tests.append((
        "BOM -> WorkOrders",
        """
        SELECT COUNT(*) FROM BOM b
        LEFT JOIN WorkOrders wo ON b.WorkOrderID = wo.WorkOrderID
        WHERE wo.WorkOrderID IS NULL
        """
    ))

    # Test BOMProcesses -> BOM
    tests.append((
        "BOMProcesses -> BOM",
        """
        SELECT COUNT(*) FROM BOMProcesses bp
        LEFT JOIN BOM b ON bp.BOMID = b.BOMID
        WHERE b.BOMID IS NULL
        """
    ))

    # Test BOMProcesses -> Vendors (nullable, so check only where VendorID is set)
    tests.append((
        "BOMProcesses -> Vendors (where set)",
        """
        SELECT COUNT(*) FROM BOMProcesses bp
        LEFT JOIN Vendors v ON bp.VendorID = v.VendorID
        WHERE bp.VendorID IS NOT NULL AND v.VendorID IS NULL
        """
    ))

    # Test PurchaseOrdersLog -> WorkOrders
    tests.append((
        "PurchaseOrdersLog -> WorkOrders",
        """
        SELECT COUNT(*) FROM PurchaseOrdersLog pol
        LEFT JOIN WorkOrders wo ON pol.WorkOrderID = wo.WorkOrderID
        WHERE wo.WorkOrderID IS NULL
        """
    ))

    # Test PurchaseOrdersLog -> Vendors
    tests.append((
        "PurchaseOrdersLog -> Vendors",
        """
        SELECT COUNT(*) FROM PurchaseOrdersLog pol
        LEFT JOIN Vendors v ON pol.VendorID = v.VendorID
        WHERE v.VendorID IS NULL
        """
    ))

    # Test CertificatesLog -> WorkOrders
    tests.append((
        "CertificatesLog -> WorkOrders",
        """
        SELECT COUNT(*) FROM CertificatesLog cl
        LEFT JOIN WorkOrders wo ON cl.WorkOrderID = wo.WorkOrderID
        WHERE wo.WorkOrderID IS NULL
        """
    ))

    # Test WorkOrderStatusHistory -> WorkOrders
    tests.append((
        "WorkOrderStatusHistory -> WorkOrders",
        """
        SELECT COUNT(*) FROM WorkOrderStatusHistory wosh
        LEFT JOIN WorkOrders wo ON wosh.WorkOrderID = wo.WorkOrderID
        WHERE wo.WorkOrderID IS NULL
        """
    ))

    # Test ProductionStages -> WorkOrders
    tests.append((
        "ProductionStages -> WorkOrders",
        """
        SELECT COUNT(*) FROM ProductionStages ps
        LEFT JOIN WorkOrders wo ON ps.WorkOrderID = wo.WorkOrderID
        WHERE wo.WorkOrderID IS NULL
        """
    ))

    # Run all tests
    for test_name, query in tests:
        cursor.execute(query)
        orphaned = cursor.fetchone()[0]

        if orphaned == 0:
            logger.info(f"✓ {test_name}: No orphaned records")
        else:
            logger.error(f"✗ {test_name}: {orphaned} orphaned records found")
            all_passed = False

    return all_passed


def test_specific_data(cursor):
    """Test specific expected data exists"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Validating Specific Data Entries")
    logger.info("="*60)

    all_passed = True

    # Check Shibaura customer exists
    cursor.execute("SELECT CustomerID FROM Customers WHERE CustomerName = 'Shibaura'")
    if cursor.fetchone():
        logger.info("✓ Shibaura customer exists")
    else:
        logger.error("✗ Shibaura customer not found")
        all_passed = False

    # Check Navy customer exists
    cursor.execute("SELECT CustomerID FROM Customers WHERE CustomerName = 'US Navy'")
    if cursor.fetchone():
        logger.info("✓ US Navy customer exists")
    else:
        logger.error("✗ US Navy customer not found")
        all_passed = False

    # Check key vendors exist
    for vendor in ['Metal Supermarkets', 'Quality Plating Services', 'Advanced Heat Treat']:
        cursor.execute("SELECT VendorID FROM Vendors WHERE VendorName = %s", (vendor,))
        if cursor.fetchone():
            logger.info(f"✓ Vendor '{vendor}' exists")
        else:
            logger.error(f"✗ Vendor '{vendor}' not found")
            all_passed = False

    # Check sample parts exist
    for part_num in ['438S5707', 'Y132076', 'N054085']:
        cursor.execute("SELECT PartID FROM Parts WHERE PartNumber = %s", (part_num,))
        if cursor.fetchone():
            logger.info(f"✓ Part {part_num} exists")
        else:
            logger.error(f"✗ Part {part_num} not found")
            all_passed = False

    # Check PO NAVY-2025-001 exists
    cursor.execute("SELECT PO_ID FROM CustomerPurchaseOrders WHERE PO_Number = 'NAVY-2025-001'")
    if cursor.fetchone():
        logger.info("✓ Active Navy PO exists")
    else:
        logger.error("✗ Active Navy PO not found")
        all_passed = False

    return all_passed


def test_data_relationships(cursor):
    """Test that data relationships make sense"""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Validating Data Relationships")
    logger.info("="*60)

    all_passed = True

    # Check that each work order has a BOM
    cursor.execute("""
        SELECT wo.WorkOrderID, p.PartNumber
        FROM WorkOrders wo
        JOIN Parts p ON wo.PartID = p.PartID
        LEFT JOIN BOM b ON wo.WorkOrderID = b.WorkOrderID
        WHERE b.BOMID IS NULL
    """)
    work_orders_without_bom = cursor.fetchall()

    if not work_orders_without_bom:
        logger.info("✓ All work orders have BOMs")
    else:
        logger.warning(f"⚠ {len(work_orders_without_bom)} work orders without BOMs (may be intentional)")
        for wo_id, part_num in work_orders_without_bom:
            logger.warning(f"  - WO {wo_id} (Part: {part_num})")

    # Check that each BOM has at least one process
    cursor.execute("""
        SELECT b.BOMID, wo.WorkOrderID
        FROM BOM b
        JOIN WorkOrders wo ON b.WorkOrderID = wo.WorkOrderID
        LEFT JOIN BOMProcesses bp ON b.BOMID = bp.BOMID
        GROUP BY b.BOMID, wo.WorkOrderID
        HAVING COUNT(bp.ProcessID) = 0
    """)
    boms_without_processes = cursor.fetchall()

    if not boms_without_processes:
        logger.info("✓ All BOMs have at least one process")
    else:
        logger.error(f"✗ {len(boms_without_processes)} BOMs without processes")
        all_passed = False

    # Check that active work orders have status history
    cursor.execute("""
        SELECT wo.WorkOrderID, p.PartNumber, wo.Status
        FROM WorkOrders wo
        JOIN Parts p ON wo.PartID = p.PartID
        LEFT JOIN WorkOrderStatusHistory wosh ON wo.WorkOrderID = wosh.WorkOrderID
        WHERE wosh.StatusHistoryID IS NULL
    """)
    wo_without_history = cursor.fetchall()

    if not wo_without_history:
        logger.info("✓ All work orders have status history")
    else:
        logger.warning(f"⚠ {len(wo_without_history)} work orders without status history")
        for wo_id, part_num, status in wo_without_history:
            logger.warning(f"  - WO {wo_id} (Part: {part_num}, Status: {status})")

    return all_passed


def test_views(cursor):
    """Test that views work correctly"""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: Validating Views")
    logger.info("="*60)

    all_passed = True

    # Test vw_WorkOrderSummary
    try:
        cursor.execute("SELECT COUNT(*) FROM vw_WorkOrderSummary")
        count = cursor.fetchone()[0]
        logger.info(f"✓ vw_WorkOrderSummary: {count} records")
    except Error as e:
        logger.error(f"✗ vw_WorkOrderSummary failed: {e}")
        all_passed = False

    # Test vw_BOMDetails
    try:
        cursor.execute("SELECT COUNT(*) FROM vw_BOMDetails")
        count = cursor.fetchone()[0]
        logger.info(f"✓ vw_BOMDetails: {count} records")
    except Error as e:
        logger.error(f"✗ vw_BOMDetails failed: {e}")
        all_passed = False

    # Test vw_CustomerPODetails
    try:
        cursor.execute("SELECT COUNT(*) FROM vw_CustomerPODetails")
        count = cursor.fetchone()[0]
        logger.info(f"✓ vw_CustomerPODetails: {count} records")
    except Error as e:
        logger.error(f"✗ vw_CustomerPODetails failed: {e}")
        all_passed = False

    return all_passed


def generate_summary_report(cursor):
    """Generate a summary report of the database"""
    logger.info("\n" + "="*60)
    logger.info("DATABASE SUMMARY REPORT")
    logger.info("="*60)

    # Active work orders
    cursor.execute("""
        SELECT
            wo.WorkOrderID,
            c.CustomerName,
            p.PartNumber,
            wo.QuantityOrdered,
            wo.Status,
            wo.DueDate
        FROM WorkOrders wo
        JOIN Customers c ON wo.CustomerID = c.CustomerID
        JOIN Parts p ON wo.PartID = p.PartID
        WHERE wo.Status NOT IN ('Completed', 'Shipped')
        ORDER BY wo.DueDate
    """)
    active_wos = cursor.fetchall()

    logger.info(f"\nActive Work Orders: {len(active_wos)}")
    for wo_id, customer, part, qty, status, due_date in active_wos:
        logger.info(f"  WO-{wo_id}: {customer} | {part} | Qty: {qty} | {status} | Due: {due_date}")

    # Total BOM process costs
    cursor.execute("""
        SELECT
            wo.WorkOrderID,
            p.PartNumber,
            SUM(bp.EstimatedCost * wo.QuantityOrdered) as TotalEstimated
        FROM WorkOrders wo
        JOIN Parts p ON wo.PartID = p.PartID
        JOIN BOM b ON wo.WorkOrderID = b.WorkOrderID
        JOIN BOMProcesses bp ON b.BOMID = bp.BOMID
        GROUP BY wo.WorkOrderID, p.PartNumber
    """)
    costs = cursor.fetchall()

    logger.info(f"\nEstimated Work Order Costs:")
    total_cost = 0
    for wo_id, part, cost in costs:
        logger.info(f"  WO-{wo_id} ({part}): ${cost:,.2f}")
        total_cost += cost
    logger.info(f"  Total Estimated Cost: ${total_cost:,.2f}")


def main():
    """Main validation execution"""
    connection = None
    all_tests_passed = True

    try:
        logger.info("="*60)
        logger.info("AMC MRP BASE DATA VALIDATION")
        logger.info("="*60)

        # Connect to database
        connection = connect_database()
        cursor = connection.cursor()

        # Run all tests
        all_tests_passed &= test_table_counts(cursor)
        all_tests_passed &= test_foreign_key_integrity(cursor)
        all_tests_passed &= test_specific_data(cursor)
        all_tests_passed &= test_data_relationships(cursor)
        all_tests_passed &= test_views(cursor)

        # Generate summary report
        generate_summary_report(cursor)

        # Final result
        logger.info("\n" + "="*60)
        if all_tests_passed:
            logger.info("✓ ALL VALIDATION TESTS PASSED")
            logger.info("="*60)
            logger.info("Database is ready for use!")
            sys.exit(0)
        else:
            logger.error("✗ SOME VALIDATION TESTS FAILED")
            logger.info("="*60)
            logger.error("Please review the errors above")
            sys.exit(1)

    except Error as e:
        logger.error(f"Validation failed with error: {e}")
        sys.exit(1)

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


if __name__ == "__main__":
    main()
