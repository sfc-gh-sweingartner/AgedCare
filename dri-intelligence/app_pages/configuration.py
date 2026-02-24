import streamlit as st
import json

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

session = get_snowflake_session()

if session:
    with st.expander("How to use this page", expanded=False, icon=":material/help:"):
        st.markdown("""
### Purpose
This is the **administration hub** for configuring the DRI Intelligence system. It contains client settings, form mappings, and **production deployment settings**.

### Tabs Overview

| Tab | Purpose |
|-----|---------|
| **Client Config** | View/edit client details and full JSON configuration |
| **Form Mappings** | See how client-specific form fields map to DRI indicators |
| **DRI Rules** | View/edit all 33 deficit detection rules with versioning |
| **Processing Settings** | **Configure production model, prompt, and batch schedule** |

### Processing Settings (Most Important)
This tab controls what runs during **nightly batch processing**:
- **Production Model**: Which LLM model to use (recommend Claude 4.5 variants)
- **Production Prompt**: The exact prompt text used for batch analysis
- **Batch Schedule**: When the nightly job runs (cron format)
- **Adaptive Token Sizing**: Threshold for standard vs large token mode

### Workflow
1. Test prompts in the **Prompt Engineering** page
2. Once satisfied, come here to **Processing Settings**
3. Select your tested model and load your prompt template
4. Click **Save for Production** to deploy
5. The nightly batch will use these settings automatically

### Tips
- Always test thoroughly in Prompt Engineering before saving to production
- Use **Claude vs Regex** comparison to validate accuracy improvements
- The context threshold affects processing speed vs completeness tradeoff
- Lower threshold = more residents use large mode (slower but complete)
        """)

    clients = execute_query_df("""
        SELECT CONFIG_ID, CLIENT_SYSTEM_KEY, CLIENT_NAME, IS_ACTIVE
        FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG
        ORDER BY CLIENT_NAME
    """, session)
    
    if clients is not None and len(clients) > 0:
        client_options = {f"{row['CLIENT_NAME']} ({row['CLIENT_SYSTEM_KEY']})": row['CONFIG_ID'] for _, row in clients.iterrows()}
        
        st.subheader("Select client")
        selected_client_display = st.selectbox(
            "Client",
            list(client_options.keys()),
            help="All configuration changes will apply to the selected client"
        )
        selected_config_id = client_options[selected_client_display]
    else:
        st.error("No clients found in configuration table", icon=":material/error:")
        st.stop()
    
    st.warning("**Sample data:** The configuration below is mocked for demonstration. Modify these mappings to match your client's specific system.", icon=":material/warning:")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Client config", "Form mappings", "DRI Rules", "Processing settings"])
    
    with tab1:
        st.subheader("Client configuration")
        
        config_data = execute_query_df(f"""
            SELECT CONFIG_ID, CLIENT_SYSTEM_KEY, CLIENT_NAME, DESCRIPTION, 
                   VERSION, IS_ACTIVE, CREATED_BY, CREATED_TIMESTAMP,
                   TO_JSON(CONFIG_JSON) as CONFIG_JSON_TEXT
            FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG
            WHERE CONFIG_ID = '{selected_config_id}'
        """, session)
        
        if config_data is not None and len(config_data) > 0:
            row = config_data.iloc[0]
            if row['IS_ACTIVE']:
                st.badge("Active", icon=":material/check:", color="green")
            else:
                st.badge("Inactive", color="gray")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**System key:** `{row['CLIENT_SYSTEM_KEY']}`")
                st.markdown(f"**Version:** {row['VERSION']}")
                st.markdown(f"**Created by:** {row['CREATED_BY']}")
            with col2:
                st.markdown(f"**Description:** {row['DESCRIPTION']}")
                st.markdown(f"**Created:** {row['CREATED_TIMESTAMP']}")
            
            st.markdown("**Full configuration JSON:**")
            try:
                config_json = json.loads(row['CONFIG_JSON_TEXT'])
                st.json(config_json)
            except:
                st.code(row['CONFIG_JSON_TEXT'])
    
    with tab2:
        st.subheader("Form mappings")
        st.caption("Form mappings define how client-specific form fields map to standard DRI indicators.")
        
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
            
            st.markdown("**Mapping details:**")
            for idx, row in mappings.iterrows():
                if row['IS_ACTIVE']:
                    st.markdown(f":material/check_circle: **{row['FIELD_NAME']}** → `{row['MAPPED_INDICATOR']}` ({row['MAPPING_TYPE']})")
                else:
                    st.markdown(f":material/circle: **{row['FIELD_NAME']}** → `{row['MAPPED_INDICATOR']}` ({row['MAPPING_TYPE']})")
                if row['NOTES']:
                    st.caption(f"   {row['NOTES']}")
        else:
            st.info("No form mappings found for this client", icon=":material/info:")
    
    with tab3:
        st.subheader("DRI Rules")
        st.caption("Unified deficit detection rules with version control. Rules define how deficits are detected including temporal behavior, keywords, and thresholds.")
        
        current_version = execute_query("""
            SELECT DISTINCT VERSION_NUMBER, VERSION_DESCRIPTION 
            FROM AGEDCARE.AGEDCARE.DRI_RULES 
            WHERE IS_CURRENT_VERSION = TRUE
            LIMIT 1
        """, session)
        
        if current_version:
            st.success(f"**Current Version:** {current_version[0]['VERSION_NUMBER']} - {current_version[0]['VERSION_DESCRIPTION'] or 'No description'}", icon=":material/verified:")
        
        dri_rules = execute_query_df("""
            SELECT DEFICIT_NUMBER, DEFICIT_ID, DEFICIT_NAME, DOMAIN, DEFICIT_TYPE, 
                   EXPIRY_DAYS, RENEWAL_REMINDER_DAYS, LOOKBACK_DAYS_HISTORIC,
                   KEYWORDS_TO_SEARCH, RULES_JSON, IS_ACTIVE
            FROM AGEDCARE.AGEDCARE.DRI_RULES
            WHERE IS_CURRENT_VERSION = TRUE
            ORDER BY DEFICIT_NUMBER
        """, session)
        
        if dri_rules is not None and len(dri_rules) > 0:
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("Total deficits", len(dri_rules))
            with col_m2:
                persistent = len(dri_rules[dri_rules['DEFICIT_TYPE'] == 'PERSISTENT'])
                st.metric("Persistent", persistent)
            with col_m3:
                fluctuating = len(dri_rules[dri_rules['DEFICIT_TYPE'] == 'FLUCTUATING'])
                st.metric("Fluctuating", fluctuating)
            with col_m4:
                active_rules = len(dri_rules[dri_rules['IS_ACTIVE'] == True])
                st.metric("Active", active_rules)
            
            type_filter = st.selectbox("Filter by type", ["All", "PERSISTENT", "FLUCTUATING"], key="dri_type_filter")
            domain_filter = st.selectbox("Filter by domain", ["All"] + sorted(dri_rules['DOMAIN'].unique().tolist()), key="dri_domain_filter")
            
            filtered_rules = dri_rules.copy()
            if type_filter != "All":
                filtered_rules = filtered_rules[filtered_rules['DEFICIT_TYPE'] == type_filter]
            if domain_filter != "All":
                filtered_rules = filtered_rules[filtered_rules['DOMAIN'] == domain_filter]
            
            st.dataframe(
                filtered_rules[['DEFICIT_ID', 'DEFICIT_NAME', 'DOMAIN', 'DEFICIT_TYPE', 'EXPIRY_DAYS', 'RENEWAL_REMINDER_DAYS', 'LOOKBACK_DAYS_HISTORIC']],
                use_container_width=True,
                column_config={
                    'DEFICIT_ID': st.column_config.TextColumn('ID', width='small'),
                    'DEFICIT_NAME': st.column_config.TextColumn('Deficit Name', width='medium'),
                    'DOMAIN': st.column_config.TextColumn('Domain', width='medium'),
                    'DEFICIT_TYPE': st.column_config.TextColumn('Type', width='small'),
                    'EXPIRY_DAYS': st.column_config.NumberColumn('Expiry (days)', width='small', help='0 = Never expires (persistent)'),
                    'RENEWAL_REMINDER_DAYS': st.column_config.NumberColumn('Reminder (days)', width='small', help='Days before expiry to show in review queue'),
                    'LOOKBACK_DAYS_HISTORIC': st.column_config.TextColumn('Lookback', width='small')
                }
            )
            
            st.subheader("Rule details")
            selected_deficit = st.selectbox(
                "Select deficit to view full rules",
                filtered_rules['DEFICIT_ID'].tolist(),
                format_func=lambda x: f"{x} - {filtered_rules[filtered_rules['DEFICIT_ID']==x]['DEFICIT_NAME'].iloc[0]}",
                key="dri_detail_select"
            )
            
            if selected_deficit:
                deficit_row = filtered_rules[filtered_rules['DEFICIT_ID'] == selected_deficit].iloc[0]
                
                with st.container(border=True):
                    st.markdown(f"### {deficit_row['DEFICIT_NAME']} ({deficit_row['DEFICIT_ID']})")
                    
                    edit_mode = st.toggle("Edit mode", key=f"edit_mode_{selected_deficit}")
                    
                    if edit_mode:
                        st.info("Edit the deficit settings below and click Save to update.", icon=":material/edit:")
                        
                        edit_col1, edit_col2 = st.columns(2)
                        with edit_col1:
                            edit_deficit_type = st.selectbox(
                                "Deficit Type",
                                ["PERSISTENT", "FLUCTUATING"],
                                index=0 if deficit_row['DEFICIT_TYPE'] == 'PERSISTENT' else 1,
                                key=f"edit_type_{selected_deficit}"
                            )
                            edit_domain = st.text_input(
                                "Domain",
                                value=deficit_row['DOMAIN'],
                                key=f"edit_domain_{selected_deficit}"
                            )
                            edit_lookback = st.text_input(
                                "Lookback (days or 'all')",
                                value=str(deficit_row['LOOKBACK_DAYS_HISTORIC'] or 'all'),
                                key=f"edit_lookback_{selected_deficit}"
                            )
                        with edit_col2:
                            edit_expiry = st.number_input(
                                "Expiry Days (0 = never)",
                                value=int(deficit_row['EXPIRY_DAYS'] or 0),
                                min_value=0,
                                max_value=365,
                                key=f"edit_expiry_{selected_deficit}"
                            )
                            edit_reminder = st.number_input(
                                "Renewal Reminder Days",
                                value=int(deficit_row['RENEWAL_REMINDER_DAYS'] or 7),
                                min_value=1,
                                max_value=30,
                                key=f"edit_reminder_{selected_deficit}"
                            )
                            edit_active = st.checkbox(
                                "Is Active",
                                value=bool(deficit_row['IS_ACTIVE']),
                                key=f"edit_active_{selected_deficit}"
                            )
                        
                        st.markdown("---")
                        st.markdown("**Detection Rules**")
                        
                        try:
                            rules_json = deficit_row['RULES_JSON']
                            if isinstance(rules_json, str):
                                rules_json = json.loads(rules_json)
                            
                            edited_rules = []
                            if rules_json:
                                for i, rule in enumerate(rules_json):
                                    with st.expander(f"Rule {rule.get('rule_number', i+1)}: {rule.get('rule_description', 'N/A')}", expanded=i==0):
                                        rule_edit_col1, rule_edit_col2 = st.columns(2)
                                        with rule_edit_col1:
                                            rule_status = st.selectbox(
                                                "Status",
                                                ["active", "inactive"],
                                                index=0 if rule.get('rule_status', 'active') == 'active' else 1,
                                                key=f"rule_status_{selected_deficit}_{i}"
                                            )
                                            rule_type = st.selectbox(
                                                "Rule Type",
                                                ["keyword_search", "specific_value", "aggregation"],
                                                index=["keyword_search", "specific_value", "aggregation"].index(rule.get('rule_type', 'keyword_search')),
                                                key=f"rule_type_{selected_deficit}_{i}"
                                            )
                                            rule_source = st.selectbox(
                                                "Source Table",
                                                ["ACTIVE_RESIDENT_MEDICAL_PROFILE", "ACTIVE_RESIDENT_NOTES", "ACTIVE_RESIDENT_MEDICATION", 
                                                 "ACTIVE_RESIDENT_OBSERVATIONS", "ACTIVE_RESIDENT_ASSESSMENT_FORMS", "ACTIVE_RESIDENT_OBSERVATION_GROUP"],
                                                index=["ACTIVE_RESIDENT_MEDICAL_PROFILE", "ACTIVE_RESIDENT_NOTES", "ACTIVE_RESIDENT_MEDICATION", 
                                                       "ACTIVE_RESIDENT_OBSERVATIONS", "ACTIVE_RESIDENT_ASSESSMENT_FORMS", "ACTIVE_RESIDENT_OBSERVATION_GROUP"].index(rule.get('source_type', 'ACTIVE_RESIDENT_NOTES')) if rule.get('source_type') in ["ACTIVE_RESIDENT_MEDICAL_PROFILE", "ACTIVE_RESIDENT_NOTES", "ACTIVE_RESIDENT_MEDICATION", "ACTIVE_RESIDENT_OBSERVATIONS", "ACTIVE_RESIDENT_ASSESSMENT_FORMS", "ACTIVE_RESIDENT_OBSERVATION_GROUP"] else 0,
                                                key=f"rule_source_{selected_deficit}_{i}"
                                            )
                                        with rule_edit_col2:
                                            rule_threshold = st.number_input(
                                                "Threshold",
                                                value=int(rule.get('threshold', 1)) if rule.get('threshold') and str(rule.get('threshold')).isdigit() else 1,
                                                min_value=1,
                                                key=f"rule_threshold_{selected_deficit}_{i}"
                                            )
                                            rule_desc = st.text_input(
                                                "Description",
                                                value=rule.get('rule_description', ''),
                                                key=f"rule_desc_{selected_deficit}_{i}"
                                            )
                                            rule_search_field = st.text_input(
                                                "Search Field",
                                                value=str(rule.get('search_field', '')) if rule.get('search_field') and str(rule.get('search_field')) != 'nan' else '',
                                                key=f"rule_search_{selected_deficit}_{i}"
                                            )
                                        
                                        st.markdown("**Filters:**")
                                        functions = rule.get('functions', [])
                                        edited_functions = []
                                        for j, func in enumerate(functions):
                                            func_col1, func_col2, func_col3 = st.columns([1, 1, 2])
                                            with func_col1:
                                                func_type = st.selectbox(
                                                    "Type",
                                                    ["inclusion_filter", "exclusion_filter", "aggregation"],
                                                    index=["inclusion_filter", "exclusion_filter", "aggregation"].index(func.get('function_type', 'inclusion_filter')),
                                                    key=f"func_type_{selected_deficit}_{i}_{j}"
                                                )
                                            with func_col2:
                                                func_key = st.text_input(
                                                    "Key",
                                                    value=func.get('key', ''),
                                                    key=f"func_key_{selected_deficit}_{i}_{j}"
                                                )
                                            with func_col3:
                                                func_value = st.text_input(
                                                    "Value",
                                                    value=func.get('value', ''),
                                                    key=f"func_value_{selected_deficit}_{i}_{j}"
                                                )
                                            edited_functions.append({
                                                "function_type": func_type,
                                                "key": func_key,
                                                "value": func_value
                                            })
                                        
                                        edited_rules.append({
                                            "rule_number": rule.get('rule_number', i+1),
                                            "rule_status": rule_status,
                                            "rule_type": rule_type,
                                            "rule_description": rule_desc,
                                            "source_type": rule_source,
                                            "source_table_description": rule.get('source_table_description', ''),
                                            "search_field": rule_search_field if rule_search_field else None,
                                            "threshold": rule_threshold,
                                            "functions": edited_functions
                                        })
                            
                            st.session_state[f'edited_rules_{selected_deficit}'] = edited_rules
                            
                        except Exception as e:
                            st.error(f"Error parsing rules for editing: {e}")
                        
                        st.markdown("---")
                        if st.button("Save Deficit Changes", type="primary", key=f"save_deficit_{selected_deficit}", icon=":material/save:"):
                            try:
                                edited_rules_json = json.dumps(st.session_state.get(f'edited_rules_{selected_deficit}', []))
                                escaped_rules = edited_rules_json.replace("'", "''")
                                
                                execute_query(f"""
                                    UPDATE AGEDCARE.AGEDCARE.DRI_RULES 
                                    SET 
                                        DEFICIT_TYPE = '{edit_deficit_type}',
                                        DOMAIN = '{edit_domain}',
                                        EXPIRY_DAYS = {edit_expiry},
                                        RENEWAL_REMINDER_DAYS = {edit_reminder},
                                        LOOKBACK_DAYS_HISTORIC = '{edit_lookback}',
                                        IS_ACTIVE = {edit_active},
                                        RULES_JSON = PARSE_JSON('{escaped_rules}'),
                                        MODIFIED_BY = CURRENT_USER(),
                                        MODIFIED_TIMESTAMP = CURRENT_TIMESTAMP()
                                    WHERE DEFICIT_ID = '{selected_deficit}' AND IS_CURRENT_VERSION = TRUE
                                """, session)
                                st.success(f"Saved changes for {selected_deficit}", icon=":material/check_circle:")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to save: {e}", icon=":material/error:")
                    
                    else:
                        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                        with col_d1:
                            if deficit_row['DEFICIT_TYPE'] == 'PERSISTENT':
                                st.badge("PERSISTENT", icon=":material/all_inclusive:", color="blue")
                            else:
                                st.badge("FLUCTUATING", icon=":material/timelapse:", color="orange")
                        with col_d2:
                            st.markdown(f"**Domain:** {deficit_row['DOMAIN']}")
                        with col_d3:
                            expiry = deficit_row['EXPIRY_DAYS']
                            st.markdown(f"**Expiry:** {expiry if expiry > 0 else 'Never'}")
                        with col_d4:
                            st.markdown(f"**Reminder:** {deficit_row['RENEWAL_REMINDER_DAYS']} days")
                        
                        st.markdown("---")
                        st.markdown(f"**Lookback period:** {deficit_row['LOOKBACK_DAYS_HISTORIC']}")
                        st.markdown(f"**Active:** {'Yes' if deficit_row['IS_ACTIVE'] else 'No'}")
                        
                        st.markdown("---")
                        st.markdown("**Detection Rules:**")
                        
                        try:
                            rules_json = deficit_row['RULES_JSON']
                            if isinstance(rules_json, str):
                                rules_json = json.loads(rules_json)
                            
                            if rules_json:
                                for i, rule in enumerate(rules_json):
                                    rule_status = rule.get('rule_status', 'active')
                                    status_icon = ":material/check_circle:" if rule_status == 'active' else ":material/cancel:"
                                    
                                    with st.expander(f"{status_icon} Rule {rule.get('rule_number', i+1)}: {rule.get('rule_description', 'N/A')}", expanded=i==0):
                                        rule_cols = st.columns([1, 1, 1, 1])
                                        with rule_cols[0]:
                                            if rule_status == 'active':
                                                st.badge("active", icon=":material/check:", color="green")
                                            else:
                                                st.badge("inactive", color="gray")
                                        with rule_cols[1]:
                                            rule_type = rule.get('rule_type', 'unknown')
                                            if rule_type == 'keyword_search':
                                                st.badge("keyword_search", icon=":material/search:", color="blue")
                                            elif rule_type == 'specific_value':
                                                st.badge("specific_value", icon=":material/check_box:", color="purple")
                                            elif rule_type == 'aggregation':
                                                st.badge("aggregation", icon=":material/functions:", color="orange")
                                            else:
                                                st.badge(rule_type, color="gray")
                                        with rule_cols[2]:
                                            st.markdown(f"**Source:** `{rule.get('source_type', 'N/A')}`")
                                        with rule_cols[3]:
                                            st.markdown(f"**Threshold:** {rule.get('threshold', 1)}")
                                        
                                        search_field = rule.get('search_field')
                                        if search_field and str(search_field) != 'nan':
                                            st.markdown(f"**Search field:** `{search_field}`")
                                        
                                        functions = rule.get('functions', [])
                                        if functions:
                                            st.markdown("**Filters:**")
                                            for func in functions:
                                                func_type = func.get('function_type', '')
                                                key = func.get('key', '')
                                                value = func.get('value', '')
                                                if func_type == 'inclusion_filter':
                                                    st.markdown(f"- ✅ Include: `{key}` = `{value}`")
                                                elif func_type == 'exclusion_filter':
                                                    st.markdown(f"- ❌ Exclude: `{key}` = `{value}`")
                                                elif func_type == 'aggregation':
                                                    st.markdown(f"- 📊 Aggregate: `{key}` → `{value}`")
                            else:
                                st.info("No detection rules configured for this deficit", icon=":material/info:")
                        except Exception as e:
                            st.error(f"Error parsing rules: {e}")
                            st.json(deficit_row['RULES_JSON'])
            
            st.markdown("---")
            st.subheader("Version management")
            
            all_versions = execute_query_df("""
                SELECT DISTINCT VERSION_NUMBER, VERSION_DESCRIPTION, IS_CURRENT_VERSION, 
                       MIN(CREATED_TIMESTAMP) as CREATED_TIMESTAMP
                FROM AGEDCARE.AGEDCARE.DRI_RULES
                GROUP BY VERSION_NUMBER, VERSION_DESCRIPTION, IS_CURRENT_VERSION
                ORDER BY CREATED_TIMESTAMP DESC
            """, session)
            
            if all_versions is not None and len(all_versions) > 0:
                st.dataframe(all_versions, use_container_width=True)
            
            with st.expander("Create new version", expanded=False):
                new_version_number = st.text_input("New version number", value="v1.1", key="new_rule_version")
                new_version_desc = st.text_input("Version description", value="Updated rules", key="new_rule_desc")
                
                if st.button("Save as new version", key="save_new_version", icon=":material/save:"):
                    try:
                        execute_query(f"""
                            UPDATE AGEDCARE.AGEDCARE.DRI_RULES 
                            SET IS_CURRENT_VERSION = FALSE 
                            WHERE IS_CURRENT_VERSION = TRUE
                        """, session)
                        
                        execute_query(f"""
                            INSERT INTO AGEDCARE.AGEDCARE.DRI_RULES (
                                VERSION_NUMBER, VERSION_DESCRIPTION, IS_CURRENT_VERSION,
                                DEFICIT_NUMBER, DEFICIT_ID, DOMAIN, DEFICIT_NAME, DEFICIT_TYPE,
                                EXPIRY_DAYS, LOOKBACK_DAYS_HISTORIC, LOOKBACK_DAYS_DELTA,
                                RENEWAL_REMINDER_DAYS, KEYWORDS_TO_SEARCH, RULES_JSON,
                                IS_ACTIVE, CREATED_BY
                            )
                            SELECT 
                                '{new_version_number}', '{new_version_desc}', TRUE,
                                DEFICIT_NUMBER, DEFICIT_ID, DOMAIN, DEFICIT_NAME, DEFICIT_TYPE,
                                EXPIRY_DAYS, LOOKBACK_DAYS_HISTORIC, LOOKBACK_DAYS_DELTA,
                                RENEWAL_REMINDER_DAYS, KEYWORDS_TO_SEARCH, RULES_JSON,
                                IS_ACTIVE, CURRENT_USER()
                            FROM AGEDCARE.AGEDCARE.DRI_RULES
                            WHERE VERSION_NUMBER = (
                                SELECT VERSION_NUMBER FROM AGEDCARE.AGEDCARE.DRI_RULES 
                                WHERE IS_CURRENT_VERSION = FALSE 
                                ORDER BY CREATED_TIMESTAMP DESC LIMIT 1
                            )
                        """, session)
                        st.success(f"Created new version: {new_version_number}", icon=":material/check_circle:")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create version: {e}", icon=":material/error:")
        else:
            st.info("No DRI rules found. Please load rules from the business rules template.", icon=":material/info:")
            
    with tab4:
        st.subheader("Processing settings")
        st.caption("All production settings for nightly batch processing are stored per-client in this table. The batch job reads this configuration directly.")
        
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
        
        with st.container(border=True):
            st.markdown("**Current Production Settings Summary**")
            summary_cols = st.columns(5)
            with summary_cols[0]:
                st.markdown(f"**DRI Rules:** v1.0")
            with summary_cols[1]:
                st.markdown(f"**Prompt:** {prod_prompt_version}")
            with summary_cols[2]:
                st.markdown(f"**Model:** {prod_model}")
            with summary_cols[3]:
                st.markdown(f"**Schedule:** {batch_schedule}")
            with summary_cols[4]:
                st.markdown(f"**Token Threshold:** {db_threshold:,}")
        
        st.subheader("Production model")
        st.caption(f"Current production model: **{prod_model}**")
        
        model_options = [
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
        
        default_model_idx = model_options.index(prod_model) if prod_model in model_options else 3
        selected_prod_model = st.selectbox(
            "Select model for production",
            model_options,
            index=default_model_idx,
            help="This model will be used by the nightly batch process"
        )
        

        
        st.subheader("Production prompt")
        
        prompt_versions = execute_query_df("""
            SELECT VERSION_NUMBER, DESCRIPTION, PROMPT_TEXT, IS_ACTIVE, CREATED_TIMESTAMP
            FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS
            ORDER BY CREATED_TIMESTAMP DESC
        """, session)
        
        if prompt_versions is not None and len(prompt_versions) > 0:
            version_list = prompt_versions['VERSION_NUMBER'].tolist()
            default_prompt_idx = version_list.index(prod_prompt_version) if prod_prompt_version in version_list else 0
            
            selected_prompt_version = st.selectbox(
                "Prompt version",
                version_list,
                index=default_prompt_idx,
                help="Select the prompt version to use for production"
            )
            
            selected_prompt_info = prompt_versions[prompt_versions['VERSION_NUMBER'] == selected_prompt_version].iloc[0]
            st.caption(f"{selected_prompt_info['DESCRIPTION']} | Created: {selected_prompt_info['CREATED_TIMESTAMP']}")
            
            prompt_text_display = selected_prompt_info['PROMPT_TEXT']
            
            st.text_area(
                "Prompt text (read-only)",
                value=prompt_text_display,
                height=300,
                disabled=True,
                help="This prompt text will be used for nightly batch processing"
            )
        
        st.subheader("Batch schedule")
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
            "Nightly batch start time",
            list(schedule_options.keys()),
            index=list(schedule_options.keys()).index(default_schedule),
            help="When the nightly batch job runs to process delta records"
        )
        selected_schedule = schedule_options[selected_schedule_name]
        
        st.info("**Delta processing:** The nightly batch only processes records that have changed since the last successful run.", icon=":material/info:")
        

        
        st.subheader("Adaptive token sizing")
        st.caption("The LLM analysis uses adaptive token sizing to optimize performance during batch processing. A pre-query measures each resident's context size (notes, meds, observations, forms) before calling the LLM.")
        
        current_threshold = st.session_state.get('context_threshold', db_threshold)
        st.caption(f"Production value: **{db_threshold:,}** | Session value: **{current_threshold:,}**")
        
        new_threshold = st.number_input(
            "Context threshold (characters)",
            min_value=2000,
            max_value=20000,
            value=current_threshold,
            step=500,
            help="Residents with context below this threshold use standard mode (faster). Above uses large mode (slower but complete)."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.markdown("**Standard mode** (below threshold)")
                st.markdown("- `max_tokens`: 4,096")
                st.markdown("- Fast processing")
                st.markdown("- Ideal for residents with few notes")
        with col2:
            with st.container(border=True):
                st.markdown("**Large mode** (above threshold)")
                st.markdown("- `max_tokens`: 16,384")
                st.markdown("- Slower processing")
                st.markdown("- Prevents truncation for complex cases")
        
        st.subheader("Trade-offs")
        st.warning("**Lower threshold** = More residents use large mode = Slower batch, but fewer truncation failures. **Higher threshold** = More residents use standard mode = Faster batch, but risk truncation for data-heavy residents.", icon=":material/warning:")
        
        st.markdown("---")
        if st.button("Save for production", type="primary", key="save_all_prod", icon=":material/save:", use_container_width=True):
            try:
                escaped_prompt = prompt_text_display.replace("'", "''").replace("\\", "\\\\") if 'prompt_text_display' in dir() else ''
                prompt_ver = selected_prompt_version if 'selected_prompt_version' in dir() else prod_prompt_version
                execute_query(f"""
                    UPDATE AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG 
                    SET CONFIG_JSON = OBJECT_INSERT(
                        OBJECT_INSERT(
                            CONFIG_JSON, 
                            'production_settings', 
                            OBJECT_CONSTRUCT(
                                'model', '{selected_prod_model}',
                                'prompt_text', '{escaped_prompt}',
                                'prompt_version', '{prompt_ver}',
                                'batch_schedule', '{selected_schedule}'
                            ),
                            TRUE
                        ),
                        'client_settings', 
                        OBJECT_INSERT(COALESCE(CONFIG_JSON:client_settings, OBJECT_CONSTRUCT()), 'context_threshold', {new_threshold}, TRUE),
                        TRUE
                    ),
                    MODIFIED_BY = CURRENT_USER(),
                    MODIFIED_TIMESTAMP = CURRENT_TIMESTAMP()
                    WHERE CONFIG_ID = '{selected_config_id}'
                """, session)
                st.session_state['context_threshold'] = new_threshold
                st.success(f"All production settings saved successfully!", icon=":material/check_circle:")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}", icon=":material/error:")

else:
    st.error("Failed to connect to Snowflake", icon=":material/error:")
