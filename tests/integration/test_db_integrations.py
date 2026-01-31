"""
Integration tests for DatabaseClient.

These tests use a REAL PostgreSQL database running in Docker.
No mocking - we test actual database operations!
"""
import pytest
import os
import psycopg2
from decimal import Decimal
from utils.db_client import DatabaseClient


class TestDatabaseClientIntegration:
    """Integration tests for database client with real PostgreSQL"""

    @pytest.fixture(autouse=True)
    def setup(self, test_database_url):
        """
        Setup before each test.
        Sets DATABASE_URL environment variable.
        """
        os.environ['DATABASE_URL'] = test_database_url
        yield
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']

    def test_basic_connection(self, test_database_url):
        """
        Test 1: Can we connect to the database?
        This is the simplest test - just connect and run a query.
        """
        db = DatabaseClient()

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 as test_value")
                result = cur.fetchone()

                # Result should be a dict because we use RealDictCursor
                assert result['test_value'] == 1

    def test_multiple_client_instances(self, test_database_url):
        """
        Test 2: Multiple DatabaseClient instances work independently.
        Each creates its own connection when needed.
        """
        db1 = DatabaseClient()
        db2 = DatabaseClient()

        # Both instances should work independently
        with db1.get_connection() as conn1:
            with conn1.cursor() as cur:
                cur.execute("SELECT 1 as value")
                result = cur.fetchone()
                assert result['value'] == 1

        with db2.get_connection() as conn2:
            with conn2.cursor() as cur:
                cur.execute("SELECT 2 as value")
                result = cur.fetchone()
                assert result['value'] == 2

    def test_transaction_commit(self, test_database_url, sample_user):
        """
        Test 3: Successful operations commit automatically.
        The context manager should commit when no errors occur.
        """
        db = DatabaseClient()

        # Insert a product
        product_id = None
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO products (user_id, name, description, is_active)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (sample_user['id'], 'Integration Test Product', 'Test description', True))
                product_id = cur.fetchone()['id']

        # Verify it was committed by reading in a NEW connection
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT name, description FROM products WHERE id = %s
                """, (product_id,))
                result = cur.fetchone()

                assert result is not None
                assert result['name'] == 'Integration Test Product'
                assert result['description'] == 'Test description'

    def test_transaction_rollback(self, test_database_url, sample_user):
        """
        Test 4: Failed operations rollback automatically.
        Critical for data integrity! If something fails, nothing should persist.
        """
        db = DatabaseClient()

        # Try to insert a product but raise an error
        with pytest.raises(Exception, match="Test error"):
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO products (user_id, name, is_active)
                        VALUES (%s, %s, %s)
                    """, (sample_user['id'], 'Should Not Exist', True))

                    # Raise an error before commit
                    raise Exception("Test error")

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM products
                    WHERE name = 'Should Not Exist'
                """)
                result = cur.fetchone()

                assert result['count'] == 0

    def test_real_dict_cursor(self, test_database_url, sample_product):
        """
        Test 5: RealDictCursor returns dictionaries (not tuples).
        This makes your Lambda code cleaner - you can access columns by name!
        """
        db = DatabaseClient()

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, is_active, target_price, currency
                    FROM products
                    WHERE id = %s
                """, (sample_product['id'],))
                result = cur.fetchone()

                # Should be a dict, not a tuple
                assert isinstance(result, dict)
                assert result['id'] == sample_product['id']
                assert result['name'] == sample_product['name']
                assert result['is_active'] is True
                assert result['target_price'] == Decimal('99.99')
                assert result['currency'] == 'BRL'

    def test_multiple_rows(self, test_database_url, sample_user):
        """
        Test 6: Fetching multiple rows works correctly.
        Important for your scraper which will fetch many product links!
        """
        db = DatabaseClient()

        # Insert multiple products
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                products = [
                    (sample_user['id'], 'Product 1', 'Description 1'),
                    (sample_user['id'], 'Product 2', 'Description 2'),
                    (sample_user['id'], 'Product 3', 'Description 3'),
                ]
                cur.executemany("""
                    INSERT INTO products (user_id, name, description)
                    VALUES (%s, %s, %s)
                """, products)

        # Fetch them all
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT name, description FROM products
                    WHERE user_id = %s
                    ORDER BY name
                """, (sample_user['id'],))
                results = cur.fetchall()

                assert len(results) == 3
                assert results[0]['name'] == 'Product 1'
                assert results[1]['name'] == 'Product 2'
                assert results[2]['name'] == 'Product 3'

    def test_uuid_primary_keys(self, test_database_url, sample_user):
        """
        Test 7: UUID primary keys are working correctly.
        Your schema uses UUIDs, not integers!
        """
        db = DatabaseClient()

        # Insert a product and verify UUID is returned
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO products (user_id, name)
                    VALUES (%s, %s)
                    RETURNING id
                """, (sample_user['id'], 'UUID Test Product'))
                product_id = cur.fetchone()['id']

                assert isinstance(product_id, str)
                assert len(product_id) == 36
                assert product_id.count('-') == 4

    def test_product_link_insertion(self, test_database_url, sample_product):
        """
        Test 8: Insert product links (critical for scraper workflow!).
        This tests the exact data structure your scraper will use.
        """
        db = DatabaseClient()

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO product_links (
                        product_id,
                        url,
                        store,
                        product_identifier,
                        is_active
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, url, store, product_identifier
                """, (
                    sample_product['id'],
                    'https://www.amazon.com/dp/B08N5WRWNW',
                    'amazon',
                    'B08N5WRWNW',
                    True
                ))
                result = cur.fetchone()

                assert result['url'] == 'https://www.amazon.com/dp/B08N5WRWNW'
                assert result['store'] == 'amazon'
                assert result['product_identifier'] == 'B08N5WRWNW'

    def test_price_history_insertion(self, test_database_url, sample_product_link):
        """
        Test 9: Insert price history (the core scraper function!).
        This is what your Lambda will do after scraping a price.
        """
        db = DatabaseClient()

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO price_history (
                        product_link_id,
                        price,
                        original_price,
                        discount_percentage,
                        currency,
                        was_available,
                        scrape_source,
                        response_time_ms
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, price, original_price, discount_percentage
                """, (
                    sample_product_link['id'],
                    79.99,
                    99.99,
                    20.00,
                    'BRL',
                    True,
                    'scraper_v1',
                    1250
                ))
                result = cur.fetchone()

                assert result['price'] == Decimal('79.99')
                assert result['original_price'] == Decimal('99.99')
                assert result['discount_percentage'] == Decimal('20.00')

    def test_fetch_active_product_links(self, test_database_url, sample_product_link):
        """
        Test 10: Fetch active product links for scraping.
        This simulates what your Lambda will do at the start of each run.
        """
        db = DatabaseClient()

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # This is the type of query your scraper will use
                cur.execute("""
                    SELECT 
                        pl.id,
                        pl.url,
                        pl.store,
                        pl.product_identifier,
                        pl.last_price,
                        pl.scrape_error_count
                    FROM product_links pl
                    JOIN products p ON pl.product_id = p.id
                    WHERE pl.is_active = true 
                    AND p.is_active = true
                    ORDER BY pl.last_checked_at ASC NULLS FIRST
                """)
                results = cur.fetchall()

                assert len(results) >= 1
                assert results[0]['store'] == 'amazon'
                assert results[0]['url'] == 'https://www.amazon.com/dp/B08N5WRWNW'

    def test_update_product_link_after_scrape(self, test_database_url, sample_product_link):
        """
        Test 11: Update product link after scraping.
        After scraping, your Lambda updates last_price and last_checked_at.
        """
        db = DatabaseClient()

        # Scrape and update
        new_price = Decimal('89.99')

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE product_links
                    SET 
                        last_price = %s,
                        last_checked_at = now(),
                        lowest_price_seen = COALESCE(
                            LEAST(lowest_price_seen, %s), 
                            %s
                        ),
                        highest_price_seen = COALESCE(
                            GREATEST(highest_price_seen, %s), 
                            %s
                        )
                    WHERE id = %s
                    RETURNING last_price, lowest_price_seen, highest_price_seen
                """, (
                    new_price,
                    new_price, new_price,  # For lowest_price_seen
                    new_price, new_price,  # For highest_price_seen
                    sample_product_link['id']
                ))
                result = cur.fetchone()

                assert result['last_price'] == new_price
                assert result['lowest_price_seen'] == new_price
                assert result['highest_price_seen'] == new_price

    def test_cascade_delete(self, test_database_url, sample_user):
        """
        Test 12: Cascade deletes work correctly.
        When a user is deleted, all their products should be deleted too.
        """
        db = DatabaseClient()

        # Create a product
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO products (user_id, name)
                    VALUES(%s, %s)
                    RETURNING id
                """, (sample_user['id'], 'Will be deleted'))
                product_id = cur.fetchone()['id']

        # Delete the user
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM users WHERE id = %s", (sample_user['id'],))

        # Verify product was cascade deleted
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM products
                    WHERE id = %s
                """, (product_id,))
                result = cur.fetchone()

                assert result['count'] == 0
