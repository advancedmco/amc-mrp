"""
Base importer class providing common functionality for all importers.
"""

import pymysql
import logging
from typing import Any, Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
from contextlib import contextmanager

from .normalizers import DataNormalizer


class BaseImporter(ABC):
    """Base class for all data importers."""

    def __init__(self, db_config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize the importer.

        Args:
            db_config: Database configuration dictionary
            logger: Optional logger instance
        """
        self.db_config = db_config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.normalizer = DataNormalizer()
        self.stats = {
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }

    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = pymysql.connect(
                host=self.db_config['host'],
                port=self.db_config.get('port', 3306),
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            yield conn
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(self, query: str, params: Optional[Tuple] = None) -> Optional[List[Dict]]:
        """
        Execute a SELECT query and return results.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            List of result dictionaries
        """
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Query execution error: {e}\nQuery: {query}")
            return None

    def execute_insert(self, query: str, params: Optional[Tuple] = None) -> Optional[int]:
        """
        Execute an INSERT query and return the last insert ID.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            Last insert ID or None on error
        """
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Insert error: {e}\nQuery: {query}")
            return None

    def execute_update(self, query: str, params: Optional[Tuple] = None) -> bool:
        """
        Execute an UPDATE query.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    conn.commit()
                    return True
        except Exception as e:
            self.logger.error(f"Update error: {e}\nQuery: {query}")
            return False

    def batch_insert(self, query: str, records: List[Tuple]) -> int:
        """
        Execute batch insert operation.

        Args:
            query: SQL query string with placeholders
            records: List of parameter tuples

        Returns:
            Number of records inserted
        """
        if not records:
            return 0

        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(query, records)
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            self.logger.error(f"Batch insert error: {e}\nQuery: {query}")
            return 0

    def record_exists(self, table: str, conditions: Dict[str, Any]) -> bool:
        """
        Check if a record exists based on conditions.

        Args:
            table: Table name
            conditions: Dictionary of field:value conditions

        Returns:
            True if record exists, False otherwise
        """
        where_clause = ' AND '.join([f"{k} = %s" for k in conditions.keys()])
        query = f"SELECT 1 FROM {table} WHERE {where_clause} LIMIT 1"
        result = self.execute_query(query, tuple(conditions.values()))
        return bool(result)

    def get_or_create_id(self, table: str, id_field: str, unique_field: str,
                         unique_value: Any, default_data: Dict[str, Any]) -> Optional[int]:
        """
        Get existing record ID or create new record and return its ID.

        Args:
            table: Table name
            id_field: Primary key field name
            unique_field: Unique identifier field name
            unique_value: Value to search for
            default_data: Data for creating new record if not found

        Returns:
            Record ID or None on error
        """
        # Try to find existing record
        query = f"SELECT {id_field} FROM {table} WHERE {unique_field} = %s LIMIT 1"
        result = self.execute_query(query, (unique_value,))

        if result:
            return result[0][id_field]

        # Create new record
        fields = ', '.join(default_data.keys())
        placeholders = ', '.join(['%s'] * len(default_data))
        insert_query = f"INSERT INTO {table} ({fields}) VALUES ({placeholders})"

        return self.execute_insert(insert_query, tuple(default_data.values()))

    @abstractmethod
    def import_data(self, data: List[Dict[str, Any]], **options) -> Dict[str, int]:
        """
        Import data into the database.

        Args:
            data: List of data records to import
            options: Additional import options

        Returns:
            Statistics dictionary with counts
        """
        pass

    @abstractmethod
    def validate_record(self, record: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a single record before import.

        Args:
            record: Data record to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    def reset_stats(self):
        """Reset import statistics."""
        self.stats = {
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }

    def get_stats(self) -> Dict[str, int]:
        """Get current import statistics."""
        return self.stats.copy()

    def log_stats(self):
        """Log import statistics."""
        self.logger.info(
            f"Import complete - Inserted: {self.stats['inserted']}, "
            f"Updated: {self.stats['updated']}, "
            f"Skipped: {self.stats['skipped']}, "
            f"Errors: {self.stats['errors']}"
        )
