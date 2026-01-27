"""
Shared Data Processing Functions
================================

Common data transformation and processing functions used across all three UI styles.
This module provides a consistent interface for data manipulation regardless of UI style.
"""

import pandas as pd
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import streamlit as st


def parse_json_safely(json_str: str) -> dict:
    """
    Safely parse JSON string with fallback handling.
    Used across all styles for parsing AI responses.
    """
    if not json_str or pd.isna(json_str):
        return {}
    
    try:
        if isinstance(json_str, str):
            return json.loads(json_str)
        return json_str if isinstance(json_str, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def parse_consolidated_response(response: str) -> dict:
    """
    Parse consolidated AI response into structured data.
    Extracts JSON from AI text responses.
    """
    try:
        # Look for JSON pattern in the response
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {}
    except (json.JSONDecodeError, TypeError):
        return {}


def format_sbar_summary(patient_data: dict) -> str:
    """
    Format patient data into SBAR (Situation, Background, Assessment, Recommendation) format.
    Medical standard communication format used across all UI styles.
    """
    if not patient_data:
        return "No patient data available"
    
    sbar_parts = []
    
    # Situation
    if 'situation' in patient_data:
        sbar_parts.append(f"**Situation**: {patient_data['situation']}")
    
    # Background  
    if 'background' in patient_data:
        sbar_parts.append(f"**Background**: {patient_data['background']}")
    
    # Assessment
    if 'assessment' in patient_data:
        sbar_parts.append(f"**Assessment**: {patient_data['assessment']}")
    
    # Recommendation
    if 'recommendation' in patient_data:
        sbar_parts.append(f"**Recommendation**: {patient_data['recommendation']}")
    
    return "\n\n".join(sbar_parts) if sbar_parts else "SBAR format not available"


def process_patient_metrics(patient_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate key patient metrics for dashboard display.
    Returns standardized metrics dict used by all UI styles.
    """
    if patient_data.empty:
        return {
            'total_patients': 0,
            'avg_age': 0,
            'age_range': (0, 0),
            'gender_distribution': {},
            'common_conditions': [],
            'recent_visits': 0
        }
    
    metrics = {}
    
    # Basic counts
    metrics['total_patients'] = len(patient_data)
    
    # Age statistics
    if 'age' in patient_data.columns:
        age_data = pd.to_numeric(patient_data['age'], errors='coerce').dropna()
        metrics['avg_age'] = round(age_data.mean(), 1) if not age_data.empty else 0
        metrics['age_range'] = (int(age_data.min()), int(age_data.max())) if not age_data.empty else (0, 0)
    else:
        metrics['avg_age'] = 0
        metrics['age_range'] = (0, 0)
    
    # Gender distribution
    if 'gender' in patient_data.columns:
        gender_counts = patient_data['gender'].value_counts()
        metrics['gender_distribution'] = gender_counts.to_dict()
    else:
        metrics['gender_distribution'] = {}
    
    # Common conditions (if available)
    condition_columns = [col for col in patient_data.columns if 'condition' in col.lower() or 'diagnosis' in col.lower()]
    if condition_columns:
        all_conditions = []
        for col in condition_columns:
            conditions = patient_data[col].dropna().str.split(',').explode().str.strip()
            all_conditions.extend(conditions.tolist())
        
        condition_counts = pd.Series(all_conditions).value_counts().head(5)
        metrics['common_conditions'] = condition_counts.to_dict()
    else:
        metrics['common_conditions'] = {}
    
    # Recent visits (placeholder - would need visit date column)
    metrics['recent_visits'] = metrics['total_patients']  # Simplified for demo
    
    return metrics


def prepare_chart_data(df: pd.DataFrame, chart_type: str, **kwargs) -> Dict[str, Any]:
    """
    Prepare data for different chart types in a standardized format.
    All UI styles can use this for consistent data visualization.
    """
    if df.empty:
        return {'error': 'No data available for chart'}
    
    try:
        if chart_type == 'age_distribution':
            if 'age' in df.columns:
                age_data = pd.to_numeric(df['age'], errors='coerce').dropna()
                bins = kwargs.get('bins', 10)
                hist_data, bin_edges = pd.cut(age_data, bins=bins, retbins=True)
                
                # Create histogram data
                hist_counts = hist_data.value_counts().sort_index()
                
                return {
                    'data': {
                        'x': [f"{int(interval.left)}-{int(interval.right)}" for interval in hist_counts.index],
                        'y': hist_counts.values.tolist()
                    },
                    'title': 'Age Distribution',
                    'x_title': 'Age Range',
                    'y_title': 'Number of Patients'
                }
            else:
                return {'error': 'Age column not found'}
        
        elif chart_type == 'gender_pie':
            if 'gender' in df.columns:
                gender_counts = df['gender'].value_counts()
                return {
                    'data': {
                        'labels': gender_counts.index.tolist(),
                        'values': gender_counts.values.tolist()
                    },
                    'title': 'Gender Distribution'
                }
            else:
                return {'error': 'Gender column not found'}
        
        elif chart_type == 'trend_line':
            date_col = kwargs.get('date_col', 'date')
            value_col = kwargs.get('value_col', 'value')
            
            if date_col in df.columns and value_col in df.columns:
                # Convert date column to datetime if needed
                df_copy = df.copy()
                df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
                df_clean = df_copy.dropna(subset=[date_col, value_col]).sort_values(date_col)
                
                return {
                    'data': {
                        'x': df_clean[date_col].tolist(),
                        'y': df_clean[value_col].tolist()
                    },
                    'title': kwargs.get('title', 'Trend Over Time'),
                    'x_title': kwargs.get('x_title', 'Date'),
                    'y_title': kwargs.get('y_title', 'Value')
                }
            else:
                return {'error': f'Required columns {date_col}, {value_col} not found'}
        
        else:
            return {'error': f'Chart type {chart_type} not supported'}
    
    except Exception as e:
        return {'error': f'Error preparing chart data: {str(e)}'}


def validate_patient_data(patient_data: dict) -> Tuple[bool, List[str]]:
    """
    Validate patient data structure and content.
    Returns (is_valid, list_of_errors)
    """
    errors = []
    
    if not patient_data:
        errors.append("Patient data is empty")
        return False, errors
    
    # Check for required fields (customize based on your requirements)
    required_fields = ['patient_id']
    for field in required_fields:
        if field not in patient_data:
            errors.append(f"Missing required field: {field}")
    
    # Validate data types
    if 'patient_id' in patient_data:
        try:
            int(patient_data['patient_id'])
        except (ValueError, TypeError):
            errors.append("Patient ID must be numeric")
    
    if 'age' in patient_data:
        try:
            age = float(patient_data['age'])
            if age < 0 or age > 150:
                errors.append("Age must be between 0 and 150")
        except (ValueError, TypeError):
            errors.append("Age must be numeric")
    
    return len(errors) == 0, errors


def clean_text_for_display(text: str, max_length: Optional[int] = None) -> str:
    """
    Clean text for safe display in UI components.
    Removes problematic characters and truncates if needed.
    """
    if not text or pd.isna(text):
        return ""
    
    # Convert to string if not already
    text = str(text)
    
    # Remove or replace problematic characters
    text = text.replace('\x00', '')  # Remove null bytes
    text = text.replace('\r\n', '\n')  # Normalize line endings
    text = text.replace('\r', '\n')
    
    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text


def format_medical_value(value: Any, value_type: str = 'auto') -> str:
    """
    Format medical values for consistent display across all UI styles.
    Handles different data types appropriately for medical context.
    """
    if pd.isna(value) or value is None:
        return "Not recorded"
    
    if value_type == 'auto':
        # Auto-detect type
        if isinstance(value, (int, float)):
            value_type = 'numeric'
        elif isinstance(value, str) and value.replace('.', '').isdigit():
            value_type = 'numeric'
        else:
            value_type = 'text'
    
    if value_type == 'numeric':
        try:
            num_val = float(value)
            if num_val == int(num_val):
                return str(int(num_val))
            else:
                return f"{num_val:.1f}"
        except (ValueError, TypeError):
            return str(value)
    
    elif value_type == 'percentage':
        try:
            return f"{float(value):.1f}%"
        except (ValueError, TypeError):
            return str(value)
    
    elif value_type == 'currency':
        try:
            return f"${float(value):,.2f}"
        except (ValueError, TypeError):
            return str(value)
    
    else:  # text
        return clean_text_for_display(str(value))


def create_medical_disclaimer() -> str:
    """
    Standard medical disclaimer used across all UI styles.
    """
    return """
    ⚠️ **IMPORTANT MEDICAL DISCLAIMER**
    
    This application is for **demonstration purposes only** and is not intended for actual clinical use. 
    All AI-generated content should be reviewed by qualified healthcare professionals. 
    This system is not a substitute for professional medical judgment.
    """


# Cache commonly used data processing functions for performance
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_patient_metrics(patient_data_hash: str, patient_data: pd.DataFrame) -> Dict[str, Any]:
    """Cached version of process_patient_metrics for better performance"""
    return process_patient_metrics(patient_data)


@st.cache_data(ttl=300)
def get_cached_chart_data(data_hash: str, df: pd.DataFrame, chart_type: str, **kwargs) -> Dict[str, Any]:
    """Cached version of prepare_chart_data for better performance"""
    return prepare_chart_data(df, chart_type, **kwargs)
