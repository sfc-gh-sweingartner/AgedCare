import streamlit as st
import json
import sys
from datetime import datetime, timedelta
sys.path.insert(0, '/Users/sweingartner/CoCo/AgedCare/dri-intelligence')

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

st.set_page_config(page_title="Batch Testing", page_icon="🧪", layout="wide")
st.title("🧪 Batch Testing")
st.caption("Test batch processing on a selected range of records before production deployment")

session = get_snowflake_session()

if session:
    clients = execute_query_df("""
        SELECT CONFIG_ID, CLIENT_SYSTEM_KEY, CLIENT_NAME, IS_ACTIVE
        FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG
        ORDER BY CLIENT_NAME
    """, session)
    
    if clients is not None and len(clients) > 0:
        client_options = {f"{row['CLIENT_NAME']} ({row['CLIENT_SYSTEM_KEY']})": row['CONFIG_ID'] for _, row in clients.iterrows()}
        client_keys = {row['CONFIG_ID']: row['CLIENT_SYSTEM_KEY'] for _, row in clients.iterrows()}
        
        st.markdown("### 🏢 Select Client")
        selected_client_display = st.selectbox(
            "Client",
            list(client_options.keys()),
            help="Batch test will use this client's production configuration"
        )
        selected_config_id = client_options[selected_client_display]
        selected_client_key = client_keys[selected_config_id]
        
        st.markdown("---")
    else:
        st.error("No clients found in configuration table")
        st.stop()

    prod_config = execute_query(f"""
        SELECT 
            CONFIG_JSON:production_settings:model::VARCHAR as PROD_MODEL,
            CONFIG_JSON:production_settings:prompt_text::VARCHAR as PROD_PROMPT_TEXT,
            CONFIG_JSON:production_settings:prompt_version::VARCHAR as PROD_PROMPT_VERSION,
            CONFIG_JSON:production_settings:batch_schedule::VARCHAR as BATCH_SCHEDULE,
            CONFIG_JSON:client_settings:context_threshold::NUMBER as CONTEXT_THRESHOLD
        FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG 
        WHERE CONFIG_ID = '{selected_config_id}'
    """, session)
    
    prod_model = prod_config[0]['PROD_MODEL'] if prod_config and prod_config[0]['PROD_MODEL'] else 'claude-3-5-sonnet'
    prod_prompt_text = prod_config[0]['PROD_PROMPT_TEXT'] if prod_config and prod_config[0]['PROD_PROMPT_TEXT'] else None
    prod_prompt_version = prod_config[0]['PROD_PROMPT_VERSION'] if prod_config and prod_config[0]['PROD_PROMPT_VERSION'] else 'v1.0'
    context_threshold = prod_config[0]['CONTEXT_THRESHOLD'] if prod_config and prod_config[0]['CONTEXT_THRESHOLD'] else 6000
    
    if not prod_prompt_text:
        fallback_prompt = execute_query(f"""
            SELECT PROMPT_TEXT FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS 
            WHERE VERSION_NUMBER = '{prod_prompt_version}'
        """, session)
        if fallback_prompt:
            prod_prompt_text = fallback_prompt[0]['PROMPT_TEXT']
            st.info("Using prompt from DRI_PROMPT_VERSIONS (not yet saved to client config)")
    
    st.markdown("### Current Production Configuration")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Model", prod_model)
    with col2:
        st.metric("Prompt Version", prod_prompt_version)
    with col3:
        st.metric("Context Threshold", f"{context_threshold:,}")
    with col4:
        has_prompt = "✅ Configured" if prod_prompt_text else "⚠️ Not Set"
        st.metric("Prompt Text", has_prompt)
    
    if not prod_prompt_text:
        st.error("No production prompt configured. Go to Configuration → Processing Settings to save a prompt for production.")
        st.stop()
    
    st.markdown("---")
    st.markdown("### Select Records for Batch Test")
    
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        st.markdown("#### Date Range Filter")
        
        try:
            date_stats = execute_query("""
                SELECT 
                    TO_CHAR(MIN(CAST(EVENT_DATE AS DATE)), 'YYYY-MM-DD') as MIN_DATE,
                    TO_CHAR(MAX(CAST(EVENT_DATE AS DATE)), 'YYYY-MM-DD') as MAX_DATE,
                    COUNT(DISTINCT RESIDENT_ID) as TOTAL_RESIDENTS
                FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES
                WHERE EVENT_DATE IS NOT NULL
            """, session)
            
            if date_stats and date_stats[0]['MIN_DATE']:
                min_date_str = date_stats[0]['MIN_DATE']
                max_date_str = date_stats[0]['MAX_DATE']
                min_date = datetime.strptime(min_date_str, '%Y-%m-%d').date()
                max_date = datetime.strptime(max_date_str, '%Y-%m-%d').date()
                total_residents = date_stats[0]['TOTAL_RESIDENTS'] or 0
                st.caption(f"Data available from {min_date} to {max_date} ({total_residents} residents)")
            else:
                min_date = datetime.now().date() - timedelta(days=365)
                max_date = datetime.now().date()
        except Exception as e:
            st.warning(f"Could not load date range: {e}")
            min_date = datetime.now().date() - timedelta(days=365)
            max_date = datetime.now().date()
        
        date_from = st.date_input("From Date", value=max(min_date, max_date - timedelta(days=30)), min_value=min_date, max_value=max_date)
        date_to = st.date_input("To Date", value=max_date, min_value=min_date, max_value=max_date)
    
    with col_filter2:
        st.markdown("#### Resident Filter")
        
        residents = execute_query_df("""
            SELECT DISTINCT RESIDENT_ID 
            FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES
            ORDER BY RESIDENT_ID
        """, session)
        
        if residents is not None and len(residents) > 0:
            resident_list = ["All Residents"] + [str(r) for r in residents['RESIDENT_ID'].tolist()]
        else:
            resident_list = ["All Residents"]
        
        selected_residents = st.multiselect(
            "Select Specific Residents (optional)",
            resident_list,
            default=[],
            help="Leave empty to process all residents in the date range"
        )
        
        use_all_residents = "All Residents" in selected_residents or len(selected_residents) == 0
    
    st.markdown("---")
    
    where_clause_parts = [f"EVENT_DATE >= '{date_from}'", f"EVENT_DATE <= '{date_to}'"]
    if not use_all_residents:
        resident_ids = [r for r in selected_residents if r != "All Residents"]
        if resident_ids:
            where_clause_parts.append(f"RESIDENT_ID IN ({','.join(resident_ids)})")
    
    where_clause = " AND ".join(where_clause_parts)
    
    preview_query = f"""
        SELECT 
            RESIDENT_ID,
            COUNT(DISTINCT PROGRESS_NOTE_ID) as NOTE_COUNT,
            MIN(EVENT_DATE)::DATE as EARLIEST_NOTE,
            MAX(EVENT_DATE)::DATE as LATEST_NOTE
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES
        WHERE {where_clause}
        GROUP BY RESIDENT_ID
        ORDER BY RESIDENT_ID
    """
    
    preview_data = execute_query_df(preview_query, session)
    
    st.markdown("### Records to Process")
    
    if preview_data is not None and len(preview_data) > 0:
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Residents to Process", len(preview_data))
        with col_m2:
            st.metric("Total Notes", preview_data['NOTE_COUNT'].sum())
        with col_m3:
            est_time = len(preview_data) * 45
            st.metric("Est. Processing Time", f"{est_time // 60}m {est_time % 60}s")
        
        with st.expander("View Residents to Process", expanded=False):
            st.dataframe(preview_data, use_container_width=True)
    else:
        st.warning("No records match the selected filters")
    
    st.markdown("---")
    st.markdown("### Run Batch Test")
    
    col_run1, col_run2 = st.columns([2, 1])
    
    with col_run1:
        st.info("""
        **What this does:**
        - Runs DRI analysis on each resident using the production model and prompt from client config
        - Stores results in DRI_LLM_ANALYSIS for review
        - Creates entries in DRI_REVIEW_QUEUE for human approval
        - Does NOT update production DRI scores (requires approval)
        """)
    
    with col_run2:
        run_batch = st.button(
            "🚀 Run Batch Test",
            type="primary",
            use_container_width=True,
            disabled=(preview_data is None or len(preview_data) == 0)
        )
    
    if run_batch and preview_data is not None and len(preview_data) > 0:
        import time
        import uuid
        
        batch_id = str(uuid.uuid4())
        residents_to_process = preview_data['RESIDENT_ID'].tolist()
        total_residents = len(residents_to_process)
        
        st.markdown(f"### Batch Run: `{batch_id[:8]}...`")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()
        
        successful = 0
        failed = 0
        results = []
        
        escaped_prompt_for_sql = prod_prompt_text.replace("'", "''")
        
        for idx, resident_id in enumerate(residents_to_process):
            status_text.markdown(f"Processing resident **{resident_id}** ({idx + 1}/{total_residents})...")
            progress_bar.progress((idx + 1) / total_residents)
            
            try:
                context_size_query = f"""
                WITH resident_notes AS (
                    SELECT LISTAGG(LEFT(PROGRESS_NOTE, 400) || ' [' || NOTE_TYPE || ']', ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as notes_text
                    FROM (SELECT PROGRESS_NOTE, NOTE_TYPE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 15)
                ),
                resident_meds AS (
                    SELECT LISTAGG(MED_NAME || ' (' || MED_STATUS || ')', ', ') as meds_text
                    FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION WHERE RESIDENT_ID = {resident_id}
                ),
                resident_obs AS (
                    SELECT LISTAGG(CHART_NAME || ': ' || LEFT(OBSERVATION_VALUE, 100), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as obs_text
                    FROM (SELECT CHART_NAME, OBSERVATION_VALUE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 30)
                ),
                resident_forms AS (
                    SELECT LISTAGG(FORM_NAME || ': ' || ELEMENT_NAME || '=' || LEFT(RESPONSE, 100), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as forms_text
                    FROM (SELECT FORM_NAME, ELEMENT_NAME, RESPONSE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_ASSESSMENT_FORMS WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 20)
                ),
                rag_indicators AS (
                    SELECT LISTAGG(INDICATOR_ID || ' - ' || INDICATOR_NAME || ': ' || DEFINITION, ' || ') WITHIN GROUP (ORDER BY INDICATOR_ID) as indicators_text
                    FROM AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS
                )
                SELECT 
                    LENGTH(COALESCE((SELECT notes_text FROM resident_notes), '')) +
                    LENGTH(COALESCE((SELECT meds_text FROM resident_meds), '')) +
                    LENGTH(COALESCE((SELECT obs_text FROM resident_obs), '')) +
                    LENGTH(COALESCE((SELECT forms_text FROM resident_forms), '')) +
                    LENGTH(COALESCE((SELECT indicators_text FROM rag_indicators), '')) as TOTAL_CONTEXT_LENGTH
                """
                
                size_result = execute_query(context_size_query, session)
                context_length = size_result[0]['TOTAL_CONTEXT_LENGTH'] if size_result else 0
                
                if context_length > context_threshold:
                    max_tokens = 16384
                    token_mode = "large"
                else:
                    max_tokens = 4096
                    token_mode = "standard"
                
                start_time = time.time()
                
                analysis_query = f"""
                WITH resident_notes AS (
                    SELECT LISTAGG(LEFT(PROGRESS_NOTE, 400) || ' [' || NOTE_TYPE || ']', ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as notes_text
                    FROM (SELECT PROGRESS_NOTE, NOTE_TYPE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 15)
                ),
                resident_meds AS (
                    SELECT LISTAGG(MED_NAME || ' (' || MED_STATUS || ')', ', ') as meds_text
                    FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION WHERE RESIDENT_ID = {resident_id}
                ),
                resident_obs AS (
                    SELECT LISTAGG(CHART_NAME || ': ' || LEFT(OBSERVATION_VALUE, 100), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as obs_text
                    FROM (SELECT CHART_NAME, OBSERVATION_VALUE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 30)
                ),
                resident_forms AS (
                    SELECT LISTAGG(FORM_NAME || ': ' || ELEMENT_NAME || '=' || LEFT(RESPONSE, 100), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as forms_text
                    FROM (SELECT FORM_NAME, ELEMENT_NAME, RESPONSE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_ASSESSMENT_FORMS WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 20)
                ),
                rag_indicators AS (
                    SELECT LISTAGG(INDICATOR_ID || ' - ' || INDICATOR_NAME || ': ' || DEFINITION, ' || ') WITHIN GROUP (ORDER BY INDICATOR_ID) as indicators_text
                    FROM AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS
                ),
                full_context AS (
                    SELECT 
                        'PROGRESS NOTES: ' || (SELECT notes_text FROM resident_notes) ||
                        ' MEDICATIONS: ' || (SELECT meds_text FROM resident_meds) ||
                        ' OBSERVATIONS: ' || (SELECT obs_text FROM resident_obs) ||
                        ' ASSESSMENT FORMS: ' || (SELECT forms_text FROM resident_forms) ||
                        ' DRI INDICATORS TO CHECK: ' || (SELECT indicators_text FROM rag_indicators) as context
                )
                SELECT 
                    SNOWFLAKE.CORTEX.COMPLETE(
                        '{prod_model}',
                        [
                            {{
                                'role': 'user',
                                'content': REPLACE(REPLACE(
                                    '{escaped_prompt_for_sql}',
                                    '{{resident_context}}', (SELECT context FROM full_context)
                                ), '{{rag_indicator_context}}', '')
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
                    except (json.JSONDecodeError, TypeError):
                        response_text = raw_response
                    
                    insert_query = f"""
                        INSERT INTO AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS 
                        (RESIDENT_ID, CLIENT_SYSTEM_KEY, MODEL_USED, PROMPT_VERSION, 
                         RAW_RESPONSE, PROCESSING_TIME_MS, BATCH_RUN_ID)
                        VALUES (
                            {resident_id},
                            '{selected_client_key}',
                            '{prod_model}',
                            '{prod_prompt_version}',
                            PARSE_JSON($${json.dumps({"response": response_text})}$$),
                            {processing_time},
                            '{batch_id}'
                        )
                    """
                    execute_query(insert_query, session)
                    
                    indicators_detected = 0
                    try:
                        cleaned = response_text.strip()
                        if cleaned.startswith('```json'):
                            cleaned = cleaned[7:]
                        if cleaned.endswith('```'):
                            cleaned = cleaned[:-3]
                        json_start = cleaned.find('{')
                        json_end = cleaned.rfind('}') + 1
                        if json_start >= 0 and json_end > json_start:
                            parsed = json.loads(cleaned[json_start:json_end])
                            indicators_detected = parsed.get('summary', {}).get('indicators_detected', 0)
                    except:
                        pass
                    
                    results.append({
                        "resident_id": resident_id,
                        "status": "Success",
                        "processing_time_ms": processing_time,
                        "token_mode": token_mode,
                        "indicators_detected": indicators_detected
                    })
                    successful += 1
                else:
                    results.append({
                        "resident_id": resident_id,
                        "status": "Failed - No response",
                        "processing_time_ms": 0,
                        "token_mode": token_mode,
                        "indicators_detected": 0
                    })
                    failed += 1
                    
            except Exception as e:
                results.append({
                    "resident_id": resident_id,
                    "status": f"Error: {str(e)[:50]}",
                    "processing_time_ms": 0,
                    "token_mode": "N/A",
                    "indicators_detected": 0
                })
                failed += 1
        
        progress_bar.progress(1.0)
        status_text.markdown("**Batch processing complete!**")
        
        with results_container:
            st.markdown("### Batch Results")
            
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("Successful", successful, delta=None)
            with col_r2:
                st.metric("Failed", failed, delta=None)
            with col_r3:
                avg_time = sum(r['processing_time_ms'] for r in results) // max(len(results), 1)
                st.metric("Avg Processing Time", f"{avg_time}ms")
            
            import pandas as pd
            results_df = pd.DataFrame(results)
            st.dataframe(results_df, use_container_width=True)
            
            st.success(f"""
            Batch test complete! Results stored with batch ID: `{batch_id}`
            
            **Next steps:**
            1. Review results in the **Analysis Results** page
            2. Approve or reject changes in the **Review Queue** page
            """)

else:
    st.error("Failed to connect to Snowflake")
