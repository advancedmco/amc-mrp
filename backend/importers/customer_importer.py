"""
Customer data importer.

Handles importing customer data with display names from various sources.
Supports both creation and updates of customer records.
"""

from typing import Any, Dict, List, Optional, Tuple
from .base_importer import BaseImporter


class CustomerImporter(BaseImporter):
    """Imports customer data into the Customers table."""

    def validate_record(self, record: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a customer record.

        Args:
            record: Customer data record

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Customer name is required
        if not record.get('CustomerName') and not record.get('DisplayName'):
            return False, "Customer name is required"

        return True, None

    def normalize_customer_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a customer record from various source formats.

        Args:
            record: Raw customer data

        Returns:
            Normalized customer record
        """
        normalized = {}

        # Handle QuickBooks format
        if 'DisplayName' in record or 'Id' in record:
            # Extract customer name - use DisplayName as it's the primary identifier
            customer_name = record.get('DisplayName') or record.get('CompanyName')

            # If no display name or company name, build from person name
            if not customer_name and record.get('GivenName'):
                given = record.get('GivenName', '')
                middle = record.get('MiddleName', '')
                family = record.get('FamilyName', '')
                name_parts = [given, middle, family]
                customer_name = ' '.join(filter(None, name_parts))

            # If still no name, use FullyQualifiedName
            if not customer_name:
                customer_name = record.get('FullyQualifiedName')

            normalized['CustomerName'] = self.normalizer.normalize_string(
                customer_name, add_quotes=False
            )

            # QuickBooks ID
            if 'Id' in record:
                normalized['QuickBooksID'] = record['Id']

        else:
            # Handle simple/CSV format
            customer_name = (
                record.get('CustomerName') or
                record.get('customer_name') or
                record.get('name') or
                record.get('display_name') or
                record.get('DisplayName')
            )

            normalized['CustomerName'] = self.normalizer.normalize_string(
                customer_name, add_quotes=False
            )

            # QuickBooks ID if provided
            qb_id = record.get('QuickBooksID') or record.get('qb_id') or record.get('Id')
            if qb_id:
                normalized['QuickBooksID'] = qb_id

        return normalized

    def import_data(self, data: List[Dict[str, Any]], **options) -> Dict[str, int]:
        """
        Import customer data into the database.

        Args:
            data: List of customer records
            options: Additional options
                - update_existing: Whether to update existing records (default: True)
                - match_by_qb_id: Whether to match by QuickBooks ID (default: True)
                - match_by_name: Whether to match by customer name (default: True)

        Returns:
            Statistics dictionary
        """
        self.reset_stats()
        update_existing = options.get('update_existing', True)
        match_by_qb_id = options.get('match_by_qb_id', True)
        match_by_name = options.get('match_by_name', True)

        for record in data:
            try:
                # Normalize the record
                normalized = self.normalize_customer_record(record)

                if not normalized.get('CustomerName'):
                    self.logger.warning(f"Skipping customer with no name: {record}")
                    self.stats['skipped'] += 1
                    continue

                # Validate the record
                is_valid, error_msg = self.validate_record(normalized)
                if not is_valid:
                    self.logger.warning(f"Invalid customer record: {error_msg} - {normalized}")
                    self.stats['errors'] += 1
                    continue

                # Check if customer exists
                customer_id = None

                # Try matching by QuickBooks ID first
                if match_by_qb_id and normalized.get('QuickBooksID'):
                    query = "SELECT CustomerID FROM Customers WHERE QuickBooksID = %s"
                    result = self.execute_query(query, (normalized['QuickBooksID'],))
                    if result:
                        customer_id = result[0]['CustomerID']

                # Try matching by name if not found
                if not customer_id and match_by_name:
                    query = "SELECT CustomerID FROM Customers WHERE CustomerName = %s"
                    result = self.execute_query(query, (normalized['CustomerName'],))
                    if result:
                        customer_id = result[0]['CustomerID']

                if customer_id and update_existing:
                    # Update existing customer
                    self._update_customer(customer_id, normalized)
                    self.stats['updated'] += 1
                elif customer_id:
                    # Skip existing customer
                    self.stats['skipped'] += 1
                else:
                    # Insert new customer
                    self._insert_customer(normalized)
                    self.stats['inserted'] += 1

            except Exception as e:
                self.logger.error(f"Error importing customer: {e} - Record: {record}")
                self.stats['errors'] += 1

        self.log_stats()
        return self.get_stats()

    def _insert_customer(self, customer_data: Dict[str, Any]) -> Optional[int]:
        """Insert a new customer record."""
        fields = []
        values = []

        for field in ['CustomerName', 'QuickBooksID']:
            if customer_data.get(field) is not None:
                fields.append(field)
                values.append(customer_data[field])

        if not fields:
            return None

        query = f"""
            INSERT INTO Customers ({', '.join(fields)})
            VALUES ({', '.join(['%s'] * len(values))})
        """

        return self.execute_insert(query, tuple(values))

    def _update_customer(self, customer_id: int, customer_data: Dict[str, Any]) -> bool:
        """Update an existing customer record."""
        update_fields = []
        values = []

        for field in ['CustomerName', 'QuickBooksID']:
            if customer_data.get(field) is not None:
                update_fields.append(f"{field} = %s")
                values.append(customer_data[field])

        if not update_fields:
            return False

        values.append(customer_id)
        query = f"""
            UPDATE Customers
            SET {', '.join(update_fields)}
            WHERE CustomerID = %s
        """

        return self.execute_update(query, tuple(values))
