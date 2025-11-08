import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from utils.db_client import DatabaseClient
from psycopg2 import extras
import utils.db_client


class TestDatabaseClient:
    """Test suite for DatabaseClient"""

    @pytest.fixture(autouse=True)
    def reset_connection_pool(self):
        """Reset the module-level connection pool before each test"""
        utils.db_client._connection_pool = None
        yield
        utils.db_client._connection_pool = None

    def test_initialization_without_url_raises_error(self):
        """Test that initialization fails without DATABASE_URL"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DATABASE_URL"):
                DatabaseClient()
    
    def test_initialization_with_url(self):
        """Test successful initialization with DATABASE_URL"""
        test_url = "postgresql://user:pass@localhost:5432/testdb"

        with patch('utils.db_client.psycopg2.pool.SimpleConnectionPool') as mock_pool:
            db = DatabaseClient(database_url=test_url)
            assert db.database_url == test_url
            assert db.max_retries == 3
            mock_pool.assert_called_once()

    def test_connection_pool_creation(self):
        """Test that connection pool is created correctly"""
        test_url = "postgresql://user:pass@localhost:5432/testdb"

        with patch('utils.db_client.psycopg2.pool.SimpleConnectionPool') as mock_pool:
            db = DatabaseClient(database_url=test_url)
            mock_pool.assert_called_once_with(
                minconn=1,
                maxconn=5,
                dsn=test_url,
                cursor_factory=extras.RealDictCursor
            )

    @patch('utils.db_client._connection_pool')
    def test_get_connection_context_manager(self, mock_pool):
        """Test connection context manager commits on success"""
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        test_url = "postgresql://user:pass@localhost:5432/testdb"
        with patch('utils.db_client.psycopg2.pool.SimpleConnectionPool'):
            db = DatabaseClient(database_url=test_url)

            with db.get_connection() as conn:
                assert conn == mock_conn
            
            mock_conn.commit.assert_called_once()
            mock_pool.putconn.assert_called_once_with(mock_conn)

            
    @patch('utils.db_client._connection_pool')
    def test_get_connection_rollback_on_error(self, mock_pool):
        """Test connection rollback on error"""
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        test_url = "postgresql://user:pass@localhost:5432/testdb"
        with patch('utils.db_client.psycopg2.pool.SimpleConnectionPool'):
            db = DatabaseClient(database_url=test_url)

            with pytest.raises(Exception):
                with db.get_connection() as conn:
                    raise Exception("Test error")
            
            mock_conn.rollback.assert_called_once()
            mock_pool.putconn.assert_called_once_with(mock_conn)
    
    @patch('utils.db_client.time.sleep')
    @patch('utils.db_client._connection_pool')
    def test_retry_logic(self, mock_pool, mock_sleep):
        """Test retry logic with exponential backoff"""
        import psycopg2

        test_url = "postgresql://user:pass@localhost:5432/testdb"
        with patch('utils.db_client.psycopg2.pool.SimpleConnectionPool'):
            db = DatabaseClient(database_url=test_url, max_retries=3)

            mock_operation = Mock(side_effect=[
                psycopg2.OperationalError("Connection lost"),
                psycopg2.OperationalError("Connection lost"),
                "Success"
            ])

            result = db._execute_with_retry(mock_operation)

            assert result == "Success"
            assert mock_operation.call_count == 3
            assert mock_sleep.call_count == 2