"""
Healthcare AI Demo - Complete Deployment Script
==============================================

This script automates the complete deployment of the Healthcare AI Demo solution including:
- PMC_PATIENTS database and data loading
- HEALTHCARE_DEMO database with all analysis tables
- AI batch processing procedures
- Demo scenarios and reference data
- Cortex Search configuration
- Complete validation and testing

Author: Healthcare AI Demo Team
"""

import snowflake.connector
import tomli
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class HealthcareDemoDeployment:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.conn = None
        self.cursor = None
        self.project_root = Path(__file__).parent.parent
        self.errors = []
        self.warnings = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamps and levels"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "WARNING": "⚠️",
            "ERROR": "❌",
            "STEP": "🔧"
        }.get(level, "ℹ️")
        
        if self.verbose or level in ["SUCCESS", "ERROR", "STEP"]:
            print(f"[{timestamp}] {prefix} {message}")
            
        if level == "ERROR":
            self.errors.append(message)
        elif level == "WARNING":
            self.warnings.append(message)

    def get_connection(self) -> bool:
        """Establish connection to Snowflake"""
        try:
            # Try environment variables first
            if all(os.getenv(var) for var in ['SNOWFLAKE_ACCOUNT', 'SNOWFLAKE_USER', 'SNOWFLAKE_PASSWORD']):
                self.log("Using environment variables for connection", "INFO")
                conn_params = {
                    'account': os.getenv('SNOWFLAKE_ACCOUNT'),
                    'user': os.getenv('SNOWFLAKE_USER'),
                    'password': os.getenv('SNOWFLAKE_PASSWORD'),
                    'role': os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
                    'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE')
                }
            else:
                # Fall back to config file
                config_path = os.path.expanduser('~/.snowflake/config.toml')
                if not os.path.exists(config_path):
                    self.log(f"Config file not found at {config_path}", "ERROR")
                    return False
                
                with open(config_path, 'rb') as f:
                    config = tomli.load(f)
                
                default_conn = config.get('default_connection_name')
                if not default_conn:
                    self.log("No default connection specified in config.toml", "ERROR")
                    return False
                    
                conn_params = config.get('connections', {}).get(default_conn)
                if not conn_params:
                    self.log(f"Connection '{default_conn}' not found in config.toml", "ERROR")
                    return False
            
            self.conn = snowflake.connector.connect(**conn_params)
            self.cursor = self.conn.cursor()
            self.log("Connection established successfully", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Failed to connect: {str(e)}", "ERROR")
            return False

    def execute_sql_file(self, filepath: Path, description: str) -> Tuple[int, int]:
        """Execute SQL statements from a file"""
        self.log(f"Executing {description}: {filepath.name}", "STEP")
        
        if not filepath.exists():
            self.log(f"SQL file not found: {filepath}", "ERROR")
            return 0, 1
        
        with open(filepath, 'r') as f:
            sql_content = f.read()
        
        # Split into statements, handling complex SQL with comments
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
            
            # Check if statement is complete
            if line.endswith(';'):
                statements.append(current_statement.strip())
                current_statement = ""
        
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements):
            if not statement:
                continue
            
            # Extract description for logging
            stmt_preview = ' '.join(statement.split()[:4])
            
            try:
                self.log(f"  Executing: {stmt_preview}...", "INFO")
                self.cursor.execute(statement)
                success_count += 1
            except Exception as e:
                error_msg = f"Error in {stmt_preview}: {str(e)}"
                self.log(f"  {error_msg}", "ERROR")
                error_count += 1
                # Continue with other statements for non-critical errors
        
        self.log(f"  Completed: {success_count} successful, {error_count} errors", "INFO")
        return success_count, error_count

    def setup_pmc_patients_database(self) -> bool:
        """Set up the PMC_PATIENTS database and load CSV data"""
        self.log("Setting up PMC_PATIENTS database", "STEP")
        
        # Execute PMC database setup SQL
        sql_file = self.project_root / "sql" / "00_setup_pmc_patients_database.sql"
        success, errors = self.execute_sql_file(sql_file, "PMC Patients database setup")
        
        if errors > 0:
            self.log(f"PMC database setup had {errors} errors", "WARNING")
        
        # Load CSV data
        csv_file = self.project_root / "Data" / "PMC-Patients.csv"
        if not csv_file.exists():
            self.log(f"CSV file not found: {csv_file}", "ERROR")
            return False
        
        try:
            self.log("Uploading CSV data to Snowflake", "INFO")
            
            # Switch to PMC database context
            self.cursor.execute("USE DATABASE PMC_PATIENTS")
            self.cursor.execute("USE SCHEMA PMC_PATIENTS")
            
            # Upload CSV file
            put_command = f"PUT 'file://{csv_file}' @PMC_DATA_STAGE AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
            self.cursor.execute(put_command)
            self.log("  CSV file uploaded successfully", "SUCCESS")
            
            # Load data into table
            copy_command = """
            COPY INTO PMC_PATIENTS (
                PATIENT_ID, PATIENT_UID, PMID, FILE_PATH, PATIENT_TITLE,
                PATIENT_NOTES, AGE, GENDER, RELEVANT_ARTICLES, SIMILAR_PATIENTS
            )
            FROM (
                SELECT 
                    TRY_CAST($1 AS NUMBER), $2, TRY_CAST($3 AS NUMBER), $4, $5,
                    $6, $7, $8, $9, $10
                FROM @PMC_DATA_STAGE
            )
            FILE_FORMAT = CSV_FORMAT
            ON_ERROR = 'CONTINUE'
            PURGE = TRUE
            """
            
            self.cursor.execute(copy_command)
            self.log("  Data loaded successfully", "SUCCESS")
            
            # Verify data load
            self.cursor.execute("SELECT COUNT(*) FROM PMC_PATIENTS")
            count = self.cursor.fetchone()[0]
            self.log(f"  Total records loaded: {count:,}", "INFO")
            
            if count == 0:
                self.log("No data was loaded - check CSV file format", "ERROR")
                return False
            
            return True
            
        except Exception as e:
            self.log(f"Error loading CSV data: {str(e)}", "ERROR")
            return False

    def setup_healthcare_demo_database(self) -> bool:
        """Set up the HEALTHCARE_DEMO database and all analysis tables"""
        self.log("Setting up HEALTHCARE_DEMO database", "STEP")
        
        # Execute database setup scripts in order
        scripts = [
            ("sql/01_create_database_objects.sql", "Core database objects"),
            ("sql/02_create_subset_and_new_tables.sql", "Analysis tables and reference data"),
            ("sql/03_create_batch_processing_procedure.sql", "AI batch processing procedures")
        ]
        
        total_errors = 0
        for script_path, description in scripts:
            sql_file = self.project_root / script_path
            success, errors = self.execute_sql_file(sql_file, description)
            total_errors += errors
        
        if total_errors > 0:
            self.log(f"Healthcare demo setup had {total_errors} total errors", "WARNING")
        else:
            self.log("Healthcare demo database setup completed successfully", "SUCCESS")
        
        return total_errors == 0

    def validate_deployment(self) -> bool:
        """Validate that all components are working correctly"""
        self.log("Validating deployment", "STEP")
        
        validation_passed = True
        
        try:
            # Check PMC_PATIENTS database
            self.log("Checking PMC_PATIENTS database...", "INFO")
            self.cursor.execute("SELECT COUNT(*) FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS")
            pmc_count = self.cursor.fetchone()[0]
            
            if pmc_count > 0:
                self.log(f"  ✅ PMC_PATIENTS: {pmc_count:,} records", "SUCCESS")
            else:
                self.log("  ❌ PMC_PATIENTS: No data found", "ERROR")
                validation_passed = False
            
            # Check HEALTHCARE_DEMO database tables
            self.log("Checking HEALTHCARE_DEMO database...", "INFO")
            self.cursor.execute("USE DATABASE HEALTHCARE_DEMO")
            self.cursor.execute("USE SCHEMA MEDICAL_NOTES")
            
            demo_tables = [
                "PATIENT_ANALYSIS",
                "REALTIME_ANALYSIS_LOG", 
                "COHORT_INSIGHTS",
                "PHYSICIAN_INSIGHTS",
                "PROCESSING_STATUS",
                "DEMO_SCENARIOS",
                "MEDICATION_ANALYSIS",
                "COST_ANALYSIS",
                "PROCEDURE_COSTS",
                "DRUG_INTERACTIONS_REFERENCE"
            ]
            
            for table in demo_tables:
                try:
                    self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = self.cursor.fetchone()[0]
                    self.log(f"  ✅ {table}: Available ({count} records)", "INFO")
                except Exception as e:
                    self.log(f"  ❌ {table}: Not found or inaccessible", "ERROR")
                    validation_passed = False
            
            # Test Cortex AI functionality
            self.log("Testing Cortex AI functionality...", "INFO")
            try:
                self.cursor.execute("""
                    SELECT SNOWFLAKE.CORTEX.COMPLETE(
                        'llama3.1-8b',
                        'Reply with exactly: CORTEX_AI_WORKING'
                    )
                """)
                ai_response = self.cursor.fetchone()[0]
                if 'CORTEX_AI_WORKING' in ai_response.upper():
                    self.log("  ✅ Cortex AI is functional", "SUCCESS")
                else:
                    self.log("  ⚠️ Cortex AI responded but with unexpected output", "WARNING")
            except Exception as e:
                self.log(f"  ❌ Cortex AI not available: {str(e)}", "ERROR")
                validation_passed = False
            
            # Test stored procedures
            self.log("Checking stored procedures...", "INFO")
            try:
                self.cursor.execute("SHOW PROCEDURES LIKE 'BATCH_PROCESS_PATIENTS'")
                if self.cursor.fetchone():
                    self.log("  ✅ Batch processing procedure available", "SUCCESS")
                else:
                    self.log("  ❌ Batch processing procedure not found", "ERROR")
                    validation_passed = False
            except Exception as e:
                self.log(f"  ❌ Error checking procedures: {str(e)}", "ERROR")
                validation_passed = False
            
            # Test sample data access
            self.log("Testing sample data access...", "INFO")
            try:
                self.cursor.execute("""
                    SELECT PATIENT_ID, PATIENT_TITLE, AGE, GENDER 
                    FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS 
                    LIMIT 3
                """)
                sample_data = self.cursor.fetchall()
                self.log("  Sample patient records:", "INFO")
                for row in sample_data:
                    title_preview = row[1][:50] + "..." if len(row[1]) > 50 else row[1]
                    self.log(f"    Patient {row[0]}: {title_preview} (Age: {row[2]}, Gender: {row[3]})", "INFO")
                self.log("  ✅ Sample data access working", "SUCCESS")
            except Exception as e:
                self.log(f"  ❌ Error accessing sample data: {str(e)}", "ERROR")
                validation_passed = False
            
        except Exception as e:
            self.log(f"Validation failed with error: {str(e)}", "ERROR")
            validation_passed = False
        
        if validation_passed:
            self.log("🎉 All validation checks passed!", "SUCCESS")
        else:
            self.log("❌ Some validation checks failed", "ERROR")
            
        return validation_passed

    def display_summary(self):
        """Display deployment summary"""
        print("\n" + "="*80)
        print("🏥 HEALTHCARE AI DEMO - DEPLOYMENT SUMMARY")
        print("="*80)
        
        if not self.errors:
            print("✅ DEPLOYMENT SUCCESSFUL!")
            print("\nYour Healthcare AI Demo is ready to use!")
            print("\n🚀 Next Steps:")
            print("  1. Start the Streamlit application:")
            print("     streamlit run src/streamlit_main.py")
            print("\n  2. Navigate to http://localhost:8501")
            print("\n  3. Explore the demo pages:")
            print("     • Data Foundation - Explore the PMC patients dataset")
            print("     • Clinical Decision Support - AI-powered diagnosis tools")
            print("     • Prompt and Model Testing - Real-time AI experimentation")
            print("     • Population Health Analytics - Cohort analysis")
            print("     • Cost Analysis - Healthcare cost prediction")
            print("     • And 4 more specialized healthcare AI use cases!")
            
            print("\n📊 Deployed Components:")
            print("     • PMC_PATIENTS database with 167K+ medical cases")
            print("     • HEALTHCARE_DEMO database with analysis tables")
            print("     • AI batch processing procedures")
            print("     • Cortex Search for fast patient retrieval")
            print("     • Demo scenarios for presentations")
            
        else:
            print("❌ DEPLOYMENT COMPLETED WITH ERRORS")
            print(f"\n{len(self.errors)} error(s) encountered:")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print(f"\n⚠️  {len(self.warnings)} warning(s):")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        print("\n" + "="*80)
        print("⚠️  IMPORTANT: This is a demonstration system for educational")
        print("   purposes only. Do not use for actual clinical decisions.")
        print("="*80)

    def deploy(self, update_mode: bool = False) -> bool:
        """Execute the complete deployment process"""
        start_time = datetime.now()
        
        print("🏥 Healthcare AI Demo - Complete Deployment")
        print("=" * 50)
        print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Project root: {self.project_root}")
        print(f"Mode: {'Update' if update_mode else 'Fresh deployment'}")
        print()
        
        # Step 1: Connect to Snowflake
        if not self.get_connection():
            return False
        
        # Step 2: Setup PMC_PATIENTS database
        if not self.setup_pmc_patients_database():
            self.log("PMC_PATIENTS setup failed - continuing anyway", "WARNING")
        
        # Step 3: Setup HEALTHCARE_DEMO database  
        if not self.setup_healthcare_demo_database():
            self.log("HEALTHCARE_DEMO setup failed", "ERROR")
        
        # Step 4: Validate deployment
        validation_success = self.validate_deployment()
        
        # Step 5: Display summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\nDeployment completed in {duration.total_seconds():.1f} seconds")
        self.display_summary()
        
        if self.conn:
            self.conn.close()
        
        return validation_success and len(self.errors) == 0

def main():
    parser = argparse.ArgumentParser(description='Deploy Healthcare AI Demo')
    parser.add_argument('--update', action='store_true', 
                       help='Update existing deployment')
    parser.add_argument('--verbose', action='store_true', default=True,
                       help='Enable verbose logging')
    parser.add_argument('--quiet', action='store_true',
                       help='Minimize output (only show errors and success)')
    
    args = parser.parse_args()
    
    # Handle verbose/quiet flags
    verbose = args.verbose and not args.quiet
    
    deployer = HealthcareDemoDeployment(verbose=verbose)
    
    try:
        success = deployer.deploy(update_mode=args.update)
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n❌ Deployment interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Deployment failed with unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
