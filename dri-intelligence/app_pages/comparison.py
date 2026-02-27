"""
=============================================================================
DEMO-ONLY PAGE - Claude vs Regex Comparison
=============================================================================
This page is intended for DEMONSTRATION PURPOSES ONLY to show stakeholders
that Claude LLM analysis achieves significantly lower false positive rates
compared to the traditional regex/keyword matching approach.

TARGET STATE: This page will be REMOVED once the demo is complete and
stakeholders are convinced of the AI approach's superiority.

For ongoing quality metrics and model evaluation, use the "Quality Metrics"
page which integrates with Snowflake AI Observability.
=============================================================================
"""

import streamlit as st
import json
import re

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

session = get_snowflake_session()

TOTAL_DEFICITS = 33

st.warning("**Demo page** - This comparison tool is for demonstration purposes only. For ongoing quality metrics, use the Quality Metrics page.", icon=":material/science:")

if session:
    with st.expander("How to use this page", expanded=False, icon=":material/help:"):
        st.markdown("""
### Purpose
This page demonstrates the **accuracy improvement** of AI (Claude) over the traditional regex/keyword matching approach. It shows side-by-side comparison of DRI detection results.

### Why This Matters
The old regex system has a **~10% false positive rate** (e.g., flagging "patient's son has asthma" as the patient having asthma). The goal is to achieve **<1% false positives** with contextual AI analysis.

### How to Use
1. **Select a resident** to compare
2. **Choose an LLM model** (Claude 4.5 recommended)
3. **Select prompt version** to use
4. Review the **Resident context** to see the data being analyzed
5. Click **Run comparison** to execute both methods

### Understanding Results

**DRI Score Comparison Panel:**
- Shows active indicators, DRI score, and severity for each method
- Difference section highlights discrepancies

**Detailed Tabs:**
| Tab | Meaning |
|-----|---------|
| **Both Agree** | Indicators detected by both Claude AND regex (true positives) |
| **Claude Only** | Claude detected but regex missed (AI catching nuanced cases) |
| **Regex Only** | Regex flagged but Claude rejected (**likely false positives!**) |

### Interpreting False Positives
Items in the **Regex Only** tab are likely false positives that Claude correctly filtered out by understanding context:
- Family member references ("son has diabetes")
- Negated statements ("no signs of infection")
- Historical/resolved conditions

### Tips
- Large **Regex Only** counts indicate significant false positive reduction
- Check Claude's reasoning for each indicator to verify accuracy
- Use this data to demonstrate ROI of the AI approach to stakeholders
        """)

    st.caption("Compare DRI indicator detection and scores between Claude LLM analysis and the Regex/Rules based approach. This helps measure accuracy improvements and identify false positive reductions.")

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
    colors = {"Low": "green", "Medium": "orange", "High": "red", "Very High": "violet"}
    return colors.get(band, "gray")

def run_regex_detection(text: str, keyword_df) -> dict:
    results = {}
    text_lower = text.lower()
    text_clean = re.sub(r'[^\w\s]', ' ', text_lower)
    
    negation_before = [
        "no", "no symptoms of", "nil signs of", "does not require",
        "-ve", "doesn't have", "neg", "negative", "denies", "no evidence of"
    ]
    negation_after = ["absent", "doesn't have", "neg", "nad", "ruled out"]
    
    for _, row in keyword_df.iterrows():
        deficit_id = row['DRI_DEFICIT_ID']
        deficit_name = row['DEFICIT_NAME']
        keywords_raw = row['KEYWORDS']
        
        keywords = []
        if keywords_raw is not None:
            if isinstance(keywords_raw, list):
                keywords = keywords_raw
            elif isinstance(keywords_raw, str):
                keywords_raw = keywords_raw.strip()
                if keywords_raw.startswith('['):
                    try:
                        keywords = json.loads(keywords_raw)
                    except:
                        keywords = [k.strip().strip('"\'') for k in keywords_raw[1:-1].split(',')]
                else:
                    keywords = [k.strip() for k in keywords_raw.split(',')]
        
        matches = []
        matched_keywords = []
        
        for kw in keywords:
            kw_lower = str(kw).lower().strip()
            if len(kw_lower) < 2:
                continue
                
            pattern = re.compile(rf'\b{re.escape(kw_lower)}\b')
            for match in pattern.finditer(text_clean):
                start, end = match.span()
                
                before_context = text_clean[max(0, start-50):start].strip()
                after_context = text_clean[end:end+50].strip()
                
                negated_before = any(re.search(rf'\b{re.escape(phrase)}\b', before_context) for phrase in negation_before)
                negated_after = any(re.search(rf'\b{re.escape(phrase)}\b', after_context) for phrase in negation_after)
                
                if not negated_before and not negated_after:
                    context_start = max(0, start - 30)
                    context_end = min(len(text), end + 30)
                    matches.append(text[context_start:context_end])
                    matched_keywords.append(kw_lower)
        
        unique_matches = list(set(matched_keywords))
        
        results[deficit_id] = {
            'indicator_id': deficit_id,
            'indicator_name': deficit_name,
            'detected': len(unique_matches) > 0,
            'match_count': len(unique_matches),
            'matches': matches[:5],
            'matched_keywords': unique_matches[:5]
        }
    
    return results

if session:
    st.caption("Compare DRI indicator detection and scores between Claude LLM analysis and the Regex/Rules based approach. This helps measure accuracy improvements and identify false positive reductions.")
    
    cfg_col1, cfg_col2, cfg_col3 = st.columns(3)
    
    with cfg_col1:
        residents = execute_query_df("""
            SELECT DISTINCT RESIDENT_ID 
            FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES
            ORDER BY RESIDENT_ID
        """, session)
        
        if residents is not None and len(residents) > 0:
            selected_resident = st.selectbox(
                "Select resident",
                residents['RESIDENT_ID'].tolist(),
                help="Choose a resident to compare"
            )
        else:
            selected_resident = st.number_input("Resident ID", value=871, min_value=1)
    
    with cfg_col2:
        model_options = [
            'claude-haiku-4-6',
            'claude-opus-4-6',
            'claude-sonnet-4-6',
            'claude-sonnet-4-5',
            'claude-opus-4-5',
            'claude-haiku-4-5',
            'claude-3-5-sonnet',
            'claude-3-7-sonnet',
            'mistral-large2',
            'llama3.1-70b'
        ]
        selected_model = st.selectbox("LLM model for analysis", model_options)
    
    with cfg_col3:
        prompt_versions = execute_query_df("""
            SELECT VERSION_NUMBER, IS_ACTIVE 
            FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS
            ORDER BY CREATED_TIMESTAMP DESC
        """, session)
        
        if prompt_versions is not None and len(prompt_versions) > 0:
            version_options = prompt_versions['VERSION_NUMBER'].tolist()
            active_version = prompt_versions[prompt_versions['IS_ACTIVE'] == True]['VERSION_NUMBER'].tolist()
            default_idx = version_options.index(active_version[0]) if active_version else 0
            selected_version = st.selectbox("Prompt version", version_options, index=default_idx)
        else:
            selected_version = "v1.0"
    
    with st.expander("Resident context", expanded=True, icon=":material/description:"):
        preview_query = f"""
            WITH notes AS (
                SELECT LISTAGG(LEFT(PROGRESS_NOTE, 400), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as txt
                FROM (SELECT PROGRESS_NOTE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES WHERE RESIDENT_ID = {selected_resident} ORDER BY EVENT_DATE DESC LIMIT 15)
            ),
            meds AS (
                SELECT LISTAGG(MED_NAME || ' (' || MED_STATUS || ')', ', ') as txt
                FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION WHERE RESIDENT_ID = {selected_resident}
            ),
            obs AS (
                SELECT LISTAGG(CHART_NAME || ': ' || LEFT(OBSERVATION_VALUE, 100), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as txt
                FROM (SELECT CHART_NAME, OBSERVATION_VALUE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS WHERE RESIDENT_ID = {selected_resident} ORDER BY EVENT_DATE DESC LIMIT 30)
            ),
            forms AS (
                SELECT LISTAGG(FORM_NAME || ': ' || ELEMENT_NAME || '=' || LEFT(RESPONSE, 300), ' | ') as txt
                FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_ASSESSMENT_FORMS WHERE RESIDENT_ID = {selected_resident} AND RESPONSE IS NOT NULL AND TRIM(RESPONSE) != ''
            )
            SELECT 
                'PROGRESS NOTES:\n' || COALESCE((SELECT txt FROM notes), 'None') ||
                '\n\nMEDICATIONS:\n' || COALESCE((SELECT txt FROM meds), 'None') ||
                '\n\nOBSERVATIONS:\n' || COALESCE((SELECT txt FROM obs), 'None') ||
                '\n\nASSESSMENT FORMS:\n' || COALESCE((SELECT txt FROM forms), 'None') as CONTEXT
        """
        preview_result = execute_query(preview_query, session)
        if preview_result:
            st.text_area("Context", preview_result[0]['CONTEXT'], height=300, label_visibility="collapsed")
    
    st.subheader("Comparison results")
    
    run_comparison = st.button("Run comparison", type="primary", icon=":material/compare_arrows:")
    
    if run_comparison:
        import time
        
        with st.spinner(f"Running analysis for Resident {selected_resident}..."):
            start_time = time.time()
            
            try:
                context_query = f"""
                WITH resident_notes AS (
                    SELECT LISTAGG(LEFT(PROGRESS_NOTE, 500) || ' [' || NOTE_TYPE || ']', ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC NULLS LAST) as notes_text
                    FROM (SELECT PROGRESS_NOTE, NOTE_TYPE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES WHERE RESIDENT_ID = {selected_resident} ORDER BY EVENT_DATE DESC NULLS LAST LIMIT 20)
                ),
                resident_meds AS (
                    SELECT LISTAGG(MED_NAME || ' (' || MED_STATUS || ')', ', ') as meds_text
                    FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION WHERE RESIDENT_ID = {selected_resident}
                ),
                resident_obs AS (
                    SELECT LISTAGG(CHART_NAME || ': ' || LEFT(OBSERVATION_VALUE, 200), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC NULLS LAST) as obs_text
                    FROM (SELECT CHART_NAME, OBSERVATION_VALUE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS WHERE RESIDENT_ID = {selected_resident} ORDER BY EVENT_DATE DESC NULLS LAST LIMIT 40)
                ),
                resident_forms AS (
                    SELECT LISTAGG(FORM_NAME || ': ' || ELEMENT_NAME || '=' || LEFT(RESPONSE, 400), ' | ') as forms_text
                    FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_ASSESSMENT_FORMS WHERE RESIDENT_ID = {selected_resident} AND RESPONSE IS NOT NULL AND TRIM(RESPONSE) != ''
                )
                SELECT 
                    'PROGRESS NOTES: ' || (SELECT notes_text FROM resident_notes) ||
                    ' MEDICATIONS: ' || (SELECT meds_text FROM resident_meds) ||
                    ' OBSERVATIONS: ' || (SELECT obs_text FROM resident_obs) ||
                    ' ASSESSMENT FORMS: ' || (SELECT forms_text FROM resident_forms) as CONTEXT
                """
                context_result = execute_query(context_query, session)
                resident_context = context_result[0]['CONTEXT'] if context_result else ""
                
                keyword_df = execute_query_df("""
                    SELECT DRI_DEFICIT_ID, DEFICIT_NAME, KEYWORDS
                    FROM AGEDCARE.AGEDCARE.DRI_KEYWORD_MASTER_LIST
                    ORDER BY DRI_DEFICIT_ID
                """, session)
                
                if keyword_df is None or len(keyword_df) == 0:
                    st.warning("Keyword master list not available. Regex comparison will be skipped. Only Claude analysis will run.", icon=":material/warning:")
                    regex_results = {}
                    regex_detected_ids = set()
                    regex_time = 0
                else:
                    regex_start = time.time()
                    regex_results = run_regex_detection(resident_context, keyword_df)
                    regex_time = int((time.time() - regex_start) * 1000)
                    regex_detected_ids = {k for k, v in regex_results.items() if v['detected']}
                
                analysis_query = f"""
                WITH dri_rules AS (
                    SELECT LISTAGG(DEFICIT_ID || ' - ' || DEFICIT_NAME || ': ' || COALESCE(DEFINITION, ARRAY_TO_STRING(KEYWORDS, ', ')), ' || ') WITHIN GROUP (ORDER BY DEFICIT_ID) as indicators_text
                    FROM AGEDCARE.AGEDCARE.DRI_RULES
                    WHERE IS_CURRENT_VERSION = TRUE AND IS_ACTIVE = TRUE
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
                                ), '{{rag_indicator_context}}', (SELECT indicators_text FROM dri_rules))
                            }}
                        ],
                        {{
                            'max_tokens': 16384
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
                        st.warning(f"Could not parse Claude response: {e}", icon=":material/warning:")
                    
                    claude_active = len(claude_detected_ids)
                    regex_active = len(regex_detected_ids)
                    claude_dri_score = calculate_dri_score(claude_active)
                    regex_dri_score = calculate_dri_score(regex_active)
                    claude_severity = get_severity_band(claude_dri_score)
                    regex_severity = get_severity_band(regex_dri_score)
                    
                    st.subheader("DRI score comparison")
                    
                    col_c, col_r, col_d = st.columns(3)
                    
                    with col_c:
                        with st.container(border=True):
                            st.markdown("### Claude LLM")
                            st.metric("Active indicators", claude_active)
                            st.metric("DRI score", f"{claude_dri_score:.4f}")
                            st.badge(claude_severity, color=get_severity_color(claude_severity))
                            st.caption(f"Analysis time: {claude_time}ms")
                    
                    with col_r:
                        with st.container(border=True):
                            st.markdown("### Regex/Keywords")
                            st.metric("Active indicators", regex_active)
                            st.metric("DRI score", f"{regex_dri_score:.4f}")
                            st.badge(regex_severity, color=get_severity_color(regex_severity))
                            st.caption(f"Analysis time: {regex_time}ms")
                    
                    with col_d:
                        with st.container(border=True):
                            st.markdown("### Difference")
                            
                            # Both systems now use the same D001-D033 identifiers, so comparison is direct
                            both = claude_detected_ids & regex_detected_ids
                            only_claude = claude_detected_ids - regex_detected_ids
                            only_regex = regex_detected_ids - claude_detected_ids
                            
                            st.metric("Both agree", len(both))
                            st.metric("Only Claude", len(only_claude), help="Claude detected, regex missed")
                            st.metric("Only Regex", len(only_regex), delta=f"-{len(only_regex)} potential FP", delta_color="inverse", help="Likely false positives")
                    
                    st.subheader("Detailed indicator comparison")
                    
                    all_detected = claude_detected_ids | regex_detected_ids
                    
                    agree_tab, claude_only_tab, regex_only_tab, raw_tab = st.tabs([
                        f"Both agree ({len(both)})", 
                        f"Claude only ({len(only_claude)})", 
                        f"Regex only ({len(only_regex)})",
                        "Raw JSON"
                    ])
                    
                    with agree_tab:
                        if both:
                            for ind_id in sorted(both):
                                claude_ind = claude_indicators.get(ind_id, {})
                                regex_ind = regex_results.get(ind_id, {})
                                
                                confidence = claude_ind.get('confidence', 'N/A')
                                
                                with st.expander(f"{ind_id} - {claude_ind.get('deficit_name', regex_ind.get('indicator_name', 'Unknown'))} ({confidence})", icon=":material/check_circle:"):
                                    col_cl, col_rx = st.columns(2)
                                    
                                    with col_cl:
                                        st.markdown("**Claude analysis:**")
                                        with st.container(border=True):
                                            st.write(claude_ind.get('reasoning', 'N/A'))
                                        
                                        if claude_ind.get('evidence'):
                                            st.markdown("**Evidence:**")
                                            for ev in claude_ind['evidence'][:2]:
                                                st.caption(f"{ev.get('source_table', 'N/A')}: {ev.get('text_excerpt', 'N/A')[:100]}...")
                                    
                                    with col_rx:
                                        st.markdown("**Regex matches:**")
                                        with st.container(border=True):
                                            st.write(f"Found {regex_ind.get('match_count', 0)} keyword matches")
                                        
                                        if regex_ind.get('matches'):
                                            st.markdown("**Matched text:**")
                                            for m in regex_ind['matches'][:2]:
                                                st.caption(f"...{m}...")
                        else:
                            st.info("No indicators detected by both methods", icon=":material/info:")
                    
                    with claude_only_tab:
                        if only_claude:
                            st.success("These indicators were detected by Claude's contextual analysis but missed by simple keyword matching.", icon=":material/check_circle:")
                            for ind_id in sorted(only_claude):
                                claude_ind = claude_indicators.get(ind_id, {})
                                confidence = claude_ind.get('confidence', 'N/A')
                                
                                with st.expander(f"{ind_id} - {claude_ind.get('deficit_name', 'Unknown')} ({confidence})", icon=":material/add_circle:"):
                                    with st.container(border=True):
                                        st.markdown(f"**Reasoning:** {claude_ind.get('reasoning', 'N/A')}")
                                    
                                    if claude_ind.get('evidence'):
                                        st.markdown("**Evidence:**")
                                        for ev in claude_ind['evidence']:
                                            with st.container(border=True):
                                                st.caption(f"Source: {ev.get('source_table', 'N/A')} | Date: {ev.get('event_date', 'N/A')}")
                                                st.caption(f"_{ev.get('text_excerpt', 'N/A')}_")
                        else:
                            st.info("No indicators detected only by Claude", icon=":material/info:")
                    
                    with regex_only_tab:
                        if only_regex:
                            st.warning("These are likely **false positives** - regex matched keywords but Claude determined they don't indicate actual deficits.", icon=":material/warning:")
                            for ind_id in sorted(only_regex):
                                regex_ind = regex_results.get(ind_id, {})
                                
                                with st.expander(f"{ind_id} - {regex_ind.get('indicator_name', 'Unknown')} (Potential false positive)", icon=":material/error:"):
                                    col_cl, col_rx = st.columns(2)
                                    
                                    with col_cl:
                                        st.markdown("**Claude decision:**")
                                        st.error("**Not detected** - Claude did not find sufficient evidence for this indicator.", icon=":material/close:")
                                    
                                    with col_rx:
                                        st.markdown("**Regex matches:**")
                                        st.warning(f"Found {regex_ind.get('match_count', 0)} keyword matches (likely out of context)", icon=":material/warning:")
                                        
                                        if regex_ind.get('matches'):
                                            st.markdown("**Matched text (false positive):**")
                                            for m in regex_ind['matches'][:3]:
                                                st.caption(f"...{m}...")
                        else:
                            st.info("No false positives detected - regex did not flag anything Claude didn't", icon=":material/info:")
                    
                    with raw_tab:
                        st.markdown("### Raw Claude JSON response")
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
                    st.error("No response from Claude", icon=":material/error:")
                    
            except Exception as e:
                st.error(f"Analysis failed: {e}", icon=":material/error:")
                import traceback
                st.code(traceback.format_exc())
    
    st.subheader("Formula reference")
    
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        with st.container(border=True):
            st.markdown("""
            **DRI score formula:**
            ```
            DRI Score = Active Indicators / Total Indicators
            DRI Score = Active / 33
            ```
            
            **Severity bands:**
            - **Low**: 0.0 - 0.2 (≤6 indicators)
            - **Medium**: 0.2001 - 0.4 (7-13 indicators)
            - **High**: 0.4001 - 0.6 (14-20 indicators)
            - **Very High**: 0.6001 - 1.0 (21-33 indicators)
            """)
    
    with col_f2:
        with st.container(border=True):
            indicator_count = execute_query_df("""
                SELECT COUNT(*) as COUNT FROM AGEDCARE.AGEDCARE.DRI_RULES WHERE IS_CURRENT_VERSION = TRUE AND IS_ACTIVE = TRUE
            """, session)
            
            if indicator_count is not None and len(indicator_count) > 0:
                st.metric("Total DRI indicators", indicator_count['COUNT'].iloc[0])
            
            st.markdown("""
            **Accuracy metrics (goal):**
            - Current Regex False Positive Rate: ~10%
            - Target Claude False Positive Rate: ~1%
            """)

else:
    st.error("Failed to connect to Snowflake", icon=":material/error:")
