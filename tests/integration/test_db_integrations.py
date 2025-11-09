"""
Integration tests for DatabaseClient.

These tests use a REAL PostgresSQL database running in Docker.
No mocking - we test actual database operations!
"""
import pytest
import os
import psycopg2
from decimal import Decimal
from utils.db_client import DatabaseClient
import utils.db_client

class TestDatabaseClientIntegration:
    """Integration tests for database client with real PostgresSQL"""

    @pytest.fixture(autouse=True)
    def setup(self, test_database_url):
        """
        Setup before each test.

        - Sets DATABASE_URL environment variable
        - Resets the connection pool (important!)
        """

        # Set the test database URL
        os.environ['DATABASE_URL'] = test_database_url

        # Reset module-level connection pool
        utils.db_client._connection_pool = None

        yield

        # Cleanup after each test
        utils.db_client._connection_pool = None
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
    
    def test_basic_connection(self, test_database_url):
        """
        Test 1: Can we connect to the database?"

        This is the simplest test - just connect and run a query.
        """
        db = DatabaseClient()

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 as test_value")
                result = cur.fetchone()

                # Result should be a dict because we use RealDictCursor
                assert result['test_value'] == 1
    
