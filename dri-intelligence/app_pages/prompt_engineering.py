"""DRI Intelligence - Prompt Engineering

Interactive page for testing and tuning LLM prompts:
- Select resident and client configuration
- Choose model (Claude 4.5, etc.) and prompt version
- Edit prompts with variable placeholders
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

### How to Use
1. **Select a resident** to analyze
2. **Choose a model** (Claude 4.5 variants recommended)
3. **Select or edit a prompt version** - prompts include variable placeholders for resident data and DRI rules
4. **Click "Run Analysis"** to test the prompt
5. **Review JSON results** - check detected indicators, confidence, and evidence
6. **Save as new version** when satisfied (versions auto-increment: v0001, v0002, etc.)

### Key Features
| Feature | Description |
|---------|-------------|
| **Preview full prompt** | See the complete prompt with all variables expanded |
| **Adaptive token sizing** | Automatically uses larger token limit for residents with more data |
| **Evidence traceability** | Each detected indicator includes source references |
| **Version history** | All prompt versions are retained for comparison |

### Variable Placeholders
The prompt template includes these variables that get replaced at runtime:
- `{client_form_mappings}` - Client-specific form field mappings
- `{resident_context}` - All resident data (notes, meds, observations, forms)
- `{rag_indicator_context}` - DRI rules from the DRI_RULES table

### Tips
- Test with multiple residents to verify prompt handles different scenarios
- Compare results before and after prompt changes
- Check evidence quality - good prompts cite specific source records
- After testing, go to Configuration > Processing Settings to deploy to production
        """)
    
    st.caption("Test and tune LLM prompts for DRI indicator detection")

@st.cache_data(ttl=300)
def load_residents(_session):
    return execute_query_df("""
        SELECT DISTINCT RESIDENT_ID 
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES
        ORDER BY RESIDENT_ID
    """, _session)

@st.cache_data(ttl=300)
def load_configs(_session):
    return execute_query_df("""
        SELECT CLIENT_SYSTEM_KEY, CLIENT_NAME 
        FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG
        WHERE IS_ACTIVE = TRUE
    """, _session)

@st.cache_data(ttl=300)
def load_prompt_versions(_session):
    return execute_query_df("""
        SELECT VERSION_NUMBER, IS_ACTIVE 
        FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS
        ORDER BY CREATED_TIMESTAMP DESC
    """, _session)

@st.cache_data(ttl=300)
def load_prompt_text(version, _session):
    return execute_query_df(f"""
        SELECT PROMPT_TEXT 
        FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS
        WHERE VERSION_NUMBER = '{version}'
    """, _session)

if session:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Test configuration")
        
        residents = load_residents(session)
        if residents is not None and len(residents) > 0:
            selected_resident = st.selectbox(
                "Select resident",
                residents['RESIDENT_ID'].tolist(),
                help="Choose a resident to analyze"
            )
        else:
            selected_resident = st.number_input("Resident ID", value=871, min_value=1)
        
        configs = load_configs(session)
        if configs is not None and len(configs) > 0:
            client_options = {row['CLIENT_NAME']: row['CLIENT_SYSTEM_KEY'] for _, row in configs.iterrows()}
            selected_client_name = st.selectbox("Client configuration", list(client_options.keys()))
            selected_client = client_options[selected_client_name]
        else:
            selected_client = "DEMO_CLIENT_871"
        
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
            'llama3.1-70b',
            'llama3.1-405b',
            'llama3.3-70b',
            'snowflake-llama-3.3-70b',
            'deepseek-r1'
        ]
        selected_model = st.selectbox(
            "LLM model", 
            model_options, 
            index=0,
            help="Cross-region inference enabled"
        )
        
        prompt_versions = load_prompt_versions(session)
        if prompt_versions is not None and len(prompt_versions) > 0:
            version_options = prompt_versions['VERSION_NUMBER'].tolist()
            active_version = prompt_versions[prompt_versions['IS_ACTIVE'] == True]['VERSION_NUMBER'].tolist()
            default_idx = version_options.index(active_version[0]) if active_version else 0
            selected_version = st.selectbox("Prompt version", version_options, index=default_idx)
        else:
            selected_version = "v1.0"
        
        col_ctx1, col_ctx2 = st.columns(2)
        with col_ctx1:
            view_context_btn = st.button("📖 View resident data", use_container_width=True)
        with col_ctx2:
            preview_prompt_btn = st.button("👁️ Preview full prompt", use_container_width=True, help="See exactly what gets sent to the LLM")
        
        if view_context_btn:
            with st.spinner("Loading..."):
                context_query = f"""
                    WITH notes AS (
                        SELECT LISTAGG(LEFT(PROGRESS_NOTE, 400), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as txt
                        FROM (SELECT PROGRESS_NOTE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES WHERE RESIDENT_ID = {selected_resident} ORDER BY EVENT_DATE DESC LIMIT 15)
                    ),
                    meds AS (
                        SELECT LISTAGG(MED_NAME || ' (' || MED_STATUS || ')', ', ') as txt
                        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION WHERE RESIDENT_ID = {selected_resident}
                    ),
                    obs AS (
                        SELECT LISTAGG(CHART_NAME || ': ' || LEFT(OBSERVATION_VALUE, 50), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as txt
                        FROM (SELECT CHART_NAME, OBSERVATION_VALUE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS WHERE RESIDENT_ID = {selected_resident} ORDER BY EVENT_DATE DESC LIMIT 30)
                    ),
                    medical_profile AS (
                        SELECT COALESCE(SPECIAL_NEEDS, '') || ' | Allergies: ' || COALESCE(ALLERGIES, 'None') || ' | Diet: ' || COALESCE(DIET, 'Standard') as txt
                        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICAL_PROFILE WHERE RESIDENT_ID = {selected_resident}
                    ),
                    obs_groups AS (
                        SELECT LISTAGG(CHART_NAME || ' (' || OBSERVATION_STATUS || '): ' || OBSERVATION_TYPE || ' - ' || OBSERVATION_LOCATION || ' - ' || COALESCE(OBSERVATION_DESCRIPTION, ''), ' | ') as txt
                        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATION_GROUP WHERE RESIDENT_ID = {selected_resident}
                    )
                    SELECT 
                        'MEDICAL PROFILE (DIAGNOSES):\\n' || COALESCE((SELECT txt FROM medical_profile), 'None') ||
                        '\\n\\nPROGRESS NOTES:\\n' || COALESCE((SELECT txt FROM notes), 'None') ||
                        '\\n\\nMEDICATIONS:\\n' || COALESCE((SELECT txt FROM meds), 'None') ||
                        '\\n\\nOBSERVATIONS:\\n' || COALESCE((SELECT txt FROM obs), 'None') ||
                        '\\n\\nOBSERVATION GROUPS (Wounds/Pain):\\n' || COALESCE((SELECT txt FROM obs_groups), 'None') as CONTEXT
                """
                result = execute_query(context_query, session)
                if result:
                    st.text_area("Resident context preview", result[0]['CONTEXT'], height=250)
        
        if preview_prompt_btn:
            with st.spinner("Building full prompt..."):
                full_prompt_query = f"""
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
                    ),
                    resident_medical_profile AS (
                        SELECT COALESCE(SPECIAL_NEEDS, '') || ' | Allergies: ' || COALESCE(ALLERGIES, 'None') || ' | Diet: ' || COALESCE(DIET, 'Standard') as profile_text
                        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICAL_PROFILE WHERE RESIDENT_ID = {selected_resident}
                    ),
                    resident_obs_groups AS (
                        SELECT LISTAGG(CHART_NAME || ' (' || OBSERVATION_STATUS || '): ' || COALESCE(OBSERVATION_TYPE, '') || ' - ' || COALESCE(OBSERVATION_LOCATION, '') || ' - ' || COALESCE(OBSERVATION_DESCRIPTION, ''), ' | ') as obs_groups_text
                        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATION_GROUP WHERE RESIDENT_ID = {selected_resident}
                    ),
                    clinical_rules AS (
                        SELECT LISTAGG(
                            '=== ' || DEFICIT_ID || ' - ' || DEFICIT_NAME || ' ===' ||
                            '\nDEFICIT_TYPE: ' || DEFICIT_TYPE || 
                            '\nEXPIRY_DAYS: ' || COALESCE(TO_VARCHAR(EXPIRY_DAYS), '0') || 
                            '\nRENEWAL_REMINDER_DAYS: ' || COALESCE(TO_VARCHAR(RENEWAL_REMINDER_DAYS), '7') ||
                            '\nLOOKBACK_DAYS_HISTORIC: ' || COALESCE(LOOKBACK_DAYS_HISTORIC, 'all') ||
                            '\nRULES_JSON: ' || COALESCE(TO_VARCHAR(RULES_JSON), '[]'),
                            '\n\n'
                        ) WITHIN GROUP (ORDER BY DEFICIT_ID) as rules_text
                        FROM AGEDCARE.AGEDCARE.DRI_RULES
                        WHERE IS_CURRENT_VERSION = TRUE AND IS_ACTIVE = TRUE
                    ),
                    full_context AS (
                        SELECT 
                            'MEDICAL PROFILE (DIAGNOSES - PRIMARY SOURCE): ' || COALESCE((SELECT profile_text FROM resident_medical_profile), 'None') ||
                            '\\n\\nPROGRESS NOTES: ' || COALESCE((SELECT notes_text FROM resident_notes), 'None') ||
                            '\\n\\nMEDICATIONS: ' || COALESCE((SELECT meds_text FROM resident_meds), 'None') ||
                            '\\n\\nOBSERVATIONS: ' || COALESCE((SELECT obs_text FROM resident_obs), 'None') ||
                            '\\n\\nOBSERVATION GROUPS (Wounds/Pain Charts): ' || COALESCE((SELECT obs_groups_text FROM resident_obs_groups), 'None') ||
                            '\\n\\nASSESSMENT FORMS: ' || COALESCE((SELECT forms_text FROM resident_forms), 'None') as context
                    ),
                    prompt_template AS (
                        SELECT PROMPT_TEXT FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS WHERE VERSION_NUMBER = '{selected_version}'
                    )
                    SELECT 
                        REPLACE(REPLACE(
                            (SELECT PROMPT_TEXT FROM prompt_template),
                            '{{resident_context}}', (SELECT context FROM full_context)
                        ), '{{rag_indicator_context}}', (SELECT rules_text FROM clinical_rules)) as FULL_PROMPT,
                        LENGTH(REPLACE(REPLACE(
                            (SELECT PROMPT_TEXT FROM prompt_template),
                            '{{resident_context}}', (SELECT context FROM full_context)
                        ), '{{rag_indicator_context}}', (SELECT rules_text FROM clinical_rules))) as PROMPT_LENGTH
                """
                result = execute_query(full_prompt_query, session)
                if result:
                    full_prompt = result[0]['FULL_PROMPT']
                    prompt_length = result[0]['PROMPT_LENGTH']
                    st.success(f"Full prompt length: {prompt_length:,} characters")
                    st.text_area("Full prompt (exactly what gets sent to LLM)", full_prompt, height=400)
                    st.info("💡 This is the complete prompt with all placeholders resolved. Copy this to test in other environments.")
    
    with col2:
        st.subheader("Prompt template")
        
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
        
        max_version = execute_query("""
            SELECT MAX(VERSION_NUMBER) as MAX_VER FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS 
            WHERE VERSION_NUMBER LIKE 'v%'
        """, session)
        if max_version and max_version[0]['MAX_VER']:
            current_max = max_version[0]['MAX_VER']
            next_num = int(current_max[1:]) + 1
            next_version = f"v{next_num:04d}"
        else:
            next_version = "v0001"
        
        st.info(f"Next version will be: **{next_version}**", icon=":material/info:")
        new_description = st.text_input("Description", value="Updated prompt")
        
        if st.button("💾 Save as new version"):
            escaped_prompt = edited_prompt.replace("'", "''")
            try:
                execute_query(f"""
                    INSERT INTO AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS 
                    (VERSION_NUMBER, PROMPT_TEXT, DESCRIPTION, CREATED_BY, IS_ACTIVE)
                    VALUES ('{next_version}', '{escaped_prompt}', '{new_description}', 'user', FALSE)
                """, session)
                st.success(f"Saved as version {next_version}")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Failed to save: {e}")
    
    st.subheader("🚀 Run analysis")
    
    run_button = st.button("🧪 Run Single Analysis", type="primary", use_container_width=True, help="Test prompt on selected resident")
    
    if run_button:
        with st.spinner(f"Analyzing resident {selected_resident} with {selected_model}..."):
            import time
            start_time = time.time()
            
            try:
                context_size_query = f"""
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
                ),
                resident_medical_profile AS (
                    SELECT COALESCE(SPECIAL_NEEDS, '') || ' | Allergies: ' || COALESCE(ALLERGIES, 'None') || ' | Diet: ' || COALESCE(DIET, 'Standard') as profile_text
                    FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICAL_PROFILE WHERE RESIDENT_ID = {selected_resident}
                ),
                resident_obs_groups AS (
                    SELECT LISTAGG(CHART_NAME || ' (' || OBSERVATION_STATUS || '): ' || OBSERVATION_TYPE || ' - ' || OBSERVATION_LOCATION || ' - ' || COALESCE(OBSERVATION_DESCRIPTION, ''), ' | ') as obs_groups_text
                    FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATION_GROUP WHERE RESIDENT_ID = {selected_resident}
                ),
                clinical_rules AS (
                    SELECT LISTAGG(
                        '=== ' || DEFICIT_ID || ' - ' || DEFICIT_NAME || ' ===' ||
                        '\nDEFICIT_TYPE: ' || DEFICIT_TYPE || 
                        '\nEXPIRY_DAYS: ' || COALESCE(TO_VARCHAR(EXPIRY_DAYS), '0') || 
                        '\nRENEWAL_REMINDER_DAYS: ' || COALESCE(TO_VARCHAR(RENEWAL_REMINDER_DAYS), '7') ||
                        '\nLOOKBACK_DAYS_HISTORIC: ' || COALESCE(LOOKBACK_DAYS_HISTORIC, 'all') ||
                        '\nRULES_JSON: ' || COALESCE(TO_VARCHAR(RULES_JSON), '[]'),
                        ' || '
                    ) WITHIN GROUP (ORDER BY DEFICIT_ID) as rules_text
                    FROM AGEDCARE.AGEDCARE.DRI_RULES
                    WHERE IS_CURRENT_VERSION = TRUE AND IS_ACTIVE = TRUE
                )
                SELECT 
                    LENGTH(COALESCE((SELECT notes_text FROM resident_notes), '')) +
                    LENGTH(COALESCE((SELECT meds_text FROM resident_meds), '')) +
                    LENGTH(COALESCE((SELECT obs_text FROM resident_obs), '')) +
                    LENGTH(COALESCE((SELECT forms_text FROM resident_forms), '')) +
                    LENGTH(COALESCE((SELECT profile_text FROM resident_medical_profile), '')) +
                    LENGTH(COALESCE((SELECT obs_groups_text FROM resident_obs_groups), '')) +
                    LENGTH(COALESCE((SELECT rules_text FROM clinical_rules), '')) as TOTAL_CONTEXT_LENGTH
                """
                
                size_result = execute_query(context_size_query, session)
                context_length = size_result[0]['TOTAL_CONTEXT_LENGTH'] if size_result else 0
                
                if 'context_threshold' not in st.session_state:
                    db_threshold = execute_query("""
                        SELECT CONFIG_JSON:client_settings:context_threshold::NUMBER as VAL
                        FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG WHERE IS_ACTIVE = TRUE LIMIT 1
                    """, session)
                    st.session_state['context_threshold'] = db_threshold[0]['VAL'] if db_threshold and db_threshold[0]['VAL'] else 6000
                
                CONTEXT_THRESHOLD = st.session_state.get('context_threshold', 6000)
                if context_length > CONTEXT_THRESHOLD:
                    max_tokens = 16384
                    token_mode = "large"
                else:
                    max_tokens = 4096
                    token_mode = "standard"
                
                st.info(f"Context size: {context_length:,} chars → Using {token_mode} mode ({max_tokens:,} max tokens)")
                
                analysis_query = f"""
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
                ),
                resident_medical_profile AS (
                    SELECT COALESCE(SPECIAL_NEEDS, '') || ' | Allergies: ' || COALESCE(ALLERGIES, 'None') || ' | Diet: ' || COALESCE(DIET, 'Standard') as profile_text
                    FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICAL_PROFILE WHERE RESIDENT_ID = {selected_resident}
                ),
                resident_obs_groups AS (
                    SELECT LISTAGG(CHART_NAME || ' (' || OBSERVATION_STATUS || '): ' || OBSERVATION_TYPE || ' - ' || OBSERVATION_LOCATION || ' - ' || COALESCE(OBSERVATION_DESCRIPTION, ''), ' | ') as obs_groups_text
                    FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATION_GROUP WHERE RESIDENT_ID = {selected_resident}
                ),
                clinical_rules AS (
                    SELECT LISTAGG(
                        '=== ' || DEFICIT_ID || ' - ' || DEFICIT_NAME || ' ===' ||
                        '\\nDEFICIT_TYPE: ' || DEFICIT_TYPE || 
                        '\\nEXPIRY_DAYS: ' || COALESCE(TO_VARCHAR(EXPIRY_DAYS), '0') || 
                        '\\nRENEWAL_REMINDER_DAYS: ' || COALESCE(TO_VARCHAR(RENEWAL_REMINDER_DAYS), '7') ||
                        '\\nLOOKBACK_DAYS_HISTORIC: ' || COALESCE(LOOKBACK_DAYS_HISTORIC, 'all') ||
                        '\\nRULES_JSON: ' || COALESCE(TO_VARCHAR(RULES_JSON), '[]'),
                        '\\n\\n'
                    ) WITHIN GROUP (ORDER BY DEFICIT_ID) as rules_text
                    FROM AGEDCARE.AGEDCARE.DRI_RULES
                    WHERE IS_CURRENT_VERSION = TRUE AND IS_ACTIVE = TRUE
                ),
                full_context AS (
                    SELECT 
                        'MEDICAL PROFILE (DIAGNOSES - PRIMARY SOURCE): ' || COALESCE((SELECT profile_text FROM resident_medical_profile), 'None') ||
                        '\\n\\nPROGRESS NOTES: ' || COALESCE((SELECT notes_text FROM resident_notes), 'None') ||
                        '\\n\\nMEDICATIONS: ' || COALESCE((SELECT meds_text FROM resident_meds), 'None') ||
                        '\\n\\nOBSERVATIONS: ' || COALESCE((SELECT obs_text FROM resident_obs), 'None') ||
                        '\\n\\nOBSERVATION GROUPS (Wounds/Pain Charts): ' || COALESCE((SELECT obs_groups_text FROM resident_obs_groups), 'None') ||
                        '\\n\\nASSESSMENT FORMS: ' || COALESCE((SELECT forms_text FROM resident_forms), 'None') as context
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
                                    '{{resident_context}}', (SELECT context FROM full_context)
                                ), '{{rag_indicator_context}}', (SELECT rules_text FROM clinical_rules))
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
                                        st.metric("Indicators detected", summary.get('indicators_detected', 0))
                                    with cols[1]:
                                        st.metric("Indicators cleared", summary.get('indicators_cleared', 0))
                                    with cols[2]:
                                        st.metric("Requires review", summary.get('requires_review_count', 0))
                                    if 'analysis_notes' in summary:
                                        st.caption(summary['analysis_notes'])
                                
                                if 'indicators' in parsed and parsed['indicators']:
                                    st.markdown("### 🔍 Detected Indicators")
                                    for ind in parsed['indicators']:
                                        confidence = ind.get('confidence', 'N/A')
                                        requires_review = ind.get('requires_review', False)
                                        conf_color = '#28a745' if confidence == 'high' else '#ffc107' if confidence == 'medium' else '#dc3545'
                                        review_badge = '⚠️ REVIEW' if requires_review else ''
                                        
                                        with st.expander(f"✅ {ind.get('deficit_id', 'Unknown')} - {ind.get('deficit_name', 'Unknown')} ({confidence} confidence) {review_badge}", expanded=False):
                                            st.markdown(f"""
                                            <div style="background-color: #f8f9fa; padding: 0.75rem; border-radius: 0.25rem; border-left: 4px solid {conf_color}; margin-bottom: 1rem;">
                                                <strong>Reasoning:</strong> {ind.get('reasoning', 'N/A')}
                                            </div>
                                            """, unsafe_allow_html=True)
                                            
                                            temporal = ind.get('temporal_status', {})
                                            if temporal:
                                                st.markdown(f"""
                                                <div style="background-color: #e7f3ff; padding: 0.5rem; border-radius: 0.25rem; margin-bottom: 0.5rem; font-size: 0.9rem;">
                                                    <strong>Temporal:</strong> {temporal.get('type', 'N/A')} | 
                                                    Onset: {temporal.get('onset_date', 'N/A')} | 
                                                    Persistence: {temporal.get('persistence_rule', 'N/A')}
                                                </div>
                                                """, unsafe_allow_html=True)
                                            
                                            if 'evidence' in ind and ind['evidence']:
                                                st.markdown("**Evidence:**")
                                                for ev in ind['evidence']:
                                                    source = ev.get('source_table', 'N/A')
                                                    record_id = ev.get('record_id', 'N/A')
                                                    event_date = ev.get('event_date', 'N/A')
                                                    excerpt = ev.get('text_excerpt', 'N/A')
                                                    st.markdown(f"""
                                                    <div style="background-color: #fff3cd; padding: 0.5rem; border-radius: 0.25rem; margin-bottom: 0.5rem; font-size: 0.85rem;">
                                                        <strong>Source:</strong> {source} | <strong>Record ID:</strong> {record_id} | <strong>Date:</strong> {event_date}<br>
                                                        <em>{excerpt}</em>
                                                    </div>
                                                    """, unsafe_allow_html=True)
                                
                                if 'clinical_indicators' in parsed:
                                    st.write("**Clinical indicators detected**")
                                    for domain, data in parsed['clinical_indicators'].items():
                                        if isinstance(data, dict) and data.get('present', False):
                                            with st.expander(f"✅ {domain.upper()}", expanded=True):
                                                if 'evidence' in data:
                                                    for ev in data['evidence']:
                                                        st.write(f"- {ev}")
                            else:
                                st.warning("Could not parse JSON from response")
                                st.text(response_text)
                        except json.JSONDecodeError as e:
                            st.warning(f"JSON parsing error: {e}. The LLM response may be truncated or malformed.")
                            with st.expander("View raw response", expanded=False):
                                st.code(response_text, language="json")
                    
                    with tab2:
                        st.code(response_text, language="json")
                    
                    with tab3:
                        st.write(f"""
- **Resident ID:** {selected_resident}
- **Client:** {selected_client}
- **Model:** {selected_model}
- **Prompt version:** {selected_version}
- **Processing time:** {processing_time}ms
- **Response length:** {len(response_text)} chars
                        """)
                else:
                    st.error("No response from LLM")
            except Exception as e:
                st.error(f"Analysis failed: {e}")
    
    st.markdown("---")
    st.caption("💡 **Tip:** Use 'Run Single Analysis' to test prompts. Use 'Batch Testing' page for multi-resident tests with quality metrics.")

else:
    st.error("Failed to connect to Snowflake")
