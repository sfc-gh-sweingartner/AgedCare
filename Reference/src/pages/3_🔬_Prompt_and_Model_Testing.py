"""
Page 3: Prompt and Model Testing
================================

Experiment with prompts and models on medical notes in real-time.
Based on the successful superannuation demo pattern.
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
import sys
import html
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from connection_helper import (
    get_snowflake_connection,
    execute_query,
    execute_cortex_complete,
    log_realtime_analysis,
    query_cortex_search_service,
    process_single_patient_comprehensive,
    COMPREHENSIVE_ANALYSIS_PROMPT
)

# Now using comprehensive prompt from stored procedure via connection_helper.py
# This provides the full 8-section analysis from the stored procedure instead of the previous 7-section version

# The comprehensive prompt includes enhanced sections like:
# - diagnostic_workup and diagnostic_confidence in differential_diagnosis
# - safety_alerts and risk_assessment in medication_safety  
# - contraindications in treatment_analysis
# - specialist_referral in pattern_recognition
# - safety_assessment and care_coordination in quality_metrics
# - detailed cost_drivers and financial_impact in cost_analysis
# - case_discussion and assessment_tools in educational_value

# Page configuration
st.set_page_config(
    page_title="Prompt and Model Testing - Healthcare AI",
    page_icon="🔬",
    layout="wide",
)

# Initialize session state
if 'processing_results' not in st.session_state:
    st.session_state.processing_results = {}
if 'current_note' not in st.session_state:
    st.session_state.current_note = ""
if 'selected_demo_patient' not in st.session_state:
    st.session_state.selected_demo_patient = None


def get_allowed_models(region: str):
    au_models = [
        ("Claude 3.5 Sonnet", "claude-3.5-sonnet"),
        ("Llama 3.1 8B", "llama3.1-8b"),
        ("Llama 3.1 70B", "llama3.1-70b"),
        ("Mistral Large", "mistral-large"),
        ("Mistral Large 2", "mistral-large2"),
        ("Mixtral 8x7B", "mixtral-8x7b"),
        ("Mistral 7B", "mistral-7b"),
    ]
    cross_region_extra = [
        ("Claude 4 Sonnet", "claude-4-sonnet"),
        ("OpenAI GPT-4.1", "openai-gpt-4.1"),
        ("OpenAI GPT-5", "openai-gpt-5"),
        ("OpenAI GPT-5 Mini", "openai-gpt-5-mini"),
        ("OpenAI GPT-5 Nano", "openai-gpt-5-nano"),
        ("OpenAI GPT-5 Chat", "openai-gpt-5-chat"),
        ("OpenAI GPT OSS 120B", "openai-gpt-oss-120b"),
        ("OpenAI GPT OSS 20B", "openai-gpt-oss-20b"),
        # Note: openai-o4-mini requires additional account enablement
    ]
    return au_models + (cross_region_extra if region == "Cross Region" else [])


@st.cache_data(ttl=300)
def search_patients_cortex(search_term, _conn):
    try:
        search_results = query_cortex_search_service(search_term, limit=20, conn=_conn)
        if not search_results.empty:
            search_results_with_preview = search_results.copy()
            if 'PATIENT_NOTES' not in search_results.columns:
                patient_ids = ','.join(str(pid) for pid in search_results['PATIENT_ID'])
                notes_query = f"""
                SELECT PATIENT_ID, SUBSTR(PATIENT_NOTES, 1, 200) || '...' AS NOTES_PREVIEW
                FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
                WHERE PATIENT_ID IN ({patient_ids})
                """
                notes_data = execute_query(notes_query, _conn)
                search_results_with_preview = search_results.merge(notes_data, on='PATIENT_ID', how='left')
            else:
                search_results_with_preview['NOTES_PREVIEW'] = search_results['PATIENT_NOTES'].apply(
                    lambda x: str(x)[:200] + '...' if str(x) != 'nan' and x is not None else 'No notes available'
                )
            if 'score' in search_results_with_preview.columns:
                search_results_with_preview.rename(columns={'score': 'RELEVANCE_SCORE'}, inplace=True)
            return search_results_with_preview
    except Exception:
        pass
    return search_patients_basic(search_term, _conn)


@st.cache_data(ttl=300)
def search_patients_basic(search_term, _conn):
    query = f"""
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            PATIENT_UID,
            PATIENT_TITLE,
            GENDER,
            PATIENT_NOTES,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    )
    SELECT DISTINCT
        p.PATIENT_ID,
        p.PATIENT_UID,
        p.PATIENT_TITLE,
        p.AGE_YEARS AS AGE,
        p.GENDER,
        SUBSTR(p.PATIENT_NOTES, 1, 200) || '...' AS NOTES_PREVIEW
    FROM parsed_pmc p
    WHERE CAST(p.PATIENT_ID AS STRING) LIKE '%{search_term}%'
       OR UPPER(p.PATIENT_TITLE) LIKE UPPER('%{search_term}%')
       OR UPPER(p.PATIENT_NOTES) LIKE UPPER('%{search_term}%')
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
    query = f"""
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            PATIENT_UID,
            PATIENT_TITLE,
            PATIENT_NOTES,
            SIMILAR_PATIENTS,
            RELEVANT_ARTICLES,
            GENDER,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    )
    SELECT PATIENT_ID, PATIENT_UID, PATIENT_TITLE, AGE_YEARS AS AGE, GENDER,
           PATIENT_NOTES, SIMILAR_PATIENTS, RELEVANT_ARTICLES
    FROM parsed_pmc
    WHERE PATIENT_ID = {patient_id}
    """
    return execute_query(query, _conn)


def parse_consolidated_response(response: str) -> dict:
    try:
        import re as _re
        # Prefer fenced JSON if present
        fence = _re.search(r"```(?:json)?\s*([\s\S]*?)```", response, _re.IGNORECASE)
        if fence:
            try:
                return json.loads(fence.group(1))
            except Exception:
                pass
        # General JSON object fallback
        json_match = _re.search(r'\{[\s\S]*\}', response, _re.DOTALL)
        if json_match:
            try:
                full_result = json.loads(json_match.group())
                return full_result if isinstance(full_result, dict) else {"result": full_result}
            except Exception:
                from connection_helper import parse_json_safely as _safe
                parsed = _safe(json_match.group(), {})
                if isinstance(parsed, dict) and parsed:
                    return parsed
    except Exception:
        pass
    return {}


def display_consolidated_results(results: dict):
    """Enhanced display function with clinical styling similar to Clinical Decision Support page"""
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

    def render_clinical_section(title: str, content: str, section_type: str = "default"):
        """Render content with consistent blue styling"""
        if content is None:
            return
        
        # Use consistent blue styling for all sections
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
                        
                        # Handle special case for drug interactions (without hard-coding)
                        if 'drug1' in item and 'drug2' in item:
                            name = f"Interaction: {item['drug1']} + {item['drug2']}"
                        
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
                        st.markdown(f"**Item {idx}**")
                        render_value(item, level + 1, parent_key)
            else:
                # Render simple lists with consistent blue styling per item (no hard-coded field names)
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
            # Special handling for Evidence & Literature section
            if key == 'evidence_literature':
                render_evidence_literature_section(results.get(key, {}))
            else:
                render_value(results.get(key, {}), level=0, parent_key=key)

def render_evidence_literature_section(evidence_data: dict):
    """Special rendering for Evidence & Literature section"""
    try:
        from connection_helper import parse_json_safely
        
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
        
        st.markdown("### 👥 Similar Patient Cases")
        
        similar_patients = evidence_data.get('similar_patients', '')
        if similar_patients:
            similar = parse_json_safely(similar_patients, {})
            if isinstance(similar, dict) and len(similar) > 0:
                # Convert dict to list of tuples and sort by score
                similar_items = list(similar.items())
                try:
                    similar_items.sort(key=lambda x: float(x[1]), reverse=True)
                except (ValueError, TypeError):
                    pass  # Keep original order if scores aren't numeric
                
                # Show top 3 similar patients
                for i, (patient_key, score) in enumerate(similar_items[:3]):
                    try:
                        patient_id = patient_key.split('-')[0] if '-' in str(patient_key) else str(patient_key)
                        score_display = f"{float(score):.2f}" if isinstance(score, (int, float)) else str(score)
                        
                        st.markdown(f"""
                        <div style="
                            background-color: #fff3cd;
                            padding: 0.75rem;
                            border-radius: 0.25rem;
                            margin-bottom: 0.5rem;
                            font-size: 0.9rem;
                        ">
                            <strong>Similar Case #{i+1}</strong> (Similarity: {score_display})<br>
                            Patient ID: {patient_id}
                        </div>
                        """, unsafe_allow_html=True)
                    except (ValueError, AttributeError):
                        continue
            else:
                st.info("No similar patient cases found.")
        else:
            st.info("No similar patient cases found.")
            
    except Exception as e:
        st.error(f"Error displaying evidence and literature: {str(e)}")


def main():
    st.title("🔬 Prompt and Model Testing")
    st.markdown("Test prompts and models on medical notes in real-time with Snowflake Cortex AI")

    conn = get_snowflake_connection()
    if conn is None:
        st.error("Unable to connect to Snowflake. Please check your configuration.")
        st.stop()

    with st.expander("📖 How to use this page", expanded=True):
        st.markdown(
            """
            - **Search** and select any patient from the database (or paste custom notes).
            - **Review/Edit** the consolidated prompt used in batch processing.
            - **Choose** a model (availability depends on region) and run the analysis.
            - **Inspect** parsed results across multiple clinical use cases.
            """
        )

    st.markdown("---")

    st.markdown("### 1️⃣ Search and Select Patient")
    with st.form(key="search_form_prompt_model"):
        c1, c2 = st.columns([3, 1])
        with c1:
            search_term = st.text_input(
                "🤖 AI-Powered Patient Search",
                placeholder="e.g., 9283, tumors, female with cardiac issues and diabetes",
                key="patient_search_live",
                help="Uses Snowflake Cortex AI for semantic search.",
            )
        with c2:
            st.markdown(
                """
                <style>
                div[data-testid=\"column\"]:nth-child(2) .stFormSubmitButton > button { margin-top: 12px; }
                </style>
                """,
                unsafe_allow_html=True,
            )
            do_search = st.form_submit_button("Search", type="primary", use_container_width=True)

    if 'search_results_live' not in st.session_state:
        st.session_state.search_results_live = pd.DataFrame()
    if 'last_search_term_live' not in st.session_state:
        st.session_state.last_search_term_live = ""
    if do_search and search_term:
        with st.spinner("🔍 Searching patients..."):
            # If the user entered a numeric patient_id, query directly instead of Cortex
            if search_term.strip().isdigit():
                pid = int(search_term.strip())
                direct_query = f"""
                WITH parsed_pmc AS (
                    SELECT 
                        PATIENT_ID,
                        PATIENT_UID,
                        PATIENT_TITLE,
                        GENDER,
                        PATIENT_NOTES,
                        TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS
                    FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
                )
                SELECT DISTINCT
                    p.PATIENT_ID,
                    p.PATIENT_UID,
                    p.PATIENT_TITLE,
                    p.AGE_YEARS AS AGE,
                    p.GENDER,
                    SUBSTR(p.PATIENT_NOTES, 1, 200) || '...' AS NOTES_PREVIEW
                FROM parsed_pmc p
                WHERE p.PATIENT_ID = {pid}
                LIMIT 20
                """
                st.session_state.search_results_live = execute_query(direct_query, conn)
            else:
                st.session_state.search_results_live = search_patients_cortex(search_term, conn)
            st.session_state.last_search_term_live = search_term
    if not st.session_state.search_results_live.empty and st.session_state.last_search_term_live:
        st.markdown(
            f"Found {len(st.session_state.search_results_live)} patients for '{st.session_state.last_search_term_live}'"
        )
        # Temporary debug: show raw Cortex Search response if available
        raw = st.session_state.get('last_cortex_search_raw')
        if raw:
            with st.expander("🔎 Debug: Raw Cortex Search response", expanded=False):
                st.json(raw)
        for _, patient in st.session_state.search_results_live.iterrows():
            cc1, cc2 = st.columns([4, 1])
            with cc1:
                st.markdown(
                    f"**Patient {int(patient['PATIENT_ID'])}**: {str(patient['PATIENT_TITLE'])[:80]}..."
                )
                st.caption(f"Age: {patient['AGE']} | Gender: {patient['GENDER']}")
            with cc2:
                if st.button("Select", key=f"select_live_{int(patient['PATIENT_ID'])}"):
                    st.session_state.selected_patient_id_live = int(patient['PATIENT_ID'])
                    st.session_state.search_results_live = pd.DataFrame()
                    st.session_state.last_search_term_live = ""
                    st.rerun()
        if st.button("🗑️ Clear Results", key="clear_results_live"):
            st.session_state.search_results_live = pd.DataFrame()
            st.session_state.last_search_term_live = ""
            st.rerun()

    use_custom = st.checkbox(
        "Or paste custom notes instead",
        value=False,
        help="Use this if you want to test free-text notes.",
    )
    selected_note_text = ""
    selected_patient_id_display = None
    if not use_custom and 'selected_patient_id_live' in st.session_state:
        pid = st.session_state.selected_patient_id_live
        details = get_patient_details(pid, conn)
        if not details.empty:
            patient = details.iloc[0]
            selected_patient_id_display = int(patient['PATIENT_ID'])
            st.markdown("### 🧾 Selected Patient Notes")
            notes_html = f"""
            <style>
            .notes-box {{
                background-color: #FFFFFF;
                color: #212529;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 0.75rem;
                max-height: 220px;
                overflow-y: auto;
                white-space: pre-wrap;
                font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,'Apple Color Emoji','Segoe UI Emoji';
                font-size: 0.95rem;
                line-height: 1.4;
            }}
            </style>
            <div class="notes-box">{html.escape(str(patient['PATIENT_NOTES']))}</div>
            """
            st.markdown(notes_html, unsafe_allow_html=True)
            selected_note_text = str(patient['PATIENT_NOTES'])
        else:
            st.warning(f"Patient {pid} not found.")
    elif use_custom:
        st.markdown("### 🧾 Custom Notes")
        selected_note_text = st.text_area(
            "Paste patient notes:",
            value=st.session_state.get('current_note', ''),
            height=200,
            key="custom_notes_area",
        )

    st.markdown("---")

    st.markdown("### 2️⃣ Review and Edit Comprehensive Prompt")
    if 'consolidated_prompt_text' not in st.session_state:
        st.session_state.consolidated_prompt_text = COMPREHENSIVE_ANALYSIS_PROMPT
    colp1, colp2 = st.columns([3, 1])
    with colp1:
        prompt_text = st.text_area(
            "Comprehensive Prompt Template (from Stored Procedure)",
            value=st.session_state.consolidated_prompt_text,
            height=350,
            key="consolidated_prompt_editor",
            help="This is the comprehensive 8-section prompt from the stored procedure. You can edit it here for experimentation."
        )
    with colp2:
        if st.button("Reset to Comprehensive", key="reset_prompt"):
            st.session_state.consolidated_prompt_text = COMPREHENSIVE_ANALYSIS_PROMPT
            st.rerun()

    st.markdown("### 3️⃣ Select Model and Run")
    colm1, colm2, colm3 = st.columns([1, 2, 1])
    with colm1:
        region = st.selectbox(
            "Region", ["Australia", "Cross Region"], index=1, help="Controls available models"
        )
    with colm2:
        models = get_allowed_models(region)
        model_labels = [m[0] for m in models]
        model_values = [m[1] for m in models]
        # Default to OpenAI GPT-5 if available, otherwise Claude 4 Sonnet, otherwise Mistral Large, otherwise first model
        if "openai-gpt-5" in model_values:
            default_idx = model_values.index("openai-gpt-5")
        elif "claude-4-sonnet" in model_values:
            default_idx = model_values.index("claude-4-sonnet")
        elif "mistral-large" in model_values:
            default_idx = model_values.index("mistral-large")
        else:
            default_idx = 0
        selected_model_label = st.selectbox("Model", model_labels, index=default_idx)
        selected_model = model_values[model_labels.index(selected_model_label)]
    with colm3:
        if st.button("🚀 Run Prompt", type="primary", use_container_width=True):
            if selected_note_text and len(selected_note_text) > 50:
                st.session_state.consolidated_prompt_text = prompt_text
                filled_prompt = prompt_text.replace("{patient_notes}", selected_note_text[:4000])
                with st.spinner("Running model and parsing results..."):
                    try:
                        raw_response = execute_cortex_complete(filled_prompt, selected_model, conn)
                        parsed = parse_consolidated_response(raw_response or "")
                        # Fallback to alternate model if parsed is empty
                        if not parsed:
                            try:
                                alt_model = "mistral-large" if selected_model != "mistral-large" else "llama3.1-8b"
                                raw_alt = execute_cortex_complete(filled_prompt, alt_model, conn)
                                parsed = parse_consolidated_response(raw_alt or "")
                                if not parsed and (raw_alt or raw_response):
                                    minimal = (raw_alt or raw_response or "").strip()
                                    if minimal:
                                        parsed = {"clinical_summary": {"clinical_summary": minimal[:1500]}}
                            except Exception:
                                pass
                        st.session_state.processing_results = parsed
                        st.session_state.raw_model_response = raw_response
                        try:
                            log_realtime_analysis(
                                session_id=st.session_state.get('session_id', 'demo'),
                                user_name='demo_user',
                                patient_id=selected_patient_id_display or 0,
                                original_text=selected_note_text[:500],
                                modified_text=selected_note_text[:500],
                                analysis_type='consolidated',
                                ai_model=selected_model,
                                processing_time_ms=0,
                                results=parsed,
                                success=True,
                                conn=conn,
                            )
                        except Exception:
                            pass
                        st.success("✅ Analysis complete!")
                    except Exception as e:
                        st.error(f"❌ Failed to run analysis: {str(e)}")
            else:
                st.warning("Please provide patient notes with at least 50 characters.")

    # Schema Builder (experimental) - Simplified for JSON generation only
    st.markdown("---")
    with st.expander("🧱 Enhanced Schema Builder", expanded=False):
        st.caption(
            "Generate complex JSON structures for your analysis. Choose from templates or build custom sections with values and examples."
        )

        # Initialize session state
        if 'working_schema' not in st.session_state:
            st.session_state.working_schema = {}
        if 'schema_builder_mode' not in st.session_state:
            st.session_state.schema_builder_mode = "Template"

        # Mode selection
        schema_mode = st.radio(
            "Choose Builder Mode:",
            ["Template", "Custom Builder"],
            horizontal=True,
            help="Templates provide pre-built complex structures; Custom Builder lets you create from scratch"
        )
        st.session_state.schema_builder_mode = schema_mode

        if schema_mode == "Template":
            st.markdown("### 📋 Pre-built Templates")
            
            template_options = {
                "Complete Medical Analysis": {
                    "differential_diagnosis": {
                        "chief_complaint": "Main presenting complaint",
                        "key_findings": [
                            {"finding": "specific finding", "category": "symptom/sign/lab", "severity": "mild/moderate/severe"}
                        ],
                        "differential_diagnoses": [
                            {
                                "diagnosis": "diagnosis name",
                                "confidence": "high/medium/low",
                                "evidence": ["supporting finding 1", "supporting finding 2"],
                                "icd10_code": "ICD-10 code if known"
                            }
                        ],
                        "diagnostic_reasoning": "Brief explanation of diagnostic thinking",
                        "recommended_tests": ["test1", "test2"]
                    },
                    "treatment_analysis": {
                        "current_treatments": [
                            {"treatment": "name", "category": "medication/procedure/therapy", "effectiveness": "noted outcome if mentioned"}
                        ],
                        "treatment_effectiveness": "Overall assessment of treatment response",
                        "evidence_based_recommendations": [
                            {"recommendation": "specific recommendation", "rationale": "clinical reasoning", "evidence_level": "high/moderate/low"}
                        ],
                        "contraindications": ["any treatments to avoid based on patient condition"]
                    },
                    "clinical_summary": {
                        "situation": "Current clinical situation and reason for encounter",
                        "background": "Relevant medical history, medications, allergies",
                        "assessment": "Clinical assessment including vital signs and key findings",
                        "recommendation": "Treatment plan and follow-up recommendations",
                        "clinical_summary": "One paragraph narrative summary"
                    }
                },
                "Diagnosis & Assessment": {
                    "differential_diagnosis": {
                        "chief_complaint": "Main presenting complaint",
                        "key_findings": [
                            {"finding": "specific finding", "category": "symptom/sign/lab", "severity": "mild/moderate/severe"}
                        ],
                        "differential_diagnoses": [
                            {
                                "diagnosis": "diagnosis name",
                                "confidence": "high/medium/low",
                                "evidence": ["supporting finding 1", "supporting finding 2"],
                                "icd10_code": "ICD-10 code if known"
                            }
                        ],
                        "diagnostic_reasoning": "Brief explanation of diagnostic thinking",
                        "recommended_tests": ["test1", "test2"]
                    },
                    "pattern_recognition": {
                        "presentation_type": "typical/atypical/rare",
                        "symptom_pattern": "Description of the symptom constellation",
                        "rare_disease_indicators": [
                            {"indicator": "specific finding", "associated_conditions": ["condition1", "condition2"], "significance": "explanation"}
                        ],
                        "anomaly_score": 0.0,
                        "similar_rare_conditions": ["condition name with brief description"],
                        "recommended_specialist": "Suggested specialist consultation if needed"
                    }
                },
                "Medication & Safety": {
                    "medication_safety": {
                        "extracted_medications": [
                            {"medication": "name", "dosage": "if mentioned", "frequency": "if mentioned", "indication": "reason for use"}
                        ],
                        "drug_interactions": [
                            {"drugs": ["drug1", "drug2"], "interaction_type": "major/moderate/minor", "clinical_effect": "description"}
                        ],
                        "contraindications": [
                            {"medication": "name", "contraindication": "condition/allergy", "severity": "absolute/relative"}
                        ],
                        "safety_alerts": ["alert1", "alert2"],
                        "polypharmacy_risk": "low/medium/high"
                    },
                    "quality_metrics": {
                        "quality_indicators": [
                            {"indicator": "name", "met": True, "details": "explanation"}
                        ],
                        "guideline_adherence": [
                            {"guideline": "name", "adherent": True, "gaps": ["gap1", "gap2"]}
                        ],
                        "improvement_opportunities": ["opportunity1", "opportunity2"],
                        "safety_events": ["event1 if any"]
                    }
                },
                "Cost & Utilization": {
                    "cost_analysis": {
                        "extracted_procedures": [
                            {"procedure": "name", "category": "diagnostic/therapeutic/surgical", "complexity": "low/medium/high"}
                        ],
                        "high_cost_indicators": [
                            {"indicator": "specific finding", "cost_driver": "reason for high cost", "estimated_impact": "high/medium/low"}
                        ],
                        "cost_category": "low/medium/high/very_high",
                        "utilization_factors": ["factor1", "factor2"]
                    }
                },
                "Educational Value": {
                    "educational_value": {
                        "teaching_points": [
                            {"point": "key learning", "category": "diagnosis/treatment/prevention", "relevance": "why important"}
                        ],
                        "clinical_pearls": "Key insights or unusual aspects of this case",
                        "quiz_questions": [
                            {"question": "clinical question", "options": ["A", "B", "C", "D"], "correct_answer": "A", "explanation": "why"}
                        ]
                    }
                }
            }

            selected_template = st.selectbox(
                "Select a template:",
                list(template_options.keys()),
                help="Choose a pre-built template that matches your analysis needs"
            )

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("📋 Use This Template", type="primary"):
                    st.session_state.working_schema = template_options[selected_template].copy()
                    st.success(f"Loaded '{selected_template}' template!")
            
            with col2:
                if st.button("➕ Add to Current Schema"):
                    st.session_state.working_schema.update(template_options[selected_template])
                    st.success(f"Added '{selected_template}' sections to your schema!")

        else:  # Custom Builder
            st.markdown("### 🔧 Custom Schema Builder")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                new_section_name = st.text_input(
                    "Section Name",
                    placeholder="e.g., medical_coding, quality_metrics, cost_analysis",
                    help="This will become a new top-level key in the JSON",
                )

            with col2:
                section_type = st.selectbox(
                    "Section Type",
                    ["Simple Object", "Complex Object", "Array of Objects", "Array of Strings"],
                    help="Choose the structure type for this section",
                )

            if new_section_name:
                st.markdown(f"**Configure '{new_section_name}' section:**")

                if section_type == "Simple Object":
                    field_config = st.text_area(
                        "Field Configuration (one per line: field_name = example_value)",
                        value="diagnosis = diabetes mellitus type 2\nconfidence = high\nicd10_code = E11.9",
                        height=120,
                        help="Define fields with example values to show the expected format. Edit the examples above or replace with your own fields."
                    )
                    
                elif section_type == "Complex Object":
                    field_config = st.text_area(
                        "Complex Object Structure (JSON format)",
                        value='{\n  "nested_object": {\n    "field1": "value1",\n    "field2": ["item1", "item2"]\n  },\n  "simple_field": "example_value"\n}',
                        height=150,
                        help="Define a complex nested structure in JSON format. Edit the example above or replace with your own structure."
                    )
                    
                elif section_type == "Array of Objects":
                    field_config = st.text_area(
                        "Object Template (one per line: field_name = example_value)",
                        value="medication = aspirin\ndosage = 81mg\nfrequency = daily\nindication = cardiovascular protection",
                        height=120,
                        help="Define the structure for each object in the array. Edit the examples above or replace with your own fields."
                    )
                    
                elif section_type == "Array of Strings":
                    field_config = st.text_input(
                        "Example Values (comma-separated)",
                        value="contraindication 1, contraindication 2, contraindication 3",
                        help="Provide example string values for the array. Edit the examples above or replace with your own values."
                    )

                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    if st.button(f"➕ Add '{new_section_name}' Section", type="primary"):
                        try:
                            if section_type == "Simple Object":
                                obj = {}
                                for line in field_config.split('\n'):
                                    if '=' in line:
                                        key, value = line.split('=', 1)
                                        obj[key.strip()] = value.strip()
                                st.session_state.working_schema[new_section_name] = obj
                                
                            elif section_type == "Complex Object":
                                obj = json.loads(field_config) if field_config.strip() else {}
                                st.session_state.working_schema[new_section_name] = obj
                                
                            elif section_type == "Array of Objects":
                                obj = {}
                                for line in field_config.split('\n'):
                                    if '=' in line:
                                        key, value = line.split('=', 1)
                                        obj[key.strip()] = value.strip()
                                st.session_state.working_schema[new_section_name] = [obj]
                                
                            elif section_type == "Array of Strings":
                                items = [item.strip() for item in field_config.split(',') if item.strip()]
                                st.session_state.working_schema[new_section_name] = items
                                
                            st.success(f"Added '{new_section_name}' section!")
                            
                        except json.JSONDecodeError:
                            st.error("Invalid JSON format. Please check your syntax.")
                        except Exception as e:
                            st.error(f"Error adding section: {str(e)}")

        # Schema Management
        st.markdown("---")
        st.markdown("### 🔧 Schema Management")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("🗑️ Clear Schema"):
                st.session_state.working_schema = {}
                st.success("Schema cleared!")
        
        with col2:
            if st.button("📋 Generate JSON", type="primary"):
                if st.session_state.working_schema:
                    st.session_state.show_schema_preview = True
                else:
                    st.warning("No schema defined yet. Please add sections first.")
        
        with col3:
            if st.session_state.working_schema:
                st.write(f"**Sections:** {len(st.session_state.working_schema)}")

        # Display current schema sections
        if st.session_state.working_schema:
            st.markdown("**Current Schema Sections:**")
            for section_name in st.session_state.working_schema.keys():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"• {section_name}")
                with col2:
                    if st.button(f"❌", key=f"remove_{section_name}", help=f"Remove {section_name}"):
                        del st.session_state.working_schema[section_name]
                        st.experimental_rerun()

        # Show generated JSON
        if st.session_state.get('show_schema_preview', False) and st.session_state.working_schema:
            st.markdown("---")
            st.markdown("### 📄 Generated JSON Schema")
            st.caption("Copy this JSON and paste it into the Consolidated Prompt Template above")
            
            json_output = json.dumps(st.session_state.working_schema, indent=2)
            st.code(json_output, language="json")
            
            # Copy helper
            st.info("💡 **Usage Tip:** Copy the JSON above and paste it into the prompt template. The AI will populate the structure with actual data from the patient notes.")

    if st.session_state.processing_results:
        st.markdown("---")
        st.markdown("## 📊 Preview Output")
        if 'raw_model_response' in st.session_state and st.session_state.raw_model_response:
            with st.expander("🔎 View Raw Model Response"):
                response_html = f"""
                <style>
                .response-box {{
                    background-color: #FFFFFF;
                    color: #212529;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 0.75rem;
                    max-height: 220px;
                    overflow-y: auto;
                    white-space: pre-wrap;
                    font-family: ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono','Courier New',monospace;
                    font-size: 0.9rem;
                    line-height: 1.4;
                }}
                </style>
                <div class="response-box">{html.escape(str(st.session_state.raw_model_response))}</div>
                """
                st.markdown(response_html, unsafe_allow_html=True)
        
        # Add Evidence & Literature tab to the results
        enhanced_results = st.session_state.processing_results.copy()
        
        # Get evidence & literature data if we have a selected patient
        if 'selected_patient_id_live' in st.session_state:
            patient_id = st.session_state.selected_patient_id_live
            patient_details = get_patient_details(patient_id, conn)
            if not patient_details.empty:
                patient = patient_details.iloc[0]
                # Add Evidence & Literature section
                enhanced_results['evidence_literature'] = {
                    'relevant_articles': patient.get('RELEVANT_ARTICLES', ''),
                    'similar_patients': patient.get('SIMILAR_PATIENTS', '')
                }
        
        display_consolidated_results(enhanced_results)
        st.markdown("---")


if __name__ == "__main__":
    main()
