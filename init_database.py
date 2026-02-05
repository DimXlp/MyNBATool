# init_database.py
"""Initialize the NBA 2K26 PostgreSQL database."""

from pathlib import Path
import db_config

def main():
    """Initialize the database and create tables."""
    print("=" * 60)
    print("NBA 2K26 Database Initialization")
    print("=" * 60)
    
    # Check if database exists, create if not
    print("\n1. Checking database...")
    if not db_config.database_exists():
        print(f"   Database '{db_config.DB_CONFIG['database']}' does not exist.")
        if not db_config.create_database():
            print("   Failed to create database. Exiting.")
            return
    else:
        print(f"   ✓ Database '{db_config.DB_CONFIG['database']}' exists")
    
    # Test connection
    print("\n2. Testing connection...")
    if not db_config.test_connection():
        print("   Failed to connect. Check your configuration.")
        return
    
    # Execute schema file
    print("\n3. Creating tables...")
    schema_file = Path("database/schema.sql")
    if not schema_file.exists():
        print(f"   ✗ Schema file not found: {schema_file}")
        return
    
    if db_config.execute_sql_file(schema_file):
        print("   ✓ Tables created successfully")
    else:
        print("   ✗ Failed to create tables")
        return
    
    # Verify tables
    print("\n4. Verifying tables...")
    tables = ["roster_players", "contracts", "draft_picks", "standings", "extraction_sources"]
    all_good = True
    
    for table in tables:
        if db_config.table_exists(table):
            count = db_config.get_table_count(table)
            print(f"   ✓ {table:30} ({count} rows)")
        else:
            print(f"   ✗ {table:30} (not found)")
            all_good = False
    
    # Check views
    print("\n5. Verifying views...")
    views = ["player_complete_info", "team_salary_summary", "draft_picks_inventory", "standings_detailed"]
    for view in views:
        if db_config.table_exists(view):  # Views are also in information_schema.tables
            print(f"   ✓ {view}")
        else:
            print(f"   ✗ {view}")
    
    if all_good:
        print("\n" + "=" * 60)
        print("✓ Database initialized successfully!")
        print("=" * 60)
        print("\nConnection details:")
        print(f"  Host:     {db_config.DB_CONFIG['host']}")
        print(f"  Port:     {db_config.DB_CONFIG['port']}")
        print(f"  Database: {db_config.DB_CONFIG['database']}")
        print(f"  User:     {db_config.DB_CONFIG['user']}")
        print("\nNext steps:")
        print("  1. Run: python import_to_database.py")
        print("     (Import existing JSON data into the database)")
        print("  2. Update extractors to write to database")
        print("  3. Query the database or create reports")
    else:
        print("\n⚠ Some tables are missing. Check the errors above.")

if __name__ == "__main__":
    main()
