import streamlit as st
import json
from datetime import datetime

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
- Current active indicators and their status
- Historical indicators (expired, resolved, rejected)
- Clinical decision history
- Leave status and admission tracking

### Use Cases
- **Full Resident Review**: See all indicators ever flagged for a resident
- **Audit Trail**: Track clinical decisions over time
- **Trend Analysis**: Understand resident deterioration patterns
        """)
    
    st.caption("Complete resident view with full indicator history")
    
    residents = execute_query_df("""
        SELECT DISTINCT 
               n.RESIDENT_ID, 
               n.SYSTEM_KEY as CLIENT_SYSTEM_KEY
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES n
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
            FROM AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS
            WHERE RESIDENT_ID = {selected_resident}
            ORDER BY DECISION_DATE DESC
        """, session)
        
        active_count = 0
        expired_count = 0
        rejected_count = 0
        
        if decisions is not None:
            active_count = len(decisions[decisions['STATUS'] == 'ACTIVE'])
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
        
        tab_active, tab_history, tab_all_analyses = st.tabs(["Active Indicators", "Decision History", "All LLM Analyses"])
        
        with tab_active:
            st.subheader("Currently Active Indicators")
            
            if decisions is not None:
                active = decisions[decisions['STATUS'] == 'ACTIVE']
                
                if len(active) > 0:
                    persistent = active[active['DEFICIT_TYPE'] == 'PERSISTENT']
                    fluctuating = active[active['DEFICIT_TYPE'] != 'PERSISTENT']
                    
                    if len(persistent) > 0:
                        st.markdown("#### Persistent Indicators (Never Expire)")
                        for _, row in persistent.iterrows():
                            with st.container(border=True):
                                st.markdown(f"**{row['DEFICIT_ID']} - {row['DEFICIT_NAME']}**")
                                st.caption(f"Confirmed by {row['DECIDED_BY']} on {row['DECISION_DATE']}")
                                if row['DECISION_REASON']:
                                    st.caption(f"Reason: {row['DECISION_REASON']}")
                    
                    if len(fluctuating) > 0:
                        st.markdown("#### Fluctuating Indicators (Time-Limited)")
                        for _, row in fluctuating.iterrows():
                            with st.container(border=True):
                                st.markdown(f"**{row['DEFICIT_ID']} - {row['DEFICIT_NAME']}**")
                                st.caption(f"Confirmed by {row['DECIDED_BY']} on {row['DECISION_DATE']}")
                                if row['EXPIRY_DATE']:
                                    st.caption(f"Expires: {row['EXPIRY_DATE']}")
                                if row['DECISION_REASON']:
                                    st.caption(f"Reason: {row['DECISION_REASON']}")
                else:
                    st.info("No active indicators for this resident.", icon=":material/info:")
            else:
                st.info("No clinical decisions found for this resident.", icon=":material/info:")
        
        with tab_history:
            st.subheader("Complete Decision History")
            
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
        
        with tab_all_analyses:
            st.subheader("All LLM Analyses")
            
            analyses = execute_query_df(f"""
                SELECT ANALYSIS_ID, ANALYSIS_TIMESTAMP, MODEL_USED, PROMPT_VERSION, 
                       PROCESSING_TIME_MS, BATCH_RUN_ID
                FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS
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
                            SELECT RAW_RESPONSE FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS
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
