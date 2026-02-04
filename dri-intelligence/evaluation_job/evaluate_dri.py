"""
DRI Evaluation Job - TruLens-based AI Observability Evaluation
==============================================================
This script runs DRI analysis evaluations using Snowflake AI Observability.
It is designed to run as an SPCS Job container.

Usage:
    python evaluate_dri.py --run-name "MyEval" --prompt-version "v1.0" --model "claude-3-5-sonnet" --sample-size 10
"""

import os
import sys
import json
import time
import uuid
import argparse
from datetime import datetime
from typing import Optional, Dict, List, Any

from snowflake.snowpark import Session
from trulens.core import TruSession
from trulens.core.otel.instrument import instrument
from trulens.otel.semconv.trace import SpanAttributes
from trulens.connectors.snowflake import SnowflakeConnector
from trulens.providers.cortex import Cortex


class DRIAnalyzer:
    """
    DRI Analysis application instrumented with TruLens for AI Observability.
    Each method is decorated with @instrument() to capture traces and enable evaluation metrics.
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
            SpanAttributes.RETRIEVAL.QUERY_TEXT: "resident_id",
            SpanAttributes.RETRIEVAL.RETRIEVED_CONTEXTS: "return",
        }
    )
    def retrieve_resident_context(self, resident_id: int) -> str:
        """
        Retrieve aggregated context for a resident including notes, medications, observations.
        Instrumented as RETRIEVAL span for context relevance evaluation.
        """
        query = f"""
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
        )
        SELECT 
            'PROGRESS NOTES: ' || COALESCE((SELECT txt FROM notes), 'None') ||
            ' MEDICATIONS: ' || COALESCE((SELECT txt FROM meds), 'None') ||
            ' OBSERVATIONS: ' || COALESCE((SELECT txt FROM obs), 'None') as CONTEXT
        """
        result = self.session.sql(query).collect()
        return result[0]['CONTEXT'] if result else ""
    
    @instrument(span_type=SpanAttributes.SpanType.GENERATION)
    def generate_analysis(self, prompt: str) -> str:
        """
        Generate DRI analysis using Cortex LLM.
        Instrumented as GENERATION span for groundedness and answer relevance evaluation.
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
            SpanAttributes.RECORD_ROOT.INPUT: "resident_id",
            SpanAttributes.RECORD_ROOT.OUTPUT: "return",
        }
    )
    def analyze_resident(self, resident_id: int) -> Dict[str, Any]:
        """
        Main entry point - analyze a resident for DRI indicators.
        Instrumented as RECORD_ROOT span - this is where evaluation starts.
        """
        context = self.retrieve_resident_context(resident_id)
        
        full_prompt = self.prompt_text.replace('{resident_context}', context)
        full_prompt = full_prompt.replace('{rag_indicator_context}', self.rag_context)
        
        response = self.generate_analysis(full_prompt)
        
        indicators = self._parse_indicators(response)
        
        return {
            'resident_id': resident_id,
            'context': context,
            'response': response,
            'indicators': indicators,
            'indicator_count': len(indicators)
        }
    
    def _parse_indicators(self, response: str) -> List[str]:
        """Parse detected indicators from LLM response."""
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(response[json_start:json_end])
                if 'indicators' in parsed:
                    return [ind.get('deficit_id', '') for ind in parsed['indicators'] if ind.get('detected', True)]
        except:
            pass
        return []


def run_evaluation(
    session: Session,
    run_name: str,
    prompt_version: str,
    model: str,
    sample_size: int
) -> Dict[str, Any]:
    """
    Run a full evaluation using TruLens AI Observability.
    """
    print(f"Starting evaluation: {run_name}")
    print(f"  Prompt version: {prompt_version}")
    print(f"  Model: {model}")
    print(f"  Sample size: {sample_size}")
    
    connector = SnowflakeConnector(snowpark_session=session)
    tru_session = TruSession(connector=connector)
    
    analyzer = DRIAnalyzer(session, prompt_version, model)
    
    residents = session.sql(f"""
        SELECT DISTINCT RESIDENT_ID 
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES
        ORDER BY RESIDENT_ID
        LIMIT {sample_size}
    """).collect()
    
    resident_ids = [r['RESIDENT_ID'] for r in residents]
    print(f"Evaluating {len(resident_ids)} residents...")
    
    evaluation_id = str(uuid.uuid4())
    session.sql(f"""
        INSERT INTO AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS 
        (EVALUATION_ID, RUN_NAME, PROMPT_VERSION, MODEL_USED, CLIENT_SYSTEM_KEY, DATASET_NAME, STATUS, TOTAL_RECORDS)
        VALUES ('{evaluation_id}', '{run_name}', '{prompt_version}', '{model}', 'SPCS_JOB', 'ACTIVE_RESIDENTS', 'RUNNING', {len(resident_ids)})
    """).collect()
    
    results = []
    total_latency = 0
    
    for idx, resident_id in enumerate(resident_ids):
        print(f"  Processing resident {idx + 1}/{len(resident_ids)}: {resident_id}")
        
        start_time = time.time()
        
        try:
            result = analyzer.analyze_resident(resident_id)
            
            latency_ms = int((time.time() - start_time) * 1000)
            total_latency += latency_ms
            
            results.append({
                'resident_id': resident_id,
                'indicators': result['indicators'],
                'indicator_count': result['indicator_count'],
                'latency_ms': latency_ms,
                'status': 'COMPLETED'
            })
            
            detail_id = str(uuid.uuid4())
            indicators_json = json.dumps(result['indicators'])
            session.sql(f"""
                INSERT INTO AGEDCARE.AGEDCARE.DRI_EVALUATION_DETAIL 
                (DETAIL_ID, EVALUATION_ID, RESIDENT_ID, RECORD_INDEX, INDICATORS_DETECTED, LATENCY_MS)
                SELECT '{detail_id}', '{evaluation_id}', {resident_id}, {idx}, {result['indicator_count']}, {latency_ms}
            """).collect()
            
        except Exception as e:
            print(f"    Error: {e}")
            results.append({
                'resident_id': resident_id,
                'error': str(e),
                'status': 'FAILED'
            })
    
    successful = [r for r in results if r.get('status') == 'COMPLETED']
    n = len(successful)
    avg_latency = total_latency // n if n > 0 else 0
    
    session.sql(f"""
        UPDATE AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS
        SET 
            RECORDS_EVALUATED = {n},
            AVG_LATENCY_MS = {avg_latency},
            STATUS = 'COMPLETED'
        WHERE EVALUATION_ID = '{evaluation_id}'
    """).collect()
    
    print(f"\nEvaluation complete!")
    print(f"  Records evaluated: {n}")
    print(f"  Average latency: {avg_latency}ms")
    print(f"\nView results in Snowsight: AI & ML → Evaluations")
    
    return {
        'evaluation_id': evaluation_id,
        'run_name': run_name,
        'records_evaluated': n,
        'avg_latency_ms': avg_latency
    }


def main():
    parser = argparse.ArgumentParser(description='DRI Evaluation Job')
    parser.add_argument('--run-name', type=str, default='Evaluation', help='Name for this evaluation run')
    parser.add_argument('--prompt-version', type=str, default='v1.0', help='Prompt version to evaluate')
    parser.add_argument('--model', type=str, default='claude-3-5-sonnet', help='LLM model to use')
    parser.add_argument('--sample-size', type=int, default=10, help='Number of residents to evaluate')
    
    args = parser.parse_args()
    
    print("Connecting to Snowflake...")
    
    token_path = "/snowflake/session/token"
    if os.path.exists(token_path):
        with open(token_path, 'r') as f:
            token = f.read().strip()
        session = Session.builder.configs({
            "account": os.environ.get("SNOWFLAKE_ACCOUNT"),
            "host": os.environ.get("SNOWFLAKE_HOST"),
            "authenticator": "oauth",
            "token": token,
            "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            "database": os.environ.get("SNOWFLAKE_DATABASE", "AGEDCARE"),
            "schema": os.environ.get("SNOWFLAKE_SCHEMA", "AGEDCARE"),
        }).create()
    else:
        session = Session.builder.configs({
            "account": os.environ.get("SNOWFLAKE_ACCOUNT"),
            "user": os.environ.get("SNOWFLAKE_USER"),
            "password": os.environ.get("SNOWFLAKE_PASSWORD"),
            "role": os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
            "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            "database": os.environ.get("SNOWFLAKE_DATABASE", "AGEDCARE"),
            "schema": os.environ.get("SNOWFLAKE_SCHEMA", "AGEDCARE"),
        }).create()
    
    try:
        results = run_evaluation(
            session=session,
            run_name=args.run_name,
            prompt_version=args.prompt_version,
            model=args.model,
            sample_size=args.sample_size
        )
        
        print(f"\nResults: {json.dumps(results, indent=2)}")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()
