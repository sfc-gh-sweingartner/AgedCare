"""
Page 2: Clinical Decision Support
==================================

Primary physician interface for AI-powered clinical insights.
Shows patient summaries, differential diagnoses, and treatment recommendations.
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from connection_helper import (
    get_snowflake_connection,
    execute_query,
    format_sbar_summary,
    parse_json_safely,
    execute_cortex_complete,
    query_cortex_search_service,
    process_single_patient_comprehensive
)

# Now using comprehensive prompt from stored procedure via connection_helper.py
# This provides much more detailed analysis than the previous embedded prompt

def parse_consolidated_response_batch(response: str) -> dict:
    """Parse the consolidated AI response into structured data"""
    try:
        import re, json as _json
        m = re.search(r"\{.*\}", response, re.DOTALL)
        return _json.loads(m.group()) if m else {}
    except Exception:
        return {}

def save_patient_results_batch(patient_id: int, results: dict, conn):
    """No-op function for real-time context - results are displayed inline"""
    return None

# Local copy of dynamic renderer to avoid import issues with emoji filenames
def display_consolidated_results(results: dict):
    if not results or not isinstance(results, dict):
        st.info("No results to display.")
        return

    def beautify(label: str) -> str:
        try:
            return str(label).replace('_', ' ').title()
        except Exception:
            return str(label)

    def is_scalar(x):
        return isinstance(x, (str, int, float, bool)) or x is None

    def render_clinical_section(title: str, content: str):
        if content is None:
            return
        st.markdown(f"""
        <div style="
            background-color: #e8f4fd;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 0.5rem;
            border-left: 3px solid #0066CC;
        ">
            <strong>{title}:</strong><br>
            {content}
        </div>
        """, unsafe_allow_html=True)

    def render_confidence_badge(confidence: str):
        if not confidence:
            return ""
        c = confidence.lower()
        color = "#6c757d"
        if "high" in c:
            color = "#28a745"
        elif "medium" in c:
            color = "#ffc107"
        elif "low" in c:
            color = "#dc3545"
        return f'<span style="color: {color}; font-weight: bold;">({confidence})</span>'

    def render_value(value, level: int = 0, parent_key: str = ""):
        if isinstance(value, dict):
            if not value:
                title = beautify(parent_key) if parent_key else "Content"
                render_clinical_section(title, "None")
                return
            for k, v in value.items():
                title = beautify(k)
                if is_scalar(v):
                    # Apply blue styling to all scalar values regardless of level
                    content = str(v) if v is not None else ""
                    if "confidence" in k.lower() and content:
                        content += f" {render_confidence_badge(content)}"
                    render_clinical_section(title, content)
                else:
                    # Render non-scalar values with blue section headers
                    st.markdown(f"### {title}")
                    render_value(v, level + 1, k)
        elif isinstance(value, list):
            if not value:
                title = beautify(parent_key) if parent_key else "Content"
                render_clinical_section(title, "None")
                return
            contains_complex = any(isinstance(it, (dict, list)) for it in value)
            if contains_complex:
                for idx, item in enumerate(value, 1):
                    if isinstance(item, dict):
                        name = None
                        for key, val in item.items():
                            if isinstance(val, str) and 0 < len(val) < 200:
                                name = val
                                break
                        if not name:
                            name = f"Item {idx}"
                        details = []
                        confidence = item.get('confidence', '')
                        evidence = item.get('evidence', [])
                        if 'drug1' in item and 'drug2' in item:
                            name = f"Interaction: {item['drug1']} + {item['drug2']}"
                        name_key = None
                        for key, val in item.items():
                            if isinstance(val, str) and val == name:
                                name_key = key
                                break
                        for key, val in item.items():
                            if key not in ['confidence', 'evidence', 'drug1', 'drug2'] and key != name_key and val:
                                if isinstance(val, list):
                                    if len(val) <= 3:
                                        value_str = ', '.join(str(v) for v in val)
                                        details.append(f"{key.replace('_', ' ').title()}: {value_str}")
                                elif isinstance(val, bool):
                                    value_str = "✓ Yes" if val else "✗ No"
                                    details.append(f"{key.replace('_', ' ').title()}: {value_str}")
                                elif not isinstance(val, dict):
                                    details.append(f"{key.replace('_', ' ').title()}: {val}")
                        badge = render_confidence_badge(confidence)
                        # Handle evidence that might be a list of dictionaries or strings
                        if isinstance(evidence, list):
                            evidence_strings = []
                            for e in evidence:
                                if isinstance(e, dict) and 'evidence_text' in e:
                                    evidence_strings.append(e['evidence_text'])
                                elif isinstance(e, str):
                                    evidence_strings.append(e)
                                else:
                                    evidence_strings.append(str(e))
                            evidence_text = '; '.join(evidence_strings)
                        else:
                            evidence_text = str(evidence)
                        details_text = "<br>" + "<br>".join(details) if details else ""
                        evidence_section = f"<br><strong>Evidence:</strong> {evidence_text}" if evidence_text else ""
                        st.markdown(f"""
                        <div style="
                            background-color: #e8f4fd;
                            padding: 1rem;
                            border-radius: 0.5rem;
                            margin-bottom: 0.5rem;
                            border-left: 3px solid #0066CC;
                        ">
                            <strong>{idx}. {name}</strong> {badge}{details_text}{evidence_section}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"**Item {idx}**")
                        render_value(item, level + 1, parent_key)
            else:
                for idx, item in enumerate(value, 1):
                    display_text = item if item is not None else ""
                    st.markdown(f"""
                    <div style="
                        background-color: #e8f4fd;
                        padding: 1rem;
                        border-radius: 0.5rem;
                        margin-bottom: 0.5rem;
                        border-left: 3px solid #0066CC;
                    ">
                        <strong>Item {idx}</strong><br>{display_text}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.write(value if value is not None else "")

    keys = list(results.keys())
    if not keys:
        st.write("No content")
        return
    tabs = st.tabs([beautify(k) for k in keys])
    for tab, key in zip(tabs, keys):
        with tab:
            if key == 'evidence_literature':
                # Reuse existing evidence renderer for clinical page
                display_evidence_literature_clinical(results.get(key, {}), patient=None, conn=None) if False else render_value(results.get(key, {}), 0, key)
            else:
                render_value(results.get(key, {}), level=0, parent_key=key)

# Page configuration
st.set_page_config(
    page_title="Clinical Decision Support - Healthcare AI Demo",
    page_icon="🩺",
    layout="wide"
)

# Custom CSS for clinical interface
st.markdown("""
<style>
.clinical-card {
    background-color: white;
    padding: 1.5rem;
    border-radius: 0.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 1rem;
}

.patient-header {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #0066CC;
    margin-bottom: 1rem;
}

.diagnosis-item {
    background-color: #e8f4fd;
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 0.5rem;
    border-left: 3px solid #0066CC;
}

.treatment-recommendation {
    background-color: #d4edda;
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 0.5rem;
    border-left: 3px solid #28a745;
}

.evidence-link {
    color: #0066CC;
    text-decoration: none;
    font-size: 0.875rem;
}

.evidence-link:hover {
    text-decoration: underline;
}

.confidence-high { color: #28a745; font-weight: bold; }
.confidence-medium { color: #ffc107; font-weight: bold; }
.confidence-low { color: #dc3545; font-weight: bold; }

.sbar-section {
    margin-bottom: 1rem;
    padding: 0.75rem;
    background-color: #f8f9fa;
    border-radius: 0.25rem;
}

.similar-patient {
    background-color: #fff3cd;
    padding: 0.75rem;
    border-radius: 0.25rem;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def search_patients_cortex(search_term, _conn, processed_only: bool = False):
    """Search for patients using Cortex Search service for fast semantic search"""
    try:
        # Use the Cortex Search service helper function
        filter_param = None
        if processed_only:
            # Apply processed filter at the service layer using a range filter on PATIENT_ID
            # Use MAX(PATIENT_ID) from PATIENT_ANALYSIS as the upper bound
            try:
                max_df = execute_query(
                    "SELECT MAX(PATIENT_ID) AS MAX_ID FROM HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS",
                    _conn
                )
                if not max_df.empty and pd.notna(max_df.iloc[0]['MAX_ID']):
                    max_id = int(max_df.iloc[0]['MAX_ID'])
                    filter_param = {"@lte": {"PATIENT_ID": max_id}}
            except Exception:
                filter_param = None

        search_results = query_cortex_search_service(
            search_term,
            limit=20,
            conn=_conn,
            filter_param=filter_param
        )
        
        if not search_results.empty:
            # Add notes preview for display
            search_results_with_preview = search_results.copy()
            
            # Get patient notes for preview if not already included
            if 'PATIENT_NOTES' not in search_results.columns:
                patient_ids = ','.join(str(pid) for pid in search_results['PATIENT_ID'])
                notes_query = f"""
                SELECT 
                    PATIENT_ID,
                    SUBSTR(PATIENT_NOTES, 1, 200) || '...' as NOTES_PREVIEW
                FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
                WHERE PATIENT_ID IN ({patient_ids})
                """
                notes_data = execute_query(notes_query, _conn)
                search_results_with_preview = search_results.merge(notes_data, on='PATIENT_ID', how='left')
            else:
                search_results_with_preview['NOTES_PREVIEW'] = search_results['PATIENT_NOTES'].apply(
                    lambda x: str(x)[:200] + '...' if str(x) != 'nan' and x is not None else 'No notes available'
                )
            
            # Rename score column for consistency
            if 'score' in search_results_with_preview.columns:
                search_results_with_preview.rename(columns={'score': 'RELEVANCE_SCORE'}, inplace=True)
            
            # If filter couldn't be applied at the service layer, fallback to post-filter
            if processed_only and filter_param is None and not search_results_with_preview.empty:
                processed_df = execute_query("SELECT DISTINCT PATIENT_ID FROM HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS", _conn)
                if not processed_df.empty:
                    processed_ids = set(processed_df['PATIENT_ID'].astype(int))
                    search_results_with_preview = search_results_with_preview[search_results_with_preview['PATIENT_ID'].astype(int).isin(processed_ids)]
            return search_results_with_preview
            
    except Exception as e:
        error_msg = str(e)
        if "399131" in error_msg or "suspended" in error_msg.lower():
            st.info("🔄 Cortex Search service was suspended. Attempting to resume automatically...")
        else:
            st.warning(f"⚠️ Cortex Search service error: {error_msg[:200]}")
    
    # Fallback to basic text search if Cortex Search fails
    return search_patients_basic(search_term, _conn, processed_only)

@st.cache_data(ttl=300)
def search_patients_basic(search_term, _conn, processed_only: bool = False):
    """Basic text search for patients (fallback)"""
    query = f"""
    SELECT DISTINCT
        p.PATIENT_ID,
        p.PATIENT_UID,
        p.PATIENT_TITLE,
        p.AGE,
        p.GENDER,
        SUBSTR(p.PATIENT_NOTES, 1, 200) || '...' as NOTES_PREVIEW
    FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS p
    WHERE 1=1
        AND (
            CAST(p.PATIENT_ID AS STRING) LIKE '%{search_term}%'
            OR UPPER(p.PATIENT_TITLE) LIKE UPPER('%{search_term}%')
            OR UPPER(p.PATIENT_NOTES) LIKE UPPER('%{search_term}%')
        )
        {"AND EXISTS (SELECT 1 FROM HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS pa WHERE pa.PATIENT_ID = p.PATIENT_ID)" if processed_only else ''}
    ORDER BY 
        CASE 
            WHEN CAST(p.PATIENT_ID AS STRING) LIKE '%{search_term}%' THEN 1
            WHEN UPPER(p.PATIENT_TITLE) LIKE UPPER('%{search_term}%') THEN 2
            ELSE 3
        END
    LIMIT 20
    """
    return execute_query(query, _conn)

@st.cache_data(ttl=300)
def get_patient_details(patient_id, _conn):
    """Get full patient details including notes"""
    query = f"""
    SELECT 
        PATIENT_ID,
        PATIENT_UID,
        PATIENT_TITLE,
        AGE,
        GENDER,
        PATIENT_NOTES,
        SIMILAR_PATIENTS,
        RELEVANT_ARTICLES
    FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    WHERE PATIENT_ID = {patient_id}
    """
    return execute_query(query, _conn)

@st.cache_data(ttl=300)
def get_patient_analysis(patient_id, _conn):
    """Get pre-computed analysis if available"""
    query = f"""
    SELECT *
    FROM HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS
    WHERE PATIENT_ID = {patient_id}
    """
    return execute_query(query, _conn)

def generate_clinical_summary(patient_notes, conn):
    """Generate SBAR clinical summary using Cortex AI"""
    prompt = f"""
    You are an experienced physician creating a clinical summary.
    
    Create an SBAR (Situation, Background, Assessment, Recommendation) summary from these patient notes:
    
    {patient_notes[:2000]}  # Limit to first 2000 chars for prompt
    
    Format your response as a JSON object with exactly these keys:
    {{
        "situation": "Current clinical situation in 1-2 sentences",
        "background": "Relevant medical history and context",
        "assessment": "Current diagnosis and clinical status",
        "recommendation": "Next steps and treatment plan"
    }}
    
    Be concise but comprehensive. Focus on clinically relevant information.
    """
    
    try:
        response = execute_cortex_complete(prompt, "gpt-4o", conn)
        # Parse the response
        if response:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        return None
    except Exception as e:
        st.error(f"Error generating summary: {str(e)}")
        return None

def generate_differential_diagnosis(patient_notes, similar_patients, conn):
    """Generate differential diagnosis using AI"""
    prompt = f"""
    You are an expert diagnostician analyzing a patient case.
    
    Patient Notes:
    {patient_notes[:1500]}
    
    Based on these findings, provide 5 differential diagnoses.
    
    Format your response as a JSON array with exactly this structure:
    [
        {{
            "diagnosis": "Diagnosis name",
            "confidence": "HIGH/MEDIUM/LOW",
            "evidence": "Key supporting findings from the notes",
            "discriminating_features": "What distinguishes this from other diagnoses"
        }}
    ]
    
    Order by likelihood, with most likely first.
    """
    
    try:
        response = execute_cortex_complete(prompt, "gpt-4o", conn)
        if response:
            # Extract JSON array from response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        return []
    except Exception as e:
        st.error(f"Error generating diagnoses: {str(e)}")
        return []

def display_patient_header(patient_data):
    """Display patient header information"""
    if patient_data.empty:
        return
    
    patient = patient_data.iloc[0]
    
    st.markdown(f"""
    <div class="patient-header">
        <h3>Patient {patient['PATIENT_ID']}</h3>
        <strong>{patient['PATIENT_TITLE']}</strong><br>
        Age: {patient['AGE']} | Gender: {patient['GENDER']} | UID: {patient['PATIENT_UID']}
    </div>
    """, unsafe_allow_html=True)




def display_sbar_summary(sbar_data):
    """Display SBAR summary in clinical format"""
    if not sbar_data:
        st.info("No clinical summary available. Click 'Generate Clinical Summary' to create one.")
        return
    
    st.markdown("### 📋 Clinical Summary (SBAR Format)")
    
    sections = [
        ("Situation", sbar_data.get("situation", "Not available")),
        ("Background", sbar_data.get("background", "Not available")),
        ("Assessment", sbar_data.get("assessment", "Not available")),
        ("Recommendation", sbar_data.get("recommendation", "Not available"))
    ]
    
    for title, content in sections:
        st.markdown(f"""
        <div class="sbar-section">
            <strong>{title}:</strong><br>
            {content}
        </div>
        """, unsafe_allow_html=True)

def display_differential_diagnoses(diagnoses):
    """Display differential diagnoses"""
    if not diagnoses:
        st.info("No differential diagnoses available. Click 'Generate Diagnoses' to create them.")
        return
    
    st.markdown("### 🔍 Differential Diagnoses")
    
    for i, dx in enumerate(diagnoses, 1):
        confidence_class = f"confidence-{dx.get('confidence', 'MEDIUM').lower()}"
        
        st.markdown(f"""
        <div class="diagnosis-item">
            <strong>{i}. {dx.get('diagnosis', 'Unknown')}</strong> 
            <span class="{confidence_class}">({dx.get('confidence', 'MEDIUM')} confidence)</span><br>
            <strong>Evidence:</strong> {dx.get('evidence', 'No evidence provided')}<br>
            <strong>Discriminating Features:</strong> {dx.get('discriminating_features', 'None specified')}
        </div>
        """, unsafe_allow_html=True)


def save_sbar_summary_to_db(patient_id: int, sbar_data: dict, conn) -> bool:
    """Persist SBAR summary to PATIENT_ANALYSIS.SBAR_SUMMARY for the patient."""
    try:
        sbar_json = json.dumps(sbar_data)
        if hasattr(conn, 'sql'):
            conn.sql(f"""
                MERGE INTO HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS pa
                USING (SELECT {patient_id} AS PATIENT_ID) s
                ON pa.PATIENT_ID = s.PATIENT_ID
                WHEN MATCHED THEN UPDATE SET
                    SBAR_SUMMARY = PARSE_JSON('{sbar_json.replace("'", "''")}'),
                    PROCESSED_TIMESTAMP = CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN INSERT (
                    PATIENT_ID, SBAR_SUMMARY
                ) VALUES (
                    {patient_id}, PARSE_JSON('{sbar_json.replace("'", "''")}')
                )
            """).collect()
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                MERGE INTO HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS pa
                USING (SELECT ? AS PATIENT_ID) s
                ON pa.PATIENT_ID = s.PATIENT_ID
                WHEN MATCHED THEN UPDATE SET
                    SBAR_SUMMARY = PARSE_JSON(?),
                    PROCESSED_TIMESTAMP = CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN INSERT (
                    PATIENT_ID, SBAR_SUMMARY
                ) VALUES (
                    ?, PARSE_JSON(?)
                )
                """,
                (patient_id, sbar_json, patient_id, sbar_json)
            )
            cursor.close()
        return True
    except Exception as e:
        st.warning(f"Failed to save SBAR summary: {str(e)}")
        return False


def save_differential_to_db(patient_id: int, diagnoses: list, conn) -> bool:
    """Persist differential diagnoses to PATIENT_ANALYSIS.DIFFERENTIAL_DIAGNOSES."""
    try:
        dx_json = json.dumps(diagnoses)
        if hasattr(conn, 'sql'):
            conn.sql(f"""
                MERGE INTO HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS pa
                USING (SELECT {patient_id} AS PATIENT_ID) s
                ON pa.PATIENT_ID = s.PATIENT_ID
                WHEN MATCHED THEN UPDATE SET
                    DIFFERENTIAL_DIAGNOSES = PARSE_JSON('{dx_json.replace("'", "''")}'),
                    PROCESSED_TIMESTAMP = CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN INSERT (
                    PATIENT_ID, DIFFERENTIAL_DIAGNOSES
                ) VALUES (
                    {patient_id}, PARSE_JSON('{dx_json.replace("'", "''")}')
                )
            """).collect()
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                MERGE INTO HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS pa
                USING (SELECT ? AS PATIENT_ID) s
                ON pa.PATIENT_ID = s.PATIENT_ID
                WHEN MATCHED THEN UPDATE SET
                    DIFFERENTIAL_DIAGNOSES = PARSE_JSON(?),
                    PROCESSED_TIMESTAMP = CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN INSERT (
                    PATIENT_ID, DIFFERENTIAL_DIAGNOSES
                ) VALUES (
                    ?, PARSE_JSON(?)
                )
                """,
                (patient_id, dx_json, patient_id, dx_json)
            )
            cursor.close()
        return True
    except Exception as e:
        st.warning(f"Failed to save differential diagnoses: {str(e)}")
        return False


def save_treatment_analysis_to_db(patient_id: int, treatment: dict, conn) -> bool:
    """Persist treatment analysis fields to PATIENT_ANALYSIS."""
    try:
        current_treatments = json.dumps(treatment.get('current_treatments', []))
        treatment_effectiveness = treatment.get('treatment_effectiveness', '')
        evidence = json.dumps(treatment.get('evidence_based_recommendations', []))
        if hasattr(conn, 'sql'):
            conn.sql(f"""
                MERGE INTO HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS pa
                USING (SELECT {patient_id} AS PATIENT_ID) s
                ON pa.PATIENT_ID = s.PATIENT_ID
                WHEN MATCHED THEN UPDATE SET
                    TREATMENTS_ADMINISTERED = PARSE_JSON('{current_treatments.replace("'", "''")}'),
                    TREATMENT_EFFECTIVENESS = '{treatment_effectiveness.replace("'", "''")}',
                    EVIDENCE_BASED_RECOMMENDATIONS = PARSE_JSON('{evidence.replace("'", "''")}'),
                    PROCESSED_TIMESTAMP = CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN INSERT (
                    PATIENT_ID, TREATMENTS_ADMINISTERED, TREATMENT_EFFECTIVENESS, EVIDENCE_BASED_RECOMMENDATIONS
                ) VALUES (
                    {patient_id}, PARSE_JSON('{current_treatments.replace("'", "''")}'), '{treatment_effectiveness.replace("'", "''")}', PARSE_JSON('{evidence.replace("'", "''")}')
                )
            """).collect()
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                MERGE INTO HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS pa
                USING (SELECT ? AS PATIENT_ID) s
                ON pa.PATIENT_ID = s.PATIENT_ID
                WHEN MATCHED THEN UPDATE SET
                    TREATMENTS_ADMINISTERED = PARSE_JSON(?),
                    TREATMENT_EFFECTIVENESS = ?,
                    EVIDENCE_BASED_RECOMMENDATIONS = PARSE_JSON(?),
                    PROCESSED_TIMESTAMP = CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN INSERT (
                    PATIENT_ID, TREATMENTS_ADMINISTERED, TREATMENT_EFFECTIVENESS, EVIDENCE_BASED_RECOMMENDATIONS
                ) VALUES (
                    ?, PARSE_JSON(?), ?, PARSE_JSON(?)
                )
                """,
                (
                    patient_id,
                    current_treatments,
                    treatment_effectiveness,
                    evidence,
                    patient_id,
                    current_treatments,
                    treatment_effectiveness,
                    evidence,
                )
            )
            cursor.close()
        return True
    except Exception as e:
        st.warning(f"Failed to save treatment analysis: {str(e)}")
        return False


def generate_treatment_analysis(patient_notes: str, conn) -> dict:
    """Generate treatment analysis JSON using Cortex AI and return parsed dict."""
    prompt = f"""
    You are a clinical expert reviewing a patient's medical note. Extract current treatments, assess effectiveness, and provide evidence-based recommendations.
    Return ONLY valid JSON with this exact structure:
    {{
      "current_treatments": [{{"treatment": "name", "category": "medication|procedure|therapy", "effectiveness": "if any noted"}}],
      "treatment_effectiveness": "overall one-paragraph assessment",
      "evidence_based_recommendations": [{{"recommendation": "specific action", "rationale": "clinical reasoning", "evidence_level": "high|moderate|low"}}]
    }}

    Patient note:
    {patient_notes[:2000]}
    """
    try:
        response = execute_cortex_complete(prompt, "gpt-4o", conn)
        if response:
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
    except Exception as e:
        st.error(f"Error generating treatment analysis: {str(e)}")
    return {
        "current_treatments": [],
        "treatment_effectiveness": "",
        "evidence_based_recommendations": []
    }

def display_similar_patients(similar_patients_json, conn):
    """Display similar patient cases"""
    if not similar_patients_json:
        return
    
    try:
        similar = parse_json_safely(similar_patients_json, {})
        
        # Handle different formats - could be dict or list
        if isinstance(similar, dict) and len(similar) > 0:
            st.markdown("### 👥 Similar Patient Cases")
            
            # Convert dict to list of tuples and sort by score (descending)
            similar_items = list(similar.items())
            # Sort by score if scores are numeric, otherwise keep original order
            try:
                similar_items.sort(key=lambda x: float(x[1]), reverse=True)
            except (ValueError, TypeError):
                pass  # Keep original order if scores aren't numeric
            
            # Show top 3 similar patients
            for i, (patient_key, score) in enumerate(similar_items[:3]):
                # Extract patient ID from key (handle formats like "6077966-1" -> "6077966")
                try:
                    patient_id = patient_key.split('-')[0] if '-' in str(patient_key) else str(patient_key)
                    patient_id = int(patient_id)
                except (ValueError, AttributeError):
                    continue  # Skip if we can't parse the patient ID
                
                # Get basic info about similar patient
                query = f"""
                SELECT PATIENT_TITLE, AGE, GENDER
                FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
                WHERE PATIENT_ID = {patient_id}
                """
                similar_data = execute_query(query, conn)
                
                if not similar_data.empty:
                    sim_patient = similar_data.iloc[0]
                    # Format score for display
                    score_display = f"{float(score):.2f}" if isinstance(score, (int, float)) else str(score)
                    
                    st.markdown(f"""
                    <div class="similar-patient">
                        <strong>Similar Case #{i+1}</strong> (Similarity: {score_display})<br>
                        Patient ID: {patient_id}<br>
                        {sim_patient['PATIENT_TITLE'][:100]}...<br>
                        Age: {sim_patient['AGE']} | Gender: {sim_patient['GENDER']}
                    </div>
                    """, unsafe_allow_html=True)
        
        elif isinstance(similar, list) and len(similar) > 0:
            st.markdown("### 👥 Similar Patient Cases")
            
            # Handle list format (legacy support)
            for i, item in enumerate(similar[:3]):
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    patient_id, score = item[0], item[1]
                else:
                    continue  # Skip malformed items
                
                # Get basic info about similar patient
                query = f"""
                SELECT PATIENT_TITLE, AGE, GENDER
                FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
                WHERE PATIENT_ID = {patient_id}
                """
                similar_data = execute_query(query, conn)
                
                if not similar_data.empty:
                    sim_patient = similar_data.iloc[0]
                    st.markdown(f"""
                    <div class="similar-patient">
                        <strong>Similar Case #{i+1}</strong> (Similarity: {score:.2f})<br>
                        Patient ID: {patient_id}<br>
                        {sim_patient['PATIENT_TITLE'][:100]}...<br>
                        Age: {sim_patient['AGE']} | Gender: {sim_patient['GENDER']}
                    </div>
                    """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error displaying similar patients: {str(e)}")


def build_consolidated_analysis_results(patient_id: int, analysis_data, patient, conn) -> dict:
    """Build consolidated analysis results from pre-computed data or offer generation"""
    results = {}
    
    # Initialize with doctor-friendly ordering
    sections = [
        'clinical_summary',
        'differential_diagnosis', 
        'medication_safety',
        'treatment_analysis',
        'pattern_recognition',
        'quality_metrics',
        'cost_analysis',
        'educational_value',
        'evidence_literature'
    ]
    
    # Initialize all sections
    for section in sections:
        results[section] = {}
    
    if not analysis_data.empty:
        row = analysis_data.iloc[0]
        
        # Read from AI_ANALYSIS_JSON column (simplified structure)
        if row.get('AI_ANALYSIS_JSON'):
            try:
                complete_json = parse_json_safely(row['AI_ANALYSIS_JSON'])
                if complete_json and isinstance(complete_json, dict):
                    # Use the complete JSON structure
                    results.update(complete_json)
                    
                    # Add Evidence & Literature (always available from patient data)
                    results['evidence_literature'] = {
                        'relevant_articles': patient.get('RELEVANT_ARTICLES', ''),
                        'similar_patients': patient.get('SIMILAR_PATIENTS', '')
                    }
                    
                    return results
            except Exception as e:
                st.error(f"Error parsing AI_ANALYSIS_JSON: {e}")
                return results
        else:
            st.warning("No AI analysis found for this patient. Please use the 'Process with AI' button below.")
    
    # Evidence & Literature (always available from patient data)
    results['evidence_literature'] = {
        'relevant_articles': patient.get('RELEVANT_ARTICLES', ''),
        'similar_patients': patient.get('SIMILAR_PATIENTS', '')
    }
    
    return results


def display_clinical_analysis_results(results: dict, patient_id: int, patient, conn):
    """Deprecated: legacy renderer kept for reference; dynamic display now uses display_consolidated_results"""
    display_consolidated_results(results)


def display_generation_interface(section_key: str, patient_id: int, patient, conn):
    """Display interface for generating missing analysis sections"""
    if section_key == 'clinical_summary':
        st.info("No pre-computed clinical summary available.")
        if st.button("Generate Clinical Summary", key="gen_summary"):
            with st.spinner("Generating clinical summary..."):
                sbar_data = generate_clinical_summary(patient['PATIENT_NOTES'], conn)
                if sbar_data:
                    display_sbar_summary(sbar_data)
                    if save_sbar_summary_to_db(int(patient_id), sbar_data, conn):
                        st.success("Clinical summary saved to database.")
                        st.rerun()
                else:
                    st.error("Failed to generate summary.")
    
    elif section_key == 'differential_diagnosis':
        st.info("No pre-computed differential diagnoses available.")
        if st.button("Generate Differential Diagnoses", key="gen_dx"):
            with st.spinner("Analyzing patient case..."):
                diagnoses = generate_differential_diagnosis(
                    patient['PATIENT_NOTES'],
                    patient['SIMILAR_PATIENTS'],
                    conn
                )
                if diagnoses:
                    display_differential_diagnoses(diagnoses)
                    if save_differential_to_db(int(patient_id), diagnoses, conn):
                        st.success("Differential diagnoses saved to database.")
                        st.rerun()
                else:
                    st.error("Failed to generate diagnoses.")
    
    elif section_key == 'treatment_analysis':
        st.info("No pre-computed treatment analysis available.")
        if st.button("Generate Treatment Analysis", key="gen_tx"):
            with st.spinner("Generating treatment analysis..."):
                tx = generate_treatment_analysis(patient['PATIENT_NOTES'], conn)
                if tx and (tx.get('current_treatments') or tx.get('evidence_based_recommendations') or tx.get('treatment_effectiveness')):
                    display_treatment_analysis_clinical(tx)
                    if save_treatment_analysis_to_db(int(patient_id), tx, conn):
                        st.success("Treatment analysis saved to database.")
                        st.rerun()
                else:
                    st.error("Failed to generate treatment analysis.")


def display_section_with_clinical_styling(section_key: str, section_data: dict):
    """Display section data with enhanced clinical styling"""
    if not section_data:
        return
    
    if section_key == 'clinical_summary':
        display_sbar_summary(section_data)
    elif section_key == 'differential_diagnosis':
        display_enhanced_section_content(section_data, section_key)
    elif section_key == 'treatment_analysis':
        display_enhanced_section_content(section_data, section_key)
    elif section_key == 'medication_safety':
        display_enhanced_section_content(section_data, section_key)
    else:
        # Enhanced display for other sections using the new hierarchical structure
        display_enhanced_section_content(section_data, section_key)


def display_enhanced_section_content(section_data: dict, section_key: str):
    """Display hierarchical section content with appropriate styling"""
    
    def render_confidence_badge(confidence: str):
        """Render confidence level with appropriate styling"""
        if not confidence:
            return ""
        
        confidence_lower = confidence.lower()
        if "high" in confidence_lower:
            color_class = "#28a745"
        elif "medium" in confidence_lower:
            color_class = "#ffc107"
        elif "low" in confidence_lower:
            color_class = "#dc3545"
        else:
            color_class = "#6c757d"
        
        return f'<span style="color: {color_class}; font-weight: bold;">({confidence})</span>'
    
    def render_enhanced_array_items(items: list, parent_key: str):
        """Render array items with enhanced clinical styling"""
        if not items:
            return
        
        for idx, item in enumerate(items, 1):
            if isinstance(item, dict):
                # Extract display name dynamically from item content
                name = None
                # Look for any field that could be a display name
                for key, value in item.items():
                    if isinstance(value, str) and len(value) > 0 and len(value) < 200:
                        name = value
                        break
                
                if not name:
                    name = f"Item {idx}"
                
                # Build details dynamically from all available fields
                details = []
                confidence = item.get('confidence', '')
                evidence = item.get('evidence', [])
                
                # Add all fields as details (except the name field we used)
                name_key = None
                for key, value in item.items():
                    if isinstance(value, str) and value == name:
                        name_key = key
                        break
                
                for key, value in item.items():
                    if key not in ['confidence', 'evidence', 'drug1', 'drug2'] and key != name_key and value:
                        if isinstance(value, list):
                            if len(value) <= 3:  # Only show short lists inline
                                value_str = ', '.join(str(v) for v in value)
                                details.append(f"{key.replace('_', ' ').title()}: {value_str}")
                        elif isinstance(value, bool):
                            value_str = "✓ Yes" if value else "✗ No"
                            details.append(f"{key.replace('_', ' ').title()}: {value_str}")
                        elif not isinstance(value, dict):
                            details.append(f"{key.replace('_', ' ').title()}: {value}")
                
                # Handle special case for drug interactions (without hard-coding)
                if 'drug1' in item and 'drug2' in item:
                    name = f"Interaction: {item['drug1']} + {item['drug2']}"
                
                # Format confidence and evidence
                confidence_html = render_confidence_badge(confidence)
                # Handle evidence that might be a list of dictionaries or strings
                if isinstance(evidence, list):
                    evidence_strings = []
                    for e in evidence:
                        if isinstance(e, dict) and 'evidence_text' in e:
                            evidence_strings.append(e['evidence_text'])
                        elif isinstance(e, str):
                            evidence_strings.append(e)
                        else:
                            evidence_strings.append(str(e))
                    evidence_text = '; '.join(evidence_strings)
                else:
                    evidence_text = str(evidence)
                details_text = "<br>" + "<br>".join(details) if details else ""
                evidence_section = f"<br><strong>Evidence:</strong> {evidence_text}" if evidence_text else ""
                
                # Use consistent blue styling for all items
                st.markdown(f"""
                <div style="
                    background-color: #e8f4fd;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    margin-bottom: 0.5rem;
                    border-left: 3px solid #0066CC;
                ">
                    <strong>{idx}. {name}</strong> {confidence_html}{details_text}{evidence_section}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"- {item}")
    
    # Render the hierarchical section content
    for main_key, main_value in section_data.items():
        if not main_value:
            continue
            
        main_title = str(main_key).replace('_', ' ').title()
        
        # Handle nested structures
        if isinstance(main_value, dict):
            st.markdown(f"### {main_title}")
            for sub_key, sub_value in main_value.items():
                if not sub_value:
                    continue
                    
                sub_title = str(sub_key).replace('_', ' ').title()
                
                if isinstance(sub_value, list):
                    st.markdown(f"**{sub_title}:**")
                    render_enhanced_array_items(sub_value, sub_key)
                elif isinstance(sub_value, str):
                    st.markdown(f"**{sub_title}:** {sub_value}")
                else:
                    st.markdown(f"**{sub_title}:**")
                    st.write(sub_value)
        elif isinstance(main_value, list):
            st.markdown(f"### {main_title}")
            # If list contains only simple values, render each in a blue section
            if not any(isinstance(it, (dict, list)) for it in main_value):
                for idx, simple_item in enumerate(main_value, 1):
                    display_text = simple_item if simple_item is not None else ""
                    st.markdown(f"""
                    <div style="
                        background-color: #e8f4fd;
                        padding: 1rem;
                        border-radius: 0.5rem;
                        margin-bottom: 0.5rem;
                        border-left: 3px solid #0066CC;
                    ">
                        <strong>Item {idx}</strong><br>{display_text}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                render_enhanced_array_items(main_value, main_key)
        else:
            st.markdown(f"### {main_title}")
            st.write(main_value)


def display_treatment_analysis_clinical(treatment_data: dict):
    """Display treatment analysis with clinical styling"""
    if not treatment_data:
        return
    
    treatments = treatment_data.get('current_treatments', [])
    effectiveness = treatment_data.get('treatment_effectiveness', '')
    recs = treatment_data.get('evidence_based_recommendations', [])
    
    if treatments:
        st.markdown("### 💊 Current Treatments")
        for t in treatments:
            name = t.get('treatment', 'Unknown')
            category = t.get('category', 'n/a')
            effect = t.get('effectiveness', '')
            
            st.markdown(f"""
            <div class="treatment-recommendation">
                <strong>{name}</strong> ({category})<br>
                {f"Effectiveness: {effect}" if effect else ""}
            </div>
            """, unsafe_allow_html=True)
    
    if effectiveness:
        st.markdown("### 📊 Treatment Effectiveness")
        st.markdown(f"""
        <div class="treatment-recommendation">
            {effectiveness}
        </div>
        """, unsafe_allow_html=True)
    
    if recs:
        st.markdown("### 🎯 Evidence-based Recommendations")
        for r in recs:
            rec = r.get('recommendation', '')
            rationale = r.get('rationale', '')
            evidence = r.get('evidence_level', 'n/a')
            
            st.markdown(f"""
            <div class="treatment-recommendation">
                <strong>Recommendation:</strong> {rec}<br>
                <strong>Rationale:</strong> {rationale}<br>
                <strong>Evidence Level:</strong> {evidence}
            </div>
            """, unsafe_allow_html=True)


def display_evidence_literature_clinical(evidence_data: dict, patient, conn):
    """Display evidence & literature section with clinical styling"""
    st.markdown("### 📚 Relevant Medical Literature")
    
    relevant_articles = evidence_data.get('relevant_articles', '')
    if relevant_articles:
        articles = parse_json_safely(relevant_articles, {})
        if articles:
            st.markdown("Articles related to this case:")
            # Handle both dict and list formats
            if isinstance(articles, dict):
                article_items = list(articles.items())[:5]
            else:
                article_items = articles[:5]
            
            for i, (pmid, score) in enumerate(article_items):
                score_display = f"{float(score):.2f}" if isinstance(score, (int, float)) else str(score)
                st.markdown(f"""
                <div style="
                    background-color: #f8f9fa;
                    padding: 0.75rem;
                    border-radius: 0.25rem;
                    margin-bottom: 0.5rem;
                    font-size: 0.9rem;
                ">
                    {i+1}. PMID: <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank" style="color: #0066CC; text-decoration: none;">{pmid}</a> 
                    (Relevance Score: {score_display})
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No related articles found for this case.")
    else:
        st.info("No related articles found for this case.")
    
    # Display similar patients
    display_similar_patients(patient['SIMILAR_PATIENTS'], conn)

def main():
    """Main page function"""
    st.title("🩺 Clinical Decision Support")
    st.markdown("Clinical insights for improved patient care")
    
    # Get connection
    conn = get_snowflake_connection()
    if conn is None:
        st.error("Unable to connect to Snowflake. Please check your configuration.")
        st.stop()
    
    # Patient search section
    st.markdown("---")
    st.markdown("## 🔍 Patient Search")
    
    # Use a form to enable Enter key functionality
    with st.form(key="search_form"):
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            search_term = st.text_input(
                "Patient Search",
                placeholder="e.g., 9283, tumors, female with cardiac issues and diabetes",
                key="patient_search",
                help="Searches patient notes using Cortex Search"
            )
        
        with col2:
            # Add custom CSS to vertically center button with text input
            st.markdown("""
            <style>
            div[data-testid="column"]:nth-child(2) .stFormSubmitButton > button {
                margin-top: 12px;
            }
            </style>
            """, unsafe_allow_html=True)
            search_button = st.form_submit_button("Search", type="primary", use_container_width=True)

        with col3:
            filter_choice = st.radio("Search Filter", ["All", "Processed"], index=0, horizontal=False)
    
    # Initialize search results in session state
    if 'search_results' not in st.session_state:
        st.session_state.search_results = pd.DataFrame()
    if 'last_search_term' not in st.session_state:
        st.session_state.last_search_term = ""
    
    # Perform search when form is submitted (button clicked or Enter pressed)
    if search_term and search_button:
        with st.spinner("🔍 Searching patients..."):
            # If the search term is numeric, perform a direct SQL lookup on PATIENT_ID
            if search_term.strip().isdigit():
                pid = int(search_term.strip())
                direct_query = f"""
                SELECT DISTINCT
                    p.PATIENT_ID,
                    p.PATIENT_UID,
                    p.PATIENT_TITLE,
                    TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(p.AGE)[0][0])) AS AGE,
                    p.GENDER,
                    SUBSTR(p.PATIENT_NOTES, 1, 200) || '...' as NOTES_PREVIEW
                FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS p
                WHERE p.PATIENT_ID = {pid}
                {"AND EXISTS (SELECT 1 FROM HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS pa WHERE pa.PATIENT_ID = p.PATIENT_ID)" if filter_choice == "Processed" else ''}
                LIMIT 20
                """
                st.session_state.search_results = execute_query(direct_query, conn)
            else:
                st.session_state.search_results = search_patients_cortex(
                    search_term,
                    conn,
                    processed_only=(filter_choice == "Processed")
                )
            st.session_state.last_search_term = search_term
    
    # Display search results if available
    if not st.session_state.search_results.empty and st.session_state.last_search_term:
        st.markdown(f"### Found {len(st.session_state.search_results)} patients for '{st.session_state.last_search_term}'")
        # Temporary debug: show raw Cortex Search response if available
        raw = st.session_state.get('last_cortex_search_raw')
        if raw:
            with st.expander("🔎 Debug: Raw Cortex Search response", expanded=False):
                st.json(raw)
        
        # Add clear results button
        if st.button("🗑️ Clear Search Results", key="clear_search"):
            st.session_state.search_results = pd.DataFrame()
            st.session_state.last_search_term = ""
            st.rerun()
        
        # Display results in a selectable format
        for _, patient in st.session_state.search_results.iterrows():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(f"""
                **Patient {patient['PATIENT_ID']}**: {patient['PATIENT_TITLE'][:80]}...  
                Age: {patient['AGE']} | Gender: {patient['GENDER']}
                """)
            
            with col2:
                if st.button("Select", key=f"select_{int(patient['PATIENT_ID'])}"):
                    st.session_state.selected_patient_id = patient['PATIENT_ID']
                    # Clear search results after selection
                    st.session_state.search_results = pd.DataFrame()
                    st.session_state.last_search_term = ""
                    st.rerun()
    elif search_term and search_button and st.session_state.search_results.empty:
        st.warning("No patients found matching your search criteria.")
    


    # Display selected patient details
    if 'selected_patient_id' in st.session_state:
        patient_id = st.session_state.selected_patient_id
        
        st.markdown("---")
        
        # Get patient data
        patient_data = get_patient_details(patient_id, conn)
        
        if not patient_data.empty:
            patient = patient_data.iloc[0]

            # Display patient header
            display_patient_header(patient_data)

            # Move Full Clinical Notes directly under the summary area
            with st.expander("📝 Full Clinical Notes", expanded=False):
                st.markdown("""
                <style>
                .clinical-notes-text {
                    background-color: white;
                    color: black;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    border: 1px solid #ddd;
                    font-family: 'Courier New', monospace;
                    font-size: 14px;
                    line-height: 1.5;
                    white-space: pre-wrap;
                    max-height: 400px;
                    overflow-y: auto;
                }
                </style>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="clinical-notes-text">
                {patient['PATIENT_NOTES']}
                </div>
                """, unsafe_allow_html=True)

            # Get pre-computed analysis
            analysis_data = get_patient_analysis(patient_id, conn)
            # Safely detect presence of any precomputed content (avoid NaN truthiness)
            row0 = analysis_data.iloc[0] if not analysis_data.empty else {}
            def _has_value(val):
                try:
                    import pandas as _pd
                    return (val is not None) and (not (_pd.isna(val) if hasattr(_pd, 'isna') else False)) and str(val).strip() != ''
                except Exception:
                    return bool(val)
            has_precomputed = False
            if not analysis_data.empty:
                has_precomputed = _has_value(row0.get('AI_ANALYSIS_JSON'))

            if has_precomputed:
                analysis_results = build_consolidated_analysis_results(patient_id, analysis_data, patient, conn)
            else:
                # Auto-generate consolidated analysis using comprehensive prompt from stored procedure
                try:
                    with st.spinner("Running comprehensive AI analysis for this patient..."):
                        analysis_results = process_single_patient_comprehensive(
                            patient_notes=str(patient['PATIENT_NOTES']),
                            model="openai-gpt-5",
                            conn=conn
                        )
                        # Persist results for future loads (best-effort)
                        try:
                            save_patient_results_batch(int(patient_id), analysis_results, conn)
                        except Exception:
                            pass
                except Exception as e:
                    st.warning(f"Automatic analysis failed: {str(e)}")
                    analysis_results = {}

            # Dynamic display at the very bottom (identical to AI Processing page)
            st.markdown("---")
            st.markdown("## 📊 Preview Output")
            display_consolidated_results(analysis_results if isinstance(analysis_results, dict) else {})
        else:
            st.error(f"Patient {patient_id} not found in database.")
    else:
        # No patient selected
        pass

if __name__ == "__main__":
    main()