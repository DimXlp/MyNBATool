# check_postgres.py
"""Check if PostgreSQL is installed and accessible."""

import subprocess
import sys

def check_postgres_service():
    """Check if PostgreSQL service is running on Windows."""
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-Service postgresql*"],
            capture_output=True,
            text=True
        )
        
        if "Running" in result.stdout:
            print("✓ PostgreSQL service is running")
            return True
        elif result.stdout.strip():
            print("⚠ PostgreSQL service exists but is not running")
            print("  Start it with: Start-Service postgresql-x64-*")
            return False
        else:
            print("✗ PostgreSQL service not found")
            return False
    except Exception as e:
        print(f"⚠ Could not check service status: {e}")
        return False

def check_psql_command():
    """Check if psql command is available."""
    try:
        result = subprocess.run(
            ["psql", "--version"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✓ psql is available: {result.stdout.strip()}")
            return True
        else:
            print("✗ psql command not found")
            return False
    except FileNotFoundError:
        print("✗ psql command not found in PATH")
        print("  Add PostgreSQL bin directory to PATH")
        return False

def main():
    print("=" * 60)
    print("PostgreSQL Installation Check")
    print("=" * 60)
    
    print("\n1. Checking PostgreSQL service...")
    service_ok = check_postgres_service()
    
    print("\n2. Checking psql command...")
    psql_ok = check_psql_command()
    
    print("\n" + "=" * 60)
    if service_ok and psql_ok:
        print("✓ PostgreSQL is installed and ready!")
        print("\nNext steps:")
        print("  1. Run: python init_database.py")
        print("  2. Run: python import_to_database.py")
    elif service_ok and not psql_ok:
        print("⚠ PostgreSQL is running but psql is not in PATH")
        print("\nYou can still proceed:")
        print("  1. Run: python init_database.py")
        print("  2. Run: python import_to_database.py")
    else:
        print("✗ PostgreSQL needs to be installed")
        print("\nInstallation options:")
        print("  1. Download from: https://www.postgresql.org/download/windows/")
        print("  2. Or use chocolatey: choco install postgresql")

if __name__ == "__main__":
    main()
