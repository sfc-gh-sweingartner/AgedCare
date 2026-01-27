"""
Healthcare AI Demo - Deployment Validation Script
===============================================

This script validates that the Healthcare AI Demo has been deployed correctly
and all components are working as expected.

Usage:
    python scripts/validate_deployment.py
"""

import snowflake.connector
import tomli
import os
import sys
from datetime import datetime
from pathlib import Path

def get_connection():
    """Get Snowflake connection"""
    try:
        # Try environment variables first
        if all(os.getenv(var) for var in ['SNOWFLAKE_ACCOUNT', 'SNOWFLAKE_USER', 'SNOWFLAKE_PASSWORD']):
            conn_params = {
                'account': os.getenv('SNOWFLAKE_ACCOUNT'),
                'user': os.getenv('SNOWFLAKE_USER'), 
                'password': os.getenv('SNOWFLAKE_PASSWORD'),
                'role': os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
                'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE')
            }
        else:
            config_path = os.path.expanduser('~/.snowflake/config.toml')
            if not os.path.exists(config_path):
                print(f"❌ Config file not found at {config_path}")
                return None
                
            with open(config_path, 'rb') as f:
                config = tomli.load(f)
            
            default_conn = config.get('default_connection_name')
            conn_params = config.get('connections', {}).get(default_conn)
        
        return snowflake.connector.connect(**conn_params)
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return None

def validate_pmc_database(cursor):
    """Validate PMC_PATIENTS database"""
    print("\n🔍 Validating PMC_PATIENTS Database")
    print("-" * 40)
    
    try:
        cursor.execute("SELECT COUNT(*) FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS")
        count = cursor.fetchone()[0]
        print(f"✅ PMC_PATIENTS table: {count:,} records")
        
        if count == 0:
            print("⚠️  Warning: No data found in PMC_PATIENTS table")
            return False
            
        # Test sample data
        cursor.execute("""
            SELECT PATIENT_ID, PATIENT_TITLE, AGE, GENDER 
            FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS 
            WHERE PATIENT_NOTES IS NOT NULL 
            LIMIT 3
        """)
        
        samples = cursor.fetchall()
        print("📋 Sample records:")
        for row in samples:
            title = row[1][:50] + "..." if len(row[1]) > 50 else row[1]
            print(f"   • Patient {row[0]}: {title} (Age: {row[2]}, Gender: {row[3]})")
            
        return True
        
    except Exception as e:
        print(f"❌ PMC_PATIENTS validation failed: {str(e)}")
        return False

def validate_healthcare_demo_database(cursor):
    """Validate HEALTHCARE_DEMO database"""
    print("\n🔍 Validating HEALTHCARE_DEMO Database")
    print("-" * 40)
    
    try:
        cursor.execute("USE DATABASE HEALTHCARE_DEMO")
        cursor.execute("USE SCHEMA MEDICAL_NOTES")
        
        # Check core tables
        tables = [
            ("PATIENT_ANALYSIS", "Pre-computed analysis results"),
            ("REALTIME_ANALYSIS_LOG", "Real-time processing log"),
            ("COHORT_INSIGHTS", "Population health insights"),
            ("PHYSICIAN_INSIGHTS", "Physician workflow optimization"),
            ("PROCESSING_STATUS", "Batch processing tracking"),
            ("DEMO_SCENARIOS", "Pre-configured demo scenarios"),
            ("MEDICATION_ANALYSIS", "Drug safety analysis"),
            ("COST_ANALYSIS", "Cost analysis results"),
            ("PROCEDURE_COSTS", "Procedure cost reference"),
            ("DRUG_INTERACTIONS_REFERENCE", "Drug interactions reference")
        ]
        
        success = True
        for table_name, description in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"✅ {table_name}: {count} records - {description}")
            except Exception as e:
                print(f"❌ {table_name}: Failed - {str(e)}")
                success = False
        
        return success
        
    except Exception as e:
        print(f"❌ HEALTHCARE_DEMO validation failed: {str(e)}")
        return False

def validate_stored_procedures(cursor):
    """Validate stored procedures"""
    print("\n🔍 Validating Stored Procedures")
    print("-" * 40)
    
    try:
        cursor.execute("USE DATABASE HEALTHCARE_DEMO")
        cursor.execute("USE SCHEMA MEDICAL_NOTES")
        
        cursor.execute("SHOW PROCEDURES LIKE 'BATCH_PROCESS_PATIENTS'")
        procedures = cursor.fetchall()
        
        if procedures:
            print("✅ BATCH_PROCESS_PATIENTS: Available")
            print("   • Handles AI batch processing of patient notes")
            print("   • Supports multiple AI models and use cases")
            return True
        else:
            print("❌ BATCH_PROCESS_PATIENTS: Not found")
            return False
            
    except Exception as e:
        print(f"❌ Stored procedure validation failed: {str(e)}")
        return False

def validate_cortex_ai(cursor):
    """Validate Cortex AI functionality"""
    print("\n🔍 Validating Cortex AI")
    print("-" * 40)
    
    try:
        # Test basic AI functionality
        cursor.execute("""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'llama3.1-8b',
                'Reply with exactly: AI_TEST_SUCCESS'
            )
        """)
        
        response = cursor.fetchone()[0]
        if 'AI_TEST_SUCCESS' in response.upper():
            print("✅ Cortex AI (LLaMA 3.1 8B): Working")
        else:
            print(f"⚠️  Cortex AI responded but output unexpected: {response}")
        
        # Test Claude model
        try:
            cursor.execute("""
                SELECT SNOWFLAKE.CORTEX.COMPLETE(
                    'claude-3-sonnet',
                    'Reply with exactly: CLAUDE_TEST_SUCCESS'
                )
            """)
            
            response = cursor.fetchone()[0]
            if 'CLAUDE_TEST_SUCCESS' in response.upper():
                print("✅ Cortex AI (Claude 3 Sonnet): Working")
            else:
                print("⚠️  Claude model available but unexpected output")
        except:
            print("⚠️  Claude 3 Sonnet not available (optional)")
        
        return True
        
    except Exception as e:
        print(f"❌ Cortex AI validation failed: {str(e)}")
        print("   • Ensure Cortex features are enabled on your account")
        print("   • Check that your role has AI function permissions")
        return False

def validate_demo_scenarios(cursor):
    """Validate demo scenarios"""
    print("\n🔍 Validating Demo Scenarios")
    print("-" * 40)
    
    try:
        cursor.execute("USE DATABASE HEALTHCARE_DEMO")
        cursor.execute("USE SCHEMA MEDICAL_NOTES")
        
        cursor.execute("SELECT COUNT(*) FROM DEMO_SCENARIOS")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"✅ Demo scenarios: {count} available")
            
            cursor.execute("""
                SELECT SCENARIO_NAME, SCENARIO_TYPE, DESCRIPTION 
                FROM DEMO_SCENARIOS 
                ORDER BY SCENARIO_ID
            """)
            
            scenarios = cursor.fetchall()
            for scenario in scenarios:
                print(f"   • {scenario[0]} ({scenario[1]})")
                print(f"     {scenario[2]}")
            
            return True
        else:
            print("❌ No demo scenarios found")
            return False
            
    except Exception as e:
        print(f"❌ Demo scenarios validation failed: {str(e)}")
        return False

def validate_streamlit_requirements():
    """Validate Streamlit application requirements"""
    print("\n🔍 Validating Streamlit Requirements")
    print("-" * 40)
    
    project_root = Path(__file__).parent.parent
    
    # Check main files exist
    required_files = [
        "src/streamlit_main.py",
        "src/connection_helper.py",
        "requirements.txt"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {file_path}: Found")
        else:
            print(f"❌ {file_path}: Missing")
            missing_files.append(file_path)
    
    # Check page files
    pages_dir = project_root / "src" / "pages"
    if pages_dir.exists():
        page_files = list(pages_dir.glob("*.py"))
        print(f"✅ Streamlit pages: {len(page_files)} found")
        for page in sorted(page_files):
            print(f"   • {page.name}")
    else:
        print("❌ src/pages directory missing")
        missing_files.append("src/pages/")
    
    return len(missing_files) == 0

def run_sample_query(cursor):
    """Run a sample healthcare AI query"""
    print("\n🔍 Testing Sample Healthcare AI Query")
    print("-" * 40)
    
    try:
        cursor.execute("""
            SELECT 
                p.PATIENT_ID,
                p.PATIENT_TITLE,
                LEFT(p.PATIENT_NOTES, 200) as NOTES_PREVIEW
            FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS p
            WHERE p.PATIENT_NOTES IS NOT NULL
            AND LENGTH(p.PATIENT_NOTES) > 100
            LIMIT 1
        """)
        
        sample = cursor.fetchone()
        if sample:
            print(f"📋 Sample Patient: {sample[0]}")
            print(f"   Title: {sample[1]}")
            print(f"   Notes Preview: {sample[2]}...")
            
            # Try a simple AI analysis
            cursor.execute(f"""
                SELECT SNOWFLAKE.CORTEX.COMPLETE(
                    'llama3.1-8b',
                    'Summarize this medical case in one sentence: {sample[2]}'
                ) as AI_SUMMARY
            """)
            
            ai_summary = cursor.fetchone()[0]
            print(f"   AI Summary: {ai_summary}")
            print("✅ Sample AI analysis completed successfully")
            
            return True
        else:
            print("❌ No suitable sample patient found")
            return False
            
    except Exception as e:
        print(f"❌ Sample query failed: {str(e)}")
        return False

def main():
    """Main validation function"""
    print("🏥 Healthcare AI Demo - Deployment Validation")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Connect to Snowflake
    print("\n🔗 Establishing Connection")
    print("-" * 40)
    conn = get_connection()
    if not conn:
        print("❌ Cannot validate - connection failed")
        return 1
    
    print("✅ Connected to Snowflake successfully")
    cursor = conn.cursor()
    
    # Run validation tests
    validation_results = []
    
    validation_results.append(validate_pmc_database(cursor))
    validation_results.append(validate_healthcare_demo_database(cursor))
    validation_results.append(validate_stored_procedures(cursor))
    validation_results.append(validate_cortex_ai(cursor))
    validation_results.append(validate_demo_scenarios(cursor))
    validation_results.append(validate_streamlit_requirements())
    validation_results.append(run_sample_query(cursor))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(validation_results)
    total = len(validation_results)
    
    if passed == total:
        print("🎉 ALL VALIDATION TESTS PASSED!")
        print("\n✅ Your Healthcare AI Demo is fully deployed and ready to use!")
        print("\n🚀 Next Steps:")
        print("   1. Start the Streamlit app: streamlit run src/streamlit_main.py")
        print("   2. Open http://localhost:8501 in your browser")
        print("   3. Explore the demo pages and AI capabilities")
        success = True
    else:
        print(f"⚠️  VALIDATION INCOMPLETE: {passed}/{total} tests passed")
        print("\n❌ Issues found - please review the errors above")
        print("   Consider re-running the deployment script:")
        print("   python scripts/deploy_healthcare_demo.py")
        success = False
    
    print("\n" + "=" * 60)
    print("⚠️  Remember: This is a demo system - not for clinical use!")
    print("=" * 60)
    
    conn.close()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
