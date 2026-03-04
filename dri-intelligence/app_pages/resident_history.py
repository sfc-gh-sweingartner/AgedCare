import streamlit as st
import json
from datetime import datetime, timedelta

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

def calculate_severity_band(dri_score):
    if dri_score <= 0.2:
        return 'Low', '🟢'
    elif dri_score <= 0.4:
        return 'Medium', '🟡'
    elif dri_score <= 0.6:
        return 'High', '🟠'
    else:
        return 'Very High', '🔴'

session = get_snowflake_session()

if session:
    with st.expander("How to use this page", expanded=False, icon=":material/help:"):
        st.markdown("""
### Purpose
This page provides a **complete view of a resident's DRI history**, including:
- Current active indicators and their status (with expiry countdown)
- **Occurrence Timeline**: Every approved detection event chronologically
- Historical clinical decisions (expired, resolved, rejected)
- **DRI Trend**: Score changes over time with event markers
- LLM analysis history

### Use Cases
- **Full Resident Review**: See all indicators ever flagged for a resident
- **Audit Trail**: Track clinical decisions over time
- **Trend Analysis**: Understand resident deterioration patterns
- **Threshold Tracking**: See progress toward threshold-based indicators
        """)
    
    st.caption("Complete resident view with full indicator history and trend analysis")
    
    residents = execute_query_df("""
        SELECT DISTINCT 
               n.RESIDENT_ID, 
               n.SYSTEM_KEY as CLIENT_SYSTEM_KEY
        FROM ACTIVE_RESIDENT_NOTES n
        ORDER BY n.RESIDENT_ID
    """, session)
    
    if residents is not None and len(residents) > 0:
        resident_options = {f"Resident {r['RESIDENT_ID']} ({r['CLIENT_SYSTEM_KEY']})": r['RESIDENT_ID'] 
                          for _, r in residents.iterrows()}
        
        selected_label = st.selectbox("Select Resident", list(resident_options.keys()))
        selected_resident = resident_options[selected_label]
        
        st.divider()
        
        decisions = execute_query_df(f"""
            SELECT DEFICIT_ID, DEFICIT_NAME, DECISION_TYPE, DEFICIT_TYPE,
                   DECISION_DATE, EXPIRY_DATE, STATUS, DECISION_REASON, DECIDED_BY
            FROM DRI_CLINICAL_DECISIONS
            WHERE RESIDENT_ID = {selected_resident}
            ORDER BY DECISION_DATE DESC
        """, session)
        
        active_count = 0
        expired_count = 0
        rejected_count = 0
        
        if decisions is not None:
            active_decisions = decisions[(decisions['STATUS'] == 'ACTIVE') & (decisions['DECISION_TYPE'] == 'CONFIRMED')]
            active_count = len(active_decisions)
            expired_count = len(decisions[decisions['STATUS'] == 'EXPIRED'])
            rejected_count = len(decisions[decisions['DECISION_TYPE'] == 'REJECTED'])
        
        dri_score = active_count / 32.0
        severity_band, severity_emoji = calculate_severity_band(dri_score)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("DRI Score", f"{dri_score:.4f}")
        col2.metric("Active Indicators", active_count)
        col3.metric("Expired", expired_count)
        col4.metric("Rejected (False Positives)", rejected_count)
        
        st.markdown(f"### {severity_emoji} Severity Band: **{severity_band}**")
        
        tab_active, tab_occurrences, tab_history, tab_trend, tab_analyses = st.tabs([
            "Active Indicators", 
            "Occurrence Timeline", 
            "Decision History", 
            "DRI Trend",
            "LLM Analyses"
        ])
        
        with tab_active:
            st.subheader("Currently Active Indicators")
            st.caption("Indicators currently contributing to the DRI score")
            
            if decisions is not None:
                active = decisions[(decisions['STATUS'] == 'ACTIVE') & (decisions['DECISION_TYPE'] == 'CONFIRMED')]
                
                if len(active) > 0:
                    persistent = active[active['DEFICIT_TYPE'] == 'PERSISTENT']
                    fluctuating = active[active['DEFICIT_TYPE'] != 'PERSISTENT']
                    
                    if len(persistent) > 0:
                        st.markdown("#### Persistent Indicators (Never Expire)")
                        for _, row in persistent.iterrows():
                            with st.container(border=True):
                                col_info, col_badge = st.columns([4, 1])
                                with col_info:
                                    st.markdown(f"**{row['DEFICIT_ID']} - {row['DEFICIT_NAME']}**")
                                    st.caption(f"Confirmed by {row['DECIDED_BY']} on {row['DECISION_DATE']}")
                                    if row['DECISION_REASON']:
                                        st.caption(f"Evidence: {row['DECISION_REASON'][:100]}...")
                                with col_badge:
                                    st.badge("PERMANENT", icon=":material/all_inclusive:", color="blue")
                    
                    if len(fluctuating) > 0:
                        st.markdown("#### Fluctuating Indicators (Time-Limited)")
                        for _, row in fluctuating.iterrows():
                            with st.container(border=True):
                                col_info, col_expiry = st.columns([3, 1])
                                with col_info:
                                    st.markdown(f"**{row['DEFICIT_ID']} - {row['DEFICIT_NAME']}**")
                                    st.caption(f"Confirmed by {row['DECIDED_BY']} on {row['DECISION_DATE']}")
                                    if row['DECISION_REASON']:
                                        st.caption(f"Evidence: {row['DECISION_REASON'][:100]}...")
                                with col_expiry:
                                    if row['EXPIRY_DATE']:
                                        try:
                                            exp_date = row['EXPIRY_DATE']
                                            if isinstance(exp_date, str):
                                                exp_date = datetime.strptime(exp_date[:10], '%Y-%m-%d').date()
                                            today = datetime.now().date()
                                            days_left = (exp_date - today).days
                                            
                                            if days_left <= 1:
                                                st.badge(f"{days_left}d left", icon=":material/warning:", color="red")
                                            elif days_left <= 7:
                                                st.badge(f"{days_left}d left", icon=":material/schedule:", color="orange")
                                            else:
                                                st.badge(f"{days_left}d left", icon=":material/schedule:", color="green")
                                            
                                            progress = max(0, min(1, days_left / 90))
                                            st.progress(progress)
                                        except:
                                            st.caption(f"Expires: {row['EXPIRY_DATE']}")
                else:
                    st.info("No active indicators for this resident.", icon=":material/info:")
            else:
                st.info("No clinical decisions found for this resident.", icon=":material/info:")
        
        with tab_occurrences:
            st.subheader("Occurrence Timeline")
            st.caption("Chronological list of all approved indicator detections")
            
            occurrences = execute_query_df(f"""
                SELECT OCCURRENCE_ID, DEFICIT_ID, DEFICIT_NAME, OCCURRENCE_DATE,
                       SOURCE_TABLE, EVIDENCE_TEXT, APPROVED_BY, APPROVAL_DATE
                FROM DRI_INDICATOR_OCCURRENCES
                WHERE RESIDENT_ID = {selected_resident}
                ORDER BY OCCURRENCE_DATE DESC, APPROVAL_DATE DESC
            """, session)
            
            rules_data = execute_query_df("""
                SELECT DEFICIT_ID, DEFICIT_TYPE, 
                       LOOKBACK_DAYS_HISTORIC as LOOKBACK_DAYS,
                       RULES_JSON
                FROM DRI_RULES
                WHERE IS_CURRENT_VERSION = TRUE
            """, session)
            
            threshold_rules = {}
            if rules_data is not None:
                for _, r in rules_data.iterrows():
                    threshold = 1
                    rules_json = r['RULES_JSON']
                    if rules_json and isinstance(rules_json, list) and len(rules_json) > 0:
                        threshold = rules_json[0].get('threshold', 1) if isinstance(rules_json[0], dict) else 1
                    if threshold > 1:
                        lb = r['LOOKBACK_DAYS']
                        try:
                            lookback = 9999 if lb is None or str(lb).lower() == 'all' else int(lb)
                        except (ValueError, TypeError):
                            lookback = 9999
                        threshold_rules[r['DEFICIT_ID']] = {
                            'threshold': threshold,
                            'lookback_days': lookback
                        }
            
            if occurrences is not None and len(occurrences) > 0:
                for deficit_id in threshold_rules:
                    rule = threshold_rules[deficit_id]
                    deficit_occs = occurrences[occurrences['DEFICIT_ID'] == deficit_id]
                    recent_count = len(deficit_occs[deficit_occs['OCCURRENCE_DATE'] >= (datetime.now().date() - timedelta(days=rule['lookback_days']))])
                    
                    if recent_count > 0:
                        deficit_name = deficit_occs.iloc[0]['DEFICIT_NAME'] if len(deficit_occs) > 0 else deficit_id
                        progress_pct = min(1.0, recent_count / rule['threshold'])
                        
                        with st.container(border=True):
                            st.markdown(f"**{deficit_id} - {deficit_name}**: {recent_count} of {rule['threshold']} occurrences")
                            st.progress(progress_pct)
                            if recent_count >= rule['threshold']:
                                st.success("Threshold met - indicator active", icon=":material/check:")
                            else:
                                st.info(f"Need {rule['threshold'] - recent_count} more occurrences in {rule['lookback_days']} day window", icon=":material/info:")
                
                st.markdown("---")
                st.markdown("#### All Occurrences")
                
                for _, occ in occurrences.iterrows():
                    with st.expander(f"{occ['OCCURRENCE_DATE']} - {occ['DEFICIT_ID']}: {occ['DEFICIT_NAME']}"):
                        st.markdown(f"**Source:** `{occ['SOURCE_TABLE']}`")
                        st.markdown(f"**Evidence:** {occ['EVIDENCE_TEXT'][:500] if occ['EVIDENCE_TEXT'] else 'N/A'}...")
                        st.caption(f"Approved by {occ['APPROVED_BY']} on {occ['APPROVAL_DATE']}")
            else:
                st.info("No occurrences recorded yet. Occurrences are logged when indicators are approved in the Review Queue.", icon=":material/info:")
        
        with tab_history:
            st.subheader("Complete Decision History")
            st.caption("All clinical decisions made for this resident")
            
            if decisions is not None and len(decisions) > 0:
                st.dataframe(
                    decisions,
                    use_container_width=True,
                    column_config={
                        'DEFICIT_ID': st.column_config.TextColumn('ID', width='small'),
                        'DEFICIT_NAME': st.column_config.TextColumn('Deficit', width='medium'),
                        'DECISION_TYPE': st.column_config.TextColumn('Decision', width='small'),
                        'DEFICIT_TYPE': st.column_config.TextColumn('Type', width='small'),
                        'DECISION_DATE': st.column_config.DateColumn('Date', width='small'),
                        'EXPIRY_DATE': st.column_config.DateColumn('Expires', width='small'),
                        'STATUS': st.column_config.TextColumn('Status', width='small'),
                        'DECISION_REASON': st.column_config.TextColumn('Reason', width='large'),
                        'DECIDED_BY': st.column_config.TextColumn('By', width='medium')
                    }
                )
            else:
                st.info("No decision history for this resident.", icon=":material/info:")
        
        with tab_trend:
            st.subheader("DRI Score Trend")
            st.caption("Historical DRI score changes over time")
            
            processor_runs = execute_query_df(f"""
                SELECT RUN_TIMESTAMP, 
                       DETAILS_JSON:indicators_activated::INT as ACTIVATED,
                       DETAILS_JSON:indicators_expired::INT as EXPIRED,
                       RUN_TYPE
                FROM DRI_PROCESSOR_RUNS
                WHERE RESIDENT_ID = {selected_resident}
                OR (RESIDENT_ID IS NULL AND RUN_TYPE = 'TIME')
                ORDER BY RUN_TIMESTAMP DESC
                LIMIT 50
            """, session)
            
            score_history = execute_query_df(f"""
                SELECT LOAD_TIMESTAMP as DATE, DRI_SCORE, SEVERITY_BAND
                FROM DRI_DEFICIT_SUMMARY
                WHERE RESIDENT_ID = {selected_resident}
                ORDER BY LOAD_TIMESTAMP DESC
                LIMIT 30
            """, session)
            
            if score_history is not None and len(score_history) > 0:
                import pandas as pd
                
                chart_data = score_history.rename(columns={'DATE': 'date', 'DRI_SCORE': 'DRI Score'})
                chart_data = chart_data.sort_values('date')
                
                st.line_chart(chart_data.set_index('date')['DRI Score'], use_container_width=True)
                
                st.markdown("#### Score History")
                st.dataframe(
                    score_history,
                    use_container_width=True,
                    column_config={
                        'DATE': st.column_config.DatetimeColumn('Date', width='medium'),
                        'DRI_SCORE': st.column_config.NumberColumn('DRI Score', format="%.4f", width='small'),
                        'SEVERITY_BAND': st.column_config.TextColumn('Severity', width='small')
                    }
                )
            else:
                st.info("No historical score data available yet.", icon=":material/info:")
            
            st.markdown("---")
            st.markdown("#### Recent Events")
            
            events = execute_query_df(f"""
                SELECT 
                    DECISION_DATE as EVENT_DATE,
                    CASE DECISION_TYPE 
                        WHEN 'CONFIRMED' THEN '✅ Activated'
                        WHEN 'REJECTED' THEN '❌ Rejected'
                    END as EVENT_TYPE,
                    DEFICIT_ID || ' - ' || DEFICIT_NAME as DESCRIPTION,
                    DECIDED_BY as ACTOR
                FROM DRI_CLINICAL_DECISIONS
                WHERE RESIDENT_ID = {selected_resident}
                
                UNION ALL
                
                SELECT 
                    APPROVAL_DATE as EVENT_DATE,
                    '📝 Occurrence' as EVENT_TYPE,
                    DEFICIT_ID || ' - ' || DEFICIT_NAME as DESCRIPTION,
                    APPROVED_BY as ACTOR
                FROM DRI_INDICATOR_OCCURRENCES
                WHERE RESIDENT_ID = {selected_resident}
                
                ORDER BY EVENT_DATE DESC
                LIMIT 20
            """, session)
            
            if events is not None and len(events) > 0:
                for _, event in events.iterrows():
                    st.markdown(f"**{event['EVENT_DATE']}** | {event['EVENT_TYPE']} | {event['DESCRIPTION']} | by {event['ACTOR']}")
            else:
                st.info("No events recorded yet.", icon=":material/info:")
        
        with tab_analyses:
            st.subheader("All LLM Analyses")
            st.caption("Historical LLM analysis runs for this resident")
            
            analyses = execute_query_df(f"""
                SELECT ANALYSIS_ID, ANALYSIS_TIMESTAMP, MODEL_USED, PROMPT_VERSION, 
                       PROCESSING_TIME_MS, BATCH_RUN_ID
                FROM DRI_LLM_ANALYSIS
                WHERE RESIDENT_ID = {selected_resident}
                ORDER BY ANALYSIS_TIMESTAMP DESC
                LIMIT 20
            """, session)
            
            if analyses is not None and len(analyses) > 0:
                for _, analysis in analyses.iterrows():
                    with st.expander(f"Analysis: {analysis['ANALYSIS_TIMESTAMP']} ({analysis['MODEL_USED']})"):
                        st.write(f"**Prompt Version:** {analysis['PROMPT_VERSION']}")
                        st.write(f"**Processing Time:** {analysis['PROCESSING_TIME_MS']}ms")
                        st.write(f"**Batch ID:** {analysis['BATCH_RUN_ID']}")
                        
                        raw = execute_query(f"""
                            SELECT RAW_RESPONSE FROM DRI_LLM_ANALYSIS
                            WHERE ANALYSIS_ID = '{analysis['ANALYSIS_ID']}'
                        """, session)
                        
                        if raw and raw[0]['RAW_RESPONSE']:
                            with st.expander("View Raw JSON"):
                                st.json(raw[0]['RAW_RESPONSE'])
            else:
                st.info("No LLM analyses found for this resident.", icon=":material/info:")
    else:
        st.warning("No residents found in the system.", icon=":material/warning:")

else:
    st.error("Failed to connect to Snowflake", icon=":material/error:")
