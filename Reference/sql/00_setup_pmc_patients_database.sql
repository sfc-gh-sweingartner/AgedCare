-- PMC Patients Database Setup Script
-- This script creates the PMC_PATIENTS database, schema, and table structure
-- and loads data from the PMC-Patients.csv file
-- Author: Healthcare AI Demo Team
-- Date: Created for sharing with colleagues

-- =====================================================
-- STEP 1: Create Database and Schema
-- =====================================================

-- Create the PMC_PATIENTS database
CREATE DATABASE IF NOT EXISTS PMC_PATIENTS
    COMMENT = 'Database containing PMC patient case studies for medical AI analysis';

-- Use the database
USE DATABASE PMC_PATIENTS;

-- Create the schema
CREATE SCHEMA IF NOT EXISTS PMC_PATIENTS
    COMMENT = 'Schema containing patient case tables and related objects';

-- Use the schema
USE SCHEMA PMC_PATIENTS.PMC_PATIENTS;

-- =====================================================
-- STEP 2: Create File Format for CSV Loading
-- =====================================================

-- Create file format for CSV files
CREATE OR REPLACE FILE FORMAT CSV_FORMAT
    TYPE = 'CSV'
    FIELD_DELIMITER = ','
    RECORD_DELIMITER = '\n'
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    ESCAPE_CHAR = '\\'
    ESCAPE_UNENCLOSED_FIELD = FALSE
    TRIM_SPACE = TRUE
    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE
    REPLACE_INVALID_CHARACTERS = TRUE
    NULL_IF = ('NULL', 'null', '', '\\N')
    COMMENT = 'CSV file format for loading PMC patient data';

-- =====================================================
-- STEP 3: Create Stage for File Upload
-- =====================================================

-- Create stage for file uploads
CREATE STAGE IF NOT EXISTS PMC_DATA_STAGE
    COMMENT = 'Stage for uploading PMC patient CSV files';

-- =====================================================
-- STEP 4: Create PMC_PATIENTS Table
-- =====================================================

-- Create the main PMC_PATIENTS table
CREATE OR REPLACE TABLE PMC_PATIENTS (
    PATIENT_ID NUMBER,
    AGE TEXT,
    GENDER TEXT,
    SIMILAR_PATIENTS TEXT,
    PATIENT_TITLE TEXT,
    FILE_PATH TEXT,
    PATIENT_NOTES TEXT,
    RELEVANT_ARTICLES TEXT,
    PMID NUMBER,
    PATIENT_UID TEXT
) COMMENT = 'PMC patient case studies with clinical notes and metadata';

-- =====================================================
-- STEP 5: Load Data from CSV File
-- =====================================================

-- Instructions for loading the CSV file:
-- 1. First, upload the CSV file to the stage:
--    PUT file:///path/to/PMC-Patients.csv @PMC_DATA_STAGE;
--
-- 2. Then load the data using the COPY INTO command below:

/*
-- Upload the CSV file to the stage (run this from SnowSQL or similar client)
PUT file:///Users/sweingartner/Cursor/MedicalTranscripts/Data/PMC-Patients.csv @PMC_DATA_STAGE;

-- Load data from the CSV file into the table
COPY INTO PMC_PATIENTS (
    PATIENT_ID,
    PATIENT_UID, 
    PMID,
    FILE_PATH,
    PATIENT_TITLE,
    PATIENT_NOTES,
    AGE,
    GENDER,
    RELEVANT_ARTICLES,
    SIMILAR_PATIENTS
)
FROM (
    SELECT 
        TRY_CAST($1 AS NUMBER) AS PATIENT_ID,
        $2 AS PATIENT_UID,
        TRY_CAST($3 AS NUMBER) AS PMID,
        $4 AS FILE_PATH,
        $5 AS PATIENT_TITLE,
        $6 AS PATIENT_NOTES,
        $7 AS AGE,
        $8 AS GENDER,
        $9 AS RELEVANT_ARTICLES,
        $10 AS SIMILAR_PATIENTS
    FROM @PMC_DATA_STAGE/PMC-Patients.csv.gz
)
FILE_FORMAT = CSV_FORMAT
ON_ERROR = 'CONTINUE';
*/

-- =====================================================
-- STEP 6: Enable Change Tracking (for Cortex Search)
-- =====================================================

-- Enable change tracking for Cortex Search integration
ALTER TABLE PMC_PATIENTS SET CHANGE_TRACKING = TRUE;

-- =====================================================
-- STEP 7: Create Index and Constraints
-- =====================================================

-- Add primary key constraint if needed (optional)
-- ALTER TABLE PMC_PATIENTS ADD PRIMARY KEY (PATIENT_ID);

-- =====================================================
-- STEP 8: Grant Permissions
-- =====================================================

-- Grant appropriate permissions
GRANT USAGE ON DATABASE PMC_PATIENTS TO ROLE PUBLIC;
GRANT USAGE ON SCHEMA PMC_PATIENTS.PMC_PATIENTS TO ROLE PUBLIC;
GRANT SELECT ON TABLE PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS TO ROLE PUBLIC;
GRANT USAGE ON STAGE PMC_DATA_STAGE TO ROLE PUBLIC;

-- =====================================================
-- STEP 9: Verification Queries
-- =====================================================

-- Verify the table was created successfully
DESCRIBE TABLE PMC_PATIENTS;

-- Check data after loading (uncomment after running COPY INTO)
-- SELECT COUNT(*) as TOTAL_PATIENTS FROM PMC_PATIENTS;
-- SELECT PATIENT_ID, PATIENT_TITLE, AGE, GENDER FROM PMC_PATIENTS LIMIT 5;

-- Display completion message
SELECT 'PMC_PATIENTS database and table structure created successfully!' AS STATUS,
       'Run the PUT and COPY INTO commands to load your CSV data.' AS NEXT_STEP;
