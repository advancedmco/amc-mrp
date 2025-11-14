"""
Import Coordinator - Orchestrates data import from multiple sources.

Handles coordinated imports ensuring proper order and dependencies.
"""

import logging
from typing import Any, Dict, List, Optional
from .vendor_importer import VendorImporter
from .customer_importer import CustomerImporter
from .product_importer import ProductImporter
from .invoice_importer import InvoiceImporter


class ImportCoordinator:
    """Coordinates import operations across multiple entity types."""

    def __init__(self, db_config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize the coordinator.

        Args:
            db_config: Database configuration
            logger: Optional logger instance
        """
        self.db_config = db_config
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # Initialize importers
        self.vendor_importer = VendorImporter(db_config, logger)
        self.customer_importer = CustomerImporter(db_config, logger)
        self.product_importer = ProductImporter(db_config, logger)
        self.invoice_importer = InvoiceImporter(db_config, logger)

    def import_all_from_quickbooks(self, qb_data: Dict[str, List[Dict[str, Any]]],
                                  **options) -> Dict[str, Dict[str, int]]:
        """
        Import all data from QuickBooks in the proper order.

        Order of operations:
        1. Vendors (independent)
        2. Customers (independent)
        3. Products/Parts (independent)
        4. Invoices (depends on customers and parts)

        Args:
            qb_data: Dictionary with keys: 'vendors', 'customers', 'items', 'invoices'
            options: Import options to pass to individual importers

        Returns:
            Dictionary of statistics for each entity type
        """
        results = {}

        self.logger.info("Starting coordinated QuickBooks data import")

        # Phase 1: Import vendors
        if 'vendors' in qb_data and qb_data['vendors']:
            self.logger.info(f"Importing {len(qb_data['vendors'])} vendors...")
            results['vendors'] = self.vendor_importer.import_data(
                qb_data['vendors'],
                **options.get('vendors', {})
            )
        else:
            self.logger.info("No vendor data to import")
            results['vendors'] = {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

        # Phase 2: Import customers
        if 'customers' in qb_data and qb_data['customers']:
            self.logger.info(f"Importing {len(qb_data['customers'])} customers...")
            results['customers'] = self.customer_importer.import_data(
                qb_data['customers'],
                **options.get('customers', {})
            )
        else:
            self.logger.info("No customer data to import")
            results['customers'] = {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

        # Phase 3: Import products/parts
        if 'items' in qb_data and qb_data['items']:
            self.logger.info(f"Importing {len(qb_data['items'])} items/products...")
            results['items'] = self.product_importer.import_data(
                qb_data['items'],
                **options.get('items', {})
            )
        else:
            self.logger.info("No item/product data to import")
            results['items'] = {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

        # Phase 4: Import invoices (which create/update work orders)
        if 'invoices' in qb_data and qb_data['invoices']:
            self.logger.info(f"Importing {len(qb_data['invoices'])} invoices...")
            results['invoices'] = self.invoice_importer.import_data(
                qb_data['invoices'],
                **options.get('invoices', {})
            )
        else:
            self.logger.info("No invoice data to import")
            results['invoices'] = {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

        self.logger.info("QuickBooks data import completed")
        self._log_summary(results)

        return results

    def import_vendors(self, data: List[Dict[str, Any]], **options) -> Dict[str, int]:
        """Import vendors only."""
        self.logger.info(f"Importing {len(data)} vendors...")
        return self.vendor_importer.import_data(data, **options)

    def import_customers(self, data: List[Dict[str, Any]], **options) -> Dict[str, int]:
        """Import customers only."""
        self.logger.info(f"Importing {len(data)} customers...")
        return self.customer_importer.import_data(data, **options)

    def import_products(self, data: List[Dict[str, Any]], **options) -> Dict[str, int]:
        """Import products/parts only."""
        self.logger.info(f"Importing {len(data)} products...")
        return self.product_importer.import_data(data, **options)

    def import_invoices(self, data: List[Dict[str, Any]], **options) -> Dict[str, int]:
        """Import invoices only."""
        self.logger.info(f"Importing {len(data)} invoices...")
        return self.invoice_importer.import_data(data, **options)

    def import_from_csv_files(self, file_paths: Dict[str, str], **options) -> Dict[str, Dict[str, int]]:
        """
        Import data from CSV files.

        Args:
            file_paths: Dictionary mapping entity type to CSV file path
                       e.g., {'vendors': '/path/to/vendors.csv'}
            options: Import options

        Returns:
            Dictionary of statistics for each entity type
        """
        import csv

        results = {}

        # Import vendors
        if 'vendors' in file_paths:
            self.logger.info(f"Loading vendors from {file_paths['vendors']}")
            with open(file_paths['vendors'], 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                vendors = list(reader)
                results['vendors'] = self.import_vendors(vendors, **options.get('vendors', {}))

        # Import customers
        if 'customers' in file_paths:
            self.logger.info(f"Loading customers from {file_paths['customers']}")
            with open(file_paths['customers'], 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                customers = list(reader)
                results['customers'] = self.import_customers(customers, **options.get('customers', {}))

        # Import products
        if 'products' in file_paths:
            self.logger.info(f"Loading products from {file_paths['products']}")
            with open(file_paths['products'], 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                products = list(reader)
                results['products'] = self.import_products(products, **options.get('products', {}))

        # Import invoices
        if 'invoices' in file_paths:
            self.logger.info(f"Loading invoices from {file_paths['invoices']}")
            with open(file_paths['invoices'], 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                invoices = list(reader)
                results['invoices'] = self.import_invoices(invoices, **options.get('invoices', {}))

        self._log_summary(results)
        return results

    def _log_summary(self, results: Dict[str, Dict[str, int]]):
        """Log summary of all import operations."""
        self.logger.info("=" * 60)
        self.logger.info("Import Summary")
        self.logger.info("=" * 60)

        total_inserted = 0
        total_updated = 0
        total_skipped = 0
        total_errors = 0

        for entity_type, stats in results.items():
            self.logger.info(f"{entity_type.upper()}:")
            self.logger.info(f"  Inserted: {stats['inserted']}")
            self.logger.info(f"  Updated:  {stats['updated']}")
            self.logger.info(f"  Skipped:  {stats['skipped']}")
            self.logger.info(f"  Errors:   {stats['errors']}")

            total_inserted += stats['inserted']
            total_updated += stats['updated']
            total_skipped += stats['skipped']
            total_errors += stats['errors']

        self.logger.info("-" * 60)
        self.logger.info(f"TOTAL:")
        self.logger.info(f"  Inserted: {total_inserted}")
        self.logger.info(f"  Updated:  {total_updated}")
        self.logger.info(f"  Skipped:  {total_skipped}")
        self.logger.info(f"  Errors:   {total_errors}")
        self.logger.info("=" * 60)
