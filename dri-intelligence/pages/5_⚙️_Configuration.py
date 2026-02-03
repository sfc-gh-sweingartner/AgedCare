import streamlit as st
import json
import sys
sys.path.insert(0, '/Users/sweingartner/CoCo/AgedCare/dri-intelligence')

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

st.set_page_config(page_title="Configuration", page_icon="⚙️", layout="wide")
st.title("⚙️ Configuration")

session = get_snowflake_session()

if session:
    clients = execute_query_df("""
        SELECT CONFIG_ID, CLIENT_SYSTEM_KEY, CLIENT_NAME, IS_ACTIVE
        FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG
        ORDER BY CLIENT_NAME
    """, session)
    
    if clients is not None and len(clients) > 0:
        client_options = {f"{row['CLIENT_NAME']} ({row['CLIENT_SYSTEM_KEY']})": row['CONFIG_ID'] for _, row in clients.iterrows()}
        
        st.markdown("### 🏢 Select Client")
        selected_client_display = st.selectbox(
            "Client",
            list(client_options.keys()),
            help="All configuration changes will apply to the selected client"
        )
        selected_config_id = client_options[selected_client_display]
        
        st.markdown("---")
    else:
        st.error("No clients found in configuration table")
        st.stop()
    
    st.warning("⚠️ **SAMPLE DATA:** The configuration below is mocked for demonstration. Modify these mappings to match your client's specific system.")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Client Config", "Form Mappings", "Indicator Overrides", "RAG Indicators", "Processing Settings"])
    
    with tab1:
        st.subheader("Client Configuration")
        
        config_data = execute_query_df(f"""
            SELECT CONFIG_ID, CLIENT_SYSTEM_KEY, CLIENT_NAME, DESCRIPTION, 
                   VERSION, IS_ACTIVE, CREATED_BY, CREATED_TIMESTAMP,
                   TO_JSON(CONFIG_JSON) as CONFIG_JSON_TEXT
            FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG
            WHERE CONFIG_ID = '{selected_config_id}'
        """, session)
        
        if config_data is not None and len(config_data) > 0:
            row = config_data.iloc[0]
            status = "🟢 Active" if row['IS_ACTIVE'] else "⚪ Inactive"
            st.markdown(f"**Status:** {status}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**System Key:** `{row['CLIENT_SYSTEM_KEY']}`")
                st.markdown(f"**Version:** {row['VERSION']}")
                st.markdown(f"**Created By:** {row['CREATED_BY']}")
            with col2:
                st.markdown(f"**Description:** {row['DESCRIPTION']}")
                st.markdown(f"**Created:** {row['CREATED_TIMESTAMP']}")
            
            st.markdown("**Full Configuration JSON:**")
            try:
                config_json = json.loads(row['CONFIG_JSON_TEXT'])
                st.json(config_json)
            except:
                st.code(row['CONFIG_JSON_TEXT'])
    
    with tab2:
        st.subheader("Form Mappings")
        st.info("Form mappings define how client-specific form fields map to standard DRI indicators.")
        
        client_key = execute_query(f"""
            SELECT CLIENT_SYSTEM_KEY FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG WHERE CONFIG_ID = '{selected_config_id}'
        """, session)
        client_system_key = client_key[0]['CLIENT_SYSTEM_KEY'] if client_key else None
        
        mappings = execute_query_df(f"""
            SELECT MAPPING_ID, CLIENT_SYSTEM_KEY, SOURCE_TABLE, FORM_IDENTIFIER,
                   FIELD_NAME, MAPPED_INDICATOR, MAPPING_TYPE, IS_ACTIVE, NOTES
            FROM AGEDCARE.AGEDCARE.DRI_CLIENT_FORM_MAPPINGS
            WHERE CLIENT_SYSTEM_KEY = '{client_system_key}'
            ORDER BY SOURCE_TABLE, FIELD_NAME
        """, session)
        
        if mappings is not None and len(mappings) > 0:
            mappings_display = mappings[['SOURCE_TABLE', 'FORM_IDENTIFIER', 'FIELD_NAME', 'MAPPED_INDICATOR', 'MAPPING_TYPE', 'IS_ACTIVE']]
            st.dataframe(mappings_display, use_container_width=True)
            
            st.markdown("---")
            st.markdown("**Mapping Details:**")
            for idx, row in mappings.iterrows():
                status = "🟢" if row['IS_ACTIVE'] else "⚪"
                st.markdown(f"{status} **{row['FIELD_NAME']}** → `{row['MAPPED_INDICATOR']}` ({row['MAPPING_TYPE']})")
                if row['NOTES']:
                    st.caption(f"   {row['NOTES']}")
        else:
            st.info("No form mappings found for this client")
    
    with tab3:
        st.subheader("Indicator Overrides")
        st.info("Overrides allow clients to customize indicator behavior (thresholds, expiry days, etc.)")
        
        overrides = execute_query_df(f"""
            SELECT OVERRIDE_ID, CLIENT_SYSTEM_KEY, INDICATOR_ID, OVERRIDE_TYPE,
                   OVERRIDE_VALUE, REASON, IS_ACTIVE
            FROM AGEDCARE.AGEDCARE.DRI_CLIENT_INDICATOR_OVERRIDES
            WHERE CLIENT_SYSTEM_KEY = '{client_system_key}'
            ORDER BY INDICATOR_ID
        """, session)
        
        if overrides is not None and len(overrides) > 0:
            st.dataframe(overrides, use_container_width=True)
        else:
            st.info("No indicator overrides configured for this client")
    
    with tab4:
        st.subheader("DRI RAG Indicators (Knowledge Base)")
        
        indicators = execute_query_df("""
            SELECT INDICATOR_ID, INDICATOR_NAME, TEMPORAL_TYPE, DEFAULT_EXPIRY_DAYS,
                   DEFINITION
            FROM AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS
            ORDER BY INDICATOR_ID
        """, session)
        
        if indicators is not None and len(indicators) > 0:
            st.metric("Total Indicators", len(indicators))
            
            temporal_filter = st.selectbox("Filter by Type", ["All", "chronic", "acute", "recurrent"])
            
            if temporal_filter != "All":
                indicators = indicators[indicators['TEMPORAL_TYPE'] == temporal_filter]
            
            st.dataframe(indicators, use_container_width=True)
            
            st.markdown("---")
            selected_indicator = st.selectbox("View Details", indicators['INDICATOR_ID'].tolist())
            
            if selected_indicator:
                detail = execute_query_df(f"""
                    SELECT * FROM AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS
                    WHERE INDICATOR_ID = '{selected_indicator}'
                """, session)
                
                if detail is not None and len(detail) > 0:
                    row = detail.iloc[0]
                    st.markdown(f"### {row['INDICATOR_NAME']}")
                    st.markdown(f"**Definition:** {row['DEFINITION']}")
                    st.markdown(f"**Type:** {row['TEMPORAL_TYPE']}")
                    st.markdown(f"**Expiry Days:** {row['DEFAULT_EXPIRY_DAYS'] or 'N/A (chronic)'}")
                    st.markdown(f"**Include When:** {row['INCLUSION_CRITERIA']}")
                    st.markdown(f"**Exclude When:** {row['EXCLUSION_CRITERIA']}")
        else:
            st.info("No indicators found")

    with tab5:
        st.subheader("Processing Settings")
        st.info("All production settings for nightly batch processing are stored per-client in this table. The batch job reads this configuration directly.")
        
        db_production_config = execute_query(f"""
            SELECT 
                CONFIG_JSON:production_settings:model::VARCHAR as PROD_MODEL,
                CONFIG_JSON:production_settings:prompt_text::VARCHAR as PROD_PROMPT_TEXT,
                CONFIG_JSON:production_settings:prompt_version::VARCHAR as PROD_PROMPT_VERSION,
                CONFIG_JSON:production_settings:batch_schedule::VARCHAR as BATCH_SCHEDULE,
                CONFIG_JSON:client_settings:context_threshold::NUMBER as CONTEXT_THRESHOLD
            FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG 
            WHERE CONFIG_ID = '{selected_config_id}'
        """, session)
        
        prod_model = db_production_config[0]['PROD_MODEL'] if db_production_config and db_production_config[0]['PROD_MODEL'] else 'claude-3-5-sonnet'
        prod_prompt_text = db_production_config[0]['PROD_PROMPT_TEXT'] if db_production_config and db_production_config[0]['PROD_PROMPT_TEXT'] else None
        prod_prompt_version = db_production_config[0]['PROD_PROMPT_VERSION'] if db_production_config and db_production_config[0]['PROD_PROMPT_VERSION'] else 'v1.0'
        batch_schedule = db_production_config[0]['BATCH_SCHEDULE'] if db_production_config and db_production_config[0]['BATCH_SCHEDULE'] else '0 0 * * *'
        db_threshold = db_production_config[0]['CONTEXT_THRESHOLD'] if db_production_config and db_production_config[0]['CONTEXT_THRESHOLD'] else 6000
        
        st.markdown("### 🤖 Production Model")
        st.caption(f"Current production model: **{prod_model}**")
        
        model_options = [
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
        
        default_model_idx = model_options.index(prod_model) if prod_model in model_options else 3
        selected_prod_model = st.selectbox(
            "Select Model for Production",
            model_options,
            index=default_model_idx,
            help="This model will be used by the nightly batch process"
        )
        
        if st.button("🚀 Save Model for Production", key="save_model_prod"):
            try:
                execute_query(f"""
                    UPDATE AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG 
                    SET CONFIG_JSON = OBJECT_INSERT(
                        CONFIG_JSON, 
                        'production_settings', 
                        OBJECT_INSERT(
                            COALESCE(CONFIG_JSON:production_settings, OBJECT_CONSTRUCT()),
                            'model', '{selected_prod_model}', TRUE
                        ),
                        TRUE
                    ),
                    MODIFIED_BY = CURRENT_USER(),
                    MODIFIED_TIMESTAMP = CURRENT_TIMESTAMP()
                    WHERE CONFIG_ID = '{selected_config_id}'
                """, session)
                st.success(f"Production model saved: **{selected_prod_model}**")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")
        
        st.markdown("---")
        st.markdown("### 📝 Production Prompt")
        st.caption(f"Current prompt version: **{prod_prompt_version}**")
        
        prompt_versions = execute_query_df("""
            SELECT VERSION_NUMBER, DESCRIPTION, PROMPT_TEXT, IS_ACTIVE, CREATED_TIMESTAMP
            FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS
            ORDER BY CREATED_TIMESTAMP DESC
        """, session)
        
        if prompt_versions is not None and len(prompt_versions) > 0:
            version_list = prompt_versions['VERSION_NUMBER'].tolist()
            default_prompt_idx = version_list.index(prod_prompt_version) if prod_prompt_version in version_list else 0
            
            selected_version_for_copy = st.selectbox(
                "Copy Prompt from Version (Template)",
                version_list,
                index=default_prompt_idx,
                help="Select a prompt version template to copy, then customize below"
            )
            
            selected_prompt_info = prompt_versions[prompt_versions['VERSION_NUMBER'] == selected_version_for_copy].iloc[0]
            st.caption(f"Template: {selected_prompt_info['DESCRIPTION']} | Created: {selected_prompt_info['CREATED_TIMESTAMP']}")
            
            template_prompt_text = selected_prompt_info['PROMPT_TEXT']
            
            if st.button("📋 Load Template", key="load_template"):
                st.session_state['editing_prompt_text'] = template_prompt_text
                st.rerun()
        
        default_prompt_display = st.session_state.get('editing_prompt_text', prod_prompt_text or template_prompt_text if 'template_prompt_text' in dir() else '')
        
        st.markdown("**Production Prompt Text** (stored directly in client config):")
        edited_prompt_text = st.text_area(
            "Prompt Text",
            value=default_prompt_display,
            height=300,
            help="This exact prompt text will be used for nightly batch processing for this client"
        )
        
        new_version_label = st.text_input("Version Label", value=prod_prompt_version, help="Label for this prompt version (e.g., v1.1, v2.0)")
        
        if st.button("🚀 Save Prompt for Production", key="save_prompt_prod"):
            try:
                escaped_prompt = edited_prompt_text.replace("'", "''").replace("\\", "\\\\")
                execute_query(f"""
                    UPDATE AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG 
                    SET CONFIG_JSON = OBJECT_INSERT(
                        CONFIG_JSON, 
                        'production_settings', 
                        OBJECT_INSERT(
                            OBJECT_INSERT(
                                COALESCE(CONFIG_JSON:production_settings, OBJECT_CONSTRUCT()),
                                'prompt_text', '{escaped_prompt}', TRUE
                            ),
                            'prompt_version', '{new_version_label}', TRUE
                        ),
                        TRUE
                    ),
                    MODIFIED_BY = CURRENT_USER(),
                    MODIFIED_TIMESTAMP = CURRENT_TIMESTAMP()
                    WHERE CONFIG_ID = '{selected_config_id}'
                """, session)
                st.success(f"Production prompt saved for **{selected_client_display}** as version **{new_version_label}**")
                if 'editing_prompt_text' in st.session_state:
                    del st.session_state['editing_prompt_text']
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")
        
        st.markdown("---")
        st.markdown("### ⏰ Batch Schedule")
        st.caption(f"Current schedule: **{batch_schedule}** (cron format)")
        
        schedule_options = {
            "Midnight (00:00)": "0 0 * * *",
            "1:00 AM": "0 1 * * *",
            "2:00 AM": "0 2 * * *",
            "3:00 AM": "0 3 * * *",
            "4:00 AM": "0 4 * * *",
            "5:00 AM": "0 5 * * *",
            "6:00 AM": "0 6 * * *"
        }
        
        current_schedule_name = [k for k, v in schedule_options.items() if v == batch_schedule]
        default_schedule = current_schedule_name[0] if current_schedule_name else "Midnight (00:00)"
        
        selected_schedule_name = st.selectbox(
            "Nightly Batch Start Time",
            list(schedule_options.keys()),
            index=list(schedule_options.keys()).index(default_schedule),
            help="When the nightly batch job runs to process delta records"
        )
        selected_schedule = schedule_options[selected_schedule_name]
        
        st.info("**Delta Processing:** The nightly batch only processes records that have changed since the last successful run.")
        
        if st.button("🚀 Save Schedule for Production", key="save_schedule_prod"):
            try:
                execute_query(f"""
                    UPDATE AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG 
                    SET CONFIG_JSON = OBJECT_INSERT(
                        CONFIG_JSON, 
                        'production_settings', 
                        OBJECT_INSERT(
                            COALESCE(CONFIG_JSON:production_settings, OBJECT_CONSTRUCT()),
                            'batch_schedule', '{selected_schedule}', TRUE
                        ),
                        TRUE
                    ),
                    MODIFIED_BY = CURRENT_USER(),
                    MODIFIED_TIMESTAMP = CURRENT_TIMESTAMP()
                    WHERE CONFIG_ID = '{selected_config_id}'
                """, session)
                st.success(f"Batch schedule saved: **{selected_schedule_name}** ({selected_schedule})")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")
        
        st.markdown("---")
        st.markdown("### 📊 Adaptive Token Sizing")
        st.markdown("""
        The LLM analysis uses **adaptive token sizing** to optimize performance during batch processing.
        A pre-query measures each resident's context size (notes, meds, observations, forms) before calling the LLM.
        """)
        
        current_threshold = st.session_state.get('context_threshold', db_threshold)
        st.caption(f"Production value: **{db_threshold:,}** | Session value: **{current_threshold:,}**")
        
        new_threshold = st.number_input(
            "Context Threshold (characters)",
            min_value=2000,
            max_value=20000,
            value=current_threshold,
            step=500,
            help="Residents with context below this threshold use standard mode (faster). Above uses large mode (slower but complete)."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Standard Mode** (below threshold)")
            st.markdown("- `max_tokens`: 4,096")
            st.markdown("- ⚡ ~2-3x faster")
            st.markdown("- ✅ Ideal for residents with few notes")
        with col2:
            st.markdown("**Large Mode** (above threshold)")
            st.markdown("- `max_tokens`: 16,384")
            st.markdown("- 🐢 Slower processing")
            st.markdown("- ✅ Prevents truncation for complex cases")
        
        st.markdown("#### Trade-offs")
        st.warning("""
        **↓ Lower threshold** = More residents use large mode = Slower batch, but fewer truncation failures  
        **↑ Higher threshold** = More residents use standard mode = Faster batch, but risk truncation for data-heavy residents
        """)
        
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("🧪 Save for Testing", type="secondary", use_container_width=True):
                st.session_state['context_threshold'] = new_threshold
                st.success(f"Session threshold set to {new_threshold:,} characters")
                st.caption("This value will be used for interactive testing in this session.")
        
        with btn_col2:
            if st.button("🚀 Save for Production", type="primary", use_container_width=True, key="save_threshold_prod"):
                try:
                    execute_query(f"""
                        UPDATE AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG 
                        SET CONFIG_JSON = OBJECT_INSERT(
                            CONFIG_JSON, 
                            'client_settings', 
                            OBJECT_INSERT(CONFIG_JSON:client_settings, 'context_threshold', {new_threshold}, TRUE),
                            TRUE
                        ),
                        MODIFIED_BY = CURRENT_USER(),
                        MODIFIED_TIMESTAMP = CURRENT_TIMESTAMP()
                        WHERE CONFIG_ID = '{selected_config_id}'
                    """, session)
                    st.session_state['context_threshold'] = new_threshold
                    st.success(f"Production threshold saved: {new_threshold:,} characters")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save: {e}")

else:
    st.error("Failed to connect to Snowflake")
