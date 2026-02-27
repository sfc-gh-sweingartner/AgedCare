--------------------------------------------------------------------------------
-- DRI Intelligence App - User and Role Setup Script
-- Version: 1.0
-- Date: 2026-02-26
-- Purpose: Create roles and users for deploying the DRI Intelligence Streamlit app
--------------------------------------------------------------------------------

-- =============================================================================
-- SECTION 1: CREATE THE DRI_CLINICIAN ROLE
-- =============================================================================

USE ROLE SECURITYADMIN;

CREATE ROLE IF NOT EXISTS DRI_CLINICIAN
    COMMENT = 'Role for clinical staff using the DRI Intelligence Streamlit application';

-- =============================================================================
-- SECTION 2: CREATE USER
-- =============================================================================

CREATE USER IF NOT EXISTS "todd.tobin@health.telstra.com"
    LOGIN_NAME = 'todd.tobin@health.telstra.com'
    DISPLAY_NAME = 'Todd Tobin'
    EMAIL = 'todd.tobin@health.telstra.com'
    DEFAULT_ROLE = DRI_CLINICIAN
    MUST_CHANGE_PASSWORD = TRUE
    COMMENT = 'DRI Intelligence clinical user';

-- Grant the role to the user
GRANT ROLE DRI_CLINICIAN TO USER "todd.tobin@health.telstra.com";

-- =============================================================================
-- SECTION 3: GRANT WAREHOUSE ACCESS
-- =============================================================================
-- Note: Replace COMPUTE_WH with your actual warehouse name

USE ROLE SYSADMIN;

GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE DRI_CLINICIAN;

-- =============================================================================
-- SECTION 4: GRANT DATABASE AND SCHEMA ACCESS
-- =============================================================================

GRANT USAGE ON DATABASE AGEDCARE TO ROLE DRI_CLINICIAN;
GRANT USAGE ON SCHEMA AGEDCARE.AGEDCARE TO ROLE DRI_CLINICIAN;

-- =============================================================================
-- SECTION 5: READ-ONLY TABLES (Source clinical data)
-- =============================================================================
-- These are the source data tables - clinicians should only READ from these

GRANT SELECT ON TABLE AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES TO ROLE DRI_CLINICIAN;
GRANT SELECT ON TABLE AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION TO ROLE DRI_CLINICIAN;
GRANT SELECT ON TABLE AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS TO ROLE DRI_CLINICIAN;
GRANT SELECT ON TABLE AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_ASSESSMENT_FORMS TO ROLE DRI_CLINICIAN;
GRANT SELECT ON TABLE AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICAL_PROFILE TO ROLE DRI_CLINICIAN;
GRANT SELECT ON TABLE AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATION_GROUP TO ROLE DRI_CLINICIAN;

-- Reference/configuration tables (READ-ONLY)
GRANT SELECT ON TABLE AGEDCARE.AGEDCARE.DRI_RULES TO ROLE DRI_CLINICIAN;
GRANT SELECT ON TABLE AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS TO ROLE DRI_CLINICIAN;
GRANT SELECT ON TABLE AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG TO ROLE DRI_CLINICIAN;
GRANT SELECT ON TABLE AGEDCARE.AGEDCARE.DRI_KEYWORD_MASTER_LIST TO ROLE DRI_CLINICIAN;
GRANT SELECT ON TABLE AGEDCARE.AGEDCARE.DRI_SEVERITY TO ROLE DRI_CLINICIAN;

-- =============================================================================
-- SECTION 6: READ-WRITE TABLES (Application working tables)
-- =============================================================================
-- These tables are used by the app for analysis results and workflow

-- LLM Analysis results (stores each analysis run)
GRANT SELECT, INSERT, UPDATE ON TABLE AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS TO ROLE DRI_CLINICIAN;

-- Review queue (approval workflow)
GRANT SELECT, INSERT, UPDATE ON TABLE AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE TO ROLE DRI_CLINICIAN;

-- Clinical decisions (approved changes)
GRANT SELECT, INSERT, UPDATE ON TABLE AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS TO ROLE DRI_CLINICIAN;

-- Indicator rejections (rejected detections)
GRANT SELECT, INSERT, UPDATE ON TABLE AGEDCARE.AGEDCARE.DRI_INDICATOR_REJECTIONS TO ROLE DRI_CLINICIAN;

-- Deficit tracking tables
GRANT SELECT, INSERT, UPDATE ON TABLE AGEDCARE.AGEDCARE.DRI_DEFICIT_STATUS TO ROLE DRI_CLINICIAN;
GRANT SELECT, INSERT, UPDATE ON TABLE AGEDCARE.AGEDCARE.DRI_DEFICIT_DETAIL TO ROLE DRI_CLINICIAN;
GRANT SELECT, INSERT, UPDATE ON TABLE AGEDCARE.AGEDCARE.DRI_DEFICIT_SUMMARY TO ROLE DRI_CLINICIAN;

-- Ground truth and evaluation tables
GRANT SELECT, INSERT, UPDATE ON TABLE AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH TO ROLE DRI_CLINICIAN;
GRANT SELECT, INSERT, UPDATE ON TABLE AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS TO ROLE DRI_CLINICIAN;
GRANT SELECT, INSERT, UPDATE ON TABLE AGEDCARE.AGEDCARE.DRI_EVALUATION_DETAIL TO ROLE DRI_CLINICIAN;

-- =============================================================================
-- SECTION 7: VIEW ACCESS
-- =============================================================================

GRANT SELECT ON VIEW AGEDCARE.AGEDCARE.V_EVALUATION_SUMMARY TO ROLE DRI_CLINICIAN;
GRANT SELECT ON VIEW AGEDCARE.AGEDCARE.V_FP_RATE_TREND TO ROLE DRI_CLINICIAN;

-- =============================================================================
-- SECTION 8: CORTEX AI FUNCTIONS
-- =============================================================================
-- Required for LLM-based analysis

GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE DRI_CLINICIAN;

-- =============================================================================
-- SECTION 9: CORTEX SEARCH SERVICE
-- =============================================================================
-- If using Cortex Search for indicator lookup

GRANT USAGE ON CORTEX SEARCH SERVICE AGEDCARE.AGEDCARE.DRI_INDICATOR_SEARCH TO ROLE DRI_CLINICIAN;

-- =============================================================================
-- SECTION 10: STREAMLIT APP ACCESS
-- =============================================================================
-- Grant access to run the Streamlit app
-- Note: Replace DRI_INTELLIGENCE with your actual Streamlit app name

GRANT USAGE ON STREAMLIT AGEDCARE.AGEDCARE.DRI_INTELLIGENCE TO ROLE DRI_CLINICIAN;

-- =============================================================================
-- SECTION 11: ROLE HIERARCHY (OPTIONAL)
-- =============================================================================
-- If you want SYSADMIN to be able to manage this role

GRANT ROLE DRI_CLINICIAN TO ROLE SYSADMIN;

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================
-- Run these to verify the setup was successful

-- Check user exists
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.USERS 
WHERE NAME = 'todd.tobin@health.telstra.com';

-- Check role grants
SHOW GRANTS TO ROLE DRI_CLINICIAN;

-- Check user's role assignment
SHOW GRANTS TO USER "todd.tobin@health.telstra.com";

--------------------------------------------------------------------------------
-- NOTES FOR ADDITIONAL USERS
--------------------------------------------------------------------------------
-- To add more users with the same permissions, just run:
--
-- CREATE USER IF NOT EXISTS "email@health.telstra.com"
--     LOGIN_NAME = 'email@health.telstra.com'
--     DISPLAY_NAME = 'User Name'
--     EMAIL = 'email@health.telstra.com'
--     DEFAULT_ROLE = DRI_CLINICIAN
--     MUST_CHANGE_PASSWORD = TRUE;
--
-- GRANT ROLE DRI_CLINICIAN TO USER "email@health.telstra.com";
--------------------------------------------------------------------------------
