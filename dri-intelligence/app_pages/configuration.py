import streamlit as st
import json

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

session = get_snowflake_session()

if session:
    with st.expander("How to use this page", expanded=False, icon=":material/help:"):
        st.markdown("""
### Purpose
This is the **administration hub** for configuring the DRI Intelligence system. DRI Rules are managed globally, while client-specific settings (including which rule versions to use) are configured per client.

### Tabs Overview

| Tab | Purpose |
|-----|---------|
| **DRI Rules** | View/edit all 33 deficit detection rules with **per-deficit versioning** (global - not client specific) |
| **Client Settings** | Configure client-specific settings including which rule versions to use |

---

### Detection Modes (LLM-Optimized Rules)

The DRI system uses four **detection modes** to identify deficit indicators:

| Detection Mode | Description | Best For |
|----------------|-------------|----------|
| **clinical_reasoning** | LLM uses medical knowledge to identify conditions | Most chronic conditions |
| **structured_data** | Direct lookup from structured fields | Falls, Pain, ADL |
| **threshold_aggregation** | Count-based rules comparing totals to thresholds | Polypharmacy, Incontinence |
| **keyword_guidance** | LLM reasoning guided by specific terminology | Regulatory compliance matching |

---

### DRI Rules Tab
- All 33 deficit rules are stored in the unified `DRI_RULES` table
- Each deficit has its own version number (e.g., D001-0001, D001-0002)
- **Editing always creates a new version** - old versions retained for audit
- Rules are global - client-specific version assignments are in Client Settings

### Client Settings Tab
- Select which **rule version** to use per deficit for each client
- Configure production model, prompt, and batch schedule
- Manage adaptive token sizing settings
        """)

    tab1, tab2 = st.tabs(["DRI Rules", "Client Settings"])
    
    with tab1:
        st.subheader("DRI Rules")
        st.caption("Global deficit detection rules with version control. Editing creates a new version - select which versions to use per client in Client Settings.")
        
        rules_data = execute_query_df("""
            SELECT DISTINCT DEFICIT_ID, DEFICIT_NAME, DOMAIN, 
                   MAX(CASE WHEN IS_CURRENT_VERSION = TRUE THEN VERSION_NUMBER END) as LATEST_VERSION
            FROM AGEDCARE.AGEDCARE.DRI_RULES
            GROUP BY DEFICIT_ID, DEFICIT_NAME, DOMAIN
            ORDER BY DEFICIT_ID
        """, session)
        
        if rules_data is not None and len(rules_data) > 0:
            col_sel1, col_sel2 = st.columns([2, 1])
            with col_sel1:
                deficit_options = {f"{row['DEFICIT_ID']}: {row['DEFICIT_NAME']}": row['DEFICIT_ID'] for _, row in rules_data.iterrows()}
                selected_deficit_display = st.selectbox(
                    "Select deficit to view/edit",
                    list(deficit_options.keys()),
                    help="Choose a deficit indicator to view or edit its detection rules"
                )
                selected_deficit = deficit_options[selected_deficit_display]
            
            deficit_row_query = execute_query(f"""
                SELECT * FROM AGEDCARE.AGEDCARE.DRI_RULES 
                WHERE DEFICIT_ID = '{selected_deficit}' AND IS_CURRENT_VERSION = TRUE
            """, session)
            
            if deficit_row_query:
                deficit_row = deficit_row_query[0].as_dict()
                
                with st.container(border=True):
                    st.markdown(f"### {deficit_row['DEFICIT_NAME']} ({deficit_row['DEFICIT_ID']})")
                    st.caption(f"Current version: **{deficit_row['VERSION_NUMBER']}**")
                    
                    edit_mode = st.toggle("Edit mode", key=f"edit_mode_{selected_deficit}")
                    
                    if edit_mode:
                        st.info("Edit the deficit settings below. Saving will create a **new version** of this rule.", icon=":material/edit:")
                        
                        st.markdown("**Deficit Settings**")
                        
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
                        st.markdown("**Multi-Rule Orchestration**")
                        edit_multi_rule_guidance = st.text_area(
                            "Multi-Rule Guidance",
                            value=deficit_row.get('MULTI_RULE_GUIDANCE', '') or '',
                            height=100,
                            key=f"edit_multi_rule_guidance_{selected_deficit}",
                            help="Instructions for how to combine multiple rules (e.g., PRIMARY: clinical_reasoning, SECONDARY: keyword_guidance)"
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
                                            detection_mode_options = ["keyword_guidance", "clinical_reasoning", "structured_data", "threshold_aggregation"]
                                            current_det_mode = rule.get('detection_mode', 'keyword_guidance')
                                            det_mode_index = detection_mode_options.index(current_det_mode) if current_det_mode in detection_mode_options else 0
                                            rule_detection_mode = st.selectbox(
                                                "Detection Mode",
                                                detection_mode_options,
                                                index=det_mode_index,
                                                key=f"rule_detection_mode_{selected_deficit}_{i}"
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
                                        
                                        rule_inclusion_terms = st.text_area(
                                            "Inclusion Terms",
                                            value=rule.get('inclusion_terms', '') or '',
                                            height=80,
                                            key=f"rule_inclusion_{selected_deficit}_{i}",
                                            help="Keywords/phrases that suggest this condition (comma-separated)"
                                        )
                                        
                                        rule_exclusion_patterns = st.text_area(
                                            "Exclusion Patterns",
                                            value=rule.get('exclusion_patterns', '') or '',
                                            height=80,
                                            key=f"rule_exclusion_{selected_deficit}_{i}",
                                            help="Phrases that negate findings (comma-separated)"
                                        )
                                        
                                        rule_clinical_guidance = st.text_area(
                                            "Clinical Guidance",
                                            value=rule.get('clinical_guidance', '') or '',
                                            height=100,
                                            key=f"rule_clinical_guidance_{selected_deficit}_{i}",
                                            help="Instructions for the LLM on what to look for"
                                        )
                                        
                                        rule_regulatory_ref = st.text_input(
                                            "Regulatory Reference",
                                            value=rule.get('regulatory_reference', '') or '',
                                            key=f"rule_regulatory_ref_{selected_deficit}_{i}",
                                            help="Source standards (ACQSC, AN-ACC)"
                                        )
                                        
                                        st.markdown("**Filters:**")
                                        functions = rule.get('functions', [])
                                        if f'filters_{selected_deficit}_{i}' not in st.session_state:
                                            st.session_state[f'filters_{selected_deficit}_{i}'] = list(functions) if functions else []
                                        
                                        filter_key_options = ["form_name", "element_name", "response", "progress_note_type", 
                                                            "observation_value", "chart_name", "chart_label", "resident_id", "count"]
                                        
                                        edited_functions = []
                                        filters_to_display = st.session_state[f'filters_{selected_deficit}_{i}']
                                        
                                        for j, func in enumerate(filters_to_display):
                                            func_col1, func_col2, func_col3, func_col4 = st.columns([1.5, 1.5, 3, 0.5])
                                            with func_col1:
                                                func_type = st.selectbox(
                                                    "Type",
                                                    ["inclusion_filter", "exclusion_filter", "aggregation"],
                                                    index=["inclusion_filter", "exclusion_filter", "aggregation"].index(func.get('function_type', 'inclusion_filter')) if func.get('function_type') in ["inclusion_filter", "exclusion_filter", "aggregation"] else 0,
                                                    key=f"func_type_{selected_deficit}_{i}_{j}"
                                                )
                                            with func_col2:
                                                current_key = func.get('key', 'form_name')
                                                key_index = filter_key_options.index(current_key) if current_key in filter_key_options else 0
                                                func_key = st.selectbox(
                                                    "Key",
                                                    filter_key_options,
                                                    index=key_index,
                                                    key=f"func_key_{selected_deficit}_{i}_{j}"
                                                )
                                            with func_col3:
                                                func_value = st.text_input(
                                                    "Value",
                                                    value=func.get('value', ''),
                                                    key=f"func_value_{selected_deficit}_{i}_{j}"
                                                )
                                            with func_col4:
                                                st.write("")
                                                if st.button("🗑️", key=f"del_filter_{selected_deficit}_{i}_{j}", help="Delete filter"):
                                                    st.session_state[f'filters_{selected_deficit}_{i}'].pop(j)
                                                    st.rerun()
                                            
                                            edited_functions.append({
                                                "function_type": func_type,
                                                "key": func_key,
                                                "value": func_value
                                            })
                                        
                                        if st.button("➕ Add Filter", key=f"add_filter_{selected_deficit}_{i}"):
                                            st.session_state[f'filters_{selected_deficit}_{i}'].append({
                                                "function_type": "inclusion_filter",
                                                "key": "form_name",
                                                "value": ""
                                            })
                                            st.rerun()
                                        
                                        edited_rules.append({
                                            "rule_number": rule.get('rule_number', i+1),
                                            "rule_status": rule_status,
                                            "rule_type": rule.get('rule_type', 'keyword_search'),
                                            "detection_mode": rule_detection_mode,
                                            "rule_description": rule_desc,
                                            "source_type": rule_source,
                                            "source_table_description": rule.get('source_table_description', ''),
                                            "search_field": rule_search_field if rule_search_field else None,
                                            "threshold": rule_threshold,
                                            "inclusion_terms": rule_inclusion_terms,
                                            "exclusion_patterns": rule_exclusion_patterns,
                                            "clinical_guidance": rule_clinical_guidance,
                                            "regulatory_reference": rule_regulatory_ref,
                                            "functions": edited_functions
                                        })
                            
                            st.session_state[f'edited_rules_{selected_deficit}'] = edited_rules
                            
                        except Exception as e:
                            st.error(f"Error parsing rules for editing: {e}")
                        
                        st.markdown("---")
                        st.markdown("**Save as New Version**")
                        
                        current_version = deficit_row['VERSION_NUMBER']
                        if current_version and '-' in current_version:
                            prefix = current_version.split('-')[0]
                            current_num = int(current_version.split('-')[1])
                            next_version = f"{prefix}-{current_num + 1:04d}"
                        else:
                            next_version = f"{selected_deficit}-0001"
                        
                        st.info(f"Current version: **{current_version}** → New version: **{next_version}**", icon=":material/info:")
                        new_version_desc = st.text_input("Version description (required)", value="", key="new_rule_desc", placeholder="Describe what changed...")
                        
                        if st.button("Save as New Version", type="primary", key=f"save_new_version_{selected_deficit}", icon=":material/save:", disabled=not new_version_desc):
                            if not new_version_desc:
                                st.error("Please provide a version description", icon=":material/error:")
                            else:
                                try:
                                    edited_rules_json = json.dumps(st.session_state.get(f'edited_rules_{selected_deficit}', []))
                                    escaped_rules = edited_rules_json.replace("'", "''")
                                    escaped_multi_rule_guidance = (edit_multi_rule_guidance or '').replace("'", "''")
                                    escaped_version_desc = new_version_desc.replace("'", "''")
                                    escaped_domain = (edit_domain or '').replace("'", "''")
                                    escaped_deficit_name = (deficit_row['DEFICIT_NAME'] or '').replace("'", "''")
                                    lookback_value = f"'{edit_lookback}'" if edit_lookback and edit_lookback.lower() != 'none' else 'NULL'
                                    lookback_delta = deficit_row['LOOKBACK_DAYS_DELTA'] if deficit_row['LOOKBACK_DAYS_DELTA'] is not None else 1
                                    
                                    execute_query(f"""
                                        INSERT INTO AGEDCARE.AGEDCARE.DRI_RULES (
                                            VERSION_NUMBER, VERSION_DESCRIPTION, IS_CURRENT_VERSION,
                                            DEFICIT_NUMBER, DEFICIT_ID, DOMAIN, DEFICIT_NAME, DEFICIT_TYPE,
                                            EXPIRY_DAYS, LOOKBACK_DAYS_HISTORIC, LOOKBACK_DAYS_DELTA,
                                            RENEWAL_REMINDER_DAYS, RULES_JSON, MULTI_RULE_GUIDANCE,
                                            IS_ACTIVE, CREATED_BY
                                        )
                                        SELECT
                                            '{next_version}', '{escaped_version_desc}', TRUE,
                                            {deficit_row['DEFICIT_NUMBER']}, '{selected_deficit}', '{escaped_domain}', 
                                            '{escaped_deficit_name}', '{edit_deficit_type}',
                                            {edit_expiry}, {lookback_value}, {lookback_delta},
                                            {edit_reminder}, PARSE_JSON('{escaped_rules}'), '{escaped_multi_rule_guidance}',
                                            {edit_active}, CURRENT_USER()
                                    """, session)
                                    
                                    execute_query(f"""
                                        UPDATE AGEDCARE.AGEDCARE.DRI_RULES 
                                        SET IS_CURRENT_VERSION = FALSE 
                                        WHERE DEFICIT_ID = '{selected_deficit}' AND VERSION_NUMBER != '{next_version}'
                                    """, session)
                                    
                                    st.success(f"Created new version: {next_version}", icon=":material/check_circle:")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to save: {e}", icon=":material/error:")
                    
                    else:
                        col_d1, col_d2, col_d3 = st.columns(3)
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
                        
                        st.markdown("---")
                        st.markdown(f"**Lookback period:** {deficit_row['LOOKBACK_DAYS_HISTORIC']} | **Reminder:** {deficit_row['RENEWAL_REMINDER_DAYS']} days | **Active:** {'Yes' if deficit_row['IS_ACTIVE'] else 'No'}")
                        
                        if deficit_row.get('MULTI_RULE_GUIDANCE'):
                            st.markdown("---")
                            st.markdown("**Multi-Rule Orchestration:**")
                            st.info(deficit_row['MULTI_RULE_GUIDANCE'], icon=":material/psychology:")
                        
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
                                        
                                        rule_detection_mode = rule.get('detection_mode') or deficit_row.get('DETECTION_MODE') or 'keyword_search'
                                        st.markdown(f"**Detection Mode:** `{rule_detection_mode}`")
                                        
                                        search_field = rule.get('search_field')
                                        if search_field and str(search_field) != 'nan':
                                            st.markdown(f"**Search field:** `{search_field}`")
                                        
                                        rule_inclusion = rule.get('inclusion_terms')
                                        if rule_inclusion:
                                            st.markdown("**Inclusion Terms:**")
                                            st.code(rule_inclusion, language=None)
                                        
                                        rule_exclusion = rule.get('exclusion_patterns')
                                        if rule_exclusion:
                                            st.markdown("**Exclusion Patterns:**")
                                            st.code(rule_exclusion, language=None)
                                        
                                        rule_clinical_guidance = rule.get('clinical_guidance')
                                        if rule_clinical_guidance:
                                            st.markdown("**Clinical Guidance:**")
                                            st.info(rule_clinical_guidance, icon=":material/psychology:")
                                        
                                        rule_regulatory_ref = rule.get('regulatory_reference')
                                        if rule_regulatory_ref:
                                            st.markdown(f"**Regulatory Reference:** {rule_regulatory_ref}")
                                        
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
            st.subheader("Version History")
            
            all_versions = execute_query_df(f"""
                SELECT VERSION_NUMBER, VERSION_DESCRIPTION, CREATED_BY, CREATED_TIMESTAMP
                FROM AGEDCARE.AGEDCARE.DRI_RULES
                WHERE DEFICIT_ID = '{selected_deficit}'
                ORDER BY CREATED_TIMESTAMP DESC
            """, session)
            
            if all_versions is not None and len(all_versions) > 0:
                st.dataframe(all_versions, use_container_width=True, hide_index=True)
        else:
            st.info("No DRI rules found.", icon=":material/info:")
            
    with tab2:
        st.subheader("Client Settings")
        st.caption("Configure client-specific settings including which rule versions to use for each deficit.")
        
        clients = execute_query_df("""
            SELECT CONFIG_ID, CLIENT_SYSTEM_KEY, CLIENT_NAME, IS_ACTIVE
            FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG
            ORDER BY CLIENT_NAME
        """, session)
        
        if clients is not None and len(clients) > 0:
            client_options = {f"{row['CLIENT_NAME']} ({row['CLIENT_SYSTEM_KEY']})": row for _, row in clients.iterrows()}
            
            selected_client_display = st.selectbox(
                "Select client",
                list(client_options.keys()),
                help="All settings on this tab apply to the selected client"
            )
            selected_client = client_options[selected_client_display]
            selected_config_id = selected_client['CONFIG_ID']
            selected_client_key = selected_client['CLIENT_SYSTEM_KEY']
            
            st.markdown("---")
            
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
            prod_prompt_version = db_production_config[0]['PROD_PROMPT_VERSION'] if db_production_config and db_production_config[0]['PROD_PROMPT_VERSION'] else 'v0001'
            batch_schedule = db_production_config[0]['BATCH_SCHEDULE'] if db_production_config and db_production_config[0]['BATCH_SCHEDULE'] else '0 0 * * *'
            db_threshold = db_production_config[0]['CONTEXT_THRESHOLD'] if db_production_config and db_production_config[0]['CONTEXT_THRESHOLD'] else 6000
            
            with st.container(border=True):
                st.markdown("**Current Production Settings Summary**")
                summary_cols = st.columns(4)
                with summary_cols[0]:
                    st.markdown(f"**Prompt:** {prod_prompt_version}")
                with summary_cols[1]:
                    st.markdown(f"**Model:** {prod_model}")
                with summary_cols[2]:
                    st.markdown(f"**Schedule:** {batch_schedule}")
                with summary_cols[3]:
                    st.markdown(f"**Token Threshold:** {db_threshold:,}")
            
            st.subheader("Deficit Rule Versions")
            st.caption("Select which version of each deficit rule to use for this client's batch processing.")
            
            all_deficit_versions = execute_query_df("""
                SELECT DEFICIT_ID, DEFICIT_NAME, VERSION_NUMBER, VERSION_DESCRIPTION, CREATED_TIMESTAMP
                FROM AGEDCARE.AGEDCARE.DRI_RULES
                ORDER BY DEFICIT_ID, CREATED_TIMESTAMP DESC
            """, session)
            
            client_assignments = execute_query_df(f"""
                SELECT DEFICIT_ID, RULE_VERSION
                FROM AGEDCARE.AGEDCARE.DRI_CLIENT_RULE_ASSIGNMENTS
                WHERE CLIENT_SYSTEM_KEY = '{selected_client_key}'
            """, session)
            
            if client_assignments is not None:
                assignment_dict = dict(zip(client_assignments['DEFICIT_ID'], client_assignments['RULE_VERSION']))
            else:
                assignment_dict = {}
            
            if all_deficit_versions is not None and len(all_deficit_versions) > 0:
                unique_deficits = all_deficit_versions[['DEFICIT_ID', 'DEFICIT_NAME']].drop_duplicates()
                
                updated_assignments = {}
                
                for _, deficit in unique_deficits.iterrows():
                    deficit_id = deficit['DEFICIT_ID']
                    deficit_name = deficit['DEFICIT_NAME']
                    
                    versions_for_deficit = all_deficit_versions[all_deficit_versions['DEFICIT_ID'] == deficit_id]
                    version_options = versions_for_deficit['VERSION_NUMBER'].tolist()
                    
                    current_assignment = assignment_dict.get(deficit_id, version_options[0] if version_options else None)
                    
                    col1, col2 = st.columns([3, 2])
                    with col1:
                        st.markdown(f"**{deficit_id}:** {deficit_name}")
                    with col2:
                        if version_options:
                            default_idx = version_options.index(current_assignment) if current_assignment in version_options else 0
                            selected_version = st.selectbox(
                                f"Version for {deficit_id}",
                                version_options,
                                index=default_idx,
                                key=f"version_select_{deficit_id}",
                                label_visibility="collapsed"
                            )
                            updated_assignments[deficit_id] = selected_version
                
                st.session_state['updated_rule_assignments'] = updated_assignments
            
            st.markdown("---")
            st.subheader("Production Model")
            
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
            
            default_model_idx = model_options.index(prod_model) if prod_model in model_options else 3
            selected_prod_model = st.selectbox(
                "Select model for production",
                model_options,
                index=default_model_idx,
                help="This model will be used by the nightly batch process"
            )
            
            st.subheader("Production Prompt")
            
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
                
                with st.expander("View prompt text", expanded=False):
                    st.text_area(
                        "Prompt text (read-only)",
                        value=prompt_text_display,
                        height=300,
                        disabled=True
                    )
            
            st.subheader("Batch Schedule")
            
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
            
            st.subheader("Adaptive Token Sizing")
            st.caption("Threshold for standard vs large token mode.")
            
            new_threshold = st.number_input(
                "Context threshold (characters)",
                min_value=2000,
                max_value=20000,
                value=db_threshold,
                step=500,
                help="Residents with context below this threshold use standard mode (faster). Above uses large mode (slower but complete)."
            )
            
            st.markdown("---")
            if st.button("Save All Client Settings", type="primary", key="save_all_client", icon=":material/save:", use_container_width=True):
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
                    
                    updated_assignments = st.session_state.get('updated_rule_assignments', {})
                    for deficit_id, rule_version in updated_assignments.items():
                        execute_query(f"""
                            MERGE INTO AGEDCARE.AGEDCARE.DRI_CLIENT_RULE_ASSIGNMENTS t
                            USING (SELECT '{selected_client_key}' as CLIENT_SYSTEM_KEY, '{deficit_id}' as DEFICIT_ID, '{rule_version}' as RULE_VERSION) s
                            ON t.CLIENT_SYSTEM_KEY = s.CLIENT_SYSTEM_KEY AND t.DEFICIT_ID = s.DEFICIT_ID
                            WHEN MATCHED THEN UPDATE SET RULE_VERSION = s.RULE_VERSION, MODIFIED_BY = CURRENT_USER(), MODIFIED_TIMESTAMP = CURRENT_TIMESTAMP()
                            WHEN NOT MATCHED THEN INSERT (CLIENT_SYSTEM_KEY, DEFICIT_ID, RULE_VERSION, CREATED_BY) VALUES (s.CLIENT_SYSTEM_KEY, s.DEFICIT_ID, s.RULE_VERSION, CURRENT_USER())
                        """, session)
                    
                    st.success(f"All settings saved for {selected_client_display}!", icon=":material/check_circle:")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save: {e}", icon=":material/error:")
        else:
            st.error("No clients found in configuration table", icon=":material/error:")

else:
    st.error("Failed to connect to Snowflake", icon=":material/error:")
