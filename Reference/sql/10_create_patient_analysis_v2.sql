-- Healthcare AI Demo - Create simplified PATIENT_ANALYSIS_V2 table
-- This creates a clean, simplified version of the patient analysis table
-- Author: Snowflake Sales Engineering
-- Date: Clean architecture implementation

USE DATABASE HEALTHCARE_DEMO;
USE SCHEMA MEDICAL_NOTES;

-- Create the new simplified table structure
CREATE OR REPLACE TABLE PATIENT_ANALYSIS_V2 (
    PATIENT_ID NUMBER PRIMARY KEY,
    AI_ANALYSIS_JSON VARIANT NOT NULL,  -- The complete AI response (required)
    AI_MODEL_USED VARCHAR DEFAULT 'gpt-4o',  -- Track which model was used
    PROCESSED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Simplified patient analysis table storing only complete AI JSON responses';

-- Migrate existing data where AI_ANALYSIS_JSON exists
INSERT INTO PATIENT_ANALYSIS_V2 (PATIENT_ID, AI_ANALYSIS_JSON, AI_MODEL_USED, PROCESSED_TIMESTAMP)
SELECT 
    PATIENT_ID,
    AI_ANALYSIS_JSON,
    'claude-4-sonnet' as AI_MODEL_USED,  -- These were processed with claude
    PROCESSED_TIMESTAMP
FROM PATIENT_ANALYSIS
WHERE AI_ANALYSIS_JSON IS NOT NULL;

-- Verify migration
SELECT COUNT(*) as migrated_records FROM PATIENT_ANALYSIS_V2;

-- Rename tables to switch over
ALTER TABLE PATIENT_ANALYSIS RENAME TO PATIENT_ANALYSIS_OLD;
ALTER TABLE PATIENT_ANALYSIS_V2 RENAME TO PATIENT_ANALYSIS;

-- Create a view for backward compatibility if needed
CREATE OR REPLACE VIEW PATIENT_ANALYSIS_LEGACY AS
SELECT 
    pa.PATIENT_ID,
    pa.AI_MODEL_USED,
    pa.PROCESSED_TIMESTAMP,
    pa.AI_ANALYSIS_JSON,
    -- Extract individual fields from JSON for legacy queries
    pa.AI_ANALYSIS_JSON:clinical_summary:chief_complaint::TEXT as CHIEF_COMPLAINT,
    pa.AI_ANALYSIS_JSON:clinical_summary:clinical_summary::TEXT as CLINICAL_SUMMARY,
    pa.AI_ANALYSIS_JSON:clinical_summary as SBAR_SUMMARY,
    pa.AI_ANALYSIS_JSON:differential_diagnosis:clinical_findings:key_findings as KEY_FINDINGS,
    pa.AI_ANALYSIS_JSON:differential_diagnosis:diagnostic_assessment:differential_diagnoses as DIFFERENTIAL_DIAGNOSES,
    pa.AI_ANALYSIS_JSON:differential_diagnosis:diagnostic_reasoning::TEXT as DIAGNOSTIC_REASONING,
    pa.AI_ANALYSIS_JSON:treatment_analysis:active_treatments:current_treatments as TREATMENTS_ADMINISTERED,
    pa.AI_ANALYSIS_JSON:treatment_analysis:active_treatments:treatment_effectiveness::TEXT as TREATMENT_EFFECTIVENESS,
    pa.AI_ANALYSIS_JSON:treatment_analysis:clinical_recommendations:evidence_based_recommendations as EVIDENCE_BASED_RECOMMENDATIONS,
    pa.AI_ANALYSIS_JSON:pattern_recognition:clinical_patterns:presentation_type::TEXT as PRESENTATION_TYPE,
    pa.AI_ANALYSIS_JSON:pattern_recognition:clinical_patterns:rare_disease_indicators as RARE_DISEASE_INDICATORS,
    pa.AI_ANALYSIS_JSON:pattern_recognition:anomaly_detection:anomaly_score::FLOAT as ANOMALY_SCORE,
    pa.AI_ANALYSIS_JSON:cost_analysis:cost_drivers:high_cost_indicators as HIGH_COST_INDICATORS,
    pa.AI_ANALYSIS_JSON:cost_analysis:financial_impact:estimated_cost_category::TEXT as ESTIMATED_COST_CATEGORY,
    pa.AI_ANALYSIS_JSON:cost_analysis:resource_utilization as RESOURCE_UTILIZATION,
    pa.AI_ANALYSIS_JSON:quality_metrics:care_quality:quality_indicators as CARE_QUALITY_INDICATORS,
    pa.AI_ANALYSIS_JSON:quality_metrics:care_quality:guideline_adherence as GUIDELINE_ADHERENCE_FLAGS,
    pa.AI_ANALYSIS_JSON:educational_value:teaching_content:teaching_points as TEACHING_POINTS,
    pa.AI_ANALYSIS_JSON:educational_value:teaching_content:clinical_pearls::TEXT as CLINICAL_PEARLS,
    pa.AI_ANALYSIS_JSON:educational_value:assessment_tools:quiz_questions as QUIZ_QUESTIONS
FROM PATIENT_ANALYSIS pa;

-- Grant permissions
GRANT SELECT ON TABLE PATIENT_ANALYSIS TO ROLE PUBLIC;
GRANT SELECT ON VIEW PATIENT_ANALYSIS_LEGACY TO ROLE PUBLIC;
