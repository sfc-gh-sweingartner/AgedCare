import streamlit as st
import json

from src.connection_helper import get_snowflake_session, execute_query_df

st.warning("**To be completed** - This page displays results from analyses run on the Prompt engineering page.", icon=":material/construction:")

with st.expander("How to use this page", expanded=False, icon=":material/help:"):
    st.markdown("""
### Purpose
This page provides an **audit trail** of all LLM analyses run on residents. Use it to review historical results, debug issues, or understand how the AI arrived at its decisions.

### How to Use
1. **Filter by resident** to see analyses for a specific person
2. **Adjust max results** to control how many records are shown
3. **Expand each analysis** to see details:
   - Model used and prompt version
   - Processing time
   - Full raw JSON response from the LLM

### Understanding the Data
| Field | Description |
|-------|-------------|
| **Analysis ID** | Unique identifier for this analysis run |
| **Resident ID** | The resident who was analyzed |
| **Model Used** | Which LLM model processed the request |
| **Prompt Version** | Which prompt template was used |
| **Processing Time** | How long the analysis took (milliseconds) |
| **Raw Response** | Complete JSON output from the AI |

### Tips
- Compare responses across different models for the same resident
- Use this page to verify evidence before approving changes in Review Queue
- Processing times over 60 seconds may indicate context size issues
- If results seem incomplete, the response may have been truncated (check Configuration for token settings)

### Related Features
- **Quality metrics** page shows aggregated quality scores for evaluations
- **Snowsight AI Observability** provides deeper trace analysis (see Quality Metrics page for access instructions)
    """)

with st.expander("AI Observability in Snowsight", expanded=False, icon=":material/monitoring:"):
    st.markdown("""
### For Deeper Analysis

While this page shows the raw LLM outputs, Snowflake's **AI Observability** feature in Snowsight provides additional capabilities:

**Trace Analysis**
- View the complete call chain for each analysis
- See token counts, latency breakdown, and cost estimates
- Drill down into individual prompt/completion pairs

**How to Access**
1. Log into **Snowsight** (your Snowflake web interface)
2. Go to **Monitoring** → **AI Observability** in the left sidebar
3. Filter by `AGEDCARE` database
4. Search for specific analysis IDs or resident IDs

**Direct SQL Access**
```sql
-- Query analysis history with quality scores
SELECT 
    a.ANALYSIS_ID,
    a.RESIDENT_ID,
    a.MODEL_USED,
    a.PROCESSING_TIME_MS,
    e.GROUNDEDNESS_SCORE,
    e.IS_CORRECT
FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS a
LEFT JOIN AGEDCARE.AGEDCARE.DRI_EVALUATION_DETAIL e 
    ON a.ANALYSIS_ID = e.ANALYSIS_ID
ORDER BY a.ANALYSIS_TIMESTAMP DESC;
```

For full AI Observability documentation, see: [Snowflake AI Observability](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-observability)
    """)

session = get_snowflake_session()

if session:
    st.caption("View detailed LLM analysis results and audit trail.")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Search")
        
        residents = execute_query_df("""
            SELECT DISTINCT RESIDENT_ID 
            FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS
            ORDER BY RESIDENT_ID
        """, session)
        
        if residents is not None and len(residents) > 0:
            resident_filter = st.selectbox("Filter by resident", ["All"] + residents['RESIDENT_ID'].tolist())
        else:
            resident_filter = "All"
        
        limit = st.slider("Max results", 5, 50, 10)
    
    with col2:
        if resident_filter == "All":
            analyses = execute_query_df(f"""
                SELECT ANALYSIS_ID, RESIDENT_ID, CLIENT_SYSTEM_KEY, 
                       MODEL_USED, PROMPT_VERSION, PROCESSING_TIME_MS,
                       ANALYSIS_TIMESTAMP, RAW_RESPONSE
                FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS
                ORDER BY ANALYSIS_TIMESTAMP DESC
                LIMIT {limit}
            """, session)
        else:
            analyses = execute_query_df(f"""
                SELECT ANALYSIS_ID, RESIDENT_ID, CLIENT_SYSTEM_KEY, 
                       MODEL_USED, PROMPT_VERSION, PROCESSING_TIME_MS,
                       ANALYSIS_TIMESTAMP, RAW_RESPONSE
                FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS
                WHERE RESIDENT_ID = {resident_filter}
                ORDER BY ANALYSIS_TIMESTAMP DESC
                LIMIT {limit}
            """, session)
        
        if analyses is not None and len(analyses) > 0:
            for idx, row in analyses.iterrows():
                with st.expander(f"Analysis {row['ANALYSIS_ID'][:8]}... - Resident {row['RESIDENT_ID']} - {row['ANALYSIS_TIMESTAMP']}"):
                    with st.container(border=True):
                        col_m1, col_m2, col_m3 = st.columns(3)
                        col_m1.metric("Model", row['MODEL_USED'])
                        col_m2.metric("Prompt version", row['PROMPT_VERSION'])
                        col_m3.metric("Processing time", f"{row['PROCESSING_TIME_MS']}ms")
                    
                    st.markdown("**Raw LLM response:**")
                    
                    if row['RAW_RESPONSE']:
                        try:
                            if isinstance(row['RAW_RESPONSE'], str):
                                parsed = json.loads(row['RAW_RESPONSE'])
                            else:
                                parsed = row['RAW_RESPONSE']
                            st.json(parsed)
                        except:
                            st.code(str(row['RAW_RESPONSE']), language="json")
                    else:
                        st.info("No response data stored", icon=":material/info:")
        else:
            st.info("No analysis results found. Run an analysis from the Prompt engineering page.", icon=":material/info:")

else:
    st.error("Failed to connect to Snowflake", icon=":material/error:")
