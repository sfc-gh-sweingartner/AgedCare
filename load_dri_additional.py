import json
import os
import snowflake.connector

conn = snowflake.connector.connect(connection_name=os.getenv("SNOWFLAKE_CONNECTION_NAME") or "devrel")

def load_json_with_nan(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    content = content.replace(': NaN', ': null')
    return json.loads(content)

base_path = "/Users/sweingartner/CoCo/AgedCare/Confidential/DRI_Additional"

cursor = conn.cursor()
cursor.execute("DELETE FROM AGEDCARE.STAGING.REF_DRI_CLINICAL_BUSINESS_RULES")
cursor.execute("DELETE FROM AGEDCARE.STAGING.REF_DRI_KEYWORD_MASTER_LIST")

business_rules = load_json_with_nan(f"{base_path}/dri_business_rules_template.json")
cursor.execute(
    "INSERT INTO AGEDCARE.STAGING.REF_DRI_CLINICAL_BUSINESS_RULES (FILE_NAME, DATA) SELECT %s, PARSE_JSON(%s)",
    ('dri_business_rules_template.json', json.dumps(business_rules))
)
print("Loaded business rules template")

keyword_list = load_json_with_nan(f"{base_path}/dri_master_keyword_list.json")
cursor.execute(
    "INSERT INTO AGEDCARE.STAGING.REF_DRI_KEYWORD_MASTER_LIST (FILE_NAME, DATA) SELECT %s, PARSE_JSON(%s)",
    ('dri_master_keyword_list.json', json.dumps(keyword_list))
)
print("Loaded keyword master list")

cursor.execute("SELECT COUNT(*) FROM AGEDCARE.STAGING.REF_DRI_CLINICAL_BUSINESS_RULES")
print(f"Business rules rows: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM AGEDCARE.STAGING.REF_DRI_KEYWORD_MASTER_LIST")
print(f"Keyword list rows: {cursor.fetchone()[0]}")

cursor.close()
conn.close()
print("Done!")
