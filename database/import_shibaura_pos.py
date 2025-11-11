#!/usr/bin/env python3
"""
Shibaura Customer PO Import Script
Imports customer purchase orders from Shibaura_POs.csv into the database

Author: Advanced Machine Co. MRP System
Created: November 2025
"""

import os
import sys
import csv
import logging
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict
import mysql.connector
from mysql.connector import Error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ShibauraImport')

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'amcmrp'),
    'user': os.getenv('DB_USER', 'amc'),
    'password': os.getenv('DB_PASSWORD', 'Workbench.lavender.chrome'),
    'port': int(os.getenv('DB_PORT', '3306'))
}

# CSV file path
CSV_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'DevAssets', 'Shibaura_POs.csv')


def parse_date(date_str: str) -> str:
    """
    Parse date from CSV format (M/D/YYYY) to MySQL format (YYYY-MM-DD)

    Args:
        date_str: Date string from CSV

    Returns:
        Date string in MySQL format
    """
    try:
        # Handle various date formats
        date_obj = datetime.strptime(date_str, '%m/%d/%Y')
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        logger.warning(f"Could not parse date: {date_str}, using NULL")
        return None


def parse_decimal(value_str: str) -> float:
    """
    Parse decimal values from CSV

    Args:
        value_str: Decimal string from CSV

    Returns:
        Float value
    """
    try:
        # Remove any whitespace and convert to float
        return float(value_str.strip())
    except (ValueError, AttributeError):
        return 0.0


def parse_csv_file(csv_path: str) -> Dict[str, Dict]:
    """
    Parse CSV file and organize data by PO number

    Args:
        csv_path: Path to CSV file

    Returns:
        Dictionary of PO data organized by PO number
    """
    pos = defaultdict(lambda: {'line_items': []})

    logger.info(f"Reading CSV file: {csv_path}")

    with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
        # Skip BOM if present
        reader = csv.DictReader(csvfile)

        for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header
            try:
                po_number = row['PO'].strip()

                # Initialize PO header data if this is the first line item for this PO
                if not pos[po_number].get('po_number'):
                    pos[po_number]['po_number'] = po_number
                    pos[po_number]['order_date'] = parse_date(row['Order Date'])
                    pos[po_number]['total_value'] = parse_decimal(row[' Grand Total '])

                # Add line item
                line_item = {
                    'line_number': int(row['Ln']),
                    'part_number': row['Part'].strip(),
                    'description': row['Description'].strip(),
                    'quantity': int(row['Qty']),
                    'unit_price': parse_decimal(row[' Unit Price ']),
                    'due_date': parse_date(row['Due Date'])
                }

                pos[po_number]['line_items'].append(line_item)

            except Exception as e:
                logger.error(f"Error parsing row {row_num}: {e}")
                logger.error(f"Row data: {row}")
                continue

    logger.info(f"Parsed {len(pos)} unique POs with total line items")
    return pos


def get_or_create_shibaura_customer(cursor) -> int:
    """
    Get or create Shibaura customer in the database

    Args:
        cursor: Database cursor

    Returns:
        Customer ID
    """
    # Check if Shibaura customer exists
    cursor.execute("SELECT CustomerID FROM Customers WHERE CustomerName = 'Shibaura'")
    result = cursor.fetchone()

    if result:
        logger.info(f"Found existing Shibaura customer with ID: {result[0]}")
        return result[0]

    # Create Shibaura customer
    cursor.execute(
        "INSERT INTO Customers (CustomerName) VALUES ('Shibaura')"
    )
    customer_id = cursor.lastrowid
    logger.info(f"Created Shibaura customer with ID: {customer_id}")
    return customer_id


def import_pos_to_database(pos_data: Dict[str, Dict]) -> Tuple[int, int]:
    """
    Import PO data into database

    Args:
        pos_data: Dictionary of PO data

    Returns:
        Tuple of (number of POs imported, number of line items imported)
    """
    connection = None
    pos_imported = 0
    line_items_imported = 0

    try:
        # Connect to database
        logger.info("Connecting to database...")
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Get or create Shibaura customer
        customer_id = get_or_create_shibaura_customer(cursor)

        # Import each PO
        for po_number, po_data in sorted(pos_data.items()):
            try:
                # Check if PO already exists
                cursor.execute(
                    "SELECT PO_ID FROM CustomerPurchaseOrders WHERE PO_Number = %s",
                    (po_number,)
                )
                existing_po = cursor.fetchone()

                if existing_po:
                    logger.info(f"PO {po_number} already exists, skipping...")
                    continue

                # Insert PO header
                cursor.execute(
                    """
                    INSERT INTO CustomerPurchaseOrders
                    (PO_Number, CustomerID, Order_Date, Total_Value, Status)
                    VALUES (%s, %s, %s, %s, 'Completed')
                    """,
                    (
                        po_number,
                        customer_id,
                        po_data['order_date'],
                        po_data['total_value']
                    )
                )

                po_id = cursor.lastrowid
                pos_imported += 1
                logger.info(f"Imported PO {po_number} (ID: {po_id})")

                # Insert line items
                for line_item in po_data['line_items']:
                    cursor.execute(
                        """
                        INSERT INTO CustomerPOLineItems
                        (PO_ID, Line_Number, Part_Number, Description, Quantity,
                         Unit_Price, Due_Date, Status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Completed')
                        """,
                        (
                            po_id,
                            line_item['line_number'],
                            line_item['part_number'],
                            line_item['description'],
                            line_item['quantity'],
                            line_item['unit_price'],
                            line_item['due_date']
                        )
                    )
                    line_items_imported += 1

                logger.debug(f"  Imported {len(po_data['line_items'])} line items for PO {po_number}")

            except Error as e:
                logger.error(f"Error importing PO {po_number}: {e}")
                connection.rollback()
                continue

        # Commit all changes
        connection.commit()
        logger.info(f"Successfully imported {pos_imported} POs with {line_items_imported} line items")

        return pos_imported, line_items_imported

    except Error as e:
        logger.error(f"Database error: {e}")
        if connection:
            connection.rollback()
        raise

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            logger.info("Database connection closed")


def main():
    """Main execution function"""
    try:
        logger.info("Starting Shibaura PO import...")

        # Check if CSV file exists
        if not os.path.exists(CSV_FILE_PATH):
            logger.error(f"CSV file not found: {CSV_FILE_PATH}")
            sys.exit(1)

        # Parse CSV file
        pos_data = parse_csv_file(CSV_FILE_PATH)

        # Import to database
        pos_imported, line_items_imported = import_pos_to_database(pos_data)

        logger.info("="*60)
        logger.info(f"Import completed successfully!")
        logger.info(f"POs imported: {pos_imported}")
        logger.info(f"Line items imported: {line_items_imported}")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
