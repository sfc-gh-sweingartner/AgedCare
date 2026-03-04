# DRI Intelligence - Deployment Guide

## Overview
This guide covers deploying DRI Intelligence to a new Snowflake environment.

## Prerequisites
- Snowflake account with ACCOUNTADMIN role (or equivalent privileges)
- Snow CLI installed and configured (`snow --version`)
- Connection configured in `~/.snowflake/connections.toml`

## Deployment Steps

### Step 1: Configure Connection
Ensure you have a connection configured for your target environment:

```bash
# List available connections
snow connection list

# Test connection
snow connection test -c <CONNECTION_NAME>
```

### Step 2: Set SQL Variables
Before running SQL scripts, set these session variables:

```sql
SET database_name = 'AGEDCARE_TEST';   -- Your target database
SET schema_name = 'DRI';                -- Your target schema  
SET warehouse_name = 'COMPUTE_WH';      -- Your warehouse
SET compute_pool_name = 'DRI_COMPUTE_POOL';
SET external_access_name = 'ALLOW_ALL_ACCESS_INTEGRATION';
```

### Step 3: Create Infrastructure
Run `setup_infrastructure.sql` to create:
- Compute pool for SPCS container runtime
- External access integration for PyPI

```bash
snow sql -f deployment/setup_infrastructure.sql -c <CONNECTION_NAME>
```

### Step 4: Create Database Objects
Run `setup_database.sql` to create:
- Database and schema
- All source data tables (ACTIVE_RESIDENT_*)
- All DRI tables and views
- Stage for app files

```bash
snow sql -f deployment/setup_database.sql -c <CONNECTION_NAME>
```

### Step 5: Upload Config Data
Upload the CSV config files to the stage:

```bash
# From the AgedCare directory
snow stage copy Confidential/deployment/config_data/DRI_CLIENT_CONFIG.csv \
    @<DATABASE>.<SCHEMA>.DRI_STREAMLIT_STAGE/config --overwrite -c <CONNECTION_NAME>

snow stage copy Confidential/deployment/config_data/DRI_PROMPT_VERSIONS.csv \
    @<DATABASE>.<SCHEMA>.DRI_STREAMLIT_STAGE/config --overwrite -c <CONNECTION_NAME>

snow stage copy Confidential/deployment/config_data/DRI_RULES.csv \
    @<DATABASE>.<SCHEMA>.DRI_STREAMLIT_STAGE/config --overwrite -c <CONNECTION_NAME>

snow stage copy Confidential/deployment/config_data/DRI_CLIENT_RULE_ASSIGNMENTS.csv \
    @<DATABASE>.<SCHEMA>.DRI_STREAMLIT_STAGE/config --overwrite -c <CONNECTION_NAME>
```

### Step 6: Load Config Data
Run `load_config_data.sql` to load configuration:

```bash
snow sql -f deployment/load_config_data.sql -c <CONNECTION_NAME>
```

### Step 7: Configure snowflake.yml
Update `dri-intelligence/snowflake.yml` with your environment settings:

```yaml
definition_version: 2
entities:
  dri_intelligence:
    type: streamlit
    identifier:
      name: DRI_INTELLIGENCE
      database: AGEDCARE_TEST          # <-- Your database
      schema: DRI                       # <-- Your schema
    title: DRI Intelligence
    query_warehouse: COMPUTE_WH         # <-- Your warehouse
    compute_pool: DRI_COMPUTE_POOL      # <-- Your compute pool
    runtime_name: SYSTEM$ST_CONTAINER_RUNTIME_PY3_11
    external_access_integrations:
      - ALLOW_ALL_ACCESS_INTEGRATION    # <-- Your integration
    main_file: streamlit_app.py
    artifacts:
      - streamlit_app.py
      - pyproject.toml
      - uv.lock
      - src/__init__.py
      - src/connection_helper.py
      - src/dri_analysis.py
      - app_pages/__init__.py
      - app_pages/dashboard.py
      - app_pages/prompt_engineering.py
      - app_pages/batch_testing.py
      - app_pages/review_queue.py
      - app_pages/resident_history.py
      - app_pages/audit_results.py
      - app_pages/feedback_loop.py
      - app_pages/configuration.py
      - app_pages/comparison.py
      - app_pages/testing_tools.py
```

### Step 8: Deploy Streamlit App
Deploy using snow CLI (NOT SQL):

```bash
cd dri-intelligence
snow streamlit deploy -c <CONNECTION_NAME>

# For updates:
snow streamlit deploy --replace -c <CONNECTION_NAME>
```

### Step 9: Load Patient/Resident Data (Optional)
If you have demo resident data to test with, load it into the ACTIVE_RESIDENT_* tables.

**Option A: Using pre-exported CSV files**

1. Upload patient data CSVs to stage:
```bash
# From the AgedCare directory
for f in Confidential/deployment/patient_data/*.csv; do
    snow stage copy "$f" @<DATABASE>.<SCHEMA>.DRI_STREAMLIT_STAGE/patients \
        --overwrite -c <CONNECTION_NAME>
done
```

2. Run the load script:
```bash
snow sql -f deployment/load_patients.sql -c <CONNECTION_NAME>
```

**Option B: Export from another environment**

Export patient data from a source environment with date cleansing (handles corrupt timestamps):

```sql
-- In source environment, export each table with date cleansing
COPY INTO @<STAGE>/export/ACTIVE_RESIDENT_NOTES.csv
FROM ACTIVE_RESIDENT_NOTES
FILE_FORMAT = (TYPE = CSV FIELD_OPTIONALLY_ENCLOSED_BY = '"' COMPRESSION = NONE NULL_IF = (''))
OVERWRITE = TRUE SINGLE = TRUE HEADER = TRUE;

-- For tables with timestamp columns that may have invalid dates:
COPY INTO @<STAGE>/export/ACTIVE_RESIDENT_MEDICATION.csv
FROM (SELECT 
  * EXCLUDE (MED_END_DATE, UPDATED_DATE),
  CASE WHEN YEAR(MED_END_DATE) < 1900 OR YEAR(MED_END_DATE) > 2100 THEN NULL ELSE MED_END_DATE END AS MED_END_DATE,
  CASE WHEN YEAR(UPDATED_DATE) < 1900 OR YEAR(UPDATED_DATE) > 2100 THEN NULL ELSE UPDATED_DATE END AS UPDATED_DATE
FROM ACTIVE_RESIDENT_MEDICATION)
FILE_FORMAT = (TYPE = CSV FIELD_OPTIONALLY_ENCLOSED_BY = '"' COMPRESSION = NONE NULL_IF = (''))
OVERWRITE = TRUE SINGLE = TRUE HEADER = TRUE;
```

**Expected row counts after loading:**
| Table | Expected Rows |
|-------|--------------|
| ACTIVE_RESIDENT_NOTES | 632 |
| ACTIVE_RESIDENT_MEDICAL_PROFILE | 3 |
| ACTIVE_RESIDENT_MEDICATION | 124 |
| ACTIVE_RESIDENT_OBSERVATIONS | ~2026 |
| ACTIVE_RESIDENT_OBSERVATION_GROUP | 4 |
| ACTIVE_RESIDENT_ASSESSMENT_FORMS | 416 |

## Verification

### Check Database Objects
```sql
SELECT TABLE_NAME, TABLE_TYPE 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'DRI' 
ORDER BY TABLE_TYPE, TABLE_NAME;
```

### Check Config Data
```sql
SELECT 'DRI_CLIENT_CONFIG' AS TBL, COUNT(*) AS CNT FROM DRI_CLIENT_CONFIG
UNION ALL SELECT 'DRI_PROMPT_VERSIONS', COUNT(*) FROM DRI_PROMPT_VERSIONS
UNION ALL SELECT 'DRI_RULES', COUNT(*) FROM DRI_RULES
UNION ALL SELECT 'DRI_CLIENT_RULE_ASSIGNMENTS', COUNT(*) FROM DRI_CLIENT_RULE_ASSIGNMENTS;
```

### Check Streamlit App
```sql
SHOW STREAMLITS IN SCHEMA <DATABASE>.<SCHEMA>;
DESCRIBE STREAMLIT <DATABASE>.<SCHEMA>.DRI_INTELLIGENCE;
```

### Get App URL
```sql
SELECT SYSTEM$GET_STREAMLIT_URL('<DATABASE>.<SCHEMA>.DRI_INTELLIGENCE');
```

## Troubleshooting

### App shows "Starting..." for too long
1. Check compute pool: `SHOW COMPUTE POOLS;`
2. Resume if suspended: `ALTER COMPUTE POOL <NAME> RESUME;`
3. Check external access: `SHOW EXTERNAL ACCESS INTEGRATIONS;`

### "Object does not exist" errors
- The app uses `get_active_session()` which inherits database/schema context
- Ensure all tables exist in the target schema
- Check table names match (case-sensitive)

### "ROOT_LOCATION stages not supported for vNext"
- Container runtime apps MUST use `snow streamlit deploy`
- Do NOT use `CREATE STREAMLIT` SQL command

### Missing DEFICIT_TYPE or other columns
- Ensure you're using the V2.0 `setup_database.sql` which has complete schemas
- Re-run setup_database.sql to recreate tables with correct columns

## Files Reference

| File | Purpose |
|------|---------|
| `setup_infrastructure.sql` | Create compute pool and external access |
| `setup_database.sql` | Create all database objects |
| `load_config_data.sql` | Load config CSVs into tables |
| `load_patients.sql` | Load patient data CSVs (optional) |
| `deploy_streamlit.sql` | Documentation for Streamlit deployment |
| `Confidential/deployment/config_data/*.csv` | Configuration data files |
| `Confidential/deployment/patient_data/*.csv` | Patient demo data files (optional) |
