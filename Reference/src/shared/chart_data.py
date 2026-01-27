"""
Shared Chart Data Preparation Functions
=======================================

Common visualization data preparation functions used across all three UI styles.
Provides consistent data formatting for charts regardless of the visualization library used.
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Any, Tuple
import json
from datetime import datetime, timedelta
import streamlit as st


def prepare_patient_demographics_chart(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Prepare patient demographics data for visualization.
    Returns data in format suitable for any charting library.
    """
    if df.empty:
        return {'error': 'No demographic data available'}
    
    charts_data = {}
    
    # Age distribution
    if 'age' in df.columns:
        age_data = pd.to_numeric(df['age'], errors='coerce').dropna()
        if not age_data.empty:
            # Create age bins
            bins = [0, 18, 30, 45, 60, 75, 100]
            labels = ['0-17', '18-29', '30-44', '45-59', '60-74', '75+']
            age_groups = pd.cut(age_data, bins=bins, labels=labels, right=False)
            age_counts = age_groups.value_counts().sort_index()
            
            charts_data['age_distribution'] = {
                'type': 'bar',
                'data': {
                    'x': age_counts.index.tolist(),
                    'y': age_counts.values.tolist()
                },
                'layout': {
                    'title': 'Patient Age Distribution',
                    'x_title': 'Age Groups',
                    'y_title': 'Number of Patients'
                }
            }
    
    # Gender distribution
    if 'gender' in df.columns:
        gender_counts = df['gender'].value_counts()
        charts_data['gender_distribution'] = {
            'type': 'pie',
            'data': {
                'labels': gender_counts.index.tolist(),
                'values': gender_counts.values.tolist()
            },
            'layout': {
                'title': 'Gender Distribution'
            }
        }
    
    return charts_data


def prepare_clinical_metrics_chart(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Prepare clinical metrics data for dashboard visualization.
    """
    if df.empty:
        return {'error': 'No clinical data available'}
    
    charts_data = {}
    
    # Risk score distribution
    if 'risk_score' in df.columns:
        risk_data = pd.to_numeric(df['risk_score'], errors='coerce').dropna()
        if not risk_data.empty:
            # Create risk categories
            risk_categories = pd.cut(
                risk_data, 
                bins=[0, 3, 6, 8, 10], 
                labels=['Low', 'Medium', 'High', 'Critical'],
                right=False
            )
            risk_counts = risk_categories.value_counts()
            
            charts_data['risk_distribution'] = {
                'type': 'bar',
                'data': {
                    'x': risk_counts.index.tolist(),
                    'y': risk_counts.values.tolist()
                },
                'layout': {
                    'title': 'Risk Score Distribution',
                    'x_title': 'Risk Level',
                    'y_title': 'Number of Patients',
                    'colors': ['green', 'yellow', 'orange', 'red']
                }
            }
    
    # Length of stay analysis
    if 'length_of_stay' in df.columns:
        los_data = pd.to_numeric(df['length_of_stay'], errors='coerce').dropna()
        if not los_data.empty:
            # Create LOS bins
            los_bins = [0, 1, 3, 7, 14, float('inf')]
            los_labels = ['Same Day', '1-2 Days', '3-6 Days', '1-2 Weeks', '2+ Weeks']
            los_groups = pd.cut(los_data, bins=los_bins, labels=los_labels, right=False)
            los_counts = los_groups.value_counts()
            
            charts_data['length_of_stay'] = {
                'type': 'bar',
                'data': {
                    'x': los_counts.index.tolist(),
                    'y': los_counts.values.tolist()
                },
                'layout': {
                    'title': 'Length of Stay Distribution',
                    'x_title': 'Stay Duration',
                    'y_title': 'Number of Patients'
                }
            }
    
    return charts_data


def prepare_ai_performance_chart(ai_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Prepare AI model performance data for visualization.
    """
    if not ai_results:
        return {'error': 'No AI performance data available'}
    
    charts_data = {}
    
    # Confidence score distribution
    confidence_scores = []
    processing_times = []
    model_types = []
    
    for result in ai_results:
        if 'confidence_score' in result:
            confidence_scores.append(result['confidence_score'])
        if 'processing_time' in result:
            processing_times.append(result['processing_time'])
        if 'model' in result:
            model_types.append(result['model'])
    
    if confidence_scores:
        # Confidence distribution
        confidence_bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
        confidence_labels = ['Very Low', 'Low', 'Medium', 'High', 'Very High']
        conf_groups = pd.cut(confidence_scores, bins=confidence_bins, labels=confidence_labels)
        conf_counts = conf_groups.value_counts()
        
        charts_data['confidence_distribution'] = {
            'type': 'bar',
            'data': {
                'x': conf_counts.index.tolist(),
                'y': conf_counts.values.tolist()
            },
            'layout': {
                'title': 'AI Confidence Score Distribution',
                'x_title': 'Confidence Level',
                'y_title': 'Number of Analyses'
            }
        }
    
    if processing_times:
        # Processing time histogram
        time_data = pd.Series(processing_times)
        charts_data['processing_times'] = {
            'type': 'histogram',
            'data': {
                'values': processing_times
            },
            'layout': {
                'title': 'AI Processing Time Distribution',
                'x_title': 'Processing Time (seconds)',
                'y_title': 'Frequency'
            }
        }
    
    if model_types:
        # Model usage distribution
        model_counts = pd.Series(model_types).value_counts()
        charts_data['model_usage'] = {
            'type': 'pie',
            'data': {
                'labels': model_counts.index.tolist(),
                'values': model_counts.values.tolist()
            },
            'layout': {
                'title': 'AI Model Usage Distribution'
            }
        }
    
    return charts_data


def prepare_cost_analysis_chart(cost_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Prepare cost analysis data for financial visualization.
    """
    if cost_data.empty:
        return {'error': 'No cost data available'}
    
    charts_data = {}
    
    # Cost by category
    cost_columns = [col for col in cost_data.columns if 'cost' in col.lower()]
    if cost_columns:
        total_costs = cost_data[cost_columns].sum()
        charts_data['cost_breakdown'] = {
            'type': 'pie',
            'data': {
                'labels': [col.replace('_cost', '').replace('_', ' ').title() for col in total_costs.index],
                'values': total_costs.values.tolist()
            },
            'layout': {
                'title': 'Cost Breakdown by Category'
            }
        }
    
    # Cost over time (if date column available)
    if 'admission_date' in cost_data.columns and 'total_cost' in cost_data.columns:
        # Group by month
        cost_data['admission_date'] = pd.to_datetime(cost_data['admission_date'], errors='coerce')
        monthly_costs = cost_data.groupby(cost_data['admission_date'].dt.to_period('M'))['total_cost'].sum()
        
        charts_data['monthly_costs'] = {
            'type': 'line',
            'data': {
                'x': [str(period) for period in monthly_costs.index],
                'y': monthly_costs.values.tolist()
            },
            'layout': {
                'title': 'Monthly Cost Trends',
                'x_title': 'Month',
                'y_title': 'Total Cost ($)'
            }
        }
    
    return charts_data


def create_plotly_chart(chart_config: Dict[str, Any]) -> go.Figure:
    """
    Convert chart configuration to Plotly figure.
    Used by all UI styles that prefer Plotly visualization.
    """
    chart_type = chart_config.get('type', 'bar')
    data = chart_config.get('data', {})
    layout = chart_config.get('layout', {})
    
    fig = None
    
    if chart_type == 'bar':
        fig = px.bar(
            x=data.get('x', []),
            y=data.get('y', []),
            title=layout.get('title', ''),
            labels={'x': layout.get('x_title', ''), 'y': layout.get('y_title', '')}
        )
        
        # Apply custom colors if provided
        if 'colors' in layout:
            fig.update_traces(marker_color=layout['colors'])
    
    elif chart_type == 'pie':
        fig = px.pie(
            values=data.get('values', []),
            names=data.get('labels', []),
            title=layout.get('title', '')
        )
    
    elif chart_type == 'line':
        fig = px.line(
            x=data.get('x', []),
            y=data.get('y', []),
            title=layout.get('title', ''),
            labels={'x': layout.get('x_title', ''), 'y': layout.get('y_title', '')}
        )
    
    elif chart_type == 'histogram':
        fig = px.histogram(
            x=data.get('values', []),
            title=layout.get('title', ''),
            labels={'x': layout.get('x_title', ''), 'y': layout.get('y_title', 'Frequency')}
        )
    
    elif chart_type == 'scatter':
        fig = px.scatter(
            x=data.get('x', []),
            y=data.get('y', []),
            title=layout.get('title', ''),
            labels={'x': layout.get('x_title', ''), 'y': layout.get('y_title', '')}
        )
    
    else:
        # Default to bar chart
        fig = px.bar(
            x=data.get('x', []),
            y=data.get('y', []),
            title=layout.get('title', 'Chart')
        )
    
    if fig:
        # Apply consistent styling
        fig.update_layout(
            template="plotly_white",
            title_font_size=16,
            showlegend=True if chart_type == 'pie' else False
        )
    
    return fig


def prepare_dashboard_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Prepare summary statistics for dashboard display.
    Returns key metrics that work across all UI styles.
    """
    if df.empty:
        return {
            'total_patients': 0,
            'avg_age': 0,
            'high_risk_patients': 0,
            'total_cost': 0,
            'avg_los': 0
        }
    
    summary = {}
    
    # Basic counts
    summary['total_patients'] = len(df)
    
    # Age statistics
    if 'age' in df.columns:
        age_data = pd.to_numeric(df['age'], errors='coerce').dropna()
        summary['avg_age'] = round(age_data.mean(), 1) if not age_data.empty else 0
    else:
        summary['avg_age'] = 0
    
    # Risk assessment
    if 'risk_score' in df.columns:
        risk_data = pd.to_numeric(df['risk_score'], errors='coerce').dropna()
        summary['high_risk_patients'] = len(risk_data[risk_data >= 7]) if not risk_data.empty else 0
    else:
        summary['high_risk_patients'] = 0
    
    # Cost analysis
    cost_columns = [col for col in df.columns if 'cost' in col.lower()]
    if cost_columns:
        total_cost = df[cost_columns].sum().sum()
        summary['total_cost'] = round(total_cost, 2)
    else:
        summary['total_cost'] = 0
    
    # Length of stay
    if 'length_of_stay' in df.columns:
        los_data = pd.to_numeric(df['length_of_stay'], errors='coerce').dropna()
        summary['avg_los'] = round(los_data.mean(), 1) if not los_data.empty else 0
    else:
        summary['avg_los'] = 0
    
    return summary


def create_medical_timeline_data(patient_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Prepare medical timeline data for visualization.
    Used for patient history and treatment progression displays.
    """
    if not patient_events:
        return {'error': 'No timeline events available'}
    
    # Sort events by date
    sorted_events = sorted(
        patient_events, 
        key=lambda x: pd.to_datetime(x.get('date', '1900-01-01'), errors='coerce')
    )
    
    timeline_data = {
        'events': [],
        'categories': set(),
        'date_range': None
    }
    
    for event in sorted_events:
        event_date = pd.to_datetime(event.get('date'), errors='coerce')
        if pd.isna(event_date):
            continue
        
        category = event.get('category', 'General')
        timeline_data['categories'].add(category)
        
        timeline_data['events'].append({
            'date': event_date.strftime('%Y-%m-%d'),
            'title': event.get('title', 'Medical Event'),
            'description': event.get('description', ''),
            'category': category,
            'severity': event.get('severity', 'Medium')  # Low, Medium, High, Critical
        })
    
    # Convert categories to list for JSON serialization
    timeline_data['categories'] = list(timeline_data['categories'])
    
    # Calculate date range
    if timeline_data['events']:
        dates = [pd.to_datetime(event['date']) for event in timeline_data['events']]
        timeline_data['date_range'] = {
            'start': min(dates).strftime('%Y-%m-%d'),
            'end': max(dates).strftime('%Y-%m-%d')
        }
    
    return timeline_data


@st.cache_data(ttl=300)
def cached_chart_preparation(data_hash: str, chart_type: str, data_json: str) -> Dict[str, Any]:
    """
    Cached version of chart data preparation for performance.
    
    Args:
        data_hash: Hash of the input data for cache key
        chart_type: Type of chart to prepare
        data_json: JSON string of the data
    
    Returns:
        Prepared chart data
    """
    try:
        data = json.loads(data_json)
        df = pd.DataFrame(data)
        
        if chart_type == 'demographics':
            return prepare_patient_demographics_chart(df)
        elif chart_type == 'clinical':
            return prepare_clinical_metrics_chart(df)
        elif chart_type == 'cost':
            return prepare_cost_analysis_chart(df)
        else:
            return {'error': f'Unknown chart type: {chart_type}'}
    
    except Exception as e:
        return {'error': f'Chart preparation failed: {str(e)}'}


def get_color_scheme(style: str = 'corporate') -> Dict[str, str]:
    """
    Get color schemes for different UI styles.
    
    Args:
        style: UI style ('corporate', 'minimalist', 'powerhouse')
    
    Returns:
        Color scheme dictionary
    """
    color_schemes = {
        'corporate': {
            'primary': '#0066CC',
            'secondary': '#f0f2f6',
            'success': '#28a745',
            'warning': '#ffc107',
            'danger': '#dc3545',
            'info': '#17a2b8'
        },
        'minimalist': {
            'primary': '#5a5a5a',
            'secondary': '#f0f2f6',
            'success': '#6c757d',
            'warning': '#6f6f6f',
            'danger': '#495057',
            'info': '#343a40'
        },
        'powerhouse': {
            'primary': '#1c83e1',
            'secondary': '#262730',
            'success': '#28a745',
            'warning': '#ffc107',
            'danger': '#dc3545',
            'info': '#17a2b8'
        }
    }
    
    return color_schemes.get(style, color_schemes['corporate'])
