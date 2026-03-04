-- DRI Intelligence - Infrastructure Setup
-- Run this script to create SPCS compute pool and external access integration
-- Requires ACCOUNTADMIN or appropriate privileges

-- ============================================================================
-- CONFIGURATION VARIABLES (set these before running)
-- ============================================================================
-- SET database_name = 'AGEDCARE_TEST';
-- SET schema_name = 'DRI';
-- SET warehouse_name = 'COMPUTE_WH';
-- SET compute_pool_name = 'DRI_COMPUTE_POOL';
-- SET external_access_name = 'ALLOW_ALL_ACCESS_INTEGRATION';

-- ============================================================================
-- 1. CREATE COMPUTE POOL (for Streamlit SPCS Container Runtime)
-- ============================================================================
-- Instance family: CPU_X64_XS is sufficient for Streamlit apps
-- Auto-suspend after 5 minutes of inactivity

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
-- 2. OPTION A: CREATE ALLOW-ALL EXTERNAL ACCESS (Simpler, for dev/demo)
-- ============================================================================
-- This allows outbound access to any host (PyPI, APIs, etc.)

CREATE OR REPLACE NETWORK RULE IDENTIFIER($database_name || '.' || $schema_name || '.ALLOW_ALL_NETWORK_RULE')
    MODE = EGRESS
    TYPE = HOST_PORT
    VALUE_LIST = ('0.0.0.0:443', '0.0.0.0:80')
    COMMENT = 'Allow all outbound HTTPS/HTTP access';

CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION ALLOW_ALL_ACCESS_INTEGRATION
    ALLOWED_NETWORK_RULES = (IDENTIFIER($database_name || '.' || $schema_name || '.ALLOW_ALL_NETWORK_RULE'))
    ENABLED = TRUE
    COMMENT = 'External access for all outbound connections';

-- ============================================================================
-- 2. OPTION B: CREATE PYPI-ONLY EXTERNAL ACCESS (More restrictive, for prod)
-- ============================================================================
-- Uncomment this section if you prefer restricted access

-- CREATE OR REPLACE NETWORK RULE IDENTIFIER($database_name || '.' || $schema_name || '.PYPI_NETWORK_RULE')
--     MODE = EGRESS
--     TYPE = HOST_PORT
--     VALUE_LIST = (
--         'pypi.org:443',
--         'files.pythonhosted.org:443',
--         'pypi.python.org:443'
--     )
--     COMMENT = 'Network rule for PyPI package access';

-- CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION PYPI_ACCESS_INTEGRATION
--     ALLOWED_NETWORK_RULES = (IDENTIFIER($database_name || '.' || $schema_name || '.PYPI_NETWORK_RULE'))
--     ENABLED = TRUE
--     COMMENT = 'External access for PyPI package installation only';

-- ============================================================================
-- 3. GRANT PERMISSIONS (if using non-ACCOUNTADMIN role)
-- ============================================================================
-- Uncomment and modify if you need to grant permissions to other roles

-- GRANT USAGE ON COMPUTE POOL IDENTIFIER($compute_pool_name) TO ROLE <your_role>;
-- GRANT USAGE ON INTEGRATION ALLOW_ALL_ACCESS_INTEGRATION TO ROLE <your_role>;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
SELECT 'Infrastructure setup complete!' AS STATUS;

SHOW COMPUTE POOLS LIKE $compute_pool_name;
SHOW EXTERNAL ACCESS INTEGRATIONS;
