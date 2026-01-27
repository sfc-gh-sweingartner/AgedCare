"""
PMC Patients Database Setup Script
=================================

This script helps colleagues set up the PMC_PATIENTS database and load the CSV data.
It provides an automated way to execute the SQL setup and data loading process.
"""

import snowflake.connector
import tomli
import os
from datetime import datetime
from pathlib import Path

def get_connection():
    """Get Snowflake connection from config file"""
    try:
        config_path = os.path.expanduser('~/.snowflake/config.toml')
        
        if not os.path.exists(config_path):
            print(f"✗ Config file not found at {config_path}")
            print("Please create a Snowflake config file with your connection details.")
            return None
        
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
    if not os.path.exists(filepath):
        print(f"✗ SQL file not found: {filepath}")
        return 0, 1
    
    with open(filepath, 'r') as f:
        sql_content = f.read()
    
    # Split into individual statements, handling complex SQL
    statements = []
    current_statement = ""
    in_comment_block = False
    
    for line in sql_content.split('\n'):
        line = line.strip()
        
        # Handle comment blocks
        if line.startswith('/*'):
            in_comment_block = True
            continue
        if '*/' in line:
            in_comment_block = False
            continue
        if in_comment_block:
            continue
        
        # Skip single-line comments and empty lines
        if not line or line.startswith('--'):
            continue
        
        current_statement += " " + line
        
        # Check if statement is complete (ends with semicolon)
        if line.endswith(';'):
            statements.append(current_statement.strip())
            current_statement = ""
    
    cursor = conn.cursor()
    success_count = 0
    error_count = 0
    
    for i, statement in enumerate(statements):
        if not statement:
            continue
        
        # Extract first few words for description
        stmt_preview = ' '.join(statement.split()[:4])
        
        try:
            print(f"Statement {i+1}: {stmt_preview}...")
            cursor.execute(statement)
            print(f"  ✓ Success")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            error_count += 1
            # Continue with other statements for non-critical errors
    
    cursor.close()
    return success_count, error_count

def upload_and_load_csv(conn, csv_path):
    """Upload CSV file and load data into table"""
    cursor = conn.cursor()
    
    try:
        # Check if CSV file exists
        if not os.path.exists(csv_path):
            print(f"✗ CSV file not found: {csv_path}")
            return False
        
        print(f"\nUploading CSV file: {csv_path}")
        
        # Use PMC_PATIENTS database and schema
        cursor.execute("USE DATABASE PMC_PATIENTS")
        cursor.execute("USE SCHEMA PMC_PATIENTS")
        
        # Upload file to stage
        put_command = f"PUT 'file://{csv_path}' @PMC_DATA_STAGE AUTO_COMPRESS=TRUE"
        print("Uploading file to stage...")
        cursor.execute(put_command)
        print("  ✓ File uploaded successfully")
        
        # Load data from stage to table
        copy_command = """
        COPY INTO PMC_PATIENTS (
            PATIENT_ID,
            PATIENT_UID, 
            PMID,
            FILE_PATH,
            PATIENT_TITLE,
            PATIENT_NOTES,
            AGE,
            GENDER,
            RELEVANT_ARTICLES,
            SIMILAR_PATIENTS
        )
        FROM (
            SELECT 
                TRY_CAST($1 AS NUMBER) AS PATIENT_ID,
                $2 AS PATIENT_UID,
                TRY_CAST($3 AS NUMBER) AS PMID,
                $4 AS FILE_PATH,
                $5 AS PATIENT_TITLE,
                $6 AS PATIENT_NOTES,
                $7 AS AGE,
                $8 AS GENDER,
                $9 AS RELEVANT_ARTICLES,
                $10 AS SIMILAR_PATIENTS
            FROM @PMC_DATA_STAGE
        )
        FILE_FORMAT = CSV_FORMAT
        ON_ERROR = 'CONTINUE'
        """
        
        print("Loading data into table...")
        cursor.execute(copy_command)
        print("  ✓ Data loaded successfully")
        
        # Verify data was loaded
        cursor.execute("SELECT COUNT(*) FROM PMC_PATIENTS")
        count = cursor.fetchone()[0]
        print(f"  ✓ Total records loaded: {count:,}")
        
        cursor.close()
        return True
        
    except Exception as e:
        print(f"  ✗ Error during CSV loading: {str(e)}")
        cursor.close()
        return False

def verify_setup(conn):
    """Verify that the setup was completed successfully"""
    cursor = conn.cursor()
    
    print("\nVerifying database setup...")
    
    try:
        # Check database exists
        cursor.execute("SHOW DATABASES LIKE 'PMC_PATIENTS'")
        if cursor.fetchone():
            print("  ✓ Database PMC_PATIENTS exists")
        else:
            print("  ✗ Database PMC_PATIENTS not found")
            return False
        
        # Check table exists and has data
        cursor.execute("USE DATABASE PMC_PATIENTS")
        cursor.execute("USE SCHEMA PMC_PATIENTS")
        cursor.execute("SELECT COUNT(*) FROM PMC_PATIENTS")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"  ✓ Table PMC_PATIENTS has {count:,} records")
        else:
            print("  ⚠ Table PMC_PATIENTS exists but has no data")
        
        # Show sample data
        cursor.execute("SELECT PATIENT_ID, PATIENT_TITLE, AGE, GENDER FROM PMC_PATIENTS LIMIT 3")
        print("\nSample data:")
        for row in cursor.fetchall():
            print(f"  Patient {row[0]}: {row[1][:50]}... (Age: {row[2]}, Gender: {row[3]})")
        
        cursor.close()
        return True
        
    except Exception as e:
        print(f"  ✗ Error during verification: {str(e)}")
        cursor.close()
        return False

def main():
    print("="*70)
    print("PMC Patients Database Setup")
    print("="*70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Find the project root and files
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    sql_file = project_root / "sql" / "00_setup_pmc_patients_database.sql"
    csv_file = project_root / "Data" / "PMC-Patients.csv"
    
    print(f"Project root: {project_root}")
    print(f"SQL script: {sql_file}")
    print(f"CSV file: {csv_file}")
    
    # Get connection
    conn = get_connection()
    if not conn:
        print("\n❌ Setup failed - could not connect to Snowflake")
        return 1
    
    try:
        # Execute SQL setup
        print("\n" + "-"*50)
        print("Step 1: Creating database objects...")
        success, errors = execute_sql_file(conn, str(sql_file))
        print(f"SQL execution: {success} successful, {errors} errors")
        
        if errors > 0:
            print("⚠ Some SQL errors occurred, but continuing with data loading...")
        
        # Upload and load CSV data
        print("\n" + "-"*50)
        print("Step 2: Loading CSV data...")
        csv_success = upload_and_load_csv(conn, str(csv_file))
        
        # Verify setup
        print("\n" + "-"*50)
        print("Step 3: Verifying setup...")
        verify_success = verify_setup(conn)
        
        # Summary
        print("\n" + "="*70)
        if csv_success and verify_success and errors == 0:
            print("✅ PMC Patients database setup completed successfully!")
            print("\nYour database is ready to use. You can now:")
            print("  1. Connect to PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS")
            print("  2. Query patient data for analysis")
            print("  3. Integrate with the Healthcare AI Demo application")
        else:
            print("⚠ Setup completed with some issues.")
            print("Check the messages above for details.")
        
        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        return 0 if (csv_success and verify_success and errors == 0) else 1
        
    finally:
        conn.close()

if __name__ == "__main__":
    exit(main())
