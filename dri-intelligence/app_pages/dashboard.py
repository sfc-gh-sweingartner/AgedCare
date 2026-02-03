import streamlit as st
import sys
sys.path.insert(0, '/Users/sweingartner/CoCo/AgedCare/dri-intelligence')

from src.connection_helper import get_snowflake_session, execute_query_df

session = get_snowflake_session()

if session:
    with st.expander("Understanding this dashboard", expanded=False, icon=":material/help:"):
        st.markdown("""
### Metrics Overview
| Metric | Description |
|--------|-------------|
| **Total residents** | Number of unique residents with progress notes in the system |
| **Pending reviews** | DRI changes awaiting human approval in Review Queue |
| **Approved** | Changes that have been approved and applied |
| **Rejected** | Changes that were rejected by reviewers |

### Data Summary
Shows record counts across the four main data sources:
- **Progress Notes**: Free-text clinical observations
- **Medications**: Prescribed medications and their status
- **Observations**: Vital signs and measured data
- **Assessment Forms**: Structured questionnaire responses

### Recent Analyses
Shows the last 10 LLM analyses run, including model used and processing time.
        """)

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        
        residents = execute_query_df("SELECT COUNT(DISTINCT RESIDENT_ID) as CNT FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES", session)
        pending = execute_query_df("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'PENDING'", session)
        approved = execute_query_df("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'APPROVED'", session)
        rejected = execute_query_df("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'REJECTED'", session)
        
        with col1:
            st.metric("Total residents", residents['CNT'].iloc[0] if residents is not None else 0)
        with col2:
            st.metric("Pending reviews", pending['CNT'].iloc[0] if pending is not None else 0, delta_color="inverse")
        with col3:
            st.metric("Approved", approved['CNT'].iloc[0] if approved is not None else 0)
        with col4:
            st.metric("Rejected", rejected['CNT'].iloc[0] if rejected is not None else 0)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Active prompt version")
        prompt = execute_query_df("""
            SELECT VERSION_NUMBER, DESCRIPTION, CREATED_TIMESTAMP 
            FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS 
            WHERE IS_ACTIVE = TRUE
        """, session)
        if prompt is not None and len(prompt) > 0:
            st.markdown(f"**Version:** {prompt['VERSION_NUMBER'].iloc[0]}")
            st.caption(f"Description: {prompt['DESCRIPTION'].iloc[0]}")
            st.caption(f"Created: {prompt['CREATED_TIMESTAMP'].iloc[0]}")
        else:
            st.warning("No active prompt version found", icon=":material/warning:")
    
    with col2:
        st.subheader("Client configuration")
        config = execute_query_df("""
            SELECT CLIENT_SYSTEM_KEY, CLIENT_NAME, VERSION, IS_ACTIVE 
            FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG
        """, session)
        if config is not None and len(config) > 0:
            st.dataframe(config, use_container_width=True)
        else:
            st.warning("No client configurations found", icon=":material/warning:")
    
    st.subheader("Recent LLM analyses")
    
    analyses = execute_query_df("""
        SELECT RESIDENT_ID, MODEL_USED, PROMPT_VERSION, PROCESSING_TIME_MS, ANALYSIS_TIMESTAMP
        FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS
        ORDER BY ANALYSIS_TIMESTAMP DESC
        LIMIT 10
    """, session)
    
    if analyses is not None and len(analyses) > 0:
        st.dataframe(analyses, use_container_width=True)
    else:
        st.info("No analyses run yet. Use the Prompt engineering page to run your first analysis.", icon=":material/info:")
    
    st.subheader("Data summary")
    
    data_counts = execute_query_df("""
        SELECT 'Progress Notes' as SOURCE, COUNT(*) as RECORDS FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES
        UNION ALL SELECT 'Medications', COUNT(*) FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION
        UNION ALL SELECT 'Observations', COUNT(*) FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS
        UNION ALL SELECT 'Assessment Forms', COUNT(*) FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_ASSESSMENT_FORMS
        ORDER BY RECORDS DESC
    """, session)
    
    if data_counts is not None:
        st.dataframe(data_counts, use_container_width=True)

else:
    st.error("Failed to connect to Snowflake", icon=":material/error:")
