-- Healthcare AI Demo - Patient Subset and Additional Tables
-- This script creates the patient subset table and additional analysis tables
-- Author: Snowflake Sales Engineering
-- Date: Created for Phase 3 development

USE DATABASE HEALTHCARE_DEMO;
USE SCHEMA MEDICAL_NOTES;

-- PATIENT_SUBSET removed: use PMC_PATIENTS directly as needed

-- Drug safety analysis table
CREATE OR REPLACE TABLE MEDICATION_ANALYSIS (
    PATIENT_ID NUMBER PRIMARY KEY,
    EXTRACTED_MEDICATIONS VARIANT, -- Array of {name, dosage, frequency, route}
    DRUG_INTERACTIONS VARIANT, -- Array of {drug1, drug2, severity, description}
    CONTRAINDICATIONS VARIANT, -- Array of {medication, condition, risk_level}
    POLYPHARMACY_RISK_SCORE NUMBER, -- Risk score based on number and types of meds
    ANALYSIS_DATE TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Medication extraction and safety analysis results';

-- Cost analysis table
CREATE OR REPLACE TABLE COST_ANALYSIS (
    PATIENT_ID NUMBER PRIMARY KEY,
    EXTRACTED_PROCEDURES VARIANT, -- Array of {procedure, CPT_code, estimated_cost}
    EXTRACTED_CONDITIONS VARIANT, -- Array of {condition, ICD10_code, cost_impact}
    HIGH_COST_INDICATORS VARIANT, -- ICU, surgery, complications, etc.
    ESTIMATED_ENCOUNTER_COST NUMBER(10,2),
    COST_CATEGORY VARCHAR, -- 'low', 'medium', 'high', 'very_high'
    COST_DRIVERS TEXT, -- Narrative explanation
    ANALYSIS_DATE TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Cost analysis based on extracted procedures and conditions';

-- Procedure cost reference table
CREATE OR REPLACE TABLE PROCEDURE_COSTS (
    PROCEDURE_NAME VARCHAR,
    CPT_CODE VARCHAR,
    ESTIMATED_COST NUMBER(10,2),
    COST_RANGE_LOW NUMBER(10,2),
    COST_RANGE_HIGH NUMBER(10,2),
    CATEGORY VARCHAR,
    PRIMARY KEY (PROCEDURE_NAME, CPT_CODE)
) COMMENT = 'Reference table for procedure cost estimates';

-- Insert common procedure costs (sample data)
INSERT INTO PROCEDURE_COSTS (PROCEDURE_NAME, CPT_CODE, ESTIMATED_COST, COST_RANGE_LOW, COST_RANGE_HIGH, CATEGORY)
VALUES 
    -- Imaging procedures
    ('MRI Brain without contrast', '70551', 1500.00, 800.00, 3000.00, 'Imaging'),
    ('MRI Brain with contrast', '70552', 2000.00, 1200.00, 3500.00, 'Imaging'),
    ('CT Head without contrast', '70450', 825.00, 500.00, 1500.00, 'Imaging'),
    ('CT Chest with contrast', '71260', 1200.00, 700.00, 2000.00, 'Imaging'),
    ('X-ray Chest', '71045', 150.00, 100.00, 300.00, 'Imaging'),
    ('Echocardiogram', '93306', 800.00, 500.00, 1500.00, 'Imaging'),
    
    -- Laboratory tests
    ('Complete Blood Count', '85025', 30.00, 20.00, 50.00, 'Laboratory'),
    ('Comprehensive Metabolic Panel', '80053', 50.00, 30.00, 80.00, 'Laboratory'),
    ('Lipid Panel', '80061', 75.00, 50.00, 120.00, 'Laboratory'),
    ('Hemoglobin A1C', '83036', 60.00, 40.00, 100.00, 'Laboratory'),
    ('Thyroid Function Tests', '84443', 85.00, 60.00, 150.00, 'Laboratory'),
    
    -- Procedures
    ('Colonoscopy', '45380', 1800.00, 1200.00, 3000.00, 'Procedure'),
    ('Upper Endoscopy', '43235', 1500.00, 1000.00, 2500.00, 'Procedure'),
    ('Cardiac Catheterization', '93458', 5000.00, 3000.00, 8000.00, 'Procedure'),
    ('Bronchoscopy', '31622', 2500.00, 1500.00, 4000.00, 'Procedure'),
    
    -- Surgery
    ('Appendectomy', '44970', 15000.00, 10000.00, 25000.00, 'Surgery'),
    ('Cholecystectomy', '47562', 20000.00, 15000.00, 30000.00, 'Surgery'),
    ('Total Knee Replacement', '27447', 35000.00, 25000.00, 50000.00, 'Surgery'),
    ('Coronary Artery Bypass', '33533', 75000.00, 50000.00, 120000.00, 'Surgery'),
    
    -- ICU/Critical Care
    ('ICU per day', '99291', 3500.00, 2500.00, 5000.00, 'Critical Care'),
    ('Ventilator per day', '94002', 1500.00, 1000.00, 2500.00, 'Critical Care'),
    ('Dialysis session', '90935', 500.00, 350.00, 800.00, 'Critical Care');

-- Common drug interactions reference table
CREATE OR REPLACE TABLE DRUG_INTERACTIONS_REFERENCE (
    DRUG1 VARCHAR,
    DRUG2 VARCHAR,
    SEVERITY VARCHAR, -- 'MAJOR', 'MODERATE', 'MINOR'
    DESCRIPTION TEXT,
    PRIMARY KEY (DRUG1, DRUG2)
) COMMENT = 'Reference table for known drug interactions';

-- Insert common drug interactions
INSERT INTO DRUG_INTERACTIONS_REFERENCE (DRUG1, DRUG2, SEVERITY, DESCRIPTION)
VALUES 
    ('Warfarin', 'Aspirin', 'MAJOR', 'Increased risk of bleeding'),
    ('Warfarin', 'Amiodarone', 'MAJOR', 'Increased INR and bleeding risk'),
    ('Metformin', 'Contrast dye', 'MAJOR', 'Risk of lactic acidosis'),
    ('ACE inhibitors', 'Potassium supplements', 'MODERATE', 'Risk of hyperkalemia'),
    ('Statins', 'Clarithromycin', 'MAJOR', 'Increased risk of rhabdomyolysis'),
    ('SSRIs', 'NSAIDs', 'MODERATE', 'Increased risk of GI bleeding'),
    ('Digoxin', 'Amiodarone', 'MAJOR', 'Digoxin toxicity risk'),
    ('Methotrexate', 'NSAIDs', 'MAJOR', 'Increased methotrexate toxicity');

-- Enable change tracking on new table for Cortex Search
-- Removed change tracking for deprecated PATIENT_SUBSET

-- Drop the existing Cortex Search service
-- Cortex Search service now defined on PMC_PATIENTS (see 01_create_database_objects.sql)

-- Verify the data
-- Removed PATIENT_SUBSET verification/confirmation queries