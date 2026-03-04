-- DRI Intelligence - Load Configuration Data
-- Loads config data from CSV files on stage
-- Run AFTER setup_database.sql and uploading CSV files to stage

-- ============================================================================
-- CONFIGURATION (set these before running)
-- ============================================================================
-- SET database_name = 'AGEDCARE_TEST';
-- SET schema_name = 'DRI';
-- SET stage_path = '@DRI_STREAMLIT_STAGE/config';

USE DATABASE IDENTIFIER($database_name);
USE SCHEMA IDENTIFIER($schema_name);

-- ============================================================================
-- FILE FORMAT FOR CSV WITH HEADERS
-- ============================================================================
CREATE OR REPLACE FILE FORMAT DRI_CSV_FORMAT
    TYPE = CSV
    PARSE_HEADER = TRUE
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    ESCAPE_UNENCLOSED_FIELD = NONE
    NULL_IF = ('', 'NULL', 'null');

-- ============================================================================
-- 1. LOAD DRI_CLIENT_CONFIG
-- ============================================================================
COPY INTO DRI_CLIENT_CONFIG
FROM @DRI_STREAMLIT_STAGE/config/DRI_CLIENT_CONFIG.csv
FILE_FORMAT = DRI_CSV_FORMAT
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = CONTINUE;

-- ============================================================================
-- 2. LOAD DRI_PROMPT_VERSIONS
-- ============================================================================
COPY INTO DRI_PROMPT_VERSIONS
FROM @DRI_STREAMLIT_STAGE/config/DRI_PROMPT_VERSIONS.csv
FILE_FORMAT = DRI_CSV_FORMAT
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = CONTINUE;

-- ============================================================================
-- 3. LOAD DRI_RULES (V2.0 - 31 columns)
-- ============================================================================
COPY INTO DRI_RULES
FROM @DRI_STREAMLIT_STAGE/config/DRI_RULES.csv
FILE_FORMAT = DRI_CSV_FORMAT
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = CONTINUE;

-- ============================================================================
-- 4. LOAD DRI_CLIENT_RULE_ASSIGNMENTS
-- ============================================================================
COPY INTO DRI_CLIENT_RULE_ASSIGNMENTS
FROM @DRI_STREAMLIT_STAGE/config/DRI_CLIENT_RULE_ASSIGNMENTS.csv
FILE_FORMAT = DRI_CSV_FORMAT
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = CONTINUE;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
SELECT 'Config data loaded!' AS STATUS;

SELECT 'DRI_CLIENT_CONFIG' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM DRI_CLIENT_CONFIG
UNION ALL
SELECT 'DRI_PROMPT_VERSIONS', COUNT(*) FROM DRI_PROMPT_VERSIONS
UNION ALL
SELECT 'DRI_RULES', COUNT(*) FROM DRI_RULES
UNION ALL
SELECT 'DRI_CLIENT_RULE_ASSIGNMENTS', COUNT(*) FROM DRI_CLIENT_RULE_ASSIGNMENTS
ORDER BY TABLE_NAME;
