import streamlit as st
import json
import sys
sys.path.insert(0, '/Users/sweingartner/CoCo/AgedCare/dri-intelligence')

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

session = get_snowflake_session()

if session:
    with st.expander("How to use this page", expanded=False, icon=":material/help:"):
        st.markdown("""
### Purpose
This is the **human-in-the-loop approval workflow**. When the AI detects changes to a resident's DRI indicators, those changes are queued here for review before being applied to production DRI scores.

### Workflow
1. **Filter by status** to see Pending, Approved, or Rejected items
2. **Review each resident's proposed changes**:
   - Current DRI score vs Proposed DRI score
   - Number of indicators added/removed
   - Change summary explaining what was detected
3. **Approve** to apply the DRI changes to production
4. **Reject** to discard the changes (with optional notes)

### Understanding the Queue
| Field | Description |
|-------|-------------|
| **Current DRI Score** | The resident's existing score before AI analysis |
| **Proposed DRI Score** | What the score would be if changes are approved |
| **Indicators Added** | New health conditions detected by the AI |
| **Indicators Removed** | Conditions the AI determined are no longer present |

### DRI Score Formula
`DRI Score = Active Indicators / 33`

Severity bands: Low (0-0.2), Medium (0.2-0.4), High (0.4-0.6), Very High (0.6-1.0)

### Tips
- Review the **Analysis Results** page for detailed evidence before approving
- Rejections help improve the AI over time through feedback learning
- Use the **Refresh queue** button to see newly processed residents
        """)

    st.caption("Review and approve/reject DRI changes detected by the LLM. Each row represents a resident's proposed DRI score change.")
    
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        
        pending = execute_query_df("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'PENDING'", session)
        approved = execute_query_df("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'APPROVED'", session)
        rejected = execute_query_df("SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS = 'REJECTED'", session)
        
        col1.metric("Pending", pending['CNT'].iloc[0] if pending is not None else 0)
        col2.metric("Approved", approved['CNT'].iloc[0] if approved is not None else 0)
        col3.metric("Rejected", rejected['CNT'].iloc[0] if rejected is not None else 0)
    
    status_filter = st.selectbox("Filter by status", ["PENDING", "ALL", "APPROVED", "REJECTED"])
    
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
                    st.markdown("**Current state:**")
                    st.metric("DRI score", f"{row['CURRENT_DRI_SCORE']:.4f}" if row['CURRENT_DRI_SCORE'] else "N/A")
                    st.markdown(f"Severity: **{row['CURRENT_SEVERITY_BAND']}**")
                
                with col2:
                    st.markdown("**Proposed state:**")
                    st.metric("DRI score", f"{row['PROPOSED_DRI_SCORE']:.4f}" if row['PROPOSED_DRI_SCORE'] else "N/A")
                    st.markdown(f"Severity: **{row['PROPOSED_SEVERITY_BAND']}**")
                
                st.markdown(f"**Changes:** +{row['INDICATORS_ADDED'] or 0} indicators, -{row['INDICATORS_REMOVED'] or 0} cleared")
                st.markdown(f"**Summary:** {row['CHANGE_SUMMARY'] or 'No summary available'}")
                
                if row['STATUS'] == 'PENDING':
                    with st.container(horizontal=True):
                        if st.button("Approve", key=f"approve_{row['QUEUE_ID']}", icon=":material/check:"):
                            execute_query(f"""
                                UPDATE AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE 
                                SET STATUS = 'APPROVED', 
                                    REVIEW_TIMESTAMP = CURRENT_TIMESTAMP(),
                                    REVIEWER_USER = CURRENT_USER()
                                WHERE QUEUE_ID = '{row['QUEUE_ID']}'
                            """, session)
                            st.success("Approved!", icon=":material/check_circle:")
                            st.rerun()
                        
                        if st.button("Reject", key=f"reject_{row['QUEUE_ID']}", icon=":material/close:"):
                            execute_query(f"""
                                UPDATE AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE 
                                SET STATUS = 'REJECTED', 
                                    REVIEW_TIMESTAMP = CURRENT_TIMESTAMP(),
                                    REVIEWER_USER = CURRENT_USER()
                                WHERE QUEUE_ID = '{row['QUEUE_ID']}'
                            """, session)
                            st.warning("Rejected!", icon=":material/close:")
                            st.rerun()
                    
                    reviewer_notes = st.text_input("Notes", key=f"notes_{row['QUEUE_ID']}")
    else:
        st.info("No items in the review queue. Run LLM analysis from the Prompt engineering page to generate review items.", icon=":material/info:")
    
    st.subheader("Quick actions")
    
    if st.button("Refresh queue", icon=":material/refresh:"):
        st.rerun()

else:
    st.error("Failed to connect to Snowflake", icon=":material/error:")
