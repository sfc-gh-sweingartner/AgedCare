# DRI Intelligence - Deployment Guide

This guide explains how to deploy the DRI Intelligence solution to a new Snowflake environment using CoCo CLI.

## Prerequisites

1. **CoCo CLI** installed and configured with a Snowflake connection
2. **Snowflake account** with ACCOUNTADMIN or appropriate privileges:
   - CREATE DATABASE, CREATE SCHEMA, CREATE TABLE
   - CREATE COMPUTE POOL, CREATE EXTERNAL ACCESS INTEGRATION
   - CREATE STREAMLIT
3. **Demo data files** (emailed separately):
   - `De-identified - 871 - Integration.xlsx` - Demo resident data
   - `dri_master_keyword_list.json` - DRI keyword definitions
   - `dri_business_rules_template.json` - Clinical business rules
4. **Python 3.11+** with pandas, openpyxl, snowflake-connector-python

## Quick Start

1. Place the confidential data files in a local folder
2. Open CoCo CLI and connect to your target Snowflake environment
3. Run this prompt:

```
Deploy the DRI Intelligence solution. The confidential data files are in [YOUR_PATH].
```

CoCo will interactively ask you for:
- Connection name
- Database name
- Schema name  
- Warehouse name
- Compute pool name (will create if needed)
- External access integration name (will create if needed)

## Manual Deployment Steps

If you prefer to deploy manually, follow these steps in order:

### Step 1: Setup Infrastructure
```sql
-- Run setup_infrastructure.sql with your parameters
-- Creates compute pool and external access integration
```

### Step 2: Create Database Objects
```sql
-- Run setup_database.sql
-- Creates all required tables
```

### Step 3: Load Demo Data
```bash
# Run the Python data loader
SNOWFLAKE_CONNECTION_NAME=your_connection python load_demo_data.py
```

### Step 4: Deploy Streamlit App
```sql
-- Run deploy_streamlit.sql
-- Creates the Streamlit app in SPCS
```

## Files Overview

### In Git Repository (deployment/)
- `DEPLOY_INSTRUCTIONS.md` - This file
- `setup_infrastructure.sql` - SPCS compute pool & external access
- `setup_database.sql` - All table DDL
- `deploy_streamlit.sql` - Streamlit deployment command

### Confidential (emailed separately)
- `load_demo_data.py` - Loads Excel data into tables
- `load_config_data.py` - Loads JSON config files
- Demo data files (Excel, JSON)

## Post-Deployment Verification

After deployment, verify:
1. All tables exist and have data
2. Streamlit app is accessible
3. Dashboard shows resident count > 0
4. Can run LLM analysis on a test resident

## Troubleshooting

### Compute Pool Issues
If Streamlit fails to start, check compute pool is running:
```sql
SHOW COMPUTE POOLS;
ALTER COMPUTE POOL <name> RESUME;
```

### External Access Issues
If LLM calls fail, verify external access integration:
```sql
SHOW EXTERNAL ACCESS INTEGRATIONS;
```

### Data Loading Issues
If Python loader fails, ensure:
- Correct connection name in SNOWFLAKE_CONNECTION_NAME env var
- Excel file path is correct
- Database and schema exist
