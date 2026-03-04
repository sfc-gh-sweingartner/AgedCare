-- DRI Intelligence - Streamlit Deployment
-- Use snow CLI to deploy Streamlit with container runtime

-- ============================================================================
-- IMPORTANT: DO NOT USE THIS SQL FILE DIRECTLY
-- ============================================================================
-- Container runtime Streamlit apps MUST be deployed using the snow CLI:
--
--   snow streamlit deploy --replace -c <CONNECTION_NAME>
--
-- The CREATE STREAMLIT command with ROOT_LOCATION does NOT work for 
-- container runtime (vNext) applications.
-- ============================================================================

-- ============================================================================
-- PREREQUISITES CHECKLIST
-- ============================================================================
-- 1. Database and schema created (setup_database.sql)
-- 2. Compute pool created and running (setup_infrastructure.sql)
-- 3. External access integration created
-- 4. Config data loaded (load_config_data.sql)
-- 5. snowflake.yml configured with correct values

-- ============================================================================
-- SNOWFLAKE.YML CONFIGURATION
-- ============================================================================
-- Create/update dri-intelligence/snowflake.yml with your environment settings:
--
-- definition_version: 2
-- entities:
--   dri_intelligence:
--     type: streamlit
--     identifier:
--       name: DRI_INTELLIGENCE
--       database: <YOUR_DATABASE>      # e.g., AGEDCARE_TEST
--       schema: <YOUR_SCHEMA>          # e.g., DRI
--     title: DRI Intelligence
--     query_warehouse: <YOUR_WAREHOUSE>  # e.g., COMPUTE_WH
--     compute_pool: <YOUR_COMPUTE_POOL>  # e.g., DRI_COMPUTE_POOL
--     runtime_name: SYSTEM$ST_CONTAINER_RUNTIME_PY3_11
--     external_access_integrations:
--       - <YOUR_INTEGRATION>           # e.g., ALLOW_ALL_ACCESS_INTEGRATION
--     main_file: streamlit_app.py
--     artifacts:
--       - streamlit_app.py
--       - pyproject.toml
--       - uv.lock
--       - src/__init__.py
--       - src/connection_helper.py
--       - src/dri_analysis.py
--       - app_pages/__init__.py
--       - app_pages/dashboard.py
--       - app_pages/prompt_engineering.py
--       - app_pages/batch_testing.py
--       - app_pages/review_queue.py
--       - app_pages/resident_history.py
--       - app_pages/audit_results.py
--       - app_pages/feedback_loop.py
--       - app_pages/configuration.py
--       - app_pages/comparison.py
--       - app_pages/testing_tools.py

-- ============================================================================
-- DEPLOYMENT COMMAND
-- ============================================================================
-- From the dri-intelligence directory, run:
--
--   # First time deployment:
--   snow streamlit deploy -c <CONNECTION_NAME>
--
--   # Update existing app:
--   snow streamlit deploy --replace -c <CONNECTION_NAME>
--
-- Example:
--   cd /path/to/AgedCare/dri-intelligence
--   snow streamlit deploy --replace -c AU_DEMO29

-- ============================================================================
-- VERIFY DEPLOYMENT
-- ============================================================================
-- After deployment, verify the app is running:

-- Check Streamlit exists
-- SHOW STREAMLITS IN SCHEMA <DATABASE>.<SCHEMA>;

-- Check app status (should show 'RUNNING' after a minute)
-- DESCRIBE STREAMLIT <DATABASE>.<SCHEMA>.DRI_INTELLIGENCE;

-- Get app URL
-- SELECT SYSTEM$GET_STREAMLIT_URL('<DATABASE>.<SCHEMA>.DRI_INTELLIGENCE');

-- ============================================================================
-- TROUBLESHOOTING
-- ============================================================================
-- If app shows "Starting..." for more than 2 minutes:
--   1. Check compute pool is running: SHOW COMPUTE POOLS;
--   2. Check external access is enabled: SHOW EXTERNAL ACCESS INTEGRATIONS;
--   3. Check app logs in Snowsight

-- If you get "ROOT_LOCATION stages are not supported for vNext applications":
--   - You must use snow CLI deploy, not CREATE STREAMLIT command

-- If you get "Object does not exist" errors after deployment:
--   - Ensure database and schema are correctly set in app queries
--   - The app uses get_active_session() which inherits the context
