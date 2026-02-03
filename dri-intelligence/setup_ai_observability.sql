-- =============================================================================
-- AI OBSERVABILITY SETUP FOR DRI INTELLIGENCE
-- =============================================================================
-- This script sets up the Snowflake AI Observability infrastructure for
-- tracking LLM evaluation metrics, quality scores, and audit trails.
-- =============================================================================

USE DATABASE AGEDCARE;
USE SCHEMA AGEDCARE;

-- =============================================================================
-- 1. CREATE EXTERNAL AGENT
-- =============================================================================
-- The EXTERNAL AGENT object stores metadata about the DRI Intelligence
-- application and governs access to traces and evaluation results.

CREATE EXTERNAL AGENT IF NOT EXISTS AGEDCARE.AGEDCARE.DRI_INTELLIGENCE_AGENT
    COMMENT = 'DRI LLM Analysis application for aged care indicator detection. Tracks evaluation metrics, quality scores, and provides audit trail for compliance.';

-- =============================================================================
-- 2. EVALUATION METRICS TABLE
-- =============================================================================
-- Stores aggregated evaluation results from AI Observability runs.
-- This is a local cache for quick Streamlit queries - source of truth
-- is in AI Observability event tables.

CREATE TABLE IF NOT EXISTS AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS (
    EVALUATION_ID VARCHAR(36) NOT NULL DEFAULT UUID_STRING(),
    RUN_ID VARCHAR(64),
    RUN_NAME VARCHAR(256),
    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PROMPT_VERSION VARCHAR(32),
    MODEL_USED VARCHAR(64),
    CLIENT_SYSTEM_KEY VARCHAR(256),
    DATASET_NAME VARCHAR(256),
    TOTAL_RECORDS NUMBER,
    RECORDS_EVALUATED NUMBER,
    
    -- Quality Metrics (from LLM-as-judge)
    AVG_GROUNDEDNESS_SCORE FLOAT,
    AVG_CONTEXT_RELEVANCE_SCORE FLOAT,
    AVG_ANSWER_RELEVANCE_SCORE FLOAT,
    
    -- Accuracy Metrics
    TRUE_POSITIVES NUMBER,
    FALSE_POSITIVES NUMBER,
    TRUE_NEGATIVES NUMBER,
    FALSE_NEGATIVES NUMBER,
    PRECISION_SCORE FLOAT,
    RECALL_SCORE FLOAT,
    F1_SCORE FLOAT,
    FALSE_POSITIVE_RATE FLOAT,
    
    -- Performance Metrics
    AVG_LATENCY_MS NUMBER,
    TOTAL_TOKENS_USED NUMBER,
    ESTIMATED_COST_USD FLOAT,
    
    -- Status
    STATUS VARCHAR(32) DEFAULT 'PENDING',
    ERROR_MESSAGE VARCHAR(16777216),
    
    PRIMARY KEY (EVALUATION_ID)
);

-- =============================================================================
-- 3. EVALUATION DETAIL TABLE
-- =============================================================================
-- Stores per-record evaluation results for drill-down analysis.

CREATE TABLE IF NOT EXISTS AGEDCARE.AGEDCARE.DRI_EVALUATION_DETAIL (
    DETAIL_ID VARCHAR(36) NOT NULL DEFAULT UUID_STRING(),
    EVALUATION_ID VARCHAR(36) NOT NULL,
    RESIDENT_ID NUMBER,
    RECORD_INDEX NUMBER,
    
    -- Input/Output
    INPUT_PROMPT_HASH VARCHAR(64),
    OUTPUT_SUMMARY VARCHAR(16777216),
    INDICATORS_DETECTED NUMBER,
    
    -- Per-record Quality Scores
    GROUNDEDNESS_SCORE FLOAT,
    CONTEXT_RELEVANCE_SCORE FLOAT,
    ANSWER_RELEVANCE_SCORE FLOAT,
    
    -- Accuracy (if ground truth available)
    EXPECTED_INDICATORS VARIANT,
    ACTUAL_INDICATORS VARIANT,
    IS_CORRECT BOOLEAN,
    MISMATCH_DETAILS VARCHAR(16777216),
    
    -- Performance
    LATENCY_MS NUMBER,
    TOKENS_USED NUMBER,
    
    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (DETAIL_ID),
    FOREIGN KEY (EVALUATION_ID) REFERENCES DRI_EVALUATION_METRICS(EVALUATION_ID)
);

-- =============================================================================
-- 4. GROUND TRUTH DATASET TABLE
-- =============================================================================
-- Stores validated test cases with expected outcomes for evaluation.

CREATE TABLE IF NOT EXISTS AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH (
    GROUND_TRUTH_ID VARCHAR(36) NOT NULL DEFAULT UUID_STRING(),
    DATASET_NAME VARCHAR(256) NOT NULL,
    RESIDENT_ID NUMBER NOT NULL,
    CLIENT_SYSTEM_KEY VARCHAR(256),
    
    -- Expected Indicators (manually validated)
    EXPECTED_INDICATORS VARIANT,
    EXPECTED_INDICATOR_COUNT NUMBER,
    
    -- Source of Truth
    VALIDATED_BY VARCHAR(256),
    VALIDATED_TIMESTAMP TIMESTAMP_NTZ,
    VALIDATION_NOTES VARCHAR(16777216),
    
    -- Metadata
    IS_ACTIVE BOOLEAN DEFAULT TRUE,
    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    PRIMARY KEY (GROUND_TRUTH_ID)
);

-- =============================================================================
-- 5. INSERT INITIAL GROUND TRUTH FROM EXISTING FP VALIDATION
-- =============================================================================
-- Migrate any existing manual validation data to ground truth table.

INSERT INTO AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH (DATASET_NAME, RESIDENT_ID, EXPECTED_INDICATORS, EXPECTED_INDICATOR_COUNT, VALIDATED_BY, VALIDATION_NOTES)
SELECT 
    'INITIAL_VALIDATION' as DATASET_NAME,
    RESIDENT_ID,
    ARRAY_AGG(INDICATOR_ID) as EXPECTED_INDICATORS,
    COUNT(*) as EXPECTED_INDICATOR_COUNT,
    'SYSTEM_MIGRATION' as VALIDATED_BY,
    'Migrated from TEST_FP_VALIDATION table' as VALIDATION_NOTES
FROM AGEDCARE.AGEDCARE.TEST_FP_VALIDATION
WHERE MANUAL_REVIEW = 'TRUE_POSITIVE'
GROUP BY RESIDENT_ID;

-- =============================================================================
-- 6. GRANT PERMISSIONS
-- =============================================================================

GRANT SELECT, INSERT, UPDATE ON AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS TO ROLE PUBLIC;
GRANT SELECT, INSERT, UPDATE ON AGEDCARE.AGEDCARE.DRI_EVALUATION_DETAIL TO ROLE PUBLIC;
GRANT SELECT, INSERT, UPDATE ON AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH TO ROLE PUBLIC;

-- =============================================================================
-- 7. VIEWS FOR STREAMLIT
-- =============================================================================

CREATE OR REPLACE VIEW AGEDCARE.AGEDCARE.V_EVALUATION_SUMMARY AS
SELECT 
    e.EVALUATION_ID,
    e.RUN_NAME,
    e.CREATED_TIMESTAMP,
    e.PROMPT_VERSION,
    e.MODEL_USED,
    e.TOTAL_RECORDS,
    e.RECORDS_EVALUATED,
    ROUND(e.AVG_GROUNDEDNESS_SCORE * 100, 1) as GROUNDEDNESS_PCT,
    ROUND(e.AVG_CONTEXT_RELEVANCE_SCORE * 100, 1) as CONTEXT_RELEVANCE_PCT,
    ROUND(e.AVG_ANSWER_RELEVANCE_SCORE * 100, 1) as ANSWER_RELEVANCE_PCT,
    ROUND(e.FALSE_POSITIVE_RATE * 100, 2) as FP_RATE_PCT,
    ROUND(e.F1_SCORE * 100, 1) as F1_PCT,
    e.AVG_LATENCY_MS,
    e.STATUS
FROM AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS e
ORDER BY e.CREATED_TIMESTAMP DESC;

CREATE OR REPLACE VIEW AGEDCARE.AGEDCARE.V_FP_RATE_TREND AS
SELECT 
    DATE_TRUNC('day', CREATED_TIMESTAMP) as EVAL_DATE,
    PROMPT_VERSION,
    MODEL_USED,
    COUNT(*) as EVAL_COUNT,
    ROUND(AVG(FALSE_POSITIVE_RATE) * 100, 2) as AVG_FP_RATE_PCT,
    ROUND(AVG(AVG_GROUNDEDNESS_SCORE) * 100, 1) as AVG_GROUNDEDNESS_PCT
FROM AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS
WHERE STATUS = 'COMPLETED'
GROUP BY DATE_TRUNC('day', CREATED_TIMESTAMP), PROMPT_VERSION, MODEL_USED
ORDER BY EVAL_DATE DESC;

COMMIT;
