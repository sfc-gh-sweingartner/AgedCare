import streamlit as st
import json
from datetime import datetime, timedelta

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

def calculate_severity_band(dri_score):
    if dri_score <= 0.2:
        return 'Low'
    elif dri_score <= 0.4:
        return 'Medium'
    elif dri_score <= 0.6:
        return 'High'
    else:
        return 'Very High'

session = get_snowflake_session()

if session:
    with st.expander("How to use this page", expanded=False, icon=":material/help:"):
        st.markdown("""
### Purpose
This is the **clinical decision workflow** for reviewing DRI indicators. The system now remembers clinical decisions at the resident + indicator level with time-bound validity.

### Review Types

| Type | Description | Actions |
|------|-------------|---------|
| 🆕 **NEW** | First-time detection for this resident | CONFIRM or REJECT |
| ✅ **EXISTING (Permanent)** | Already confirmed persistent indicator | View only (no action needed) |
| 🔄 **EXISTING (Temporal)** | Already confirmed fluctuating indicator | EXTEND or END |
| ⏰ **RENEWAL REQUIRED** | Confirmed indicator approaching expiry | RENEW or LET EXPIRE |

### Clinical Decision Types
- **CONFIRM**: Indicator is clinically accurate (permanent or time-bound)
- **REJECT**: False positive - suppress for specified duration (default 90 days)

### Workflow
1. Filter by review type to focus on new or renewal items
2. Review evidence and AI reasoning
3. Make clinical decision with optional duration override
4. Decisions are recorded and remembered for future detections
        """)

    st.caption("Clinical review workflow with temporal memory for indicator decisions")
    
    with st.container(border=True):
        col1, col2, col3, col4, col5 = st.columns(5)
        
        pending = execute_query("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'PENDING'", session)
        approved = execute_query("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'APPROVED'", session)
        rejected = execute_query("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'REJECTED'", session)
        active_decisions = execute_query("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS WHERE STATUS = 'ACTIVE'", session)
        renewals_due = execute_query("""
            SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS 
            WHERE STATUS = 'ACTIVE' 
            AND DEFICIT_TYPE = 'FLUCTUATING'
            AND EXPIRY_DATE IS NOT NULL
            AND EXPIRY_DATE <= DATEADD(day, RENEWAL_REMINDER_DAYS, CURRENT_DATE())
        """, session)
        
        col1.metric("Pending", pending[0]['CNT'] if pending else 0)
        col2.metric("Approved", approved[0]['CNT'] if approved else 0)
        col3.metric("Rejected", rejected[0]['CNT'] if rejected else 0)
        col4.metric("Active Decisions", active_decisions[0]['CNT'] if active_decisions else 0)
        col5.metric("Renewals Due", renewals_due[0]['CNT'] if renewals_due else 0, delta_color="inverse")
    
    tab_queue, tab_decisions, tab_renewals = st.tabs(["Review Queue", "Clinical Decisions", "Renewals Due"])
    
    with tab_queue:
        col_filter1, col_filter2 = st.columns([1, 2])
        with col_filter1:
            status_filter = st.selectbox("Filter by status", ["PENDING", "ALL", "APPROVED", "REJECTED"])
        with col_filter2:
            if st.button("🔄 Refresh queue", use_container_width=True):
                st.rerun()
        
        if status_filter == "ALL":
            queue_query = """
                SELECT 
                    rq.QUEUE_ID, rq.ANALYSIS_ID, rq.RESIDENT_ID, rq.CLIENT_SYSTEM_KEY, 
                    rq.CURRENT_DRI_SCORE, rq.PROPOSED_DRI_SCORE,
                    rq.CURRENT_SEVERITY_BAND, rq.PROPOSED_SEVERITY_BAND,
                    rq.INDICATORS_ADDED, rq.INDICATORS_REMOVED,
                    rq.INDICATOR_CHANGES_JSON, rq.CHANGE_SUMMARY, 
                    rq.STATUS, rq.CREATED_TIMESTAMP, rq.REVIEWER_NOTES,
                    rq.EXCLUDED_INDICATORS,
                    lla.MODEL_USED, lla.PROMPT_VERSION
                FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE rq
                LEFT JOIN AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS lla ON rq.ANALYSIS_ID = lla.ANALYSIS_ID
                ORDER BY rq.CREATED_TIMESTAMP DESC
                LIMIT 50
            """
        else:
            queue_query = f"""
                SELECT 
                    rq.QUEUE_ID, rq.ANALYSIS_ID, rq.RESIDENT_ID, rq.CLIENT_SYSTEM_KEY, 
                    rq.CURRENT_DRI_SCORE, rq.PROPOSED_DRI_SCORE,
                    rq.CURRENT_SEVERITY_BAND, rq.PROPOSED_SEVERITY_BAND,
                    rq.INDICATORS_ADDED, rq.INDICATORS_REMOVED,
                    rq.INDICATOR_CHANGES_JSON, rq.CHANGE_SUMMARY, 
                    rq.STATUS, rq.CREATED_TIMESTAMP, rq.REVIEWER_NOTES,
                    rq.EXCLUDED_INDICATORS,
                    lla.MODEL_USED, lla.PROMPT_VERSION
                FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE rq
                LEFT JOIN AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS lla ON rq.ANALYSIS_ID = lla.ANALYSIS_ID
                WHERE rq.STATUS = '{status_filter}'
                ORDER BY rq.CREATED_TIMESTAMP DESC
                LIMIT 50
            """
        
        queue_data = execute_query_df(queue_query, session)
        
        if queue_data is not None and len(queue_data) > 0:
            for idx, row in queue_data.iterrows():
                severity_color = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Very High": "🔴"}.get(row['PROPOSED_SEVERITY_BAND'], "⚪")
                status_badge = {"PENDING": "⏳", "APPROVED": "✅", "REJECTED": "❌"}.get(row['STATUS'], "")
                
                with st.expander(f"{status_badge} Resident {row['RESIDENT_ID']} - {severity_color} {row['PROPOSED_SEVERITY_BAND'] or 'Unknown'} ({row['INDICATORS_ADDED'] or 0} indicators)"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Analysis Info:**")
                        st.write(f"- Model: `{row['MODEL_USED'] or 'N/A'}`")
                        st.write(f"- Prompt: `{row['PROMPT_VERSION'] or 'N/A'}`")
                        st.write(f"- Created: {row['CREATED_TIMESTAMP']}")
                    
                    with col2:
                        st.markdown("**DRI Score:**")
                        proposed = row['PROPOSED_DRI_SCORE'] or 0
                        st.metric("Proposed Score", f"{proposed:.4f}", label_visibility="collapsed")
                        st.progress(min(float(proposed), 1.0))
                        st.caption(f"Severity: **{row['PROPOSED_SEVERITY_BAND'] or 'Unknown'}**")
                    
                    st.markdown(f"**Summary:** {row['CHANGE_SUMMARY'] or 'No summary available'}")
                    
                    indicators = []
                    if row['INDICATOR_CHANGES_JSON']:
                        try:
                            if isinstance(row['INDICATOR_CHANGES_JSON'], str):
                                indicators = json.loads(row['INDICATOR_CHANGES_JSON'])
                            else:
                                indicators = row['INDICATOR_CHANGES_JSON']
                        except:
                            indicators = []
                    
                    if row['STATUS'] == 'PENDING' and indicators:
                        st.markdown("---")
                        st.markdown("### Clinical Review")
                        
                        existing_decisions = execute_query_df(f"""
                            SELECT DEFICIT_ID, DECISION_TYPE, DEFICIT_TYPE, EXPIRY_DATE, 
                                   DECISION_DATE, DECIDED_BY, STATUS
                            FROM AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS
                            WHERE RESIDENT_ID = {row['RESIDENT_ID']}
                            AND STATUS = 'ACTIVE'
                        """, session)
                        
                        existing_dict = {}
                        if existing_decisions is not None:
                            for _, dec in existing_decisions.iterrows():
                                existing_dict[dec['DEFICIT_ID']] = dec
                        
                        rules_data = execute_query_df("""
                            SELECT DEFICIT_ID, DEFICIT_TYPE, EXPIRY_DAYS, RENEWAL_REMINDER_DAYS
                            FROM AGEDCARE.AGEDCARE.DRI_RULES
                            WHERE IS_CURRENT_VERSION = TRUE
                        """, session)
                        
                        rules_dict = {}
                        if rules_data is not None:
                            for _, r in rules_data.iterrows():
                                rules_dict[r['DEFICIT_ID']] = {
                                    'DEFICIT_TYPE': r['DEFICIT_TYPE'],
                                    'EXPIRY_DAYS': int(r['EXPIRY_DAYS']) if r['EXPIRY_DAYS'] else 0,
                                    'RENEWAL_REMINDER_DAYS': int(r['RENEWAL_REMINDER_DAYS']) if r['RENEWAL_REMINDER_DAYS'] else 7
                                }
                        
                        for i, ind in enumerate(indicators[:15]):
                            ind_id = ind.get('deficit_id', f'unknown_{i}')
                            ind_name = ind.get('deficit_name', 'Unknown')
                            conf = ind.get('confidence', 'N/A')
                            conf_emoji = "🟢" if conf == 'high' else "🟡" if conf == 'medium' else "🔴"
                            
                            rule_info = rules_dict.get(ind_id, {})
                            deficit_type = rule_info.get('DEFICIT_TYPE', 'UNKNOWN') if rule_info else 'UNKNOWN'
                            default_expiry = rule_info.get('EXPIRY_DAYS', 0) if rule_info else 0
                            
                            existing = existing_dict.get(ind_id)
                            
                            if existing is not None:
                                if existing['DEFICIT_TYPE'] == 'PERSISTENT':
                                    review_type = "EXISTING_PERMANENT"
                                    type_badge = "✅ ALREADY CONFIRMED"
                                    type_color = "green"
                                else:
                                    review_type = "EXISTING_TEMPORAL"
                                    type_badge = "🔄 EXISTING"
                                    type_color = "blue"
                            else:
                                review_type = "NEW_INDICATOR"
                                type_badge = "🆕 NEW"
                                type_color = "orange"
                            
                            with st.container(border=True):
                                header_col1, header_col2 = st.columns([3, 1])
                                with header_col1:
                                    st.markdown(f"**{conf_emoji} {ind_id} - {ind_name}**")
                                with header_col2:
                                    st.badge(type_badge, color=type_color)
                                
                                if deficit_type == 'PERSISTENT':
                                    st.caption(f"Type: **PERSISTENT** (never expires)")
                                else:
                                    st.caption(f"Type: **FLUCTUATING** (expires in {default_expiry} days)")
                                
                                with st.expander("View evidence", expanded=False):
                                    st.markdown(f"**Reasoning:** {ind.get('reasoning', 'No reasoning provided')}")
                                    temporal = ind.get('temporal_status', {})
                                    if temporal:
                                        st.markdown(f"**Temporal:** {temporal.get('type', 'N/A')} | Onset: {temporal.get('onset_date', 'N/A')}")
                                    evidence_list = ind.get('evidence', [])
                                    if evidence_list:
                                        st.markdown("**Evidence:**")
                                        for ev in evidence_list:
                                            st.caption(f"- **{ev.get('source_table', 'N/A')}** ({ev.get('event_date', 'N/A')}): {ev.get('text_excerpt', 'N/A')}")
                                
                                if review_type == "EXISTING_PERMANENT":
                                    st.info(f"Confirmed by {existing['DECIDED_BY']} on {existing['DECISION_DATE']}. No action required.", icon=":material/check_circle:")
                                
                                elif review_type == "EXISTING_TEMPORAL":
                                    expiry = existing['EXPIRY_DATE']
                                    st.info(f"Confirmed by {existing['DECIDED_BY']} on {existing['DECISION_DATE']}. Expires: {expiry}", icon=":material/update:")
                                    
                                    col_ext, col_end = st.columns(2)
                                    with col_ext:
                                        if st.button(f"🔄 Extend", key=f"extend_{row['QUEUE_ID']}_{ind_id}", use_container_width=True):
                                            execute_query(f"""
                                                UPDATE AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS
                                                SET DECISION_DATE = CURRENT_DATE(),
                                                    EXPIRY_DATE = DATEADD(day, COALESCE(OVERRIDE_EXPIRY_DAYS, DEFAULT_EXPIRY_DAYS), CURRENT_DATE()),
                                                    DECIDED_BY = CURRENT_USER(),
                                                    DECIDED_TIMESTAMP = CURRENT_TIMESTAMP()
                                                WHERE RESIDENT_ID = {row['RESIDENT_ID']}
                                                AND DEFICIT_ID = '{ind_id}'
                                                AND STATUS = 'ACTIVE'
                                            """, session)
                                            st.success(f"Extended {ind_id}")
                                            st.rerun()
                                    with col_end:
                                        if st.button(f"🛑 End Now", key=f"end_{row['QUEUE_ID']}_{ind_id}", use_container_width=True):
                                            execute_query(f"""
                                                UPDATE AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS
                                                SET STATUS = 'EXPIRED',
                                                    EXPIRY_DATE = CURRENT_DATE()
                                                WHERE RESIDENT_ID = {row['RESIDENT_ID']}
                                                AND DEFICIT_ID = '{ind_id}'
                                                AND STATUS = 'ACTIVE'
                                            """, session)
                                            st.success(f"Ended {ind_id}")
                                            st.rerun()
                                
                                elif review_type == "NEW_INDICATOR":
                                    col_confirm, col_reject = st.columns(2)
                                    
                                    with col_confirm:
                                        if st.button(f"✅ Confirm", key=f"confirm_{row['QUEUE_ID']}_{ind_id}", use_container_width=True, type="primary"):
                                            expiry_date = "NULL" if deficit_type == 'PERSISTENT' else f"DATEADD(day, {default_expiry}, CURRENT_DATE())"
                                            review_req = "FALSE" if deficit_type == 'PERSISTENT' else "TRUE"
                                            reminder_days = rule_info.get('RENEWAL_REMINDER_DAYS', 7) if rule_info else 7
                                            
                                            execute_query(f"""
                                                INSERT INTO AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS (
                                                    RESIDENT_ID, CLIENT_SYSTEM_KEY, DEFICIT_ID, DEFICIT_NAME,
                                                    DECISION_TYPE, DECISION_REASON, DEFICIT_TYPE,
                                                    DEFAULT_EXPIRY_DAYS, EXPIRY_DATE, REVIEW_REQUIRED,
                                                    RENEWAL_REMINDER_DAYS, DECIDED_BY
                                                ) VALUES (
                                                    {row['RESIDENT_ID']}, '{row['CLIENT_SYSTEM_KEY']}', '{ind_id}', '{ind_name.replace("'", "''")}',
                                                    'CONFIRMED', 'Approved via review queue', '{deficit_type}',
                                                    {default_expiry}, {expiry_date}, {review_req},
                                                    {reminder_days}, CURRENT_USER()
                                                )
                                            """, session)
                                            st.success(f"Confirmed {ind_id}")
                                            st.rerun()
                                    
                                    with col_reject:
                                        reject_key = f"reject_expand_{row['QUEUE_ID']}_{ind_id}"
                                        if st.button(f"❌ Reject", key=f"reject_{row['QUEUE_ID']}_{ind_id}", use_container_width=True):
                                            st.session_state[reject_key] = True
                                            st.rerun()
                                        
                                        if st.session_state.get(reject_key, False):
                                            with st.form(key=f"reject_form_{row['QUEUE_ID']}_{ind_id}"):
                                                reason = st.text_input("Rejection reason", placeholder="Why is this a false positive?")
                                                suppress_days = st.selectbox("Suppress for", [7, 30, 90, 365], index=2, format_func=lambda x: f"{x} days")
                                                
                                                col_cancel, col_submit = st.columns(2)
                                                with col_cancel:
                                                    if st.form_submit_button("Cancel", use_container_width=True):
                                                        st.session_state[reject_key] = False
                                                        st.rerun()
                                                with col_submit:
                                                    if st.form_submit_button("Submit Rejection", type="primary", use_container_width=True):
                                                        reason_escaped = reason.replace("'", "''") if reason else "False positive"
                                                        execute_query(f"""
                                                            INSERT INTO AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS (
                                                                RESIDENT_ID, CLIENT_SYSTEM_KEY, DEFICIT_ID, DEFICIT_NAME,
                                                                DECISION_TYPE, DECISION_REASON, DEFICIT_TYPE,
                                                                DEFAULT_EXPIRY_DAYS, EXPIRY_DATE, REVIEW_REQUIRED,
                                                                RENEWAL_REMINDER_DAYS, DECIDED_BY
                                                            ) VALUES (
                                                                {row['RESIDENT_ID']}, '{row['CLIENT_SYSTEM_KEY']}', '{ind_id}', '{ind_name.replace("'", "''")}',
                                                                'REJECTED', '{reason_escaped}', '{deficit_type}',
                                                                {suppress_days}, DATEADD(day, {suppress_days}, CURRENT_DATE()), FALSE,
                                                                7, CURRENT_USER()
                                                            )
                                                        """, session)
                                                        
                                                        execute_query(f"""
                                                            INSERT INTO AGEDCARE.AGEDCARE.DRI_INDICATOR_REJECTIONS 
                                                            (QUEUE_ID, INDICATOR_ID, INDICATOR_NAME, REJECTION_REASON, REJECTED_BY)
                                                            VALUES ('{row['QUEUE_ID']}', '{ind_id}', '{ind_name.replace("'", "''")}', '{reason_escaped}', CURRENT_USER())
                                                        """, session)
                                                        
                                                        st.session_state[reject_key] = False
                                                        st.success(f"Rejected {ind_id} for {suppress_days} days")
                                                        st.rerun()
                        
                        st.markdown("---")
                        if st.button("✅ Mark Queue Item Complete", key=f"complete_{row['QUEUE_ID']}", use_container_width=True, type="primary"):
                            execute_query(f"""
                                UPDATE AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE 
                                SET STATUS = 'APPROVED', 
                                    REVIEW_TIMESTAMP = CURRENT_TIMESTAMP(),
                                    REVIEWER_USER = CURRENT_USER(),
                                    REVIEWER_NOTES = 'Individual indicator decisions recorded'
                                WHERE QUEUE_ID = '{row['QUEUE_ID']}'
                            """, session)
                            st.success("Queue item marked complete!")
                            st.rerun()
                    
                    elif row['STATUS'] in ['APPROVED', 'REJECTED']:
                        if row['REVIEWER_NOTES']:
                            st.info(f"**Reviewer notes:** {row['REVIEWER_NOTES']}", icon=":material/note:")
        else:
            st.info("No items in the review queue. Run a batch test from the Batch Testing page to generate items for review.", icon=":material/info:")
    
    with tab_decisions:
        st.subheader("Active Clinical Decisions")
        st.caption("All currently active clinical decisions for residents. These decisions affect future indicator detections.")
        
        col_dec_filter1, col_dec_filter2 = st.columns(2)
        with col_dec_filter1:
            dec_type_filter = st.selectbox("Decision type", ["All", "CONFIRMED", "REJECTED"], key="dec_type_filter")
        with col_dec_filter2:
            deficit_type_filter = st.selectbox("Deficit type", ["All", "PERSISTENT", "FLUCTUATING"], key="deficit_type_filter")
        
        decisions_query = """
            SELECT DECISION_ID, RESIDENT_ID, DEFICIT_ID, DEFICIT_NAME, 
                   DECISION_TYPE, DECISION_REASON, DEFICIT_TYPE,
                   DECISION_DATE, EXPIRY_DATE, RENEWAL_REMINDER_DAYS,
                   DECIDED_BY, STATUS
            FROM AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS
            WHERE STATUS = 'ACTIVE'
        """
        
        if dec_type_filter != "All":
            decisions_query += f" AND DECISION_TYPE = '{dec_type_filter}'"
        if deficit_type_filter != "All":
            decisions_query += f" AND DEFICIT_TYPE = '{deficit_type_filter}'"
        
        decisions_query += " ORDER BY DECISION_DATE DESC LIMIT 100"
        
        decisions_data = execute_query_df(decisions_query, session)
        
        if decisions_data is not None and len(decisions_data) > 0:
            st.dataframe(
                decisions_data[['RESIDENT_ID', 'DEFICIT_ID', 'DEFICIT_NAME', 'DECISION_TYPE', 'DEFICIT_TYPE', 'DECISION_DATE', 'EXPIRY_DATE', 'DECIDED_BY']],
                use_container_width=True,
                column_config={
                    'RESIDENT_ID': st.column_config.NumberColumn('Resident', width='small'),
                    'DEFICIT_ID': st.column_config.TextColumn('Deficit ID', width='small'),
                    'DEFICIT_NAME': st.column_config.TextColumn('Deficit', width='medium'),
                    'DECISION_TYPE': st.column_config.TextColumn('Decision', width='small'),
                    'DEFICIT_TYPE': st.column_config.TextColumn('Type', width='small'),
                    'DECISION_DATE': st.column_config.DateColumn('Decision Date', width='small'),
                    'EXPIRY_DATE': st.column_config.DateColumn('Expires', width='small'),
                    'DECIDED_BY': st.column_config.TextColumn('Decided By', width='medium')
                }
            )
        else:
            st.info("No active clinical decisions found.", icon=":material/info:")
    
    with tab_renewals:
        st.subheader("Renewals Due")
        st.caption("Fluctuating indicators that are approaching expiry and need clinical review.")
        
        renewals_data = execute_query_df("""
            SELECT cd.DECISION_ID, cd.RESIDENT_ID, cd.DEFICIT_ID, cd.DEFICIT_NAME, 
                   cd.DECISION_TYPE, cd.DECISION_REASON, cd.DEFICIT_TYPE,
                   cd.DECISION_DATE, cd.EXPIRY_DATE, cd.RENEWAL_REMINDER_DAYS,
                   cd.DECIDED_BY, cd.DEFAULT_EXPIRY_DAYS,
                   DATEDIFF(day, CURRENT_DATE(), cd.EXPIRY_DATE) as DAYS_REMAINING,
                   CASE 
                       WHEN EXISTS (
                           SELECT 1 FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS lla
                           WHERE lla.RESIDENT_ID = cd.RESIDENT_ID
                           AND lla.ANALYSIS_TIMESTAMP >= DATEADD(day, -30, CURRENT_DATE())
                           AND lla.RAW_RESPONSE ILIKE '%' || cd.DEFICIT_ID || '%'
                       ) THEN 'Recent evidence found. Recommend: RENEW'
                       ELSE 'No recent evidence. Recommend: LET EXPIRE'
                   END as RECOMMENDATION
            FROM AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS cd
            WHERE cd.STATUS = 'ACTIVE'
            AND cd.DEFICIT_TYPE = 'FLUCTUATING'
            AND cd.EXPIRY_DATE IS NOT NULL
            AND cd.EXPIRY_DATE <= DATEADD(day, cd.RENEWAL_REMINDER_DAYS, CURRENT_DATE())
            ORDER BY cd.EXPIRY_DATE ASC
        """, session)
        
        if renewals_data is not None and len(renewals_data) > 0:
            for _, renewal in renewals_data.iterrows():
                days_left = int(renewal['DAYS_REMAINING']) if renewal['DAYS_REMAINING'] is not None else 0
                urgency = "🔴" if days_left <= 1 else "🟠" if days_left <= 3 else "🟡"
                recommendation_str = str(renewal['RECOMMENDATION']) if renewal['RECOMMENDATION'] else ""
                recommend_renew = "RENEW" in recommendation_str
                
                with st.container(border=True):
                    col_info, col_rec = st.columns([2, 1])
                    
                    with col_info:
                        st.markdown(f"### {urgency} Resident {renewal['RESIDENT_ID']} - {renewal['DEFICIT_ID']}")
                        st.markdown(f"**{renewal['DEFICIT_NAME']}**")
                        st.caption(f"Expires in **{days_left} days** ({renewal['EXPIRY_DATE']})")
                        st.caption(f"Original decision by {renewal['DECIDED_BY']} on {renewal['DECISION_DATE']}")
                        if renewal['DECISION_REASON']:
                            st.caption(f"Reason: {renewal['DECISION_REASON']}")
                    
                    with col_rec:
                        if recommend_renew:
                            st.success(recommendation_str, icon=":material/check:")
                        else:
                            st.warning(recommendation_str, icon=":material/warning:")
                    
                    col_renew, col_custom, col_expire = st.columns(3)
                    
                    with col_renew:
                        default_days = int(renewal['DEFAULT_EXPIRY_DAYS']) if renewal['DEFAULT_EXPIRY_DAYS'] else 90
                        if st.button(f"✅ Renew ({default_days} days)", key=f"renew_{renewal['DECISION_ID']}", use_container_width=True, type="primary" if recommend_renew else "secondary"):
                            execute_query(f"""
                                UPDATE AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS
                                SET DECISION_DATE = CURRENT_DATE(),
                                    EXPIRY_DATE = DATEADD(day, {default_days}, CURRENT_DATE()),
                                    DECIDED_BY = CURRENT_USER(),
                                    DECIDED_TIMESTAMP = CURRENT_TIMESTAMP(),
                                    DECISION_REASON = 'Renewed via renewal queue'
                                WHERE DECISION_ID = '{renewal['DECISION_ID']}'
                            """, session)
                            st.success(f"Renewed for {default_days} days")
                            st.rerun()
                    
                    with col_custom:
                        custom_key = f"custom_{renewal['DECISION_ID']}"
                        if st.button("📆 Custom", key=custom_key + "_btn", use_container_width=True):
                            st.session_state[custom_key] = True
                            st.rerun()
                        
                        if st.session_state.get(custom_key, False):
                            custom_days = st.number_input("Days", min_value=1, max_value=365, value=default_days, key=custom_key + "_days")
                            if st.button("Apply", key=custom_key + "_apply"):
                                execute_query(f"""
                                    UPDATE AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS
                                    SET DECISION_DATE = CURRENT_DATE(),
                                        EXPIRY_DATE = DATEADD(day, {custom_days}, CURRENT_DATE()),
                                        OVERRIDE_EXPIRY_DAYS = {custom_days},
                                        DECIDED_BY = CURRENT_USER(),
                                        DECIDED_TIMESTAMP = CURRENT_TIMESTAMP(),
                                        DECISION_REASON = 'Renewed via renewal queue (custom duration)'
                                    WHERE DECISION_ID = '{renewal['DECISION_ID']}'
                                """, session)
                                st.session_state[custom_key] = False
                                st.success(f"Renewed for {custom_days} days")
                                st.rerun()
                    
                    with col_expire:
                        if st.button("⏹️ Let Expire", key=f"expire_{renewal['DECISION_ID']}", use_container_width=True, type="primary" if not recommend_renew else "secondary"):
                            execute_query(f"""
                                UPDATE AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS
                                SET STATUS = 'EXPIRED',
                                    DECISION_REASON = COALESCE(DECISION_REASON, '') || ' | Let expire via renewal queue'
                                WHERE DECISION_ID = '{renewal['DECISION_ID']}'
                            """, session)
                            st.info("Indicator will expire on scheduled date")
                            st.rerun()
        else:
            st.success("No renewals due! All fluctuating indicators are within their validity period.", icon=":material/check_circle:")

else:
    st.error("Failed to connect to Snowflake", icon=":material/error:")
