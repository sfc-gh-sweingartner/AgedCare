-- =============================================================================
-- DRI Intelligence - Patient Data Loading Script
-- =============================================================================
-- This script loads patient/resident data from stage files into the target tables.
-- The source data comes from exports with date cleansing applied.
-- 
-- Prerequisites:
--   1. Database and schema must exist (run setup_database.sql first)
--   2. Patient data CSV files must be uploaded to @DRI_STREAMLIT_STAGE/patients/
--   3. DRI_CSV_FORMAT file format must exist
--
-- Usage:
--   snow sql -f deployment/load_patients.sql -c <connection_name>
-- =============================================================================

USE DATABASE AGEDCARE_TEST;
USE SCHEMA DRI;

-- Verify file format exists
CREATE FILE FORMAT IF NOT EXISTS DRI_CSV_FORMAT
    TYPE = CSV
    PARSE_HEADER = TRUE
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    ESCAPE_UNENCLOSED_FIELD = NONE
    NULL_IF = ('', 'NULL', 'null');

-- =============================================================================
-- Truncate existing data (optional - comment out if appending)
-- =============================================================================
TRUNCATE TABLE IF EXISTS ACTIVE_RESIDENT_NOTES;
TRUNCATE TABLE IF EXISTS ACTIVE_RESIDENT_MEDICAL_PROFILE;
TRUNCATE TABLE IF EXISTS ACTIVE_RESIDENT_MEDICATION;
TRUNCATE TABLE IF EXISTS ACTIVE_RESIDENT_OBSERVATIONS;
TRUNCATE TABLE IF EXISTS ACTIVE_RESIDENT_OBSERVATION_GROUP;
TRUNCATE TABLE IF EXISTS ACTIVE_RESIDENT_ASSESSMENT_FORMS;

-- =============================================================================
-- Load Progress Notes (632 rows expected)
-- =============================================================================
COPY INTO ACTIVE_RESIDENT_NOTES
FROM @DRI_STREAMLIT_STAGE/patients/ACTIVE_RESIDENT_NOTES.csv
FILE_FORMAT = DRI_CSV_FORMAT
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = CONTINUE;

-- =============================================================================
-- Load Medical Profile / Diagnoses (3 rows expected)
-- =============================================================================
COPY INTO ACTIVE_RESIDENT_MEDICAL_PROFILE
FROM @DRI_STREAMLIT_STAGE/patients/ACTIVE_RESIDENT_MEDICAL_PROFILE.csv
FILE_FORMAT = DRI_CSV_FORMAT
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = CONTINUE;

-- =============================================================================
-- Load Medications (124 rows expected)
-- =============================================================================
COPY INTO ACTIVE_RESIDENT_MEDICATION
FROM @DRI_STREAMLIT_STAGE/patients/ACTIVE_RESIDENT_MEDICATION.csv
FILE_FORMAT = DRI_CSV_FORMAT
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = CONTINUE;

-- =============================================================================
-- Load Observations (2026+ rows expected - some source rows have corrupt dates)
-- =============================================================================
COPY INTO ACTIVE_RESIDENT_OBSERVATIONS
FROM @DRI_STREAMLIT_STAGE/patients/ACTIVE_RESIDENT_OBSERVATIONS.csv
FILE_FORMAT = DRI_CSV_FORMAT
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = CONTINUE;

-- =============================================================================
-- Load Observation Groups - Wounds/Pain Charts (4 rows expected)
-- =============================================================================
COPY INTO ACTIVE_RESIDENT_OBSERVATION_GROUP
FROM @DRI_STREAMLIT_STAGE/patients/ACTIVE_RESIDENT_OBSERVATION_GROUP.csv
FILE_FORMAT = DRI_CSV_FORMAT
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = CONTINUE;

-- =============================================================================
-- Load Assessment Forms (416 rows expected)
-- =============================================================================
COPY INTO ACTIVE_RESIDENT_ASSESSMENT_FORMS
FROM @DRI_STREAMLIT_STAGE/patients/ACTIVE_RESIDENT_ASSESSMENT_FORMS.csv
FILE_FORMAT = DRI_CSV_FORMAT
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = CONTINUE;

-- =============================================================================
-- Verify loaded data counts
-- =============================================================================
SELECT 'ACTIVE_RESIDENT_NOTES' as TABLE_NAME, COUNT(*) as ROW_COUNT FROM ACTIVE_RESIDENT_NOTES
UNION ALL SELECT 'ACTIVE_RESIDENT_MEDICAL_PROFILE', COUNT(*) FROM ACTIVE_RESIDENT_MEDICAL_PROFILE
UNION ALL SELECT 'ACTIVE_RESIDENT_MEDICATION', COUNT(*) FROM ACTIVE_RESIDENT_MEDICATION
UNION ALL SELECT 'ACTIVE_RESIDENT_OBSERVATIONS', COUNT(*) FROM ACTIVE_RESIDENT_OBSERVATIONS
UNION ALL SELECT 'ACTIVE_RESIDENT_OBSERVATION_GROUP', COUNT(*) FROM ACTIVE_RESIDENT_OBSERVATION_GROUP
UNION ALL SELECT 'ACTIVE_RESIDENT_ASSESSMENT_FORMS', COUNT(*) FROM ACTIVE_RESIDENT_ASSESSMENT_FORMS;
