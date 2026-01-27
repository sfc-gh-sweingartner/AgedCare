"""
Recreate Cortex Search service on the patient subset
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.connection_helper import get_snowflake_connection
import time

def main():
    print("="*60)
    print("Recreating Cortex Search Service (PMC_PATIENTS)")
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
        
        # Check eligible PMC records
        cursor.execute("SELECT COUNT(*) FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS WHERE PATIENT_NOTES IS NOT NULL AND LENGTH(PATIENT_NOTES) > 50")
        count = cursor.fetchone()[0]
        print(f"PMC_PATIENTS contains {count} eligible records")
        if count == 0:
            print("❌ No eligible data in PMC_PATIENTS table!")
            return
        
        # Drop existing service
        print("\nDropping existing Cortex Search service...")
        cursor.execute("DROP CORTEX SEARCH SERVICE IF EXISTS patient_search_service")
        print("✓ Service dropped")
        
        # Wait before recreating
        print("Waiting 5 seconds before recreating...")
        time.sleep(5)
        
        # Create new service targeting PMC_PATIENTS
        print("\nCreating new Cortex Search service...")
        create_sql = """
        CREATE OR REPLACE CORTEX SEARCH SERVICE patient_search_service
        ON PATIENT_NOTES
        WAREHOUSE = CORTEX_SEARCH_WH
        TARGET_LAG = '1 hour'
        AS (
            SELECT 
                PATIENT_NOTES,
                PATIENT_ID,
                PATIENT_UID,
                PATIENT_TITLE,
                AGE,
                GENDER
            FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
            WHERE PATIENT_NOTES IS NOT NULL AND LENGTH(PATIENT_NOTES) > 50
        )
        """
        
        cursor.execute(create_sql)
        print("✓ Cortex Search service created successfully!")
        
        # Check service status
        print("\nChecking service status...")
        cursor.execute("""
            SHOW CORTEX SEARCH SERVICES LIKE 'patient_search_service'
        """)
        
        result = cursor.fetchone()
        if result:
            print(f"Service Name: {result[0]}")
            print(f"Status: {result[3]}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()