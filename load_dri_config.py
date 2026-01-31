#!/usr/bin/env python3
import os
import json
import snowflake.connector

conn = snowflake.connector.connect(connection_name=os.getenv("SNOWFLAKE_CONNECTION_NAME") or "coco-snowflake")
cursor = conn.cursor()

with open("/Users/sweingartner/CoCo/AgedCare/Confidential/DRI_Additional/dri_master_keyword_list.json") as f:
    keywords_data = json.load(f)

for item in keywords_data:
    deficit_id = item["dri_deficit_id"]
    deficit_name = item["deficit_name"]
    keywords = json.dumps(item["keywords"])
    cursor.execute(f"""
        INSERT INTO AGEDCARE.AGEDCARE.DRI_KEYWORD_MASTER_LIST (DRI_DEFICIT_ID, DEFICIT_NAME, KEYWORDS)
        SELECT '{deficit_id}', '{deficit_name}', PARSE_JSON('{keywords}')
    """)

print(f"Loaded {len(keywords_data)} keyword entries")

with open("/Users/sweingartner/CoCo/AgedCare/Confidential/DRI_Additional/dri_business_rules_template.json") as f:
    rules_data = json.load(f)

rules_json = json.dumps(rules_data).replace("'", "''")
cursor.execute(f"""
    INSERT INTO AGEDCARE.AGEDCARE.DRI_CLINICAL_BUSINESS_RULES (CLIENT_NAME, CLIENT_SYSTEM_KEY, DRI_RULES)
    SELECT 'dri_config_template', 'SYS_Clinical_Manager_Brightwater_V_11_4', PARSE_JSON($${rules_data}$$)
""")
print("Loaded business rules")

cursor.execute("SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_KEYWORD_MASTER_LIST")
print(f"Keywords table rows: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_CLINICAL_BUSINESS_RULES")
print(f"Rules table rows: {cursor.fetchone()[0]}")

conn.close()
