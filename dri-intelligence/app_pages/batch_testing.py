"""DRI Intelligence - Batch Testing & Approval-Based Quality Metrics

v1.7 Simplified Architecture:
- Removed TruLens/AI Observability integration
- Quality metrics derived from approval workflow (DRI_REVIEW_QUEUE)
- Ground truth auto-harvested from approved/rejected decisions
- SQL views provide real-time quality scoring

Two main sections:
1. BATCH TEST: Run DRI analysis on multiple residents, store for review
2. QUALITY METRICS: Show approval rates by prompt version as the key quality signal
"""

import streamlit as st
import json
import time
import uuid
from datetime import datetime

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

session = get_snowflake_session()

if session:
    st.title("Batch Testing & Quality Metrics")
    
    tab1, tab2, tab3 = st.tabs([
        "📋 Batch Test", 
        "📊 Prompt Quality", 
        "🎯 Ground Truth"
    ])
    
    with tab1:
        st.markdown("""
        ### Batch Test for Review Workflow
        
        Run DRI analysis on selected residents and store results for the **approval workflow**:
        - Results stored in `DRI_LLM_ANALYSIS`
        - Creates `DRI_REVIEW_QUEUE` entries for human review
        - Approval/rejection decisions become your **quality signal**
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
                                'max_tokens': 8192
                            }}
                        ) as RESPONSE
                    """
                    
                    result = execute_query(analysis_query, session)
                    processing_time = int((time.time() - start_time) * 1000)
                    
                    if result:
                        raw_response = result[0]['RESPONSE']
                        
                        if isinstance(raw_response, dict):
                            response_text = raw_response.get('choices', [{}])[0].get('messages', '')
                        elif isinstance(raw_response, str):
                            try:
                                response_obj = json.loads(raw_response)
                                response_text = response_obj.get('choices', [{}])[0].get('messages', raw_response)
                            except:
                                response_text = raw_response
                        else:
                            response_text = str(raw_response)
                        
                        if not isinstance(response_text, str):
                            response_text = json.dumps(response_text) if response_text else ''
                        
                        cleaned = response_text.strip()
                        if cleaned.startswith('```json'):
                            cleaned = cleaned[7:]
                        elif cleaned.startswith('```'):
                            cleaned = cleaned[3:]
                        if cleaned.endswith('```'):
                            cleaned = cleaned[:-3]
                        cleaned = cleaned.strip()
                        
                        json_start = cleaned.find('{')
                        json_end = cleaned.rfind('}') + 1
                        if json_start >= 0 and json_end > json_start:
                            json_str = cleaned[json_start:json_end]
                        else:
                            json_str = cleaned
                        
                        def try_parse_json(s):
                            try:
                                return json.loads(s), None
                            except json.JSONDecodeError as e:
                                return None, str(e)
                        
                        def repair_truncated_json(s):
                            open_braces = s.count('{') - s.count('}')
                            open_brackets = s.count('[') - s.count(']')
                            
                            if open_braces > 0 or open_brackets > 0:
                                last_complete = max(s.rfind('},'), s.rfind('}]'), s.rfind('"'))
                                if last_complete > len(s) // 2:
                                    s = s[:last_complete+1]
                                    s += ']' * open_brackets + '}' * open_braces
                            return s
                        
                        parsed_json, parse_error = try_parse_json(json_str)
                        
                        if parsed_json is None:
                            repaired = repair_truncated_json(json_str)
                            parsed_json, parse_error = try_parse_json(repaired)
                            if parsed_json:
                                json_str = repaired
                        
                        if parsed_json:
                            
                            indicators = parsed_json.get('indicators', [])
                            summary = parsed_json.get('summary', {})
                            
                            indicators_detected = len([i for i in indicators if i.get('detected', True)])
                            indicators_cleared = summary.get('indicators_cleared', 0) or 0
                            
                            proposed_score = round(indicators_detected / 33, 4)
                            if proposed_score <= 0.2:
                                severity = 'Low'
                            elif proposed_score <= 0.4:
                                severity = 'Medium'
                            elif proposed_score <= 0.6:
                                severity = 'High'
                            else:
                                severity = 'Very High'
                            
                            indicator_changes = json.dumps(indicators)
                            change_summary = summary.get('analysis_notes', f'Detected {indicators_detected} indicators')[:500]
                            
                            session.sql("""
                                INSERT INTO AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS 
                                (RESIDENT_ID, CLIENT_SYSTEM_KEY, MODEL_USED, PROMPT_VERSION, 
                                 RAW_RESPONSE, PROCESSING_TIME_MS, BATCH_RUN_ID)
                                SELECT ?, ?, ?, ?, PARSE_JSON(?), ?, ?
                            """, params=[resident_id, selected_client_key, prod_model, prod_prompt_version, 
                                        json_str, processing_time, batch_id]).collect()
                            
                            analysis_id_result = execute_query(f"""
                                SELECT ANALYSIS_ID FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS 
                                WHERE RESIDENT_ID = {resident_id} AND BATCH_RUN_ID = '{batch_id}'
                                ORDER BY ANALYSIS_TIMESTAMP DESC LIMIT 1
                            """, session)
                            
                            if analysis_id_result:
                                analysis_id = analysis_id_result[0]['ANALYSIS_ID']
                                
                                session.sql("""
                                    INSERT INTO AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE 
                                    (ANALYSIS_ID, RESIDENT_ID, CLIENT_SYSTEM_KEY, 
                                     CURRENT_DRI_SCORE, PROPOSED_DRI_SCORE,
                                     CURRENT_SEVERITY_BAND, PROPOSED_SEVERITY_BAND,
                                     INDICATORS_ADDED, INDICATORS_REMOVED,
                                     INDICATOR_CHANGES_JSON, CHANGE_SUMMARY, STATUS)
                                    SELECT ?, ?, ?, 0.0, ?, 'Unknown', ?, ?, ?, PARSE_JSON(?), ?, 'PENDING'
                                """, params=[analysis_id, resident_id, selected_client_key,
                                            proposed_score, severity, indicators_detected, indicators_cleared,
                                            indicator_changes, change_summary]).collect()
                            
                            results.append({
                                "resident_id": resident_id,
                                "status": "Success",
                                "indicators": indicators_detected,
                                "processing_time_ms": processing_time
                            })
                            successful += 1
                            
                        else:
                            session.sql("""
                                INSERT INTO AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS 
                                (RESIDENT_ID, CLIENT_SYSTEM_KEY, MODEL_USED, PROMPT_VERSION, 
                                 RAW_RESPONSE, PROCESSING_TIME_MS, BATCH_RUN_ID)
                                SELECT ?, ?, ?, ?, OBJECT_CONSTRUCT('parse_error', TRUE, 'error', ?, 'raw_text', LEFT(?, 3000)), ?, ?
                            """, params=[resident_id, selected_client_key, prod_model, prod_prompt_version,
                                        parse_error or 'Unknown error', json_str, processing_time, batch_id]).collect()
                            
                            results.append({
                                "resident_id": resident_id,
                                "status": f"Parse error: {(parse_error or 'Unknown')[:50]}",
                                "processing_time_ms": processing_time
                            })
                            failed += 1
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
            3. Check quality metrics in **Prompt Quality** tab
            """)
    
    with tab2:
        st.markdown("""
        ### Prompt Quality Score
        
        Quality is measured by the **approval rate** of DRI changes by prompt version.
        This is your **primary quality signal** - better prompts = higher approval rates.
        """)
        
        with st.expander("Understanding Approval-Based Quality Metrics", expanded=False, icon=":material/help:"):
            st.markdown("""
### Why Approval Rate is the Best Quality Metric

| Metric | What It Measures | Why It's Better |
|--------|------------------|-----------------|
| **Approval Rate** | % of DRI changes approved by reviewers | Measures **clinical accuracy**, not just LLM behavior |
| **Rejection Reasons** | Why reviewers reject changes | Provides **actionable feedback** for prompt improvement |
| **Ground Truth Coverage** | How many validated decisions we have | Builds a **test dataset** organically |

### How It Works

```
1. LLM analyzes resident → Proposes DRI changes
2. Reviewer approves or rejects → Captures clinical judgment
3. Approved = correct → Becomes positive ground truth
4. Rejected = incorrect → Becomes negative ground truth
5. Approval rate by prompt version → Your quality score
```

### Interpreting Results

- **>95% approval**: Excellent - prompt is production-ready
- **85-95% approval**: Good - minor refinement needed
- **<85% approval**: Review rejection reasons for improvements
            """)
        
        st.markdown("---")
        
        st.subheader("Analysis Overview")
        overview_data = execute_query_df("""
            SELECT 
                lla.PROMPT_VERSION,
                COUNT(*) as TOTAL_ANALYSES,
                COUNT(CASE WHEN rq.STATUS = 'PENDING' THEN 1 END) as PENDING_REVIEW,
                COUNT(CASE WHEN rq.STATUS = 'APPROVED' THEN 1 END) as APPROVED,
                COUNT(CASE WHEN rq.STATUS = 'REJECTED' THEN 1 END) as REJECTED,
                COUNT(DISTINCT lla.RESIDENT_ID) as RESIDENTS,
                ROUND(AVG(lla.PROCESSING_TIME_MS), 0) as AVG_PROCESSING_MS,
                MAX(lla.ANALYSIS_TIMESTAMP) as LAST_RUN
            FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS lla
            LEFT JOIN AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE rq 
                ON lla.ANALYSIS_ID = rq.ANALYSIS_ID
            GROUP BY lla.PROMPT_VERSION
            ORDER BY LAST_RUN DESC
        """, session)
        
        if overview_data is not None and len(overview_data) > 0:
            st.dataframe(overview_data, use_container_width=True)
        else:
            st.info("No analysis data yet. Run a batch test to get started.", icon=":material/info:")
        
        st.markdown("---")
        st.subheader("Approval Rate by Prompt Version")
        
        quality_data = execute_query_df("""
            SELECT 
                lla.PROMPT_VERSION,
                COUNT(*) as TOTAL_REVIEWS,
                COUNT(CASE WHEN rq.STATUS = 'APPROVED' THEN 1 END) as APPROVED_COUNT,
                COUNT(CASE WHEN rq.STATUS = 'REJECTED' THEN 1 END) as REJECTED_COUNT,
                ROUND(100.0 * COUNT(CASE WHEN rq.STATUS = 'APPROVED' THEN 1 END) / 
                      NULLIF(COUNT(*), 0), 1) as APPROVAL_RATE_PCT,
                MIN(lla.ANALYSIS_TIMESTAMP) as FIRST_USED,
                MAX(lla.ANALYSIS_TIMESTAMP) as LAST_USED,
                COUNT(DISTINCT lla.RESIDENT_ID) as RESIDENTS_ANALYZED
            FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS lla
            LEFT JOIN AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE rq 
                ON lla.ANALYSIS_ID = rq.ANALYSIS_ID
            WHERE rq.STATUS IN ('APPROVED', 'REJECTED')
            GROUP BY lla.PROMPT_VERSION
            ORDER BY APPROVAL_RATE_PCT DESC
        """, session)
        
        if quality_data is not None and len(quality_data) > 0:
            st.subheader("Prompt Version Comparison")
            
            best_version = quality_data.iloc[0]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Best Prompt", best_version['PROMPT_VERSION'])
            with col2:
                st.metric("Approval Rate", f"{best_version['APPROVAL_RATE_PCT']}%")
            with col3:
                st.metric("Total Reviews", int(best_version['TOTAL_REVIEWS']))
            
            st.markdown("#### Approval Rate by Prompt Version")
            
            chart_data = quality_data[['PROMPT_VERSION', 'APPROVAL_RATE_PCT', 'APPROVED_COUNT', 'REJECTED_COUNT']].copy()
            st.bar_chart(chart_data.set_index('PROMPT_VERSION')['APPROVAL_RATE_PCT'])
            
            st.markdown("#### Detailed Breakdown")
            st.dataframe(
                quality_data.rename(columns={
                    'PROMPT_VERSION': 'Prompt',
                    'TOTAL_REVIEWS': 'Reviews',
                    'APPROVED_COUNT': 'Approved',
                    'REJECTED_COUNT': 'Rejected',
                    'APPROVAL_RATE_PCT': 'Approval %',
                    'FIRST_USED': 'First Used',
                    'LAST_USED': 'Last Used',
                    'RESIDENTS_ANALYZED': 'Residents'
                }),
                use_container_width=True
            )
        else:
            st.info("No review data yet. Run batch tests and review results to generate quality metrics.", icon=":material/info:")
            
            with st.container(border=True):
                st.markdown("**How to get started:**")
                st.markdown("""
                1. Go to **Batch Test** tab and run analysis
                2. Review results in **Review Queue** page
                3. Approve or reject the DRI changes
                4. Return here to see quality metrics
                """)
        
        st.markdown("---")
        
        st.subheader("Quality Trend Over Time")
        
        trend_data = execute_query_df("""
            SELECT 
                DATE_TRUNC('day', rq.REVIEW_TIMESTAMP) AS REVIEW_DATE,
                lla.PROMPT_VERSION,
                COUNT(*) as TOTAL_REVIEWS,
                ROUND(100.0 * COUNT(CASE WHEN rq.STATUS = 'APPROVED' THEN 1 END) / 
                      NULLIF(COUNT(*), 0), 1) as APPROVAL_RATE_PCT
            FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE rq
            JOIN AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS lla ON rq.ANALYSIS_ID = lla.ANALYSIS_ID
            WHERE rq.STATUS IN ('APPROVED', 'REJECTED')
              AND rq.REVIEW_TIMESTAMP IS NOT NULL
            GROUP BY DATE_TRUNC('day', rq.REVIEW_TIMESTAMP), lla.PROMPT_VERSION
            ORDER BY REVIEW_DATE DESC
            LIMIT 30
        """, session)
        
        if trend_data is not None and len(trend_data) > 0:
            pivot_data = trend_data.pivot(index='REVIEW_DATE', columns='PROMPT_VERSION', values='APPROVAL_RATE_PCT')
            st.line_chart(pivot_data)
        else:
            st.caption("Trend data will appear after reviews are completed over multiple days.")
        
        st.markdown("---")
        
        st.subheader("Rejection Analysis")
        st.markdown("Common rejection reasons help identify prompt weaknesses.")
        
        rejections = execute_query_df("""
            SELECT 
                lla.PROMPT_VERSION,
                rq.REVIEWER_NOTES,
                COUNT(*) as REJECTION_COUNT
            FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE rq
            JOIN AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS lla ON rq.ANALYSIS_ID = lla.ANALYSIS_ID
            WHERE rq.STATUS = 'REJECTED'
              AND rq.REVIEWER_NOTES IS NOT NULL
              AND TRIM(rq.REVIEWER_NOTES) != ''
            GROUP BY lla.PROMPT_VERSION, rq.REVIEWER_NOTES
            ORDER BY REJECTION_COUNT DESC
            LIMIT 10
        """, session)
        
        if rejections is not None and len(rejections) > 0:
            st.dataframe(
                rejections.rename(columns={
                    'PROMPT_VERSION': 'Prompt',
                    'REVIEWER_NOTES': 'Rejection Reason',
                    'REJECTION_COUNT': 'Count'
                }),
                use_container_width=True
            )
        else:
            st.caption("No rejection reasons recorded yet. Reviewers can add notes when rejecting.")
    
    with tab3:
        st.markdown("""
        ### Ground Truth Management
        
        Ground truth is **automatically harvested** from the approval workflow:
        - **Approved** DRI changes → Positive examples (indicators should be detected)
        - **Rejected** DRI changes → Negative examples (false positives to avoid)
        
        This builds your test dataset organically without manual labeling.
        """)
        
        gt_count = execute_query("""
            SELECT COUNT(*) as COUNT FROM AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH WHERE IS_ACTIVE = TRUE
        """, session)
        
        total_gt = gt_count[0]['COUNT'] if gt_count else 0
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Ground Truth Records", total_gt)
        with col2:
            pending_reviews = execute_query("""
                SELECT COUNT(*) as COUNT FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE WHERE STATUS IN ('APPROVED', 'REJECTED')
            """, session)
            pending = pending_reviews[0]['COUNT'] if pending_reviews else 0
            st.metric("Completed Reviews", pending)
        
        st.markdown("---")
        
        st.subheader("Harvest Ground Truth")
        st.markdown("Click below to populate ground truth from approved/rejected reviews.")
        
        if st.button("🌾 Harvest Ground Truth from Approvals", type="primary"):
            try:
                result = execute_query("""
                    INSERT INTO AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH 
                    (RESIDENT_ID, INDICATOR_ID, EXPECTED_DETECTED, EVIDENCE_SUMMARY, VALIDATED_BY, SOURCE_REVIEW_ID, PROMPT_VERSION)
                    SELECT DISTINCT
                        rq.RESIDENT_ID,
                        f.value:deficit_id::VARCHAR as INDICATOR_ID,
                        CASE WHEN rq.STATUS = 'APPROVED' THEN TRUE ELSE FALSE END as EXPECTED_DETECTED,
                        CASE 
                            WHEN rq.STATUS = 'APPROVED' THEN f.value:reasoning::VARCHAR
                            ELSE 'REJECTED: ' || COALESCE(rq.REVIEWER_NOTES, 'No notes')
                        END as EVIDENCE_SUMMARY,
                        rq.REVIEWER_USER as VALIDATED_BY,
                        rq.QUEUE_ID as SOURCE_REVIEW_ID,
                        lla.PROMPT_VERSION
                    FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE rq
                    JOIN AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS lla ON rq.ANALYSIS_ID = lla.ANALYSIS_ID,
                    LATERAL FLATTEN(input => COALESCE(rq.INDICATOR_CHANGES_JSON, PARSE_JSON('[]'))) f
                    WHERE rq.STATUS IN ('APPROVED', 'REJECTED')
                      AND f.value:detected::BOOLEAN = TRUE
                      AND NOT EXISTS (
                          SELECT 1 FROM AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH gt 
                          WHERE gt.SOURCE_REVIEW_ID = rq.QUEUE_ID 
                            AND gt.INDICATOR_ID = f.value:deficit_id::VARCHAR
                      )
                """, session)
                
                new_count = execute_query("""
                    SELECT COUNT(*) as COUNT FROM AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH WHERE IS_ACTIVE = TRUE
                """, session)
                new_total = new_count[0]['COUNT'] if new_count else 0
                added = new_total - total_gt
                
                st.success(f"✅ Harvested {added} new ground truth records. Total: {new_total}")
                
            except Exception as e:
                st.error(f"Error harvesting ground truth: {str(e)}")
        
        st.markdown("---")
        
        st.subheader("Ground Truth Coverage")
        
        coverage = execute_query_df("""
            SELECT 
                PROMPT_VERSION,
                COUNT(DISTINCT RESIDENT_ID) as RESIDENTS,
                COUNT(*) as TOTAL_RECORDS,
                COUNT(CASE WHEN EXPECTED_DETECTED = TRUE THEN 1 END) as POSITIVE_CASES,
                COUNT(CASE WHEN EXPECTED_DETECTED = FALSE THEN 1 END) as NEGATIVE_CASES,
                MAX(VALIDATED_TIMESTAMP) as LAST_UPDATED
            FROM AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH
            WHERE IS_ACTIVE = TRUE
            GROUP BY PROMPT_VERSION
            ORDER BY TOTAL_RECORDS DESC
        """, session)
        
        if coverage is not None and len(coverage) > 0:
            st.dataframe(
                coverage.rename(columns={
                    'PROMPT_VERSION': 'Prompt',
                    'RESIDENTS': 'Residents',
                    'TOTAL_RECORDS': 'Total',
                    'POSITIVE_CASES': 'Positives',
                    'NEGATIVE_CASES': 'Negatives',
                    'LAST_UPDATED': 'Last Updated'
                }),
                use_container_width=True
            )
        else:
            st.caption("No ground truth data yet. Complete reviews and harvest to build your test dataset.")
        
        st.markdown("---")
        
        with st.expander("View Ground Truth Details", expanded=False):
            gt_details = execute_query_df("""
                SELECT 
                    RESIDENT_ID,
                    INDICATOR_ID,
                    EXPECTED_DETECTED,
                    LEFT(EVIDENCE_SUMMARY, 100) as EVIDENCE,
                    VALIDATED_BY,
                    VALIDATED_TIMESTAMP
                FROM AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH
                WHERE IS_ACTIVE = TRUE
                ORDER BY VALIDATED_TIMESTAMP DESC
                LIMIT 50
            """, session)
            
            if gt_details is not None and len(gt_details) > 0:
                st.dataframe(gt_details, use_container_width=True)
            else:
                st.caption("No ground truth records found.")

else:
    st.error("Failed to connect to Snowflake")
