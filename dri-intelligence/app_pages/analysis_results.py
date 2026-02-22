import streamlit as st
import json

from src.connection_helper import get_snowflake_session, execute_query_df

with st.expander("How to use this page", expanded=False, icon=":material/help:"):
    st.markdown("""
### Purpose
This page provides an **audit trail** of all LLM analyses run on residents. Use it to review historical results, debug issues, or understand how the AI arrived at its decisions.

### How to Use
1. **Filter by resident** to see analyses for a specific person
2. **Filter by batch** to see results from a specific batch run
3. **Expand each analysis** to see details:
   - Model used and prompt version
   - Processing time
   - Detected indicators with evidence

### Understanding the Data
| Field | Description |
|-------|-------------|
| **Analysis ID** | Unique identifier for this analysis run |
| **Resident ID** | The resident who was analyzed |
| **Model Used** | Which LLM model processed the request |
| **Prompt Version** | Which prompt template was used |
| **Processing Time** | How long the analysis took (milliseconds) |
| **Indicators Detected** | Number of DRI indicators found |

### Tips
- Compare responses across different models for the same resident
- Use this page to verify evidence before approving changes in Review Queue
- Processing times over 60 seconds may indicate context size issues
    """)

session = get_snowflake_session()

if session:
    st.caption("View detailed LLM analysis results and audit trail.")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Filters")
        
        residents = execute_query_df("""
            SELECT DISTINCT RESIDENT_ID 
            FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS
            ORDER BY RESIDENT_ID
        """, session)
        
        if residents is not None and len(residents) > 0:
            resident_filter = st.selectbox("Filter by resident", ["All"] + residents['RESIDENT_ID'].tolist())
        else:
            resident_filter = "All"
        
        batches = execute_query_df("""
            SELECT DISTINCT BATCH_RUN_ID 
            FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS
            WHERE BATCH_RUN_ID IS NOT NULL
            ORDER BY BATCH_RUN_ID DESC
        """, session)
        
        if batches is not None and len(batches) > 0:
            batch_options = ["All"] + [b[:8] + "..." for b in batches['BATCH_RUN_ID'].tolist()]
            batch_ids = ["All"] + batches['BATCH_RUN_ID'].tolist()
            batch_filter_display = st.selectbox("Filter by batch", batch_options)
            batch_filter = batch_ids[batch_options.index(batch_filter_display)]
        else:
            batch_filter = "All"
        
        limit = st.slider("Max results", 5, 50, 10)
    
    with col2:
        where_clauses = []
        if resident_filter != "All":
            where_clauses.append(f"RESIDENT_ID = {resident_filter}")
        if batch_filter != "All":
            where_clauses.append(f"BATCH_RUN_ID = '{batch_filter}'")
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        analyses = execute_query_df(f"""
            SELECT 
                ANALYSIS_ID, 
                RESIDENT_ID, 
                CLIENT_SYSTEM_KEY, 
                MODEL_USED, 
                PROMPT_VERSION, 
                PROCESSING_TIME_MS,
                ANALYSIS_TIMESTAMP, 
                RAW_RESPONSE,
                RAW_RESPONSE:summary:indicators_detected::NUMBER as INDICATORS_DETECTED,
                ARRAY_SIZE(RAW_RESPONSE:indicators) as INDICATOR_COUNT,
                BATCH_RUN_ID
            FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS
            {where_sql}
            ORDER BY ANALYSIS_TIMESTAMP DESC
            LIMIT {limit}
        """, session)
        
        if analyses is not None and len(analyses) > 0:
            st.subheader(f"Analysis Results ({len(analyses)} records)")
            
            for idx, row in analyses.iterrows():
                indicator_count = row['INDICATOR_COUNT'] or row['INDICATORS_DETECTED'] or 0
                batch_label = f" | Batch: {row['BATCH_RUN_ID']}" if row['BATCH_RUN_ID'] else ""
                
                with st.expander(f"Resident {row['RESIDENT_ID']} - {indicator_count} indicators - {row['ANALYSIS_TIMESTAMP']}{batch_label}"):
                    with st.container(border=True):
                        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                        col_m1.metric("Model", row['MODEL_USED'] or "N/A")
                        col_m2.metric("Prompt", row['PROMPT_VERSION'] or "N/A")
                        col_m3.metric("Time", f"{row['PROCESSING_TIME_MS'] or 0}ms")
                        col_m4.metric("Indicators", indicator_count)
                    
                    if row['RAW_RESPONSE']:
                        try:
                            if isinstance(row['RAW_RESPONSE'], str):
                                parsed = json.loads(row['RAW_RESPONSE'])
                            else:
                                parsed = row['RAW_RESPONSE']
                            
                            if 'summary' in parsed:
                                summary = parsed['summary']
                                st.markdown(f"**Analysis Notes:** {summary.get('analysis_notes', 'N/A')}")
                            
                            if 'indicators' in parsed and parsed['indicators']:
                                st.markdown("**Detected Indicators:**")
                                for ind in parsed['indicators']:
                                    confidence = ind.get('confidence', 'N/A')
                                    conf_emoji = "🟢" if confidence == 'high' else "🟡" if confidence == 'medium' else "🔴"
                                    review_badge = " ⚠️" if ind.get('requires_review') else ""
                                    
                                    with st.container(border=True):
                                        st.markdown(f"**{conf_emoji} {ind.get('deficit_id', 'Unknown')} - {ind.get('deficit_name', 'Unknown')}**{review_badge}")
                                        st.caption(ind.get('reasoning', 'No reasoning provided'))
                                        
                                        if 'evidence' in ind and ind['evidence']:
                                            for ev in ind['evidence'][:2]:
                                                st.markdown(f"📄 *{ev.get('source_table', 'N/A')}*: {ev.get('text_excerpt', 'N/A')[:100]}...")
                            
                            with st.expander("View raw JSON"):
                                st.json(parsed)
                                
                        except Exception as e:
                            st.code(str(row['RAW_RESPONSE']), language="json")
                    else:
                        st.info("No response data stored", icon=":material/info:")
        else:
            st.info("No analysis results found. Run a batch test from the Batch Testing page to generate results.", icon=":material/info:")

else:
    st.error("Failed to connect to Snowflake", icon=":material/error:")
