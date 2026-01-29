import pandas as pd
import snowflake.connector
import os
from datetime import datetime

EXCEL_PATH = '/Users/sweingartner/CoCo/AgedCare/Confidential/DRI/data/De-identified - 871 - Integration.xlsx'

def get_connection():
    return snowflake.connector.connect(
        connection_name=os.getenv("SNOWFLAKE_CONNECTION_NAME") or "DEMO_SWEINGARTNER"
    )

def convert_dates(df, date_cols):
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

def load_demo_data():
    print(f"Loading demo data from {EXCEL_PATH}")
    
    xls = pd.ExcelFile(EXCEL_PATH)
    print(f"Available sheets: {xls.sheet_names}")
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("USE DATABASE AGEDCARE")
    cur.execute("USE SCHEMA AGEDCARE")
    
    from snowflake.connector.pandas_tools import write_pandas
    
    df = pd.read_excel(EXCEL_PATH, sheet_name='ACTIVE_RESIDENT_MEDICAL_PROFILE')
    df.columns = [c.upper().replace(' ', '_') for c in df.columns]
    bool_cols = ['HAS_UNCODED_ALLERGIES', 'HAS_GLUTEN_INTOLERANCE']
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: True if x == 1 or x == '1' or x == True else (False if x == 0 or x == '0' or x == False else None))
    df = convert_dates(df, ['EVENT_DATE'])
    cur.execute("TRUNCATE TABLE IF EXISTS AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICAL_PROFILE")
    success, nchunks, nrows, _ = write_pandas(conn, df, 'ACTIVE_RESIDENT_MEDICAL_PROFILE', database='AGEDCARE', schema='AGEDCARE', auto_create_table=False)
    print(f"ACTIVE_RESIDENT_MEDICAL_PROFILE: {nrows} rows")
    
    df = pd.read_excel(EXCEL_PATH, sheet_name='ACTIVE_RESIDENT_ASSESSMENT_FORM')
    df.columns = [c.upper().replace(' ', '_') for c in df.columns]
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).replace('nan', '').replace('NaT', '')
    df = convert_dates(df, ['EVENT_DATE'])
    cur.execute("TRUNCATE TABLE IF EXISTS AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_ASSESSMENT_FORMS")
    success, nchunks, nrows, _ = write_pandas(conn, df, 'ACTIVE_RESIDENT_ASSESSMENT_FORMS', database='AGEDCARE', schema='AGEDCARE', auto_create_table=False)
    print(f"ACTIVE_RESIDENT_ASSESSMENT_FORMS: {nrows} rows")
    
    df = pd.read_excel(EXCEL_PATH, sheet_name='ACTIVE_RESIDENT_MEDICATION')
    df.columns = [c.upper().replace(' ', '_') for c in df.columns]
    df = convert_dates(df, ['MED_START_DATE', 'MED_END_DATE', 'UPDATED_DATE'])
    if 'MED_START_DATE' in df.columns:
        df['MED_START_DATE'] = df['MED_START_DATE'].dt.date
    cur.execute("TRUNCATE TABLE IF EXISTS AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION")
    success, nchunks, nrows, _ = write_pandas(conn, df, 'ACTIVE_RESIDENT_MEDICATION', database='AGEDCARE', schema='AGEDCARE', auto_create_table=False)
    print(f"ACTIVE_RESIDENT_MEDICATION: {nrows} rows")
    
    df = pd.read_excel(EXCEL_PATH, sheet_name='ACTIVE_RESIDENT_NOTES')
    df.columns = [c.upper().replace(' ', '_') for c in df.columns]
    df = convert_dates(df, ['EVENT_DATE'])
    cur.execute("TRUNCATE TABLE IF EXISTS AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES")
    success, nchunks, nrows, _ = write_pandas(conn, df, 'ACTIVE_RESIDENT_NOTES', database='AGEDCARE', schema='AGEDCARE', auto_create_table=False)
    print(f"ACTIVE_RESIDENT_NOTES: {nrows} rows")
    
    df = pd.read_excel(EXCEL_PATH, sheet_name='ACTIVE_RESIDENT_OBSERVATIONS')
    df.columns = [c.upper().replace(' ', '_') for c in df.columns]
    for col in ['OBSERVATION_VALUE']:
        if col in df.columns:
            df[col] = df[col].astype(str).replace('nan', '')
    df = convert_dates(df, ['EVENT_DATE'])
    cur.execute("TRUNCATE TABLE IF EXISTS AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS")
    success, nchunks, nrows, _ = write_pandas(conn, df, 'ACTIVE_RESIDENT_OBSERVATIONS', database='AGEDCARE', schema='AGEDCARE', auto_create_table=False)
    print(f"ACTIVE_RESIDENT_OBSERVATIONS: {nrows} rows")
    
    df = pd.read_excel(EXCEL_PATH, sheet_name='ACTIVE_RESIDENT_OBSERVATION_GRO')
    df.columns = [c.upper().replace(' ', '_') for c in df.columns]
    df = convert_dates(df, ['EVENT_DATE'])
    cur.execute("TRUNCATE TABLE IF EXISTS AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATION_GROUP")
    success, nchunks, nrows, _ = write_pandas(conn, df, 'ACTIVE_RESIDENT_OBSERVATION_GROUP', database='AGEDCARE', schema='AGEDCARE', auto_create_table=False)
    print(f"ACTIVE_RESIDENT_OBSERVATION_GROUP: {nrows} rows")
    
    conn.close()
    print("\nDemo data loaded successfully!")

if __name__ == "__main__":
    load_demo_data()
