# Healthcare Transcription AI Demo - Multi-Style Design Document

## Project Overview
This document defines the design for a Snowflake-based healthcare demonstration showcasing AI-powered analysis of medical notes using the PMC patients dataset. The solution features **three distinct UI styles** to demonstrate different approaches to healthcare application design, all built on a shared hybrid architecture combining pre-processed insights with real-time AI demonstrations.

## Multi-Style UI Approach
This project implements **three complete style variations** of the same healthcare application:

1. **Corporate Standard Style**: Professional, stable interface using native Streamlit components
2. **Modern Minimalist Style**: Contemporary, elegant design with curated third-party components  
3. **Data-Dense Powerhouse Style**: High-density dashboard interface for expert users

**Purpose**: Allow stakeholders to experience different UI approaches and select the most appropriate style for their organization's culture and user requirements.

## Architecture: Hybrid Approach

### Core Design Principles
1. **Pre-processed Analytics**: Most insights are pre-computed and stored in enriched tables for optimal demo performance
2. **Real-time Demonstrations**: Selected use cases allow live AI processing to showcase Snowflake Cortex capabilities
3. **Physician-First Design**: UI/UX optimized for clinical workflows with secondary views for administrators and researchers
4. **Production-Ready Patterns**: Architecture mirrors real-world healthcare implementations

### System Architecture

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│   PMC_PATIENTS      │────▶│   Data Subset        │────▶│  PATIENT_SUBSET     │
│   (167K records)    │     │   (1K records)       │     │  (Clean age data)   │
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
                                                                    │
                                      ┌─────────────────────────────┘
                                      │
                            ┌─────────────────────┐      ┌─────────────────────┐
                            │  Batch AI Pipeline  │◀─────│  PATIENT_SUBSET     │
                            │  (Cortex AI)        │      │  (1K records)       │
                            │  - Configurable     │      └─────────────────────┘
                            │    prompts          │               │
                            └─────────────────────┘               ▼
                                      │                  ┌─────────────────────┐
                                      │                  │  Enriched Tables    │
                                      ▼                  │  (Pre-computed)     │
                            ┌─────────────────────┐      └─────────────────────┘
                            │  Real-time AI       │               │
                            │  Processing         │               ▼
                            │  (On-demand)        │      ┌─────────────────────┐
                            └─────────────────────┘      │  Shared Backend     │
                                      ▲                  │  (connection_helper │
                                      └──────────────────│   data_processors)  │
                                                         └─────────────────────┘
                                                                  │
                            ┌─────────────────────┐               ▼
                            │  Cortex Search      │      ┌─────────────────────┐
                            │  Service            │◀─────│  THREE STYLE APPS   │
                            │  (1K Indexed)       │      │                     │
                            │  Semantic Search    │      │  Corporate Standard │
                            └─────────────────────┘      │  Modern Minimalist  │
                                                         │  Data-Dense Power   │
                                                         │                     │
                                                         │  :8501  :8502  :8503│
                                                         └─────────────────────┘
```

## UI Style Implementation Details

### Style 1: Corporate Standard
- **Target Audience**: Conservative healthcare organizations, regulatory environments
- **Visual Approach**: Clean, professional, maximum stability  
- **Components**: Native Streamlit only (`st.sidebar`, `st.tabs`, `st.container(border=True)`)
- **Color Scheme**: Corporate blue (#0062df), white background, minimal styling
- **Layout**: Structured grid with visible borders, traditional navigation

### Style 2: Modern Minimalist  
- **Target Audience**: Tech-forward healthcare organizations, executive presentations
- **Visual Approach**: Contemporary, elegant, generous whitespace
- **Components**: `streamlit-option-menu`, `streamlit-shadcn-ui` cards and buttons
- **Color Scheme**: Muted grays (#5a5a5a), off-white background, subtle shadows
- **Layout**: Horizontal navigation, spacious cards, premium feel

### Style 3: Data-Dense Powerhouse
- **Target Audience**: Clinical analysts, operations teams, monitoring dashboards
- **Visual Approach**: Maximum information density, expert-focused
- **Components**: `streamlit-elements` draggable grid, compact navigation
- **Color Scheme**: Dark theme, high contrast, operational dashboard feel
- **Layout**: Customizable dashboard grid, resizable panels, efficiency-focused

### Shared Architecture Components
All three styles share:
- **Backend Logic**: Same `connection_helper.py`, data processing functions, SQL scripts
- **Business Logic**: Identical medical analysis, AI processing, and data workflows  
- **Content Structure**: Same page functionality (Data Foundation, Clinical Decision Support, etc.)
- **Database Access**: Single database/schema pattern maintained across all styles

### Demo Deployment Strategy
- **Development**: All three apps run simultaneously on ports 8501, 8502, 8503
- **Client Demos**: Share specific URLs based on client preferences and culture
- **A/B Testing**: Measure engagement and preference across different user types
- **Production Selection**: Choose one style for final deployment, archive others

## Database Schema Design

create a database named HEALTHCARE_DEMO

create a schema named MEDICAL_NOTES

use the snowflake warehouse MYWH

### Patient Subset Table

```sql
-- Subset of patients for development and demonstration
CREATE OR REPLACE TABLE HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_SUBSET (
    PATIENT_ID NUMBER PRIMARY KEY,
    PATIENT_UID VARCHAR,
    PATIENT_TITLE TEXT,
    PATIENT_NOTES TEXT,
    AGE_YEARS NUMBER(5,2), -- Cleaned age in decimal years (e.g., 12.5)
    AGE_ORIGINAL VARCHAR, -- Original age string for reference
    GENDER VARCHAR,
    SIMILAR_PATIENTS VARIANT,
    RELEVANT_ARTICLES VARIANT,
    CREATED_DATE TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

### Core Tables

```sql
-- Main analysis table for pre-computed insights
CREATE OR REPLACE TABLE HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS (
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
);

-- Real-time processing history
CREATE OR REPLACE TABLE HEALTHCARE_DEMO.MEDICAL_NOTES.REALTIME_ANALYSIS_LOG (
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
);

-- Drug safety analysis
CREATE OR REPLACE TABLE HEALTHCARE_DEMO.MEDICAL_NOTES.MEDICATION_ANALYSIS (
    PATIENT_ID NUMBER PRIMARY KEY,
    EXTRACTED_MEDICATIONS VARIANT, -- Array of {name, dosage, frequency, route}
    DRUG_INTERACTIONS VARIANT, -- Array of {drug1, drug2, severity, description}
    CONTRAINDICATIONS VARIANT, -- Array of {medication, condition, risk_level}
    POLYPHARMACY_RISK_SCORE NUMBER, -- Risk score based on number and types of meds
    ANALYSIS_DATE TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Cost analysis
CREATE OR REPLACE TABLE HEALTHCARE_DEMO.MEDICAL_NOTES.COST_ANALYSIS (
    PATIENT_ID NUMBER PRIMARY KEY,
    EXTRACTED_PROCEDURES VARIANT, -- Array of {procedure, CPT_code, estimated_cost}
    EXTRACTED_CONDITIONS VARIANT, -- Array of {condition, ICD10_code, cost_impact}
    HIGH_COST_INDICATORS VARIANT, -- ICU, surgery, complications, etc.
    ESTIMATED_ENCOUNTER_COST NUMBER(10,2),
    COST_CATEGORY VARCHAR, -- 'low', 'medium', 'high', 'very_high'
    COST_DRIVERS TEXT, -- Narrative explanation
    ANALYSIS_DATE TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Procedure cost reference table
CREATE OR REPLACE TABLE HEALTHCARE_DEMO.MEDICAL_NOTES.PROCEDURE_COSTS (
    PROCEDURE_NAME VARCHAR,
    CPT_CODE VARCHAR,
    ESTIMATED_COST NUMBER(10,2),
    COST_RANGE_LOW NUMBER(10,2),
    COST_RANGE_HIGH NUMBER(10,2),
    CATEGORY VARCHAR
);

-- Cohort analysis for population health
CREATE OR REPLACE TABLE HEALTHCARE_DEMO.MEDICAL_NOTES.COHORT_INSIGHTS (
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
);

-- Physician workflow optimization
CREATE OR REPLACE TABLE HEALTHCARE_DEMO.MEDICAL_NOTES.PHYSICIAN_INSIGHTS (
    INSIGHT_ID VARCHAR DEFAULT UUID_STRING(),
    GENERATED_DATE DATE DEFAULT CURRENT_DATE(),
    SPECIALTY VARCHAR,
    INSIGHT_TYPE VARCHAR, -- 'clinical_alert', 'best_practice', 'new_evidence'
    INSIGHT_TITLE TEXT,
    INSIGHT_CONTENT TEXT,
    EVIDENCE_LINKS VARIANT,
    APPLICABLE_PATIENTS VARIANT,
    PRIORITY_SCORE NUMBER
);
```

## Cortex Search Implementation

### Search Service Architecture
The application implements **Snowflake Cortex Search** for intelligent patient discovery with the following features:

- **Service Name**: `patient_search_service`
- **Index Status**: ACTIVE (1,000 patient records from subset)
- **Embedding Model**: `snowflake-arctic-embed-l-v2.0`
- **Refresh Frequency**: 1 hour target lag
- **Warehouse**: `CORTEX_SEARCH_WH` (X-SMALL)

### Search Capabilities
- **Semantic Understanding**: Understands medical terminology and concepts
- **Misspelling Tolerance**: Handles common medical misspellings (e.g., "brest" → "breast")
- **Multi-Column Search**: Searches across patient notes, titles, and metadata
- **Sub-Second Performance**: Vector-based search for near-instantaneous results
- **Relevance Scoring**: Returns similarity scores for result ranking

### Implementation Details
```sql
-- Drop existing service on full dataset
DROP CORTEX SEARCH SERVICE IF EXISTS patient_search_service;

-- Create new service on subset
CREATE OR REPLACE CORTEX SEARCH SERVICE patient_search_service
    ON PATIENT_SUBSET
    ATTRIBUTES PATIENT_ID, PATIENT_UID, PATIENT_TITLE, AGE_YEARS, GENDER
    WAREHOUSE = CORTEX_SEARCH_WH
    TARGET_LAG = '1 hour'
    EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
    AS (
        SELECT PATIENT_NOTES, PATIENT_ID, PATIENT_UID, PATIENT_TITLE, AGE_YEARS, GENDER
        FROM HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_SUBSET
        WHERE PATIENT_NOTES IS NOT NULL AND LENGTH(PATIENT_NOTES) > 50
    );
```

### Integration Points
- **Clinical Decision Support**: Primary search interface for patient discovery
- **API Access**: Python-based queries using Snowflake's core libraries
- **Enhanced Fallback**: Intelligent text search with medical spell correction when needed

## Batch Processing Pipeline

### Architecture
- **Data Source**: PATIENT_SUBSET table (1,000 records)
- **Processing**: Parallel batch processing with configurable batch sizes
- **Prompts**: Configurable prompt templates stored in configuration
- **Re-processing**: Ability to update prompts and re-run analysis

### Configurable Prompts
All AI prompts are stored in a configuration file allowing:
- Easy modification without code changes
- A/B testing of different prompt strategies
- Demo of prompt engineering impact
- Version control of prompt iterations

### Processing Features (OPTIMIZED IMPLEMENTATION)
1. **Consolidated Prompts**: Single API call per patient (vs 8 calls) - 5-8x performance improvement
2. **Progress Tracking**: Real-time progress updates during batch processing with estimated completion times
3. **Error Handling**: Graceful handling of AI failures with retry logic
4. **Incremental Processing**: Process only new/updated records to avoid redundant work
5. **Parallel Execution**: Process multiple patients concurrently with configurable batch sizes
6. **Cost Tracking**: Monitor Cortex AI token usage and processing costs
7. **Live Management**: Direct batch processing control from Demo Guide page

## Use Case Implementation Priority

### Phase 1: Core Clinical Use Cases (Physician-focused)

#### 1. On-Demand Patient Summary (Use Case 3)
- **Pre-computed**: SBAR summaries for all patients
- **Real-time**: Allow physicians to modify notes and regenerate summaries
- **Value**: Reduces handoff errors, saves 10-15 minutes per patient

#### 2. Differential Diagnosis Support (Use Case 1)
- **Pre-computed**: Top 5 differential diagnoses with evidence
- **Real-time**: Interactive diagnosis exploration with custom symptoms
- **Value**: Improves diagnostic accuracy, reduces time to diagnosis

#### 3. Evidence-Based Treatment Analysis (Use Case 2)
- **Pre-computed**: Treatment comparisons from similar patients
- **Real-time**: Query specific treatment outcomes
- **Value**: Promotes evidence-based medicine, improves outcomes

#### 4. Rare Disease Pattern Recognition (Use Case 4)
- **Pre-computed**: Anomaly scores and rare disease flags
- **Real-time**: Deep dive into specific symptom clusters
- **Value**: Reduces diagnostic odysseys for rare conditions

### Phase 2: Administrative Use Cases

#### 5. High-Cost Patient Analysis (Use Case 5)
- **Pre-computed**: Cost drivers and utilization patterns
- **Cost Estimation**: Extract procedures from notes and estimate costs
- **Financial Impact**: Link clinical notes to financial outcomes
- **Dashboard**: Aggregate views by department/condition
- **Value**: Identifies intervention opportunities, reduces costs

#### 6. Drug Interaction & Safety Analysis (Use Case 6)
- **Medication Extraction**: Extract all medications and dosages from notes
- **Interaction Checking**: Identify potential drug-drug interactions
- **Contraindication Alerts**: Flag medications contraindicated with patient conditions
- **Pre-computed**: Full medication lists with safety analysis
- **Real-time**: Check new medication combinations
- **Value**: Prevents adverse events, improves patient safety

### Phase 3: Quality & Education

#### 7. Quality of Care Audits (Use Case 7)
- **Pre-computed**: Adherence to guidelines metrics
- **Dashboard**: Department and physician comparisons
- **Value**: Improves care standardization

#### 8. Educational Case Generation (Use Case 8)
- **Pre-computed**: Teaching cases with quiz questions
- **Interactive**: Case-based learning modules
- **Value**: Enhances medical education

## Streamlit Application Structure

### Page Layout and Navigation (Implemented)

```
Healthcare AI Demo
├── 1_🏥_Data_Foundation.py (IMPLEMENTED)
├── 2_🩺_Clinical_Decision_Support.py (IMPLEMENTED - PRIMARY DEMO)
├── 3_🔬_Prompt_and_Model_Testing.py (IMPLEMENTED - REAL-TIME TESTING)
├── 4_📊_Population_Health_Analytics.py (IMPLEMENTED)
├── 5_💰_Cost_Analysis.py (IMPLEMENTED)
├── 6_💊_Medication_Safety.py (IMPLEMENTED)
├── 7_📈_Quality_Metrics.py (IMPLEMENTED)
├── 8_🤖_AI_Model_Performance.py (IMPLEMENTED)
└── 9_📋_Demo_Guide.py (IMPLEMENTED)
```

### Page Details

#### Page 1: Data Foundation
- PMC dataset overview and statistics
- Data quality metrics
- Sample patient records
- Processing pipeline status

#### Page 2: Clinical Decision Support (PRIMARY)
- **Patient Search**: Find patients by ID, condition, or symptoms
- **Clinical Summary**: SBAR format with key highlights
- **Differential Diagnosis**: Interactive diagnosis explorer
- **Similar Patients**: View and compare similar cases
- **Treatment Recommendations**: Evidence-based suggestions
- **Literature Links**: Relevant articles from RELEVANT_ARTICLES

#### Page 3: Prompt and Model Testing (REAL-TIME)
- **Based on superannuation demo page 2**
- Select a patient note
- Edit the text freely
- Process with Cortex AI in real-time
- Show step-by-step AI analysis
- Display results progressively

#### Page 4: Population Health Analytics
- Cohort analysis tools
- Disease prevalence maps
- Treatment effectiveness comparisons
- Cost analysis by condition
- Outcome predictions

#### Page 5: Cost Analysis
- **Procedure Cost Estimation**: Extract procedures from notes and estimate costs
- **Financial Impact Dashboard**: Link clinical activity to financial outcomes
- **High-Cost Patient Identification**: Find patients with expensive care patterns
- **Cost Driver Analysis**: Identify what clinical factors drive costs
- **Department/Condition Cost Comparisons**: Benchmark analysis
- **ROI Demonstration**: Show how AI insights can reduce costs

#### Page 6: Medication Safety
- Drug interaction checker
- Adverse event analysis
- Medication reconciliation
- Polypharmacy alerts

#### Page 7: Quality Metrics
- Care quality dashboards
- Guideline adherence rates
- Benchmark comparisons
- Improvement opportunities

#### Page 8: AI Model Performance
- Processing metrics
- Model accuracy indicators
- Prompt engineering examples
- Cost/performance analysis

#### Page 9: Demo Guide (ENHANCED)
- **Quick Start Guide**: 5-minute demo flows and timing
- **Data Story**: Comprehensive explanation of data sources and how each page uses data
- **Data Management**: Live subset expansion and batch processing controls
- **Demo Scenarios**: Pre-configured scenarios with talking points
- **Technical Architecture**: System diagrams and component details
- **Talking Points**: Audience-specific messaging (Executive, Clinical, Technical)
- **FAQ**: Common questions and responses
- **Troubleshooting**: Issue resolution and performance optimization

## AI Processing Design

### Batch Processing Pipeline (OPTIMIZED)

The current implementation uses `scripts/batch_process_all_patients_optimized.py` with a **consolidated prompt approach** that processes all 8 use cases in a single API call per patient:

- **Performance**: 5-8x faster than individual prompts (15-25 seconds vs 90+ seconds per patient)
- **Consistency**: Single claude-4-sonnet model ensures uniform output quality
- **Reliability**: Reduced API calls minimize failure points

The optimized pipeline populates:
- `PATIENT_ANALYSIS` (comprehensive analysis with all use cases)
- `MEDICATION_ANALYSIS` (extracted meds, interactions, safety)
- `COST_ANALYSIS` (procedures, estimated costs, drivers)

Processing is parallelized and tracked in `PROCESSING_STATUS`. Real-time demos are logged to `REALTIME_ANALYSIS_LOG`.

### Real-time Processing Design

The real-time showcase is implemented in `src/pages/3_🔬_Prompt_and_Model_Testing.py`. It uses the same consolidated prompt approach for consistency with batch processing. Results are logged to `REALTIME_ANALYSIS_LOG`. This page is the only place where on-demand AI runs during the demo; all other dashboards read from pre-computed tables.

## Prompt Engineering Templates

### Consolidated Analysis Prompt (OPTIMIZED APPROACH)

The implementation uses a single comprehensive prompt that analyzes all 8 use cases simultaneously:

```
Analyze these patient notes comprehensively across all healthcare AI use cases:

{patient_notes}

Create a single comprehensive JSON response with ALL the following sections:
- clinical_summary (SBAR format)
- differential_diagnosis (diagnoses with evidence)
- medication_safety (drug interactions, contraindications)
- treatment_analysis (current treatments, recommendations)
- pattern_recognition (anomaly detection, rare diseases)
- quality_metrics (guideline adherence, quality indicators)
- cost_analysis (procedures, cost drivers)
- educational_value (teaching points, clinical pearls)
```

This consolidated approach provides:
- **5-8x faster processing** compared to individual prompts
- **Consistent formatting** across all use cases
- **Reduced API failure points** for improved reliability
- **Cross-use-case insights** that individual prompts might miss

### Individual Prompt Templates (Legacy/Reference)

Individual prompts are maintained in `prompts_config.py` for reference and potential future use, but the optimized batch processing uses the consolidated approach above.

## Demo Scenarios

### Scenario 1: Complex Diagnostic Case
- **Patient**: 66-year-old with seizures and cardiac arrhythmia
- **Demo Flow**: Show differential diagnosis → Similar patients → Treatment options
- **Key Point**: AI identifies rare cardiac-neurological connection

### Scenario 2: Pediatric Rare Disease
- **Patient**: 11-year-old with multicentric peripheral ossifying fibroma
- **Demo Flow**: Rare disease detection → Literature review → Treatment protocol
- **Key Point**: AI recognizes rare pediatric condition

### Scenario 3: Cost Optimization
- **Patient**: High-utilization patient with multiple conditions
- **Demo Flow**: Cost analysis → Intervention opportunities → Outcome prediction
- **Key Point**: AI identifies cost-saving care coordination

## Technical Specifications

### Snowflake Configuration
- **Database**: HEALTHCARE_DEMO
- **Schema**: MEDICAL_NOTES
- **Warehouse**: COMPUTE_WH (or specified warehouse)
- **Cortex Models**: 
  - claude-4-sonnet (all use cases - consolidated approach for consistency and performance)

### Performance Requirements
- Batch processing: 150-240 patients/hour (optimized consolidated processing: 15-25 seconds per patient)
- Real-time analysis: < 30 seconds response
- Dashboard queries: < 2 seconds
- Concurrent users: 10-20

### Security Considerations
- All data remains within Snowflake
- No PHI in demo environment
- Role-based access control
- Audit logging for compliance

## Success Metrics

### Demo Success
- Complete patient analysis in < 30 seconds
- Clear value proposition for each persona
- Smooth navigation between use cases
- No technical failures during presentation

### Business Value
- 15-20% reduction in diagnostic time
- 25% improvement in treatment adherence
- 30% reduction in documentation time
- ROI within 6 months of implementation

## Future Enhancements

### Phase 2 Possibilities
- Integration with real EMR systems
- Continuous learning from user feedback
- Multi-language support
- Voice-to-text for note creation
- Mobile application

### Advanced Analytics
- Predictive modeling for outcomes
- Real-time clinical decision support
- Automated quality reporting
- Research cohort identification

---

*This design document serves as the blueprint for the Healthcare AI Demo. All implementation should follow these specifications unless explicitly modified.*