"""DRI Intelligence - Batch Testing / AI Observability

Two modes of operation:

1. QUALITY EVALUATION (AI Observability):
   - Triggers SPCS evaluation job container with TruLens
   - Results appear in Snowsight > AI & ML > Evaluations
   - User specifies run name and sample size
   - Uses EXECUTE JOB SERVICE to run evaluation_job container

2. BATCH TEST (Review Workflow):
   - Runs DRI analysis directly via Cortex Complete
   - Stores results in DRI_LLM_ANALYSIS for review
   - Creates entries in DRI_REVIEW_QUEUE for approval
   - Does NOT integrate with Snowsight Evaluations

See evaluation_job/README.md for SPCS container setup.
"""

import streamlit as st
import json
import time
from datetime import datetime, timedelta

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

session = get_snowflake_session()

if session:
    tab1, tab2 = st.tabs(["🔬 Quality Evaluation (AI Observability)", "📋 Batch Test (Review Workflow)"])
    
    with tab1:
        st.markdown("""
        ### Run Quality Evaluation
        
        This triggers the **SPCS TruLens evaluation job** which:
        - Evaluates DRI analysis using AI Observability metrics
        - Records traces with groundedness, context relevance, answer relevance
        - Results appear in **Snowsight > AI & ML > Evaluations > DRI_INTELLIGENCE_AGENT**
        """)
        
        with st.expander("Understanding Evaluation Metrics", expanded=False, icon=":material/help:"):
            st.markdown("""
### LLM-as-Judge Evaluation Metrics

These metrics are computed using **LLM-as-Judge** methodology - a separate LLM evaluates the quality of the AI responses. 
This is NOT a factual accuracy check against ground truth data.

| Metric | What It Measures | How It's Calculated | Target |
|--------|------------------|---------------------|--------|
| **Answer Relevance** | Is the response relevant to the question asked? | LLM judges if the response addresses the original query appropriately | >85% |
| **Coherence** | Is the response logically consistent and well-structured? | LLM evaluates internal logical consistency of the response | >85% |
| **Context Relevance** | Is the retrieved RAG context relevant to the query? | LLM judges if the retrieved documents/data are useful for answering | >85% |
| **Groundedness** | Is the response supported by the retrieved context? | LLM checks if claims in the response are backed by the provided context | >90% |

### Important Notes

- **High scores ≠ Factual correctness**: A response can score 100% and still be factually wrong if the retrieved context itself contains errors
- **Groundedness**: Measures whether the AI "stayed in bounds" - didn't hallucinate beyond what the data shows
- **These are quality signals, not accuracy guarantees**: Use alongside human review for critical decisions
- **View detailed traces**: Go to **Snowsight > AI & ML > Evaluations** to see per-record LLM judge explanations
            """)
        
        st.info("💡 The evaluation job runs in a separate container. Make sure the Docker image has been deployed (see evaluation_job/README.md)")
        
        col_eval1, col_eval2 = st.columns(2)
        
        with col_eval1:
            default_run_name = f"Eval_{datetime.now().strftime('%Y%m%d_%H%M')}"
            run_name = st.text_input(
                "Evaluation Run Name",
                value=default_run_name,
                help="This name will appear in Snowsight Evaluations"
            )
            
            sample_size = st.selectbox(
                "Sample Size",
                [5, 10, 20, 50, 100],
                index=1,
                help="Number of residents to evaluate"
            )
        
        with col_eval2:
            prompt_versions = execute_query_df("""
                SELECT VERSION_NUMBER, DESCRIPTION, IS_ACTIVE
                FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS
                ORDER BY CREATED_TIMESTAMP DESC
            """, session)
            
            if prompt_versions is not None and len(prompt_versions) > 0:
                version_options = prompt_versions['VERSION_NUMBER'].tolist()
                active_idx = 0
                for i, row in prompt_versions.iterrows():
                    if row['IS_ACTIVE']:
                        active_idx = i
                        break
                prompt_version = st.selectbox(
                    "Prompt Version",
                    version_options,
                    index=active_idx,
                    help="Prompt version to use for evaluation"
                )
            else:
                prompt_version = "v1.0"
                st.warning("No prompt versions found, using v1.0")
            
            model = st.selectbox(
                "Model",
                ["claude-sonnet-4-5", "claude-3-5-sonnet", "claude-opus-4-5", "mistral-large2"],
                index=0,
                help="LLM model for analysis"
            )
        
        st.markdown("---")
        
        existing_runs = execute_query_df("""
            SELECT 
                RECORD_ATTRIBUTES:"snow.ai.observability.run.name"::VARCHAR as RUN_NAME,
                MIN(TIMESTAMP) as STARTED,
                COUNT(*) as RECORD_COUNT
            FROM SNOWFLAKE.LOCAL.AI_OBSERVABILITY_EVENTS
            WHERE RECORD_TYPE = 'SPAN'
              AND RECORD_ATTRIBUTES:"snow.ai.observability.object.name"::VARCHAR = 'DRI_INTELLIGENCE_AGENT'
            GROUP BY 1
            ORDER BY STARTED DESC
            LIMIT 10
        """, session)
        
        if existing_runs is not None and len(existing_runs) > 0:
            with st.expander("📊 Recent Evaluation Runs", expanded=False):
                st.dataframe(existing_runs, use_container_width=True)
                st.caption("View full results in Snowsight > AI & ML > Evaluations")
        
        run_col1, run_col2 = st.columns([1, 2])
        
        with run_col1:
            run_evaluation = st.button(
                "🚀 Run Quality Evaluation",
                type="primary",
                use_container_width=True,
                help="Triggers SPCS job with TruLens for AI Observability"
            )
        
        with run_col2:
            check_status = st.button(
                "🔄 Check Job Status",
                use_container_width=True,
                help="Check status of running evaluation job"
            )
        
        if run_evaluation:
            st.markdown("### Starting Evaluation Job...")
            
            job_name = f"DRI_EVAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            try:
                insert_run = execute_query(f"""
                    INSERT INTO AGEDCARE.AGEDCARE.DRI_EVAL_RUNS 
                    (RUN_NAME, PROMPT_VERSION, MODEL, SAMPLE_SIZE, STATUS, JOB_NAME)
                    VALUES ('{run_name}', '{prompt_version}', '{model}', {sample_size}, 'PENDING', '{job_name}')
                """, session)
                st.success(f"✅ Evaluation run queued: **{run_name}**")
                
                drop_result = execute_query(f"""
                    DROP SERVICE IF EXISTS AGEDCARE.AGEDCARE.{job_name}
                """, session)
                
                with st.spinner("Executing SPCS evaluation job..."):
                    job_spec_update = f"""
                    EXECUTE JOB SERVICE
                    IN COMPUTE POOL FULLSTACK_COMPUTE_POOL
                    FROM @AGEDCARE.AGEDCARE.DRI_EVAL_STAGE
                    SPEC = 'job-run-spec.yaml'
                    NAME = AGEDCARE.AGEDCARE.{job_name}
                    QUERY_WAREHOUSE = COMPUTE_WH
                    EXTERNAL_ACCESS_INTEGRATIONS = (PYPI_ACCESS_INTEGRATION)
                    """
                    
                    st.info(f"""
**Evaluation Configuration:**
- Run Name: `{run_name}`
- Prompt Version: `{prompt_version}`
- Model: `{model}`
- Sample Size: `{sample_size}`

The job will read this config from `DRI_EVAL_RUNS` table.
                    """)
                    
                    result = execute_query(job_spec_update, session)
                    
                    if result:
                        status = str(result[0]) if result[0] else 'Unknown'
                        
                        if 'DONE' in status.upper() or 'completed' in status.lower():
                            st.success(f"""
                            ✅ **Evaluation job completed!**
                            
                            - Job Name: `{job_name}`
                            - Status: {status}
                            
                            **View results in Snowsight:**
                            1. Go to **AI & ML > Evaluations**
                            2. Click on **DRI_INTELLIGENCE_AGENT**
                            3. Find run: **{run_name}**
                            """)
                            
                            st.markdown("#### Job Logs")
                            try:
                                logs = execute_query(f"""
                                    SELECT SYSTEM$GET_SERVICE_LOGS('AGEDCARE.AGEDCARE.{job_name}', 0, 'dri-evaluation', 100)
                                """, session)
                                if logs:
                                    log_val = list(logs[0].values())[0] if hasattr(logs[0], 'values') else str(logs[0])
                                    st.code(log_val, language="text")
                            except Exception as log_err:
                                st.warning(f"Could not retrieve logs: {log_err}")
                        else:
                            st.info(f"Job status: {status}")
                    else:
                        st.warning("Job started but no result returned. Check status below.")
                        
            except Exception as e:
                error_msg = str(e)
                st.error(f"Failed to execute job: {error_msg}")
                
                if "compute pool" in error_msg.lower():
                    st.warning("Make sure FULLSTACK_COMPUTE_POOL is active and you have permissions.")
                elif "image" in error_msg.lower() or "not found" in error_msg.lower():
                    st.warning("""
                    The evaluation job image may not be deployed. Run these commands:
                    ```bash
                    cd dri-intelligence/evaluation_job
                    snow spcs image-registry login --connection DEMO_SWEINGARTNER
                    docker buildx build --platform linux/amd64 -t dri-evaluation:latest --load .
                    docker tag dri-evaluation:latest <registry>/agedcare/agedcare/dri_images/dri-evaluation:latest
                    docker push <registry>/agedcare/agedcare/dri_images/dri-evaluation:latest
                    ```
                    """)
        
        if check_status:
            st.markdown("### Recent Job Status")
            
            try:
                services = execute_query("""
                    SHOW SERVICES LIKE 'DRI_EVAL%' IN SCHEMA AGEDCARE.AGEDCARE
                """, session)
                
                if services:
                    for svc in services[-3:]:
                        svc_name = svc.get('name', 'Unknown')
                        st.markdown(f"**{svc_name}**")
                        
                        try:
                            status = execute_query(f"""
                                SELECT SYSTEM$GET_SERVICE_STATUS('AGEDCARE.AGEDCARE.{svc_name}')
                            """, session)
                            if status:
                                st.json(status[0])
                        except:
                            st.caption("Status unavailable")
                else:
                    st.info("No evaluation jobs found. Run a new evaluation to create one.")
                    
            except Exception as e:
                st.error(f"Could not check status: {e}")
        
        st.markdown("---")
        
        st.subheader("Quality Metrics Trend")
        
        metrics_trend = execute_query_df("""
            WITH eval_metrics AS (
                SELECT 
                    RECORD_ATTRIBUTES:"snow.ai.observability.run.name"::VARCHAR as RUN_NAME,
                    TIMESTAMP,
                    RECORD_ATTRIBUTES:"ai.observability.eval.metric_name"::VARCHAR as METRIC_NAME,
                    RECORD_ATTRIBUTES:"ai.observability.eval_root.score"::FLOAT as SCORE
                FROM SNOWFLAKE.LOCAL.AI_OBSERVABILITY_EVENTS
                WHERE RECORD_TYPE = 'SPAN'
                  AND RECORD_ATTRIBUTES:"snow.ai.observability.object.name"::VARCHAR = 'DRI_INTELLIGENCE_AGENT'
                  AND RECORD_ATTRIBUTES:"ai.observability.eval.metric_name" IS NOT NULL
                  AND RECORD_ATTRIBUTES:"ai.observability.eval_root.score" IS NOT NULL
            )
            SELECT 
                RUN_NAME,
                MIN(TIMESTAMP) as CREATED_TIMESTAMP,
                ROUND(AVG(CASE WHEN METRIC_NAME = 'groundedness' THEN SCORE END) * 100, 1) as GROUNDEDNESS_PCT,
                ROUND(AVG(CASE WHEN METRIC_NAME = 'context_relevance' THEN SCORE END) * 100, 1) as CONTEXT_RELEVANCE_PCT,
                ROUND(AVG(CASE WHEN METRIC_NAME = 'answer_relevance' THEN SCORE END) * 100, 1) as ANSWER_RELEVANCE_PCT,
                ROUND(AVG(CASE WHEN METRIC_NAME = 'coherence' THEN SCORE END) * 100, 1) as COHERENCE_PCT,
                COUNT(DISTINCT METRIC_NAME) as METRICS_COUNT
            FROM eval_metrics
            GROUP BY RUN_NAME
            HAVING GROUNDEDNESS_PCT IS NOT NULL
            ORDER BY CREATED_TIMESTAMP
        """, session)
        
        if metrics_trend is not None and len(metrics_trend) > 0:
            tab_all, tab_quality, tab_history = st.tabs(["All Metrics", "Quality Scores", "Evaluation History"])
            
            with tab_all:
                chart_data = metrics_trend[['CREATED_TIMESTAMP', 'GROUNDEDNESS_PCT', 'CONTEXT_RELEVANCE_PCT', 'ANSWER_RELEVANCE_PCT', 'COHERENCE_PCT']].copy()
                chart_data = chart_data.set_index('CREATED_TIMESTAMP')
                chart_data.columns = ['Groundedness %', 'Context Relevance %', 'Answer Relevance %', 'Coherence %']
                st.line_chart(chart_data, use_container_width=True)
                
                with st.container(border=True):
                    cols = st.columns(4)
                    latest = metrics_trend.iloc[-1]
                    with cols[0]:
                        g = latest['GROUNDEDNESS_PCT'] or 0
                        st.metric("Latest Groundedness", f"{g}%")
                    with cols[1]:
                        c = latest['CONTEXT_RELEVANCE_PCT'] or 0
                        st.metric("Latest Context Relevance", f"{c}%")
                    with cols[2]:
                        a = latest['ANSWER_RELEVANCE_PCT'] or 0
                        st.metric("Latest Answer Relevance", f"{a}%")
                    with cols[3]:
                        co = latest['COHERENCE_PCT'] or 0
                        st.metric("Latest Coherence", f"{co}%")
            
            with tab_quality:
                st.markdown("**Quality score targets:**")
                st.caption("Groundedness: >90% | Context Relevance: >85% | Answer Relevance: >85% | Coherence: >85%")
                
                for _, row in metrics_trend.iterrows():
                    with st.expander(f"{row['RUN_NAME']} - {row['CREATED_TIMESTAMP']}"):
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            g = row['GROUNDEDNESS_PCT'] or 0
                            delta = "Good" if g >= 90 else "Below target"
                            st.metric("Groundedness", f"{g}%", delta=delta)
                        with col2:
                            c = row['CONTEXT_RELEVANCE_PCT'] or 0
                            delta = "Good" if c >= 85 else "Below target"
                            st.metric("Context Rel.", f"{c}%", delta=delta)
                        with col3:
                            a = row['ANSWER_RELEVANCE_PCT'] or 0
                            delta = "Good" if a >= 85 else "Below target"
                            st.metric("Answer Rel.", f"{a}%", delta=delta)
                        with col4:
                            co = row['COHERENCE_PCT'] or 0
                            delta = "Good" if co >= 85 else "Below target"
                            st.metric("Coherence", f"{co}%", delta=delta)
            
            with tab_history:
                st.dataframe(
                    metrics_trend[['RUN_NAME', 'CREATED_TIMESTAMP', 'GROUNDEDNESS_PCT', 'CONTEXT_RELEVANCE_PCT', 'ANSWER_RELEVANCE_PCT', 'COHERENCE_PCT', 'METRICS_COUNT']].rename(
                        columns={
                            'RUN_NAME': 'Run Name',
                            'CREATED_TIMESTAMP': 'Timestamp',
                            'GROUNDEDNESS_PCT': 'Groundedness %',
                            'CONTEXT_RELEVANCE_PCT': 'Context Rel %',
                            'ANSWER_RELEVANCE_PCT': 'Answer Rel %',
                            'COHERENCE_PCT': 'Coherence %',
                            'METRICS_COUNT': 'Metrics'
                        }
                    ),
                    use_container_width=True
                )
        else:
            st.info("Run evaluations to see quality metrics trends over time.", icon=":material/info:")
            
            with st.container(border=True):
                st.markdown("**What metrics will be shown:**")
                st.markdown("""
                - **Groundedness**: Is the response supported by the retrieved context?
                - **Context Relevance**: Is the retrieved patient data relevant to the query?
                - **Answer Relevance**: Does the response properly address the analysis task?
                - **Coherence**: Is the response logically consistent?
                """)
        
        st.markdown("---")
        
        st.subheader("View in Snowsight")
        
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
        
        st.markdown("---")
        
        with st.expander("How It Works", expanded=False, icon=":material/architecture:"):
            st.markdown("""
            ### Evaluation Architecture
            
            1. **EXECUTE JOB SERVICE** runs the TruLens evaluation container
            2. The container connects to Snowflake and registers with AI Observability
            3. Each resident analysis is traced with:
               - **RETRIEVAL** spans (context gathering)
               - **GENERATION** spans (LLM inference)
               - **RECORD_ROOT** spans (full request/response)
            4. Evaluation metrics (groundedness, relevance) are computed via `run.compute_metrics()`
            5. Results appear in **Snowsight > AI & ML > Evaluations**
            
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
            """)
    
    with tab2:
        st.markdown("""
        ### Batch Test for Review Workflow
        
        This runs DRI analysis directly and stores results for the **approval workflow**:
        - Results stored in `DRI_LLM_ANALYSIS`
        - Creates `DRI_REVIEW_QUEUE` entries for human review
        - Does NOT appear in Snowsight Evaluations (use Quality Evaluation tab for that)
        """)
        
        clients = execute_query_df("""
            SELECT CONFIG_ID, CLIENT_SYSTEM_KEY, CLIENT_NAME, IS_ACTIVE
            FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG
            ORDER BY CLIENT_NAME
        """, session)
        
        if clients is not None and len(clients) > 0:
            client_options = {f"{row['CLIENT_NAME']} ({row['CLIENT_SYSTEM_KEY']})": row['CONFIG_ID'] for _, row in clients.iterrows()}
            client_keys = {row['CONFIG_ID']: row['CLIENT_SYSTEM_KEY'] for _, row in clients.iterrows()}
            
            st.markdown("### 🏢 Select Client")
            selected_client_display = st.selectbox(
                "Client",
                list(client_options.keys()),
                help="Batch test will use this client's production configuration",
                key="batch_client"
            )
            selected_config_id = client_options[selected_client_display]
            selected_client_key = client_keys[selected_config_id]
        else:
            st.error("No clients found in configuration table")
            st.stop()

        prod_config = execute_query(f"""
            SELECT 
                CONFIG_JSON:production_settings:model::VARCHAR as PROD_MODEL,
                CONFIG_JSON:production_settings:prompt_text::VARCHAR as PROD_PROMPT_TEXT,
                CONFIG_JSON:production_settings:prompt_version::VARCHAR as PROD_PROMPT_VERSION,
                CONFIG_JSON:client_settings:context_threshold::NUMBER as CONTEXT_THRESHOLD
            FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG 
            WHERE CONFIG_ID = '{selected_config_id}'
        """, session)
        
        prod_model = prod_config[0]['PROD_MODEL'] if prod_config and prod_config[0]['PROD_MODEL'] else 'claude-3-5-sonnet'
        prod_prompt_text = prod_config[0]['PROD_PROMPT_TEXT'] if prod_config and prod_config[0]['PROD_PROMPT_TEXT'] else None
        prod_prompt_version = prod_config[0]['PROD_PROMPT_VERSION'] if prod_config and prod_config[0]['PROD_PROMPT_VERSION'] else 'v1.0'
        context_threshold = prod_config[0]['CONTEXT_THRESHOLD'] if prod_config and prod_config[0]['CONTEXT_THRESHOLD'] else 6000
        
        if not prod_prompt_text:
            fallback_prompt = execute_query(f"""
                SELECT PROMPT_TEXT FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS 
                WHERE VERSION_NUMBER = '{prod_prompt_version}'
            """, session)
            if fallback_prompt:
                prod_prompt_text = fallback_prompt[0]['PROMPT_TEXT']
                st.info("Using prompt from DRI_PROMPT_VERSIONS (not yet saved to client config)")
        
        st.markdown("### Current Production Configuration")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Model", prod_model)
        with col2:
            st.metric("Prompt Version", prod_prompt_version)
        with col3:
            has_prompt = "✅ Set" if prod_prompt_text else "⚠️ Not Set"
            st.metric("Prompt", has_prompt)
        
        if not prod_prompt_text:
            st.error("No production prompt configured. Go to Configuration → Processing Settings.")
            st.stop()
        
        st.markdown("---")
        
        residents = execute_query_df("""
            SELECT DISTINCT RESIDENT_ID 
            FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES
            ORDER BY RESIDENT_ID
        """, session)
        
        if residents is not None and len(residents) > 0:
            resident_list = residents['RESIDENT_ID'].tolist()
            batch_sample_size = st.slider(
                "Number of residents to process",
                min_value=1,
                max_value=min(len(resident_list), 50),
                value=min(5, len(resident_list)),
                help="Select how many residents to include in this batch"
            )
            
            residents_to_process = resident_list[:batch_sample_size]
            
            st.metric("Residents Selected", batch_sample_size)
            
            with st.expander("View selected residents"):
                st.write(residents_to_process)
        else:
            st.error("No residents found")
            st.stop()
        
        st.markdown("---")
        
        run_batch = st.button(
            "🚀 Run Batch Test",
            type="primary",
            help="Run analysis and store in DRI_LLM_ANALYSIS for review workflow"
        )
        
        if run_batch:
            import uuid
            
            batch_id = str(uuid.uuid4())
            total_residents = len(residents_to_process)
            
            st.markdown(f"### Batch Run: `{batch_id[:8]}...`")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            successful = 0
            failed = 0
            results = []
            
            escaped_prompt_for_sql = prod_prompt_text.replace("'", "''")
            
            for idx, resident_id in enumerate(residents_to_process):
                status_text.markdown(f"Processing resident **{resident_id}** ({idx + 1}/{total_residents})...")
                progress_bar.progress((idx + 1) / total_residents)
                
                try:
                    start_time = time.time()
                    
                    analysis_query = f"""
                    WITH resident_notes AS (
                        SELECT LISTAGG(LEFT(PROGRESS_NOTE, 400) || ' [' || NOTE_TYPE || ']', ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as notes_text
                        FROM (SELECT PROGRESS_NOTE, NOTE_TYPE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 15)
                    ),
                    resident_meds AS (
                        SELECT LISTAGG(MED_NAME || ' (' || MED_STATUS || ')', ', ') as meds_text
                        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION WHERE RESIDENT_ID = {resident_id}
                    ),
                    resident_obs AS (
                        SELECT LISTAGG(CHART_NAME || ': ' || LEFT(OBSERVATION_VALUE, 100), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as obs_text
                        FROM (SELECT CHART_NAME, OBSERVATION_VALUE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 30)
                    ),
                    rag_indicators AS (
                        SELECT LISTAGG(INDICATOR_ID || ' - ' || INDICATOR_NAME || ': ' || DEFINITION, ' || ') WITHIN GROUP (ORDER BY INDICATOR_ID) as indicators_text
                        FROM AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS
                    ),
                    full_context AS (
                        SELECT 
                            'PROGRESS NOTES: ' || (SELECT notes_text FROM resident_notes) ||
                            ' MEDICATIONS: ' || (SELECT meds_text FROM resident_meds) ||
                            ' OBSERVATIONS: ' || (SELECT obs_text FROM resident_obs) ||
                            ' DRI INDICATORS: ' || (SELECT indicators_text FROM rag_indicators) as context
                    )
                    SELECT 
                        SNOWFLAKE.CORTEX.COMPLETE(
                            '{prod_model}',
                            [
                                {{
                                    'role': 'user',
                                    'content': REPLACE(REPLACE(
                                        '{escaped_prompt_for_sql}',
                                        '{{resident_context}}', (SELECT context FROM full_context)
                                    ), '{{rag_indicator_context}}', '')
                                }}
                            ],
                            {{
                                'max_tokens': 4096
                            }}
                        ) as RESPONSE
                    """
                    
                    result = execute_query(analysis_query, session)
                    processing_time = int((time.time() - start_time) * 1000)
                    
                    if result:
                        raw_response = result[0]['RESPONSE']
                        
                        try:
                            response_obj = json.loads(raw_response)
                            response_text = response_obj.get('choices', [{}])[0].get('messages', raw_response)
                        except:
                            response_text = raw_response
                        
                        insert_query = f"""
                            INSERT INTO AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS 
                            (RESIDENT_ID, CLIENT_SYSTEM_KEY, MODEL_USED, PROMPT_VERSION, 
                             RAW_RESPONSE, PROCESSING_TIME_MS, BATCH_RUN_ID)
                            VALUES (
                                {resident_id},
                                '{selected_client_key}',
                                '{prod_model}',
                                '{prod_prompt_version}',
                                PARSE_JSON($${json.dumps({"response": response_text})}$$),
                                {processing_time},
                                '{batch_id}'
                            )
                        """
                        execute_query(insert_query, session)
                        
                        results.append({
                            "resident_id": resident_id,
                            "status": "Success",
                            "processing_time_ms": processing_time
                        })
                        successful += 1
                    else:
                        results.append({
                            "resident_id": resident_id,
                            "status": "Failed",
                            "processing_time_ms": 0
                        })
                        failed += 1
                        
                except Exception as e:
                    results.append({
                        "resident_id": resident_id,
                        "status": f"Error: {str(e)[:50]}",
                        "processing_time_ms": 0
                    })
                    failed += 1
            
            progress_bar.progress(1.0)
            status_text.markdown("**Batch processing complete!**")
            
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.metric("Successful", successful)
            with col_r2:
                st.metric("Failed", failed)
            
            import pandas as pd
            st.dataframe(pd.DataFrame(results), use_container_width=True)
            
            st.success(f"""
            Batch test complete! Batch ID: `{batch_id}`
            
            **Next steps:**
            1. Review results in **Analysis Results** page
            2. Approve/reject in **Review Queue** page
            
            ⚠️ This does NOT appear in Snowsight Evaluations.
            Use the **Quality Evaluation** tab for AI Observability integration.
            """)

else:
    st.error("Failed to connect to Snowflake")
