import streamlit as st
import sys
sys.path.insert(0, '/Users/sweingartner/CoCo/AgedCare/dri-intelligence')

st.set_page_config(
    page_title="DRI Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏥 DRI Intelligence solution")
st.caption("Deteriorating Resident Index - AI-powered clinical analysis")

st.write("""
This solution uses Claude 4.5 (via Snowflake Cortex) to analyze aged care resident records 
and identify DRI deficit indicators with <1% false positive rate.
""")

with st.expander("ℹ️ Navigation guide", expanded=False):
    st.write("""
- **Dashboard** - Overview metrics and status
- **Prompt engineering** - Test and tune LLM prompts
- **Review queue** - Approve/reject DRI changes
- **Analysis results** - View detailed LLM analysis
- **Configuration** - Manage client settings
    """)

from src.connection_helper import get_snowflake_session, execute_query_df

session = get_snowflake_session()

@st.cache_data(ttl=60)
def load_dashboard_metrics(_session):
    residents = execute_query_df("SELECT COUNT(DISTINCT RESIDENT_ID) as CNT FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES", _session)
    pending = execute_query_df("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'PENDING'", _session)
    indicators = execute_query_df("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS", _session)
    analyses = execute_query_df("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS", _session)
    return {
        'residents': residents['CNT'].iloc[0] if residents is not None else 0,
        'pending': pending['CNT'].iloc[0] if pending is not None else 0,
        'indicators': indicators['CNT'].iloc[0] if indicators is not None else 0,
        'analyses': analyses['CNT'].iloc[0] if analyses is not None else 0
    }

if session:
    metrics = load_dashboard_metrics(session)
    
    cols = st.columns(4)
    with cols[0]:
        st.metric("Residents in system", metrics['residents'])
    with cols[1]:
        st.metric("Pending reviews", metrics['pending'])
    with cols[2]:
        st.metric("DRI indicators", metrics['indicators'])
    with cols[3]:
        st.metric("Analyses run", metrics['analyses'])
    
    st.caption("✓ Connected to Snowflake")
else:
    st.error("Failed to connect to Snowflake. Check your connection settings.")
