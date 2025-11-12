"""
Invoice data importer.

Handles importing invoice data and mapping to work orders.
Invoices are marked as complete with payment received status.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, date
from .base_importer import BaseImporter


class InvoiceImporter(BaseImporter):
    """Imports invoice data and creates/updates corresponding work orders."""

    def validate_record(self, record: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate an invoice record.

        Args:
            record: Invoice data record

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Invoice must have a customer
        if not record.get('CustomerRef') and not record.get('CustomerID'):
            return False, "Invoice must have a customer reference"

        # Invoice must have line items
        if not record.get('Line') and not record.get('LineItems'):
            return False, "Invoice must have line items"

        return True, None

    def normalize_invoice_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize an invoice record from various source formats.

        Args:
            record: Raw invoice data

        Returns:
            Normalized invoice record with line items
        """
        normalized = {}

        # Handle QuickBooks format
        if 'CustomerRef' in record or 'Id' in record:
            # Customer reference
            customer_ref = record.get('CustomerRef', {})
            if isinstance(customer_ref, dict):
                normalized['CustomerName'] = customer_ref.get('name')
                normalized['CustomerQBID'] = customer_ref.get('value')
            else:
                normalized['CustomerName'] = record.get('CustomerName')

            # Invoice details
            normalized['InvoiceNumber'] = record.get('DocNumber')
            normalized['InvoiceDate'] = self.normalizer.normalize_date(record.get('TxnDate'))
            normalized['DueDate'] = self.normalizer.normalize_date(record.get('DueDate'))
            normalized['TotalAmount'] = self.normalizer.normalize_number(record.get('TotalAmt'))

            # Line items
            line_items = []
            lines = record.get('Line', [])

            for line in lines:
                # Only process SalesItemLineDetail lines (actual products)
                detail_type = line.get('DetailType')
                if detail_type != 'SalesItemLineDetail':
                    continue

                sales_detail = line.get('SalesItemLineDetail', {})
                item_ref = sales_detail.get('ItemRef', {})

                if not isinstance(item_ref, dict):
                    continue

                line_item = {
                    'ItemName': item_ref.get('name'),
                    'ItemQBID': item_ref.get('value'),
                    'Description': line.get('Description') or item_ref.get('name'),
                    'Quantity': self.normalizer.normalize_number(sales_detail.get('Qty')),
                    'UnitPrice': self.normalizer.normalize_number(sales_detail.get('UnitPrice')),
                    'Amount': self.normalizer.normalize_number(line.get('Amount'))
                }

                if line_item['Quantity'] and line_item['Quantity'] > 0:
                    line_items.append(line_item)

            normalized['LineItems'] = line_items

        else:
            # Handle simple/CSV format
            normalized['CustomerName'] = (
                record.get('CustomerName') or
                record.get('customer_name') or
                record.get('customer')
            )

            normalized['CustomerQBID'] = record.get('CustomerQBID') or record.get('customer_qb_id')

            normalized['InvoiceNumber'] = (
                record.get('InvoiceNumber') or
                record.get('invoice_number') or
                record.get('invoice_no')
            )

            normalized['InvoiceDate'] = self.normalizer.normalize_date(
                record.get('InvoiceDate') or record.get('invoice_date')
            )

            normalized['DueDate'] = self.normalizer.normalize_date(
                record.get('DueDate') or record.get('due_date')
            )

            normalized['TotalAmount'] = self.normalizer.normalize_number(
                record.get('TotalAmount') or record.get('total_amount') or record.get('total')
            )

            # Line items - might be embedded or separate
            line_items = record.get('LineItems') or record.get('line_items') or []
            if not isinstance(line_items, list):
                # Single line item might be in the record itself
                line_items = [{
                    'ItemName': record.get('ItemName') or record.get('part_number'),
                    'Description': record.get('Description') or record.get('description'),
                    'Quantity': self.normalizer.normalize_number(
                        record.get('Quantity') or record.get('quantity')
                    ),
                    'UnitPrice': self.normalizer.normalize_number(
                        record.get('UnitPrice') or record.get('unit_price')
                    ),
                    'Amount': self.normalizer.normalize_number(
                        record.get('Amount') or record.get('amount')
                    )
                }]

            normalized['LineItems'] = line_items

        return normalized

    def import_data(self, data: List[Dict[str, Any]], **options) -> Dict[str, int]:
        """
        Import invoice data and create/update work orders.

        Args:
            data: List of invoice records
            options: Additional options
                - mark_as_complete: Mark work orders as completed (default: True)
                - set_payment_received: Set payment status to received (default: True)
                - create_missing_customers: Create customers if not found (default: True)
                - create_missing_parts: Create parts if not found (default: True)

        Returns:
            Statistics dictionary
        """
        self.reset_stats()
        mark_as_complete = options.get('mark_as_complete', True)
        set_payment_received = options.get('set_payment_received', True)
        create_missing_customers = options.get('create_missing_customers', True)
        create_missing_parts = options.get('create_missing_parts', True)

        for record in data:
            try:
                # Normalize the record
                normalized = self.normalize_invoice_record(record)

                if not normalized.get('CustomerName'):
                    self.logger.warning(f"Skipping invoice with no customer: {record}")
                    self.stats['skipped'] += 1
                    continue

                # Validate the record
                is_valid, error_msg = self.validate_record(normalized)
                if not is_valid:
                    self.logger.warning(f"Invalid invoice record: {error_msg} - {normalized}")
                    self.stats['errors'] += 1
                    continue

                # Get or create customer
                customer_id = self._get_or_create_customer(
                    normalized['CustomerName'],
                    normalized.get('CustomerQBID'),
                    create_missing_customers
                )

                if not customer_id:
                    self.logger.warning(
                        f"Customer not found and creation disabled: {normalized['CustomerName']}"
                    )
                    self.stats['errors'] += 1
                    continue

                # Process each line item
                for line_item in normalized.get('LineItems', []):
                    if not line_item.get('ItemName'):
                        continue

                    # Get or create part
                    part_id = self._get_or_create_part(
                        line_item['ItemName'],
                        line_item.get('Description'),
                        create_missing_parts
                    )

                    if not part_id:
                        self.logger.warning(
                            f"Part not found and creation disabled: {line_item['ItemName']}"
                        )
                        continue

                    # Create or update work order
                    work_order_created = self._create_or_update_work_order(
                        customer_id=customer_id,
                        part_id=part_id,
                        invoice_number=normalized.get('InvoiceNumber'),
                        quantity=line_item.get('Quantity'),
                        invoice_date=normalized.get('InvoiceDate'),
                        due_date=normalized.get('DueDate'),
                        mark_as_complete=mark_as_complete,
                        set_payment_received=set_payment_received
                    )

                    if work_order_created:
                        self.stats['inserted'] += 1
                    else:
                        self.stats['updated'] += 1

            except Exception as e:
                self.logger.error(f"Error importing invoice: {e} - Record: {record}")
                self.stats['errors'] += 1

        self.log_stats()
        return self.get_stats()

    def _get_or_create_customer(self, customer_name: str, qb_id: Optional[str],
                                create_if_missing: bool) -> Optional[int]:
        """Get existing customer ID or create new customer."""
        # Try to find by QuickBooks ID first
        if qb_id:
            query = "SELECT CustomerID FROM Customers WHERE QuickBooksID = %s"
            result = self.execute_query(query, (qb_id,))
            if result:
                return result[0]['CustomerID']

        # Try to find by name
        query = "SELECT CustomerID FROM Customers WHERE CustomerName = %s"
        result = self.execute_query(query, (customer_name,))
        if result:
            return result[0]['CustomerID']

        # Create if not found and creation is enabled
        if create_if_missing:
            if qb_id:
                insert_query = """
                    INSERT INTO Customers (CustomerName, QuickBooksID)
                    VALUES (%s, %s)
                """
                return self.execute_insert(insert_query, (customer_name, qb_id))
            else:
                insert_query = """
                    INSERT INTO Customers (CustomerName)
                    VALUES (%s)
                """
                return self.execute_insert(insert_query, (customer_name,))

        return None

    def _get_or_create_part(self, part_number: str, description: Optional[str],
                           create_if_missing: bool) -> Optional[int]:
        """Get existing part ID or create new part."""
        # Try to find by part number
        query = "SELECT PartID FROM Parts WHERE PartNumber = %s"
        result = self.execute_query(query, (part_number,))
        if result:
            return result[0]['PartID']

        # Create if not found and creation is enabled
        if create_if_missing:
            if description:
                insert_query = """
                    INSERT INTO Parts (PartNumber, Description)
                    VALUES (%s, %s)
                """
                return self.execute_insert(insert_query, (part_number, description))
            else:
                insert_query = """
                    INSERT INTO Parts (PartNumber)
                    VALUES (%s)
                """
                return self.execute_insert(insert_query, (part_number,))

        return None

    def _create_or_update_work_order(self, customer_id: int, part_id: int,
                                    invoice_number: Optional[str],
                                    quantity: Optional[int],
                                    invoice_date: Optional[date],
                                    due_date: Optional[date],
                                    mark_as_complete: bool,
                                    set_payment_received: bool) -> bool:
        """
        Create new work order or update existing one.

        Returns:
            True if created, False if updated
        """
        # Try to find existing work order
        query = """
            SELECT WorkOrderID FROM WorkOrders
            WHERE CustomerID = %s AND PartID = %s
            AND (CustomerPONumber = %s OR CustomerPONumber IS NULL)
            LIMIT 1
        """
        result = self.execute_query(query, (customer_id, part_id, invoice_number))

        if result:
            # Update existing work order
            work_order_id = result[0]['WorkOrderID']

            update_fields = []
            values = []

            if quantity:
                update_fields.append("QuantityOrdered = %s")
                update_fields.append("QuantityCompleted = %s")
                values.extend([quantity, quantity])

            if invoice_date:
                update_fields.append("CompletionDate = %s")
                values.append(invoice_date)

            if mark_as_complete:
                update_fields.append("Status = %s")
                values.append('Completed')

            if set_payment_received:
                update_fields.append("PaymentStatus = %s")
                values.append('Received')

            if update_fields:
                values.append(work_order_id)
                update_query = f"""
                    UPDATE WorkOrders
                    SET {', '.join(update_fields)}
                    WHERE WorkOrderID = %s
                """
                self.execute_update(update_query, tuple(values))

            return False  # Updated, not created

        else:
            # Create new work order
            insert_query = """
                INSERT INTO WorkOrders (
                    CustomerID, PartID, CustomerPONumber,
                    QuantityOrdered, QuantityCompleted,
                    StartDate, CompletionDate, DueDate,
                    Status, PaymentStatus
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            status = 'Completed' if mark_as_complete else 'Pending Material'
            payment_status = 'Received' if set_payment_received else 'Not Received'

            values = (
                customer_id,
                part_id,
                invoice_number,
                quantity or 1,
                quantity or 1 if mark_as_complete else 0,
                invoice_date or date.today(),
                invoice_date if mark_as_complete else None,
                due_date,
                status,
                payment_status
            )

            self.execute_insert(insert_query, values)
            return True  # Created
