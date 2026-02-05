-- ============================================================================
-- DRI Evaluation Job Setup Script
-- ============================================================================
-- This script sets up the SPCS Job for running TruLens-based AI Observability
-- evaluations of the DRI Intelligence system.
--
-- Prerequisites:
--   1. Docker image built and pushed to registry
--   2. Image repository exists
--   3. Compute pool available
--
-- Run this script as ACCOUNTADMIN or a role with appropriate privileges.
-- ============================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE AGEDCARE;
USE SCHEMA AGEDCARE;

-- ============================================================================
-- Step 1: Create Image Repository (if not exists)
-- ============================================================================

CREATE IMAGE REPOSITORY IF NOT EXISTS DRI_IMAGES;

-- Get the registry URL for docker push
SHOW IMAGE REPOSITORIES LIKE 'DRI_IMAGES';
-- Note the repository_url - use it for docker push

-- ============================================================================
-- Step 2: Create Evaluation Tables (if not exists)
-- ============================================================================

CREATE TABLE IF NOT EXISTS DRI_EVALUATION_METRICS (
    EVALUATION_ID VARCHAR(36) PRIMARY KEY,
    RUN_NAME VARCHAR(255) NOT NULL,
    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PROMPT_VERSION VARCHAR(50),
    MODEL_USED VARCHAR(100),
    CLIENT_SYSTEM_KEY VARCHAR(100),
    DATASET_NAME VARCHAR(255),
    TOTAL_RECORDS INT DEFAULT 0,
    RECORDS_EVALUATED INT DEFAULT 0,
    AVG_GROUNDEDNESS_SCORE FLOAT DEFAULT 0,
    AVG_CONTEXT_RELEVANCE_SCORE FLOAT DEFAULT 0,
    AVG_ANSWER_RELEVANCE_SCORE FLOAT DEFAULT 0,
    TRUE_POSITIVES INT DEFAULT 0,
    FALSE_POSITIVES INT DEFAULT 0,
    FALSE_POSITIVE_RATE FLOAT DEFAULT 0,
    PRECISION_SCORE FLOAT DEFAULT 0,
    AVG_LATENCY_MS INT DEFAULT 0,
    STATUS VARCHAR(50) DEFAULT 'PENDING',
    ERROR_MESSAGE VARCHAR(4000)
);

CREATE TABLE IF NOT EXISTS DRI_EVALUATION_DETAIL (
    DETAIL_ID VARCHAR(36) PRIMARY KEY,
    EVALUATION_ID VARCHAR(36) REFERENCES DRI_EVALUATION_METRICS(EVALUATION_ID),
    RESIDENT_ID INT,
    RECORD_INDEX INT,
    INDICATORS_DETECTED INT DEFAULT 0,
    GROUNDEDNESS_SCORE FLOAT,
    CONTEXT_RELEVANCE_SCORE FLOAT,
    ANSWER_RELEVANCE_SCORE FLOAT,
    EXPECTED_INDICATORS VARIANT,
    ACTUAL_INDICATORS VARIANT,
    IS_CORRECT BOOLEAN,
    MISMATCH_DETAILS VARCHAR(1000),
    LATENCY_MS INT,
    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS DRI_GROUND_TRUTH (
    GROUND_TRUTH_ID VARCHAR(36) DEFAULT UUID_STRING() PRIMARY KEY,
    DATASET_NAME VARCHAR(100) NOT NULL,
    RESIDENT_ID INT NOT NULL,
    EXPECTED_INDICATORS ARRAY,
    EXPECTED_INDICATOR_COUNT INT,
    VALIDATED_BY VARCHAR(100),
    VALIDATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    IS_ACTIVE BOOLEAN DEFAULT TRUE,
    NOTES VARCHAR(1000),
    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================================
-- Step 3: Grant AI Observability Privileges
-- ============================================================================
-- These privileges are REQUIRED for TruLens to register applications and runs
-- in Snowflake AI Observability (visible in Snowsight > AI & ML > Evaluations)

-- Create a role for AI Observability users (if not exists)
CREATE ROLE IF NOT EXISTS AI_OBSERVABILITY_USER;

-- Grant CORTEX_USER database role (required for Cortex LLM access)
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE AI_OBSERVABILITY_USER;

-- Grant AI_OBSERVABILITY_EVENTS_LOOKUP application role (required to view evaluation data)
GRANT APPLICATION ROLE SNOWFLAKE.AI_OBSERVABILITY_EVENTS_LOOKUP TO ROLE AI_OBSERVABILITY_USER;

-- Grant CREATE EXTERNAL AGENT privilege (required to register applications)
GRANT CREATE EXTERNAL AGENT ON SCHEMA AGEDCARE.AGEDCARE TO ROLE AI_OBSERVABILITY_USER;

-- Grant CREATE TASK privilege (required for evaluation runs)
GRANT CREATE TASK ON SCHEMA AGEDCARE.AGEDCARE TO ROLE AI_OBSERVABILITY_USER;

-- Grant EXECUTE TASK privilege (required to execute evaluation tasks)
GRANT EXECUTE TASK ON ACCOUNT TO ROLE AI_OBSERVABILITY_USER;

-- Grant usage on database and schema
GRANT USAGE ON DATABASE AGEDCARE TO ROLE AI_OBSERVABILITY_USER;
GRANT USAGE ON SCHEMA AGEDCARE.AGEDCARE TO ROLE AI_OBSERVABILITY_USER;

-- Grant usage on warehouse
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE AI_OBSERVABILITY_USER;

-- Grant the role to ACCOUNTADMIN and SYSADMIN
GRANT ROLE AI_OBSERVABILITY_USER TO ROLE ACCOUNTADMIN;
GRANT ROLE AI_OBSERVABILITY_USER TO ROLE SYSADMIN;

-- Grant to specific users who will run evaluations (add your users here)
-- GRANT ROLE AI_OBSERVABILITY_USER TO USER YOUR_USERNAME;

-- Also grant privileges directly to ACCOUNTADMIN for SPCS job execution
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE ACCOUNTADMIN;
GRANT APPLICATION ROLE SNOWFLAKE.AI_OBSERVABILITY_EVENTS_LOOKUP TO ROLE ACCOUNTADMIN;
GRANT APPLICATION ROLE SNOWFLAKE.AI_OBSERVABILITY_ADMIN TO ROLE ACCOUNTADMIN;
GRANT CREATE EXTERNAL AGENT ON SCHEMA AGEDCARE.AGEDCARE TO ROLE ACCOUNTADMIN;

-- ============================================================================
-- Step 4: Create Stage for Job Spec (if using stage-based deployment)
-- ============================================================================

CREATE STAGE IF NOT EXISTS DRI_EVAL_STAGE
    ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');

-- ============================================================================
-- Step 5: Create or Replace the Job Service
-- ============================================================================
-- Note: The job spec files (job-spec.yaml, job-run-spec.yaml) should be uploaded
-- to the DRI_EVAL_STAGE before running EXECUTE JOB SERVICE

-- Option A: Inline spec (for testing)
-- This creates a job service with inline specification

-- DROP SERVICE IF EXISTS DRI_EVALUATION_JOB;
-- 
-- CREATE SERVICE IF NOT EXISTS DRI_EVALUATION_JOB
--     IN COMPUTE POOL FULLSTACK_COMPUTE_POOL
--     FROM SPECIFICATION $$
-- spec:
--   containers:
--   - name: dri-evaluation
--     image: /AGEDCARE/AGEDCARE/DRI_IMAGES/dri-evaluation:latest
--     env:
--       SNOWFLAKE_DATABASE: "AGEDCARE"
--       SNOWFLAKE_SCHEMA: "AGEDCARE"
--       SNOWFLAKE_WAREHOUSE: "COMPUTE_WH"
--       TRULENS_OTEL_TRACING: "1"
--     resources:
--       requests:
--         memory: 4Gi
--         cpu: 2000m
--       limits:
--         memory: 8Gi
--         cpu: 4000m
-- $$
--     MIN_INSTANCES = 0
--     MAX_INSTANCES = 1
--     AUTO_SUSPEND_SECS = 300
--     QUERY_WAREHOUSE = COMPUTE_WH;

-- Option B: Execute as Job Service (recommended)
-- Run evaluations on-demand without maintaining a persistent service:
--
-- EXECUTE JOB SERVICE
-- IN COMPUTE POOL FULLSTACK_COMPUTE_POOL
-- FROM @AGEDCARE.AGEDCARE.DRI_EVAL_STAGE
-- SPEC = 'job-run-spec.yaml'
-- NAME = AGEDCARE.AGEDCARE.DRI_EVAL_RUN
-- QUERY_WAREHOUSE = COMPUTE_WH;

-- ============================================================================
-- Step 6: Grant privileges on the stage and tables
-- ============================================================================

GRANT READ, WRITE ON STAGE DRI_EVAL_STAGE TO ROLE AI_OBSERVABILITY_USER;
GRANT SELECT, INSERT, UPDATE ON TABLE DRI_EVALUATION_METRICS TO ROLE AI_OBSERVABILITY_USER;
GRANT SELECT, INSERT ON TABLE DRI_EVALUATION_DETAIL TO ROLE AI_OBSERVABILITY_USER;
GRANT SELECT ON TABLE DRI_GROUND_TRUTH TO ROLE AI_OBSERVABILITY_USER;
GRANT SELECT ON TABLE DRI_PROMPT_VERSIONS TO ROLE AI_OBSERVABILITY_USER;
GRANT SELECT ON TABLE DRI_RAG_INDICATORS TO ROLE AI_OBSERVABILITY_USER;
GRANT SELECT ON TABLE ACTIVE_RESIDENT_NOTES TO ROLE AI_OBSERVABILITY_USER;
GRANT SELECT ON TABLE ACTIVE_RESIDENT_MEDICATION TO ROLE AI_OBSERVABILITY_USER;
GRANT SELECT ON TABLE ACTIVE_RESIDENT_OBSERVATIONS TO ROLE AI_OBSERVABILITY_USER;
GRANT SELECT ON TABLE ACTIVE_RESIDENT_ASSESSMENT_FORMS TO ROLE AI_OBSERVABILITY_USER;

-- ============================================================================
-- Step 7: Verify setup
-- ============================================================================

-- Check privileges
SHOW GRANTS TO ROLE AI_OBSERVABILITY_USER;

-- Check tables exist
SHOW TABLES LIKE 'DRI_EVALUATION%';

-- Check stage exists
SHOW STAGES LIKE 'DRI_EVAL%';

-- ============================================================================
-- Usage Examples
-- ============================================================================

-- Run an evaluation using EXECUTE JOB SERVICE:
-- 
-- -- First, drop any existing job run
-- DROP SERVICE IF EXISTS AGEDCARE.AGEDCARE.DRI_EVAL_RUN;
-- 
-- -- Then execute the job
-- EXECUTE JOB SERVICE
-- IN COMPUTE POOL FULLSTACK_COMPUTE_POOL
-- FROM @AGEDCARE.AGEDCARE.DRI_EVAL_STAGE
-- SPEC = 'job-run-spec.yaml'
-- NAME = AGEDCARE.AGEDCARE.DRI_EVAL_RUN
-- QUERY_WAREHOUSE = COMPUTE_WH;

-- Check job status:
-- SELECT SYSTEM$GET_SERVICE_STATUS('AGEDCARE.AGEDCARE.DRI_EVAL_RUN');

-- View logs:
-- SELECT SYSTEM$GET_SERVICE_LOGS('AGEDCARE.AGEDCARE.DRI_EVAL_RUN', 0, 'dri-evaluation');

-- View results in Snowsight:
-- Navigate to: AI & ML > Evaluations > DRI_INTELLIGENCE_AGENT
