"""
Shared AI/ML Helper Functions
=============================

Common AI and machine learning functions used across all three UI styles.
Provides consistent interface for Snowflake Cortex and other AI operations.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
import json
import sys
import os

# Add parent directory for connection_helper imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from connection_helper import (
        execute_cortex_complete,
        query_cortex_search_service,
        process_single_patient_comprehensive
    )
except ImportError:
    # Fallback if connection_helper not available
    def execute_cortex_complete(*args, **kwargs):
        return "AI service temporarily unavailable"
    
    def query_cortex_search_service(*args, **kwargs):
        return []
    
    def process_single_patient_comprehensive(*args, **kwargs):
        return {}


# Standard medical AI prompts used across all styles
MEDICAL_PROMPTS = {
    'clinical_summary': """
    You are a medical AI assistant helping to summarize patient information. 
    Based on the following patient data, provide a concise clinical summary in SBAR format 
    (Situation, Background, Assessment, Recommendation).
    
    Patient Data: {patient_data}
    
    Please respond with a structured summary that a healthcare professional can quickly understand.
    Focus on key clinical insights and actionable recommendations.
    """,
    
    'differential_diagnosis': """
    You are a medical AI assistant specializing in differential diagnosis.
    Based on the patient's symptoms and medical history, suggest possible diagnoses 
    ranked by likelihood with brief explanations.
    
    Patient Information: {patient_data}
    
    Provide up to 5 differential diagnoses in JSON format:
    {{
        "diagnoses": [
            {{
                "diagnosis": "Condition name",
                "likelihood": "High/Medium/Low",
                "reasoning": "Brief explanation"
            }}
        ]
    }}
    """,
    
    'treatment_recommendations': """
    You are a medical AI assistant focused on treatment planning.
    Based on the patient information and potential diagnoses, suggest appropriate 
    treatment options and next steps.
    
    Patient Data: {patient_data}
    Suspected Conditions: {conditions}
    
    Provide treatment recommendations in JSON format:
    {{
        "immediate_actions": ["action1", "action2"],
        "medications": [{{ "drug": "name", "dosage": "amount", "rationale": "reason" }}],
        "follow_up": ["follow-up step 1", "follow-up step 2"],
        "monitoring": ["vital to monitor", "lab to check"]
    }}
    """,
    
    'risk_assessment': """
    You are a medical AI assistant specializing in patient risk assessment.
    Analyze the patient data to identify potential risks and provide a risk score.
    
    Patient Information: {patient_data}
    
    Provide risk assessment in JSON format:
    {{
        "overall_risk": "Low/Medium/High",
        "risk_factors": [
            {{
                "factor": "risk factor name",
                "severity": "Low/Medium/High",
                "impact": "description of impact"
            }}
        ],
        "recommendations": ["recommendation 1", "recommendation 2"]
    }}
    """
}


def execute_medical_ai_prompt(
    prompt_type: str, 
    patient_data: dict,
    model: str = "mixtral-8x7b",
    **kwargs
) -> Dict[str, Any]:
    """
    Execute a medical AI prompt with standardized error handling.
    
    Args:
        prompt_type: Type of prompt from MEDICAL_PROMPTS
        patient_data: Patient data dictionary
        model: Snowflake Cortex model to use
        **kwargs: Additional prompt parameters
    
    Returns:
        Dict with 'success', 'result', and 'error' keys
    """
    if prompt_type not in MEDICAL_PROMPTS:
        return {
            'success': False,
            'error': f"Unknown prompt type: {prompt_type}",
            'result': None
        }
    
    try:
        # Format the prompt with provided data
        prompt_template = MEDICAL_PROMPTS[prompt_type]
        formatted_prompt = prompt_template.format(
            patient_data=json.dumps(patient_data, indent=2),
            **kwargs
        )
        
        # Execute via Snowflake Cortex
        response = execute_cortex_complete(formatted_prompt, model)
        
        # Try to parse JSON responses
        if prompt_type in ['differential_diagnosis', 'treatment_recommendations', 'risk_assessment']:
            try:
                parsed_result = json.loads(response)
                return {
                    'success': True,
                    'result': parsed_result,
                    'error': None,
                    'raw_response': response
                }
            except json.JSONDecodeError:
                # Return raw response if JSON parsing fails
                return {
                    'success': True,
                    'result': {'raw_text': response},
                    'error': 'Could not parse JSON response',
                    'raw_response': response
                }
        else:
            return {
                'success': True,
                'result': response,
                'error': None,
                'raw_response': response
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': f"AI processing error: {str(e)}",
            'result': None
        }


def search_similar_cases(
    patient_description: str, 
    search_service: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Search for similar patient cases using Cortex Search.
    Used across all UI styles for case comparison.
    
    Args:
        patient_description: Text description of patient case
        search_service: Name of the Cortex search service
        limit: Number of results to return
    
    Returns:
        List of similar cases with metadata
    """
    try:
        search_results = query_cortex_search_service(
            search_service, 
            patient_description, 
            limit=limit
        )
        
        processed_results = []
        for result in search_results:
            processed_results.append({
                'similarity_score': result.get('similarity_score', 0),
                'patient_id': result.get('patient_id', 'Unknown'),
                'summary': result.get('summary', ''),
                'key_findings': result.get('key_findings', []),
                'outcome': result.get('outcome', 'Not recorded')
            })
        
        return processed_results
    
    except Exception as e:
        st.error(f"Error searching similar cases: {str(e)}")
        return []


def analyze_patient_comprehensively(
    patient_id: int,
    connection,
    include_similar_cases: bool = True
) -> Dict[str, Any]:
    """
    Perform comprehensive AI analysis of a patient.
    Combines multiple AI prompts and search results.
    
    Args:
        patient_id: Patient ID to analyze
        connection: Database connection
        include_similar_cases: Whether to include similar case search
    
    Returns:
        Comprehensive analysis results
    """
    try:
        # Use existing comprehensive processing function
        base_results = process_single_patient_comprehensive(patient_id, connection)
        
        if not base_results:
            return {
                'success': False,
                'error': 'No patient data found',
                'patient_id': patient_id
            }
        
        # Parse existing results if they're in JSON format
        if isinstance(base_results, str):
            try:
                base_results = json.loads(base_results)
            except json.JSONDecodeError:
                base_results = {'raw_analysis': base_results}
        
        # Add similar cases if requested
        if include_similar_cases and 'summary' in base_results:
            similar_cases = search_similar_cases(
                base_results['summary'], 
                'medical_notes_search_service',
                limit=3
            )
            base_results['similar_cases'] = similar_cases
        
        base_results['success'] = True
        base_results['patient_id'] = patient_id
        
        return base_results
    
    except Exception as e:
        return {
            'success': False,
            'error': f"Comprehensive analysis failed: {str(e)}",
            'patient_id': patient_id
        }


def validate_ai_response(response: Any, expected_format: str = 'json') -> Tuple[bool, str]:
    """
    Validate AI response format and content.
    
    Args:
        response: AI response to validate
        expected_format: Expected format ('json', 'text', 'structured')
    
    Returns:
        (is_valid, error_message)
    """
    if not response:
        return False, "Empty response"
    
    if expected_format == 'json':
        if isinstance(response, dict):
            return True, ""
        if isinstance(response, str):
            try:
                json.loads(response)
                return True, ""
            except json.JSONDecodeError:
                return False, "Invalid JSON format"
    
    elif expected_format == 'text':
        if isinstance(response, str) and len(response.strip()) > 0:
            return True, ""
        return False, "Empty or invalid text response"
    
    elif expected_format == 'structured':
        if isinstance(response, dict):
            required_keys = ['summary', 'recommendations']
            missing_keys = [key for key in required_keys if key not in response]
            if missing_keys:
                return False, f"Missing required keys: {missing_keys}"
            return True, ""
    
    return False, f"Unexpected format for {expected_format}"


def create_ai_confidence_indicator(confidence_score: float) -> str:
    """
    Create a visual confidence indicator for AI responses.
    Used across all UI styles for consistent confidence display.
    
    Args:
        confidence_score: Float between 0 and 1
    
    Returns:
        Formatted confidence string with emoji indicator
    """
    if confidence_score >= 0.8:
        return f"🟢 High Confidence ({confidence_score:.1%})"
    elif confidence_score >= 0.6:
        return f"🟡 Medium Confidence ({confidence_score:.1%})"
    else:
        return f"🔴 Low Confidence ({confidence_score:.1%})"


def format_ai_timing_info(start_time: float, end_time: float) -> str:
    """
    Format AI processing timing information.
    
    Args:
        start_time: Start timestamp
        end_time: End timestamp
    
    Returns:
        Formatted timing string
    """
    duration = end_time - start_time
    if duration < 1:
        return f"Processed in {duration*1000:.0f}ms"
    elif duration < 60:
        return f"Processed in {duration:.1f}s"
    else:
        minutes, seconds = divmod(duration, 60)
        return f"Processed in {int(minutes)}m {seconds:.0f}s"


# Cached AI functions for performance
@st.cache_data(ttl=600, show_spinner=False)  # Cache for 10 minutes
def cached_medical_ai_prompt(
    prompt_type: str,
    patient_data_str: str,  # JSON string for caching
    model: str = "mixtral-8x7b"
) -> Dict[str, Any]:
    """Cached version of execute_medical_ai_prompt"""
    try:
        patient_data = json.loads(patient_data_str)
        return execute_medical_ai_prompt(prompt_type, patient_data, model)
    except json.JSONDecodeError:
        return {
            'success': False,
            'error': 'Invalid patient data format',
            'result': None
        }


@st.cache_data(ttl=1800)  # Cache for 30 minutes
def cached_similar_cases_search(
    patient_description: str,
    search_service: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Cached version of search_similar_cases"""
    return search_similar_cases(patient_description, search_service, limit)


def clear_ai_caches():
    """Clear all AI-related caches"""
    cached_medical_ai_prompt.clear()
    cached_similar_cases_search.clear()
    st.success("AI caches cleared successfully")


# AI processing status indicators
def show_ai_processing_status(status: str, details: str = ""):
    """Show consistent AI processing status across all UI styles"""
    status_config = {
        'starting': {'icon': '🔄', 'color': 'blue'},
        'processing': {'icon': '⚙️', 'color': 'orange'},
        'completing': {'icon': '📝', 'color': 'green'},
        'error': {'icon': '❌', 'color': 'red'},
        'complete': {'icon': '✅', 'color': 'green'}
    }
    
    config = status_config.get(status, {'icon': 'ℹ️', 'color': 'gray'})
    
    message = f"{config['icon']} **AI Status**: {status.title()}"
    if details:
        message += f" - {details}"
    
    if status == 'error':
        st.error(message)
    elif status == 'complete':
        st.success(message)
    else:
        st.info(message)
