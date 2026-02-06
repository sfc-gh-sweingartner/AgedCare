"""
Quality Metrics Page - AI Observability Dashboard

This page displays quality metrics from Snowflake AI Observability,
including groundedness scores, false positive rates, and evaluation history.

Evaluations are run via a separate SPCS Job container that has TruLens installed.
Results are stored in Snowflake and viewable in Snowsight AI & ML -> Evaluations.
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

### Running Evaluations
Evaluations are run via a dedicated SPCS container job with TruLens installed.
Click **Run Evaluation** to trigger the job - results appear after completion.

### Viewing in Snowsight
For detailed trace analysis, navigate to **AI & ML → Evaluations** in Snowsight.
    """)

with st.expander("Architecture overview", expanded=False, icon=":material/architecture:"):
    st.markdown("""
### Evaluation Architecture

The evaluation system uses a **separate SPCS Job container** to run TruLens-based
evaluations. This is required because TruLens has heavy ML dependencies that
exceed the Streamlit container runtime limits.

```
┌─────────────────────┐     EXECUTE JOB SERVICE      ┌──────────────────────┐
│  This Streamlit App │ ─────────────────────────▶   │  SPCS Evaluation Job │
│  (Quality Metrics)  │                              │  (TruLens + Python)  │
└─────────────────────┘                              └──────────────────────┘
         │                                                      │
         │  SELECT FROM                                         │ Writes to
         ▼                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Snowflake AI Observability Tables                        │
│                    (Traces, Evaluations, Metrics)                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Purpose |
|-----------|---------|
| **DRI_EVALUATION_JOB** | SPCS container with TruLens for running evaluations |
| **DRI_EVALUATION_METRICS** | Summary table for evaluation runs |
| **DRI_EVALUATION_DETAIL** | Per-resident evaluation details |
| **Snowsight AI Observability** | Native UI for trace analysis |

### Running Evaluations
Evaluations can be run on-demand via SQL command (no persistent service required).
    """)

session = get_snowflake_session()

if session:
    has_evaluation_data = False
    try:
        eval_check = execute_query("""
            SELECT COUNT(*) as CNT FROM AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS
            WHERE AVG_GROUNDEDNESS_SCORE IS NOT NULL
        """, session)
        has_evaluation_data = eval_check and eval_check[0]['CNT'] > 0
    except:
        pass
    
    if not has_evaluation_data:
        with st.expander("How to run evaluations", expanded=True, icon=":material/build:"):
            st.markdown("""
### Run an Evaluation

Evaluations are run as SPCS jobs. The container image is already deployed.

**Run evaluation via SQL:**
```sql
EXECUTE JOB SERVICE
IN COMPUTE POOL FULLSTACK_COMPUTE_POOL
FROM @AGEDCARE.AGEDCARE.DRI_EVAL_STAGE
SPEC = 'job-run-spec.yaml'
NAME = AGEDCARE.AGEDCARE.DRI_EVAL_RUN
QUERY_WAREHOUSE = COMPUTE_WH;
```

This will evaluate residents and compute quality metrics (groundedness, relevance scores).
            """)
    
    st.subheader("Current quality status")
    
    tables_exist = False
    try:
        check = execute_query("""
            SELECT COUNT(*) as CNT 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'AGEDCARE' 
            AND TABLE_NAME = 'DRI_EVALUATION_METRICS'
        """, session)
        tables_exist = check and check[0]['CNT'] > 0
    except:
        pass
    
    if not tables_exist:
        with st.container(border=True):
            st.info("Evaluation tables not yet created. Run the setup script first.", icon=":material/info:")
            st.code("Run: dri-intelligence/evaluation_job/setup_evaluation_job.sql", language="text")
    else:
        latest_eval = execute_query_df("""
            SELECT 
                EVALUATION_ID,
                RUN_NAME,
                CREATED_TIMESTAMP,
                PROMPT_VERSION,
                MODEL_USED,
                TOTAL_RECORDS,
                RECORDS_EVALUATED,
                AVG_LATENCY_MS,
                ROUND(AVG_GROUNDEDNESS_SCORE * 100, 1) as GROUNDEDNESS_PCT,
                ROUND(AVG_CONTEXT_RELEVANCE_SCORE * 100, 1) as CONTEXT_RELEVANCE_PCT,
                ROUND(AVG_ANSWER_RELEVANCE_SCORE * 100, 1) as ANSWER_RELEVANCE_PCT,
                ROUND(FALSE_POSITIVE_RATE * 100, 2) as FP_RATE_PCT,
                STATUS
            FROM AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS
            WHERE AVG_GROUNDEDNESS_SCORE IS NOT NULL
            ORDER BY CREATED_TIMESTAMP DESC
            LIMIT 1
        """, session)
        
        if latest_eval is not None and len(latest_eval) > 0:
            eval_row = latest_eval.iloc[0]
            
            has_quality_metrics = eval_row['GROUNDEDNESS_PCT'] is not None
            
            with st.container(border=True):
                st.markdown(f"**Latest evaluation:** {eval_row['RUN_NAME']}")
                st.caption(f"Run on {eval_row['CREATED_TIMESTAMP']} | Model: {eval_row['MODEL_USED']} | Prompt: {eval_row['PROMPT_VERSION']}")
                
                if not has_quality_metrics:
                    st.info("Quality metrics (groundedness, FP rate) require TruLens integration via the SPCS evaluation job. Current data shows execution metrics only.", icon=":material/info:")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    fp_rate = eval_row['FP_RATE_PCT'] or 0
                    if has_quality_metrics:
                        st.metric("False positive rate", f"{fp_rate}%")
                        if fp_rate <= 1.0:
                            st.badge("Target met", icon=":material/check:", color="green")
                        else:
                            st.badge("Above target", icon=":material/warning:", color="red")
                    else:
                        st.metric("Records evaluated", eval_row['RECORDS_EVALUATED'] or 0)
                
                with col2:
                    groundedness = eval_row['GROUNDEDNESS_PCT'] or 0
                    if has_quality_metrics:
                        st.metric("Groundedness", f"{groundedness}%")
                        if groundedness >= 90:
                            st.badge("Good", icon=":material/check:", color="green")
                        elif groundedness >= 75:
                            st.badge("Acceptable", icon=":material/info:", color="orange")
                        else:
                            st.badge("Needs improvement", icon=":material/warning:", color="red")
                    else:
                        st.metric("Total records", eval_row['TOTAL_RECORDS'] or 0)
                
                with col3:
                    context_rel = eval_row['CONTEXT_RELEVANCE_PCT'] or 0
                    if has_quality_metrics:
                        st.metric("Context relevance", f"{context_rel}%")
                        if context_rel >= 85:
                            st.badge("Good", icon=":material/check:", color="green")
                        else:
                            st.badge("Review needed", icon=":material/info:", color="orange")
                    else:
                        st.metric("Status", eval_row['STATUS'])
                
                with col4:
                    if has_quality_metrics:
                        answer_rel = eval_row['ANSWER_RELEVANCE_PCT'] or 0
                        st.metric("Answer relevance", f"{answer_rel}%")
                        if answer_rel >= 85:
                            st.badge("Good", icon=":material/check:", color="green")
                        else:
                            st.badge("Review needed", icon=":material/info:", color="orange")
                    else:
                        avg_latency = eval_row['AVG_LATENCY_MS'] or 0
                        st.metric("Avg latency", f"{int(avg_latency)}ms")
        else:
            with st.container(border=True):
                st.info("No evaluations have been run yet. Use the 'Run evaluation' section below to start.", icon=":material/info:")
        
        st.subheader("Quality metrics trend")
        
        metrics_trend = execute_query_df("""
            SELECT 
                CREATED_TIMESTAMP,
                RUN_NAME,
                ROUND(COALESCE(FALSE_POSITIVE_RATE, 0) * 100, 2) as FP_RATE_PCT,
                ROUND(COALESCE(AVG_GROUNDEDNESS_SCORE, 0) * 100, 1) as GROUNDEDNESS_PCT,
                ROUND(COALESCE(AVG_CONTEXT_RELEVANCE_SCORE, 0) * 100, 1) as CONTEXT_RELEVANCE_PCT,
                ROUND(COALESCE(AVG_ANSWER_RELEVANCE_SCORE, 0) * 100, 1) as ANSWER_RELEVANCE_PCT,
                RECORDS_EVALUATED,
                AVG_LATENCY_MS
            FROM AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS
            WHERE STATUS = 'COMPLETED'
            ORDER BY CREATED_TIMESTAMP
        """, session)
        
        if metrics_trend is not None and len(metrics_trend) > 0:
            tab_all, tab_quality, tab_latency = st.tabs(["All metrics", "Quality scores", "Performance"])
            
            with tab_all:
                chart_data = metrics_trend[['CREATED_TIMESTAMP', 'GROUNDEDNESS_PCT', 'CONTEXT_RELEVANCE_PCT', 'ANSWER_RELEVANCE_PCT']].copy()
                chart_data = chart_data.set_index('CREATED_TIMESTAMP')
                chart_data.columns = ['Groundedness %', 'Context Relevance %', 'Answer Relevance %']
                st.line_chart(chart_data, use_container_width=True)
                
                with st.container(border=True):
                    cols = st.columns(4)
                    latest = metrics_trend.iloc[-1]
                    with cols[0]:
                        st.metric("Latest groundedness", f"{latest['GROUNDEDNESS_PCT']}%")
                    with cols[1]:
                        st.metric("Latest context relevance", f"{latest['CONTEXT_RELEVANCE_PCT']}%")
                    with cols[2]:
                        st.metric("Latest answer relevance", f"{latest['ANSWER_RELEVANCE_PCT']}%")
                    with cols[3]:
                        st.metric("Latest FP rate", f"{latest['FP_RATE_PCT']}%")
            
            with tab_quality:
                st.markdown("**Quality score targets:**")
                st.caption("Groundedness: >90% | Context Relevance: >85% | Answer Relevance: >85%")
                
                for _, row in metrics_trend.iterrows():
                    with st.expander(f"{row['RUN_NAME']} - {row['CREATED_TIMESTAMP']}"):
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            g = row['GROUNDEDNESS_PCT']
                            st.metric("Groundedness", f"{g}%", delta="Good" if g >= 90 else "Below target")
                        with col2:
                            c = row['CONTEXT_RELEVANCE_PCT']
                            st.metric("Context Rel.", f"{c}%", delta="Good" if c >= 85 else "Below target")
                        with col3:
                            a = row['ANSWER_RELEVANCE_PCT']
                            st.metric("Answer Rel.", f"{a}%", delta="Good" if a >= 85 else "Below target")
                        with col4:
                            fp = row['FP_RATE_PCT']
                            st.metric("FP Rate", f"{fp}%", delta="Good" if fp <= 1 else "Above target")
            
            with tab_latency:
                latency_data = metrics_trend[['CREATED_TIMESTAMP', 'AVG_LATENCY_MS', 'RECORDS_EVALUATED']].copy()
                latency_data = latency_data.set_index('CREATED_TIMESTAMP')
                st.line_chart(latency_data['AVG_LATENCY_MS'], use_container_width=True)
                st.caption("Average latency (ms) per evaluation run")
        else:
            st.info("Run evaluations to see quality metrics trends over time.", icon=":material/info:")
            
            with st.container(border=True):
                st.markdown("**What metrics will be shown:**")
                st.markdown("""
                - **Groundedness**: Is the response supported by the retrieved context?
                - **Context Relevance**: Is the retrieved patient data relevant to the query?
                - **Answer Relevance**: Does the response properly address the analysis task?
                - **False Positive Rate**: Percentage of incorrect indicator detections
                """)
    
    st.subheader("Run evaluation")
    
    with st.container(border=True):
        col_run, col_status = st.columns([2, 1])
        
        with col_run:
            sample_size = st.selectbox("Sample size", [5, 10, 25, 50], index=1, help="Number of residents to evaluate")
            
            if st.button("Run Quality Evaluation", type="primary", icon=":material/play_arrow:"):
                with st.spinner("Starting evaluation job... This takes 2-5 minutes."):
                    try:
                        execute_query("DROP SERVICE IF EXISTS AGEDCARE.AGEDCARE.DRI_EVAL_RUN", session)
                        
                        result = execute_query(f"""
                            EXECUTE JOB SERVICE
                            IN COMPUTE POOL FULLSTACK_COMPUTE_POOL
                            FROM @AGEDCARE.AGEDCARE.DRI_EVAL_STAGE
                            SPEC = 'job-run-spec.yaml'
                            NAME = AGEDCARE.AGEDCARE.DRI_EVAL_RUN
                            QUERY_WAREHOUSE = COMPUTE_WH
                        """, session)
                        
                        if result:
                            status = str(result[0]['STATUS']) if 'STATUS' in result[0] else str(result[0])
                            if 'successfully' in status.lower() or 'done' in status.lower():
                                st.success("Evaluation completed! Refreshing...", icon=":material/check_circle:")
                                st.rerun()
                            else:
                                st.info(f"Job status: {status}", icon=":material/info:")
                                st.rerun()
                        else:
                            st.success("Evaluation job submitted. Refreshing...", icon=":material/check_circle:")
                            st.rerun()
                    except Exception as e:
                        error_msg = str(e).lower()
                        if 'completed' in error_msg or 'done' in error_msg:
                            st.success("Evaluation completed! Refreshing...", icon=":material/check_circle:")
                            st.rerun()
                        else:
                            st.error(f"Failed to run evaluation: {e}", icon=":material/error:")
        
        with col_status:
            st.caption("Evaluates residents using LLM-as-judge to compute groundedness and relevance scores.")
        
        with st.expander("Manual SQL command", icon=":material/code:"):
            st.code("""EXECUTE JOB SERVICE
IN COMPUTE POOL FULLSTACK_COMPUTE_POOL
FROM @AGEDCARE.AGEDCARE.DRI_EVAL_STAGE
SPEC = 'job-run-spec.yaml'
NAME = AGEDCARE.AGEDCARE.DRI_EVAL_RUN
QUERY_WAREHOUSE = COMPUTE_WH;""", language="sql")
    
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
            avg_latency = row['AVG_LATENCY_MS'] or 0
            records = row['RECORDS_EVALUATED'] or 0
            
            if groundedness > 0 or fp_rate > 0:
                expander_title = f"{row['RUN_NAME']} - FP: {fp_rate}% | Groundedness: {groundedness}%"
            else:
                expander_title = f"{row['RUN_NAME']} - {records} records | {int(avg_latency)}ms avg latency"
            
            with st.expander(expander_title, icon=status_icon):
                col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                
                with col_d1:
                    st.markdown(f"**Prompt:** {row['PROMPT_VERSION']}")
                    st.markdown(f"**Model:** {row['MODEL_USED']}")
                
                with col_d2:
                    st.markdown(f"**Records:** {records}")
                    st.markdown(f"**Status:** {row['STATUS']}")
                
                with col_d3:
                    if groundedness > 0 or fp_rate > 0:
                        st.metric("FP Rate", f"{fp_rate}%")
                    else:
                        st.metric("Avg Latency", f"{int(avg_latency)}ms")
                
                with col_d4:
                    if groundedness > 0:
                        st.metric("Groundedness", f"{groundedness}%")
                    else:
                        st.metric("Timestamp", row['CREATED_TIMESTAMP'].strftime('%Y-%m-%d %H:%M') if row['CREATED_TIMESTAMP'] else '-')
                
                details = execute_query_df(f"""
                    SELECT 
                        RESIDENT_ID,
                        INDICATORS_DETECTED,
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
    
    st.subheader("Snowsight integration")
    
    with st.container(border=True):
        st.markdown("""
        **View detailed traces and evaluations in Snowsight:**
        
        Navigate to **AI & ML → Evaluations** to see:
        - Individual trace analysis with inputs/outputs
        - LLM judge explanations for each score
        - Side-by-side comparison of evaluation runs
        - Cost and latency breakdowns
        """)
        
        st.link_button(
            "Open Snowsight Evaluations",
            "https://app.snowflake.com/sfseapac/demo_sweingartner/#/ai-ml/evaluations",
            icon=":material/open_in_new:"
        )

else:
    st.error("Failed to connect to Snowflake", icon=":material/error:")
