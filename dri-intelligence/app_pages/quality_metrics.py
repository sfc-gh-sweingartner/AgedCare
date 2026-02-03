"""
Quality Metrics Page - AI Observability Dashboard
=================================================
This page displays quality metrics from Snowflake AI Observability,
including groundedness scores, false positive rates, and evaluation history.

Designed for clinicians - presents metrics in a user-friendly format
without requiring technical knowledge of the underlying AI Observability system.
"""

import streamlit as st
import json
from datetime import datetime, timedelta

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

st.caption("Monitor AI model quality metrics, false positive rates, and evaluation history")

with st.expander("How to use this page", expanded=False, icon=":material/help:"):
    st.markdown("""
### Purpose
This page shows **quality metrics** for the AI analysis system, helping you understand how well the prompts and models are performing over time.

### Key Metrics Explained

| Metric | What It Measures | Target |
|--------|------------------|--------|
| **False Positive Rate** | % of detections that were incorrect | <1% |
| **Groundedness** | How well responses are supported by actual data | >90% |
| **Context Relevance** | How relevant the retrieved context is | >85% |
| **Answer Relevance** | How well the response addresses the query | >85% |

### Sections

**Current Status**
- Shows the most recent evaluation results
- Green = meeting targets, Red = needs attention

**False Positive Trend**
- Chart showing FP rate over time
- Useful for tracking improvement after prompt changes

**Evaluation History**
- List of all evaluation runs with detailed metrics
- Click to expand and see per-resident breakdowns

### Running New Evaluations
Use the **Run Evaluation** section to test current prompt/model configurations.
Results appear in this dashboard after completion.

### For Auditors
All evaluation data is stored in Snowflake and can be accessed via:
- `AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS` - Summary metrics
- `AGEDCARE.AGEDCARE.DRI_EVALUATION_DETAIL` - Per-record details
- Snowsight AI Observability interface for deep trace analysis
    """)

session = get_snowflake_session()

if session:
    st.subheader("Current quality status")
    
    try:
        tables_exist = execute_query("""
            SELECT COUNT(*) as CNT 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'AGEDCARE' 
            AND TABLE_NAME = 'DRI_EVALUATION_METRICS'
        """, session)
        
        if not tables_exist or tables_exist[0]['CNT'] == 0:
            st.warning("AI Observability tables not yet created. Run the setup script first.", icon=":material/warning:")
            st.code("Run: setup_ai_observability.sql", language="text")
            
            with st.expander("Setup instructions", expanded=True, icon=":material/build:"):
                st.markdown("""
                1. Open a Snowflake worksheet
                2. Run the script: `dri-intelligence/setup_ai_observability.sql`
                3. Return to this page and refresh
                
                This creates the necessary tables and views for quality metrics tracking.
                """)
            st.stop()
    except:
        pass
    
    latest_eval = execute_query_df("""
        SELECT 
            EVALUATION_ID,
            RUN_NAME,
            CREATED_TIMESTAMP,
            PROMPT_VERSION,
            MODEL_USED,
            TOTAL_RECORDS,
            RECORDS_EVALUATED,
            ROUND(AVG_GROUNDEDNESS_SCORE * 100, 1) as GROUNDEDNESS_PCT,
            ROUND(AVG_CONTEXT_RELEVANCE_SCORE * 100, 1) as CONTEXT_RELEVANCE_PCT,
            ROUND(AVG_ANSWER_RELEVANCE_SCORE * 100, 1) as ANSWER_RELEVANCE_PCT,
            ROUND(FALSE_POSITIVE_RATE * 100, 2) as FP_RATE_PCT,
            STATUS
        FROM AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS
        ORDER BY CREATED_TIMESTAMP DESC
        LIMIT 1
    """, session)
    
    if latest_eval is not None and len(latest_eval) > 0:
        eval_row = latest_eval.iloc[0]
        
        with st.container(border=True):
            st.markdown(f"**Latest evaluation:** {eval_row['RUN_NAME']}")
            st.caption(f"Run on {eval_row['CREATED_TIMESTAMP']} | Model: {eval_row['MODEL_USED']} | Prompt: {eval_row['PROMPT_VERSION']}")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                fp_rate = eval_row['FP_RATE_PCT'] or 0
                st.metric("False positive rate", f"{fp_rate}%")
                if fp_rate <= 1.0:
                    st.badge("Target met", icon=":material/check:", color="green")
                else:
                    st.badge("Above target", icon=":material/warning:", color="red")
            
            with col2:
                groundedness = eval_row['GROUNDEDNESS_PCT'] or 0
                st.metric("Groundedness", f"{groundedness}%")
                if groundedness >= 90:
                    st.badge("Good", icon=":material/check:", color="green")
                elif groundedness >= 75:
                    st.badge("Acceptable", icon=":material/info:", color="orange")
                else:
                    st.badge("Needs improvement", icon=":material/warning:", color="red")
            
            with col3:
                context_rel = eval_row['CONTEXT_RELEVANCE_PCT'] or 0
                st.metric("Context relevance", f"{context_rel}%")
                if context_rel >= 85:
                    st.badge("Good", icon=":material/check:", color="green")
                else:
                    st.badge("Review needed", icon=":material/info:", color="orange")
            
            with col4:
                answer_rel = eval_row['ANSWER_RELEVANCE_PCT'] or 0
                st.metric("Answer relevance", f"{answer_rel}%")
                if answer_rel >= 85:
                    st.badge("Good", icon=":material/check:", color="green")
                else:
                    st.badge("Review needed", icon=":material/info:", color="orange")
    else:
        with st.container(border=True):
            st.info("No evaluations have been run yet. Use the 'Run evaluation' section below to start.", icon=":material/info:")
    
    st.subheader("False positive rate trend")
    
    fp_trend = execute_query_df("""
        SELECT 
            DATE_TRUNC('day', CREATED_TIMESTAMP)::DATE as EVAL_DATE,
            ROUND(AVG(FALSE_POSITIVE_RATE) * 100, 2) as AVG_FP_RATE_PCT,
            ROUND(AVG(AVG_GROUNDEDNESS_SCORE) * 100, 1) as AVG_GROUNDEDNESS_PCT,
            COUNT(*) as EVAL_COUNT
        FROM AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS
        WHERE STATUS = 'COMPLETED'
        GROUP BY DATE_TRUNC('day', CREATED_TIMESTAMP)::DATE
        ORDER BY EVAL_DATE
    """, session)
    
    if fp_trend is not None and len(fp_trend) > 0:
        col_chart, col_target = st.columns([3, 1])
        
        with col_chart:
            st.line_chart(fp_trend.set_index('EVAL_DATE')['AVG_FP_RATE_PCT'], use_container_width=True)
        
        with col_target:
            with st.container(border=True):
                st.markdown("**Target: <1%**")
                st.caption("Red line = 1% target threshold")
                
                current_fp = fp_trend['AVG_FP_RATE_PCT'].iloc[-1] if len(fp_trend) > 0 else 0
                if current_fp <= 1.0:
                    st.success(f"Current: {current_fp}%", icon=":material/check_circle:")
                else:
                    st.error(f"Current: {current_fp}%", icon=":material/error:")
    else:
        st.info("Run evaluations to see the false positive rate trend over time.", icon=":material/info:")
    
    st.subheader("Run evaluation")
    
    with st.container(border=True):
        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
        
        with col_cfg1:
            prompt_versions = execute_query_df("""
                SELECT VERSION_NUMBER, IS_ACTIVE 
                FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS
                ORDER BY CREATED_TIMESTAMP DESC
            """, session)
            
            if prompt_versions is not None and len(prompt_versions) > 0:
                version_options = prompt_versions['VERSION_NUMBER'].tolist()
                active_version = prompt_versions[prompt_versions['IS_ACTIVE'] == True]['VERSION_NUMBER'].tolist()
                default_idx = version_options.index(active_version[0]) if active_version else 0
                eval_prompt_version = st.selectbox("Prompt version", version_options, index=default_idx)
            else:
                eval_prompt_version = st.text_input("Prompt version", value="v1.0")
        
        with col_cfg2:
            model_options = [
                'claude-3-5-sonnet',
                'claude-sonnet-4-5',
                'claude-haiku-4-5',
                'mistral-large2',
                'llama3.1-70b'
            ]
            eval_model = st.selectbox("Model", model_options)
        
        with col_cfg3:
            residents = execute_query_df("""
                SELECT DISTINCT RESIDENT_ID 
                FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES
                ORDER BY RESIDENT_ID
            """, session)
            
            if residents is not None and len(residents) > 0:
                resident_list = ["All (up to 10)"] + [str(r) for r in residents['RESIDENT_ID'].tolist()]
            else:
                resident_list = ["All (up to 10)"]
            
            eval_residents = st.selectbox("Residents to evaluate", resident_list)
        
        eval_name = st.text_input(
            "Evaluation name (optional)",
            value=f"Eval_{eval_prompt_version}_{datetime.now().strftime('%Y%m%d')}",
            help="A descriptive name for this evaluation run"
        )
        
        run_eval = st.button("Run evaluation", type="primary", icon=":material/play_arrow:")
    
    if run_eval:
        with st.spinner("Running evaluation... This may take a few minutes."):
            try:
                from src.ai_observability import DRIObservabilityManager
                
                obs_manager = DRIObservabilityManager(session)
                
                if eval_residents == "All (up to 10)":
                    resident_ids = None
                else:
                    resident_ids = [int(eval_residents)]
                
                results = obs_manager.run_evaluation(
                    prompt_version=eval_prompt_version,
                    model=eval_model,
                    run_name=eval_name,
                    resident_ids=resident_ids
                )
                
                st.success(f"Evaluation complete! Processed {results['records_evaluated']} residents.", icon=":material/check_circle:")
                
                with st.container(border=True):
                    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                    with col_r1:
                        fp_rate = results['metrics'].get('false_positive_rate', 0) * 100
                        st.metric("False positive rate", f"{fp_rate:.2f}%")
                    with col_r2:
                        groundedness = results['metrics'].get('avg_groundedness', 0) * 100
                        st.metric("Groundedness", f"{groundedness:.1f}%")
                    with col_r3:
                        st.metric("Records evaluated", results['records_evaluated'])
                    with col_r4:
                        avg_latency = results['metrics'].get('avg_latency_ms', 0)
                        st.metric("Avg latency", f"{avg_latency}ms")
                
                st.rerun()
                
            except ImportError as e:
                st.error("AI Observability module not available. Please install TruLens packages.", icon=":material/error:")
                st.code("pip install trulens-core trulens-connectors-snowflake trulens-providers-cortex")
            except Exception as e:
                st.error(f"Evaluation failed: {e}", icon=":material/error:")
                import traceback
                with st.expander("Error details"):
                    st.code(traceback.format_exc())
    
    st.subheader("Evaluation history")
    
    eval_history = execute_query_df("""
        SELECT 
            EVALUATION_ID,
            RUN_NAME,
            CREATED_TIMESTAMP,
            PROMPT_VERSION,
            MODEL_USED,
            RECORDS_EVALUATED,
            ROUND(FALSE_POSITIVE_RATE * 100, 2) as FP_RATE_PCT,
            ROUND(AVG_GROUNDEDNESS_SCORE * 100, 1) as GROUNDEDNESS_PCT,
            ROUND(AVG_LATENCY_MS, 0) as AVG_LATENCY_MS,
            STATUS
        FROM AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS
        ORDER BY CREATED_TIMESTAMP DESC
        LIMIT 20
    """, session)
    
    if eval_history is not None and len(eval_history) > 0:
        for _, row in eval_history.iterrows():
            status_icon = ":material/check_circle:" if row['STATUS'] == 'COMPLETED' else ":material/pending:"
            fp_rate = row['FP_RATE_PCT'] or 0
            groundedness = row['GROUNDEDNESS_PCT'] or 0
            
            with st.expander(f"{row['RUN_NAME']} - FP: {fp_rate}% | Groundedness: {groundedness}%", icon=status_icon):
                col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                
                with col_d1:
                    st.markdown(f"**Prompt:** {row['PROMPT_VERSION']}")
                    st.markdown(f"**Model:** {row['MODEL_USED']}")
                
                with col_d2:
                    st.markdown(f"**Records:** {row['RECORDS_EVALUATED']}")
                    st.markdown(f"**Latency:** {row['AVG_LATENCY_MS']}ms")
                
                with col_d3:
                    st.metric("FP Rate", f"{fp_rate}%")
                
                with col_d4:
                    st.metric("Groundedness", f"{groundedness}%")
                
                details = execute_query_df(f"""
                    SELECT 
                        RESIDENT_ID,
                        INDICATORS_DETECTED,
                        ROUND(GROUNDEDNESS_SCORE * 100, 1) as GROUNDEDNESS_PCT,
                        IS_CORRECT,
                        MISMATCH_DETAILS,
                        LATENCY_MS
                    FROM AGEDCARE.AGEDCARE.DRI_EVALUATION_DETAIL
                    WHERE EVALUATION_ID = '{row['EVALUATION_ID']}'
                    ORDER BY RECORD_INDEX
                """, session)
                
                if details is not None and len(details) > 0:
                    st.markdown("**Per-resident breakdown:**")
                    st.dataframe(details, use_container_width=True)
    else:
        st.info("No evaluation history available. Run an evaluation to see results here.", icon=":material/info:")
    
    st.subheader("Ground truth management")
    
    with st.expander("Manage ground truth datasets", icon=":material/dataset:"):
        st.markdown("""
        Ground truth datasets contain manually validated indicator assignments for residents.
        These are used to measure accuracy during evaluations.
        """)
        
        ground_truth = execute_query_df("""
            SELECT 
                DATASET_NAME,
                COUNT(*) as RESIDENT_COUNT,
                SUM(EXPECTED_INDICATOR_COUNT) as TOTAL_INDICATORS,
                MAX(VALIDATED_TIMESTAMP) as LAST_UPDATED
            FROM AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH
            WHERE IS_ACTIVE = TRUE
            GROUP BY DATASET_NAME
            ORDER BY DATASET_NAME
        """, session)
        
        if ground_truth is not None and len(ground_truth) > 0:
            st.dataframe(ground_truth, use_container_width=True)
        else:
            st.info("No ground truth datasets configured. Add validated test cases to enable accuracy measurement.", icon=":material/info:")

else:
    st.error("Failed to connect to Snowflake", icon=":material/error:")
