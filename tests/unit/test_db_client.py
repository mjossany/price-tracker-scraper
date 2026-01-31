"""
Unit tests for DatabaseClient.
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from utils.db_client import DatabaseClient
from psycopg2 import extras


class TestDatabaseClient:
    """Test suite for DatabaseClient"""

    def test_initialization_without_url_raises_error(self):
        """Test that initialization fails without DATABASE_URL"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DATABASE_URL"):
                DatabaseClient()

    def test_initialization_with_url(self):
        """Test successful initialization with DATABASE_URL"""
        test_url = "postgresql://user:pass@localhost:5432/testdb"
        db = DatabaseClient(database_url=test_url)
        assert db.database_url == test_url
        assert db.max_retries == 3

    def test_initialization_with_custom_retries(self):
        """Test initialization with custom max_retries"""
        test_url = "postgresql://user:pass@localhost:5432/testdb"
        db = DatabaseClient(database_url=test_url, max_retries=5)
        assert db.max_retries == 5

    @patch('utils.db_client.psycopg2.connect')
    def test_get_connection_context_manager(self, mock_connect):
        """Test connection context manager commits on success"""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        test_url = "postgresql://user:pass@localhost:5432/testdb"
        db = DatabaseClient(database_url=test_url)

        with db.get_connection() as conn:
            assert conn == mock_conn

        mock_connect.assert_called_once_with(
            test_url,
            cursor_factory=extras.RealDictCursor
        )
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('utils.db_client.psycopg2.connect')
    def test_get_connection_rollback_on_error(self, mock_connect):
        """Test connection rollback on error"""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        test_url = "postgresql://user:pass@localhost:5432/testdb"
        db = DatabaseClient(database_url=test_url)

        with pytest.raises(Exception):
            with db.get_connection() as conn:
                raise Exception("Test error")

        mock_conn.rollback.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('utils.db_client.time.sleep')
    def test_retry_logic_success_on_retry(self, mock_sleep):
        """Test retry logic succeeds after initial failure"""
        import psycopg2

        test_url = "postgresql://user:pass@localhost:5432/testdb"
        db = DatabaseClient(database_url=test_url, max_retries=3)

        mock_operation = Mock(side_effect=[
            psycopg2.OperationalError("Connection lost"),
            psycopg2.OperationalError("Connection lost"),
            "Success"
        ])

        result = db.execute_with_retry(mock_operation)

        assert result == "Success"
        assert mock_operation.call_count == 3
        assert mock_sleep.call_count == 2

    @patch('utils.db_client.time.sleep')
    def test_retry_logic_exhausted(self, mock_sleep):
        """Test retry logic raises error when all attempts fail"""
        import psycopg2

        test_url = "postgresql://user:pass@localhost:5432/testdb"
        db = DatabaseClient(database_url=test_url, max_retries=3)

        error = psycopg2.OperationalError("Connection lost")
        mock_operation = Mock(side_effect=error)

        with pytest.raises(psycopg2.OperationalError):
            db.execute_with_retry(mock_operation)

        assert mock_operation.call_count == 3
        assert mock_sleep.call_count == 2

    def test_retry_logic_no_retry_on_non_retryable_error(self):
        """Test that non-retryable errors are not retried"""
        test_url = "postgresql://user:pass@localhost:5432/testdb"
        db = DatabaseClient(database_url=test_url, max_retries=3)

        error = ValueError("Some other error")
        mock_operation = Mock(side_effect=error)

        with pytest.raises(ValueError):
            db.execute_with_retry(mock_operation)

        # Should only try once, no retries
        assert mock_operation.call_count == 1
