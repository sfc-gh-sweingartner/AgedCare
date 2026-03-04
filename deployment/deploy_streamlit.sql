-- DRI Intelligence - Streamlit Deployment
-- Deploys the Streamlit app to SPCS (Snowpark Container Services)
-- Replace ${VARIABLE} placeholders with your values

-- ============================================================================
-- CONFIGURATION VARIABLES (set these before running)
-- ============================================================================
-- SET database_name = 'AGEDCARE';
-- SET schema_name = 'AGEDCARE';
-- SET warehouse_name = 'COMPUTE_WH';
-- SET compute_pool_name = 'DRI_COMPUTE_POOL';
-- SET external_access_name = 'PYPI_ACCESS_INTEGRATION';
-- SET streamlit_name = 'DRI_INTELLIGENCE';

-- ============================================================================
-- PRE-REQUISITES CHECK
-- ============================================================================
-- Verify compute pool exists and is running
SHOW COMPUTE POOLS LIKE $compute_pool_name;

-- Verify external access integration exists
SHOW EXTERNAL ACCESS INTEGRATIONS LIKE $external_access_name;

-- Verify stage has files
LIST @IDENTIFIER($database_name || '.' || $schema_name || '.DRI_STREAMLIT_STAGE');

-- ============================================================================
-- DEPLOY STREAMLIT APP
-- ============================================================================
-- The Streamlit app uses:
-- - Container runtime for latest Streamlit features (st.navigation)
-- - External access for PyPI dependencies
-- - Compute pool for container execution

CREATE OR REPLACE STREAMLIT IDENTIFIER($database_name || '.' || $schema_name || '.' || $streamlit_name)
    FROM @IDENTIFIER($database_name || '.' || $schema_name || '.DRI_STREAMLIT_STAGE')
    MAIN_FILE = 'streamlit_app.py'
    QUERY_WAREHOUSE = $warehouse_name
    COMPUTE_POOL = $compute_pool_name
    RUNTIME_NAME = 'SYSTEM$ST_CONTAINER_RUNTIME_PY3_11'
    EXTERNAL_ACCESS_INTEGRATIONS = (IDENTIFIER($external_access_name))
    COMMENT = 'DRI Intelligence - AI-powered clinical analysis for aged care';

-- ============================================================================
-- GRANT ACCESS (if using non-ACCOUNTADMIN role)
-- ============================================================================
-- Uncomment and modify to grant access to other roles

-- GRANT USAGE ON STREAMLIT IDENTIFIER($database_name || '.' || $schema_name || '.' || $streamlit_name) TO ROLE <your_role>;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
SHOW STREAMLITS IN SCHEMA IDENTIFIER($database_name || '.' || $schema_name);

SELECT 
    'Streamlit app deployed!' AS STATUS,
    $streamlit_name AS APP_NAME,
    CONCAT('https://app.snowflake.com/', CURRENT_ORGANIZATION_NAME(), '/', CURRENT_ACCOUNT_NAME(), '/#/streamlit-apps/', $database_name, '.', $schema_name, '.', $streamlit_name) AS APP_URL;
