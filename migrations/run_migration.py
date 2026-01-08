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
    
    # Get migration file path
    migration_file = Path(__file__).parent / '001_initial_schema.sql'
    
    if not migration_file.exists():
        print(f"Error: Migration file not found: {migration_file}")
        sys.exit(1)
    
    # Read SQL file
    with open(migration_file, 'r') as f:
        sql_content = f.read()
    
    # Try to use psycopg2 to execute SQL
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        print(f"Connecting to database...")
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print(f"Executing migration: {migration_file.name}")
        cursor.execute(sql_content)
        
        print("Migration completed successfully!")
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
