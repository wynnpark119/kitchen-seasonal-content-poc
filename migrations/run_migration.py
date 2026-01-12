#!/usr/bin/env python3
"""
Run database migration using Railway DATABASE_URL
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    # Get DATABASE_URL from Railway or environment
    database_url = os.getenv('DATABASE_URL') or os.getenv('RAILWAY_DATABASE_URL')
    
    # If DATABASE_URL not found, try to construct from individual components
    if not database_url:
        # Try to get from command line arguments or environment
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'postgres')
        
        if db_password and db_host:
            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        else:
            print("Error: DATABASE_URL not found in environment variables")
            print("Please set DATABASE_URL or provide DB_HOST, DB_PASSWORD, etc.")
            sys.exit(1)
    
    # Get migration file path - use ALL_MIGRATIONS.sql if available, otherwise 001_initial_schema.sql
    migration_file = Path(__file__).parent / 'ALL_MIGRATIONS.sql'
    if not migration_file.exists():
        migration_file = Path(__file__).parent / '001_initial_schema.sql'
    
    if not migration_file.exists():
        print(f"Error: Migration file not found: {migration_file}")
        print("Available migration files:")
        for f in Path(__file__).parent.glob('*.sql'):
            print(f"  - {f.name}")
        sys.exit(1)
    
    # Read SQL file
    print(f"Reading migration file: {migration_file.name}")
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Try to use psycopg2 to execute SQL
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        print(f"Connecting to database...")
        print(f"Database URL: {database_url[:50]}...")  # Show first 50 chars only
        
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print(f"Executing migration: {migration_file.name}")
        print("This may take a few moments...")
        
        # Execute SQL (may contain multiple statements)
        cursor.execute(sql_content)
        
        print("✅ Migration completed successfully!")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"\nCreated tables ({len(tables)}):")
        for table in tables:
            print(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        
    except ImportError:
        print("Error: psycopg2 not installed")
        print("Install it with: pip install psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        print(f"Error executing migration: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
