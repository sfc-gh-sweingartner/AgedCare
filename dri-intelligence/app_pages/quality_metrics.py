"""
Quality Metrics Page - AI Observability Dashboard
=================================================
This page displays quality metrics from Snowflake AI Observability,
including groundedness scores, false positive rates, and evaluation history.

Evaluations are run via a separate SPCS Job container that has TruLens installed.
Results are stored in Snowflake and viewable in Snowsight AI & ML → Evaluations.
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

### Setup
If the evaluation job is not yet deployed, see the setup instructions below.
    """)

session = get_snowflake_session()

if session:
    job_exists = False
    try:
        job_check = execute_query("""
            SELECT COUNT(*) as CNT FROM INFORMATION_SCHEMA.SERVICES 
            WHERE SERVICE_NAME = 'DRI_EVALUATION_JOB'
        """, session)
        job_exists = job_check and job_check[0]['CNT'] > 0
    except:
        pass
    
    if not job_exists:
        st.warning("Evaluation job not deployed. See setup instructions below.", icon=":material/warning:")
        
        with st.expander("SPCS Job setup instructions", expanded=True, icon=":material/build:"):
            st.markdown("""
### Deploy the Evaluation Job

The evaluation job requires a one-time setup. Run these commands:

**1. Build and push the container image:**
```bash
cd dri-intelligence/evaluation_job
docker build --platform linux/amd64 -t dri-evaluation:latest .
docker tag dri-evaluation:latest <registry>/AGEDCARE/AGEDCARE/DRI_IMAGES/dri-evaluation:latest
docker push <registry>/AGEDCARE/AGEDCARE/DRI_IMAGES/dri-evaluation:latest
```

**2. Create the job service in Snowflake:**
```sql
-- Run the setup script
@dri-intelligence/evaluation_job/setup_evaluation_job.sql
```

**3. Verify deployment:**
```sql
SHOW SERVICES LIKE 'DRI_EVALUATION%';
```

For detailed instructions, see `dri-intelligence/evaluation_job/README.md`
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
        if not job_exists:
            st.warning("Deploy the evaluation job first (see instructions above)", icon=":material/warning:")
            st.button("Run evaluation", type="primary", icon=":material/play_arrow:", disabled=True)
        else:
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
                sample_sizes = [10, 25, 50, 100]
                eval_sample_size = st.selectbox("Sample size", sample_sizes, index=0)
            
            eval_name = st.text_input(
                "Evaluation name",
                value=f"Eval_{eval_prompt_version}_{datetime.now().strftime('%Y%m%d_%H%M')}",
                help="A descriptive name for this evaluation run"
            )
            
            run_eval = st.button("Run evaluation", type="primary", icon=":material/play_arrow:")
            
            if run_eval:
                with st.spinner("Starting evaluation job..."):
                    try:
                        execute_query(f"""
                            EXECUTE JOB SERVICE AGEDCARE.AGEDCARE.DRI_EVALUATION_JOB
                            WITH PARAMETERS (
                                RUN_NAME => '{eval_name}',
                                PROMPT_VERSION => '{eval_prompt_version}',
                                MODEL => '{eval_model}',
                                SAMPLE_SIZE => {eval_sample_size}
                            )
                        """, session)
                        
                        st.success("Evaluation job started! Results will appear when complete.", icon=":material/check_circle:")
                        st.info("View progress in Snowsight: AI & ML → Evaluations", icon=":material/info:")
                        
                    except Exception as e:
                        st.error(f"Failed to start evaluation job: {e}", icon=":material/error:")
    
    st.subheader("Evaluation history")
    
    if tables_exist:
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
