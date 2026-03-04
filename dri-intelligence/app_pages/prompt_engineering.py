"""DRI Intelligence - Prompt Engineering

Interactive page for testing and tuning LLM prompts:
- Select resident (auto-detects facility)
- View and override production settings
- Edit resident data and prompts
- Run single analysis and view JSON results
- Save new prompt versions

Uses Snowflake Cortex Complete for LLM inference.
Supports adaptive token sizing based on context length.
"""

import streamlit as st
import json

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query
from src.dri_analysis import get_rag_indicators

session = get_snowflake_session()

if session:
    with st.expander("How to use this page", expanded=False, icon=":material/help:"):
        st.markdown("""
### Purpose
This is the **prompt development environment** for testing and tuning LLM prompts before deploying them to production.

### Terminology
- **Deficit**: A clinical condition being tracked (D001-D032)
- **Occurrence**: Evidence that a deficit may exist (individual detection)
- **Flag**: When a deficit becomes active after approval

### Workflow
1. **Select a resident** - Facility is auto-detected from resident data
2. **Review production settings** - See current prompt version, model, thresholds, and rules
3. **Override settings for testing** - Temporarily change any setting without affecting production
4. **Edit resident data** - Modify the resident context to test specific scenarios
5. **Edit the prompt template** - Modify the prompt text directly
6. **Run analysis** - Test your changes on the selected resident
7. **Save as new version** - When satisfied, save as a new prompt version

### Key Features
| Feature | Description |
|---------|-------------|
| **Auto-detect facility** | Resident selection automatically determines the aged care facility |
| **Editable resident data** | Modify context to test edge cases or specific scenarios |
| **Production settings summary** | See exactly what's running in production |
| **Override controls** | Test different models, prompts, thresholds without changing production |
| **Adaptive token sizing** | Automatically uses larger token limit for residents with more data |
| **Deficit context in results** | Shows existing occurrences, flagged status, and threshold impact for each detected deficit |

### Results Section
For each detected deficit, the results now show:
- **Already flagged**: Indicates if deficit is already active with expiry date
- **Prior occurrences**: Count and dates of approved occurrences within the lookback window
- **Threshold status**: Shows "X of Y occurrences" toward threshold
- **Will flag prediction**: Indicates if approving will meet threshold and flag the deficit

### Variable Placeholders
The prompt template includes these variables that get replaced at runtime:
- `{client_form_mappings}` - Client-specific form field mappings
- `{resident_context}` - All resident data (notes, meds, observations, forms)
- `{rag_indicator_context}` - DRI rules (deficit definitions) from the DRI_RULES table
        """)
    
    st.caption("Test and tune LLM prompts for DRI deficit detection. Deficits (D001-D032) are the clinical conditions tracked by DRI.")

@st.cache_data(ttl=300)
def load_residents_with_facility(_session):
    return execute_query_df("""
        SELECT DISTINCT n.RESIDENT_ID, n.SYSTEM_KEY as FACILITY_KEY
        FROM ACTIVE_RESIDENT_NOTES n
        WHERE n.SYSTEM_KEY IS NOT NULL
        ORDER BY n.RESIDENT_ID
    """, _session)

@st.cache_data(ttl=300)
def load_production_settings(_session, facility_key):
    result = execute_query(f"""
        SELECT 
            CONFIG_JSON:production_settings:prompt_version::VARCHAR as PROMPT_VERSION,
            CONFIG_JSON:production_settings:model::VARCHAR as MODEL,
            CONFIG_JSON:client_settings:context_threshold::NUMBER as CONTEXT_THRESHOLD
        FROM DRI_CLIENT_CONFIG 
        WHERE CLIENT_SYSTEM_KEY = '{facility_key}' AND IS_ACTIVE = TRUE
        LIMIT 1
    """, _session)
    if not result:
        result = execute_query("""
            SELECT 
                CONFIG_JSON:production_settings:prompt_version::VARCHAR as PROMPT_VERSION,
                CONFIG_JSON:production_settings:model::VARCHAR as MODEL,
                CONFIG_JSON:client_settings:context_threshold::NUMBER as CONTEXT_THRESHOLD
            FROM DRI_CLIENT_CONFIG 
            WHERE IS_ACTIVE = TRUE
            LIMIT 1
        """, _session)
    return result[0] if result else None

@st.cache_data(ttl=300)
def load_prompt_versions(_session):
    return execute_query_df("""
        SELECT VERSION_NUMBER, IS_ACTIVE, DESCRIPTION, CREATED_TIMESTAMP
        FROM DRI_PROMPT_VERSIONS
        ORDER BY CREATED_TIMESTAMP DESC
    """, _session)

@st.cache_data(ttl=300)
def load_prompt_text(version, _session):
    return execute_query_df(f"""
        SELECT PROMPT_TEXT 
        FROM DRI_PROMPT_VERSIONS
        WHERE VERSION_NUMBER = '{version}'
    """, _session)

@st.cache_data(ttl=300)
def load_client_rule_assignments(_session, facility_key):
    return execute_query_df(f"""
        SELECT DEFICIT_ID, RULE_VERSION
        FROM DRI_CLIENT_RULE_ASSIGNMENTS
        WHERE CLIENT_SYSTEM_KEY = '{facility_key}'
    """, _session)

@st.cache_data(ttl=300)
def load_all_rule_versions(_session):
    return execute_query_df("""
        SELECT DEFICIT_ID, 
               MAX(CASE WHEN IS_CURRENT_VERSION = TRUE THEN DEFICIT_NAME END) as DEFICIT_NAME,
               VERSION_NUMBER
        FROM DRI_RULES
        GROUP BY DEFICIT_ID, VERSION_NUMBER
        ORDER BY DEFICIT_ID, VERSION_NUMBER DESC
    """, _session)

@st.cache_data(ttl=300)
def load_deficit_context(_session, resident_id):
    """Load existing deficit status and occurrences for a resident."""
    rules = execute_query_df("""
        SELECT DEFICIT_ID, DEFICIT_NAME, DEFICIT_TYPE, 
               COALESCE(RULES_JSON[0]:threshold::NUMBER, 1) as THRESHOLD,
               CASE WHEN LOOKBACK_DAYS_HISTORIC = 'all' OR LOOKBACK_DAYS_HISTORIC IS NULL THEN 9999 
               ELSE TRY_TO_NUMBER(LOOKBACK_DAYS_HISTORIC) END as LOOKBACK_DAYS
        FROM DRI_RULES
        WHERE IS_CURRENT_VERSION = TRUE AND IS_ACTIVE = TRUE
    """, _session)
    
    occurrences = execute_query_df(f"""
        SELECT DEFICIT_ID, OCCURRENCE_DATE, EVIDENCE_TEXT
        FROM DRI_INDICATOR_OCCURRENCES
        WHERE RESIDENT_ID = {resident_id}
        ORDER BY DEFICIT_ID, OCCURRENCE_DATE DESC
    """, _session)
    
    active_flags = execute_query_df(f"""
        SELECT DEFICIT_ID, DECISION_TYPE, EXPIRY_DATE, DECISION_DATE
        FROM DRI_CLINICAL_DECISIONS
        WHERE RESIDENT_ID = {resident_id} AND STATUS = 'ACTIVE' AND DECISION_TYPE = 'CONFIRMED'
    """, _session)
    
    context = {}
    if rules is not None:
        for _, rule in rules.iterrows():
            deficit_id = rule['DEFICIT_ID']
            lookback_days = int(rule['LOOKBACK_DAYS']) if rule['LOOKBACK_DAYS'] else 9999
            threshold = int(rule['THRESHOLD']) if rule['THRESHOLD'] else 1
            
            occ_list = []
            if occurrences is not None:
                deficit_occs = occurrences[occurrences['DEFICIT_ID'] == deficit_id]
                from datetime import datetime, timedelta
                cutoff = datetime.now().date() - timedelta(days=lookback_days)
                for _, occ in deficit_occs.iterrows():
                    occ_date = occ['OCCURRENCE_DATE']
                    if hasattr(occ_date, 'date'):
                        occ_date = occ_date.date()
                    if occ_date >= cutoff:
                        occ_list.append(str(occ_date))
            
            is_flagged = False
            expiry_date = None
            if active_flags is not None:
                flag_row = active_flags[active_flags['DEFICIT_ID'] == deficit_id]
                if len(flag_row) > 0:
                    is_flagged = True
                    expiry_date = flag_row['EXPIRY_DATE'].iloc[0]
            
            context[deficit_id] = {
                'threshold': threshold,
                'lookback_days': lookback_days,
                'occurrence_count': len(occ_list),
                'occurrence_dates': occ_list,
                'is_flagged': is_flagged,
                'expiry_date': expiry_date,
                'deficit_type': rule['DEFICIT_TYPE']
            }
    return context

@st.cache_data(ttl=300)
def load_resident_context(_session, resident_id):
    context_query = f"""
        WITH notes AS (
            SELECT LISTAGG(LEFT(PROGRESS_NOTE, 400) || ' [' || NOTE_TYPE || ']', ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as txt
            FROM (SELECT PROGRESS_NOTE, NOTE_TYPE, EVENT_DATE FROM ACTIVE_RESIDENT_NOTES WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 15)
        ),
        meds AS (
            SELECT LISTAGG(MED_NAME || ' (' || MED_STATUS || ')', ', ') as txt
            FROM ACTIVE_RESIDENT_MEDICATION WHERE RESIDENT_ID = {resident_id}
        ),
        obs AS (
            SELECT LISTAGG(CHART_NAME || ': ' || LEFT(OBSERVATION_VALUE, 100), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as txt
            FROM (SELECT CHART_NAME, OBSERVATION_VALUE, EVENT_DATE FROM ACTIVE_RESIDENT_OBSERVATIONS WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 30)
        ),
        forms AS (
            SELECT LISTAGG(FORM_NAME || ': ' || ELEMENT_NAME || '=' || LEFT(RESPONSE, 100), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as txt
            FROM (SELECT FORM_NAME, ELEMENT_NAME, RESPONSE, EVENT_DATE FROM ACTIVE_RESIDENT_ASSESSMENT_FORMS WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 20)
        ),
        medical_profile AS (
            SELECT COALESCE(SPECIAL_NEEDS, '') || ' | Allergies: ' || COALESCE(ALLERGIES, 'None') || ' | Diet: ' || COALESCE(DIET, 'Standard') as txt
            FROM ACTIVE_RESIDENT_MEDICAL_PROFILE WHERE RESIDENT_ID = {resident_id}
        ),
        obs_groups AS (
            SELECT LISTAGG(CHART_NAME || ' (' || OBSERVATION_STATUS || '): ' || COALESCE(OBSERVATION_TYPE, '') || ' - ' || COALESCE(OBSERVATION_LOCATION, '') || ' - ' || COALESCE(OBSERVATION_DESCRIPTION, ''), ' | ') as txt
            FROM ACTIVE_RESIDENT_OBSERVATION_GROUP WHERE RESIDENT_ID = {resident_id}
        )
        SELECT 
            'MEDICAL PROFILE (DIAGNOSES - PRIMARY SOURCE): ' || COALESCE((SELECT txt FROM medical_profile), 'None') ||
            '

PROGRESS NOTES: ' || COALESCE((SELECT txt FROM notes), 'None') ||
            '

MEDICATIONS: ' || COALESCE((SELECT txt FROM meds), 'None') ||
            '

OBSERVATIONS: ' || COALESCE((SELECT txt FROM obs), 'None') ||
            '

OBSERVATION GROUPS (Wounds/Pain Charts): ' || COALESCE((SELECT txt FROM obs_groups), 'None') ||
            '

ASSESSMENT FORMS: ' || COALESCE((SELECT txt FROM forms), 'None') as CONTEXT
    """
    result = execute_query(context_query, _session)
    return result[0]['CONTEXT'] if result else ""

if session:
    st.subheader("1. Select Resident")
    
    residents = load_residents_with_facility(session)
    
    if residents is not None and len(residents) > 0:
        col_res, col_fac = st.columns([2, 1])
        with col_res:
            resident_list = residents['RESIDENT_ID'].tolist()
            selected_resident = st.selectbox(
                "Resident",
                resident_list,
                help="Choose a resident to analyze"
            )
        with col_fac:
            facility_row = residents[residents['RESIDENT_ID'] == selected_resident]
            detected_facility = facility_row['FACILITY_KEY'].iloc[0] if len(facility_row) > 0 else "UNKNOWN"
            st.text_input("Facility (auto-detected)", value=detected_facility, disabled=True)
    else:
        selected_resident = st.number_input("Resident ID", value=871, min_value=1)
        detected_facility = "DEMO_CLIENT_871"
    
    st.markdown("---")
    
    st.subheader("2. Current Production Settings")
    
    prod_settings = load_production_settings(session, detected_facility)
    prompt_versions = load_prompt_versions(session)
    client_assignments = load_client_rule_assignments(session, detected_facility)
    all_rule_versions = load_all_rule_versions(session)
    
    if prod_settings:
        prod_prompt = prod_settings['PROMPT_VERSION'] or 'v0001'
        prod_model = prod_settings['MODEL'] or 'claude-3-5-sonnet'
        prod_threshold = prod_settings['CONTEXT_THRESHOLD'] or 6000
    else:
        prod_prompt = 'v0001'
        prod_model = 'claude-3-5-sonnet'
        prod_threshold = 6000
    
    if client_assignments is not None and len(client_assignments) > 0:
        assignment_dict = dict(zip(client_assignments['DEFICIT_ID'], client_assignments['RULE_VERSION']))
    else:
        assignment_dict = {}
    
    with st.container(border=True):
        st.caption("These are the current production settings for this facility")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Prompt Version", prod_prompt)
        with col2:
            st.metric("LLM Model", prod_model)
        with col3:
            st.metric("Context Threshold", f"{prod_threshold:,}")
        with col4:
            st.metric("Active Rules", f"{len(assignment_dict)}")
    
    st.markdown("---")
    
    st.subheader("3. Test Configuration (Override for Testing)")
    st.caption("Changes here only affect this test run, not production")
    
    col_override1, col_override2 = st.columns(2)
    
    with col_override1:
        if prompt_versions is not None and len(prompt_versions) > 0:
            version_options = prompt_versions['VERSION_NUMBER'].tolist()
            try:
                default_idx = version_options.index(prod_prompt)
            except ValueError:
                default_idx = 0
            selected_version = st.selectbox(
                "Prompt Version",
                version_options,
                index=default_idx,
                help=f"Production: {prod_prompt}"
            )
            if selected_version != prod_prompt:
                st.caption(f"⚠️ Testing with different version (prod: {prod_prompt})")
        else:
            selected_version = prod_prompt
        
        model_options = [
            'claude-haiku-4-5',
            'claude-opus-4-6',
            'claude-sonnet-4-6',
            'claude-sonnet-4-5',
            'claude-opus-4-5',
            'claude-3-5-sonnet',
            'claude-3-7-sonnet',
            'mistral-large2',
            'llama3.1-70b',
            'llama3.1-405b',
            'llama3.3-70b',
            'snowflake-llama-3.3-70b',
            'deepseek-r1'
        ]
        try:
            model_default_idx = model_options.index(prod_model)
        except ValueError:
            model_default_idx = 0
        selected_model = st.selectbox(
            "LLM Model",
            model_options,
            index=model_default_idx,
            help=f"Production: {prod_model}"
        )
        if selected_model != prod_model:
            st.caption(f"⚠️ Testing with different model (prod: {prod_model})")
    
    with col_override2:
        context_threshold = st.number_input(
            "Context Threshold (chars)",
            value=int(prod_threshold),
            min_value=1000,
            max_value=50000,
            step=1000,
            help=f"Production: {prod_threshold}. Residents with context > threshold use large token mode."
        )
        if context_threshold != prod_threshold:
            st.caption(f"⚠️ Testing with different threshold (prod: {prod_threshold})")
    
    with st.expander("Deficit Rule Versions", expanded=False):
        st.caption("Select which version of each deficit rule to use for this test")
        
        if all_rule_versions is not None and len(all_rule_versions) > 0:
            unique_deficits = all_rule_versions[['DEFICIT_ID', 'DEFICIT_NAME']].drop_duplicates(subset=['DEFICIT_ID'])
            
            test_rule_assignments = {}
            
            num_cols = 4
            deficit_list = list(unique_deficits.iterrows())
            
            for i in range(0, len(deficit_list), num_cols):
                cols = st.columns(num_cols)
                for j, col in enumerate(cols):
                    if i + j < len(deficit_list):
                        _, deficit = deficit_list[i + j]
                        deficit_id = deficit['DEFICIT_ID']
                        deficit_name = deficit['DEFICIT_NAME'] or deficit_id
                        
                        versions_for_deficit = all_rule_versions[all_rule_versions['DEFICIT_ID'] == deficit_id]
                        version_options = versions_for_deficit['VERSION_NUMBER'].tolist()
                        
                        current_assignment = assignment_dict.get(deficit_id, version_options[0] if version_options else None)
                        
                        with col:
                            if version_options:
                                default_idx = version_options.index(current_assignment) if current_assignment in version_options else 0
                                selected_rule_version = st.selectbox(
                                    f"{deficit_id}",
                                    version_options,
                                    index=default_idx,
                                    key=f"rule_version_{deficit_id}",
                                    help=f"{deficit_name}"
                                )
                                test_rule_assignments[deficit_id] = selected_rule_version
            
            st.session_state['test_rule_assignments'] = test_rule_assignments
    
    st.markdown("---")
    
    st.subheader("4. Resident Data")
    st.caption("Edit the resident context below to test specific scenarios. Changes are not saved to the database.")
    
    db_resident_context = load_resident_context(session, selected_resident)
    
    if f'resident_context_{selected_resident}' not in st.session_state:
        st.session_state[f'resident_context_{selected_resident}'] = db_resident_context
    
    col_reload, col_char_count = st.columns([1, 3])
    with col_reload:
        if st.button("🔄 Reload from DB", use_container_width=True, help="Reset to original data from database"):
            st.session_state[f'resident_context_{selected_resident}'] = db_resident_context
            st.rerun()
    
    edited_resident_context = st.text_area(
        "Resident Context (editable)",
        value=st.session_state[f'resident_context_{selected_resident}'],
        height=250,
        key=f"context_editor_{selected_resident}",
        help="Edit this text to test how the LLM responds to different resident data"
    )
    
    st.session_state[f'resident_context_{selected_resident}'] = edited_resident_context
    
    context_length = len(edited_resident_context)
    if context_length > context_threshold:
        st.caption(f"📊 Context: {context_length:,} chars (large token mode)")
    else:
        st.caption(f"📊 Context: {context_length:,} chars (standard token mode)")
    
    preview_prompt_btn = st.button("👁️ Preview full prompt", use_container_width=True)
    
    if preview_prompt_btn:
        with st.spinner("Building full prompt..."):
            rules_query = """
                SELECT LISTAGG(
                    '=== ' || DEFICIT_ID || ' - ' || DEFICIT_NAME || ' ===' ||
                    '\\nDEFICIT_TYPE: ' || DEFICIT_TYPE || 
                    '\\nEXPIRY_DAYS: ' || COALESCE(TO_VARCHAR(EXPIRY_DAYS), '0') || 
                    '\\nRENEWAL_REMINDER_DAYS: ' || COALESCE(TO_VARCHAR(RENEWAL_REMINDER_DAYS), '7') ||
                    '\\nLOOKBACK_DAYS_HISTORIC: ' || COALESCE(LOOKBACK_DAYS_HISTORIC, 'all') ||
                    '\\nRULES_JSON: ' || COALESCE(TO_VARCHAR(RULES_JSON), '[]'),
                    '\\n\\n'
                ) WITHIN GROUP (ORDER BY DEFICIT_ID) as RULES_TEXT
                FROM DRI_RULES
                WHERE IS_CURRENT_VERSION = TRUE AND IS_ACTIVE = TRUE
            """
            rules_result = execute_query(rules_query, session)
            rules_text = rules_result[0]['RULES_TEXT'] if rules_result else ""
            
            prompt_data = load_prompt_text(selected_version, session)
            if prompt_data is not None and len(prompt_data) > 0:
                prompt_template = prompt_data['PROMPT_TEXT'].iloc[0]
            else:
                prompt_template = "No prompt found"
            
            full_prompt = prompt_template.replace('{resident_context}', edited_resident_context).replace('{rag_indicator_context}', rules_text)
            st.success(f"Full prompt length: {len(full_prompt):,} characters")
            st.text_area("Full prompt (exactly what gets sent to LLM)", full_prompt, height=400)
    
    st.markdown("---")
    
    st.subheader("5. Prompt Template")
    
    prompt_data = load_prompt_text(selected_version, session)
    if prompt_data is not None and len(prompt_data) > 0:
        current_prompt = prompt_data['PROMPT_TEXT'].iloc[0]
    else:
        current_prompt = "No prompt template found"
    
    edited_prompt = st.text_area(
        "Edit prompt template",
        current_prompt,
        height=300,
        help="Use {resident_context}, {rag_indicator_context}, and {client_form_mappings} as placeholders",
        label_visibility="collapsed"
    )
    
    col_save1, col_save2 = st.columns([2, 1])
    with col_save1:
        new_description = st.text_input("Version description", value="Updated prompt")
    with col_save2:
        max_version = execute_query("""
            SELECT MAX(VERSION_NUMBER) as MAX_VER FROM DRI_PROMPT_VERSIONS 
            WHERE VERSION_NUMBER LIKE 'v%'
        """, session)
        if max_version and max_version[0]['MAX_VER']:
            current_max = max_version[0]['MAX_VER']
            next_num = int(current_max[1:]) + 1
            next_version = f"v{next_num:04d}"
        else:
            next_version = "v0001"
        
        if st.button(f"💾 Save as {next_version}", use_container_width=True):
            escaped_prompt = edited_prompt.replace("'", "''")
            try:
                execute_query(f"""
                    INSERT INTO DRI_PROMPT_VERSIONS 
                    (VERSION_NUMBER, PROMPT_TEXT, DESCRIPTION, CREATED_BY, IS_ACTIVE)
                    VALUES ('{next_version}', '{escaped_prompt}', '{new_description}', 'user', FALSE)
                """, session)
                st.success(f"Saved as version {next_version}")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Failed to save: {e}")
    
    st.markdown("---")
    
    st.subheader("6. Run Analysis")
    
    run_button = st.button("🧪 Test Prompt", type="primary", use_container_width=True)
    
    if run_button:
        with st.spinner(f"Analyzing resident {selected_resident} with {selected_model}..."):
            import time
            start_time = time.time()
            
            try:
                CONTEXT_THRESHOLD = context_threshold
                if context_length > CONTEXT_THRESHOLD:
                    max_tokens = 16384
                    token_mode = "large"
                else:
                    max_tokens = 4096
                    token_mode = "standard"
                
                st.info(f"Context size: {context_length:,} chars → Using {token_mode} mode ({max_tokens:,} max tokens)")
                
                rules_query = """
                    SELECT LISTAGG(
                        '=== ' || DEFICIT_ID || ' - ' || DEFICIT_NAME || ' ===' ||
                        '\\nDEFICIT_TYPE: ' || DEFICIT_TYPE || 
                        '\\nEXPIRY_DAYS: ' || COALESCE(TO_VARCHAR(EXPIRY_DAYS), '0') || 
                        '\\nRENEWAL_REMINDER_DAYS: ' || COALESCE(TO_VARCHAR(RENEWAL_REMINDER_DAYS), '7') ||
                        '\\nLOOKBACK_DAYS_HISTORIC: ' || COALESCE(LOOKBACK_DAYS_HISTORIC, 'all') ||
                        '\\nRULES_JSON: ' || COALESCE(TO_VARCHAR(RULES_JSON), '[]'),
                        '\\n\\n'
                    ) WITHIN GROUP (ORDER BY DEFICIT_ID) as RULES_TEXT
                    FROM DRI_RULES
                    WHERE IS_CURRENT_VERSION = TRUE AND IS_ACTIVE = TRUE
                """
                rules_result = execute_query(rules_query, session)
                rules_text = rules_result[0]['RULES_TEXT'] if rules_result else ""
                
                full_prompt = edited_prompt.replace('{resident_context}', edited_resident_context).replace('{rag_indicator_context}', rules_text)
                
                escaped_full_prompt = full_prompt.replace("'", "''")
                
                analysis_query = f"""
                SELECT 
                    SNOWFLAKE.CORTEX.COMPLETE(
                        '{selected_model}',
                        [
                            {{
                                'role': 'user',
                                'content': '{escaped_full_prompt}'
                            }}
                        ],
                        {{
                            'max_tokens': {max_tokens}
                        }}
                    ) as RESPONSE
                """
                
                result = execute_query(analysis_query, session)
                processing_time = int((time.time() - start_time) * 1000)
                
                if result:
                    raw_response = result[0]['RESPONSE']
                    try:
                        response_obj = json.loads(raw_response)
                        response_text = response_obj.get('choices', [{}])[0].get('messages', raw_response)
                        tokens_used = response_obj.get('usage', {})
                    except (json.JSONDecodeError, TypeError):
                        response_text = raw_response
                        tokens_used = {}
                    st.success(f"Completed in {processing_time}ms")
                    
                    tab1, tab2, tab3 = st.tabs(["📋 Formatted results", "📝 Raw JSON", "📊 Summary"])
                    
                    with tab1:
                        try:
                            cleaned = response_text.strip()
                            if cleaned.startswith('```json'):
                                cleaned = cleaned[7:]
                            elif cleaned.startswith('```'):
                                cleaned = cleaned[3:]
                            if cleaned.endswith('```'):
                                cleaned = cleaned[:-3]
                            cleaned = cleaned.strip()
                            
                            json_start = cleaned.find('{')
                            json_end = cleaned.rfind('}') + 1
                            if json_start >= 0 and json_end > json_start:
                                json_str = cleaned[json_start:json_end]
                                def try_fix_truncated_json(s):
                                    open_braces = s.count('{') - s.count('}')
                                    open_brackets = s.count('[') - s.count(']')
                                    if open_braces > 0 or open_brackets > 0:
                                        if s.rstrip().endswith(','):
                                            s = s.rstrip()[:-1]
                                        s += ']' * open_brackets + '}' * open_braces
                                    return s
                                
                                try:
                                    parsed = json.loads(json_str)
                                except json.JSONDecodeError:
                                    import re
                                    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                                    json_str = re.sub(r'([}\]"\d])\s*\n\s*(["{[])', r'\1,\n\2', json_str)
                                    try:
                                        parsed = json.loads(json_str)
                                    except json.JSONDecodeError:
                                        json_str = try_fix_truncated_json(json_str)
                                        parsed = json.loads(json_str)
                                        st.info("Note: Response was truncated. Showing partial results.")
                                
                                if 'summary' in parsed:
                                    summary = parsed['summary']
                                    cols = st.columns(3)
                                    with cols[0]:
                                        st.metric("Deficits detected", summary.get('indicators_detected', 0))
                                    with cols[1]:
                                        st.metric("Deficits cleared", summary.get('indicators_cleared', 0))
                                    with cols[2]:
                                        st.metric("Requires review", summary.get('requires_review_count', 0))
                                    if 'analysis_notes' in summary:
                                        st.caption(summary['analysis_notes'])
                                
                                if 'indicators' in parsed and parsed['indicators']:
                                    st.markdown("### Detected Deficits")
                                    deficit_context = load_deficit_context(session, selected_resident)
                                    
                                    for ind in parsed['indicators']:
                                        confidence = ind.get('confidence', 'N/A')
                                        requires_review = ind.get('requires_review', False)
                                        conf_color = '#28a745' if confidence == 'high' else '#ffc107' if confidence == 'medium' else '#dc3545'
                                        review_badge = ' REVIEW' if requires_review else ''
                                        deficit_id = ind.get('deficit_id', 'Unknown')
                                        
                                        ctx = deficit_context.get(deficit_id, {})
                                        is_flagged = ctx.get('is_flagged', False)
                                        occ_count = ctx.get('occurrence_count', 0)
                                        threshold = ctx.get('threshold', 1)
                                        occ_dates = ctx.get('occurrence_dates', [])
                                        lookback = ctx.get('lookback_days', 9999)
                                        
                                        flag_badge = " ✅ FLAGGED" if is_flagged else ""
                                        will_flag = (occ_count + 1) >= threshold and not is_flagged
                                        
                                        with st.expander(f"{deficit_id} - {ind.get('deficit_name', 'Unknown')} ({confidence} confidence){review_badge}{flag_badge}", expanded=False):
                                            if is_flagged:
                                                expiry = ctx.get('expiry_date')
                                                if expiry:
                                                    st.success(f"Already flagged (expires: {expiry})")
                                                else:
                                                    st.success("Already flagged (persistent)")
                                            else:
                                                if occ_count > 0:
                                                    st.info(f"**{occ_count} of {threshold} occurrences** in {lookback} days")
                                                    if occ_dates:
                                                        st.caption(f"Prior dates: {', '.join(occ_dates[:5])}")
                                                else:
                                                    st.caption(f"No prior occurrences (threshold: {threshold} in {lookback} days)")
                                                
                                                if will_flag:
                                                    st.success(f"**{occ_count + 1} of {threshold} occurrences** - approving will FLAG this deficit ✅")
                                                elif threshold > 1:
                                                    remaining = threshold - occ_count - 1
                                                    st.caption(f"After approval: {occ_count + 1} of {threshold} ({remaining} more needed)")
                                            
                                            st.markdown(f"**Reasoning:** {ind.get('reasoning', 'N/A')}")
                                            
                                            temporal = ind.get('temporal_status', {})
                                            if temporal:
                                                st.caption(f"Temporal: {temporal.get('type', 'N/A')} | Onset: {temporal.get('onset_date', 'N/A')} | Persistence: {temporal.get('persistence_rule', 'N/A')}")
                                            
                                            if 'evidence' in ind and ind['evidence']:
                                                st.markdown("**Evidence:**")
                                                for ev in ind['evidence']:
                                                    source = ev.get('source_table', 'N/A')
                                                    event_date = ev.get('event_date', 'N/A')
                                                    excerpt = ev.get('text_excerpt', 'N/A')
                                                    st.caption(f"- {source} ({event_date}): {excerpt}")
                            else:
                                st.warning("Could not parse JSON from response")
                                st.text(response_text)
                        except json.JSONDecodeError as e:
                            st.warning(f"JSON parsing error: {e}")
                            with st.expander("View raw response"):
                                st.code(response_text, language="json")
                    
                    with tab2:
                        st.code(response_text, language="json")
                    
                    with tab3:
                        st.markdown(f"""
- **Resident ID:** {selected_resident}
- **Facility:** {detected_facility}
- **Model:** {selected_model}
- **Prompt version:** {selected_version}
- **Context threshold:** {context_threshold}
- **Processing time:** {processing_time}ms
- **Response length:** {len(response_text)} chars
                        """)
                else:
                    st.error("No response from LLM")
            except Exception as e:
                st.error(f"Analysis failed: {e}")
    
    st.markdown("---")
    st.caption("Use 'Batch Testing' page for multi-resident tests. Use 'Configuration' to change production settings.")

else:
    st.error("Failed to connect to Snowflake")
