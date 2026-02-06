"""
DRI Evaluation Job - TruLens-based AI Observability Evaluation
==============================================================
This script runs DRI analysis evaluations using Snowflake AI Observability.
It is designed to run as an SPCS Job container.

IMPORTANT: This module uses the official TruLens SDK pattern to register
applications and runs with Snowflake AI Observability. Results appear in
Snowsight > AI & ML > Evaluations.

KEY IMPLEMENTATION NOTES (v1.1 - 2026-02-06):
1. TruApp constructor uses POSITIONAL argument for the app:
   - Correct: TruApp(analyzer, app_name=..., connector=...)
   - Wrong: TruApp(test_app=analyzer, ...)

2. Dataset spec uses LOWERCASE keys:
   - Correct: dataset_spec={"input": "input_query"}
   - Wrong: dataset_spec={"RECORD_ROOT.INPUT": "input_query"}

3. Run type annotation:
   - Correct: run: Run = tru_app.add_run(run_config=...)

4. Required packages (separate installs):
   - trulens-core>=2.1.2
   - trulens-connectors-snowflake>=2.1.2
   - trulens-providers-cortex>=2.1.2

5. Docker build MUST use --platform linux/amd64 for SPCS

Usage:
    python evaluate_dri.py --run-name "MyEval" --prompt-version "v1.0" --model "claude-sonnet-4-5" --sample-size 10
"""

import os
import sys
import json
import time
import uuid
import argparse
from datetime import datetime
from typing import Optional, Dict, List, Any

import pandas as pd
from snowflake.snowpark import Session

from trulens.core.otel.instrument import instrument
from trulens.otel.semconv.trace import SpanAttributes
from trulens.connectors.snowflake import SnowflakeConnector
from trulens.apps.app import TruApp
from trulens.core.run import Run, RunConfig


class DRIAnalyzer:
    """
    DRI Analysis application instrumented with TruLens for AI Observability.
    Each method is decorated with @instrument() to capture traces and enable evaluation metrics.
    
    The instrumentation follows Snowflake AI Observability requirements:
    - RETRIEVAL span: captures query_text and retrieved_contexts for context_relevance
    - GENERATION span: captures LLM inference for latency/cost tracking
    - RECORD_ROOT span: captures input/output for groundedness and answer_relevance
    """
    
    def __init__(self, session: Session, prompt_version: str, model: str):
        self.session = session
        self.prompt_version = prompt_version
        self.model = model
        self.prompt_text = self._load_prompt()
        self.rag_context = self._load_rag_indicators()
    
    def _load_prompt(self) -> str:
        """Load the prompt text for the specified version."""
        result = self.session.sql(f"""
            SELECT PROMPT_TEXT FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS 
            WHERE VERSION_NUMBER = '{self.prompt_version}'
        """).collect()
        return result[0]['PROMPT_TEXT'] if result else ""
    
    def _load_rag_indicators(self) -> str:
        """Load RAG indicator definitions."""
        result = self.session.sql("""
            SELECT LISTAGG(INDICATOR_ID || ' - ' || INDICATOR_NAME || ': ' || DEFINITION, ' || ') as indicators
            FROM AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS
        """).collect()
        return result[0]['INDICATORS'] if result else ""
    
    @instrument(
        span_type=SpanAttributes.SpanType.RETRIEVAL,
        attributes={
            SpanAttributes.RETRIEVAL.QUERY_TEXT: "query",
            SpanAttributes.RETRIEVAL.RETRIEVED_CONTEXTS: "return",
        }
    )
    def retrieve_resident_context(self, query: str, resident_id: int) -> List[str]:
        """
        Retrieve aggregated context for a resident including notes, medications, observations.
        Instrumented as RETRIEVAL span for context relevance evaluation.
        
        Args:
            query: The analysis query (used for context_relevance metric)
            resident_id: The resident to retrieve context for
            
        Returns:
            List of context strings (format required by TruLens)
        """
        sql_query = f"""
        WITH notes AS (
            SELECT LISTAGG(LEFT(PROGRESS_NOTE, 400), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as txt
            FROM (SELECT PROGRESS_NOTE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES 
                  WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 15)
        ),
        meds AS (
            SELECT LISTAGG(MED_NAME || ' (' || MED_STATUS || ')', ', ') as txt
            FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION WHERE RESIDENT_ID = {resident_id}
        ),
        obs AS (
            SELECT LISTAGG(CHART_NAME || ': ' || LEFT(OBSERVATION_VALUE, 100), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as txt
            FROM (SELECT CHART_NAME, OBSERVATION_VALUE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS 
                  WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 30)
        ),
        forms AS (
            SELECT LISTAGG(FORM_NAME || ': ' || ELEMENT_NAME || '=' || LEFT(RESPONSE, 100), ' | ') as txt
            FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_ASSESSMENT_FORMS 
            WHERE RESIDENT_ID = {resident_id} AND RESPONSE IS NOT NULL AND TRIM(RESPONSE) != ''
        )
        SELECT 
            'PROGRESS NOTES: ' || COALESCE((SELECT txt FROM notes), 'None') ||
            ' MEDICATIONS: ' || COALESCE((SELECT txt FROM meds), 'None') ||
            ' OBSERVATIONS: ' || COALESCE((SELECT txt FROM obs), 'None') ||
            ' ASSESSMENT FORMS: ' || COALESCE((SELECT txt FROM forms), 'None') ||
            ' DRI INDICATORS: ' || '{self.rag_context[:2000]}' as CONTEXT
        """
        result = self.session.sql(sql_query).collect()
        context = result[0]['CONTEXT'] if result else ""
        return [context]
    
    @instrument(span_type=SpanAttributes.SpanType.GENERATION)
    def generate_analysis(self, prompt: str) -> str:
        """
        Generate DRI analysis using Cortex LLM.
        Instrumented as GENERATION span for latency and cost tracking.
        """
        escaped = prompt.replace("'", "''")
        
        query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            '{self.model}',
            [{{ 'role': 'user', 'content': '{escaped}' }}],
            {{ 'max_tokens': 8192 }}
        ) as RESPONSE
        """
        
        result = self.session.sql(query).collect()
        response = result[0]['RESPONSE'] if result else ""
        
        if '"choices"' in response:
            try:
                wrapper = json.loads(response)
                if 'choices' in wrapper:
                    response = wrapper['choices'][0].get('messages', response)
            except:
                pass
        
        return response
    
    @instrument(
        span_type=SpanAttributes.SpanType.RECORD_ROOT,
        attributes={
            SpanAttributes.RECORD_ROOT.INPUT: "input_query",
            SpanAttributes.RECORD_ROOT.OUTPUT: "return",
        }
    )
    def analyze_resident(self, input_query: str) -> str:
        """
        Main entry point - analyze a resident for DRI indicators.
        Instrumented as RECORD_ROOT span - this is where evaluation starts.
        
        The input_query format is: "Analyze resident {resident_id} for health deterioration indicators"
        This allows the evaluation to track which resident was analyzed.
        
        Returns:
            The LLM analysis response as a string (required for OUTPUT attribute)
        """
        resident_id = self._extract_resident_id(input_query)
        
        contexts = self.retrieve_resident_context(input_query, resident_id)
        context = contexts[0] if contexts else ""
        
        full_prompt = self.prompt_text.replace('{resident_context}', context)
        full_prompt = full_prompt.replace('{rag_indicator_context}', self.rag_context)
        
        response = self.generate_analysis(full_prompt)
        
        return response
    
    def _extract_resident_id(self, input_query: str) -> int:
        """Extract resident ID from the input query string."""
        try:
            import re
            match = re.search(r'resident (\d+)', input_query.lower())
            if match:
                return int(match.group(1))
        except:
            pass
        return 871


def create_evaluation_dataset(session: Session, sample_size: int) -> pd.DataFrame:
    """
    Create evaluation dataset from active residents.
    
    The dataset follows Snowflake AI Observability format with:
    - input_query: The query to analyze (maps to RECORD_ROOT.INPUT)
    - input_id: Unique identifier (maps to RECORD_ROOT.INPUT_ID)
    """
    residents = session.sql(f"""
        SELECT DISTINCT RESIDENT_ID 
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES
        ORDER BY RESIDENT_ID
        LIMIT {sample_size}
    """).collect()
    
    data = []
    for r in residents:
        resident_id = r['RESIDENT_ID']
        data.append({
            'input_query': f"Analyze resident {resident_id} for health deterioration indicators",
            'input_id': f"resident_{resident_id}",
            'resident_id': resident_id
        })
    
    return pd.DataFrame(data)


def run_evaluation(
    session: Session,
    run_name: str,
    prompt_version: str,
    model: str,
    sample_size: int,
    app_name: str = "DRI_INTELLIGENCE_AGENT"
) -> Dict[str, Any]:
    """
    Run a full evaluation using TruLens AI Observability.
    
    This follows the official Snowflake AI Observability pattern:
    1. Create TruSession with SnowflakeConnector
    2. Create DRIAnalyzer application
    3. Create TruApp to register the application
    4. Create RunConfig with dataset specification
    5. Add and start the run
    6. Compute metrics using LLM-as-judge
    
    Results appear in Snowsight > AI & ML > Evaluations
    """
    print(f"\n{'='*60}")
    print(f"Starting AI Observability Evaluation")
    print(f"{'='*60}")
    print(f"  App name: {app_name}")
    print(f"  Run name: {run_name}")
    print(f"  Prompt version: {prompt_version}")
    print(f"  Model: {model}")
    print(f"  Sample size: {sample_size}")
    
    print("\n[1/6] Creating Snowflake connector...")
    connector = SnowflakeConnector(snowpark_session=session)
    
    print("[2/6] Creating DRI Analyzer application...")
    analyzer = DRIAnalyzer(session, prompt_version, model)
    
    print("[3/6] Registering application with Snowflake AI Observability...")
    app_version = f"{prompt_version}_{model}"
    
    # Register application following official TruLens pattern
    # This creates an EXTERNAL AGENT in Snowflake and tracks runs
    tru_app = TruApp(
        analyzer,  # The application instance
        app_name=app_name,
        app_version=app_version,
        connector=connector
    )
    print(f"  Registered: {app_name} v{app_version}")
    
    print("[4/6] Creating evaluation dataset...")
    eval_df = create_evaluation_dataset(session, sample_size)
    print(f"  Dataset size: {len(eval_df)} residents")
    
    print("[5/6] Creating and starting evaluation run...")
    run_config = RunConfig(
        run_name=run_name,
        description=f"DRI evaluation with {model} using prompt {prompt_version}",
        label=f"batch_{sample_size}",
        source_type="DATAFRAME",
        dataset_name="DRI_ACTIVE_RESIDENTS",
        dataset_spec={
            "input": "input_query",
        },
    )
    
    run: Run = tru_app.add_run(run_config=run_config)
    print(f"  Run created: {run_name}")
    
    print("  Starting invocation (this may take several minutes)...")
    start_time = time.time()
    run.start(input_df=eval_df)
    invocation_time = time.time() - start_time
    print(f"  Invocation completed in {invocation_time:.1f}s")
    
    print("[6/6] Computing evaluation metrics...")
    metrics_to_compute = [
        "groundedness",
        "answer_relevance",
        "context_relevance",
        "coherence"
    ]
    print(f"  Metrics: {', '.join(metrics_to_compute)}")
    
    run.compute_metrics(metrics=metrics_to_compute)
    print("  Metric computation started (async)")
    
    print("\nWaiting for metric computation to complete...")
    max_wait = 300
    wait_interval = 10
    elapsed = 0
    
    while elapsed < max_wait:
        status = run.get_status()
        print(f"  Status: {status} ({elapsed}s elapsed)")
        
        if status in ['COMPLETED', 'PARTIALLY_COMPLETED']:
            break
        elif status in ['CANCELLED']:
            print("  Run was cancelled!")
            break
            
        time.sleep(wait_interval)
        elapsed += wait_interval
    
    final_status = run.get_status()
    total_time = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"Evaluation Complete!")
    print(f"{'='*60}")
    print(f"  Final status: {final_status}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Records evaluated: {len(eval_df)}")
    print(f"\nView results in Snowsight:")
    print(f"  AI & ML > Evaluations > {app_name} > {run_name}")
    print(f"{'='*60}\n")
    
    also_store_to_custom_tables(
        session=session,
        run_name=run_name,
        prompt_version=prompt_version,
        model=model,
        sample_size=sample_size,
        status=final_status,
        total_time_ms=int(total_time * 1000)
    )
    
    return {
        'app_name': app_name,
        'app_version': app_version,
        'run_name': run_name,
        'status': final_status,
        'records_evaluated': len(eval_df),
        'total_time_seconds': total_time,
        'metrics_computed': metrics_to_compute
    }


def also_store_to_custom_tables(
    session: Session,
    run_name: str,
    prompt_version: str,
    model: str,
    sample_size: int,
    status: str,
    total_time_ms: int
):
    """
    Also store evaluation metadata to custom tables for the Streamlit app.
    This allows the Quality Metrics page to show results even if users
    don't have access to AI Observability views.
    """
    try:
        evaluation_id = str(uuid.uuid4())
        
        session.sql(f"""
            INSERT INTO AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS 
            (EVALUATION_ID, RUN_NAME, PROMPT_VERSION, MODEL_USED, CLIENT_SYSTEM_KEY, 
             DATASET_NAME, STATUS, TOTAL_RECORDS, RECORDS_EVALUATED, AVG_LATENCY_MS)
            VALUES (
                '{evaluation_id}', 
                '{run_name}', 
                '{prompt_version}', 
                '{model}', 
                'SPCS_TRULENS_JOB',
                'ACTIVE_RESIDENTS', 
                '{status}', 
                {sample_size}, 
                {sample_size}, 
                {total_time_ms // sample_size if sample_size > 0 else 0}
            )
        """).collect()
        
        print(f"  Also stored to DRI_EVALUATION_METRICS: {evaluation_id[:8]}...")
    except Exception as e:
        print(f"  Warning: Could not store to custom tables: {e}")


def get_pending_run_config(session: Session) -> Optional[Dict[str, Any]]:
    """
    Check DRI_EVAL_RUNS table for a pending run configuration.
    This allows the Streamlit app to queue evaluations without hardcoding.
    """
    try:
        result = session.sql("""
            SELECT RUN_ID, RUN_NAME, PROMPT_VERSION, MODEL, SAMPLE_SIZE, JOB_NAME
            FROM AGEDCARE.AGEDCARE.DRI_EVAL_RUNS
            WHERE STATUS = 'PENDING'
            ORDER BY CREATED_AT ASC
            LIMIT 1
        """).collect()
        
        if result:
            row = result[0]
            session.sql(f"""
                UPDATE AGEDCARE.AGEDCARE.DRI_EVAL_RUNS 
                SET STATUS = 'RUNNING', STARTED_AT = CURRENT_TIMESTAMP()
                WHERE RUN_ID = '{row['RUN_ID']}'
            """).collect()
            
            return {
                'run_id': row['RUN_ID'],
                'run_name': row['RUN_NAME'],
                'prompt_version': row['PROMPT_VERSION'] or 'v1.0',
                'model': row['MODEL'] or 'claude-sonnet-4-5',
                'sample_size': row['SAMPLE_SIZE'] or 10,
                'job_name': row['JOB_NAME']
            }
    except Exception as e:
        print(f"  Note: Could not check DRI_EVAL_RUNS table: {e}")
    return None


def update_run_status(session: Session, run_id: str, status: str):
    """Update the status of a run in DRI_EVAL_RUNS table."""
    try:
        session.sql(f"""
            UPDATE AGEDCARE.AGEDCARE.DRI_EVAL_RUNS 
            SET STATUS = '{status}', COMPLETED_AT = CURRENT_TIMESTAMP()
            WHERE RUN_ID = '{run_id}'
        """).collect()
    except Exception as e:
        print(f"  Warning: Could not update run status: {e}")


def main():
    parser = argparse.ArgumentParser(description='DRI Evaluation Job - Snowflake AI Observability')
    parser.add_argument('--run-name', type=str, default=None, 
                        help='Name for this evaluation run (reads from DB if not provided)')
    parser.add_argument('--prompt-version', type=str, default=None, 
                        help='Prompt version to evaluate')
    parser.add_argument('--model', type=str, default=None, 
                        help='LLM model to use')
    parser.add_argument('--sample-size', type=int, default=None, 
                        help='Number of residents to evaluate')
    parser.add_argument('--app-name', type=str, default='DRI_INTELLIGENCE_AGENT',
                        help='Application name in AI Observability')
    
    args = parser.parse_args()
    
    print("="*60)
    print("DRI Evaluation Job - Snowflake AI Observability")
    print("="*60)
    print("\nConnecting to Snowflake...")
    
    run_id_from_db = None
    
    token_path = "/snowflake/session/token"
    
    if os.path.exists(token_path):
        with open(token_path, 'r') as f:
            token = f.read().strip()
        
        host = os.environ.get("SNOWFLAKE_HOST")
        account = os.environ.get("SNOWFLAKE_ACCOUNT")
        database = os.environ.get("SNOWFLAKE_DATABASE", "AGEDCARE")
        schema = os.environ.get("SNOWFLAKE_SCHEMA", "AGEDCARE")
        warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
        
        print(f"  SNOWFLAKE_HOST: {host}")
        print(f"  SNOWFLAKE_ACCOUNT: {account}")
        print(f"  SNOWFLAKE_DATABASE: {database}")
        print(f"  SNOWFLAKE_SCHEMA: {schema}")
        
        session = Session.builder.configs({
            "host": host,
            "account": account,
            "authenticator": "oauth",
            "token": token,
            "warehouse": warehouse,
            "database": database,
            "schema": schema,
        }).create()
        print("  Connected via SPCS OAuth token")
    else:
        print("  No SPCS token found, using environment credentials")
        session = Session.builder.configs({
            "account": os.environ.get("SNOWFLAKE_ACCOUNT"),
            "user": os.environ.get("SNOWFLAKE_USER"),
            "password": os.environ.get("SNOWFLAKE_PASSWORD"),
            "role": os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
            "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            "database": os.environ.get("SNOWFLAKE_DATABASE", "AGEDCARE"),
            "schema": os.environ.get("SNOWFLAKE_SCHEMA", "AGEDCARE"),
        }).create()
        print("  Connected via username/password")
    
    db_config = get_pending_run_config(session)
    if db_config:
        print(f"\n  Found pending run in DRI_EVAL_RUNS: {db_config['run_name']}")
        run_id_from_db = db_config['run_id']
        if args.run_name is None:
            args.run_name = db_config['run_name']
        if args.prompt_version is None:
            args.prompt_version = db_config['prompt_version']
        if args.model is None:
            args.model = db_config['model']
        if args.sample_size is None:
            args.sample_size = db_config['sample_size']
    else:
        print("\n  No pending runs in DB, using defaults/env vars")
        if args.run_name is None:
            args.run_name = os.environ.get('RUN_NAME', f"Eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        if args.prompt_version is None:
            args.prompt_version = os.environ.get('PROMPT_VERSION', 'v1.0')
        if args.model is None:
            args.model = os.environ.get('MODEL', 'claude-sonnet-4-5')
        if args.sample_size is None:
            args.sample_size = int(os.environ.get('SAMPLE_SIZE', '10'))
    
    if not args.run_name:
        args.run_name = f"Eval_{args.prompt_version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"\n  Final config: run_name={args.run_name}, model={args.model}, sample={args.sample_size}")
    
    try:
        results = run_evaluation(
            session=session,
            run_name=args.run_name,
            prompt_version=args.prompt_version,
            model=args.model,
            sample_size=args.sample_size,
            app_name=args.app_name
        )
        
        print(f"\nResults Summary:")
        print(json.dumps(results, indent=2, default=str))
        
        if run_id_from_db:
            update_run_status(session, run_id_from_db, 'COMPLETED')
        
    except Exception as e:
        if run_id_from_db:
            update_run_status(session, run_id_from_db, 'FAILED')
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
