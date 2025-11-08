import os
from utils.db_client import DatabaseClient
from utils.logger import get_logger

logger = get_logger(__name__)

def test_connection():
    """Simple database connectivity test"""
    try:
        print("🔄 Initializing database client...")
        db = DatabaseClient()

        print("🔄 Testing connection...")
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()
                print(f"✅ Connected to PostgresSQL!")
                print(f"📊 Version: {version['version']}")
        
        print("\n🔄 Testing table access...")
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = cur.fetchall()
                print(f"✅ Found {len(tables)} tables:")
                for table in tables:
                    print(f"  - {table['table_name']}")

        print("\n ✅ All database tests passed!")
        return True
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        logger.error("Database connectivity test failed", extra={"error": str(e)})
        return False

if __name__ == "__main__":
    if not os.environ.get("DATABASE_URL"):
        print("❌ DATABASE_URL environment variable not set")
        print("Example: export DATABASE_URL='postgresql://user:pass@host:5432/dbname'")
        exit(1)

    test_connection()
