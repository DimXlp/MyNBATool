# db_config.py
"""Database configuration and connection management for NBA 2K26 tool."""

import os
from pathlib import Path
from typing import Optional
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import connection

# Database connection parameters
# You can override these with environment variables
DB_CONFIG = {
    "host": os.getenv("NBA2K_DB_HOST", "localhost"),
    "port": int(os.getenv("NBA2K_DB_PORT", "5432")),
    "database": os.getenv("NBA2K_DB_NAME", "nba2k26"),
    "user": os.getenv("NBA2K_DB_USER", "postgres"),
    "password": os.getenv("NBA2K_DB_PASSWORD", "postgres"),
}

def get_connection() -> connection:
    """Create and return a database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.OperationalError as e:
        print(f"ERROR: Could not connect to PostgreSQL database")
        print(f"Connection details: {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
        print(f"Error: {e}")
        print("\nMake sure:")
        print("  1. PostgreSQL is installed and running")
        print("  2. Database exists (run: createdb nba2k26)")
        print("  3. User has correct permissions")
        print("  4. Password is correct (set NBA2K_DB_PASSWORD env variable)")
        raise

def test_connection() -> bool:
    """Test the database connection."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        cur.close()
        conn.close()
        print(f"✓ Connected to PostgreSQL: {version[0][:50]}...")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

def database_exists() -> bool:
    """Check if the NBA 2K26 database exists."""
    try:
        # Connect to postgres database to check if nba2k26 exists
        temp_config = DB_CONFIG.copy()
        temp_config["database"] = "postgres"
        conn = psycopg2.connect(**temp_config)
        conn.autocommit = True
        cur = conn.cursor()
        
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (DB_CONFIG["database"],)
        )
        exists = cur.fetchone() is not None
        
        cur.close()
        conn.close()
        return exists
    except Exception:
        return False

def create_database() -> bool:
    """Create the NBA 2K26 database if it doesn't exist."""
    try:
        # Connect to postgres database
        temp_config = DB_CONFIG.copy()
        temp_config["database"] = "postgres"
        conn = psycopg2.connect(**temp_config)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Create database
        cur.execute(
            sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(DB_CONFIG["database"])
            )
        )
        
        cur.close()
        conn.close()
        print(f"✓ Created database: {DB_CONFIG['database']}")
        return True
    except psycopg2.errors.DuplicateDatabase:
        print(f"✓ Database {DB_CONFIG['database']} already exists")
        return True
    except Exception as e:
        print(f"✗ Failed to create database: {e}")
        return False

def execute_sql_file(filepath: Path) -> bool:
    """Execute SQL commands from a file."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        sql_content = filepath.read_text(encoding="utf-8")
        cur.execute(sql_content)
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"✓ Executed SQL file: {filepath.name}")
        return True
    except Exception as e:
        print(f"✗ Failed to execute {filepath.name}: {e}")
        return False

def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
            """,
            (table_name,)
        )
        exists = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        return exists
    except Exception:
        return False

def get_table_count(table_name: str) -> Optional[int]:
    """Get the number of rows in a table."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(
            sql.Identifier(table_name)
        ))
        count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        return count
    except Exception:
        return None
