"""
Connection Helper Module for Healthcare AI Demo
==============================================

This module provides a unified connection interface that works in both:
1. Local Streamlit development environment
2. Streamlit in Snowflake hosted environment

Adapted from the superannuation demo pattern for healthcare use cases.
"""

import snowflake.connector
try:
    import tomllib as tomli  # Python 3.11+
except Exception:
    import tomli  # Fallback for environments without tomllib
import streamlit as st
from snowflake.snowpark.context import get_active_session
import pandas as pd
import os
import json
from typing import Dict, Any, Optional, Union

@st.cache_resource(show_spinner="Connecting to Snowflake...")
def get_snowflake_connection():
    """
    Connection handler that works in both local and Snowflake environments
    Returns either a Snowpark session or a regular connection
    Uses Streamlit caching to maintain connection across sessions
    """
    # First try to get active session (for Streamlit in Snowflake)
    try:
        session = get_active_session()
        if session:
            # Basic health check; don't fail session on context issues
            try:
                session.sql("SELECT 1").collect()
            except Exception:
                pass
            return session
    except Exception:
        # If get_active_session fails, continue to local connection
        pass
            
    # Try local connection using config file
    try:
        config_path = os.path.expanduser('~/.snowflake/config.toml')
        with open(config_path, 'rb') as f:
            config = tomli.load(f)
        
        # Get the default connection name
        default_conn = config.get('default_connection_name')
        if not default_conn:
            st.error("No default connection specified in config.toml")
            return None
            
        # Get the connection configuration for the default connection
        conn_params = config.get('connections', {}).get(default_conn)
        if not conn_params:
            st.error(f"Connection '{default_conn}' not found in config.toml")
            return None
        
        # Create a connection with error handling
        conn = snowflake.connector.connect(**conn_params)
        
        # Set up the healthcare database context
        cursor = conn.cursor()
        cursor.execute("USE DATABASE HEALTHCARE_DEMO")
        cursor.execute("USE SCHEMA MEDICAL_NOTES")
        
        # Test the connection
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        
        return conn
        
    except FileNotFoundError:
        # Don't surface as an error in UI; this is expected in Snowflake deployments
        st.info("Local Snowflake config not found at ~/.snowflake/config.toml. In Streamlit in Snowflake deployments this is not required.")
        return None
    except Exception as e:
        st.error(f"Failed to connect to Snowflake using local config: {str(e)}")
        return None

def get_fresh_connection():
    """Get a fresh connection without caching for retry scenarios"""
    try:
        # Clear the cached connection first
        get_snowflake_connection.clear()
        return get_snowflake_connection()
    except Exception as e:
        st.error(f"Failed to get fresh connection: {str(e)}")
        return None

def execute_query(query: str, conn=None) -> pd.DataFrame:
    """
    Execute a query using either Snowpark session or regular connection
    Returns pandas DataFrame with automatic retry on connection errors
    """
    if conn is None:
        conn = get_snowflake_connection()
    
    if conn is None:
        raise Exception("No valid Snowflake connection available")
    
    try:
        if hasattr(conn, 'sql'):  # Snowpark session
            result = conn.sql(query).to_pandas()
        else:  # Regular connection
            result = pd.read_sql(query, conn)
        return result
    except Exception as e:
        # Auto-reconnect on closed/expired connection and retry once
        msg = str(e)
        if '250002' in msg or 'Connection is closed' in msg or '08003' in msg:
            try:
                st.info("Reconnecting to Snowflake and retrying the query...")
                fresh_conn = get_fresh_connection()
                if fresh_conn is None:
                    raise e
                if hasattr(fresh_conn, 'sql'):
                    return fresh_conn.sql(query).to_pandas()
                else:
                    return pd.read_sql(query, fresh_conn)
            except Exception as retry_error:
                st.error(f"Query execution failed after reconnect: {str(retry_error)}")
                raise retry_error
        else:
            st.error(f"Query execution failed: {msg}")
            raise

# Removed safe_execute_query function - all queries now use execute_query directly

def test_cortex_ai_functions(conn=None) -> Dict[str, bool]:
    """
    Test Cortex AI function availability
    """
    if conn is None:
        conn = get_snowflake_connection()
    
    if conn is None:
        return {}
    
    # Test with a simple query to verify Cortex AI access
    try:
        test_query = "SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large', 'Hello') as test"
        execute_query(test_query, conn)
        return {"cortex_ai": True}
    except Exception:
        return {"cortex_ai": False}

def get_demo_data_status(_conn=None) -> Dict[str, Any]:
    """
    Check if demo data is loaded and available
    Returns dict with data availability status
    """
    if _conn is None:
        _conn = get_snowflake_connection()
    
    if _conn is None:
        return {"error": "No connection available"}
    
    data_status = {
        "pmc_patients": {"available": False, "count": 0},
        "patient_analysis": {"available": False, "count": 0},
        "demo_scenarios": {"available": False, "count": 0},
        "realtime_logs": {"available": False, "count": 0}
    }
    
    tables_to_check = [
        ("pmc_patients", "PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS"),
        ("patient_analysis", "HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS"),
        ("demo_scenarios", "HEALTHCARE_DEMO.MEDICAL_NOTES.DEMO_SCENARIOS"),
        ("realtime_logs", "HEALTHCARE_DEMO.MEDICAL_NOTES.REALTIME_ANALYSIS_LOG")
    ]
    
    for key, table_name in tables_to_check:
        try:
            query = f"SELECT COUNT(*) as row_count FROM {table_name} LIMIT 1"
            result = execute_query(query, _conn)
            if not result.empty:
                count = result.iloc[0, 0]
                data_status[key] = {"available": count > 0, "count": count}
        except:
            data_status[key] = {"available": False, "count": 0, "error": "Table not found"}
    
    return data_status

@st.cache_data(ttl=600)
def get_connection_info() -> Dict[str, Any]:
    """
    Get connection information for display purposes
    Cached for 10 minutes to avoid repeated checks
    """
    try:
        conn = get_snowflake_connection()
        if conn is None:
            return {"status": "disconnected", "type": "none"}
        
        if hasattr(conn, 'sql'):
            # Snowpark session
            account_info = conn.sql("SELECT CURRENT_ACCOUNT() as account").collect()[0]
            db_info = conn.sql("SELECT CURRENT_DATABASE() as database, CURRENT_SCHEMA() as schema").collect()[0]
            return {
                "status": "connected",
                "type": "snowpark", 
                "account": account_info['ACCOUNT'],
                "database": db_info['DATABASE'] or "HEALTHCARE_DEMO",
                "schema": db_info['SCHEMA'] or "MEDICAL_NOTES"
            }
        else:
            # Regular connection
            cursor = conn.cursor()
            cursor.execute("SELECT CURRENT_ACCOUNT(), CURRENT_DATABASE(), CURRENT_SCHEMA()")
            account, database, schema = cursor.fetchone()
            cursor.close()
            return {
                "status": "connected",
                "type": "connector",
                "account": account,
                "database": database or "HEALTHCARE_DEMO", 
                "schema": schema or "MEDICAL_NOTES"
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def initialize_demo_environment() -> Dict[str, Any]:
    """
    Initialize and validate the healthcare demo environment
    Returns comprehensive status information
    """
    status = {
        "connection": get_connection_info(),
        "ai_functions": {"error": "Not tested"},
        "data_status": {"error": "Not tested"}
    }
    
    # Only test AI functions and data if we have a good connection
    if status["connection"]["status"] == "connected":
        try:
            conn = get_snowflake_connection()
            status["ai_functions"] = test_cortex_ai_functions(conn)
            status["data_status"] = get_demo_data_status(conn)
        except Exception as e:
            status["ai_functions"] = {"error": str(e)}
            status["data_status"] = {"error": str(e)}
    
    return status

def execute_cortex_complete(prompt: str, model: str = "claude-4-sonnet", conn=None) -> str:
    """
    Execute a Cortex AI completion request
    
    Args:
        prompt: The prompt to send to the model
        model: The model to use (default: claude-4-sonnet)
        conn: Optional connection object
    
    Returns:
        The model's response as a string
    """
    if conn is None:
        conn = get_snowflake_connection()
    
    query = f"""
    SELECT SNOWFLAKE.CORTEX.COMPLETE(
        '{model}',
        '{prompt.replace("'", "''")}'
    ) as response
    """
    
    result = execute_query(query, conn)
    if not result.empty:
        return result.iloc[0, 0]
    return ""

def get_sample_patients(limit: int = 10, conn=None) -> pd.DataFrame:
    """
    Get sample patients from PMC dataset for testing
    """
    query = f"""
    SELECT 
        PATIENT_ID,
        PATIENT_UID,
        PATIENT_TITLE,
        AGE,
        GENDER,
        SUBSTR(PATIENT_NOTES, 1, 200) || '...' as NOTES_PREVIEW
    FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    LIMIT {limit}
    """
    
    return execute_query(query, conn)

def log_realtime_analysis(
    session_id: str,
    user_name: str,
    patient_id: int,
    original_text: str,
    modified_text: str,
    analysis_type: str,
    ai_model: str,
    processing_time_ms: int,
    results: Dict[str, Any],
    success: bool,
    conn=None
) -> None:
    """
    Log a real-time analysis request for audit and performance tracking
    Uses parameterized queries to avoid SQL injection and escaping issues
    """
    if conn is None:
        conn = get_snowflake_connection()
    
    try:
        # Truncate long text fields to prevent database errors
        original_text_truncated = original_text[:1000] if original_text else ""
        modified_text_truncated = modified_text[:1000] if modified_text else ""
        
        # Convert results to JSON string with proper handling
        results_json = json.dumps(results, ensure_ascii=True, separators=(',', ':'))
        
        # Use parameterized query approach based on connection type
        if hasattr(conn, 'sql'):
            # Snowpark session - use SQL with binding
            query = """
            INSERT INTO HEALTHCARE_DEMO.MEDICAL_NOTES.REALTIME_ANALYSIS_LOG
            (SESSION_ID, USER_NAME, PATIENT_ID, ORIGINAL_TEXT, MODIFIED_TEXT, 
             ANALYSIS_TYPE, AI_MODEL_USED, PROCESSING_TIME_MS, RESULTS, SUCCESS_FLAG)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, PARSE_JSON(?), ?)
            """
            conn.sql(query, params=[
                session_id, user_name, patient_id, original_text_truncated, 
                modified_text_truncated, analysis_type, ai_model, 
                processing_time_ms, results_json, success
            ]).collect()
        else:
            # Regular connection - use cursor with parameters
            cursor = conn.cursor()
            query = """
            INSERT INTO HEALTHCARE_DEMO.MEDICAL_NOTES.REALTIME_ANALYSIS_LOG
            (SESSION_ID, USER_NAME, PATIENT_ID, ORIGINAL_TEXT, MODIFIED_TEXT, 
             ANALYSIS_TYPE, AI_MODEL_USED, PROCESSING_TIME_MS, RESULTS, SUCCESS_FLAG)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s), %s)
            """
            cursor.execute(query, (
                session_id, user_name, patient_id, original_text_truncated,
                modified_text_truncated, analysis_type, ai_model,
                processing_time_ms, results_json, success
            ))
            cursor.close()
            
    except Exception as e:
        # Silently handle logging failures to not disrupt user experience
        print(f"Failed to log analysis: {str(e)}")
        # For debugging, you can temporarily enable this:
        # st.warning(f"Logging failed (analysis continued): {str(e)}")

# Medical-specific helper functions

def format_sbar_summary(sbar_data: Dict[str, str]) -> str:
    """
    Format SBAR summary data for display
    """
    return f"""
**Situation:** {sbar_data.get('situation', 'N/A')}

**Background:** {sbar_data.get('background', 'N/A')}

**Assessment:** {sbar_data.get('assessment', 'N/A')}

**Recommendation:** {sbar_data.get('recommendation', 'N/A')}
    """

def parse_json_safely(json_str: str, default=None) -> Any:
    """
    Safely parse JSON string with fallback
    """
    if not json_str:
        return default if default is not None else {}
    
    try:
        return json.loads(json_str)
    except:
        # Try to fix common issues
        try:
            # Replace single quotes with double quotes
            fixed_str = json_str.replace("'", '"')
            return json.loads(fixed_str)
        except:
            return default if default is not None else {}

def query_cortex_search_service(search_term: str, service_name: str = 'patient_search_service', limit: int = 20, conn=None, filter_param: Optional[dict] = None) -> pd.DataFrame:
    """
    Query the Snowflake Cortex Search service using the Python API (Root -> cortex_search_services).
    
    Automatically resumes the service if it's suspended.

    Returns columns compatible with UI expectations:
      - PATIENT_ID, PATIENT_UID, PATIENT_TITLE, AGE, GENDER, RELEVANCE_SCORE (0..1)
    """
    if conn is None:
        conn = get_snowflake_connection()

    if conn is None:
        raise Exception("No valid Snowflake connection available")

    def _attempt_resume_service(session_or_conn, db: str, schema: str, svc_name: str):
        """Helper to resume a suspended Cortex Search service"""
        try:
            resume_sql = f"ALTER CORTEX SEARCH SERVICE {db}.{schema}.{svc_name} RESUME"
            if hasattr(session_or_conn, 'sql'):
                session_or_conn.sql(resume_sql).collect()
            else:
                cursor = session_or_conn.cursor()
                cursor.execute(f"USE DATABASE {db}")
                cursor.execute(f"USE SCHEMA {schema}")
                cursor.execute(f"ALTER CORTEX SEARCH SERVICE {svc_name} RESUME")
                cursor.close()
            import time
            time.sleep(3)  # Wait for service to initialize
            return True
        except Exception as resume_err:
            if "already running" not in str(resume_err).lower():
                print(f"Warning: Could not resume service: {resume_err}")
            return False

    try:
        # Prefer Python API if Snowpark session is available (SiS)
        if hasattr(conn, 'sql'):
            # Import inside function to avoid import issues in local envs
            from snowflake.core import Root  # type: ignore
            import json as _json

            session = conn  # Snowpark session
            root = Root(session)

            # Resolve service by fully qualified path using current context
            db_df = session.sql("SELECT CURRENT_DATABASE() AS DB, CURRENT_SCHEMA() AS SCH").to_pandas()
            current_db = (db_df.loc[0, 'DB'] or 'HEALTHCARE_DEMO') if not db_df.empty else 'HEALTHCARE_DEMO'
            current_sch = (db_df.loc[0, 'SCH'] or 'MEDICAL_NOTES') if not db_df.empty else 'MEDICAL_NOTES'

            svc = (root
                .databases[current_db]
                .schemas[current_sch]
                .cortex_search_services[service_name]
            )

            kwargs = {
                "query": str(search_term),
                "columns": ["PATIENT_ID", "PATIENT_UID", "PATIENT_TITLE", "AGE", "GENDER"],
                "limit": int(limit),
            }
            if filter_param:
                kwargs["filter"] = filter_param
            
            # Attempt search, resume if suspended
            try:
                resp = svc.search(**kwargs)
            except Exception as search_err:
                # Check if service is suspended (error code 399131)
                if "399131" in str(search_err) or "suspended" in str(search_err).lower():
                    # Attempt to resume the service
                    _attempt_resume_service(session, current_db, current_sch, service_name)
                    # Retry the search
                    resp = svc.search(**kwargs)
                else:
                    raise

            # Convert response to JSON then pandas
            raw_json = resp.to_json()  # JSON string
            parsed = _json.loads(raw_json) if isinstance(raw_json, str) else raw_json
            # Store raw for debug UI
            try:
                st.session_state['last_cortex_search_raw'] = parsed
            except Exception:
                pass
            results = parsed.get('results', []) if isinstance(parsed, dict) else []

            # Normalize to DataFrame and map field names
            records = []
            for item in results:
                # Defensive casts
                patient_id = int(item.get('PATIENT_ID')) if item.get('PATIENT_ID') is not None else None
                age_years = item.get('AGE')
                try:
                    age_val = float(age_years) if age_years is not None else None
                except Exception:
                    age_val = None
                # Score (try multiple common keys)
                score_val = (
                    item.get('score')
                    or item.get('SCORE')
                    or item.get('relevance')
                    or item.get('RELEVANCE')
                )
                try:
                    rel_score = float(score_val) if score_val is not None else None
                except Exception:
                    rel_score = None

                records.append({
                    'PATIENT_ID': patient_id,
                    'PATIENT_UID': item.get('PATIENT_UID'),
                    'PATIENT_TITLE': item.get('PATIENT_TITLE'),
                    'AGE': age_val,
                    'GENDER': item.get('GENDER'),
                    'RELEVANCE_SCORE': rel_score,
                })

            return pd.DataFrame.from_records(records)

        # Local fallback: SQL SEARCH_PREVIEW (no score in response)
        import json as _json
        payload = {
            "query": str(search_term),
            "columns": [
                "PATIENT_ID",
                "PATIENT_UID",
                "PATIENT_TITLE",
                "AGE",
                "GENDER"
            ],
            "limit": int(limit)
        }
        if filter_param:
            payload["filter"] = filter_param
        payload_str = _json.dumps(payload).replace("'", "''")

        # Capture raw JSON for debug
        raw_sql = f"""
        SELECT PARSE_JSON(
            SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                '{service_name}',
                '{payload_str}'
            )
        ) AS J
        """
        try:
            raw_df = execute_query(raw_sql, conn)
            if not raw_df.empty:
                st.session_state['last_cortex_search_raw'] = raw_df.iloc[0, 0]
        except Exception:
            pass

        sql = f"""
        WITH raw AS (
            SELECT PARSE_JSON(
                SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                    '{service_name}',
                    '{payload_str}'
                )
            ) AS j
        )
        SELECT 
            r.value:"PATIENT_ID"::NUMBER      AS PATIENT_ID,
            r.value:"PATIENT_UID"::STRING     AS PATIENT_UID,
            r.value:"PATIENT_TITLE"::STRING   AS PATIENT_TITLE,
            COALESCE(
                TRY_TO_DOUBLE(TO_VARCHAR(r.value:"AGE"[0][0])),
                TRY_TO_DOUBLE(TO_VARCHAR(r.value:"AGE"[0])),
                TRY_TO_DOUBLE(TO_VARCHAR(r.value:"AGE"))
            )                                   AS AGE,
            r.value:"GENDER"::STRING          AS GENDER,
            NULL::FLOAT                        AS RELEVANCE_SCORE
        FROM raw, LATERAL FLATTEN(input => raw.j:results) r
        LIMIT {int(limit)}
        """
        
        # Try the query, resume if suspended
        try:
            return execute_query(sql, conn)
        except Exception as sql_err:
            # Check if service is suspended (error code 399131)
            if "399131" in str(sql_err) or "suspended" in str(sql_err).lower():
                # Get current database and schema
                cursor = conn.cursor()
                cursor.execute("SELECT CURRENT_DATABASE() AS DB, CURRENT_SCHEMA() AS SCH")
                result = cursor.fetchone()
                current_db = result[0] if result and result[0] else 'HEALTHCARE_DEMO'
                current_sch = result[1] if result and result[1] else 'MEDICAL_NOTES'
                cursor.close()
                
                # Attempt to resume the service
                _attempt_resume_service(conn, current_db, current_sch, service_name)
                
                # Retry the query
                return execute_query(sql, conn)
            else:
                raise
                
    except Exception as e:
        # Bubble up so caller can show fallback or error message
        raise

# Comprehensive prompt from stored procedure for single patient processing
COMPREHENSIVE_ANALYSIS_PROMPT = """
Analyze these patient notes comprehensively across all healthcare AI use cases:

{patient_notes}

Create a single comprehensive JSON response with ALL the following sections in this exact order:

{{
    "clinical_summary": {{
        "situation": "Current clinical situation and reason for encounter",
        "background": "Relevant medical history, medications, allergies",
        "assessment": "Clinical assessment including vital signs and key findings",
        "recommendation": "Treatment plan and follow-up recommendations",
        "clinical_summary": "One paragraph narrative summary",
        "chief_complaint": "Main presenting complaint"
    }},
    
    "differential_diagnosis": {{
        "chief_complaint": "Main presenting complaint",
        "clinical_findings": {{
            "key_findings": [
                {{"finding": "specific finding", "category": "symptom/sign/lab", "severity": "mild/moderate/severe"}}
            ]
        }},
        "diagnostic_assessment": {{
            "differential_diagnoses": [
                {{
                    "diagnosis": "diagnosis name",
                    "confidence": "high/medium/low",
                    "evidence": [{{"evidence_text": "Quote specific sentences from patient notes that support this diagnosis"}}],
                    "discriminating_features": "What distinguishes this from other diagnoses",
                    "icd10_code": "ICD-10 code if known"
                }}
            ]
        }},
        "diagnostic_workup": {{
            "recommended_tests": [
                {{"test": "test name", "rationale": "why this test is needed", "priority": "high/medium/low"}}
            ]
        }},
        "diagnostic_reasoning": "Brief explanation of diagnostic thinking with specific references to patient notes",
        "diagnostic_confidence": "high/medium/low - overall confidence in diagnostic assessment"
    }},
    
    "medication_safety": {{
        "current_medications": {{
            "extracted_medications": [
                {{"medication": "name", "dosage": "if mentioned", "frequency": "if mentioned", "indication": "reason for use"}}
            ]
        }},
        "safety_concerns": {{
            "drug_interactions": [
                {{"drug1": "drug1", "drug2": "drug2", "interaction_type": "major/moderate/minor", "clinical_effect": "description", "confidence": "high/medium/low"}}
            ],
            "contraindications": [
                {{"medication": "name", "contraindication": "condition/allergy", "severity": "absolute/relative", "evidence": "Quote from notes supporting this contraindication"}}
            ],
            "safety_alerts": [
                {{"alert": "safety alert description", "severity": "high/medium/low", "medication": "related medication if applicable"}}
            ]
        }},
        "risk_assessment": {{
            "polypharmacy_risk": "low/medium/high",
            "polypharmacy_confidence": "high/medium/low - confidence in polypharmacy assessment"
        }}
    }},
    
    "treatment_analysis": {{
        "active_treatments": {{
            "current_treatments": [
                {{"treatment": "name", "category": "medication/procedure/therapy", "effectiveness": "noted outcome if mentioned", "evidence": "Quote from notes about treatment response"}}
            ],
            "treatment_effectiveness": "Overall assessment of treatment response with specific evidence from notes"
        }},
        "clinical_recommendations": {{
            "evidence_based_recommendations": [
                {{"recommendation": "specific recommendation", "rationale": "clinical reasoning with quotes from notes", "evidence_level": "high/moderate/low", "confidence": "high/medium/low"}}
            ],
            "contraindications": [
                {{"treatment": "treatment to avoid", "reason": "clinical reason", "severity": "absolute/relative"}}
            ]
        }}
    }},
    
    "pattern_recognition": {{
        "clinical_patterns": {{
            "presentation_type": "typical/atypical/rare",
            "symptom_pattern": "Description of the symptom constellation",
            "rare_disease_indicators": [
                {{"indicator": "specific finding", "associated_conditions": ["condition1", "condition2"], "significance": "explanation"}}
            ]
        }},
        "anomaly_detection": {{
            "anomaly_score": 0.0,
            "anomaly_confidence": "high/medium/low - confidence in anomaly assessment",
            "unusual_features": [
                {{"feature": "unusual aspect", "rarity": "common/uncommon/rare", "clinical_significance": "why this matters"}}
            ]
        }},
        "specialist_referral": {{
            "recommended_specialist": "Suggested specialist consultation if needed",
            "referral_urgency": "routine/urgent/emergent",
            "referral_rationale": "Why specialist input is needed"
        }}
    }},
    
    "quality_metrics": {{
        "care_quality": {{
            "quality_indicators": [
                {{"indicator": "specific quality measure", "met": true/false, "details": "explanation", "confidence": "high/medium/low"}}
            ],
            "guideline_adherence": [
                {{"guideline": "relevant clinical guideline", "adherent": true/false, "gaps": ["any gaps identified"], "confidence": "high/medium/low"}}
            ]
        }},
        "safety_assessment": {{
            "safety_events": ["any safety issues or near misses identified in notes"],
            "risk_factors": [
                {{"risk_factor": "identified risk", "severity": "high/medium/low", "mitigation": "suggested mitigation"}}
            ]
        }},
        "care_coordination": {{
            "coordination_quality": "Assessment of care coordination quality",
            "improvement_opportunities": ["specific improvement suggestions"]
        }}
    }},
    
    "cost_analysis": {{
        "resource_utilization": {{
            "extracted_procedures": [
                {{"procedure": "procedure name", "category": "imaging/lab/surgery/other", "potential_cpt": "CPT code if identifiable", "cost_impact": "high/medium/low"}}
            ],
            "imaging_studies": ["list of imaging studies mentioned"],
            "laboratory_tests": ["list of lab tests mentioned"],
            "specialist_consults": ["specialties involved"]
        }},
        "cost_drivers": {{
            "high_cost_indicators": [
                {{"indicator": "ICU admission/complex surgery/etc", "impact": "high/medium/low", "details": "specific details"}}
            ],
            "complications": ["any complications that would increase cost"],
            "length_of_stay_indicators": "inpatient/outpatient/prolonged - evidence from notes"
        }},
        "financial_impact": {{
            "estimated_cost_category": "low/medium/high/very_high - based on procedures and complexity",
            "cost_justification": "Explanation of cost category assignment",
            "cost_optimization_opportunities": ["suggestions for cost reduction if applicable"]
        }}
    }},
    
    "educational_value": {{
        "teaching_content": {{
            "teaching_points": [
                {{"concept": "key clinical concept", "explanation": "why it's important", "pearls": "clinical pearl"}}
            ],
            "clinical_pearls": "Key takeaway message for learners",
            "complexity_level": "medical student/resident/fellow - appropriate learning level"
        }},
        "case_discussion": {{
            "differential_teaching": "How to approach the differential diagnosis - educational perspective",
            "evidence_discussion": "Key evidence-based medicine points for learning",
            "learning_objectives": ["what learners should take away from this case"]
        }},
        "assessment_tools": {{
            "quiz_questions": [
                {{
                    "question": "Clinical question based on the case",
                    "options": ["A) option 1", "B) option 2", "C) option 3", "D) option 4"],
                    "correct_answer": "Letter of correct option",
                    "explanation": "Why this answer is correct with reference to case details"
                }}
            ]
        }}
    }}
}}

Return ONLY the JSON response. Ensure all fields are populated with clinically relevant information extracted from or inferred from the patient notes. Use "Not mentioned" or "Unable to determine from notes" only when information is truly absent.
"""

def parse_comprehensive_response(response: str) -> dict:
    """Parse the comprehensive AI response into structured data (from stored procedure)"""
    try:
        import re
        # Try to extract fenced JSON first
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response, re.IGNORECASE)
        if fence_match:
            fenced = fence_match.group(1).strip()
            try:
                return json.loads(fenced)
            except Exception:
                pass

        # Extract the largest JSON object in the response
        json_match = re.search(r'\{[\s\S]*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            try:
                return json.loads(json_str)
            except Exception:
                # Safer fallback to tolerate minor formatting issues
                from connection_helper import parse_json_safely as _safe
                parsed = _safe(json_str, {})
                if isinstance(parsed, dict) and parsed:
                    return parsed
        return {}
    except Exception as e:
        print(f"Error parsing AI response: {e}")
        return {}

def process_single_patient_comprehensive(patient_notes: str, model: str = "openai-gpt-5", conn=None) -> dict:
    """
    Process a single patient using the comprehensive prompt from the stored procedure
    
    Args:
        patient_notes: The patient notes to analyze
        model: The AI model to use (default: gpt-4o)
        conn: Optional connection object
    
    Returns:
        Parsed comprehensive analysis results as a dictionary
    """
    if conn is None:
        conn = get_snowflake_connection()
    
    try:
        # Format prompt with patient notes (limit to 4000 chars to prevent token limits)
        formatted_prompt = COMPREHENSIVE_ANALYSIS_PROMPT.format(
            patient_notes=patient_notes[:4000]
        )
        
        # Execute AI analysis
        raw_response = execute_cortex_complete(formatted_prompt, model, conn)
        
        # Parse consolidated response
        consolidated_results = parse_comprehensive_response(raw_response or "")
        alt_response = ""
        
        # Fallback: try an alternate model once if parsing failed or empty
        if not consolidated_results:
            try:
                alt_model = "openai-gpt-5" if model != "openai-gpt-5" else "claude-4-sonnet"
                alt_response = execute_cortex_complete(formatted_prompt, alt_model, conn)
                consolidated_results = parse_comprehensive_response(alt_response or "")
            except Exception:
                pass
        
        # Final safety: if still empty but we have raw text from either attempt, surface minimal structure
        if not consolidated_results:
            fallback_text = (raw_response or alt_response or "").strip()
            if fallback_text:
                consolidated_results = {
                    "clinical_summary": {
                        "clinical_summary": fallback_text[:1500]
                    }
                }
        
        return consolidated_results
        
    except Exception as e:
        print(f"Error processing patient with comprehensive prompt: {e}")
        return {}