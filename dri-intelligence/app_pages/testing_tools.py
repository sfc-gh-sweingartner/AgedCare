import streamlit as st

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

session = get_snowflake_session()

if session:
    with st.expander("How to use this page", expanded=False, icon=":material/help:"):
        st.markdown("""
### Purpose
This page provides **testing utilities** to reset DRI analysis data during development and prompt iteration.

### Features
- **Clear Review Decisions**: Remove approval/rejection decisions from the review queue
- **Clear Analysis Results**: Remove LLM analysis records
- **Clear Indicator Status**: Reset deficit status for residents
- **Selective Clearing**: Choose specific residents or clear all

### When to Use
- After improving prompts and wanting to re-test the same residents
- When resetting test data for a fresh evaluation run
- Before running batch tests on previously analyzed residents

### ⚠️ Warning
These operations **permanently delete** data. Use with caution in production environments.
        """)

    st.title("Testing Tools")
    st.caption("Reset analysis data for re-testing after prompt improvements")
    
    st.warning("⚠️ These operations permanently delete data. Use for development/testing only.", icon=":material/warning:")
    
    residents = execute_query_df("""
        SELECT DISTINCT r.RESIDENT_ID,
               COUNT(DISTINCT rq.QUEUE_ID) as REVIEW_COUNT,
               COUNT(DISTINCT lla.ANALYSIS_ID) as ANALYSIS_COUNT,
               COUNT(DISTINCT ds.DEFICIT_ID) as DEFICIT_COUNT
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES r
        LEFT JOIN AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE rq ON r.RESIDENT_ID = rq.RESIDENT_ID
        LEFT JOIN AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS lla ON r.RESIDENT_ID = lla.RESIDENT_ID
        LEFT JOIN AGEDCARE.AGEDCARE.DRI_DEFICIT_STATUS ds ON r.RESIDENT_ID = ds.RESIDENT_ID
        GROUP BY r.RESIDENT_ID
        ORDER BY r.RESIDENT_ID
    """, session)
    
    if residents is not None and len(residents) > 0:
        tab1, tab2, tab3 = st.tabs([
            "🗑️ Clear by Resident", 
            "🧹 Clear All Data",
            "📊 Data Summary"
        ])
        
        with tab1:
            st.subheader("Clear Data for Selected Residents")
            
            resident_list = residents['RESIDENT_ID'].tolist()
            
            col1, col2 = st.columns([2, 1])
            with col1:
                selected_residents = st.multiselect(
                    "Select residents to clear",
                    resident_list,
                    help="Choose one or more residents"
                )
            with col2:
                if st.button("Select All", key="select_all_btn"):
                    st.session_state['selected_residents_clear'] = resident_list
                    st.rerun()
            
            if selected_residents:
                st.markdown(f"**Selected:** {len(selected_residents)} resident(s)")
                
                selected_data = residents[residents['RESIDENT_ID'].isin(selected_residents)]
                total_reviews = selected_data['REVIEW_COUNT'].sum()
                total_analyses = selected_data['ANALYSIS_COUNT'].sum()
                total_deficits = selected_data['DEFICIT_COUNT'].sum()
                
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("Review Queue Items", int(total_reviews))
                with col_m2:
                    st.metric("Analysis Records", int(total_analyses))
                with col_m3:
                    st.metric("Deficit Status Records", int(total_deficits))
                
                st.markdown("---")
                st.markdown("**Select what to clear:**")
                
                clear_reviews = st.checkbox("Clear Review Queue (approvals/rejections)", value=True, key="clear_reviews_cb")
                clear_analyses = st.checkbox("Clear LLM Analysis results", value=True, key="clear_analyses_cb")
                clear_deficits = st.checkbox("Clear Deficit Status", value=False, key="clear_deficits_cb")
                clear_decisions = st.checkbox("Clear Clinical Decisions", value=False, key="clear_decisions_cb")
                
                st.markdown("---")
                
                resident_ids_str = ",".join([str(r) for r in selected_residents])
                
                confirm_text = st.text_input(
                    "Type 'CONFIRM' to enable the clear button",
                    key="confirm_resident_clear"
                )
                
                if st.button("🗑️ Clear Selected Data", type="primary", 
                           disabled=confirm_text != "CONFIRM",
                           key="clear_resident_btn"):
                    try:
                        deleted_counts = []
                        
                        if clear_reviews:
                            result = execute_query(f"""
                                DELETE FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE 
                                WHERE RESIDENT_ID IN ({resident_ids_str})
                            """, session)
                            deleted_counts.append(f"Review Queue: cleared")
                        
                        if clear_analyses:
                            result = execute_query(f"""
                                DELETE FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS 
                                WHERE RESIDENT_ID IN ({resident_ids_str})
                            """, session)
                            deleted_counts.append(f"LLM Analysis: cleared")
                        
                        if clear_deficits:
                            result = execute_query(f"""
                                DELETE FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_STATUS 
                                WHERE RESIDENT_ID IN ({resident_ids_str})
                            """, session)
                            result = execute_query(f"""
                                DELETE FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_DETAIL 
                                WHERE RESIDENT_ID IN ({resident_ids_str})
                            """, session)
                            deleted_counts.append(f"Deficit Status/Detail: cleared")
                        
                        if clear_decisions:
                            result = execute_query(f"""
                                DELETE FROM AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS 
                                WHERE RESIDENT_ID IN ({resident_ids_str})
                            """, session)
                            deleted_counts.append(f"Clinical Decisions: cleared")
                        
                        st.success(f"✅ Cleared data for {len(selected_residents)} resident(s): {', '.join(deleted_counts)}")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error clearing data: {e}")
            else:
                st.info("Select one or more residents to clear their data", icon=":material/info:")
        
        with tab2:
            st.subheader("Clear All Testing Data")
            st.error("⚠️ This will delete ALL analysis and review data across ALL residents!", icon=":material/dangerous:")
            
            summary = execute_query("""
                SELECT 
                    (SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE) as REVIEW_COUNT,
                    (SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS) as ANALYSIS_COUNT,
                    (SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_STATUS) as DEFICIT_STATUS_COUNT,
                    (SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_DETAIL) as DEFICIT_DETAIL_COUNT,
                    (SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS) as DECISION_COUNT,
                    (SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH) as GROUND_TRUTH_COUNT
            """, session)
            
            if summary:
                st.markdown("**Current data counts:**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Review Queue", summary[0]['REVIEW_COUNT'])
                    st.metric("Clinical Decisions", summary[0]['DECISION_COUNT'])
                with col2:
                    st.metric("LLM Analysis", summary[0]['ANALYSIS_COUNT'])
                    st.metric("Ground Truth", summary[0]['GROUND_TRUTH_COUNT'])
                with col3:
                    st.metric("Deficit Status", summary[0]['DEFICIT_STATUS_COUNT'])
                    st.metric("Deficit Detail", summary[0]['DEFICIT_DETAIL_COUNT'])
            
            st.markdown("---")
            st.markdown("**Select tables to clear:**")
            
            clear_all_reviews = st.checkbox("Clear ALL Review Queue", value=False, key="clear_all_reviews")
            clear_all_analyses = st.checkbox("Clear ALL LLM Analysis", value=False, key="clear_all_analyses")
            clear_all_deficits = st.checkbox("Clear ALL Deficit Status & Detail", value=False, key="clear_all_deficits")
            clear_all_decisions = st.checkbox("Clear ALL Clinical Decisions", value=False, key="clear_all_decisions")
            clear_all_ground_truth = st.checkbox("Clear ALL Ground Truth", value=False, key="clear_all_gt")
            
            st.markdown("---")
            
            confirm_all = st.text_input(
                "Type 'DELETE ALL' to enable the clear button",
                key="confirm_all_clear"
            )
            
            if st.button("🗑️ Clear All Selected Tables", type="primary",
                       disabled=confirm_all != "DELETE ALL",
                       key="clear_all_btn"):
                try:
                    cleared = []
                    
                    if clear_all_reviews:
                        execute_query("DELETE FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE", session)
                        cleared.append("Review Queue")
                    
                    if clear_all_analyses:
                        execute_query("DELETE FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS", session)
                        cleared.append("LLM Analysis")
                    
                    if clear_all_deficits:
                        execute_query("DELETE FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_STATUS", session)
                        execute_query("DELETE FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_DETAIL", session)
                        cleared.append("Deficit Status/Detail")
                    
                    if clear_all_decisions:
                        execute_query("DELETE FROM AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS", session)
                        cleared.append("Clinical Decisions")
                    
                    if clear_all_ground_truth:
                        execute_query("DELETE FROM AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH", session)
                        cleared.append("Ground Truth")
                    
                    if cleared:
                        st.success(f"✅ Cleared: {', '.join(cleared)}")
                        st.rerun()
                    else:
                        st.warning("No tables selected to clear")
                        
                except Exception as e:
                    st.error(f"Error: {e}")
        
        with tab3:
            st.subheader("Data Summary")
            
            st.markdown("**Records by Resident:**")
            st.dataframe(
                residents.rename(columns={
                    'RESIDENT_ID': 'Resident',
                    'REVIEW_COUNT': 'Reviews',
                    'ANALYSIS_COUNT': 'Analyses',
                    'DEFICIT_COUNT': 'Deficits'
                }),
                use_container_width=True,
                hide_index=True
            )
            
            st.markdown("---")
            st.markdown("**Review Status Breakdown:**")
            
            review_status = execute_query_df("""
                SELECT STATUS, COUNT(*) as COUNT
                FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE
                GROUP BY STATUS
                ORDER BY COUNT DESC
            """, session)
            
            if review_status is not None and len(review_status) > 0:
                st.dataframe(review_status, use_container_width=True, hide_index=True)
            else:
                st.info("No review queue data", icon=":material/info:")
            
            st.markdown("---")
            st.markdown("**Analysis by Prompt Version:**")
            
            analysis_by_version = execute_query_df("""
                SELECT PROMPT_VERSION, COUNT(*) as COUNT, 
                       COUNT(DISTINCT RESIDENT_ID) as RESIDENTS
                FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS
                GROUP BY PROMPT_VERSION
                ORDER BY COUNT DESC
            """, session)
            
            if analysis_by_version is not None and len(analysis_by_version) > 0:
                st.dataframe(analysis_by_version, use_container_width=True, hide_index=True)
            else:
                st.info("No analysis data", icon=":material/info:")
    else:
        st.info("No resident data found", icon=":material/info:")

else:
    st.error("Failed to connect to Snowflake")
