"""
Vendor data importer.

Handles importing vendor data with contact information from various sources.
Supports both creation and updates of vendor records.
"""

from typing import Any, Dict, List, Optional, Tuple
from .base_importer import BaseImporter


class VendorImporter(BaseImporter):
    """Imports vendor data into the Vendors table."""

    # Field mapping for QuickBooks vendor data
    QB_FIELD_MAPPING = {
        'DisplayName': 'VendorName',
        'Id': 'QuickBooksID',
        'PrimaryPhone': 'ContactPhone',
        'PrimaryEmailAddr': 'ContactEmail',
        'CompanyName': 'VendorName',
        'GivenName': 'FirstName',
        'FamilyName': 'LastName',
        'AcctNum': 'AccountNumber'
    }

    def validate_record(self, record: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a vendor record.

        Args:
            record: Vendor data record

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Vendor name is required
        if not record.get('VendorName') and not record.get('DisplayName'):
            return False, "Vendor name is required"

        # Validate email format if provided
        email = record.get('ContactEmail') or record.get('PrimaryEmailAddr', {}).get('Address')
        if email:
            normalized_email = self.normalizer.normalize_email(email)
            if not normalized_email:
                return False, f"Invalid email format: {email}"

        return True, None

    def normalize_vendor_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a vendor record from various source formats.

        Args:
            record: Raw vendor data

        Returns:
            Normalized vendor record
        """
        normalized = {}

        # Handle QuickBooks format
        if 'DisplayName' in record or 'Id' in record:
            # Extract vendor name
            vendor_name = record.get('DisplayName') or record.get('CompanyName')
            if not vendor_name and record.get('GivenName'):
                # Build name from parts
                given = record.get('GivenName', '')
                family = record.get('FamilyName', '')
                vendor_name = f"{given} {family}".strip()

            normalized['VendorName'] = self.normalizer.normalize_string(vendor_name, add_quotes=False)

            # QuickBooks ID
            if 'Id' in record:
                normalized['QuickBooksID'] = record['Id']

            # Contact phone
            phone_obj = record.get('PrimaryPhone')
            if phone_obj and isinstance(phone_obj, dict):
                phone = phone_obj.get('FreeFormNumber')
            elif phone_obj:
                phone = phone_obj
            else:
                phone = record.get('ContactPhone')

            if phone:
                normalized['ContactPhone'] = self.normalizer.normalize_phone(phone)

            # Contact email
            email_obj = record.get('PrimaryEmailAddr')
            if email_obj and isinstance(email_obj, dict):
                email = email_obj.get('Address')
            elif email_obj:
                email = email_obj
            else:
                email = record.get('ContactEmail')

            if email:
                normalized['ContactEmail'] = self.normalizer.normalize_email(email)

            # Address - combine address components
            address_parts = []
            bill_addr = record.get('BillAddr', {})
            if isinstance(bill_addr, dict):
                for key in ['Line1', 'Line2', 'Line3', 'Line4', 'Line5']:
                    if bill_addr.get(key):
                        address_parts.append(bill_addr[key])
                if bill_addr.get('City'):
                    city_state_zip = bill_addr.get('City', '')
                    if bill_addr.get('CountrySubDivisionCode'):
                        city_state_zip += f", {bill_addr['CountrySubDivisionCode']}"
                    if bill_addr.get('PostalCode'):
                        city_state_zip += f" {bill_addr['PostalCode']}"
                    address_parts.append(city_state_zip)

            if address_parts:
                normalized['Address'] = '\n'.join(address_parts)
            elif record.get('Address'):
                normalized['Address'] = self.normalizer.normalize_string(
                    record['Address'], add_quotes=False
                )

            # Account number
            if record.get('AcctNum'):
                normalized['AccountNumber'] = self.normalizer.normalize_string(
                    record['AcctNum'], add_quotes=False
                )

        else:
            # Handle simple/CSV format
            normalized['VendorName'] = self.normalizer.normalize_string(
                record.get('VendorName') or record.get('vendor_name') or record.get('name'),
                add_quotes=False
            )

            if record.get('QuickBooksID') or record.get('qb_id'):
                normalized['QuickBooksID'] = record.get('QuickBooksID') or record.get('qb_id')

            phone = record.get('ContactPhone') or record.get('phone') or record.get('contact_phone')
            if phone:
                normalized['ContactPhone'] = self.normalizer.normalize_phone(phone)

            email = record.get('ContactEmail') or record.get('email') or record.get('contact_email')
            if email:
                normalized['ContactEmail'] = self.normalizer.normalize_email(email)

            address = record.get('Address') or record.get('address')
            if address:
                normalized['Address'] = self.normalizer.normalize_string(address, add_quotes=False)

            account_num = record.get('AccountNumber') or record.get('account_number')
            if account_num:
                normalized['AccountNumber'] = self.normalizer.normalize_string(
                    account_num, add_quotes=False
                )

        return normalized

    def import_data(self, data: List[Dict[str, Any]], **options) -> Dict[str, int]:
        """
        Import vendor data into the database.

        Args:
            data: List of vendor records
            options: Additional options
                - update_existing: Whether to update existing records (default: True)
                - match_by_qb_id: Whether to match by QuickBooks ID (default: True)
                - match_by_name: Whether to match by vendor name (default: True)

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
                normalized = self.normalize_vendor_record(record)

                if not normalized.get('VendorName'):
                    self.logger.warning(f"Skipping vendor with no name: {record}")
                    self.stats['skipped'] += 1
                    continue

                # Validate the record
                is_valid, error_msg = self.validate_record(normalized)
                if not is_valid:
                    self.logger.warning(f"Invalid vendor record: {error_msg} - {normalized}")
                    self.stats['errors'] += 1
                    continue

                # Check if vendor exists
                vendor_id = None

                # Try matching by QuickBooks ID first
                if match_by_qb_id and normalized.get('QuickBooksID'):
                    query = "SELECT VendorID FROM Vendors WHERE QuickBooksID = %s"
                    result = self.execute_query(query, (normalized['QuickBooksID'],))
                    if result:
                        vendor_id = result[0]['VendorID']

                # Try matching by name if not found
                if not vendor_id and match_by_name:
                    query = "SELECT VendorID FROM Vendors WHERE VendorName = %s"
                    result = self.execute_query(query, (normalized['VendorName'],))
                    if result:
                        vendor_id = result[0]['VendorID']

                if vendor_id and update_existing:
                    # Update existing vendor
                    self._update_vendor(vendor_id, normalized)
                    self.stats['updated'] += 1
                elif vendor_id:
                    # Skip existing vendor
                    self.stats['skipped'] += 1
                else:
                    # Insert new vendor
                    self._insert_vendor(normalized)
                    self.stats['inserted'] += 1

            except Exception as e:
                self.logger.error(f"Error importing vendor: {e} - Record: {record}")
                self.stats['errors'] += 1

        self.log_stats()
        return self.get_stats()

    def _insert_vendor(self, vendor_data: Dict[str, Any]) -> Optional[int]:
        """Insert a new vendor record."""
        fields = []
        values = []

        for field in ['VendorName', 'QuickBooksID', 'ContactPhone', 'ContactEmail',
                      'Address', 'AccountNumber']:
            if vendor_data.get(field) is not None:
                fields.append(field)
                values.append(vendor_data[field])

        if not fields:
            return None

        query = f"""
            INSERT INTO Vendors ({', '.join(fields)})
            VALUES ({', '.join(['%s'] * len(values))})
        """

        return self.execute_insert(query, tuple(values))

    def _update_vendor(self, vendor_id: int, vendor_data: Dict[str, Any]) -> bool:
        """Update an existing vendor record."""
        update_fields = []
        values = []

        for field in ['VendorName', 'QuickBooksID', 'ContactPhone', 'ContactEmail',
                      'Address', 'AccountNumber']:
            if vendor_data.get(field) is not None:
                update_fields.append(f"{field} = %s")
                values.append(vendor_data[field])

        if not update_fields:
            return False

        values.append(vendor_id)
        query = f"""
            UPDATE Vendors
            SET {', '.join(update_fields)}
            WHERE VendorID = %s
        """

        return self.execute_update(query, tuple(values))
