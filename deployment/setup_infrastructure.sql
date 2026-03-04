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
-- 2. CREATE PYPI EXTERNAL ACCESS INTEGRATION (Recommended - Restrictive)
-- ============================================================================
-- This integration ONLY allows outbound access to PyPI for package installation.
-- This is the secure default for production and sensitive environments.

CREATE OR REPLACE NETWORK RULE IDENTIFIER($database_name || '.' || $schema_name || '.DRI_PYPI_NETWORK_RULE')
    MODE = EGRESS
    TYPE = HOST_PORT
    VALUE_LIST = (
        'pypi.org:443',
        'files.pythonhosted.org:443',
        'pypi.python.org:443'
    )
    COMMENT = 'Network rule for PyPI package access only';

CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION DRI_PYPI_ACCESS_INTEGRATION
    ALLOWED_NETWORK_RULES = (IDENTIFIER($database_name || '.' || $schema_name || '.DRI_PYPI_NETWORK_RULE'))
    ENABLED = TRUE
    COMMENT = 'External access for PyPI package installation only - no other outbound access';

-- ============================================================================
-- 3. OPTIONAL: CREATE ALLOW-ALL EXTERNAL ACCESS (Development/Demo Only)
-- ============================================================================
-- WARNING: This allows outbound access to ANY host on ports 80/443.
-- DO NOT use in production or environments with sensitive data.
-- Only uncomment if you need to access external APIs beyond PyPI.

-- CREATE OR REPLACE NETWORK RULE IDENTIFIER($database_name || '.' || $schema_name || '.DRI_ALLOW_ALL_NETWORK_RULE')
--     MODE = EGRESS
--     TYPE = HOST_PORT
--     VALUE_LIST = ('0.0.0.0:443', '0.0.0.0:80')
--     COMMENT = 'WARNING: Allow all outbound HTTPS/HTTP access - DEV ONLY';

-- CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION DRI_ALLOW_ALL_ACCESS_INTEGRATION
--     ALLOWED_NETWORK_RULES = (IDENTIFIER($database_name || '.' || $schema_name || '.DRI_ALLOW_ALL_NETWORK_RULE'))
--     ENABLED = TRUE
--     COMMENT = 'WARNING: External access for all outbound connections - DEV ONLY';

-- ============================================================================
-- 4. GRANT PERMISSIONS (if using non-ACCOUNTADMIN role)
-- ============================================================================
-- Uncomment and modify if you need to grant permissions to other roles

-- GRANT USAGE ON COMPUTE POOL IDENTIFIER($compute_pool_name) TO ROLE <your_role>;
-- GRANT USAGE ON INTEGRATION DRI_PYPI_ACCESS_INTEGRATION TO ROLE <your_role>;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
SELECT 'Infrastructure setup complete!' AS STATUS;

SHOW COMPUTE POOLS LIKE $compute_pool_name;
SHOW EXTERNAL ACCESS INTEGRATIONS LIKE 'DRI%';
