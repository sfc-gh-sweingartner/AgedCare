import streamlit as st
import json
import re
import sys
sys.path.insert(0, '/Users/sweingartner/CoCo/AgedCare/dri-intelligence')

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

st.set_page_config(page_title="Claude vs Regex Comparison", page_icon="🔄", layout="wide")
st.title("🔄 Claude vs Regex DRI Comparison")

session = get_snowflake_session()

TOTAL_DEFICITS = 33

def calculate_dri_score(active_deficits: int) -> float:
    return round(active_deficits / TOTAL_DEFICITS, 4)

def get_severity_band(score: float) -> str:
    if score <= 0.2:
        return "Low"
    elif score <= 0.4:
        return "Medium"
    elif score <= 0.6:
        return "High"
    else:
        return "Very High"

def get_severity_color(band: str) -> str:
    colors = {"Low": "green", "Medium": "orange", "High": "red", "Very High": "darkred"}
    return colors.get(band, "gray")

def run_regex_detection(text: str, indicators_df) -> dict:
    """Run simple keyword/pattern matching against text for each indicator."""
    results = {}
    text_lower = text.lower()
    
    for _, row in indicators_df.iterrows():
        indicator_id = row['INDICATOR_ID']
        indicator_name = row['INDICATOR_NAME']
        definition = str(row['DEFINITION'] or '').lower()
        keywords = str(row['KEYWORDS'] or '').lower()
        inclusion = str(row['INCLUSION_CRITERIA'] or '').lower()
        
        search_terms = []
        search_terms.append(indicator_name.lower())
        search_terms.extend([t.strip() for t in definition.split(';') if t.strip()])
        search_terms.extend([t.strip() for t in keywords.split(',') if t.strip()])
        search_terms.extend([t.strip() for t in inclusion.split(';') if t.strip()])
        
        matches = []
        for term in search_terms:
            if len(term) > 3 and term in text_lower:
                start = text_lower.find(term)
                context_start = max(0, start - 30)
                context_end = min(len(text), start + len(term) + 30)
                matches.append(text[context_start:context_end])
        
        results[indicator_id] = {
            'indicator_id': indicator_id,
            'indicator_name': indicator_name,
            'detected': len(matches) > 0,
            'match_count': len(matches),
            'matches': matches[:3]
        }
    
    return results

if session:
    st.markdown("""
    Compare DRI indicator detection and scores between **Claude LLM** analysis and the **Regex/Rules** based approach.
    This helps measure accuracy improvements and identify false positive reductions.
    """)
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Configuration")
        
        residents = execute_query_df("""
            SELECT DISTINCT RESIDENT_ID 
            FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES
            ORDER BY RESIDENT_ID
        """, session)
        
        if residents is not None and len(residents) > 0:
            selected_resident = st.selectbox(
                "Select Resident",
                residents['RESIDENT_ID'].tolist(),
                help="Choose a resident to compare"
            )
        else:
            selected_resident = st.number_input("Resident ID", value=871, min_value=1)
        
        model_options = [
            'claude-sonnet-4-5',
            'claude-opus-4-5',
            'claude-haiku-4-5',
            'claude-3-5-sonnet',
            'claude-3-7-sonnet',
            'claude-4-sonnet',
            'mistral-large2',
            'llama3.1-70b'
        ]
        selected_model = st.selectbox("LLM Model for Analysis", model_options)
        
        prompt_versions = execute_query_df("""
            SELECT VERSION_NUMBER, IS_ACTIVE 
            FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS
            ORDER BY CREATED_TIMESTAMP DESC
        """, session)
        
        if prompt_versions is not None and len(prompt_versions) > 0:
            version_options = prompt_versions['VERSION_NUMBER'].tolist()
            active_version = prompt_versions[prompt_versions['IS_ACTIVE'] == True]['VERSION_NUMBER'].tolist()
            default_idx = version_options.index(active_version[0]) if active_version else 0
            selected_version = st.selectbox("Prompt Version", version_options, index=default_idx)
        else:
            selected_version = "v1.0"
    
    with col2:
        st.subheader("Comparison Results")
        
        btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
        with btn_col1:
            run_comparison = st.button("🔄 Run Comparison", type="primary")
        
        if run_comparison:
            import time
            
            with st.spinner(f"Running analysis for Resident {selected_resident}..."):
                start_time = time.time()
                
                try:
                    context_query = f"""
                    WITH resident_notes AS (
                        SELECT LISTAGG(LEFT(PROGRESS_NOTE, 400) || ' [' || NOTE_TYPE || ']', ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as notes_text
                        FROM (SELECT PROGRESS_NOTE, NOTE_TYPE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES WHERE RESIDENT_ID = {selected_resident} ORDER BY EVENT_DATE DESC LIMIT 15)
                    ),
                    resident_meds AS (
                        SELECT LISTAGG(MED_NAME || ' (' || MED_STATUS || ')', ', ') as meds_text
                        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION WHERE RESIDENT_ID = {selected_resident}
                    ),
                    resident_obs AS (
                        SELECT LISTAGG(CHART_NAME || ': ' || LEFT(OBSERVATION_VALUE, 100), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as obs_text
                        FROM (SELECT CHART_NAME, OBSERVATION_VALUE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS WHERE RESIDENT_ID = {selected_resident} ORDER BY EVENT_DATE DESC LIMIT 30)
                    ),
                    resident_forms AS (
                        SELECT LISTAGG(FORM_NAME || ': ' || ELEMENT_NAME || '=' || LEFT(RESPONSE, 100), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as forms_text
                        FROM (SELECT FORM_NAME, ELEMENT_NAME, RESPONSE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_ASSESSMENT_FORMS WHERE RESIDENT_ID = {selected_resident} ORDER BY EVENT_DATE DESC LIMIT 20)
                    )
                    SELECT 
                        'PROGRESS NOTES: ' || (SELECT notes_text FROM resident_notes) ||
                        ' MEDICATIONS: ' || (SELECT meds_text FROM resident_meds) ||
                        ' OBSERVATIONS: ' || (SELECT obs_text FROM resident_obs) ||
                        ' ASSESSMENT FORMS: ' || (SELECT forms_text FROM resident_forms) as CONTEXT
                    """
                    context_result = execute_query(context_query, session)
                    resident_context = context_result[0]['CONTEXT'] if context_result else ""
                    
                    indicators_df = execute_query_df("""
                        SELECT INDICATOR_ID, INDICATOR_NAME, DEFINITION, KEYWORDS, INCLUSION_CRITERIA
                        FROM AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS
                        ORDER BY INDICATOR_ID
                    """, session)
                    
                    regex_start = time.time()
                    regex_results = run_regex_detection(resident_context, indicators_df)
                    regex_time = int((time.time() - regex_start) * 1000)
                    regex_detected_ids = {k for k, v in regex_results.items() if v['detected']}
                    
                    analysis_query = f"""
                    WITH rag_indicators AS (
                        SELECT LISTAGG(INDICATOR_ID || ' - ' || INDICATOR_NAME || ': ' || DEFINITION, ' || ') WITHIN GROUP (ORDER BY INDICATOR_ID) as indicators_text
                        FROM AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS
                    ),
                    prompt_template AS (
                        SELECT PROMPT_TEXT FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS WHERE VERSION_NUMBER = '{selected_version}'
                    )
                    SELECT 
                        SNOWFLAKE.CORTEX.COMPLETE(
                            '{selected_model}',
                            [
                                {{
                                    'role': 'user',
                                    'content': REPLACE(REPLACE(
                                        (SELECT PROMPT_TEXT FROM prompt_template),
                                        '{{resident_context}}', '{resident_context.replace("'", "''")[:50000]}'
                                    ), '{{rag_indicator_context}}', (SELECT indicators_text FROM rag_indicators))
                                }}
                            ],
                            {{
                                'max_tokens': 8192
                            }}
                        ) as RESPONSE
                    """
                    
                    result = execute_query(analysis_query, session)
                    claude_time = int((time.time() - start_time) * 1000)
                    
                    if result:
                        response_text = result[0]['RESPONSE']
                        
                        claude_indicators = {}
                        claude_detected_ids = set()
                        
                        try:
                            if isinstance(response_text, str) and response_text.strip().startswith('{') and '"choices"' in response_text:
                                wrapper = json.loads(response_text)
                                if 'choices' in wrapper and len(wrapper['choices']) > 0:
                                    response_text = wrapper['choices'][0].get('messages', wrapper['choices'][0].get('message', wrapper['choices'][0].get('text', '')))
                            
                            json_start = response_text.find('{')
                            json_end = response_text.rfind('}') + 1
                            if json_start >= 0 and json_end > json_start:
                                json_str = response_text[json_start:json_end]
                                parsed = json.loads(json_str)
                                
                                if 'indicators' in parsed:
                                    for ind in parsed['indicators']:
                                        ind_id = ind.get('deficit_id', '')
                                        claude_indicators[ind_id] = {
                                            'deficit_id': ind_id,
                                            'deficit_name': ind.get('deficit_name', ''),
                                            'detected': True,
                                            'confidence': ind.get('confidence', 'low'),
                                            'reasoning': ind.get('reasoning', ''),
                                            'evidence': ind.get('evidence', []),
                                            'temporal_status': ind.get('temporal_status', {}),
                                            'requires_review': ind.get('requires_review', False)
                                        }
                                        claude_detected_ids.add(ind_id)
                        except json.JSONDecodeError as e:
                            st.warning(f"Could not parse Claude response: {e}")
                        
                        claude_active = len(claude_detected_ids)
                        regex_active = len(regex_detected_ids)
                        claude_dri_score = calculate_dri_score(claude_active)
                        regex_dri_score = calculate_dri_score(regex_active)
                        claude_severity = get_severity_band(claude_dri_score)
                        regex_severity = get_severity_band(regex_dri_score)
                        
                        st.markdown("---")
                        st.subheader("📊 DRI Score Comparison")
                        
                        col_c, col_r, col_d = st.columns(3)
                        
                        with col_c:
                            st.markdown("### Claude LLM")
                            st.metric("Active Indicators", claude_active)
                            st.metric("DRI Score", f"{claude_dri_score:.4f}")
                            severity_color = get_severity_color(claude_severity)
                            st.markdown(f"**Severity:** <span style='color:{severity_color}'>{claude_severity}</span>", unsafe_allow_html=True)
                            st.caption(f"Analysis time: {claude_time}ms")
                        
                        with col_r:
                            st.markdown("### Regex/Keywords")
                            st.metric("Active Indicators", regex_active)
                            st.metric("DRI Score", f"{regex_dri_score:.4f}")
                            regex_color = get_severity_color(regex_severity)
                            st.markdown(f"**Severity:** <span style='color:{regex_color}'>{regex_severity}</span>", unsafe_allow_html=True)
                            st.caption(f"Analysis time: {regex_time}ms")
                        
                        with col_d:
                            st.markdown("### Difference")
                            
                            only_claude = claude_detected_ids - regex_detected_ids
                            only_regex = regex_detected_ids - claude_detected_ids
                            both = claude_detected_ids & regex_detected_ids
                            
                            st.metric("Both Agree", len(both))
                            st.metric("Only Claude", len(only_claude), help="Claude detected, regex missed")
                            st.metric("Only Regex", len(only_regex), delta=f"-{len(only_regex)} potential FP", delta_color="inverse", help="Likely false positives")
                        
                        st.markdown("---")
                        st.subheader("📋 Detailed Indicator Comparison")
                        
                        all_detected = claude_detected_ids | regex_detected_ids
                        
                        agree_tab, claude_only_tab, regex_only_tab, raw_tab = st.tabs([
                            f"✅ Both Agree ({len(both)})", 
                            f"🟢 Claude Only ({len(only_claude)})", 
                            f"🔴 Regex Only ({len(only_regex)})",
                            "📝 Raw JSON"
                        ])
                        
                        with agree_tab:
                            if both:
                                for ind_id in sorted(both):
                                    claude_ind = claude_indicators.get(ind_id, {})
                                    regex_ind = regex_results.get(ind_id, {})
                                    
                                    confidence = claude_ind.get('confidence', 'N/A')
                                    conf_color = '#28a745' if confidence == 'high' else '#ffc107' if confidence == 'medium' else '#dc3545'
                                    
                                    with st.expander(f"✅ {ind_id} - {claude_ind.get('deficit_name', regex_ind.get('indicator_name', 'Unknown'))} ({confidence})"):
                                        col_cl, col_rx = st.columns(2)
                                        
                                        with col_cl:
                                            st.markdown("**Claude Analysis:**")
                                            st.markdown(f"""
                                            <div style="background-color: #d4edda; padding: 0.5rem; border-radius: 0.25rem; border-left: 4px solid {conf_color};">
                                                {claude_ind.get('reasoning', 'N/A')}
                                            </div>
                                            """, unsafe_allow_html=True)
                                            
                                            if claude_ind.get('evidence'):
                                                st.markdown("**Evidence:**")
                                                for ev in claude_ind['evidence'][:2]:
                                                    st.caption(f"{ev.get('source_table', 'N/A')}: {ev.get('text_excerpt', 'N/A')[:100]}...")
                                        
                                        with col_rx:
                                            st.markdown("**Regex Matches:**")
                                            st.markdown(f"""
                                            <div style="background-color: #d4edda; padding: 0.5rem; border-radius: 0.25rem;">
                                                Found {regex_ind.get('match_count', 0)} keyword matches
                                            </div>
                                            """, unsafe_allow_html=True)
                                            
                                            if regex_ind.get('matches'):
                                                st.markdown("**Matched text:**")
                                                for m in regex_ind['matches'][:2]:
                                                    st.caption(f"...{m}...")
                            else:
                                st.info("No indicators detected by both methods")
                        
                        with claude_only_tab:
                            if only_claude:
                                st.success("These indicators were detected by Claude's contextual analysis but missed by simple keyword matching.")
                                for ind_id in sorted(only_claude):
                                    claude_ind = claude_indicators.get(ind_id, {})
                                    confidence = claude_ind.get('confidence', 'N/A')
                                    conf_color = '#28a745' if confidence == 'high' else '#ffc107' if confidence == 'medium' else '#dc3545'
                                    
                                    with st.expander(f"🟢 {ind_id} - {claude_ind.get('deficit_name', 'Unknown')} ({confidence})"):
                                        st.markdown(f"""
                                        <div style="background-color: #d4edda; padding: 0.75rem; border-radius: 0.25rem; border-left: 4px solid {conf_color}; margin-bottom: 1rem;">
                                            <strong>Reasoning:</strong> {claude_ind.get('reasoning', 'N/A')}
                                        </div>
                                        """, unsafe_allow_html=True)
                                        
                                        if claude_ind.get('evidence'):
                                            st.markdown("**Evidence:**")
                                            for ev in claude_ind['evidence']:
                                                st.markdown(f"""
                                                <div style="background-color: #fff3cd; padding: 0.5rem; border-radius: 0.25rem; margin-bottom: 0.5rem; font-size: 0.85rem;">
                                                    <strong>Source:</strong> {ev.get('source_table', 'N/A')} | <strong>Date:</strong> {ev.get('event_date', 'N/A')}<br>
                                                    <em>{ev.get('text_excerpt', 'N/A')}</em>
                                                </div>
                                                """, unsafe_allow_html=True)
                            else:
                                st.info("No indicators detected only by Claude")
                        
                        with regex_only_tab:
                            if only_regex:
                                st.warning("These are likely **false positives** - regex matched keywords but Claude determined they don't indicate actual deficits.")
                                for ind_id in sorted(only_regex):
                                    regex_ind = regex_results.get(ind_id, {})
                                    
                                    with st.expander(f"🔴 {ind_id} - {regex_ind.get('indicator_name', 'Unknown')} (Potential False Positive)"):
                                        col_cl, col_rx = st.columns(2)
                                        
                                        with col_cl:
                                            st.markdown("**Claude Decision:**")
                                            st.markdown("""
                                            <div style="background-color: #f8d7da; padding: 0.5rem; border-radius: 0.25rem;">
                                                <strong>NOT DETECTED</strong> - Claude did not find sufficient evidence for this indicator.
                                            </div>
                                            """, unsafe_allow_html=True)
                                        
                                        with col_rx:
                                            st.markdown("**Regex Matches:**")
                                            st.markdown(f"""
                                            <div style="background-color: #fff3cd; padding: 0.5rem; border-radius: 0.25rem;">
                                                Found {regex_ind.get('match_count', 0)} keyword matches (likely out of context)
                                            </div>
                                            """, unsafe_allow_html=True)
                                            
                                            if regex_ind.get('matches'):
                                                st.markdown("**Matched text (false positive):**")
                                                for m in regex_ind['matches'][:3]:
                                                    st.caption(f"...{m}...")
                            else:
                                st.info("No false positives detected - regex did not flag anything Claude didn't")
                        
                        with raw_tab:
                            st.markdown("### Raw Claude JSON Response")
                            try:
                                json_start = response_text.find('{')
                                json_end = response_text.rfind('}') + 1
                                if json_start >= 0 and json_end > json_start:
                                    json_str = response_text[json_start:json_end]
                                    formatted_json = json.dumps(json.loads(json_str), indent=2)
                                    st.code(formatted_json, language="json")
                                else:
                                    st.code(response_text, language="text")
                            except:
                                st.code(response_text, language="text")
                    else:
                        st.error("No response from Claude")
                        
                except Exception as e:
                    st.error(f"Analysis failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())
    
    st.markdown("---")
    st.subheader("📈 Formula Reference")
    
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        st.markdown("""
        **DRI Score Formula:**
        ```
        DRI Score = Active Indicators / Total Indicators
        DRI Score = Active / 33
        ```
        
        **Severity Bands:**
        - **Low**: 0.0 - 0.2 (≤6 indicators)
        - **Medium**: 0.2001 - 0.4 (7-13 indicators)
        - **High**: 0.4001 - 0.6 (14-20 indicators)
        - **Very High**: 0.6001 - 1.0 (21-33 indicators)
        """)
    
    with col_f2:
        indicator_count = execute_query_df("""
            SELECT COUNT(*) as COUNT FROM AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS
        """, session)
        
        if indicator_count is not None and len(indicator_count) > 0:
            st.metric("Total DRI Indicators", indicator_count['COUNT'].iloc[0])
        
        st.markdown("""
        **Accuracy Metrics (Goal):**
        - Current Regex False Positive Rate: ~10%
        - Target Claude False Positive Rate: ~1%
        """)

else:
    st.error("Failed to connect to Snowflake")
