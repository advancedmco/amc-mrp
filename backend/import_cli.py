#!/usr/bin/env python3
"""
CLI tool for importing data into AMC-MRP system.

Usage:
    python import_cli.py quickbooks              # Import from QuickBooks cache
    python import_cli.py csv --vendors vendors.csv --customers customers.csv
    python import_cli.py vendors vendor_data.json
    python import_cli.py customers customer_data.json
    python import_cli.py products products.csv
    python import_cli.py invoices invoices.json
"""

import os
import sys
import json
import csv
import logging
import argparse
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from importers import ImportCoordinator


# Database configuration from environment
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'root'),
    'database': os.getenv('DB_NAME', 'mrp_db')
}


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def load_json_file(file_path: str) -> List[Dict[str, Any]]:
    """Load data from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # Handle both list and dict formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Assume dict has entity names as keys
            for key in ['data', 'records', 'items']:
                if key in data:
                    return data[key]
            # Return first list value found
            for value in data.values():
                if isinstance(value, list):
                    return value
        return []


def load_csv_file(file_path: str) -> List[Dict[str, Any]]:
    """Load data from CSV file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_file(file_path: str) -> List[Dict[str, Any]]:
    """Load data from file (auto-detect format)."""
    if file_path.endswith('.json'):
        return load_json_file(file_path)
    elif file_path.endswith('.csv'):
        return load_csv_file(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path}")


def get_quickbooks_cached_data() -> Dict[str, List[Dict[str, Any]]]:
    """Get data from QuickBooks cache via backend API."""
    import requests

    backend_url = os.getenv('BACKEND_URL', 'http://localhost:5002')

    try:
        # Fetch all data from backend
        qb_data = {}

        for entity in ['customers', 'vendors', 'items', 'invoices']:
            response = requests.get(f"{backend_url}/api/data/{entity}", timeout=30)
            if response.status_code == 200:
                data = response.json()
                qb_data[entity] = data.get(entity, [])
            else:
                logging.warning(f"Could not fetch {entity} from backend: {response.status_code}")
                qb_data[entity] = []

        return qb_data

    except Exception as e:
        logging.error(f"Error fetching QuickBooks data: {e}")
        return {}


def import_quickbooks(args):
    """Import data from QuickBooks."""
    print("Fetching data from QuickBooks cache...")
    qb_data = get_quickbooks_cached_data()

    if not any(qb_data.values()):
        print("No data found in QuickBooks cache. Make sure backend is running and authenticated.")
        sys.exit(1)

    print(f"Found:")
    print(f"  - {len(qb_data.get('customers', []))} customers")
    print(f"  - {len(qb_data.get('vendors', []))} vendors")
    print(f"  - {len(qb_data.get('items', []))} items/products")
    print(f"  - {len(qb_data.get('invoices', []))} invoices")
    print()

    coordinator = ImportCoordinator(DB_CONFIG)

    options = {
        'vendors': {'update_existing': not args.skip_updates},
        'customers': {'update_existing': not args.skip_updates},
        'items': {
            'update_existing': not args.skip_updates,
            'filter_inventory': args.inventory_only,
            'filter_non_inventory': args.non_inventory_only
        },
        'invoices': {
            'mark_as_complete': args.mark_complete,
            'set_payment_received': args.payment_received,
            'create_missing_customers': True,
            'create_missing_parts': True
        }
    }

    results = coordinator.import_all_from_quickbooks(qb_data, **options)

    print("\nImport completed!")
    return 0


def import_csv_files(args):
    """Import data from CSV files."""
    coordinator = ImportCoordinator(DB_CONFIG)

    file_paths = {}
    if args.vendors:
        file_paths['vendors'] = args.vendors
    if args.customers:
        file_paths['customers'] = args.customers
    if args.products:
        file_paths['products'] = args.products
    if args.invoices:
        file_paths['invoices'] = args.invoices

    if not file_paths:
        print("Error: No CSV files specified")
        sys.exit(1)

    options = {
        'vendors': {'update_existing': not args.skip_updates},
        'customers': {'update_existing': not args.skip_updates},
        'products': {'update_existing': not args.skip_updates},
        'invoices': {
            'mark_as_complete': args.mark_complete,
            'set_payment_received': args.payment_received
        }
    }

    results = coordinator.import_from_csv_files(file_paths, **options)

    print("\nImport completed!")
    return 0


def import_entity(args, entity_type: str):
    """Import a specific entity type."""
    data = load_file(args.file)

    if not data:
        print(f"No data found in {args.file}")
        sys.exit(1)

    print(f"Loaded {len(data)} {entity_type} records from {args.file}")

    coordinator = ImportCoordinator(DB_CONFIG)

    options = {'update_existing': not args.skip_updates}

    if entity_type == 'vendors':
        results = coordinator.import_vendors(data, **options)
    elif entity_type == 'customers':
        results = coordinator.import_customers(data, **options)
    elif entity_type == 'products':
        results = coordinator.import_products(data, **options)
    elif entity_type == 'invoices':
        options['mark_as_complete'] = args.mark_complete
        options['set_payment_received'] = args.payment_received
        results = coordinator.import_invoices(data, **options)

    print("\nImport completed!")
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Import data into AMC-MRP system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import from QuickBooks cache
  python import_cli.py quickbooks

  # Import from CSV files
  python import_cli.py csv --vendors vendors.csv --customers customers.csv

  # Import specific entity from file
  python import_cli.py vendors vendor_data.json
  python import_cli.py customers customers.csv
  python import_cli.py products products.json
  python import_cli.py invoices invoices.json
        """
    )

    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--skip-updates', action='store_true',
                       help='Skip updating existing records')

    subparsers = parser.add_subparsers(dest='command', help='Import command')

    # QuickBooks import
    qb_parser = subparsers.add_parser('quickbooks', help='Import from QuickBooks cache')
    qb_parser.add_argument('--inventory-only', action='store_true',
                          help='Import only inventory items')
    qb_parser.add_argument('--non-inventory-only', action='store_true',
                          help='Import only non-inventory items')
    qb_parser.add_argument('--no-mark-complete', dest='mark_complete',
                          action='store_false', default=True,
                          help='Do not mark work orders as complete')
    qb_parser.add_argument('--no-payment-received', dest='payment_received',
                          action='store_false', default=True,
                          help='Do not set payment status to received')

    # CSV import
    csv_parser = subparsers.add_parser('csv', help='Import from CSV files')
    csv_parser.add_argument('--vendors', help='Vendors CSV file')
    csv_parser.add_argument('--customers', help='Customers CSV file')
    csv_parser.add_argument('--products', help='Products CSV file')
    csv_parser.add_argument('--invoices', help='Invoices CSV file')
    csv_parser.add_argument('--no-mark-complete', dest='mark_complete',
                           action='store_false', default=True,
                           help='Do not mark work orders as complete')
    csv_parser.add_argument('--no-payment-received', dest='payment_received',
                           action='store_false', default=True,
                           help='Do not set payment status to received')

    # Individual entity imports
    for entity in ['vendors', 'customers', 'products', 'invoices']:
        entity_parser = subparsers.add_parser(entity, help=f'Import {entity} from file')
        entity_parser.add_argument('file', help=f'{entity.capitalize()} data file (JSON or CSV)')

        if entity == 'invoices':
            entity_parser.add_argument('--no-mark-complete', dest='mark_complete',
                                      action='store_false', default=True,
                                      help='Do not mark work orders as complete')
            entity_parser.add_argument('--no-payment-received', dest='payment_received',
                                      action='store_false', default=True,
                                      help='Do not set payment status to received')

    args = parser.parse_args()

    setup_logging(args.verbose)

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == 'quickbooks':
            return import_quickbooks(args)
        elif args.command == 'csv':
            return import_csv_files(args)
        elif args.command in ['vendors', 'customers', 'products', 'invoices']:
            return import_entity(args, args.command)
        else:
            print(f"Unknown command: {args.command}")
            return 1

    except Exception as e:
        logging.error(f"Import failed: {e}", exc_info=args.verbose)
        return 1


if __name__ == '__main__':
    sys.exit(main())
