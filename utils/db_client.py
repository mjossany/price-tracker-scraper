"""
Simple PostgreSQL database client for AWS Lambda.
"""
import os
import time
import logging
import psycopg2
from psycopg2 import extras
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    PostgreSQL database client with basic retry logic.
    """

    def __init__(self, database_url: Optional[str] = None, max_retries: int = 3):
        """
        Initialize database client.

        Args:
            database_url: PostgreSQL connection string (defaults to DATABASE_URL env var)
            max_retries: Maximum number of retry attempts for failed operations
        """
        self.database_url = database_url or os.environ.get("DATABASE_URL")
        self.max_retries = max_retries

        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        logger.info(f"DatabaseClient initialized with max_retries={max_retries}")

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Yields:
            A database connection

        Example:
            with db_client.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM products")
        """
        conn = None
        try:
            conn = psycopg2.connect(
                self.database_url,
                cursor_factory=extras.RealDictCursor
            )
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_with_retry(self, operation, *args, **kwargs):
        """
        Execute a database operation with basic retry logic.

        Args:
            operation: Function to execute
            *args, **kwargs: Arguments to pass to the operation

        Returns:
            Result of the operation

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                last_exception = e
                logger.warning(
                    f"Database operation failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                
                if attempt < self.max_retries - 1:
                    time.sleep(1)  # Simple 1 second delay between retries
            except Exception as e:
                # Don't retry on other types of errors
                logger.error(f"Non-retryable database error: {e}")
                raise

        logger.error(f"All retry attempts exhausted. Final error: {last_exception}")
        raise last_exception
