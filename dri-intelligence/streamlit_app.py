import streamlit as st

st.set_page_config(
    page_title="DRI Intelligence",
    page_icon=":material/local_hospital:",
    layout="wide",
    initial_sidebar_state="expanded"
)

from src.connection_helper import get_snowflake_session, execute_query_df

page = st.navigation([
    st.Page("app_pages/dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
    st.Page("app_pages/prompt_engineering.py", title="Prompt engineering", icon=":material/science:"),
    st.Page("app_pages/review_queue.py", title="Review queue", icon=":material/checklist:"),
    st.Page("app_pages/analysis_results.py", title="Analysis results", icon=":material/analytics:"),
    st.Page("app_pages/configuration.py", title="Configuration", icon=":material/settings:"),
    st.Page("app_pages/comparison.py", title="Claude vs Regex", icon=":material/compare_arrows:"),
    st.Page("app_pages/quality_metrics.py", title="Quality metrics", icon=":material/monitoring:"),
], position="sidebar")

st.title(f"{page.icon} {page.title}")

if page.title == "Dashboard":
    st.caption("Deteriorating Resident Index - AI-powered clinical analysis")
    
    with st.expander("How to use this application", expanded=False, icon=":material/help:"):
        st.markdown("""
### What is DRI Intelligence?
This application uses AI (Claude LLM) to detect health indicators in aged care resident records, replacing the traditional regex/keyword matching approach that has a ~10% false positive rate. The goal is to achieve <1% false positives.

### Typical Workflow
1. **Configure** your client settings and production prompt in the **Configuration** page
2. **Test & tune** prompts on individual residents in **Prompt Engineering**
3. **Compare** Claude vs Regex results in **Claude vs Regex** to validate accuracy
4. **Run batch tests** on multiple residents in **Batch Testing**
5. **Review & approve** DRI changes in the **Review Queue**
6. **Monitor** results in **Analysis Results** and this **Dashboard**

### Page Guide
| Page | Purpose |
|------|--------|
| **Dashboard** | Overview metrics, recent analyses, system status |
| **Prompt Engineering** | Test prompts on individual residents, tune LLM parameters |
| **Review Queue** | Approve/reject AI-detected DRI indicator changes |
| **Analysis Results** | Browse historical LLM analysis outputs |
| **Configuration** | Client settings, form mappings, production model/prompt |
| **Claude vs Regex** | Side-by-side comparison showing false positive reduction (demo) |
| **Quality Metrics** | AI Observability metrics - groundedness, relevance, FP rates |
        """)
    
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
        
        with st.container(border=True):
            cols = st.columns(4)
            with cols[0]:
                st.metric("Residents in system", metrics['residents'])
            with cols[1]:
                st.metric("Pending reviews", metrics['pending'])
            with cols[2]:
                st.metric("DRI indicators", metrics['indicators'])
            with cols[3]:
                st.metric("Analyses run", metrics['analyses'])
        
        st.caption(":material/check_circle: Connected to Snowflake")
    else:
        st.error("Failed to connect to Snowflake. Check your connection settings.", icon=":material/error:")

page.run()
