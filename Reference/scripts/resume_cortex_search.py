"""
Resume the Cortex Search service if it's suspended
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.connection_helper import get_snowflake_connection

def main():
    print("="*60)
    print("Checking and Resuming Cortex Search Service")
    print("="*60)
    
    conn = get_snowflake_connection()
    if not conn:
        print("Failed to connect to Snowflake")
        return
    
    cursor = conn.cursor()
    
    try:
        # Use database and schema
        cursor.execute("USE DATABASE HEALTHCARE_DEMO")
        cursor.execute("USE SCHEMA MEDICAL_NOTES")
        
        # Check service status
        print("\nChecking service status...")
        cursor.execute("""
            SHOW CORTEX SEARCH SERVICES LIKE 'patient_search_service'
        """)
        
        result = cursor.fetchone()
        if result:
            # SHOW CORTEX SEARCH SERVICES returns multiple columns
            # Print all columns to understand the structure
            print(f"\nService details (all columns):")
            for i, val in enumerate(result):
                print(f"  Column {i}: {val}")
            
            service_name = result[1]
            print(f"\nService Name: {service_name}")
            
            # Always try to resume to ensure it's active
            print("\nAttempting to RESUME service...")
            try:
                cursor.execute("ALTER CORTEX SEARCH SERVICE patient_search_service RESUME")
                print("✓ RESUME command executed successfully!")
            except Exception as resume_err:
                if "already running" in str(resume_err).lower():
                    print("ℹ️  Service is already running")
                else:
                    print(f"⚠️  Resume warning: {resume_err}")
            
            # Wait a moment for the service to initialize
            import time
            print("\nWaiting 10 seconds for service to fully initialize...")
            time.sleep(10)
                
            # Test the service with a simple query
            print("\nTesting service with a sample query...")
            test_query = """
            SELECT PARSE_JSON(
                SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                    'patient_search_service',
                    '{"query": "cancer", "columns": ["PATIENT_ID", "PATIENT_TITLE"], "limit": 3}'
                )
            ) AS result
            """
            cursor.execute(test_query)
            test_result = cursor.fetchone()
            if test_result:
                print("✓ Service is responding to queries!")
                print(f"Sample result: {str(test_result[0])[:200]}...")
            else:
                print("⚠️  Service did not return results")
        else:
            print("❌ Service 'patient_search_service' not found!")
            print("\nYou may need to recreate the service. Run:")
            print("  python scripts/recreate_cortex_search.py")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
    
    print("\n" + "="*60)
    print("Done!")
    print("="*60)

if __name__ == "__main__":
    main()

