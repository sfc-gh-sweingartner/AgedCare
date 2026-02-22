# DRI Intelligence Solution - Functional Design Document

## Executive Summary

This document defines the functional design for replacing Telstra Health's regex/rules-based DRI (Deteriorating Resident Index) scoring system with an LLM-powered intelligent analysis solution using Snowflake Cortex and Claude 4.5.

**Business Problem**: The current system flags ~10% false positives (e.g., "patient's son has asthma" flagged as patient condition). Target is <1% false positives to maintain market position.

**Solution**: Context-aware LLM analysis for indicator detection only, with human-in-the-loop approval, prompt engineering UI, and RAG-enhanced context. DRI score calculation remains a standard deterministic formula for compliance and auditability.

---

## 1. Solution Overview

### 1.1 Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGED CARE SOURCE SYSTEM                              │
│  (Progress Notes, Medical Profile, Assessment Forms, Medications,           │
│   Observations, Observation Groups)                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (Existing ETL)
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SNOWFLAKE DATA LAYER                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │ ACTIVE_RESIDENT_ │  │ ACTIVE_RESIDENT_ │  │ ACTIVE_RESIDENT_ │          │
│  │ NOTES            │  │ MEDICAL_PROFILE  │  │ ASSESSMENT_FORMS │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │ ACTIVE_RESIDENT_ │  │ ACTIVE_RESIDENT_ │  │ ACTIVE_RESIDENT_ │          │
│  │ MEDICATION       │  │ OBSERVATIONS     │  │ OBSERVATION_GROUP│          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   CLIENT CONFIGURATION LAYER                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  DRI_CLIENT_CONFIG (Per-client assessment form mappings)            │   │
│  │  - Maps client-specific form fields to standard DRI indicators      │   │
│  │  - Supports client onboarding without code changes                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DRI INTELLIGENCE ENGINE                                 │
│                                                                              │
│  ┌─────────────────────┐    ┌─────────────────────┐                        │
│  │   RAG Knowledge     │    │   Cortex Search     │                        │
│  │   Base              │    │   Service           │                        │
│  │   - DRI Indicators  │    │   - Indicator Defs  │                        │
│  │   - Business Rules  │    │   - Clinical Terms  │                        │
│  │   - Past Decisions  │    │   - Client Configs  │                        │
│  │   - Temporal Rules  │    │                     │                        │
│  └─────────────────────┘    └─────────────────────┘                        │
│            │                         │                                      │
│            └────────────┬────────────┘                                      │
│                         ▼                                                   │
│  ┌───────────────────────────────────────────────────────────────┐         │
│  │                   SNOWFLAKE CORTEX                             │         │
│  │                   Claude 4.5 (Australia)                       │         │
│  │                                                                │         │
│  │   Input: Resident records + RAG context + Client config        │         │
│  │   Output: JSON with indicators, confidence, evidence,          │         │
│  │           temporal status, source traceability                 │         │
│  └───────────────────────────────────────────────────────────────┘         │
│                         │                                                   │
└─────────────────────────┼───────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      OUTPUT TABLES (Human Review Queue)                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │ DRI_LLM_ANALYSIS │  │ DRI_REVIEW_QUEUE │  │ DRI_AUDIT_LOG    │          │
│  │ (Raw LLM output) │  │ (Pending review) │  │ (All decisions)  │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼ (After Human Approval)
┌─────────────────────────────────────────────────────────────────────────────┐
│              EXISTING DRI OUTPUT TABLES (Fact/Dimension Model)               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │ DRI_DEFICIT_     │  │ DRI_DEFICIT_     │  │ DRI_DEFICIT_     │          │
│  │ DETAIL           │  │ STATUS           │  │ SUMMARY          │          │
│  │ (Fact table)     │  │ (Status tracking)│  │ (Aggregated)     │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                              │
│  Schema maintained for Power BI compatibility:                               │
│  - DRI_DEFICIT_DETAIL: resident_id, deficit_id, rule_number, source_id,     │
│    source_table, source_type, result, event_date, rule_status, expiry_days  │
│  - DRI_DEFICIT_STATUS: resident_id, deficit_id, deficit_status,             │
│    deficit_start_date, deficit_expiry_date, deficit_last_occurrence         │
│  - DRI_DEFICIT_SUMMARY: resident_id, dri_score, severity_band               │
└─────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼ (Existing Interface)
┌─────────────────────────────────────────────────────────────────────────────┐
│              POWER BI REPORT (Embedded in Source System)                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| RAG Knowledge Base | Provide DRI context to LLM | Cortex Search + Snowflake tables |
| Client Config Layer | Handle per-client assessment form mappings | JSON config tables |
| LLM Analysis Engine | Intelligent **indicator detection** (not DRI calculation) | Cortex Complete (Claude 4.5) |
| DRI Calculator | Standard formula: active_deficits / 33 | SQL/Python script |
| Prompt Engineering UI | Business user prompt tuning | Streamlit on SPCS |
| Review Queue | Human approval workflow | Snowflake tables + Streamlit |
| Batch Processor | Scheduled analysis runs | Snowflake Notebook/Task |
| Quality Metrics | Approval-based prompt quality scoring | SQL Views + DRI_REVIEW_QUEUE |

---

## 2. Functional Requirements

### 2.1 Source Data Tables

The solution reads from **six** source tables (existing ETL populates these):

| Table | Description | Key Fields |
|-------|-------------|------------|
| ACTIVE_RESIDENT_NOTES | Progress notes (free text) | resident_id, progress_note_id, note_text, event_date |
| ACTIVE_RESIDENT_MEDICAL_PROFILE | Special needs, conditions | resident_id, condition_type, condition_value |
| ACTIVE_RESIDENT_ASSESSMENT_FORMS | Structured form responses | resident_id, form_id, form_name, question, response |
| ACTIVE_RESIDENT_MEDICATION | Prescribed medications | resident_id, med_id, med_name, dosage, frequency |
| ACTIVE_RESIDENT_OBSERVATIONS | Individual observations | resident_id, observation_id, chart_name, observation_value |
| ACTIVE_RESIDENT_OBSERVATION_GROUP | Grouped observations | resident_id, observation_group_id, chart_name, observation_description, observation_location |

### 2.2 Core Processing Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Batch   │───▶│ Retrieve │───▶│  Client  │───▶│   RAG    │───▶│   LLM    │
│ Trigger  │    │ Records  │    │  Config  │    │ Context  │    │ Analysis │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
  Scheduled       From all 6      Apply form      Lookup DRI      Claude 4.5
  daily run       source tables   mappings        indicators      processing
                                                        │
                          ┌─────────────────────────────┘
                          ▼
                   ┌──────────┐    ┌──────────┐
                   │  Store   │───▶│  Output  │
                   │ Results  │    │  Tables  │
                   └──────────┘    └──────────┘
                     Review         Fact/Dim
                     queue          for Power BI
```

**Step 1: Batch Trigger**
- Scheduled daily (configurable time)
- Processes records modified since last run
- **On-demand testing**: Streamlit UI allows selection of specific residents for immediate processing

**Step 2: Record Retrieval**
- Aggregates data per resident from all **6** source tables
- Creates consolidated resident context for LLM

**Step 3: Client Configuration**
- Looks up client-specific assessment form mappings
- Normalizes client-specific field names to standard DRI indicators
- Enables new client onboarding without code changes

**Step 4: RAG Context Enrichment**
- Retrieves relevant DRI indicator definitions
- Includes applicable business rules and temporal logic
- References similar historical decisions

**Step 5: LLM Analysis (Indicator Detection Only)**
- Single comprehensive prompt per resident
- Returns structured JSON with all 33 indicators assessed
- Includes confidence scores, evidence, and temporal status
- **Does NOT calculate DRI score** (this is done by standard script)

**Step 6: Result Storage**
- Raw LLM output stored for audit (DRI_LLM_ANALYSIS)
- Flagged indicators added to review queue (DRI_REVIEW_QUEUE)
- **After approval**: Updates DRI_DEFICIT_STATUS table

**Step 7: DRI Score Calculation (Standard Script)**
- Runs after human approval updates DRI_DEFICIT_STATUS
- Counts ACTIVE deficits per resident
- Calculates: `dri_score = active_deficits / 33`
- Looks up severity_band from DRI_SEVERITY table
- Updates DRI_DEFICIT_SUMMARY for Power BI

### 2.3 Client-Specific Configuration

Clients customize their assessment forms. The solution handles this via a configuration layer:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CLIENT CONFIGURATION FLOW                                │
│                                                                              │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       │
│  │ Client A Forms  │     │ DRI_CLIENT_     │     │ Standard DRI    │       │
│  │ - "Fall Risk    │────▶│ CONFIG          │────▶│ Indicators      │       │
│  │    Assessment"  │     │                 │     │ - FALL_01       │       │
│  │ - Field: "risk" │     │ Maps client     │     │ - FALL_02       │       │
│  └─────────────────┘     │ form fields to  │     └─────────────────┘       │
│                          │ DRI indicators  │                                │
│  ┌─────────────────┐     │                 │                                │
│  │ Client B Forms  │     │ JSON per client │                                │
│  │ - "Falls Screen"│────▶│ defining field  │                                │
│  │ - Field: "score"│     │ mappings        │                                │
│  └─────────────────┘     └─────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Configuration Table Structure:**
```json
{
  "client_system_key": "SYS_Clinical_Manager_ClientA",
  "form_mappings": [
    {
      "form_name_pattern": "Fall Risk Assessment",
      "field_mappings": [
        {
          "source_field": "risk_level",
          "target_indicator": "FALL_01",
          "value_mapping": {
            "High": "flag",
            "Medium": "flag",
            "Low": "no_flag"
          }
        }
      ]
    }
  ]
}
```

**Impact on RAG and Prompts:**
- RAG knowledge base includes client-specific form mappings
- Prompt receives normalized data regardless of client form structure
- New clients onboarded by adding configuration, not code changes

### 2.4 Deficit Temporal Logic

Some deficits have expiry or persistence windows. The LLM output includes temporal status:

| Temporal Type | Example | LLM Handling |
|---------------|---------|--------------|
| **Acute/Expiring** | Fracture recovery | Flag with expiry_date, auto-expire after window |
| **Chronic/Persistent** | Diabetes, COPD | Flag without expiry, persists until explicitly removed |
| **Recurrent** | UTI, Falls | Track occurrence count, flag if threshold met in window |

**Enhanced LLM Output with Temporal Logic:**
```json
{
  "deficit_id": "FRAC_01",
  "deficit_name": "Recent Fracture",
  "detected": true,
  "temporal_status": {
    "type": "acute",
    "onset_date": "2025-01-15",
    "expected_duration_days": 90,
    "expiry_date": "2025-04-15",
    "persistence_rule": "Auto-expire unless new evidence"
  },
  "evidence": [...]
}
```

### 2.5 Separation of Concerns: Detection vs Calculation

**Why Claude Does NOT Calculate DRI Score:**

| Task | Owner | Rationale |
|------|-------|----------|
| Indicator detection | Claude (LLM) | Requires context understanding ("patient vs family member") |
| DRI score calculation | Standard script | Simple arithmetic, auditable, compliant with industry standard |
| Temporal expiry | Standard script | Rule-based, deterministic |
| Severity band lookup | Standard script | Table lookup, no interpretation needed |

**Benefits of this split:**
1. **Compliance**: Formula is auditable SQL, not a "black box" prompt
2. **Maintainability**: Formula changes don't require prompt updates
3. **Cost**: Fewer tokens per resident (no calculation instructions)
4. **Auditability**: Clear separation - "Claude detected X, formula gave Y"

### 2.6 DRI Indicator Analysis (Claude Output)

The LLM assesses all 33 DRI deficit indicators in a single call, returning **detection results only**:

```json
{
  "resident_id": "12345",
  "client_system_key": "SYS_Clinical_Manager_ClientA",
  "analysis_timestamp": "2025-01-27T10:30:00Z",
  "model_used": "claude-4-sonnet",
  "summary": {
    "indicators_detected": 2,
    "indicators_cleared": 1,
    "requires_review_count": 2,
    "analysis_notes": "Two new indicators detected requiring attention"
  },
  "indicators": [
    {
      "deficit_id": "RESP_01",
      "deficit_name": "Respiratory Condition",
      "detected": true,
      "confidence": 0.92,
      "temporal_status": {
        "type": "chronic",
        "persistence_rule": "Persists until clinical resolution documented"
      },
      "reasoning": "Patient notes from 2025-01-25 document diagnosis of COPD with current oxygen therapy requirement",
      "evidence": [
        {
          "source_table": "ACTIVE_RESIDENT_NOTES",
          "source_id": "NOTE_789",
          "source_type": "Progress Notes",
          "text_excerpt": "Diagnosed with moderate COPD, requiring 2L O2 via nasal cannula",
          "event_date": "2025-01-25",
          "entered_by_user": "nurse_smith"
        }
      ],
      "false_positive_check": {
        "family_reference": false,
        "historical_only": false,
        "negated_statement": false
      },
      "suggested_action": "Add respiratory deficit to DRI profile",
      "requires_review": true
    },
    {
      "deficit_id": "RESP_02", 
      "deficit_name": "Asthma",
      "detected": false,
      "confidence": 0.95,
      "reasoning": "Note mentions 'son has asthma' - this is a family member reference, not resident condition",
      "evidence": [
        {
          "source_table": "ACTIVE_RESIDENT_NOTES",
          "source_id": "NOTE_456",
          "source_type": "Progress Notes",
          "text_excerpt": "Discussed family history - son has asthma",
          "event_date": "2025-01-20",
          "entered_by_user": "dr_jones"
        }
      ],
      "false_positive_check": {
        "family_reference": true,
        "historical_only": false,
        "negated_statement": false
      },
      "suggested_action": "No change - family reference only",
      "requires_review": false
    }
  ],
  "processing_metadata": {
    "records_analyzed": 15,
    "processing_time_ms": 2340,
    "prompt_version": "v1.2",
    "client_config_version": "v2.1"
  }
}
```

**Note**: The JSON does NOT include `dri_score` or `severity_band`. These are calculated by the standard script after human approval.

### 2.7 DRI Score Calculation (Standard Script)

After indicators are approved, a deterministic script calculates the DRI:

```sql
-- DRI Score Calculation (runs after human approval)
WITH active_counts AS (
    SELECT 
        resident_id,
        COUNT(*) as active_deficits
    FROM DRI_DEFICIT_STATUS
    WHERE deficit_status = 'ACTIVE'
    GROUP BY resident_id
)
SELECT 
    a.resident_id,
    CURRENT_TIMESTAMP() as load_timestamp,
    a.active_deficits / 33.0 as dri_score,
    s.DRI_SEVERITY_NAME as severity_band
FROM active_counts a
LEFT JOIN DRI_SEVERITY s 
    ON a.active_deficits / 33.0 BETWEEN s.DRI_SEVERITY_MINIMUM_VALUE AND s.DRI_SEVERITY_MAXIMUM_VALUE;
```

This formula:
- Is **identical** to the existing production calculation
- Is **auditable** and **compliant** with industry standards
- Can be **changed independently** of Claude prompts

### 2.8 Explainability & Traceability

**Critical Requirement**: Every LLM-identified deficit must link back to source records.

### 2.8.1 Approval-Based Quality Metrics

The solution uses the human approval workflow as the primary quality signal:

| Metric | Purpose | How Calculated |
|--------|---------|----------------|
| **Approval Rate** | Measures prompt effectiveness | Approved / (Approved + Rejected) per prompt version |
| **Rejection Reasons** | Identifies prompt weaknesses | Aggregated from reviewer notes |
| **False Positive Rate** | Tracks incorrect detections | Rejected indicators / Total detected |
| **Ground Truth Coverage** | Measures validation dataset size | Count of validated indicator decisions |

**Architecture Decision**: Simplified approach
- **Streamlit UI**: Clinician-facing interface with quality dashboards
- **DRI_REVIEW_QUEUE**: Source of truth for quality signals (approvals/rejections)
- **DRI_GROUND_TRUTH**: Auto-populated from approved/rejected review decisions
- **V_PROMPT_QUALITY_SCORE**: SQL view aggregating approval rates by prompt version

**Key Insight**: The human-in-the-loop approval workflow provides better quality signals than LLM-as-judge metrics because:
1. Reviewers assess clinical accuracy, not just LLM behavior
2. Rejection reasons provide actionable feedback for prompt improvement
3. Approved decisions become validated ground truth for future testing

| Traceability Field | Description | Example |
|--------------------|-------------|---------|
| source_table | Which of the 6 tables | ACTIVE_RESIDENT_NOTES |
| source_id | Primary key of source record | NOTE_789, FORM_456 |
| source_type | Human-readable type | "Progress Notes", "Fall Risk Assessment" |
| text_excerpt | Exact text that triggered finding | "Diagnosed with moderate COPD..." |
| event_date | When the source record was created | 2025-01-25 |
| entered_by_user | Who created the source record | nurse_smith |

**Audit Trail**: All evidence is stored in DRI_LLM_ANALYSIS.RAW_RESPONSE and can be queried for compliance/audit purposes.

### 2.9 Human Review Workflow

**Approval Level**: The review workflow operates at the **aggregate DRI score change level**, not individual indicator level. When the LLM detects indicator changes that would affect a resident's DRI score, a single review item is created summarizing the proposed changes.

```
┌─────────────────────────────────────────────────────────────────┐
│                    REVIEW QUEUE STATUS                          │
├─────────────────────────────────────────────────────────────────┤
│  PENDING    │  IN_REVIEW  │  APPROVED   │  REJECTED            │
│  New DRI    │  Reviewer   │  DRI score  │  Changes             │
│  changes    │  examining  │  updated    │  discarded           │
│  from LLM   │  indicators │             │                      │
└─────────────────────────────────────────────────────────────────┘
```

**Review Queue Fields (Aggregate View):**
- Resident ID and name
- **Current DRI score and severity band**
- **Proposed DRI score and severity band**
- **Summary of indicator changes** (e.g., "+2 indicators detected, -1 cleared")
- List of affected indicators with confidence scores
- **Expandable detail view** showing all indicator evidence
- Single approve/reject action for the entire DRI change
- Optional reviewer notes

**Approval Actions:**
- **Approve All**: Accepts ALL proposed indicator changes, updates DRI_DEFICIT_DETAIL, DRI_DEFICIT_STATUS, DRI_DEFICIT_SUMMARY
- **Reject Specific Indicators**: Reviewer selects which indicators are incorrect and provides a reason for each. This creates:
  - Individual rejection records in DRI_INDICATOR_REJECTIONS (for prompt improvement analysis)
  - STATUS = 'PARTIAL_REJECT' if some indicators accepted, 'REJECTED' if all rejected
  - EXCLUDED_INDICATORS array with rejected indicator IDs
  - REVIEWER_NOTES with summary of all rejection reasons

**Rejection Workflow (v1.8):**
1. Reviewer clicks "Reject Some..."
2. Selects specific indicators to reject via checkboxes
3. Enters reason for each rejected indicator (required)
4. Submits rejections - records saved to DRI_INDICATOR_REJECTIONS
5. Queue item updated with excluded indicators and notes

**Rejection Reason Examples:**
- "False positive - no supporting evidence in notes"
- "Misinterpretation - medication is PRN not regular"
- "Outdated - condition resolved per latest assessment"
- "Wrong indicator - symptoms match different condition"

### 2.10 Prompt Engineering Interface

Business users (trained medical professionals) can tune prompts via a Streamlit UI:

**Features:**
1. **Prompt Editor**: Edit the comprehensive analysis prompt
2. **Test Mode**: Run prompt against sample residents without saving
3. **Compare Results**: Side-by-side view of old vs new prompt results
4. **Version Control**: Save prompt versions with descriptions
5. **Promote to Production**: Make tested prompt the active version

**Prompt Template Structure:**
```
You are an expert aged care clinical analyst. Analyze the following resident records 
to identify DRI (Deteriorating Resident Index) conditions.

CRITICAL INSTRUCTIONS:
- Only flag conditions that apply DIRECTLY to this resident
- Do NOT flag conditions mentioned for family members
- Do NOT flag historical conditions that have resolved
- Do NOT flag negated statements (e.g., "no signs of diabetes")
- Identify temporal type (acute vs chronic) for each indicator
- Do NOT calculate DRI scores - only detect indicators

CLIENT CONFIGURATION:
{client_form_mappings}

RESIDENT DATA:
{resident_context}

DRI INDICATOR DEFINITIONS:
{rag_indicator_context}

TEMPORAL RULES:
{rag_temporal_rules}

BUSINESS RULES:
{rag_business_rules}

For each finding, you MUST provide:
- The specific source_table and source_id where you found the evidence
- The exact text excerpt that supports your finding
- The event_date and entered_by_user if available

Return your analysis as JSON with the following structure:
{json_schema}
```

---

## 3. Data Model

### 3.1 New Tables

#### DRI_LLM_ANALYSIS
Stores raw LLM output for audit, traceability, and reprocessing.

| Column | Type | Description |
|--------|------|-------------|
| ANALYSIS_ID | VARCHAR | Primary key (UUID) |
| RESIDENT_ID | NUMBER | Foreign key to resident |
| CLIENT_SYSTEM_KEY | VARCHAR | Which client's data |
| ANALYSIS_TIMESTAMP | TIMESTAMP_NTZ | When analysis ran |
| MODEL_USED | VARCHAR | e.g., claude-4-sonnet |
| PROMPT_VERSION | VARCHAR | Which prompt was used |
| CLIENT_CONFIG_VERSION | VARCHAR | Which client config used |
| RAW_RESPONSE | VARIANT | Full JSON from LLM (includes all evidence) |
| PROCESSING_TIME_MS | NUMBER | Performance metric |
| BATCH_RUN_ID | VARCHAR | Groups analysis runs |

#### DRI_REVIEW_QUEUE
Aggregate DRI changes pending human review (one row per resident per analysis run).

| Column | Type | Description |
|--------|------|-------------|
| QUEUE_ID | VARCHAR | Primary key (UUID) |
| ANALYSIS_ID | VARCHAR | Foreign key to DRI_LLM_ANALYSIS |
| RESIDENT_ID | NUMBER | Foreign key to resident |
| CLIENT_SYSTEM_KEY | VARCHAR | Which client |
| CURRENT_DRI_SCORE | FLOAT | DRI score before changes |
| PROPOSED_DRI_SCORE | FLOAT | DRI score if changes applied |
| CURRENT_SEVERITY_BAND | VARCHAR | Severity band before changes |
| PROPOSED_SEVERITY_BAND | VARCHAR | Severity band if changes applied |
| INDICATORS_ADDED | NUMBER | Count of new indicators detected |
| INDICATORS_REMOVED | NUMBER | Count of indicators cleared |
| INDICATOR_CHANGES_JSON | VARIANT | Array of all indicator changes with evidence |
| CHANGE_SUMMARY | TEXT | Human-readable summary of changes |
| STATUS | VARCHAR | PENDING, APPROVED, REJECTED, PARTIAL_REJECT |
| REVIEWER_USER | VARCHAR | Who reviewed |
| REVIEWER_NOTES | TEXT | Rejection summary (auto-generated from indicator rejections) |
| EXCLUDED_INDICATORS | VARIANT | Array of indicator IDs rejected (for PARTIAL_REJECT) |
| REVIEW_TIMESTAMP | TIMESTAMP_NTZ | When reviewed |
| CREATED_TIMESTAMP | TIMESTAMP_NTZ | When added to queue |

#### DRI_INDICATOR_REJECTIONS
Stores detailed rejection feedback for individual indicators (for prompt improvement analysis).

| Column | Type | Description |
|--------|------|-------------|
| REJECTION_ID | VARCHAR | Primary key (UUID) |
| QUEUE_ID | VARCHAR | Foreign key to DRI_REVIEW_QUEUE |
| INDICATOR_ID | VARCHAR | The rejected indicator (e.g., RESP_01) |
| INDICATOR_NAME | VARCHAR | Human-readable indicator name |
| REJECTION_REASON | TEXT | Detailed explanation of why rejected |
| REJECTED_BY | VARCHAR | User who rejected |
| REJECTED_TIMESTAMP | TIMESTAMP_NTZ | When rejected |

#### DRI_CLIENT_CONFIG
Per-client assessment form mappings.

| Column | Type | Description |
|--------|------|-------------|
| CONFIG_ID | VARCHAR | Primary key (UUID) |
| CLIENT_SYSTEM_KEY | VARCHAR | e.g., SYS_Clinical_Manager_ClientA |
| CLIENT_NAME | VARCHAR | Human-readable name |
| CONFIG_JSON | VARIANT | Form field mappings (see Section 2.3) |
| VERSION | VARCHAR | Config version |
| IS_ACTIVE | BOOLEAN | Currently in use |
| CREATED_BY | VARCHAR | Who created |
| CREATED_TIMESTAMP | TIMESTAMP_NTZ | When created |

#### DRI_PROMPT_VERSIONS
Stores prompt templates and versions.

| Column | Type | Description |
|--------|------|-------------|
| PROMPT_ID | VARCHAR | Primary key (UUID) |
| VERSION_NUMBER | VARCHAR | e.g., v1.0, v1.1 |
| PROMPT_TEXT | TEXT | Full prompt template |
| DESCRIPTION | TEXT | What changed |
| CREATED_BY | VARCHAR | Who created |
| CREATED_TIMESTAMP | TIMESTAMP_NTZ | When created |
| IS_ACTIVE | BOOLEAN | Currently in production |

#### DRI_RAG_INDICATORS
Knowledge base for RAG retrieval.

| Column | Type | Description |
|--------|------|-------------|
| INDICATOR_ID | VARCHAR | e.g., RESP_01 |
| DEFICIT_ID | VARCHAR | Maps to existing deficit |
| INDICATOR_NAME | VARCHAR | Display name |
| DEFINITION | TEXT | Full clinical definition |
| KEYWORDS | VARIANT | Array of related terms |
| INCLUSION_CRITERIA | TEXT | When to flag |
| EXCLUSION_CRITERIA | TEXT | When NOT to flag |
| TEMPORAL_TYPE | VARCHAR | acute, chronic, recurrent |
| DEFAULT_EXPIRY_DAYS | NUMBER | For acute deficits |
| EXAMPLES | VARIANT | Positive/negative examples |

#### DRI_RAG_DECISIONS
Historical decisions for RAG learning.

| Column | Type | Description |
|--------|------|-------------|
| DECISION_ID | VARCHAR | Primary key |
| DEFICIT_ID | VARCHAR | Which indicator |
| SOURCE_TEXT | TEXT | The text analyzed |
| DECISION | VARCHAR | APPROVED, REJECTED |
| REASONING | TEXT | Why decision made |
| CREATED_TIMESTAMP | TIMESTAMP_NTZ | When recorded |

### 3.2 Existing Output Tables (Schema Preserved)

The solution writes to existing tables to maintain Power BI compatibility:

#### DRI_DEFICIT_DETAIL (Existing - Fact Table)
| Column | Type | Notes |
|--------|------|-------|
| resident_id | NUMBER | |
| load_timestamp | TIMESTAMP | |
| deficit_id | VARCHAR | |
| rule_number | NUMBER | Maps to LLM indicator |
| rule_description | TEXT | LLM reasoning summary |
| source_id | VARCHAR | **Traceability link** |
| source_table | VARCHAR | **Traceability link** |
| source_type | VARCHAR | Human-readable |
| result | TEXT | Evidence excerpt |
| entered_by_user | VARCHAR | From source record |
| event_date | DATE | From source record |
| rule_status | VARCHAR | ACTIVE/INACTIVE |
| expiry_days | NUMBER | For temporal logic |
| client_name | VARCHAR | |

#### DRI_DEFICIT_STATUS (Existing)
| Column | Type | Notes |
|--------|------|-------|
| resident_id | NUMBER | |
| load_timestamp | TIMESTAMP | |
| deficit_id | VARCHAR | |
| deficit_status | VARCHAR | ACTIVE/INACTIVE |
| deficit_start_date | DATE | |
| deficit_expiry_date | DATE | For temporal logic |
| deficit_last_occurrence | DATE | |
| rule_number | NUMBER | |

#### DRI_DEFICIT_SUMMARY (Existing)
| Column | Type | Notes |
|--------|------|-------|
| resident_id | NUMBER | |
| load_timestamp | TIMESTAMP | |
| dri_score | FLOAT | active_deficits / 33 |
| severity_band | VARCHAR | From DRI_SEVERITY lookup |

### 3.3 Cortex Search Service

```sql
CREATE OR REPLACE CORTEX SEARCH SERVICE dri_indicator_search
    ON DRI_RAG_INDICATORS
    ATTRIBUTES INDICATOR_ID, DEFICIT_ID, INDICATOR_NAME, TEMPORAL_TYPE
    WAREHOUSE = CORTEX_SEARCH_WH
    TARGET_LAG = '1 hour'
    AS (
        SELECT 
            INDICATOR_ID,
            DEFICIT_ID,
            INDICATOR_NAME,
            TEMPORAL_TYPE,
            DEFINITION || ' ' || INCLUSION_CRITERIA AS SEARCHABLE_TEXT
        FROM DRI_RAG_INDICATORS
    );
```

---

## 4. User Interface Design

### 4.1 Streamlit Application Structure

```
DRI Intelligence POC (Implemented)
├── dashboard.py              :material/dashboard:     (Overview metrics and status)
├── prompt_engineering.py     :material/science:       (Edit and test prompts + Run Evaluation)
├── review_queue.py           :material/checklist:     (Human approval workflow)
├── analysis_results.py       :material/analytics:     (View LLM analysis details)
├── configuration.py          :material/settings:      (Settings, RAG, client config)
├── comparison.py             :material/compare_arrows: (Claude vs Regex - DEMO ONLY)
└── quality_metrics.py        :material/monitoring:    (AI Observability quality metrics)
```

**Navigation:** Uses `st.navigation()` with Material icons (implemented in streamlit_app.py)

### 4.2 Page Descriptions

#### Page 1: Dashboard (IMPLEMENTED)
- Residents in system count
- Pending reviews count
- DRI indicators count (33)
- Analyses run count
- Connection status indicator
- Navigation guide expander

#### Page 2: Prompt Engineering / Model Testing (IMPLEMENTED)
- Resident selector dropdown (populated from ACTIVE_RESIDENT_NOTES)
- Model selector (Claude 4.5 variants + other Cortex models)
- Prompt version selector from DRI_PROMPT_VERSIONS
- Editable prompt text area with variable placeholders
- On-demand LLM execution with adaptive token sizing
- JSON result viewer with parsed indicator display
- Evidence display with source references
- Processing time and token mode indicator
- Save new prompt version functionality

#### Page 3: Review Queue (IMPLEMENTED)
- Filterable list of pending DRI changes from DRI_REVIEW_QUEUE
- Each item represents a resident's proposed DRI score change
- Status filtering (PENDING, APPROVED, REJECTED, PARTIAL_REJECT)
- Expandable detail view with indicator changes
- **Approve All**: Accepts all detected indicators
- **Reject Some...**: Two-phase rejection workflow:
  1. Select specific indicators to reject via checkboxes
  2. Enter reason for each rejection (required)
  3. Rejections stored in DRI_INDICATOR_REJECTIONS for prompt improvement
- View rejection details on already-rejected items
- Full batch ID displayed in Analysis Results (not truncated)

#### Page 4: Analysis Results (IMPLEMENTED)
- Browse all LLM analyses from DRI_LLM_ANALYSIS
- Filter by resident, date range, batch ID
- View full raw JSON response
- Processing time and model used
- Source traceability through evidence array

#### Page 5: Configuration (IMPLEMENTED - 5 Tabs)
- **Client Config Tab**: Client details, status, CONFIG_JSON viewer
- **Form Mappings Tab**: Read-only table of form-to-indicator mappings
- **Indicator Overrides Tab**: Read-only table of client overrides
- **RAG Indicators Tab**: Browse all 33 indicators with filtering
- **Processing Settings Tab**: Production model, prompt, schedule, token threshold

#### Page 6: Claude vs Regex Comparison (DEMO ONLY - To Be Removed)
**Note**: This page is for demonstration purposes only to show stakeholders the accuracy improvement of Claude over regex. It will be removed after the demo is complete.
- Side-by-side DRI score comparison
- Demo warning banner displayed at top
- Detailed indicator breakdown tabs

#### Batch Testing Page (Simplified)
This page provides batch analysis and approval-based quality metrics:
- **Batch Test**: Run DRI analysis on selected residents, store results for review
- **Prompt Quality Dashboard**: Shows approval rates by prompt version
- **Quality Trend**: Chart showing approval rate trends over time
- **Ground Truth Status**: Shows count of validated decisions available for testing
- **Explainability Log**: Links to DRI_LLM_ANALYSIS for audit trail

**Technical Integration**:
- Quality metrics derived from DRI_REVIEW_QUEUE (approvals/rejections)
- No external SPCS containers required
- Ground truth auto-populated from approved/rejected decisions
- SQL views provide real-time quality scoring

---

## 5. Integration Points

### 5.1 Input Integration
- **Source**: Existing ETL populates all 6 ACTIVE_RESIDENT_* tables
- **No changes required**: Solution reads from existing tables
- **Client config**: Existing JSON configs migrated to DRI_CLIENT_CONFIG table

### 5.2 Output Integration
- **Target**: Existing DRI_DEFICIT_* tables (schema preserved)
- **Power BI**: Continues to read from existing fact/dimension tables
- **No changes to Power BI**: Output schema matches existing model
- **New tables**: DRI_LLM_ANALYSIS, DRI_REVIEW_QUEUE for internal use only

### 5.3 Data Flow

```
Existing ETL ──▶ 6 Source Tables ──▶ Client Config ──▶ LLM Engine ──▶ Review Queue
                                                                           │
                                                                           ▼
                                                      ┌──────────────────────────┐
                                                      │ Existing DRI Tables      │
                                                      │ (Fact/Dimension Model)   │
                                                      └──────────────────────────┘
                                                                           │
                                                                           ▼
                                                      ┌──────────────────────────┐
                                                      │ Power BI Report          │
                                                      │ (No changes required)    │
                                                      └──────────────────────────┘
```

---

## 6. Processing Specifications

### 6.1 Batch Processing

| Parameter | Value |
|-----------|-------|
| Frequency | Daily (configurable) |
| Trigger | Snowflake Task |
| Records per batch | 100 residents |
| Parallelization | 5 concurrent threads |
| Timeout | 30 seconds per resident |
| Retry | 3 attempts with exponential backoff |

### 6.2 Performance Targets

| Metric | Target |
|--------|--------|
| False positive rate | <1% (from current 10%) |
| Processing time per resident | <30 seconds |
| Daily throughput | 5,000 residents |
| Review queue SLA | 24 hours |

### 6.3 Cost Considerations

| Component | Estimated Usage |
|-----------|-----------------|
| Cortex Complete (Claude 4.5) | ~2000 tokens per resident |
| Cortex Search | Minimal (reference lookups) |
| Compute warehouse | X-SMALL for batch processing |
| Storage | ~1KB per analysis record |

---

## 7. Security & Compliance

### 7.1 Data Handling
- All processing within Snowflake (no data egress)
- PHI remains in existing tables
- LLM analysis stored with same access controls
- Audit logging for all decisions

### 7.2 Access Control
- Prompt engineering: Restricted to trained medical professionals
- Review queue: Restricted to authorized reviewers
- Dashboard: Read-only for reporting users
- Configuration: Admin only

### 7.3 Audit Trail
- All LLM analyses logged with full evidence and source links
- Review decisions tracked with user and timestamp
- Prompt versions maintained with change history
- RAG and client config updates logged

---

## 8. POC Scope

### 8.1 In Scope
- LLM analysis replacing regex for all 33 indicators
- All 6 source tables processed
- Client configuration handling (single client for POC)
- Temporal logic for acute/chronic deficits
- Full traceability to source records
- Prompt engineering UI
- Human review workflow
- Basic dashboard
- RAG for indicator definitions and business rules
- Sample data testing
- Output to existing fact/dimension tables

### 8.2 Out of Scope (Future)
- Real-time processing
- Power BI modifications (not needed)
- Mobile interface
- Multi-client onboarding automation
- Automated prompt optimization
- LLM-as-judge evaluation metrics (removed in v1.7 - using approval-based metrics instead)

### 8.3 Success Criteria
1. False positive rate <1% on test dataset
2. Processing completes within daily batch window
3. Reviewers can approve/reject with <30 seconds per item
4. Prompt changes can be tested and deployed without IT
5. **Every flagged deficit links to specific source record(s)**
6. **Output compatible with existing Power BI reports**

---

## 9. Implementation Status

**All core features have been implemented as of 2026-01-30:**

| Feature | Status | Notes |
|---------|--------|-------|
| Database schema | ✅ Complete | All 15+ tables created in AGEDCARE.AGEDCARE |
| Demo data loading | ✅ Complete | 50 residents across 3 facilities |
| Cortex Search service | ✅ Complete | DRI_INDICATOR_SEARCH with 33 indicators |
| Dashboard page | ✅ Complete | Metrics display, connection status |
| Prompt Engineering page | ✅ Complete | Resident/model/version selector, run analysis |
| Review Queue page | ✅ Complete | Aggregate approval workflow |
| Analysis Results page | ✅ Complete | Browse LLM analyses |
| Configuration page | ✅ Complete | 5 tabs including processing settings |
| Claude vs Regex page | ✅ Complete (DEMO) | Side-by-side comparison - demo only, to be removed |
| Batch Testing page | ✅ Complete | Batch analysis + approval-based quality metrics |
| Adaptive token sizing | ✅ Complete | Context threshold-based mode selection |
| Production config storage | ✅ Complete | Model/prompt stored per-client in CONFIG_JSON |

---

## 10. Next Steps (Post-POC)

1. ~~Approve this functional design~~ ✅ Approved
2. ~~Create detailed technical design~~ ✅ Complete (v1.2)
3. ~~Set up POC environment~~ ✅ Complete
4. ~~Implement core components~~ ✅ Complete
5. ~~Test with sample data~~ ✅ Complete
6. **Demo to Telstra Health** - Pending
7. **Production onboarding** - After demo approval

---

## Appendix A: Feedback Incorporation

This document has been updated based on feedback from Telstra Health's data engineering team:

| Feedback Item | Resolution |
|---------------|------------|
| DRI = Deteriorating Resident Index | Acronym corrected throughout |
| Missing ACTIVE_RESIDENT_OBSERVATION_GROUP table | Added as 6th source table |
| Client-specific assessment form mappings | Added Section 2.3 and DRI_CLIENT_CONFIG table |
| Deficit temporal logic (expiry/persistence) | Added Section 2.4 and temporal_status in JSON output |
| Power BI fact/dimension alignment | Confirmed existing table schema preserved (Section 3.2) |
| Explainability & traceability | Enhanced evidence structure with source_id, source_table, text_excerpt (Section 2.8) |
| DRI formula is standard/agreed | Added Section 2.5 - Claude detects only, standard script calculates DRI (Section 2.7) |
| Approval at aggregate DRI level (v1.3) | Review queue now operates at resident DRI change level, not individual indicator level |
| On-demand testing for POC (v1.3) | Added resident selection capability in Prompt Engineering page for testing |

---

## Appendix B: DRI Business Rules Specification (33 Deficits)

This section documents the complete business rules for all 33 DRI deficit indicators as specified in the requirements document.

### B.1 Deficit Types

| Type | Description | Expiry Behavior |
|------|-------------|----------------|
| **PERSISTENT** | Chronic conditions that never expire once flagged | `expiry_days = 0` (never expires) |
| **FLUCTUATING** | Acute/recurrent conditions with time-limited flags | `expiry_days = 1-90` (auto-expire unless re-triggered) |

### B.2 Rule Types

| Rule Type | Description | Example |
|-----------|-------------|--------|
| `keyword_search` | Regex/keyword matching in free-text fields | "COPD", "asthma" in progress notes |
| `specific_value` | Exact dropdown/selection value matching | "Fall" in Type of Incident dropdown |
| `aggregation` | Count/percentage-based thresholds | ≥5 medications = polypharmacy |

### B.3 Functions

| Function Type | Purpose | Example |
|---------------|---------|--------|
| `inclusion_filter` | Restrict rule to specific form/field/value | form_name = "Comprehensive Medical Assessment" |
| `exclusion_filter` | Exclude specific locations/values | observation_location NOT IN ('foot', 'heel', 'toe') |
| `aggregation` | Group and count operations | COUNT(*) GROUP BY resident_id |

### B.4 Complete Deficit Specification

| Deficit # | Domain | Deficit Name | Type | Expiry Days | Lookback | Rule Type | Threshold | Key Notes |
|-----------|--------|--------------|------|-------------|----------|-----------|-----------|----------|
| D001 | Chronic Diseases | Respiratory | PERSISTENT | 0 | All | keyword_search | 1 | Never expires |
| D002 | Chronic Diseases | Cardiac | PERSISTENT | 0 | All | keyword_search | 1 | Never expires |
| D003 | Chronic Diseases | Neurological | PERSISTENT | 0 | All | keyword_search | 1 | Never expires |
| D004 | Chronic Diseases | Renal | PERSISTENT | 0 | All | keyword_search | 1 | Never expires |
| D005 | Chronic Diseases | Cancer | PERSISTENT | 0 | All | keyword_search | 1 | Never expires |
| D006 | Chronic Diseases | Peripheral Vascular Disease | PERSISTENT | 0 | All | keyword_search | 1 | Never expires |
| D007 | Chronic Diseases | Thyroid | PERSISTENT | 0 | All | keyword_search | 1 | Never expires |
| D008 | Blood-specific | Diabetes | PERSISTENT | 0 | All | keyword_search + specific_value | 1 | Includes dropdown values |
| D009 | Blood-specific | Blood Pressure | PERSISTENT | 0 | All | keyword_search | 1 | Never expires |
| D010 | Bone-specific | Osteoporosis | PERSISTENT | 0 | All | keyword_search | 1 | Never expires |
| D011 | Bone-specific | Arthritis | PERSISTENT | 0 | All | keyword_search | 1 | Never expires |
| D012 | Geriatric Syndrome | Falls | FLUCTUATING | 1 | 365 days | specific_value | 1 | 24hr expiry, 12-month lookback |
| D013 | Geriatric Syndrome | Ulcers GI | PERSISTENT | 0 | All | keyword_search | 1 | Never expires |
| D014 | Geriatric Syndrome | Ulcers Wound | FLUCTUATING | 1 | 90 days | keyword_search | 1 | Exclude foot locations, status-based |
| D015 | Geriatric Syndrome | Polypharmacy | FLUCTUATING | 1 | 1 day | aggregation | 5 | Count meds ≥5, exclude creams/drops |
| D016 | Geriatric Syndrome | Dysphagia | PERSISTENT | 0 | All | keyword_search + specific_value | 1 | Multiple sources |
| D017 | Geriatric Syndrome | Pain | FLUCTUATING | 1 | 7 days | specific_value | varies | Pain Chart ≥1, PainChek ≥7 |
| D018 | Geriatric Syndrome | Fracture | PERSISTENT | 0 | All | keyword_search + specific_value | 1 | Exclude suspected/no fracture |
| D019 | Cognition | Cognition | PERSISTENT | 0 | All | keyword_search | 1 | Never expires |
| D020 | Cognition | Dementia | PERSISTENT | 0 | All | keyword_search | 1 | Never expires |
| D021 | Nutrition | Weight Loss | FLUCTUATING | 90 | 90 days | aggregation + specific_value | 5% | MNA or 5% weight loss over quarter |
| D022 | Activities of Daily Life | ADL | FLUCTUATING | 3 | 72 hrs | specific_value | 1 | Hygiene/Dressing/Toileting |
| D023 | Activities of Daily Life | Mobility | FLUCTUATING | 1 | 7 days | specific_value | 1 | Transfer/mobility aids required |
| D024 | Elimination | Incontinence | FLUCTUATING | 10 | 10 days | aggregation | 50% | 50% incontinent over 10 days OR urinary chart |
| D025 | Emotional | Depression | FLUCTUATING | 90 | 90 days | keyword_search + specific_value | varies | GDS ≥6, Cornell ≥11, Progress Notes ≥2/month |
| D026 | Emotional | Anxiety | FLUCTUATING | 90 | 90 days | keyword_search + specific_value | varies | 1 in assessments, 2 in progress notes |
| D027 | Emotional | Insomnia | FLUCTUATING | 90 | 90 days | keyword_search + specific_value | varies | 1 in assessments, 3/18 in progress notes |
| D028 | Communication | Vision | PERSISTENT | 0 | All | keyword_search + specific_value | 1 | Never expires |
| D029 | Communication | Hearing | PERSISTENT | 0 | All | keyword_search + specific_value | 1 | Never expires |
| D030 | Other symptoms | Dyspnoea | FLUCTUATING | 60 | 60 days | keyword_search | varies | 1 in assessments, 3 in progress notes |
| D031 | Other symptoms | Anaemia | FLUCTUATING | 90 | 90 days | keyword_search | varies | 1 in assessments, 1 in progress notes |
| D032 | Other symptoms | Dizziness | FLUCTUATING | 60 | 60 days | keyword_search | varies | Exclude negated statements |
| D033 | Other symptoms | Foot/Feet | PERSISTENT | 0 | All | keyword_search + specific_value | 1 | Never expires |

### B.5 Complex Rule Examples

**D015 Polypharmacy (aggregation):**
```json
{
  "rule_type": "aggregation",
  "source_type": "ACTIVE_RESIDENT_MEDICATION",
  "threshold": 5,
  "functions": [
    {"function_type": "exclusion_filter", "key": "med_route", "value": "TOP"},
    {"function_type": "aggregation", "key": "resident_id", "value": "group by"},
    {"function_type": "aggregation", "key": "resident_id", "value": "count"}
  ]
}
```

**D014 Ulcers Wound (with exclusions):**
```json
{
  "rule_type": "keyword_search",
  "source_type": "ACTIVE_RESIDENT_OBSERVATION_GROUP",
  "threshold": 1,
  "functions": [
    {"function_type": "inclusion_filter", "key": "chart_name", "value": "Wound Chart"},
    {"function_type": "inclusion_filter", "key": "observation_status", "value": "Active"},
    {"function_type": "exclusion_filter", "key": "observation_location", "value": "foot"},
    {"function_type": "exclusion_filter", "key": "observation_location", "value": "heel"},
    {"function_type": "exclusion_filter", "key": "observation_location", "value": "toe"}
  ]
}
```

**D024 Incontinence (percentage-based):**
```json
{
  "rule_type": "aggregation",
  "source_type": "ACTIVE_RESIDENT_OBSERVATIONS",
  "threshold": 50,
  "functions": [
    {"function_type": "inclusion_filter", "key": "chart_name", "value": "Bowel Chart"},
    {"function_type": "aggregation", "key": "observation_value", "value": "value count of Incontinent"}
  ]
}
```

### B.6 Outstanding Requirements (Not Yet Implemented)

The following requirements from the DRI specification are **documented but not yet implemented** in this solution:

| # | Requirement | Description | Status |
|---|-------------|-------------|--------|
| 1 | **Audit Tables** | Rule applications, scoring decisions, and explainability metadata tracking | 🔴 Pending |
| 2 | **Daily Delta Processing** | Incremental updates with temporal logic (flag expiry, re-trigger) | 🔴 Pending |
| 3 | **Version Controlled Config** | Client-specific rules updates without code changes | 🟡 Partial (prompt versions exist) |
| 4 | **Data Lineage Tracking** | Full traceability from source to output | 🔴 Pending |
| 5 | **Orchestration Framework** | Scheduled tasks for daily processing | 🔴 Pending |

---

## Appendix C: Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-27 | Initial draft |
| 1.1 | 2025-01-27 | Added ACTIVE_RESIDENT_OBSERVATION_GROUP, client config, temporal logic |
| 1.2 | 2025-01-27 | Enhanced traceability, separation of detection vs calculation |
| 1.3 | 2025-01-27 | Aggregate approval workflow, on-demand testing |
| 1.4 | 2026-01-30 | Implementation sync: Updated UI structure to match actual build (7 pages), added Claude vs Regex comparison page, added Batch Testing page, marked all features as IMPLEMENTED, added implementation status table |
| 1.5 | 2026-02-03 | AI Observability integration with TruLens |
| 1.6 | 2026-02-05 | UI improvements: Run Quality Evaluation button, resident dropdown shows facility, auto-select client config, expanded test data to 50 residents |
| 1.7 | 2026-02-17 | Architecture simplification - removed TruLens, added approval-based metrics |
| 1.8 | 2026-02-18 | Enhanced rejection workflow: Added DRI_INDICATOR_REJECTIONS table for granular indicator-level rejection feedback. Review Queue now supports two-phase rejection: select indicators via checkboxes, provide reason for each. STATUS includes PARTIAL_REJECT. Analysis Results shows full batch ID (not truncated). |
| 1.9 | 2026-02-22 | **Business Rules Integration**: Added Appendix B with complete 33-deficit specification from DRI requirements. Documented PERSISTENT vs FLUCTUATING types, rule types (keyword_search, specific_value, aggregation), inclusion/exclusion filters, temporal logic. Added Outstanding Requirements section tracking 5 pending items. |

---

*Document Version: 1.9*  
*Created: 2025-01-27*  
*Updated: 2026-02-22 (Business Rules Integration - 33 deficits documented)*  
*Status: Approved*
