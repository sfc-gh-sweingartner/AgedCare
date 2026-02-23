import streamlit as st
import json

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
This is the **human-in-the-loop approval workflow**. When the AI detects DRI indicators for a resident, those results are queued here for review before being considered validated.

### Workflow
1. **Filter by status** to see Pending, Approved, or Rejected items
2. **Review each resident's detected indicators**
3. **Approve All** if all indicators are clinically accurate
4. **Reject Some...** to select specific incorrect indicators:
   - Check the indicators you want to reject
   - Enter a reason for each rejection
   - Click **Recalculate DRI** to see the new score
   - Then **Approve Recalculated DRI** or **Reject All**

### Understanding the Recalculated DRI
When you reject specific indicators, the DRI score is recalculated based only on the accepted indicators. You then decide whether to approve this new score or reject the entire analysis.
        """)

    st.caption("Review and approve/reject DRI analyses. Rejections with specific feedback help improve the AI.")
    
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        
        pending = execute_query("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'PENDING'", session)
        approved = execute_query("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'APPROVED'", session)
        rejected = execute_query("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'REJECTED'", session)
        
        col1.metric("Pending", pending[0]['CNT'] if pending else 0)
        col2.metric("Approved", approved[0]['CNT'] if approved else 0)
        col3.metric("Rejected", rejected[0]['CNT'] if rejected else 0)
    
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
                
                if row['STATUS'] == 'PENDING':
                    st.markdown("---")
                    st.markdown("### Review Indicators")
                    
                    if indicators:
                        reject_mode_key = f"reject_mode_{row['QUEUE_ID']}"
                        recalc_mode_key = f"recalc_mode_{row['QUEUE_ID']}"
                        rejected_ids_key = f"rejected_ids_{row['QUEUE_ID']}"
                        reason_mode_key = f"reason_mode_{row['QUEUE_ID']}"
                        
                        if reject_mode_key not in st.session_state:
                            st.session_state[reject_mode_key] = False
                        if recalc_mode_key not in st.session_state:
                            st.session_state[recalc_mode_key] = False
                        if rejected_ids_key not in st.session_state:
                            st.session_state[rejected_ids_key] = {}
                        
                        if not st.session_state[reject_mode_key] and not st.session_state[recalc_mode_key]:
                            st.markdown("**Detected Indicators:**")
                            for i, ind in enumerate(indicators[:15]):
                                conf = ind.get('confidence', 'N/A')
                                conf_emoji = "🟢" if conf == 'high' else "🟡" if conf == 'medium' else "🔴"
                                with st.container(border=True):
                                    st.markdown(f"**{conf_emoji} {ind.get('deficit_id', '?')} - {ind.get('deficit_name', 'Unknown')}**")
                                    with st.expander("View details", expanded=False):
                                        st.markdown(f"**Reasoning:** {ind.get('reasoning', 'No reasoning provided')}")
                                        temporal = ind.get('temporal_status', {})
                                        if temporal:
                                            st.markdown(f"**Temporal:** {temporal.get('type', 'N/A')} | Onset: {temporal.get('onset_date', 'N/A')} | Persistence: {temporal.get('persistence_rule', 'N/A')}")
                                        evidence_list = ind.get('evidence', [])
                                        if evidence_list:
                                            st.markdown("**Evidence:**")
                                            for ev in evidence_list:
                                                st.caption(f"- **{ev.get('source_table', 'N/A')}** ({ev.get('event_date', 'N/A')}): {ev.get('text_excerpt', 'N/A')}")
                            
                            st.markdown("---")
                            col_btn1, col_btn2 = st.columns(2)
                            
                            with col_btn1:
                                if st.button("✅ Approve All", key=f"approve_{row['QUEUE_ID']}", use_container_width=True, type="primary"):
                                    execute_query(f"""
                                        UPDATE AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE 
                                        SET STATUS = 'APPROVED', 
                                            REVIEW_TIMESTAMP = CURRENT_TIMESTAMP(),
                                            REVIEWER_USER = CURRENT_USER()
                                        WHERE QUEUE_ID = '{row['QUEUE_ID']}'
                                    """, session)
                                    st.success("All indicators approved!")
                                    st.rerun()
                            
                            with col_btn2:
                                if st.button("❌ Reject Some...", key=f"reject_start_{row['QUEUE_ID']}", use_container_width=True):
                                    st.session_state[reject_mode_key] = True
                                    st.session_state[rejected_ids_key] = {}
                                    st.rerun()
                        
                        elif st.session_state[reject_mode_key] and not st.session_state[recalc_mode_key] and not st.session_state.get(f"reason_mode_{row['QUEUE_ID']}", False):
                            st.warning("**Select indicators to reject, then click 'Continue' to add reasons:**")
                            
                            with st.form(key=f"reject_form_{row['QUEUE_ID']}"):
                                for i, ind in enumerate(indicators[:15]):
                                    ind_id = ind.get('deficit_id', f'unknown_{i}')
                                    ind_name = ind.get('deficit_name', 'Unknown')
                                    conf = ind.get('confidence', 'N/A')
                                    conf_emoji = "🟢" if conf == 'high' else "🟡" if conf == 'medium' else "🔴"
                                    
                                    col_check, col_info = st.columns([1, 6])
                                    
                                    with col_check:
                                        st.checkbox(
                                            "Reject", 
                                            key=f"reject_ind_{row['QUEUE_ID']}_{i}",
                                            label_visibility="collapsed"
                                        )
                                    
                                    with col_info:
                                        st.markdown(f"**{conf_emoji} {ind_id}** - {ind_name}")
                                        with st.expander("View details", expanded=False):
                                            st.markdown(f"**Reasoning:** {ind.get('reasoning', 'No reasoning provided')}")
                                            temporal = ind.get('temporal_status', {})
                                            if temporal:
                                                st.markdown(f"**Temporal:** {temporal.get('type', 'N/A')} | Onset: {temporal.get('onset_date', 'N/A')} | Persistence: {temporal.get('persistence_rule', 'N/A')}")
                                            evidence_list = ind.get('evidence', [])
                                            if evidence_list:
                                                st.markdown("**Evidence:**")
                                                for ev in evidence_list:
                                                    st.caption(f"- **{ev.get('source_table', 'N/A')}** ({ev.get('event_date', 'N/A')}): {ev.get('text_excerpt', 'N/A')}")
                                
                                st.markdown("---")
                                col_cancel, col_continue = st.columns(2)
                                
                                with col_cancel:
                                    back_clicked = st.form_submit_button("← Back", use_container_width=True)
                                
                                with col_continue:
                                    continue_clicked = st.form_submit_button("Continue →", use_container_width=True, type="primary")
                            
                            if back_clicked:
                                st.session_state[reject_mode_key] = False
                                st.session_state[rejected_ids_key] = {}
                                st.rerun()
                            
                            if continue_clicked:
                                checked_rejections = {}
                                for i, ind in enumerate(indicators[:15]):
                                    checkbox_key = f"reject_ind_{row['QUEUE_ID']}_{i}"
                                    if st.session_state.get(checkbox_key, False):
                                        ind_id = ind.get('deficit_id', f'unknown_{i}')
                                        ind_name = ind.get('deficit_name', 'Unknown')
                                        checked_rejections[ind_id] = {
                                            'indicator_id': ind_id,
                                            'indicator_name': ind_name,
                                            'confidence': ind.get('confidence', 'N/A'),
                                            'reasoning': ind.get('reasoning', 'No reasoning provided'),
                                            'temporal_status': ind.get('temporal_status', {}),
                                            'evidence': ind.get('evidence', []),
                                            'reason': ''
                                        }
                                
                                if checked_rejections:
                                    st.session_state[rejected_ids_key] = checked_rejections
                                    st.session_state[f"reason_mode_{row['QUEUE_ID']}"] = True
                                    st.rerun()
                                else:
                                    st.error("Please select at least one indicator to reject.")
                        
                        elif st.session_state.get(f"reason_mode_{row['QUEUE_ID']}", False) and not st.session_state[recalc_mode_key]:
                            st.info("**Provide a reason for each rejected indicator:**")
                            
                            rejections = st.session_state[rejected_ids_key]
                            
                            with st.form(key=f"reason_form_{row['QUEUE_ID']}"):
                                for ind_id, rej_data in rejections.items():
                                    conf = rej_data.get('confidence', 'N/A')
                                    conf_emoji = "🟢" if conf == 'high' else "🟡" if conf == 'medium' else "🔴"
                                    with st.container(border=True):
                                        st.markdown(f"**❌ {conf_emoji} {ind_id}** - {rej_data['indicator_name']}")
                                        with st.expander("View details", expanded=False):
                                            st.markdown(f"**Reasoning:** {rej_data.get('reasoning', 'No reasoning provided')}")
                                            temporal = rej_data.get('temporal_status', {})
                                            if temporal:
                                                st.markdown(f"**Temporal:** {temporal.get('type', 'N/A')} | Onset: {temporal.get('onset_date', 'N/A')} | Persistence: {temporal.get('persistence_rule', 'N/A')}")
                                            evidence_list = rej_data.get('evidence', [])
                                            if evidence_list:
                                                st.markdown("**Evidence:**")
                                                for ev in evidence_list:
                                                    st.caption(f"- **{ev.get('source_table', 'N/A')}** ({ev.get('event_date', 'N/A')}): {ev.get('text_excerpt', 'N/A')}")
                                        reason = st.text_input(
                                            f"Rejection reason",
                                            key=f"reason_{row['QUEUE_ID']}_{ind_id}",
                                            placeholder="Enter rejection reason...",
                                            label_visibility="collapsed"
                                        )
                                
                                st.markdown("---")
                                col_back, col_recalc = st.columns(2)
                                
                                with col_back:
                                    back_to_select = st.form_submit_button("← Back", use_container_width=True)
                                
                                with col_recalc:
                                    recalc_clicked = st.form_submit_button("🔄 Recalculate DRI", use_container_width=True, type="primary")
                            
                            if back_to_select:
                                st.session_state[f"reason_mode_{row['QUEUE_ID']}"] = False
                                st.rerun()
                            
                            if recalc_clicked:
                                rejections_with_reasons = {}
                                all_have_reasons = True
                                for ind_id in rejections.keys():
                                    reason = st.session_state.get(f"reason_{row['QUEUE_ID']}_{ind_id}", "")
                                    if reason.strip():
                                        rejections_with_reasons[ind_id] = {
                                            'indicator_id': ind_id,
                                            'indicator_name': rejections[ind_id]['indicator_name'],
                                            'reason': reason
                                        }
                                    else:
                                        all_have_reasons = False
                                
                                if all_have_reasons and rejections_with_reasons:
                                    st.session_state[rejected_ids_key] = rejections_with_reasons
                                    st.session_state[recalc_mode_key] = True
                                    st.session_state[f"reason_mode_{row['QUEUE_ID']}"] = False
                                    st.rerun()
                                else:
                                    st.warning("Please provide a reason for each rejected indicator.")
                        
                        elif st.session_state[recalc_mode_key]:
                            rejections_with_reasons = st.session_state[rejected_ids_key]
                            excluded_ids = list(rejections_with_reasons.keys())
                            
                            accepted_count = len(indicators) - len(excluded_ids)
                            new_dri_score = accepted_count / 33.0
                            new_severity = calculate_severity_band(new_dri_score)
                            original_dri = row['PROPOSED_DRI_SCORE'] or 0
                            
                            st.success("### Recalculated DRI Score")
                            
                            col_orig, col_arrow, col_new = st.columns([2, 1, 2])
                            
                            with col_orig:
                                st.markdown("**Original:**")
                                st.metric("Original DRI", f"{original_dri:.4f}")
                                orig_severity_color = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Very High": "🔴"}.get(row['PROPOSED_SEVERITY_BAND'], "⚪")
                                st.caption(f"{orig_severity_color} {row['PROPOSED_SEVERITY_BAND']} ({len(indicators)} indicators)")
                            
                            with col_arrow:
                                st.markdown("")
                                st.markdown("")
                                st.markdown("### →")
                            
                            with col_new:
                                st.markdown("**Recalculated:**")
                                st.metric("New DRI", f"{new_dri_score:.4f}", delta=f"{new_dri_score - original_dri:.4f}")
                                new_severity_color = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Very High": "🔴"}.get(new_severity, "⚪")
                                st.caption(f"{new_severity_color} {new_severity} ({accepted_count} indicators)")
                            
                            st.markdown("---")
                            st.markdown("**Rejected Indicators:**")
                            for ind_id, rej_data in rejections_with_reasons.items():
                                st.markdown(f"- ❌ **{ind_id}** - {rej_data['indicator_name']}: _{rej_data['reason']}_")
                            
                            st.markdown("---")
                            col_back, col_reject_all, col_approve = st.columns(3)
                            
                            with col_back:
                                if st.button("← Edit Selections", key=f"back_edit_{row['QUEUE_ID']}", use_container_width=True):
                                    st.session_state[recalc_mode_key] = False
                                    st.rerun()
                            
                            with col_reject_all:
                                if st.button("❌ Reject All", key=f"reject_all_{row['QUEUE_ID']}", use_container_width=True):
                                    for ind_id, rej_data in rejections_with_reasons.items():
                                        reason_escaped = rej_data['reason'].replace("'", "''")
                                        name_escaped = rej_data['indicator_name'].replace("'", "''")
                                        execute_query(f"""
                                            INSERT INTO AGEDCARE.AGEDCARE.DRI_INDICATOR_REJECTIONS 
                                            (QUEUE_ID, INDICATOR_ID, INDICATOR_NAME, REJECTION_REASON, REJECTED_BY)
                                            VALUES ('{row['QUEUE_ID']}', '{ind_id}', '{name_escaped}', '{reason_escaped}', CURRENT_USER())
                                        """, session)
                                    
                                    summary_notes = "REJECTED - " + "; ".join([f"{k}: {v['reason']}" for k, v in rejections_with_reasons.items()])
                                    summary_escaped = summary_notes[:4000].replace("'", "''")
                                    excluded_json = json.dumps(excluded_ids).replace("'", "''")
                                    
                                    execute_query(f"""
                                        UPDATE AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE 
                                        SET STATUS = 'REJECTED', 
                                            REVIEW_TIMESTAMP = CURRENT_TIMESTAMP(),
                                            REVIEWER_USER = CURRENT_USER(),
                                            EXCLUDED_INDICATORS = PARSE_JSON('{excluded_json}'),
                                            REVIEWER_NOTES = '{summary_escaped}'
                                        WHERE QUEUE_ID = '{row['QUEUE_ID']}'
                                    """, session)
                                    
                                    st.session_state[reject_mode_key] = False
                                    st.session_state[recalc_mode_key] = False
                                    st.session_state[rejected_ids_key] = {}
                                    st.warning("Analysis rejected!")
                                    st.rerun()
                            
                            with col_approve:
                                if st.button("✅ Approve New DRI", key=f"approve_recalc_{row['QUEUE_ID']}", use_container_width=True, type="primary"):
                                    for ind_id, rej_data in rejections_with_reasons.items():
                                        reason_escaped = rej_data['reason'].replace("'", "''")
                                        name_escaped = rej_data['indicator_name'].replace("'", "''")
                                        execute_query(f"""
                                            INSERT INTO AGEDCARE.AGEDCARE.DRI_INDICATOR_REJECTIONS 
                                            (QUEUE_ID, INDICATOR_ID, INDICATOR_NAME, REJECTION_REASON, REJECTED_BY)
                                            VALUES ('{row['QUEUE_ID']}', '{ind_id}', '{name_escaped}', '{reason_escaped}', CURRENT_USER())
                                        """, session)
                                    
                                    summary_notes = f"APPROVED with {len(excluded_ids)} indicator(s) excluded: " + "; ".join([f"{k}: {v['reason']}" for k, v in rejections_with_reasons.items()])
                                    summary_escaped = summary_notes[:4000].replace("'", "''")
                                    excluded_json = json.dumps(excluded_ids).replace("'", "''")
                                    
                                    execute_query(f"""
                                        UPDATE AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE 
                                        SET STATUS = 'APPROVED', 
                                            PROPOSED_DRI_SCORE = {new_dri_score},
                                            PROPOSED_SEVERITY_BAND = '{new_severity}',
                                            INDICATORS_ADDED = {accepted_count},
                                            REVIEW_TIMESTAMP = CURRENT_TIMESTAMP(),
                                            REVIEWER_USER = CURRENT_USER(),
                                            EXCLUDED_INDICATORS = PARSE_JSON('{excluded_json}'),
                                            REVIEWER_NOTES = '{summary_escaped}'
                                        WHERE QUEUE_ID = '{row['QUEUE_ID']}'
                                    """, session)
                                    
                                    st.session_state[reject_mode_key] = False
                                    st.session_state[recalc_mode_key] = False
                                    st.session_state[rejected_ids_key] = {}
                                    st.success("Recalculated DRI approved!")
                                    st.rerun()
                    else:
                        st.info("No indicator details available for this analysis.")
                        
                        notes_key = f"notes_{row['QUEUE_ID']}"
                        reviewer_notes = st.text_input("General notes", key=notes_key)
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("✅ Approve", key=f"approve_{row['QUEUE_ID']}", use_container_width=True, type="primary"):
                                execute_query(f"""
                                    UPDATE AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE 
                                    SET STATUS = 'APPROVED', 
                                        REVIEW_TIMESTAMP = CURRENT_TIMESTAMP(),
                                        REVIEWER_USER = CURRENT_USER()
                                    WHERE QUEUE_ID = '{row['QUEUE_ID']}'
                                """, session)
                                st.rerun()
                        with col_btn2:
                            if st.button("❌ Reject", key=f"reject_{row['QUEUE_ID']}", use_container_width=True):
                                notes_escaped = reviewer_notes.replace("'", "''") if reviewer_notes else "No specific reason provided"
                                execute_query(f"""
                                    UPDATE AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE 
                                    SET STATUS = 'REJECTED', 
                                        REVIEW_TIMESTAMP = CURRENT_TIMESTAMP(),
                                        REVIEWER_USER = CURRENT_USER(),
                                        REVIEWER_NOTES = '{notes_escaped}'
                                    WHERE QUEUE_ID = '{row['QUEUE_ID']}'
                                """, session)
                                st.rerun()
                
                elif row['STATUS'] in ['APPROVED', 'REJECTED']:
                    excluded = []
                    if row['EXCLUDED_INDICATORS']:
                        try:
                            if isinstance(row['EXCLUDED_INDICATORS'], str):
                                excluded = json.loads(row['EXCLUDED_INDICATORS'])
                            else:
                                excluded = row['EXCLUDED_INDICATORS']
                        except:
                            excluded = []
                    
                    if excluded:
                        st.info(f"**{len(excluded)} indicator(s) were excluded** from this {row['STATUS'].lower()} analysis.", icon=":material/info:")
                    
                    if indicators:
                        with st.expander("View detected indicators", expanded=False):
                            for ind in indicators[:15]:
                                ind_id = ind.get('deficit_id', '?')
                                conf = ind.get('confidence', 'N/A')
                                conf_emoji = "🟢" if conf == 'high' else "🟡" if conf == 'medium' else "🔴"
                                rejected_badge = " ❌ EXCLUDED" if ind_id in excluded else " ✅"
                                
                                with st.container(border=True):
                                    st.markdown(f"**{conf_emoji} {ind_id} - {ind.get('deficit_name', 'Unknown')}**{rejected_badge}")
                                    st.caption(ind.get('reasoning', 'No reasoning')[:200])
                    
                    if row['REVIEWER_NOTES']:
                        st.info(f"**Reviewer notes:** {row['REVIEWER_NOTES']}", icon=":material/note:")
                    
                    if excluded:
                        rejections_data = execute_query_df(f"""
                            SELECT INDICATOR_ID, INDICATOR_NAME, REJECTION_REASON, REJECTED_BY, REJECTED_TIMESTAMP
                            FROM AGEDCARE.AGEDCARE.DRI_INDICATOR_REJECTIONS
                            WHERE QUEUE_ID = '{row['QUEUE_ID']}'
                            ORDER BY REJECTED_TIMESTAMP
                        """, session)
                        
                        if rejections_data is not None and len(rejections_data) > 0:
                            with st.expander("View exclusion details", expanded=True):
                                for _, rej in rejections_data.iterrows():
                                    st.markdown(f"**❌ {rej['INDICATOR_ID']} - {rej['INDICATOR_NAME']}**")
                                    st.caption(f"Reason: {rej['REJECTION_REASON']}")
                                    st.caption(f"By: {rej['REJECTED_BY']} at {rej['REJECTED_TIMESTAMP']}")
    else:
        st.info("No items in the review queue. Run a batch test from the Batch Testing page to generate items for review.", icon=":material/info:")

else:
    st.error("Failed to connect to Snowflake", icon=":material/error:")
