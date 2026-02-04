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
    STATUS VARCHAR(50) DEFAULT 'PENDING'
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
-- Step 3: Create External Access Integration for PyPI (if needed)
-- ============================================================================
-- Note: The container needs network access to reach Snowflake endpoints.
-- If you don't already have an external access integration, create one:

-- CREATE OR REPLACE NETWORK RULE snowflake_egress_rule
--     MODE = EGRESS
--     TYPE = HOST_PORT
--     VALUE_LIST = ('*.snowflakecomputing.com:443', '*.amazonaws.com:443');
--
-- CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION snowflake_egress_integration
--     ALLOWED_NETWORK_RULES = (snowflake_egress_rule)
--     ENABLED = TRUE;

-- ============================================================================
-- Step 4: Create the Job Service
-- ============================================================================

CREATE SERVICE IF NOT EXISTS DRI_EVALUATION_JOB
    IN COMPUTE POOL STREAMLIT_COMPUTE_POOL
    FROM SPECIFICATION $$
spec:
  containers:
  - name: dri-evaluation
    image: /AGEDCARE/AGEDCARE/DRI_IMAGES/dri-evaluation:latest
    env:
      SNOWFLAKE_DATABASE: "AGEDCARE"
      SNOWFLAKE_SCHEMA: "AGEDCARE"
      SNOWFLAKE_WAREHOUSE: "COMPUTE_WH"
      TRULENS_OTEL_TRACING: "1"
    resources:
      requests:
        memory: 4Gi
        cpu: 2000m
      limits:
        memory: 8Gi
        cpu: 4000m
$$
    MIN_INSTANCES = 0
    MAX_INSTANCES = 1
    AUTO_SUSPEND_SECS = 300
    QUERY_WAREHOUSE = COMPUTE_WH;

-- ============================================================================
-- Step 5: Grant necessary privileges
-- ============================================================================

-- Grant usage on the service to roles that need to run evaluations
GRANT USAGE ON SERVICE DRI_EVALUATION_JOB TO ROLE SYSADMIN;
GRANT USAGE ON SERVICE DRI_EVALUATION_JOB TO ROLE DATA_ENGINEER;

-- ============================================================================
-- Step 6: Verify deployment
-- ============================================================================

SHOW SERVICES LIKE 'DRI_EVALUATION%';
SELECT SYSTEM$GET_SERVICE_STATUS('DRI_EVALUATION_JOB');

-- ============================================================================
-- Usage Examples
-- ============================================================================

-- Run an evaluation:
-- EXECUTE JOB SERVICE DRI_EVALUATION_JOB
--     WITH PARAMETERS (
--         RUN_NAME => 'MyEvaluation',
--         PROMPT_VERSION => 'v1.0',
--         MODEL => 'claude-3-5-sonnet',
--         SAMPLE_SIZE => 10
--     );

-- Check job status:
-- SELECT SYSTEM$GET_SERVICE_STATUS('DRI_EVALUATION_JOB');

-- View logs:
-- SELECT SYSTEM$GET_SERVICE_LOGS('DRI_EVALUATION_JOB', 0, 'dri-evaluation');
