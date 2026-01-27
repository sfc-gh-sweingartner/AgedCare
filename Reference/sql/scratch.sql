
-- Use the healthcare database and schema
USE DATABASE HEALTHCARE_DEMO;
USE SCHEMA MEDICAL_NOTES;

-- process 20 more records into the processed tables
CALL HEALTHCARE_DEMO.MEDICAL_NOTES.BATCH_PROCESS_PATIENTS(10, 20);