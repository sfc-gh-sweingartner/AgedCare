"""
AI Observability Integration for DRI Intelligence
=================================================
This module provides the integration between DRI analysis and Snowflake AI Observability.
It wraps LLM calls with TruLens instrumentation for quality metrics and tracing.

Prerequisites:
- trulens-core>=2.1.2
- trulens-connectors-snowflake>=2.1.2
- trulens-providers-cortex>=2.1.2
- Environment variable: TRULENS_OTEL_TRACING=1

Note: This module can run in SPCS containers or external Python environments.
It CANNOT run in Snowflake Notebooks (TruLens limitation).
"""

import os
import json
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

from trulens.core import TruSession
from trulens.apps.custom import TruCustomApp, instrument
from trulens.connectors.snowflake import SnowflakeConnector
from trulens.providers.cortex import Cortex


class DRIObservabilityManager:
    """
    Manages AI Observability for DRI Intelligence application.
    Provides methods for:
    - Running evaluations with quality metrics
    - Storing evaluation results
    - Querying historical metrics
    
    Requires TruLens packages to be installed.
    """
    
    def __init__(self, session, client_system_key: str = "DEMO_CLIENT_871"):
        self.session = session
        self.client_system_key = client_system_key
        self.tru_session = None
        self.feedback_functions = None
        self._init_trulens()
    
    def _init_trulens(self):
        """Initialize TruLens session and feedback functions."""
        connector = SnowflakeConnector(snowpark_session=self.session)
        self.tru_session = TruSession(connector=connector)
        
        provider = Cortex(self.session, model_engine="claude-3-5-sonnet")
        
        self.feedback_functions = {
            'groundedness': provider.groundedness_measure_with_cot_reasons,
            'context_relevance': provider.context_relevance,
            'answer_relevance': provider.relevance,
        }
    
    def is_observability_enabled(self) -> bool:
        """Check if AI Observability is available and enabled."""
        return self.tru_session is not None
    
    def run_evaluation(
        self,
        prompt_version: str,
        model: str,
        dataset_name: str = "DEFAULT",
        resident_ids: Optional[List[int]] = None,
        run_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run an evaluation on a dataset of residents.
        
        Args:
            prompt_version: Version of prompt to evaluate
            model: LLM model to use
            dataset_name: Name of ground truth dataset to use
            resident_ids: Optional list of specific residents (if None, uses dataset)
            run_name: Optional name for this evaluation run
        
        Returns:
            Dictionary with evaluation results and metrics
        """
        evaluation_id = str(uuid.uuid4())
        run_name = run_name or f"Eval_{prompt_version}_{model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self._create_evaluation_record(evaluation_id, run_name, prompt_version, model, dataset_name)
        
        if resident_ids is None:
            resident_ids = self._get_residents_from_dataset(dataset_name)
        
        if not resident_ids:
            resident_ids = self._get_all_residents()
        
        results = {
            'evaluation_id': evaluation_id,
            'run_name': run_name,
            'total_records': len(resident_ids),
            'records_evaluated': 0,
            'details': [],
            'metrics': {
                'avg_groundedness': 0.0,
                'avg_context_relevance': 0.0,
                'avg_answer_relevance': 0.0,
                'true_positives': 0,
                'false_positives': 0,
                'true_negatives': 0,
                'false_negatives': 0,
                'avg_latency_ms': 0,
                'total_tokens': 0
            }
        }
        
        total_groundedness = 0.0
        total_context_relevance = 0.0
        total_answer_relevance = 0.0
        total_latency = 0
        
        for idx, resident_id in enumerate(resident_ids):
            try:
                detail = self._evaluate_resident(
                    evaluation_id=evaluation_id,
                    resident_id=resident_id,
                    prompt_version=prompt_version,
                    model=model,
                    record_index=idx,
                    dataset_name=dataset_name
                )
                
                results['details'].append(detail)
                results['records_evaluated'] += 1
                
                if detail.get('groundedness_score'):
                    total_groundedness += detail['groundedness_score']
                if detail.get('context_relevance_score'):
                    total_context_relevance += detail['context_relevance_score']
                if detail.get('answer_relevance_score'):
                    total_answer_relevance += detail['answer_relevance_score']
                if detail.get('latency_ms'):
                    total_latency += detail['latency_ms']
                
                if detail.get('is_correct') is not None:
                    if detail['is_correct']:
                        results['metrics']['true_positives'] += 1
                    else:
                        results['metrics']['false_positives'] += 1
                        
            except Exception as e:
                results['details'].append({
                    'resident_id': resident_id,
                    'error': str(e),
                    'status': 'FAILED'
                })
        
        n = results['records_evaluated']
        if n > 0:
            results['metrics']['avg_groundedness'] = total_groundedness / n
            results['metrics']['avg_context_relevance'] = total_context_relevance / n
            results['metrics']['avg_answer_relevance'] = total_answer_relevance / n
            results['metrics']['avg_latency_ms'] = total_latency // n
        
        tp = results['metrics']['true_positives']
        fp = results['metrics']['false_positives']
        if tp + fp > 0:
            results['metrics']['false_positive_rate'] = fp / (tp + fp)
            results['metrics']['precision'] = tp / (tp + fp)
        else:
            results['metrics']['false_positive_rate'] = 0.0
            results['metrics']['precision'] = 0.0
        
        self._update_evaluation_metrics(evaluation_id, results)
        
        return results
    
    def _evaluate_resident(
        self,
        evaluation_id: str,
        resident_id: int,
        prompt_version: str,
        model: str,
        record_index: int,
        dataset_name: str
    ) -> Dict[str, Any]:
        """Evaluate a single resident and compute quality metrics."""
        detail_id = str(uuid.uuid4())
        
        context = self._get_resident_context(resident_id)
        prompt_text = self._get_prompt_text(prompt_version)
        
        start_time = time.time()
        
        response = self._run_llm_analysis(resident_id, prompt_text, model, context)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        indicators = self._parse_indicators(response)
        
        groundedness = self._compute_groundedness(response, context)
        context_relevance = self._compute_context_relevance(context, prompt_text)
        answer_relevance = self._compute_answer_relevance(response, prompt_text)
        
        expected = self._get_expected_indicators(resident_id, dataset_name)
        is_correct, mismatch = self._compare_indicators(indicators, expected)
        
        detail = {
            'detail_id': detail_id,
            'evaluation_id': evaluation_id,
            'resident_id': resident_id,
            'record_index': record_index,
            'indicators_detected': len(indicators),
            'groundedness_score': groundedness,
            'context_relevance_score': context_relevance,
            'answer_relevance_score': answer_relevance,
            'expected_indicators': expected,
            'actual_indicators': indicators,
            'is_correct': is_correct,
            'mismatch_details': mismatch,
            'latency_ms': latency_ms,
            'status': 'COMPLETED'
        }
        
        self._store_evaluation_detail(detail)
        
        return detail
    
    def _compute_groundedness(self, response: str, context: str) -> float:
        """
        Compute groundedness score using TruLens LLM-as-judge.
        Measures if the response is grounded in the provided context.
        """
        score = self.feedback_functions['groundedness'](context, response)
        return float(score) if score is not None else 0.0
    
    def _compute_context_relevance(self, context: str, prompt: str) -> float:
        """Compute context relevance score using TruLens."""
        score = self.feedback_functions['context_relevance'](prompt, context)
        return float(score) if score is not None else 0.0
    
    def _compute_answer_relevance(self, response: str, prompt: str) -> float:
        """Compute answer relevance score using TruLens."""
        score = self.feedback_functions['answer_relevance'](prompt, response)
        return float(score) if score is not None else 0.0
    
    def _get_resident_context(self, resident_id: int) -> str:
        """Get aggregated context for a resident."""
        query = f"""
        WITH notes AS (
            SELECT LISTAGG(LEFT(PROGRESS_NOTE, 400), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as txt
            FROM (SELECT PROGRESS_NOTE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 15)
        ),
        meds AS (
            SELECT LISTAGG(MED_NAME || ' (' || MED_STATUS || ')', ', ') as txt
            FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION WHERE RESIDENT_ID = {resident_id}
        ),
        obs AS (
            SELECT LISTAGG(CHART_NAME || ': ' || LEFT(OBSERVATION_VALUE, 100), ' | ') WITHIN GROUP (ORDER BY EVENT_DATE DESC) as txt
            FROM (SELECT CHART_NAME, OBSERVATION_VALUE, EVENT_DATE FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS WHERE RESIDENT_ID = {resident_id} ORDER BY EVENT_DATE DESC LIMIT 30)
        )
        SELECT 
            'PROGRESS NOTES: ' || COALESCE((SELECT txt FROM notes), 'None') ||
            ' MEDICATIONS: ' || COALESCE((SELECT txt FROM meds), 'None') ||
            ' OBSERVATIONS: ' || COALESCE((SELECT txt FROM obs), 'None') as CONTEXT
        """
        result = self.session.sql(query).collect()
        return result[0]['CONTEXT'] if result else ""
    
    def _get_prompt_text(self, version: str) -> str:
        """Get prompt text for a version."""
        query = f"""
        SELECT PROMPT_TEXT FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS 
        WHERE VERSION_NUMBER = '{version}'
        """
        result = self.session.sql(query).collect()
        return result[0]['PROMPT_TEXT'] if result else ""
    
    def _run_llm_analysis(self, resident_id: int, prompt: str, model: str, context: str) -> str:
        """Run LLM analysis for a resident."""
        rag_query = """
        SELECT LISTAGG(INDICATOR_ID || ' - ' || INDICATOR_NAME || ': ' || DEFINITION, ' || ') as indicators
        FROM AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS
        """
        rag_result = self.session.sql(rag_query).collect()
        rag_context = rag_result[0]['INDICATORS'] if rag_result else ""
        
        final_prompt = prompt.replace('{resident_context}', context).replace('{rag_indicator_context}', rag_context)
        
        escaped = final_prompt.replace("'", "''")
        
        query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            '{model}',
            [{{ 'role': 'user', 'content': '{escaped}' }}],
            {{ 'max_tokens': 8192 }}
        ) as RESPONSE
        """
        
        result = self.session.sql(query).collect()
        return result[0]['RESPONSE'] if result else ""
    
    def _parse_indicators(self, response: str) -> List[str]:
        """Parse detected indicators from LLM response."""
        try:
            if '"choices"' in response:
                wrapper = json.loads(response)
                if 'choices' in wrapper:
                    response = wrapper['choices'][0].get('messages', response)
            
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(response[json_start:json_end])
                if 'indicators' in parsed:
                    return [ind.get('deficit_id', '') for ind in parsed['indicators'] if ind.get('detected', True)]
        except:
            pass
        return []
    
    def _get_expected_indicators(self, resident_id: int, dataset_name: str) -> List[str]:
        """Get expected indicators from ground truth."""
        query = f"""
        SELECT EXPECTED_INDICATORS 
        FROM AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH
        WHERE RESIDENT_ID = {resident_id} 
          AND DATASET_NAME = '{dataset_name}'
          AND IS_ACTIVE = TRUE
        ORDER BY CREATED_TIMESTAMP DESC
        LIMIT 1
        """
        result = self.session.sql(query).collect()
        if result and result[0]['EXPECTED_INDICATORS']:
            return list(result[0]['EXPECTED_INDICATORS'])
        return []
    
    def _compare_indicators(self, actual: List[str], expected: List[str]) -> Tuple[bool, str]:
        """Compare actual vs expected indicators."""
        if not expected:
            return None, "No ground truth available"
        
        actual_set = set(actual)
        expected_set = set(expected)
        
        fp = actual_set - expected_set
        fn = expected_set - actual_set
        
        if not fp and not fn:
            return True, "Perfect match"
        
        mismatch = []
        if fp:
            mismatch.append(f"False positives: {list(fp)}")
        if fn:
            mismatch.append(f"Missed: {list(fn)}")
        
        return False, "; ".join(mismatch)
    
    def _create_evaluation_record(self, eval_id: str, run_name: str, prompt_version: str, model: str, dataset_name: str):
        """Create initial evaluation record."""
        query = f"""
        INSERT INTO AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS 
        (EVALUATION_ID, RUN_NAME, PROMPT_VERSION, MODEL_USED, CLIENT_SYSTEM_KEY, DATASET_NAME, STATUS)
        VALUES ('{eval_id}', '{run_name}', '{prompt_version}', '{model}', '{self.client_system_key}', '{dataset_name}', 'RUNNING')
        """
        self.session.sql(query).collect()
    
    def _update_evaluation_metrics(self, eval_id: str, results: Dict):
        """Update evaluation record with final metrics."""
        m = results['metrics']
        query = f"""
        UPDATE AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS
        SET 
            TOTAL_RECORDS = {results['total_records']},
            RECORDS_EVALUATED = {results['records_evaluated']},
            AVG_GROUNDEDNESS_SCORE = {m.get('avg_groundedness', 0)},
            AVG_CONTEXT_RELEVANCE_SCORE = {m.get('avg_context_relevance', 0)},
            AVG_ANSWER_RELEVANCE_SCORE = {m.get('avg_answer_relevance', 0)},
            TRUE_POSITIVES = {m.get('true_positives', 0)},
            FALSE_POSITIVES = {m.get('false_positives', 0)},
            FALSE_POSITIVE_RATE = {m.get('false_positive_rate', 0)},
            PRECISION_SCORE = {m.get('precision', 0)},
            AVG_LATENCY_MS = {m.get('avg_latency_ms', 0)},
            STATUS = 'COMPLETED'
        WHERE EVALUATION_ID = '{eval_id}'
        """
        self.session.sql(query).collect()
    
    def _store_evaluation_detail(self, detail: Dict):
        """Store evaluation detail record."""
        expected_json = json.dumps(detail.get('expected_indicators', []))
        actual_json = json.dumps(detail.get('actual_indicators', []))
        is_correct = 'TRUE' if detail.get('is_correct') else 'FALSE' if detail.get('is_correct') is False else 'NULL'
        
        query = f"""
        INSERT INTO AGEDCARE.AGEDCARE.DRI_EVALUATION_DETAIL 
        (DETAIL_ID, EVALUATION_ID, RESIDENT_ID, RECORD_INDEX, INDICATORS_DETECTED,
         GROUNDEDNESS_SCORE, CONTEXT_RELEVANCE_SCORE, ANSWER_RELEVANCE_SCORE,
         EXPECTED_INDICATORS, ACTUAL_INDICATORS, IS_CORRECT, MISMATCH_DETAILS, LATENCY_MS)
        SELECT
            '{detail['detail_id']}',
            '{detail['evaluation_id']}',
            {detail['resident_id']},
            {detail['record_index']},
            {detail.get('indicators_detected', 0)},
            {detail.get('groundedness_score', 0)},
            {detail.get('context_relevance_score', 0)},
            {detail.get('answer_relevance_score', 0)},
            PARSE_JSON('{expected_json}'),
            PARSE_JSON('{actual_json}'),
            {is_correct},
            '{detail.get('mismatch_details', '').replace("'", "''")}',
            {detail.get('latency_ms', 0)}
        """
        self.session.sql(query).collect()
    
    def _get_residents_from_dataset(self, dataset_name: str) -> List[int]:
        """Get resident IDs from ground truth dataset."""
        query = f"""
        SELECT DISTINCT RESIDENT_ID 
        FROM AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH
        WHERE DATASET_NAME = '{dataset_name}' AND IS_ACTIVE = TRUE
        """
        result = self.session.sql(query).collect()
        return [row['RESIDENT_ID'] for row in result]
    
    def _get_all_residents(self) -> List[int]:
        """Get all resident IDs."""
        query = """
        SELECT DISTINCT RESIDENT_ID 
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES
        ORDER BY RESIDENT_ID
        LIMIT 100
        """
        result = self.session.sql(query).collect()
        return [row['RESIDENT_ID'] for row in result]
    
    def get_evaluation_history(self, limit: int = 20) -> List[Dict]:
        """Get recent evaluation history."""
        query = f"""
        SELECT * FROM AGEDCARE.AGEDCARE.V_EVALUATION_SUMMARY
        LIMIT {limit}
        """
        result = self.session.sql(query).collect()
        return [dict(row) for row in result]
    
    def get_fp_rate_trend(self, days: int = 30) -> List[Dict]:
        """Get false positive rate trend."""
        query = f"""
        SELECT * FROM AGEDCARE.AGEDCARE.V_FP_RATE_TREND
        WHERE EVAL_DATE >= DATEADD(day, -{days}, CURRENT_DATE())
        ORDER BY EVAL_DATE
        """
        result = self.session.sql(query).collect()
        return [dict(row) for row in result]
    
    def get_evaluation_details(self, evaluation_id: str) -> List[Dict]:
        """Get details for a specific evaluation."""
        query = f"""
        SELECT * FROM AGEDCARE.AGEDCARE.DRI_EVALUATION_DETAIL
        WHERE EVALUATION_ID = '{evaluation_id}'
        ORDER BY RECORD_INDEX
        """
        result = self.session.sql(query).collect()
        return [dict(row) for row in result]
