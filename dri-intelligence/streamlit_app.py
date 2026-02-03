import streamlit as st

st.set_page_config(
    page_title="DRI Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

from src.connection_helper import get_snowflake_session, execute_query_df

PAGES = {
    "Dashboard": "app_pages/dashboard.py",
    "Prompt engineering": "app_pages/prompt_engineering.py",
    "Review queue": "app_pages/review_queue.py",
    "Analysis results": "app_pages/analysis_results.py",
    "Configuration": "app_pages/configuration.py",
    "Claude vs Regex": "app_pages/comparison.py",
    "Quality metrics": "app_pages/quality_metrics.py",
}

PAGE_ICONS = {
    "Dashboard": "📊",
    "Prompt engineering": "🔬",
    "Review queue": "✅",
    "Analysis results": "📈",
    "Configuration": "⚙️",
    "Claude vs Regex": "⚖️",
    "Quality metrics": "📉",
}

st.sidebar.title("DRI Intelligence")
st.sidebar.caption("AI-powered clinical analysis")

selection = st.sidebar.radio(
    "Navigate to",
    list(PAGES.keys()),
    format_func=lambda x: f"{PAGE_ICONS.get(x, '')} {x}"
)

st.title(f"{PAGE_ICONS.get(selection, '')} {selection}")

if selection == "Dashboard":
    st.caption("Deteriorating Resident Index - AI-powered clinical analysis")
    
    with st.expander("How to use this application", expanded=False):
        st.markdown("""
### What is DRI Intelligence?
This application uses AI (Claude LLM) to detect health indicators in aged care resident records, replacing the traditional regex/keyword matching approach that has a ~10% false positive rate. The goal is to achieve <1% false positives.

### Typical Workflow
1. **Configure** your client settings and production prompt in the **Configuration** page
2. **Test & tune** prompts on individual residents in **Prompt Engineering**
3. **Compare** Claude vs Regex results in **Claude vs Regex** to validate accuracy
4. **Review & approve** DRI changes in the **Review Queue**
5. **Monitor** results in **Analysis Results** and this **Dashboard**
6. **Track quality** over time in **Quality Metrics**

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
        
        st.success("Connected to Snowflake")
    else:
        st.error("Failed to connect to Snowflake. Check your connection settings.")

else:
    exec(open(PAGES[selection]).read())
