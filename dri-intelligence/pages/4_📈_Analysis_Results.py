import streamlit as st
import json
import sys
sys.path.insert(0, '/Users/sweingartner/CoCo/AgedCare/dri-intelligence')

from src.connection_helper import get_snowflake_session, execute_query_df

st.set_page_config(page_title="Analysis Results", page_icon="📈", layout="wide")
st.title("📈 Analysis Results")

session = get_snowflake_session()

if session:
    st.markdown("View detailed LLM analysis results and audit trail.")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Search")
        
        residents = execute_query_df("""
            SELECT DISTINCT RESIDENT_ID 
            FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS
            ORDER BY RESIDENT_ID
        """, session)
        
        if residents is not None and len(residents) > 0:
            resident_filter = st.selectbox("Filter by Resident", ["All"] + residents['RESIDENT_ID'].tolist())
        else:
            resident_filter = "All"
        
        limit = st.slider("Max Results", 5, 50, 10)
    
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
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("Model", row['MODEL_USED'])
                    col_m2.metric("Prompt Version", row['PROMPT_VERSION'])
                    col_m3.metric("Processing Time", f"{row['PROCESSING_TIME_MS']}ms")
                    
                    st.markdown("---")
                    st.markdown("**Raw LLM Response:**")
                    
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
                        st.info("No response data stored")
        else:
            st.info("No analysis results found. Run an analysis from the Prompt Engineering page.")

else:
    st.error("Failed to connect to Snowflake")
