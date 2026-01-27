-- Healthcare AI Demo - Database Setup
-- This script creates the database, schema, and tables for the healthcare demo
-- Author: Snowflake Sales Engineering
-- Date: Created on project initialization

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS HEALTHCARE_DEMO
    COMMENT = 'Healthcare AI demonstration database for medical notes analysis';

-- Use the database immediately after creation
USE DATABASE HEALTHCARE_DEMO;

-- Create schema for medical notes analysis
CREATE SCHEMA IF NOT EXISTS MEDICAL_NOTES
    COMMENT = 'Schema containing patient notes analysis tables and views';

-- Use the schema immediately after creation
USE SCHEMA HEALTHCARE_DEMO.MEDICAL_NOTES;

-- Create stage for file uploads
CREATE STAGE IF NOT EXISTS MEDICAL_NOTES_STAGE
    COMMENT = 'Stage for uploading medical data files and Streamlit app';

-- Main analysis table for pre-computed insights
CREATE OR REPLACE TABLE PATIENT_ANALYSIS (
    -- Identifiers
    PATIENT_ID NUMBER PRIMARY KEY,
    PATIENT_UID VARCHAR,
    ANALYSIS_VERSION VARCHAR DEFAULT 'v1.0',
    PROCESSED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    -- Clinical Summary (Use Case 3)
    CHIEF_COMPLAINT TEXT,
    CLINICAL_SUMMARY TEXT,
    SBAR_SUMMARY VARIANT, -- {situation, background, assessment, recommendation}
    
    -- Diagnostic Analysis (Use Case 1)
    KEY_FINDINGS VARIANT, -- Array of {finding, category, severity}
    DIFFERENTIAL_DIAGNOSES VARIANT, -- Array of {diagnosis, confidence, evidence}
    DIAGNOSTIC_REASONING TEXT,
    SIMILAR_PATIENT_DIAGNOSES VARIANT, -- From SIMILAR_PATIENTS analysis
    
    -- Treatment Analysis (Use Case 2)
    TREATMENTS_ADMINISTERED VARIANT, -- Array of {treatment, date, outcome}
    TREATMENT_EFFECTIVENESS TEXT,
    EVIDENCE_BASED_RECOMMENDATIONS VARIANT, -- From RELEVANT_ARTICLES
    SIMILAR_PATIENT_TREATMENTS VARIANT, -- Comparative analysis
    
    -- Pattern Recognition (Use Case 4)
    PRESENTATION_TYPE VARCHAR, -- typical, atypical, rare
    RARE_DISEASE_INDICATORS VARIANT,
    SYMPTOM_CLUSTER_ID VARCHAR,
    ANOMALY_SCORE FLOAT,
    
    -- Cost Analysis (Use Case 5)
    HIGH_COST_INDICATORS VARIANT, -- procedures, medications, complications
    ESTIMATED_COST_CATEGORY VARCHAR, -- low, medium, high, very_high
    RESOURCE_UTILIZATION VARIANT,
    
    -- Quality Metrics (Use Case 7)
    CARE_QUALITY_INDICATORS VARIANT,
    GUIDELINE_ADHERENCE_FLAGS VARIANT,
    
    -- Educational Value (Use Case 8)
    TEACHING_POINTS VARIANT,
    CLINICAL_PEARLS TEXT,
    QUIZ_QUESTIONS VARIANT -- Array of Q&A for education
) COMMENT = 'Pre-computed AI analysis results for patient notes';

-- Real-time processing history
CREATE OR REPLACE TABLE REALTIME_ANALYSIS_LOG (
    ANALYSIS_ID VARCHAR DEFAULT UUID_STRING(),
    SESSION_ID VARCHAR,
    USER_NAME VARCHAR,
    ANALYSIS_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PATIENT_ID NUMBER,
    ORIGINAL_TEXT TEXT,
    MODIFIED_TEXT TEXT,
    ANALYSIS_TYPE VARCHAR, -- 'full', 'differential', 'summary', etc.
    AI_MODEL_USED VARCHAR,
    PROCESSING_TIME_MS NUMBER,
    RESULTS VARIANT,
    SUCCESS_FLAG BOOLEAN
) COMMENT = 'Log of real-time AI processing requests and results';

-- Cohort analysis for population health
CREATE OR REPLACE TABLE COHORT_INSIGHTS (
    COHORT_ID VARCHAR DEFAULT UUID_STRING(),
    ANALYSIS_DATE DATE DEFAULT CURRENT_DATE(),
    COHORT_DEFINITION VARIANT, -- Criteria used
    PATIENT_COUNT NUMBER,
    
    -- Aggregate metrics
    COMMON_DIAGNOSES VARIANT,
    TREATMENT_PATTERNS VARIANT,
    OUTCOME_STATISTICS VARIANT,
    COST_ANALYSIS VARIANT,
    QUALITY_METRICS VARIANT,
    
    -- Trends
    TEMPORAL_TRENDS VARIANT,
    EMERGING_PATTERNS TEXT
) COMMENT = 'Aggregated insights for patient cohorts';

-- Physician workflow optimization
CREATE OR REPLACE TABLE PHYSICIAN_INSIGHTS (
    INSIGHT_ID VARCHAR DEFAULT UUID_STRING(),
    GENERATED_DATE DATE DEFAULT CURRENT_DATE(),
    SPECIALTY VARCHAR,
    INSIGHT_TYPE VARCHAR, -- 'clinical_alert', 'best_practice', 'new_evidence'
    INSIGHT_TITLE TEXT,
    INSIGHT_CONTENT TEXT,
    EVIDENCE_LINKS VARIANT,
    APPLICABLE_PATIENTS VARIANT,
    PRIORITY_SCORE NUMBER
) COMMENT = 'Curated insights for physician workflows';

-- Processing status tracking
CREATE OR REPLACE TABLE PROCESSING_STATUS (
    BATCH_ID VARCHAR DEFAULT UUID_STRING(),
    START_TIME TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    END_TIME TIMESTAMP_NTZ,
    STATUS VARCHAR, -- 'running', 'completed', 'failed'
    TOTAL_PATIENTS NUMBER,
    PROCESSED_PATIENTS NUMBER,
    FAILED_PATIENTS NUMBER,
    ERROR_DETAILS VARIANT,
    PROCESSING_METRICS VARIANT
) COMMENT = 'Track batch processing jobs';

-- Create a view for easy patient lookup
CREATE OR REPLACE VIEW V_PATIENT_SUMMARY AS
SELECT 
    p.PATIENT_ID,
    p.PATIENT_UID,
    pmc.PATIENT_TITLE,
    pmc.AGE,
    pmc.GENDER,
    p.CHIEF_COMPLAINT,
    p.CLINICAL_SUMMARY,
    p.PRESENTATION_TYPE,
    p.ESTIMATED_COST_CATEGORY,
    p.PROCESSED_TIMESTAMP
FROM PATIENT_ANALYSIS p
LEFT JOIN PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS pmc
    ON p.PATIENT_ID = pmc.PATIENT_ID
ORDER BY p.PROCESSED_TIMESTAMP DESC;

-- Create demo scenarios table
CREATE OR REPLACE TABLE DEMO_SCENARIOS (
    SCENARIO_ID VARCHAR PRIMARY KEY,
    SCENARIO_NAME VARCHAR,
    SCENARIO_TYPE VARCHAR, -- 'diagnostic', 'treatment', 'cost', 'education'
    PATIENT_ID NUMBER,
    DESCRIPTION TEXT,
    TALKING_POINTS VARIANT,
    EXPECTED_OUTCOMES VARIANT,
    DEMO_DURATION_MINUTES NUMBER
) COMMENT = 'Pre-configured demo scenarios for consistent presentations';

-- Insert initial demo scenarios
INSERT INTO DEMO_SCENARIOS (SCENARIO_ID, SCENARIO_NAME, SCENARIO_TYPE, PATIENT_ID, DESCRIPTION, DEMO_DURATION_MINUTES)
VALUES 
    ('COMPLEX_DIAGNOSIS', 'Complex Diagnostic Case', 'diagnostic', 163844, 
     '66-year-old with seizures and cardiac arrhythmia requiring differential diagnosis', 5),
    ('RARE_DISEASE', 'Pediatric Rare Disease', 'diagnostic', 163840,
     '11-year-old with multicentric peripheral ossifying fibroma', 5),
    ('COST_OPTIMIZATION', 'High-Cost Patient Analysis', 'cost', 163841,
     'Patient with multiple procedures and complications', 5);

-- Enable change tracking on source table (required for Cortex Search)
ALTER TABLE PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS SET CHANGE_TRACKING = TRUE;

-- Create warehouse for Cortex Search service if not exists
CREATE WAREHOUSE IF NOT EXISTS CORTEX_SEARCH_WH WITH
    WAREHOUSE_SIZE='X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    COMMENT = 'Dedicated warehouse for Cortex Search service operations';

-- Create Cortex Search service for fast patient search
CREATE OR REPLACE CORTEX SEARCH SERVICE patient_search_service
    ON PATIENT_NOTES
    ATTRIBUTES PATIENT_ID, PATIENT_UID, PATIENT_TITLE, AGE, GENDER
    WAREHOUSE = CORTEX_SEARCH_WH
    TARGET_LAG = '1 day'
    EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0-8k'
    AS (
        SELECT
            PATIENT_NOTES,
            PATIENT_ID,
            PATIENT_UID, 
            PATIENT_TITLE,
            AGE,
            GENDER
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
        WHERE PATIENT_NOTES IS NOT NULL
            AND LENGTH(PATIENT_NOTES) > 50
    );

-- Grant appropriate permissions
GRANT USAGE ON DATABASE HEALTHCARE_DEMO TO ROLE PUBLIC;
GRANT USAGE ON SCHEMA HEALTHCARE_DEMO.MEDICAL_NOTES TO ROLE PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA HEALTHCARE_DEMO.MEDICAL_NOTES TO ROLE PUBLIC;
GRANT SELECT ON ALL VIEWS IN SCHEMA HEALTHCARE_DEMO.MEDICAL_NOTES TO ROLE PUBLIC;
GRANT USAGE ON WAREHOUSE CORTEX_SEARCH_WH TO ROLE PUBLIC;

-- Display confirmation
SELECT 'Healthcare Demo database objects and Cortex Search service created successfully' as STATUS;