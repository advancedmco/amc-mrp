"""
Product/Part data importer.

Handles importing product data from various sources and mapping to Parts table.
Supports both inventory and non-inventory items from QuickBooks.
"""

from typing import Any, Dict, List, Optional, Tuple
from .base_importer import BaseImporter


class ProductImporter(BaseImporter):
    """Imports product/item data into the Parts table."""

    # QuickBooks item types that should be imported
    SUPPORTED_ITEM_TYPES = [
        'Inventory',
        'NonInventory',
        'Service',
        'Category',  # Sometimes used for parts organization
        'Group'  # Part kits/assemblies
    ]

    def validate_record(self, record: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a product/part record.

        Args:
            record: Product data record

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Part number is required
        if not record.get('PartNumber'):
            return False, "Part number is required"

        # Part number should not be too long
        part_number = str(record['PartNumber'])
        if len(part_number) > 100:
            return False, f"Part number too long (max 100 chars): {part_number}"

        return True, None

    def normalize_product_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a product record from various source formats.

        Args:
            record: Raw product/item data

        Returns:
            Normalized product record
        """
        normalized = {}

        # Handle QuickBooks format
        if 'Type' in record or 'Id' in record:
            # Check if this is a supported item type
            item_type = record.get('Type', '')
            if item_type and item_type not in self.SUPPORTED_ITEM_TYPES:
                # Skip unsupported types (like Discount, Payment, Tax, etc.)
                return {}

            # Extract part number - use SKU if available, otherwise use Name
            part_number = record.get('Sku') or record.get('Name')

            # If no SKU or Name, use FullyQualifiedName
            if not part_number:
                part_number = record.get('FullyQualifiedName')

            normalized['PartNumber'] = self.normalizer.normalize_string(
                part_number, add_quotes=False
            )

            # Description - use Description field or fall back to Name
            description = record.get('Description') or record.get('Name')
            if description:
                normalized['Description'] = self.normalizer.normalize_string(
                    description, add_quotes=False
                )

            # Try to extract material information from description or custom fields
            # QuickBooks doesn't have a standard Material field, but it might be in description
            material = None
            desc_lower = (description or '').lower()

            # Common material keywords
            materials = ['aluminum', 'steel', 'stainless', 'brass', 'copper', 'titanium',
                        'plastic', 'nylon', 'delrin', 'acetal', 'bronze', 'iron']

            for mat in materials:
                if mat in desc_lower:
                    material = mat.title()
                    break

            if material:
                normalized['Material'] = material

            # Check for FSN (Federal Stock Number) in custom fields or SKU
            fsn = None
            sku = record.get('Sku', '')
            if sku and len(sku) >= 13 and sku[:4].isdigit():
                # FSN format: 4-digit NSN + 2-digit country code + 7-digit item number
                fsn = sku

            if fsn:
                normalized['FSN'] = self.normalizer.normalize_string(fsn, add_quotes=False)

        else:
            # Handle simple/CSV format
            part_number = (
                record.get('PartNumber') or
                record.get('part_number') or
                record.get('SKU') or
                record.get('sku') or
                record.get('part_no') or
                record.get('item_number')
            )

            normalized['PartNumber'] = self.normalizer.normalize_string(
                part_number, add_quotes=False
            )

            # Description
            description = (
                record.get('Description') or
                record.get('description') or
                record.get('name') or
                record.get('item_name')
            )
            if description:
                normalized['Description'] = self.normalizer.normalize_string(
                    description, add_quotes=False
                )

            # Material
            material = record.get('Material') or record.get('material')
            if material:
                normalized['Material'] = self.normalizer.normalize_string(
                    material, add_quotes=False
                )

            # FSN (Federal Stock Number)
            fsn = record.get('FSN') or record.get('fsn') or record.get('federal_stock_number')
            if fsn:
                normalized['FSN'] = self.normalizer.normalize_string(fsn, add_quotes=False)

        return normalized

    def import_data(self, data: List[Dict[str, Any]], **options) -> Dict[str, int]:
        """
        Import product/part data into the database.

        Args:
            data: List of product records
            options: Additional options
                - update_existing: Whether to update existing records (default: True)
                - filter_inventory: Only import inventory items (default: False)
                - filter_non_inventory: Only import non-inventory items (default: False)

        Returns:
            Statistics dictionary
        """
        self.reset_stats()
        update_existing = options.get('update_existing', True)
        filter_inventory = options.get('filter_inventory', False)
        filter_non_inventory = options.get('filter_non_inventory', False)

        for record in data:
            try:
                # Apply filters if specified
                if filter_inventory and record.get('Type') != 'Inventory':
                    self.stats['skipped'] += 1
                    continue

                if filter_non_inventory and record.get('Type') not in ['NonInventory', 'Service']:
                    self.stats['skipped'] += 1
                    continue

                # Normalize the record
                normalized = self.normalize_product_record(record)

                # Skip if normalization returned empty (unsupported type)
                if not normalized:
                    self.stats['skipped'] += 1
                    continue

                if not normalized.get('PartNumber'):
                    self.logger.warning(f"Skipping product with no part number: {record}")
                    self.stats['skipped'] += 1
                    continue

                # Validate the record
                is_valid, error_msg = self.validate_record(normalized)
                if not is_valid:
                    self.logger.warning(f"Invalid product record: {error_msg} - {normalized}")
                    self.stats['errors'] += 1
                    continue

                # Check if part exists by part number
                query = "SELECT PartID FROM Parts WHERE PartNumber = %s"
                result = self.execute_query(query, (normalized['PartNumber'],))

                if result:
                    part_id = result[0]['PartID']
                    if update_existing:
                        # Update existing part
                        self._update_part(part_id, normalized)
                        self.stats['updated'] += 1
                    else:
                        # Skip existing part
                        self.stats['skipped'] += 1
                else:
                    # Insert new part
                    self._insert_part(normalized)
                    self.stats['inserted'] += 1

            except Exception as e:
                self.logger.error(f"Error importing product: {e} - Record: {record}")
                self.stats['errors'] += 1

        self.log_stats()
        return self.get_stats()

    def _insert_part(self, part_data: Dict[str, Any]) -> Optional[int]:
        """Insert a new part record."""
        fields = []
        values = []

        for field in ['PartNumber', 'Description', 'Material', 'FSN']:
            if part_data.get(field) is not None:
                fields.append(field)
                values.append(part_data[field])

        if not fields:
            return None

        query = f"""
            INSERT INTO Parts ({', '.join(fields)})
            VALUES ({', '.join(['%s'] * len(values))})
        """

        return self.execute_insert(query, tuple(values))

    def _update_part(self, part_id: int, part_data: Dict[str, Any]) -> bool:
        """Update an existing part record."""
        update_fields = []
        values = []

        # Update all fields except PartNumber (which is the unique identifier)
        for field in ['Description', 'Material', 'FSN']:
            if part_data.get(field) is not None:
                update_fields.append(f"{field} = %s")
                values.append(part_data[field])

        if not update_fields:
            return False

        values.append(part_id)
        query = f"""
            UPDATE Parts
            SET {', '.join(update_fields)}
            WHERE PartID = %s
        """

        return self.execute_update(query, tuple(values))
