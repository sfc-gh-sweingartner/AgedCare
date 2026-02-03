import streamlit as st
import json
import sys
sys.path.insert(0, '/Users/sweingartner/CoCo/AgedCare/dri-intelligence')

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

st.set_page_config(page_title="Review Queue", page_icon="📋", layout="wide")
st.title("📋 Review Queue")

session = get_snowflake_session()

if session:
    st.markdown("""
    Review and approve/reject DRI changes detected by the LLM.
    Each row represents a resident's proposed DRI score change.
    """)
    
    col1, col2, col3 = st.columns(3)
    
    pending = execute_query_df("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'PENDING'", session)
    approved = execute_query_df("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'APPROVED'", session)
    rejected = execute_query_df("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'REJECTED'", session)
    
    col1.metric("Pending", pending['CNT'].iloc[0] if pending is not None else 0)
    col2.metric("Approved", approved['CNT'].iloc[0] if approved is not None else 0)
    col3.metric("Rejected", rejected['CNT'].iloc[0] if rejected is not None else 0)
    
    st.markdown("---")
    
    status_filter = st.selectbox("Filter by Status", ["PENDING", "ALL", "APPROVED", "REJECTED"])
    
    if status_filter == "ALL":
        queue_query = """
            SELECT QUEUE_ID, RESIDENT_ID, CLIENT_SYSTEM_KEY, 
                   CURRENT_DRI_SCORE, PROPOSED_DRI_SCORE,
                   CURRENT_SEVERITY_BAND, PROPOSED_SEVERITY_BAND,
                   INDICATORS_ADDED, INDICATORS_REMOVED,
                   CHANGE_SUMMARY, STATUS, CREATED_TIMESTAMP
            FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE
            ORDER BY CREATED_TIMESTAMP DESC
        """
    else:
        queue_query = f"""
            SELECT QUEUE_ID, RESIDENT_ID, CLIENT_SYSTEM_KEY, 
                   CURRENT_DRI_SCORE, PROPOSED_DRI_SCORE,
                   CURRENT_SEVERITY_BAND, PROPOSED_SEVERITY_BAND,
                   INDICATORS_ADDED, INDICATORS_REMOVED,
                   CHANGE_SUMMARY, STATUS, CREATED_TIMESTAMP
            FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE
            WHERE STATUS = '{status_filter}'
            ORDER BY CREATED_TIMESTAMP DESC
        """
    
    queue_data = execute_query_df(queue_query, session)
    
    if queue_data is not None and len(queue_data) > 0:
        for idx, row in queue_data.iterrows():
            with st.expander(f"Resident {row['RESIDENT_ID']} - {row['STATUS']} - DRI: {row['CURRENT_DRI_SCORE']:.4f} → {row['PROPOSED_DRI_SCORE']:.4f}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Current State:**")
                    st.metric("DRI Score", f"{row['CURRENT_DRI_SCORE']:.4f}" if row['CURRENT_DRI_SCORE'] else "N/A")
                    st.markdown(f"Severity: **{row['CURRENT_SEVERITY_BAND']}**")
                
                with col2:
                    st.markdown("**Proposed State:**")
                    st.metric("DRI Score", f"{row['PROPOSED_DRI_SCORE']:.4f}" if row['PROPOSED_DRI_SCORE'] else "N/A")
                    st.markdown(f"Severity: **{row['PROPOSED_SEVERITY_BAND']}**")
                
                st.markdown("---")
                st.markdown(f"**Changes:** +{row['INDICATORS_ADDED'] or 0} indicators, -{row['INDICATORS_REMOVED'] or 0} cleared")
                st.markdown(f"**Summary:** {row['CHANGE_SUMMARY'] or 'No summary available'}")
                
                if row['STATUS'] == 'PENDING':
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    
                    with col_btn1:
                        if st.button(f"✅ Approve", key=f"approve_{row['QUEUE_ID']}"):
                            execute_query(f"""
                                UPDATE AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE 
                                SET STATUS = 'APPROVED', 
                                    REVIEW_TIMESTAMP = CURRENT_TIMESTAMP(),
                                    REVIEWER_USER = CURRENT_USER()
                                WHERE QUEUE_ID = '{row['QUEUE_ID']}'
                            """, session)
                            st.success("Approved!")
                            st.rerun()
                    
                    with col_btn2:
                        if st.button(f"❌ Reject", key=f"reject_{row['QUEUE_ID']}"):
                            execute_query(f"""
                                UPDATE AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE 
                                SET STATUS = 'REJECTED', 
                                    REVIEW_TIMESTAMP = CURRENT_TIMESTAMP(),
                                    REVIEWER_USER = CURRENT_USER()
                                WHERE QUEUE_ID = '{row['QUEUE_ID']}'
                            """, session)
                            st.warning("Rejected!")
                            st.rerun()
                    
                    with col_btn3:
                        reviewer_notes = st.text_input("Notes", key=f"notes_{row['QUEUE_ID']}")
    else:
        st.info("No items in the review queue. Run LLM analysis from the Prompt Engineering page to generate review items.")
    
    st.markdown("---")
    st.subheader("Quick Actions")
    
    if st.button("🔄 Refresh Queue"):
        st.rerun()

else:
    st.error("Failed to connect to Snowflake")
