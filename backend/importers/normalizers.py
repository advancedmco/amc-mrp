"""
Data normalization utilities for import operations.

Handles:
- String quoting and escaping
- Data type normalization
- Null/empty value handling
- Field validation
"""

import re
from typing import Any, Dict, List, Optional
from datetime import datetime, date
from decimal import Decimal


class DataNormalizer:
    """Normalizes and validates data for database import."""

    @staticmethod
    def normalize_string(value: Any, add_quotes: bool = True) -> Optional[str]:
        """
        Normalize a string value with proper quoting and escaping.

        Args:
            value: The value to normalize
            add_quotes: Whether to wrap in double quotes

        Returns:
            Normalized string or None if value is empty/null
        """
        if value is None or value == '':
            return None

        # Convert to string
        str_value = str(value).strip()

        if not str_value:
            return None

        # Escape existing quotes
        str_value = str_value.replace('"', '\\"')

        # Add double quotes if requested
        if add_quotes:
            return f'"{str_value}"'

        return str_value

    @staticmethod
    def normalize_number(value: Any) -> Optional[Decimal]:
        """
        Normalize a numeric value.

        Args:
            value: The value to normalize

        Returns:
            Decimal value or None
        """
        if value is None or value == '':
            return None

        try:
            # Remove any non-numeric characters except decimal point and minus
            if isinstance(value, str):
                # Remove currency symbols, commas, etc.
                clean_value = re.sub(r'[^\d.-]', '', value)
                if not clean_value or clean_value == '-':
                    return None
                return Decimal(clean_value)
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def normalize_date(value: Any) -> Optional[date]:
        """
        Normalize a date value.

        Args:
            value: The value to normalize (string, datetime, or date)

        Returns:
            date object or None
        """
        if value is None or value == '':
            return None

        if isinstance(value, date):
            return value

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            # Try common date formats
            formats = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y/%m/%d',
                '%m-%d-%Y',
                '%d-%m-%Y',
                '%Y%m%d'
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(value.strip(), fmt).date()
                except ValueError:
                    continue

        return None

    @staticmethod
    def normalize_boolean(value: Any) -> bool:
        """
        Normalize a boolean value.

        Args:
            value: The value to normalize

        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.strip().lower() in ('true', 'yes', '1', 'y', 't')

        return bool(value)

    @staticmethod
    def normalize_email(value: Any) -> Optional[str]:
        """
        Normalize and validate an email address.

        Args:
            value: The email to normalize

        Returns:
            Normalized email or None if invalid
        """
        if value is None or value == '':
            return None

        email = str(value).strip().lower()

        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, email):
            return email

        return None

    @staticmethod
    def normalize_phone(value: Any) -> Optional[str]:
        """
        Normalize a phone number.

        Args:
            value: The phone number to normalize

        Returns:
            Normalized phone number or None
        """
        if value is None or value == '':
            return None

        # Extract digits only
        digits = re.sub(r'\D', '', str(value))

        if not digits:
            return None

        # Format based on length
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        else:
            return digits

    @staticmethod
    def normalize_record(record: Dict[str, Any], field_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Normalize an entire record based on field mapping.

        Args:
            record: The raw data record
            field_mapping: Dictionary mapping source fields to target fields with types
                          Format: {'source_field': 'target_field:type'}

        Returns:
            Normalized record
        """
        normalized = {}

        for source_field, target_spec in field_mapping.items():
            if ':' in target_spec:
                target_field, field_type = target_spec.split(':', 1)
            else:
                target_field = target_spec
                field_type = 'string'

            value = record.get(source_field)

            # Apply appropriate normalization based on type
            if field_type == 'string':
                normalized[target_field] = DataNormalizer.normalize_string(value, add_quotes=False)
            elif field_type == 'quoted_string':
                normalized[target_field] = DataNormalizer.normalize_string(value, add_quotes=True)
            elif field_type == 'number':
                normalized[target_field] = DataNormalizer.normalize_number(value)
            elif field_type == 'date':
                normalized[target_field] = DataNormalizer.normalize_date(value)
            elif field_type == 'boolean':
                normalized[target_field] = DataNormalizer.normalize_boolean(value)
            elif field_type == 'email':
                normalized[target_field] = DataNormalizer.normalize_email(value)
            elif field_type == 'phone':
                normalized[target_field] = DataNormalizer.normalize_phone(value)
            else:
                normalized[target_field] = value

        return normalized

    @staticmethod
    def prepare_for_sql(value: Any) -> str:
        """
        Prepare a value for SQL insertion with proper quoting.

        Args:
            value: The value to prepare

        Returns:
            SQL-safe string representation
        """
        if value is None:
            return 'NULL'

        if isinstance(value, bool):
            return '1' if value else '0'

        if isinstance(value, (int, Decimal)):
            return str(value)

        if isinstance(value, (date, datetime)):
            return f"'{value.strftime('%Y-%m-%d')}'"

        # String value - escape and quote
        str_value = str(value).replace("'", "''").replace('\\', '\\\\')
        return f"'{str_value}'"
