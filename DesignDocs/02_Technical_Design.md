# DRI Intelligence Solution - Technical Design Document

## Document Information
| Field | Value |
|-------|-------|
| Version | 1.1 |
| Created | 2026-01-28 |
| Status | Draft |
| Prerequisite | Functional Design v1.3 (Approved) |

---

## 1. Environment Configuration

### 1.1 Database and Schema
```sql
-- POC Environment
DATABASE: AGEDCARE
SCHEMA: AGEDCARE
WAREHOUSE: MYWH (for SQL execution only - Streamlit runs on SPCS, Cortex is serverless)
```

### 1.2 Required Snowflake Features
| Feature | Purpose | Notes |
|---------|---------|-------|
| Cortex Complete | LLM analysis (Claude 4.5) | Available in Australia region |
| Cortex Search | RAG indicator lookup | For semantic search of indicator definitions |
| SPCS | Streamlit hosting | Snowpark Container Services |
| Dynamic Tables | Real-time data refresh | For source data views |

---

## 2. Data Model DDL

### 2.1 Source Tables (Demo Data - Static Tables from Excel)

For the POC, we convert the dynamic table definitions to static tables loaded from the Excel demo data.

```sql
-- ============================================================================
-- SOURCE TABLES (Static versions for POC demo data)
-- ============================================================================

-- Table 1: Active Resident Medical Profile
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICAL_PROFILE (
    RESIDENT_ID NUMBER NOT NULL,
    EVENT_DATE TIMESTAMP_NTZ,
    SPECIAL_NEEDS VARCHAR(16777216),
    ENTERED_BY_USER VARCHAR(256),
    ALLERGIES VARCHAR(16777216),
    ALLERGY_NOTES VARCHAR(16777216),
    ALLERGY_EXCLUSION VARCHAR(256),
    HAS_UNCODED_ALLERGIES BOOLEAN,
    HAS_GLUTEN_INTOLERANCE BOOLEAN,
    DIET VARCHAR(256),
    USUAL_BOWEL_PATTERN VARCHAR(256),
    HEIGHT NUMBER(10,2),
    WEIGHT_UPON_ADMISSION NUMBER(10,2),
    SYSTEM_KEY VARCHAR(256),
    LOAD_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Table 2: Active Resident Assessment Forms
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_ASSESSMENT_FORMS (
    BATCH_ID NUMBER NOT NULL,
    RESIDENT_ID NUMBER NOT NULL,
    EVENT_DATE TIMESTAMP_NTZ,
    FORM_ID NUMBER,
    FORM_NAME VARCHAR(512),
    ELEMENT_NO NUMBER,
    ELEMENT_NAME VARCHAR(1024),
    ELEMENT_TYPE VARCHAR(64),
    REPORT_CODE VARCHAR(64),
    QUESTION_CODE VARCHAR(64),
    ITEM_CODE VARCHAR(64),
    ITEM_NAME VARCHAR(512),
    RESPONSE VARCHAR(16777216),
    RESPONSE_OTHER VARCHAR(16777216),
    ENTERED_BY_USER VARCHAR(256),
    SYSTEM_KEY VARCHAR(256),
    LOAD_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Table 3: Active Resident Medication
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION (
    RESIDENT_ID NUMBER NOT NULL,
    MED_ID NUMBER,
    MED_NAME VARCHAR(512),
    MED_ROUTE VARCHAR(32),
    MED_STATUS VARCHAR(32),
    MED_START_DATE DATE,
    MED_END_DATE TIMESTAMP_NTZ,
    UPDATED_DATE TIMESTAMP_NTZ,
    SYSTEM_KEY VARCHAR(256),
    LOAD_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Table 4: Active Resident Notes
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES (
    PROGRESS_NOTE_ID NUMBER NOT NULL,
    PROGRESS_NOTE_TYPE VARCHAR(64),
    ADDITIONAL_NOTE_ID NUMBER,
    RESIDENT_ID NUMBER NOT NULL,
    EVENT_DATE TIMESTAMP_NTZ,
    PROGRESS_NOTE VARCHAR(16777216),
    ENTERED_BY_USER VARCHAR(256),
    NOTE_TYPE VARCHAR(64),
    SYSTEM_KEY VARCHAR(256),
    LOAD_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Table 5: Active Resident Observations
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS (
    RESIDENT_ID NUMBER NOT NULL,
    CHART_NAME VARCHAR(256),
    OBSERVATION_GROUP_ID NUMBER,
    OBSERVATION_ID NUMBER,
    EVENT_DATE TIMESTAMP_NTZ,
    CHART_SECTION VARCHAR(256),
    CHART_LABEL VARCHAR(256),
    OBSERVATION_VALUE VARCHAR(1024),
    ENTERED_BY_USER VARCHAR(256),
    SYSTEM_KEY VARCHAR(256),
    LOAD_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Table 6: Active Resident Observation Group
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATION_GROUP (
    OBSERVATION_GROUP_ID NUMBER NOT NULL,
    CHART_TEMPLATE_ID NUMBER,
    CHART_NAME VARCHAR(256),
    RESIDENT_ID NUMBER NOT NULL,
    OBSERVATION_STATUS VARCHAR(32),
    OBSERVATION_TYPE VARCHAR(256),
    OBSERVATION_LOCATION VARCHAR(256),
    EVENT_DATE TIMESTAMP_NTZ,
    OBSERVATION_DESCRIPTION VARCHAR(16777216),
    ENTERED_BY_USER VARCHAR(256),
    SYSTEM_KEY VARCHAR(256),
    LOAD_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

### 2.2 DRI Output Tables (Fact/Dimension Model)

```sql
-- ============================================================================
-- DRI OUTPUT TABLES (Compatible with existing Power BI reports)
-- ============================================================================

-- DRI Deficit Detail (Fact Table)
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.DRI_DEFICIT_DETAIL (
    RESIDENT_ID NUMBER NOT NULL,
    LOAD_TIMESTAMP TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    DEFICIT_ID VARCHAR(64) NOT NULL,
    RULE_NUMBER NUMBER,
    RULE_DESCRIPTION VARCHAR(16777216),
    SOURCE_ID VARCHAR(64),
    SOURCE_TABLE VARCHAR(256),
    SOURCE_TYPE VARCHAR(256),
    RESULT VARCHAR(16777216),
    ENTERED_BY_USER VARCHAR(256),
    EVENT_DATE DATE,
    RULE_STATUS VARCHAR(32),
    EXPIRY_DAYS NUMBER,
    CLIENT_NAME VARCHAR(256)
)
CHANGE_TRACKING = TRUE;

-- DRI Deficit Status (Status Tracking)
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.DRI_DEFICIT_STATUS (
    RESIDENT_ID NUMBER NOT NULL,
    LOAD_TIMESTAMP TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    DEFICIT_ID VARCHAR(64) NOT NULL,
    DEFICIT_STATUS VARCHAR(32),
    DEFICIT_START_DATE DATE,
    DEFICIT_EXPIRY_DATE DATE,
    DEFICIT_LAST_OCCURRENCE DATE,
    RULE_NUMBER NUMBER
)
CHANGE_TRACKING = TRUE;

-- DRI Deficit Summary (Aggregated for Power BI)
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.DRI_DEFICIT_SUMMARY (
    RESIDENT_ID NUMBER NOT NULL,
    LOAD_TIMESTAMP TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    DRI_SCORE NUMBER(5,4),
    SEVERITY_BAND VARCHAR(64)
)
CHANGE_TRACKING = TRUE;

-- DRI Severity Bands (Lookup Table)
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.DRI_SEVERITY (
    DRI_SEVERITY_ID NUMBER NOT NULL,
    DRI_SEVERITY_NAME VARCHAR(64),
    DRI_SEVERITY_MINIMUM_VALUE NUMBER(5,4),
    DRI_SEVERITY_MAXIMUM_VALUE NUMBER(5,4)
);

INSERT INTO AGEDCARE.AGEDCARE.DRI_SEVERITY VALUES
(1, 'Low', 0.0000, 0.2000),
(2, 'Medium', 0.2001, 0.4000),
(3, 'High', 0.4001, 0.6000),
(4, 'Very High', 0.6001, 1.0000);
```

### 2.3 New Intelligence Tables

```sql
-- ============================================================================
-- NEW TABLES FOR LLM INTELLIGENCE ENGINE
-- ============================================================================

-- DRI LLM Analysis (Raw LLM Output for Audit)
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS (
    ANALYSIS_ID VARCHAR(36) NOT NULL DEFAULT UUID_STRING(),
    RESIDENT_ID NUMBER NOT NULL,
    CLIENT_SYSTEM_KEY VARCHAR(256),
    ANALYSIS_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    MODEL_USED VARCHAR(64),
    PROMPT_VERSION VARCHAR(32),
    CLIENT_CONFIG_VERSION VARCHAR(32),
    RAW_RESPONSE VARIANT,
    PROCESSING_TIME_MS NUMBER,
    BATCH_RUN_ID VARCHAR(36),
    PRIMARY KEY (ANALYSIS_ID)
);

-- DRI Review Queue (Aggregate DRI Changes Pending Approval)
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE (
    QUEUE_ID VARCHAR(36) NOT NULL DEFAULT UUID_STRING(),
    ANALYSIS_ID VARCHAR(36),
    RESIDENT_ID NUMBER NOT NULL,
    CLIENT_SYSTEM_KEY VARCHAR(256),
    CURRENT_DRI_SCORE NUMBER(5,4),
    PROPOSED_DRI_SCORE NUMBER(5,4),
    CURRENT_SEVERITY_BAND VARCHAR(64),
    PROPOSED_SEVERITY_BAND VARCHAR(64),
    INDICATORS_ADDED NUMBER,
    INDICATORS_REMOVED NUMBER,
    INDICATOR_CHANGES_JSON VARIANT,
    CHANGE_SUMMARY VARCHAR(16777216),
    STATUS VARCHAR(32) DEFAULT 'PENDING',
    REVIEWER_USER VARCHAR(256),
    REVIEWER_NOTES VARCHAR(16777216),
    EXCLUDED_INDICATORS VARIANT,
    REVIEW_TIMESTAMP TIMESTAMP_NTZ,
    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (QUEUE_ID)
);

-- DRI Client Configuration (Multi-tenant - one config per end customer)
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG (
    CONFIG_ID VARCHAR(36) NOT NULL DEFAULT UUID_STRING(),
    CLIENT_SYSTEM_KEY VARCHAR(256) NOT NULL,
    CLIENT_NAME VARCHAR(256),
    DESCRIPTION VARCHAR(16777216),
    CONFIG_JSON VARIANT,
    VERSION VARCHAR(32),
    IS_ACTIVE BOOLEAN DEFAULT TRUE,
    CREATED_BY VARCHAR(256),
    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    MODIFIED_BY VARCHAR(256),
    MODIFIED_TIMESTAMP TIMESTAMP_NTZ,
    PRIMARY KEY (CONFIG_ID)
);

-- DRI Client Form Mappings (Client-specific field mappings)
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.DRI_CLIENT_FORM_MAPPINGS (
    MAPPING_ID VARCHAR(36) NOT NULL DEFAULT UUID_STRING(),
    CLIENT_SYSTEM_KEY VARCHAR(256) NOT NULL,
    SOURCE_TABLE VARCHAR(256) NOT NULL,
    FORM_IDENTIFIER VARCHAR(256),
    FIELD_NAME VARCHAR(256) NOT NULL,
    MAPPED_INDICATOR VARCHAR(64),
    MAPPING_TYPE VARCHAR(32),
    MAPPING_RULES VARIANT,
    IS_ACTIVE BOOLEAN DEFAULT TRUE,
    NOTES VARCHAR(16777216),
    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (MAPPING_ID)
);

-- DRI Client Indicator Overrides (Client-specific indicator settings)
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.DRI_CLIENT_INDICATOR_OVERRIDES (
    OVERRIDE_ID VARCHAR(36) NOT NULL DEFAULT UUID_STRING(),
    CLIENT_SYSTEM_KEY VARCHAR(256) NOT NULL,
    INDICATOR_ID VARCHAR(64) NOT NULL,
    OVERRIDE_TYPE VARCHAR(32) NOT NULL,
    OVERRIDE_VALUE VARIANT,
    REASON VARCHAR(16777216),
    IS_ACTIVE BOOLEAN DEFAULT TRUE,
    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (OVERRIDE_ID)
);

-- DRI Prompt Versions
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS (
    PROMPT_ID VARCHAR(36) NOT NULL DEFAULT UUID_STRING(),
    VERSION_NUMBER VARCHAR(32),
    PROMPT_TEXT VARCHAR(16777216),
    DESCRIPTION VARCHAR(16777216),
    CREATED_BY VARCHAR(256),
    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    IS_ACTIVE BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (PROMPT_ID)
);

-- DRI RAG Indicators (Knowledge Base)
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS (
    INDICATOR_ID VARCHAR(64) NOT NULL,
    DEFICIT_ID VARCHAR(64),
    INDICATOR_NAME VARCHAR(256),
    DEFINITION VARCHAR(16777216),
    KEYWORDS VARIANT,
    INCLUSION_CRITERIA VARCHAR(16777216),
    EXCLUSION_CRITERIA VARCHAR(16777216),
    TEMPORAL_TYPE VARCHAR(32),
    DEFAULT_EXPIRY_DAYS NUMBER,
    EXAMPLES VARIANT,
    PRIMARY KEY (INDICATOR_ID)
);

-- DRI RAG Decisions (Historical Decisions for Learning)
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.DRI_RAG_DECISIONS (
    DECISION_ID VARCHAR(36) NOT NULL DEFAULT UUID_STRING(),
    DEFICIT_ID VARCHAR(64),
    SOURCE_TEXT VARCHAR(16777216),
    DECISION VARCHAR(32),
    REASONING VARCHAR(16777216),
    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (DECISION_ID)
);

-- DRI Audit Log (All System Events)
CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.DRI_AUDIT_LOG (
    LOG_ID VARCHAR(36) NOT NULL DEFAULT UUID_STRING(),
    EVENT_TYPE VARCHAR(64),
    RESIDENT_ID NUMBER,
    USER_NAME VARCHAR(256),
    EVENT_DETAILS VARIANT,
    CREATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (LOG_ID)
);
```

### 2.4 Cortex Search Service

```sql
-- ============================================================================
-- CORTEX SEARCH SERVICE FOR RAG
-- ============================================================================

CREATE OR REPLACE CORTEX SEARCH SERVICE AGEDCARE.AGEDCARE.DRI_INDICATOR_SEARCH
    ON AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS
    ATTRIBUTES INDICATOR_ID, DEFICIT_ID, INDICATOR_NAME, TEMPORAL_TYPE
    WAREHOUSE = MYWH
    TARGET_LAG = '1 hour'
    AS (
        SELECT 
            INDICATOR_ID,
            DEFICIT_ID,
            INDICATOR_NAME,
            TEMPORAL_TYPE,
            DEFINITION || ' ' || COALESCE(INCLUSION_CRITERIA, '') AS SEARCHABLE_TEXT
        FROM AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS
    );
```

---

## 3. DRI Indicator Reference Data

### 3.1 33 DRI Deficit Indicators

```sql
-- ============================================================================
-- DRI RAG INDICATORS - ALL 33 DEFICITS
-- ============================================================================

INSERT INTO AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS 
(INDICATOR_ID, DEFICIT_ID, INDICATOR_NAME, DEFINITION, TEMPORAL_TYPE, DEFAULT_EXPIRY_DAYS, INCLUSION_CRITERIA, EXCLUSION_CRITERIA) 
VALUES
-- RESPIRATORY DOMAIN
('RESP_01', 'D001', 'COPD/Emphysema', 'Chronic obstructive pulmonary disease or emphysema diagnosis', 'chronic', NULL, 
 'Documented COPD, emphysema, or chronic bronchitis diagnosis; oxygen therapy requirement; spirometry results indicating obstruction',
 'Family member has COPD; historical resolved condition; suspected but not confirmed'),

('RESP_02', 'D002', 'Asthma', 'Active asthma requiring ongoing management', 'chronic', NULL,
 'Documented asthma diagnosis; use of bronchodilators or inhaled corticosteroids; history of asthma exacerbations',
 'Family member has asthma; childhood asthma now resolved; reactive airway disease not confirmed as asthma'),

('RESP_03', 'D003', 'Respiratory Infection', 'Acute respiratory infection including pneumonia, bronchitis', 'acute', 30,
 'Documented pneumonia, bronchitis, or other respiratory infection; antibiotic treatment for respiratory infection; positive cultures',
 'Suspected but not confirmed infection; prophylactic antibiotics; historical resolved infection'),

-- CARDIOVASCULAR DOMAIN
('CARD_01', 'D004', 'Heart Failure', 'Congestive heart failure or cardiac insufficiency', 'chronic', NULL,
 'Documented CHF, congestive cardiac failure; ejection fraction documented; diuretic therapy for heart failure; fluid restriction orders',
 'Family history of heart disease; stable well-controlled condition without active symptoms'),

('CARD_02', 'D005', 'Atrial Fibrillation', 'Atrial fibrillation requiring anticoagulation', 'chronic', NULL,
 'Documented AF or AFib; anticoagulant therapy (warfarin, NOACs); rate or rhythm control medications',
 'Historical AF now resolved; single episode of AF'),

('CARD_03', 'D006', 'Hypertension', 'Uncontrolled or high-risk hypertension', 'chronic', NULL,
 'BP readings consistently above target; multiple antihypertensive medications; documented end-organ damage from hypertension',
 'Well-controlled hypertension on stable medication; white coat hypertension'),

-- NEUROLOGICAL DOMAIN
('NEURO_01', 'D007', 'Dementia', 'Dementia of any type including Alzheimer\'s', 'chronic', NULL,
 'Documented dementia diagnosis; cognitive assessment scores indicating dementia; behavior changes consistent with dementia',
 'Delirium (acute confusion); mild cognitive impairment without dementia diagnosis; family member has dementia'),

('NEURO_02', 'D008', 'Stroke/CVA', 'History of stroke or cerebrovascular accident', 'chronic', NULL,
 'Documented stroke or TIA; neurological deficits from CVA; rehabilitation for stroke',
 'Family history of stroke; suspected TIA not confirmed'),

('NEURO_03', 'D009', 'Parkinson\'s Disease', 'Parkinson\'s disease or parkinsonism', 'chronic', NULL,
 'Documented Parkinson\'s diagnosis; dopaminergic medications; movement disorder symptoms',
 'Drug-induced parkinsonism; essential tremor'),

('NEURO_04', 'D010', 'Epilepsy/Seizures', 'Seizure disorder requiring anticonvulsant therapy', 'chronic', NULL,
 'Documented epilepsy; anticonvulsant medications; witnessed seizure activity',
 'Single febrile seizure; seizure from acute cause now resolved'),

-- DIABETES DOMAIN
('DM_01', 'D011', 'Diabetes Type 1', 'Insulin-dependent diabetes mellitus', 'chronic', NULL,
 'Documented Type 1 diabetes; insulin therapy; HbA1c monitoring',
 'Type 2 diabetes; gestational diabetes; family member has diabetes'),

('DM_02', 'D012', 'Diabetes Type 2', 'Non-insulin dependent diabetes mellitus', 'chronic', NULL,
 'Documented Type 2 diabetes; oral hypoglycemics or insulin; blood glucose monitoring',
 'Prediabetes; impaired glucose tolerance; family member has diabetes'),

('DM_03', 'D013', 'Diabetic Complications', 'Complications from diabetes (retinopathy, neuropathy, nephropathy)', 'chronic', NULL,
 'Documented diabetic retinopathy, neuropathy, or nephropathy; foot ulcers related to diabetes',
 'Neuropathy from other causes; retinopathy from other causes'),

-- FALLS DOMAIN
('FALL_01', 'D014', 'Fall Risk - High', 'High fall risk assessment or recent fall', 'acute', 90,
 'Fall risk assessment score indicating high risk; documented fall in past 90 days; multiple falls history',
 'Low fall risk score; environmental fall (tripping hazard removed)'),

('FALL_02', 'D015', 'Fracture History', 'Recent fracture from fall', 'acute', 180,
 'Documented fracture from fall; X-ray confirmed fracture; surgical repair of fracture',
 'Pathological fracture from disease; historical healed fracture'),

-- SKIN INTEGRITY DOMAIN
('SKIN_01', 'D016', 'Pressure Injury', 'Pressure ulcer or pressure injury any stage', 'acute', 90,
 'Documented pressure injury Stage 1-4; wound care orders; pressure relieving devices',
 'Healed pressure injury; skin tear (not pressure related)'),

('SKIN_02', 'D017', 'Skin Tear', 'Skin tear or wound', 'acute', 30,
 'Documented skin tear; wound dressing orders; fragile skin noted',
 'Healed skin tear; surgical wound'),

('SKIN_03', 'D018', 'Chronic Wound', 'Non-healing wound requiring ongoing care', 'chronic', NULL,
 'Wound present >30 days; wound care specialist involvement; negative pressure wound therapy',
 'Acute wound expected to heal; surgical site healing normally'),

-- NUTRITION DOMAIN
('NUTR_01', 'D019', 'Malnutrition Risk', 'At risk or diagnosed malnutrition', 'chronic', NULL,
 'BMI <18.5; unintentional weight loss >5% in 3 months; low albumin; dietary supplements prescribed',
 'Weight loss from fluid shifts; intentional weight loss'),

('NUTR_02', 'D020', 'Weight Loss >5%', 'Significant unintentional weight loss', 'acute', 90,
 'Documented weight loss >5% in 3-6 months; weight monitoring orders; nutritional intervention',
 'Intentional weight loss; weight fluctuation from fluid balance'),

('NUTR_03', 'D021', 'Dysphagia', 'Swallowing difficulty requiring modified diet', 'chronic', NULL,
 'Speech pathology assessment; modified texture diet; thickened fluids',
 'Temporary dysphagia post-procedure; resolved dysphagia'),

-- CONTINENCE DOMAIN
('CONT_01', 'D022', 'Urinary Incontinence', 'Urinary incontinence requiring management', 'chronic', NULL,
 'Documented urinary incontinence; continence aids in use; bladder chart showing incontinence',
 'Temporary incontinence from UTI; stress incontinence well-managed'),

('CONT_02', 'D023', 'Fecal Incontinence', 'Bowel incontinence requiring management', 'chronic', NULL,
 'Documented fecal incontinence; bowel management program; protective underwear for bowel',
 'Temporary diarrhea; laxative-induced loose stools'),

('CONT_03', 'D024', 'UTI Recurrent', 'Recurrent urinary tract infections', 'recurrent', 30,
 '>2 UTIs in 6 months; prophylactic antibiotics for UTI; urine culture positive',
 'Single UTI episode; asymptomatic bacteriuria'),

-- PAIN DOMAIN
('PAIN_01', 'D025', 'Chronic Pain', 'Chronic pain requiring ongoing management', 'chronic', NULL,
 'Pain >3 months duration; regular analgesia; pain specialist involvement',
 'Acute pain expected to resolve; well-controlled chronic pain'),

('PAIN_02', 'D026', 'Pain Assessment High', 'Pain score consistently elevated', 'acute', 14,
 'Pain score >6/10 consistently; breakthrough pain medication use; pain affecting function',
 'Procedural pain; pain well-controlled with current regimen'),

-- MENTAL HEALTH DOMAIN
('MH_01', 'D027', 'Depression', 'Major depression or depressive disorder', 'chronic', NULL,
 'Documented depression diagnosis; antidepressant medications; mental health review',
 'Grief reaction; adjustment disorder; family member has depression'),

('MH_02', 'D028', 'Anxiety', 'Anxiety disorder requiring treatment', 'chronic', NULL,
 'Documented anxiety disorder; anxiolytic medications; psychological therapy for anxiety',
 'Situational anxiety; anxiety symptoms without diagnosis'),

('MH_03', 'D029', 'Behavioral Symptoms', 'Behavioral and psychological symptoms (BPSD)', 'chronic', NULL,
 'Documented BPSD; antipsychotic medications; behavior support plan',
 'Delirium-related behavior; acute distress behavior'),

-- MEDICATION DOMAIN
('MED_01', 'D030', 'Polypharmacy', '9 or more regular medications', 'chronic', NULL,
 'Medication chart shows >=9 regular medications; pharmacy review recommended',
 'PRN medications only; short-term additional medications'),

('MED_02', 'D031', 'High-Risk Medications', 'On anticoagulants, opioids, or insulin', 'chronic', NULL,
 'Warfarin, NOAC, opioid, or insulin prescribed; medication monitoring required',
 'Short-term opioid for acute pain; discontinued high-risk medication'),

-- INFECTION DOMAIN
('INF_01', 'D032', 'Infection Current', 'Active infection requiring treatment', 'acute', 14,
 'Documented active infection; antibiotic therapy; infection control precautions',
 'Colonization without infection; resolved infection'),

-- FUNCTIONAL DOMAIN
('FUNC_01', 'D033', 'Functional Decline', 'Declining ADL independence', 'chronic', NULL,
 'ADL assessment showing decline; increased assistance required; OT/PT intervention',
 'Temporary decline during acute illness; stable ADL function');
```

---

## 4. LLM Prompt Templates

### 4.1 Comprehensive DRI Analysis Prompt

```sql
-- Insert initial active prompt version
INSERT INTO AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS 
(VERSION_NUMBER, PROMPT_TEXT, DESCRIPTION, CREATED_BY, IS_ACTIVE)
VALUES (
'v1.0',
'You are an expert aged care clinical analyst specializing in the Deteriorating Resident Index (DRI) assessment system. Your task is to analyze resident records to identify DRI deficit indicators.

CRITICAL INSTRUCTIONS:
1. Only flag conditions that apply DIRECTLY to this resident
2. Do NOT flag conditions mentioned for family members (e.g., "son has asthma" is NOT a resident condition)
3. Do NOT flag historical conditions that have resolved
4. Do NOT flag negated statements (e.g., "no signs of diabetes", "nil respiratory issues")
5. Identify temporal type (acute vs chronic) for each indicator
6. Do NOT calculate DRI scores - only detect indicators
7. For each finding, you MUST provide specific source evidence

CLIENT CONFIGURATION:
{client_form_mappings}

RESIDENT DATA:
{resident_context}

DRI INDICATOR DEFINITIONS (33 total):
{rag_indicator_context}

TEMPORAL RULES:
- Acute: Time-limited conditions (infections, falls, wounds) - include expected expiry date
- Chronic: Persistent conditions (dementia, heart failure, diabetes) - no expiry
- Recurrent: Episodic conditions (UTIs) - track frequency

For EACH indicator, analyze and return:
- detected: true/false
- confidence: high/medium/low
- temporal_status: {type, onset_date, expected_duration_days, expiry_date, persistence_rule}
- reasoning: Clear explanation with direct quotes from source records
- evidence: Array of source references with {source_table, source_id, source_type, text_excerpt, event_date, entered_by_user}
- false_positive_check: {family_reference: bool, historical_only: bool, negated_statement: bool}
- suggested_action: What to do with this finding
- requires_review: true/false (true if human review recommended)

Return your analysis as JSON with the following structure:
{
  "resident_id": "...",
  "client_system_key": "...",
  "analysis_timestamp": "ISO8601 timestamp",
  "model_used": "...",
  "summary": {
    "indicators_detected": count,
    "indicators_cleared": count,
    "requires_review_count": count,
    "analysis_notes": "brief summary"
  },
  "indicators": [
    {
      "deficit_id": "e.g., RESP_01",
      "deficit_name": "e.g., COPD/Emphysema",
      "detected": true/false,
      "confidence": "high/medium/low",
      "temporal_status": {...},
      "reasoning": "...",
      "evidence": [...],
      "false_positive_check": {...},
      "suggested_action": "...",
      "requires_review": true/false
    }
  ],
  "processing_metadata": {
    "records_analyzed": count,
    "prompt_version": "v1.0"
  }
}

IMPORTANT: Return ONLY the JSON response. Ensure thorough analysis of ALL 33 indicators.',
'Initial comprehensive DRI analysis prompt',
'system',
TRUE
);
```

### 4.2 Prompt Variable Placeholders

| Placeholder | Description | Source |
|-------------|-------------|--------|
| `{client_form_mappings}` | Client-specific form field mappings | DRI_CLIENT_CONFIG table |
| `{resident_context}` | Aggregated resident data from all 6 source tables | Runtime aggregation |
| `{rag_indicator_context}` | DRI indicator definitions from RAG | Cortex Search / DRI_RAG_INDICATORS |

---

## 5. Streamlit Application Specifications

### 5.1 Application Structure

```
dri-intelligence/
├── streamlit_app.py           # Main entry point
├── pages/
│   ├── 1_📊_Dashboard.py
│   ├── 2_🔬_Prompt_Engineering.py
│   ├── 3_📋_Review_Queue.py
│   ├── 4_📈_Analysis_Results.py
│   ├── 5_⚙️_Configuration.py
│   ├── 6_🔄_Claude_vs_Regex_Comparison.py
│   └── 7_🧪_Batch_Testing.py    # NEW: On-demand batch test runs
├── src/
│   ├── connection_helper.py
│   ├── dri_analysis.py
│   ├── prompt_manager.py
│   └── review_workflow.py
└── requirements.txt
```

### 5.2 Page 2: Prompt Engineering / Model Testing (Key Page)

Based on Reference/src/pages/3_🔬_Prompt_and_Model_Testing.py pattern:

```python
# Key Features Required:
# 1. Resident selector - search and select demo residents
# 2. Prompt editor with syntax highlighting
# 3. Model selector (Claude 4.5 as primary for AU)
# 4. On-demand LLM execution
# 5. JSON result viewer with evidence display
# 6. Version comparison (old vs new prompt)
# 7. Save/promote prompt versions

# UI Components:
# - st.text_area for prompt editing (height=350)
# - st.selectbox for model selection
# - st.button("🚀 Run Prompt") for execution
# - st.tabs for result sections
# - st.expander for raw response viewing
# - Custom CSS for clinical result styling (blue boxes)
```

### 5.3 Page 3: Review Queue

```python
# Review Queue Features:
# - Aggregate view: One row per resident with DRI change summary
# - Show: Current DRI Score → Proposed DRI Score
# - Show: Current Severity Band → Proposed Severity Band  
# - Expandable detail: All indicator changes with evidence
# - Single approve/reject per resident
# - Bulk approve for high-confidence items
# - Filter by severity change, date, confidence
```

### 5.4 Page 5: Configuration (Client Management) - KEY UI

This page displays and manages client-specific configurations. **NOTE:** Sample data is mocked for the POC to demonstrate multi-tenant configurability.

```python
# Configuration Page Features:
# 1. Client Selector - dropdown of configured clients
# 2. Client Details Panel - name, description, version, status
# 3. Form Mappings Table - editable grid showing:
#    - Source Table | Form Identifier | Field Name | Mapped Indicator | Active
# 4. Indicator Overrides Table - editable grid showing:
#    - Indicator | Override Type | Override Value | Reason | Active
# 5. JSON Config Editor - advanced view of full CONFIG_JSON
# 6. Import/Export buttons for configuration migration
# 7. Version history with rollback capability

# UI Components:
# - st.dataframe(editable=True) for mapping tables
# - st.json() for config display
# - st.info() boxes explaining each mapping's purpose
# - Color coding: Green = active, Gray = inactive, Yellow = mock data
# - st.warning() banner: "⚠️ Sample Configuration - Modify for your client"
```

### 5.5 Processing Settings Tab (in Configuration Page)

The Processing Settings tab controls production batch processing configuration:

```python
# Processing Settings Features:
# 1. Production Model Selection
#    - Dropdown of available LLM models (Claude 4.5, Claude 3.5, etc.)
#    - "Save Model for Production" button stores selection in DRI_CLIENT_CONFIG
#    - Nightly batch uses saved production model
#
# 2. Production Prompt Version Selection  
#    - Dropdown of saved prompt versions from DRI_PROMPT_VERSIONS
#    - "Save Prompt for Production" button stores selection
#    - Separates testing (any version) from production (locked version)
#
# 3. Batch Schedule Configuration
#    - Dropdown for nightly batch start time (default: midnight)
#    - Cron format stored in CONFIG_JSON:production_settings:batch_schedule
#    - Options: Midnight, 1 AM, 2 AM, 3 AM, 4 AM, 5 AM, 6 AM
#
# 4. Adaptive Token Sizing
#    - Context threshold configuration (default: 6,000 chars)
#    - Standard mode (<threshold): 4,096 max_tokens
#    - Large mode (>threshold): 16,384 max_tokens
```

**Configuration JSON Structure:**
```json
{
  "client_settings": {
    "timezone": "Australia/Sydney",
    "context_threshold": 6000,
    ...
  },
  "production_settings": {
    "model": "claude-3-5-sonnet",
    "prompt_version": "v1.0",
    "batch_schedule": "0 0 * * *"
  }
}
```

### 5.6 Page 7: Batch Testing (NEW)

On-demand batch testing page for validating prompt/model configurations before production:

```python
# Batch Testing Features:
# 1. Shows current production configuration (model, prompt, threshold)
# 2. Date Range Filter
#    - Select records by EVENT_DATE range
#    - Defaults to last 30 days
# 3. Resident Filter
#    - Multi-select specific residents OR "All Residents"
#    - Filter combined with date range
# 4. Preview Panel
#    - Shows count of residents to process
#    - Total notes in selection
#    - Estimated processing time
# 5. Run Batch Button
#    - Executes DRI analysis for each selected resident
#    - Uses PRODUCTION model and prompt (not testing versions)
#    - Progress bar with per-resident status
#    - Stores results in DRI_LLM_ANALYSIS with batch_run_id
# 6. Results Summary
#    - Success/failure counts
#    - Average processing time
#    - Links to Analysis Results and Review Queue pages

# Key Difference from Prompt Engineering Page:
# - Prompt Engineering: Test ANY model/prompt on single residents (experimentation)
# - Batch Testing: Test PRODUCTION config on multiple residents (validation before deploy)
```

#### Configuration Page Mockup

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ⚙️ Client Configuration                                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  ⚠️ SAMPLE DATA: The configuration below is mocked for demonstration.   │
│     Modify these mappings to match your client's specific system.       │
├─────────────────────────────────────────────────────────────────────────┤
│  Client: [DEMO_CLIENT_871 ▼]                                            │
│                                                                         │
│  ┌─ Client Details ──────────────────────────────────────────────────┐  │
│  │  Name: Demo Aged Care Facility                                    │  │
│  │  System Key: DEMO_CLIENT_871                                      │  │
│  │  Version: v1.0                                                    │  │
│  │  Status: ● Active                                                 │  │
│  │  Description: Sample configuration for Resident 871 demo data     │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  [Form Mappings] [Indicator Overrides] [Raw JSON]                       │
│                                                                         │
│  ┌─ Form Mappings (12 active) ───────────────────────────────────────┐  │
│  │  Source Table          | Form/Field         | Maps To   | Active  │  │
│  │  ─────────────────────────────────────────────────────────────────│  │
│  │  ASSESSMENT_FORMS      | CARE_PLAN/BMI      | NUTR_01   | ✓       │  │
│  │  ASSESSMENT_FORMS      | FALLS_RISK/SCORE   | FALL_01   | ✓       │  │
│  │  OBSERVATIONS          | BP_SYSTOLIC        | CARD_03   | ✓       │  │
│  │  MEDICATIONS           | *WARFARIN*         | MED_02    | ✓       │  │
│  │  ...                                                              │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  [+ Add Mapping] [Import JSON] [Export JSON] [Save Changes]             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Client Configuration Reference Data

### 6.1 Sample Client Configuration (MOCK DATA)

**NOTE:** This sample data demonstrates the multi-tenant configuration capability. In production, each end customer would have their own configuration created during onboarding.

```sql
-- ============================================================================
-- SAMPLE CLIENT CONFIGURATION (MOCK DATA FOR POC)
-- ============================================================================

-- Insert sample client
INSERT INTO AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG 
(CLIENT_SYSTEM_KEY, CLIENT_NAME, DESCRIPTION, CONFIG_JSON, VERSION, IS_ACTIVE, CREATED_BY)
VALUES (
    'DEMO_CLIENT_871',
    'Demo Aged Care Facility',
    'Sample configuration for POC demonstration using Resident 871 data. This configuration shows typical form mappings for an aged care facility using standard clinical documentation systems.',
    PARSE_JSON('{
        "client_settings": {
            "timezone": "Australia/Sydney",
            "date_format": "DD/MM/YYYY",
            "confidence_threshold": 0.7,
            "auto_approve_high_confidence": false,
            "review_expiry_days": 7
        },
        "form_identifiers": {
            "care_plan_form": "CARE_PLAN_ASSESSMENT",
            "falls_risk_form": "FALLS_RISK_ASSESSMENT",
            "nutrition_form": "NUTRITION_SCREENING",
            "pain_form": "PAIN_ASSESSMENT",
            "skin_form": "SKIN_INTEGRITY_CHECK",
            "continence_form": "CONTINENCE_ASSESSMENT"
        },
        "field_aliases": {
            "blood_pressure": ["BP", "B/P", "Blood Pressure", "BLOOD_PRESSURE"],
            "weight": ["WT", "Weight", "WEIGHT_KG", "Body Weight"],
            "pain_score": ["Pain Level", "PAIN_SCORE", "Pain Rating"]
        },
        "notes": "This is sample configuration - modify for actual client requirements"
    }'),
    'v1.0',
    TRUE,
    'system'
);

-- Insert sample form mappings (MOCK DATA)
-- These demonstrate how different client systems map their form fields to DRI indicators
INSERT INTO AGEDCARE.AGEDCARE.DRI_CLIENT_FORM_MAPPINGS 
(CLIENT_SYSTEM_KEY, SOURCE_TABLE, FORM_IDENTIFIER, FIELD_NAME, MAPPED_INDICATOR, MAPPING_TYPE, MAPPING_RULES, IS_ACTIVE, NOTES)
VALUES 
-- Assessment Form Mappings
('DEMO_CLIENT_871', 'ACTIVE_RESIDENT_ASSESSMENT_FORMS', 'CARE_PLAN_ASSESSMENT', 'BMI_CALCULATED', 'NUTR_01', 'THRESHOLD', 
 PARSE_JSON('{"operator": "<", "value": 18.5, "description": "BMI below 18.5 indicates malnutrition risk"}'), 
 TRUE, 'SAMPLE: Maps low BMI from care plan to malnutrition indicator'),

('DEMO_CLIENT_871', 'ACTIVE_RESIDENT_ASSESSMENT_FORMS', 'FALLS_RISK_ASSESSMENT', 'TOTAL_SCORE', 'FALL_01', 'THRESHOLD',
 PARSE_JSON('{"operator": ">=", "value": 10, "description": "Falls risk score >= 10 is high risk"}'),
 TRUE, 'SAMPLE: Maps high falls risk score to falls indicator'),

('DEMO_CLIENT_871', 'ACTIVE_RESIDENT_ASSESSMENT_FORMS', 'PAIN_ASSESSMENT', 'PAIN_SCORE', 'PAIN_02', 'THRESHOLD',
 PARSE_JSON('{"operator": ">=", "value": 7, "description": "Pain score >= 7 indicates high pain"}'),
 TRUE, 'SAMPLE: Maps high pain scores to pain indicator'),

('DEMO_CLIENT_871', 'ACTIVE_RESIDENT_ASSESSMENT_FORMS', 'SKIN_INTEGRITY_CHECK', 'PRESSURE_INJURY_PRESENT', 'SKIN_01', 'BOOLEAN',
 PARSE_JSON('{"true_value": "Yes", "description": "Any documented pressure injury"}'),
 TRUE, 'SAMPLE: Maps pressure injury presence to skin indicator'),

('DEMO_CLIENT_871', 'ACTIVE_RESIDENT_ASSESSMENT_FORMS', 'NUTRITION_SCREENING', 'WEIGHT_LOSS_PERCENT', 'NUTR_02', 'THRESHOLD',
 PARSE_JSON('{"operator": ">", "value": 5, "description": "Weight loss > 5% in 3 months"}'),
 TRUE, 'SAMPLE: Maps significant weight loss to nutrition indicator'),

-- Observation Mappings
('DEMO_CLIENT_871', 'ACTIVE_RESIDENT_OBSERVATIONS', NULL, 'BP_SYSTOLIC', 'CARD_03', 'THRESHOLD',
 PARSE_JSON('{"operator": ">", "value": 180, "description": "Systolic BP > 180 indicates uncontrolled hypertension"}'),
 TRUE, 'SAMPLE: Maps high BP readings to hypertension indicator'),

('DEMO_CLIENT_871', 'ACTIVE_RESIDENT_OBSERVATIONS', NULL, 'BLOOD_GLUCOSE', 'DM_02', 'THRESHOLD',
 PARSE_JSON('{"operator": ">", "value": 15, "description": "Blood glucose > 15 mmol/L indicates poor control"}'),
 TRUE, 'SAMPLE: Maps high glucose to diabetes indicator'),

('DEMO_CLIENT_871', 'ACTIVE_RESIDENT_OBSERVATIONS', NULL, 'OXYGEN_SATURATION', 'RESP_01', 'THRESHOLD',
 PARSE_JSON('{"operator": "<", "value": 92, "description": "SpO2 < 92% on room air"}'),
 TRUE, 'SAMPLE: Maps low oxygen to respiratory indicator'),

-- Medication Mappings
('DEMO_CLIENT_871', 'ACTIVE_RESIDENT_MEDICATION', NULL, 'MED_NAME', 'MED_02', 'KEYWORD',
 PARSE_JSON('{"keywords": ["WARFARIN", "RIVAROXABAN", "APIXABAN", "DABIGATRAN"], "description": "Anticoagulant medications"}'),
 TRUE, 'SAMPLE: Maps anticoagulant medications to high-risk med indicator'),

('DEMO_CLIENT_871', 'ACTIVE_RESIDENT_MEDICATION', NULL, 'MED_NAME', 'MED_02', 'KEYWORD',
 PARSE_JSON('{"keywords": ["INSULIN", "NOVORAPID", "LANTUS", "HUMALOG"], "description": "Insulin medications"}'),
 TRUE, 'SAMPLE: Maps insulin to high-risk med indicator'),

('DEMO_CLIENT_871', 'ACTIVE_RESIDENT_MEDICATION', NULL, 'MED_NAME', 'MED_01', 'COUNT',
 PARSE_JSON('{"operator": ">=", "value": 9, "count_field": "MED_ID", "description": "9+ regular medications = polypharmacy"}'),
 TRUE, 'SAMPLE: Counts medications for polypharmacy indicator'),

-- Notes/Progress Note Mappings (for LLM analysis hints)
('DEMO_CLIENT_871', 'ACTIVE_RESIDENT_NOTES', NULL, 'PROGRESS_NOTE', 'ALL', 'LLM_CONTEXT',
 PARSE_JSON('{"priority": "high", "include_in_context": true, "description": "All progress notes included in LLM context"}'),
 TRUE, 'SAMPLE: Progress notes are primary source for LLM analysis');

-- Insert sample indicator overrides (MOCK DATA)
-- These demonstrate how clients can customize indicator behavior
INSERT INTO AGEDCARE.AGEDCARE.DRI_CLIENT_INDICATOR_OVERRIDES
(CLIENT_SYSTEM_KEY, INDICATOR_ID, OVERRIDE_TYPE, OVERRIDE_VALUE, REASON, IS_ACTIVE)
VALUES
('DEMO_CLIENT_871', 'FALL_01', 'EXPIRY_DAYS', PARSE_JSON('{"value": 60}'), 
 'SAMPLE: Client policy requires 60-day tracking instead of default 90 days', TRUE),

('DEMO_CLIENT_871', 'PAIN_02', 'THRESHOLD', PARSE_JSON('{"value": 6}'), 
 'SAMPLE: Client uses pain score >= 6 instead of default >= 7', TRUE),

('DEMO_CLIENT_871', 'MED_01', 'COUNT_THRESHOLD', PARSE_JSON('{"value": 10}'), 
 'SAMPLE: Client defines polypharmacy as 10+ meds instead of 9+', TRUE),

('DEMO_CLIENT_871', 'SKIN_03', 'DISABLED', PARSE_JSON('{"value": true}'), 
 'SAMPLE: Chronic wound indicator disabled - client uses separate wound management system', FALSE);
```

### 6.2 Viewing Configuration in Streamlit

The Configuration page will display this data with clear visual indicators:

| Visual Element | Meaning |
|----------------|---------|
| 🟡 Yellow highlight | Mock/Sample data - needs customization |
| 🟢 Green badge | Active mapping |
| ⚪ Gray badge | Inactive mapping |
| ⚠️ Warning banner | Reminds user this is sample configuration |
| ℹ️ Info tooltip | Explains each mapping's purpose |

---

## 7. Processing Flow

### 6.1 Batch Processing Stored Procedure

```sql
CREATE OR REPLACE PROCEDURE AGEDCARE.AGEDCARE.DRI_BATCH_ANALYSIS(
    RUN_DATE DATE,
    RUN_MODE VARCHAR,        -- 'onboarding' or 'daily_delta'
    CLIENT_SYSTEM_KEY VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE
    batch_id VARCHAR;
    resident_cursor CURSOR FOR 
        SELECT DISTINCT RESIDENT_ID 
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES
        WHERE EVENT_DATE >= :RUN_DATE - 1;
BEGIN
    batch_id := UUID_STRING();
    
    -- Process each resident
    FOR resident_rec IN resident_cursor DO
        -- Call LLM analysis (implemented in Python UDF)
        CALL AGEDCARE.AGEDCARE.ANALYZE_RESIDENT_DRI(
            resident_rec.RESIDENT_ID,
            :CLIENT_SYSTEM_KEY,
            :batch_id
        );
    END FOR;
    
    RETURN 'Batch ' || :batch_id || ' completed';
END;
$$;
```

### 6.2 DRI Score Calculation (Post-Approval)

```sql
CREATE OR REPLACE PROCEDURE AGEDCARE.AGEDCARE.CALCULATE_DRI_SCORES()
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
    -- Calculate DRI scores from approved deficit status
    MERGE INTO AGEDCARE.AGEDCARE.DRI_DEFICIT_SUMMARY AS target
    USING (
        SELECT 
            ds.RESIDENT_ID,
            CURRENT_TIMESTAMP() AS LOAD_TIMESTAMP,
            COUNT(*) / 33.0 AS DRI_SCORE,
            CASE 
                WHEN COUNT(*) / 33.0 <= 0.2 THEN 'Low'
                WHEN COUNT(*) / 33.0 <= 0.4 THEN 'Medium'
                WHEN COUNT(*) / 33.0 <= 0.6 THEN 'High'
                ELSE 'Very High'
            END AS SEVERITY_BAND
        FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_STATUS ds
        WHERE ds.DEFICIT_STATUS = 'ACTIVE'
        GROUP BY ds.RESIDENT_ID
    ) AS source
    ON target.RESIDENT_ID = source.RESIDENT_ID
    WHEN MATCHED THEN UPDATE SET
        target.DRI_SCORE = source.DRI_SCORE,
        target.SEVERITY_BAND = source.SEVERITY_BAND,
        target.LOAD_TIMESTAMP = source.LOAD_TIMESTAMP
    WHEN NOT MATCHED THEN INSERT (RESIDENT_ID, LOAD_TIMESTAMP, DRI_SCORE, SEVERITY_BAND)
        VALUES (source.RESIDENT_ID, source.LOAD_TIMESTAMP, source.DRI_SCORE, source.SEVERITY_BAND);
    
    RETURN 'DRI scores updated';
END;
$$;
```

---

## 7. Demo Data Loading

### 7.1 Load Script from Excel

```python
# Python script to load demo data from Excel to Snowflake
# Run locally or in Snowflake notebook

import pandas as pd
from snowflake.connector import connect

EXCEL_PATH = 'Confidential/DRI/data/De-identified - 871 - Integration.xlsx'

SHEET_TABLE_MAP = {
    'ACTIVE_RESIDENT_MEDICAL_PROFILE': 'AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICAL_PROFILE',
    'ACTIVE_RESIDENT_ASSESSMENT_FORM': 'AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_ASSESSMENT_FORMS',
    'ACTIVE_RESIDENT_MEDICATION': 'AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION',
    'ACTIVE_RESIDENT_NOTES': 'AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES',
    'ACTIVE_RESIDENT_OBSERVATIONS': 'AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS',
    'ACTIVE_RESIDENT_OBSERVATION_GRO': 'AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATION_GROUP'
}

def load_demo_data(conn):
    for sheet_name, table_name in SHEET_TABLE_MAP.items():
        df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name)
        # Write to Snowflake using write_pandas or similar
        # Implementation depends on connection type
```

---

## 8. SPCS Deployment

### 8.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 8.2 requirements.txt

```
streamlit>=1.28.0
snowflake-connector-python[pandas]>=3.0.0
snowflake-snowpark-python>=1.0.0
pandas>=2.0.0
```

### 8.3 SPCS Service Definition

```sql
-- Create compute pool
CREATE COMPUTE POOL IF NOT EXISTS DRI_COMPUTE_POOL
    MIN_NODES = 1
    MAX_NODES = 1
    INSTANCE_FAMILY = CPU_X64_XS;

-- Create service
CREATE SERVICE AGEDCARE.AGEDCARE.DRI_INTELLIGENCE_APP
    IN COMPUTE POOL DRI_COMPUTE_POOL
    FROM SPECIFICATION $$
    spec:
      containers:
      - name: dri-app
        image: /agedcare/agedcare/images/dri-intelligence:latest
        env:
          SNOWFLAKE_DATABASE: AGEDCARE
          SNOWFLAKE_SCHEMA: AGEDCARE
      endpoints:
      - name: streamlit
        port: 8501
        public: true
    $$;
```

---

## 10. Comprehensive Testing Strategy

### 10.1 Automated Test Suite (Run by Developer)

All tests below will be executed during implementation to ensure quality before handoff.

#### 10.1.1 Database Setup Tests

```sql
-- TEST 1: Verify all tables created successfully
SELECT TABLE_NAME, ROW_COUNT 
FROM AGEDCARE.INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'AGEDCARE'
ORDER BY TABLE_NAME;
-- Expected: 15+ tables listed

-- TEST 2: Verify demo data loaded
SELECT 'ACTIVE_RESIDENT_NOTES' AS TABLE_NAME, COUNT(*) AS ROWS FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES
UNION ALL SELECT 'ACTIVE_RESIDENT_OBSERVATIONS', COUNT(*) FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS
UNION ALL SELECT 'ACTIVE_RESIDENT_MEDICATION', COUNT(*) FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION
UNION ALL SELECT 'ACTIVE_RESIDENT_ASSESSMENT_FORMS', COUNT(*) FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_ASSESSMENT_FORMS;
-- Expected: Notes=256, Observations=1816, Medications=30, Assessments=404

-- TEST 3: Verify indicator reference data
SELECT COUNT(*) AS INDICATOR_COUNT FROM AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS;
-- Expected: 33

-- TEST 4: Verify client config loaded
SELECT CLIENT_SYSTEM_KEY, CLIENT_NAME, IS_ACTIVE 
FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG;
-- Expected: DEMO_CLIENT_871, Active

-- TEST 5: Verify form mappings loaded
SELECT COUNT(*) AS MAPPING_COUNT 
FROM AGEDCARE.AGEDCARE.DRI_CLIENT_FORM_MAPPINGS 
WHERE CLIENT_SYSTEM_KEY = 'DEMO_CLIENT_871' AND IS_ACTIVE = TRUE;
-- Expected: 12
```

#### 10.1.2 Cortex Complete LLM Tests

```sql
-- TEST 6: Basic Cortex Complete connectivity
SELECT SNOWFLAKE.CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    'Return only the word "SUCCESS" if you can read this message.'
) AS LLM_RESPONSE;
-- Expected: Contains "SUCCESS"

-- TEST 7: JSON output capability
SELECT SNOWFLAKE.CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    'Return valid JSON with format: {"test": "passed", "value": 123}. Return ONLY the JSON.'
) AS LLM_RESPONSE;
-- Expected: Valid parseable JSON

-- TEST 8: Clinical analysis basic test
SELECT SNOWFLAKE.CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    'Analyze this clinical note for DRI indicators: "Patient has documented COPD requiring home oxygen therapy." Return JSON with format: {"indicator": "RESP_01", "detected": true, "confidence": "high"}'
) AS LLM_RESPONSE;
-- Expected: RESP_01 detected with high confidence
```

#### 10.1.3 False Positive Detection Tests (Critical for <1% target)

```sql
-- TEST 9: Family reference detection
SELECT SNOWFLAKE.CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    'Analyze: "Resident''s son has severe asthma and visits weekly." 
     Does the RESIDENT have asthma? Return JSON: {"resident_has_asthma": bool, "is_family_reference": bool, "reasoning": "..."}'
) AS RESULT;
-- Expected: resident_has_asthma=false, is_family_reference=true

-- TEST 10: Negated statement detection
SELECT SNOWFLAKE.CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    'Analyze: "Assessment shows no signs of diabetes. Blood glucose within normal limits."
     Return JSON: {"diabetes_detected": bool, "is_negated_statement": bool, "reasoning": "..."}'
) AS RESULT;
-- Expected: diabetes_detected=false, is_negated_statement=true

-- TEST 11: Historical condition detection
SELECT SNOWFLAKE.CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    'Analyze: "Patient had pneumonia in 2019 which fully resolved with antibiotics."
     Return JSON: {"current_respiratory_infection": bool, "is_historical_only": bool, "reasoning": "..."}'
) AS RESULT;
-- Expected: current_respiratory_infection=false, is_historical_only=true

-- TEST 12: Combined false positive test
SELECT SNOWFLAKE.CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    'Analyze these statements for the RESIDENT (not family):
     1. "Mother had heart failure"
     2. "No diabetes"
     3. "Resolved UTI December 2024"
     4. "Current COPD requiring oxygen"
     Return JSON array with detected conditions for the RESIDENT only.'
) AS RESULT;
-- Expected: Only COPD detected as current resident condition
```

#### 10.1.4 Full Resident Analysis Test

```sql
-- TEST 13: End-to-end analysis for Resident 871
-- First, aggregate resident data
WITH resident_context AS (
    SELECT 
        871 AS RESIDENT_ID,
        (SELECT LISTAGG(PROGRESS_NOTE, '\n---\n') WITHIN GROUP (ORDER BY EVENT_DATE DESC) 
         FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES 
         WHERE RESIDENT_ID = 871 
         LIMIT 20) AS NOTES,
        (SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION WHERE RESIDENT_ID = 871) AS MED_COUNT
)
SELECT SNOWFLAKE.CORTEX.COMPLETE(
    'claude-3-5-sonnet',
    'Analyze this aged care resident data for DRI indicators. Return JSON with indicators array.
     NOTES: ' || NOTES || '
     MEDICATION_COUNT: ' || MED_COUNT::VARCHAR
) AS ANALYSIS_RESULT
FROM resident_context;
-- Expected: Valid JSON with indicators array, reasonable detections based on actual data
```

#### 10.1.5 Cortex Search Service Tests

```sql
-- TEST 14: Cortex Search service creation
SHOW CORTEX SEARCH SERVICES IN SCHEMA AGEDCARE.AGEDCARE;
-- Expected: DRI_INDICATOR_SEARCH listed

-- TEST 15: Cortex Search query test
SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
    'AGEDCARE.AGEDCARE.DRI_INDICATOR_SEARCH',
    '{
        "query": "heart failure cardiac",
        "columns": ["INDICATOR_ID", "INDICATOR_NAME", "DEFINITION"],
        "limit": 3
    }'
)::VARIANT AS SEARCH_RESULTS;
-- Expected: Returns CARD_01 (Heart Failure) as top result
```

#### 10.1.6 Stored Procedure Tests

```sql
-- TEST 16: DRI score calculation procedure
-- First insert test deficit status
INSERT INTO AGEDCARE.AGEDCARE.DRI_DEFICIT_STATUS 
(RESIDENT_ID, DEFICIT_ID, DEFICIT_STATUS, DEFICIT_START_DATE)
VALUES 
(871, 'RESP_01', 'ACTIVE', CURRENT_DATE()),
(871, 'CARD_01', 'ACTIVE', CURRENT_DATE()),
(871, 'MED_01', 'ACTIVE', CURRENT_DATE());

CALL AGEDCARE.AGEDCARE.CALCULATE_DRI_SCORES();

SELECT RESIDENT_ID, DRI_SCORE, SEVERITY_BAND 
FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_SUMMARY 
WHERE RESIDENT_ID = 871;
-- Expected: DRI_SCORE = 3/33 = 0.0909, SEVERITY_BAND = 'Low'
```

### 10.2 Streamlit Application Tests

#### 10.2.1 Connection Test
```python
# Run from Streamlit app or separate test script
def test_snowflake_connection():
    conn = get_snowflake_connection()
    result = conn.cursor().execute("SELECT CURRENT_USER(), CURRENT_ROLE()").fetchone()
    assert result is not None, "Connection failed"
    print(f"✅ Connected as {result[0]} with role {result[1]}")
```

#### 10.2.2 Page Load Tests
| Page | Test | Success Criteria |
|------|------|------------------|
| Dashboard | Load resident count | Shows "1 resident" (871) |
| Prompt Engineering | Load prompt versions | Shows v1.0 as active |
| Review Queue | Load pending items | Table renders (may be empty) |
| Analysis Results | Load analysis history | Table renders |
| Configuration | Load client config | Shows DEMO_CLIENT_871 with mappings |

#### 10.2.3 Functional Tests (Performed via UI)
| Test | Steps | Expected Result |
|------|-------|-----------------|
| Run LLM Analysis | Select Resident 871, click "Run Analysis" | JSON response with indicators |
| Save Prompt | Edit prompt, click "Save as New Version" | New version appears in dropdown |
| View Configuration | Go to Config page, expand mappings | 12 form mappings visible |
| Export Config | Click "Export JSON" | Valid JSON file downloads |

### 10.3 Test Execution Checklist

The developer will execute and document results for each test:

```
[ ] TEST 1: Tables created - ___ tables found
[ ] TEST 2: Demo data loaded - Notes: ___, Obs: ___, Meds: ___, Assess: ___
[ ] TEST 3: Indicator reference - ___ indicators
[ ] TEST 4: Client config - Client: _______________
[ ] TEST 5: Form mappings - ___ active mappings
[ ] TEST 6: Cortex Complete connectivity - PASS/FAIL
[ ] TEST 7: JSON output - PASS/FAIL
[ ] TEST 8: Clinical analysis - PASS/FAIL
[ ] TEST 9: Family reference detection - PASS/FAIL
[ ] TEST 10: Negated statement detection - PASS/FAIL
[ ] TEST 11: Historical condition detection - PASS/FAIL
[ ] TEST 12: Combined false positive - PASS/FAIL
[ ] TEST 13: Full resident analysis - PASS/FAIL
[ ] TEST 14: Cortex Search service exists - PASS/FAIL
[ ] TEST 15: Cortex Search query - PASS/FAIL
[ ] TEST 16: DRI score calculation - Score: ___, Band: ___
[ ] Streamlit: Dashboard loads - PASS/FAIL
[ ] Streamlit: Prompt Engineering runs LLM - PASS/FAIL
[ ] Streamlit: Configuration shows mappings - PASS/FAIL
```

### 10.4 False Positive Rate Validation

To validate the <1% false positive target:

```sql
-- After running full analysis on Resident 871, manually review each detected indicator
-- and categorize as True Positive or False Positive

CREATE OR REPLACE TABLE AGEDCARE.AGEDCARE.TEST_FP_VALIDATION (
    TEST_RUN_ID VARCHAR(36) DEFAULT UUID_STRING(),
    RESIDENT_ID NUMBER,
    INDICATOR_ID VARCHAR(64),
    LLM_DETECTED BOOLEAN,
    MANUAL_REVIEW VARCHAR(32), -- 'TRUE_POSITIVE', 'FALSE_POSITIVE', 'UNCERTAIN'
    FP_REASON VARCHAR(256),    -- 'FAMILY_REF', 'NEGATED', 'HISTORICAL', 'OTHER'
    REVIEWER_NOTES VARCHAR(16777216),
    REVIEWED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- After manual review, calculate FP rate:
SELECT 
    COUNT(CASE WHEN MANUAL_REVIEW = 'FALSE_POSITIVE' THEN 1 END) AS FALSE_POSITIVES,
    COUNT(CASE WHEN LLM_DETECTED = TRUE THEN 1 END) AS TOTAL_DETECTIONS,
    ROUND(100.0 * COUNT(CASE WHEN MANUAL_REVIEW = 'FALSE_POSITIVE' THEN 1 END) / 
          NULLIF(COUNT(CASE WHEN LLM_DETECTED = TRUE THEN 1 END), 0), 2) AS FP_RATE_PERCENT
FROM AGEDCARE.AGEDCARE.TEST_FP_VALIDATION;
-- Target: FP_RATE_PERCENT < 1.0
```

---

## 11. Security & Access Control

### 11.1 Role Hierarchy

```sql
-- Create roles
CREATE ROLE IF NOT EXISTS DRI_ADMIN;       -- Full access
CREATE ROLE IF NOT EXISTS DRI_REVIEWER;    -- Review queue access
CREATE ROLE IF NOT EXISTS DRI_ANALYST;     -- Prompt engineering
CREATE ROLE IF NOT EXISTS DRI_VIEWER;      -- Dashboard only

-- Grant hierarchy
GRANT ROLE DRI_VIEWER TO ROLE DRI_ANALYST;
GRANT ROLE DRI_ANALYST TO ROLE DRI_REVIEWER;
GRANT ROLE DRI_REVIEWER TO ROLE DRI_ADMIN;

-- Table grants
GRANT SELECT ON ALL TABLES IN SCHEMA AGEDCARE.AGEDCARE TO ROLE DRI_VIEWER;
GRANT SELECT, INSERT ON AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE TO ROLE DRI_REVIEWER;
GRANT SELECT, INSERT, UPDATE ON AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS TO ROLE DRI_ANALYST;
GRANT ALL ON SCHEMA AGEDCARE.AGEDCARE TO ROLE DRI_ADMIN;
```

---

## 12. Compute Resource Clarification

### 12.1 Resource Usage Summary

| Component | Compute Resource | Notes |
|-----------|------------------|-------|
| Streamlit Application | SPCS (DRI_COMPUTE_POOL) | Runs in container, NOT on warehouse |
| Cortex Complete (LLM) | Serverless | Billed per token, no warehouse needed |
| Cortex Search | Serverless | Billed separately, uses warehouse for index build only |
| SQL Queries (DDL, DML) | MYWH | Standard warehouse for data operations |
| Data Loading | MYWH | Used for loading Excel demo data |
| Stored Procedures | MYWH | DRI score calculations, batch operations |

### 12.2 Warehouse Usage

The warehouse `MYWH` is used ONLY for:
- Creating/altering database objects (DDL)
- Loading and querying data (DML/SELECT)
- Running stored procedures
- Building Cortex Search index (one-time/periodic)

**NOT used for:**
- Streamlit hosting (uses SPCS)
- LLM inference (serverless)
- Cortex Search queries at runtime (serverless)

---

## 13. Implementation Timeline

| Phase | Tasks | Duration |
|-------|-------|----------|
| 1. Setup | Create database, tables, load demo data | 1 day |
| 2. Core Engine | LLM analysis, RAG setup, prompt engineering | 3 days |
| 3. Streamlit UI | All 5 pages, connection helper | 3 days |
| 4. Review Workflow | Queue, approval, DRI calculation | 2 days |
| 5. Testing | Unit tests, integration tests | 2 days |
| 6. SPCS Deployment | Container, service, access control | 1 day |
| **Total** | | **~12 days** |

---

## 14. Appendices

### A. Excel Sheet to Table Column Mapping

| Excel Sheet | Table | Key Column Differences |
|-------------|-------|------------------------|
| ACTIVE_RESIDENT_MEDICAL_PROFILE | Same | allergy_exclusion → ALLERGY_EXCLUSION |
| ACTIVE_RESIDENT_ASSESSMENT_FORM | ACTIVE_RESIDENT_ASSESSMENT_FORMS | Added ITEM_CODE, ITEM_NAME |
| ACTIVE_RESIDENT_MEDICATION | Same | updated_date → EVENT_DATE |
| ACTIVE_RESIDENT_NOTES | Same | Exact match |
| ACTIVE_RESIDENT_OBSERVATIONS | Same | Exact match |
| ACTIVE_RESIDENT_OBSERVATION_GRO | ACTIVE_RESIDENT_OBSERVATION_GROUP | Truncated name in Excel |

### B. Model Availability (Australia Region)

| Model | Availability | Use Case |
|-------|--------------|----------|
| Claude 4.5 Sonnet | Primary | Main analysis |
| Claude 3.5 Sonnet | Fallback | If 4.5 unavailable |
| Mistral Large 2 | Testing | Prompt testing |
| Llama 3.1 70B | Testing | Cost comparison |

---

*Document Version: 1.1*  
*Created: 2026-01-28*  
*Updated: 2026-01-28*  
*Status: Draft - Ready for Review*

### Change Log
| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-28 | Initial draft |
| 1.1 | 2026-01-28 | Added: Comprehensive automated testing (Section 10), Client configuration UI details (Section 5.4), Sample client mappings (Section 6), Compute resource clarification (Section 12), Changed warehouse to MYWH |
