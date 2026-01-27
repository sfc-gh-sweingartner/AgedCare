"""
Healthcare AI Demo - Simple Database Setup Script
================================================

This script creates the database objects without Streamlit dependencies.
"""

import snowflake.connector
import tomli
import os
from datetime import datetime

def get_connection():
    """Get Snowflake connection from config file"""
    try:
        config_path = '/Users/sweingartner/.snowflake/config.toml'
        
        with open(config_path, 'rb') as f:
            config = tomli.load(f)
        
        default_conn = config.get('default_connection_name')
        if not default_conn:
            raise ValueError("No default connection specified in config.toml")
            
        conn_params = config.get('connections', {}).get(default_conn)
        if not conn_params:
            raise ValueError(f"Connection '{default_conn}' not found in config.toml")
        
        conn = snowflake.connector.connect(**conn_params)
        print("✓ Connection established")
        return conn
        
    except Exception as e:
        print(f"✗ Failed to connect: {str(e)}")
        return None

def execute_sql_file(conn, filepath):
    """Execute SQL statements from a file"""
    with open(filepath, 'r') as f:
        sql_content = f.read()
    
    # Split into individual statements
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
    
    cursor = conn.cursor()
    success_count = 0
    error_count = 0
    
    for i, statement in enumerate(statements):
        # Skip comments and empty statements
        if not statement or statement.startswith('--'):
            continue
        
        # Extract first few words for description
        stmt_preview = ' '.join(statement.split()[:3])
        
        try:
            print(f"Statement {i+1}: {stmt_preview}...")
            cursor.execute(statement)
            print(f"  ✓ Success")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            error_count += 1
            # Continue with other statements
    
    cursor.close()
    return success_count, error_count

def test_setup(conn):
    """Test that tables were created successfully"""
    cursor = conn.cursor()
    
    print("\nVerifying tables...")
    tables = [
        "HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS",
        "HEALTHCARE_DEMO.MEDICAL_NOTES.REALTIME_ANALYSIS_LOG",
        "HEALTHCARE_DEMO.MEDICAL_NOTES.COHORT_INSIGHTS",
        "HEALTHCARE_DEMO.MEDICAL_NOTES.PHYSICIAN_INSIGHTS",
        "HEALTHCARE_DEMO.MEDICAL_NOTES.PROCESSING_STATUS",
        "HEALTHCARE_DEMO.MEDICAL_NOTES.DEMO_SCENARIOS"
    ]
    
    verified = 0
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            result = cursor.fetchone()
            print(f"  ✓ {table.split('.')[-1]}: Found")
            verified += 1
        except Exception as e:
            print(f"  ✗ {table.split('.')[-1]}: Not found")
    
    # Test PMC access
    print("\nTesting PMC patients access...")
    try:
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
        """)
        count = cursor.fetchone()[0]
        print(f"  ✓ PMC patients accessible: {count:,} records")
    except Exception as e:
        print(f"  ✗ PMC patients not accessible: {str(e)}")
    
    # Test Cortex AI
    print("\nTesting Cortex AI...")
    try:
        cursor.execute("""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'claude-4-sonnet',
                'Reply with just: WORKING'
            )
        """)
        result = cursor.fetchone()[0]
        if 'WORKING' in result.upper():
            print("  ✓ Cortex AI (Claude 4.0) is working")
        else:
            print("  ⚠ Cortex AI responded but unexpected output")
    except Exception as e:
        print(f"  ✗ Cortex AI not available: {str(e)}")
    
    cursor.close()
    return verified == len(tables)

def main():
    print("="*60)
    print("Healthcare AI Demo - Database Setup")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get connection
    conn = get_connection()
    if not conn:
        return 1
    
    # Execute SQL script
    print("\nCreating database objects...")
    success, errors = execute_sql_file(conn, 'sql/01_create_database_objects.sql')
    print(f"\nCompleted: {success} successful, {errors} errors")
    
    # Test setup
    all_good = test_setup(conn)
    
    # Summary
    print("\n" + "="*60)
    if all_good and errors == 0:
        print("✓ Setup completed successfully!")
        print("\nNext steps:")
        print("  1. Run: streamlit run src/streamlit_main.py")
        print("  2. Navigate to different pages to explore the demo")
    else:
        print("⚠ Setup completed with some issues. Check the errors above.")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    conn.close()
    return 0 if all_good else 1

if __name__ == "__main__":
    exit(main())