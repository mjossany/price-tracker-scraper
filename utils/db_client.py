import os
import time
import psycopg2
from psycopg2 import pool, extras
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime
from utils.logger import get_logger

# Module-level connection pool (persists across Lambda invocations)
_connection_pool = None
logger = get_logger(__name__)

class DatabaseClient:
    """
    PostgresSQL database client optimized for AWS Lambda.

    Features:
    - Connection pooling for efficient resource usage
    - Automatic retry logic with exponential backoff
    - Context managers for safe connection handling
    - Structured logging for all operations
    """

    def __init__(self, database_url: Optional[str] = None, max_retries: int = 3):
        """
        Initialize database client.

        Args:
            database_url: PostgresSQL connection string (defaults to DATABASE_URL env var)
            max_retries: Maximum number of retry attempts for failed operations
        """
        self.database_url = database_url or os.environ.get("DATABASE_URL")
        self.max_retries = max_retries

        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        self._ensure_connection_pool()
        logger.info("DatabaseClient initialized", extra={
            "max_retries": max_retries
        })
    
    def _ensure_connection_pool(self):
        """
        Ensure connection pool exists and is healthy.

        Lambda functions reuse execution environments, so we create a module-level connection pool that persists across invocations. This significantly reduces cold start time.
        """

        global _connection_pool
        
        if _connection_pool is None:
            try:
                logger.info("Creating new database connection pool")
                _connection_pool = psycopg2.pool.SimpleConnectionPool(
                    minconn = 1,
                    maxconn = 5,
                    dsn = self.database_url,
                    cursor_factory=extras.RealDictCursor
                )
                logger.info("Connection pool created successfully")
            except Exception as e:
                logger.error("Failed to create connection pool", extra={
                    "error": str(e)
                })
                raise
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Yields:
            A database connection from the pool

        Example:
            with db_client.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM products")
        """
        conn = None
        try:
            conn = _connection_pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("Database operation failed", extra={
                "error": str(e)
            })
            raise
        finally:
            if conn:
                _connection_pool.putconn(conn)

    def _execute_with_retry(self, operation, *args, **kwargs):
        """
        Execute a database operation with exponential backoff retry logic.

        Args:
            operation: function to execute
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
                wait_time = 2 ** attempt

                logger.warning(f"Database operation failed, retrying...", extra={
                    "attempt": attempt + 1,
                    "max_retries": self.max_retries,
                    "wait_time": wait_time,
                    "error": str(e)
                })

                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
                    # Recreate connection pool on connection errors
                    global _connection_pool
                    _connection_pool = None
                    self._ensure_connection_pool()
            except Exception as e:
                #Don't retry on other types of errors (e.g., SQL syntax errors)
                logger.error("Non-retryable database error", extra={
                    "error": str(e)
                })
                raise
        logger.error("All retry attempts exhausted", extra={
            "max_retries": self.max_retries,
            "final_error": str(last_exception)
        })
        raise last_exception