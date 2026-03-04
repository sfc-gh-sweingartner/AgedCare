-- DRI Intelligence - Infrastructure Setup
-- Run this script to create SPCS compute pool and external access integration
-- Replace ${VARIABLE} placeholders with your values

-- ============================================================================
-- CONFIGURATION VARIABLES (set these before running)
-- ============================================================================
-- SET database_name = 'AGEDCARE';
-- SET schema_name = 'AGEDCARE';
-- SET warehouse_name = 'COMPUTE_WH';
-- SET compute_pool_name = 'DRI_COMPUTE_POOL';
-- SET external_access_name = 'PYPI_ACCESS_INTEGRATION';

-- ============================================================================
-- 1. CREATE COMPUTE POOL (for Streamlit SPCS Container)
-- ============================================================================
-- Suggested name: DRI_COMPUTE_POOL
-- Instance family: CPU_X64_XS is sufficient for Streamlit apps

CREATE COMPUTE POOL IF NOT EXISTS IDENTIFIER($compute_pool_name)
    MIN_NODES = 1
    MAX_NODES = 1
    INSTANCE_FAMILY = CPU_X64_XS
    AUTO_RESUME = TRUE
    AUTO_SUSPEND_SECS = 300
    COMMENT = 'Compute pool for DRI Intelligence Streamlit app';

-- Resume if suspended
ALTER COMPUTE POOL IF EXISTS IDENTIFIER($compute_pool_name) RESUME;

-- Verify compute pool status
SHOW COMPUTE POOLS LIKE $compute_pool_name;

-- ============================================================================
-- 2. CREATE NETWORK RULE (for PyPI access)
-- ============================================================================
CREATE OR REPLACE NETWORK RULE IDENTIFIER($database_name || '.' || $schema_name || '.PYPI_NETWORK_RULE')
    MODE = EGRESS
    TYPE = HOST_PORT
    VALUE_LIST = (
        'pypi.org',
        'files.pythonhosted.org',
        'pypi.python.org'
    )
    COMMENT = 'Network rule for PyPI package access';

-- ============================================================================
-- 3. CREATE EXTERNAL ACCESS INTEGRATION
-- ============================================================================
-- Suggested name: PYPI_ACCESS_INTEGRATION
-- This allows the Streamlit container to install Python packages

CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION IDENTIFIER($external_access_name)
    ALLOWED_NETWORK_RULES = (IDENTIFIER($database_name || '.' || $schema_name || '.PYPI_NETWORK_RULE'))
    ENABLED = TRUE
    COMMENT = 'External access for PyPI package installation';

-- Verify external access integration
SHOW EXTERNAL ACCESS INTEGRATIONS LIKE $external_access_name;

-- ============================================================================
-- 4. GRANT PERMISSIONS (if using non-ACCOUNTADMIN role)
-- ============================================================================
-- Uncomment and modify if you need to grant permissions to other roles

-- GRANT USAGE ON COMPUTE POOL IDENTIFIER($compute_pool_name) TO ROLE <your_role>;
-- GRANT USAGE ON INTEGRATION IDENTIFIER($external_access_name) TO ROLE <your_role>;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
SELECT 'Infrastructure setup complete!' AS STATUS;
SELECT 
    'Compute Pool: ' || $compute_pool_name AS RESOURCE,
    (SELECT STATE FROM TABLE(RESULT_SCAN(LAST_QUERY_ID(-2)))) AS STATUS
UNION ALL
SELECT 
    'External Access: ' || $external_access_name,
    'ENABLED';
