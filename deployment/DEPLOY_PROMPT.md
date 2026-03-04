# DRI Intelligence Deployment Prompt

Copy and paste this prompt into CoCo CLI to deploy the DRI Intelligence solution to your Snowflake environment.

---

## The Prompt

```
I need to deploy the DRI Intelligence (Aged Care DRI) solution to my Snowflake environment.

The deployment files are at: /Users/sweingartner/CoCo/AgedCare/deployment/
The confidential data files are at: /Users/sweingartner/CoCo/AgedCare/Confidential/deployment/
The Streamlit app source is at: /Users/sweingartner/CoCo/AgedCare/dri-intelligence/

Please deploy the solution by:
1. Asking me for: connection name, database name, schema name, warehouse name
2. Asking if I have an existing compute pool (suggest DRI_COMPUTE_POOL as default)
3. Asking if I have an existing external access integration (suggest PYPI_ACCESS_INTEGRATION as default)
4. Creating the infrastructure (compute pool, external access) if needed
5. Creating all database tables using setup_database.sql
6. Loading the demo data from the Excel file
7. Loading the config data from the JSON files
8. Uploading the Streamlit app files to the stage
9. Deploying the Streamlit app using deploy_streamlit.sql
10. Verifying everything works by checking table counts and app accessibility
```

---

## What the Deployment Does

### Phase 1: Infrastructure Setup
- Creates a compute pool for running the Streamlit container
- Creates network rules and external access integration for PyPI

### Phase 2: Database Setup  
- Creates the database and schema (if they don't exist)
- Creates ~25 tables for source data, DRI outputs, and intelligence features
- Inserts seed data (severity bands)

### Phase 3: Data Loading
- Loads demo resident data from Excel file (6 source tables)
- Loads DRI configuration from JSON files (keywords, business rules)

### Phase 4: Streamlit Deployment
- Uploads app files to a Snowflake stage
- Creates the Streamlit app with SPCS container runtime
- Links external access for dependencies

### Phase 5: Verification
- Checks all tables have expected row counts
- Verifies Streamlit app is accessible
- Tests basic dashboard functionality

---

## Files Required (Email to Recipients)

### From Confidential/deployment/:
1. `load_demo_data.py` - Python script to load Excel data
2. `load_config_data.py` - Python script to load JSON configs

### From Confidential/DRI/data/:
3. `De-identified - 871 - Integration.xlsx` - Demo resident data

### From Confidential/DRI_Additional/:
4. `dri_master_keyword_list.json` - DRI keyword definitions
5. `dri_business_rules_template.json` - Clinical business rules

---

## Post-Deployment

After deployment, the user should:
1. Access the Streamlit app URL provided
2. Navigate to Configuration page to verify settings
3. Run a test analysis on a resident from the Dashboard
4. Check Review Queue for generated results
