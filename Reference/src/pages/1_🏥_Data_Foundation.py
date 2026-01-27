"""
Page 1: Data Foundation
=======================

Overview of the PMC patients dataset and demo environment status.
Shows data quality, sample records, and processing pipeline readiness.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from connection_helper import (
    get_snowflake_connection,
    execute_query,
    get_demo_data_status
)

# Page configuration
st.set_page_config(
    page_title="Data Foundation - Healthcare AI Demo",
    page_icon="🏥",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
.data-card {
    background-color: #f8f9fa;
    padding: 1.5rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
    border-left: 4px solid #0066CC;
}

.metric-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 0.5rem 0;
}

.sample-patient {
    background-color: white;
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #dee2e6;
    margin-bottom: 0.5rem;
}

.status-indicator {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 0.5rem;
}

.status-green { background-color: #28a745; }
.status-yellow { background-color: #ffc107; }
.status-red { background-color: #dc3545; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300, show_spinner="Loading PMC patient data...")
def get_pmc_overview(_conn):
    """Get overview statistics of PMC patients data"""
    query = """
    SELECT 
        COUNT(*) as total_patients,
        COUNT(DISTINCT GENDER) as unique_genders,
        COUNT(DISTINCT PMID) as unique_articles,
        COUNT(CASE WHEN SIMILAR_PATIENTS IS NOT NULL THEN 1 END) as patients_with_similar,
        COUNT(CASE WHEN RELEVANT_ARTICLES IS NOT NULL THEN 1 END) as patients_with_articles,
        MIN(PATIENT_ID) as min_patient_id,
        MAX(PATIENT_ID) as max_patient_id
    FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    """
    
    return execute_query(query, _conn)

@st.cache_data(ttl=300)
def get_gender_distribution(_conn):
    """Get gender distribution"""
    query = """
    SELECT 
        GENDER,
        COUNT(*) as count
    FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    WHERE GENDER IS NOT NULL
    GROUP BY GENDER
    ORDER BY count DESC
    """
    
    return execute_query(query, _conn)

@st.cache_data(ttl=300)
def get_age_distribution(_conn):
    """Get age distribution with parsing"""
    query = """
    SELECT 
        AGE,
        COUNT(*) as count
    FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    WHERE AGE IS NOT NULL
    GROUP BY AGE
    ORDER BY count DESC
    LIMIT 20
    """
    return execute_query(query, _conn)

@st.cache_data(ttl=300)
def get_sample_patients(_conn, limit=5):
    """Get sample patient records"""
    query = f"""
    SELECT 
        PATIENT_ID,
        PATIENT_UID,
        PATIENT_TITLE,
        AGE,
        GENDER,
        SUBSTR(PATIENT_NOTES, 1, 300) || '...' as NOTES_PREVIEW,
        ARRAY_SIZE(PARSE_JSON(SIMILAR_PATIENTS)) as SIMILAR_COUNT,
        ARRAY_SIZE(PARSE_JSON(RELEVANT_ARTICLES)) as ARTICLE_COUNT
    FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    WHERE PATIENT_NOTES IS NOT NULL
    ORDER BY PATIENT_ID
    LIMIT {limit}
    """
    return execute_query(query, _conn)

@st.cache_data(ttl=300, show_spinner="Loading processing status...")
def get_processing_status(_conn):
    """Get processing pipeline status"""
    query = """
    SELECT 
        COUNT(*) as processed_count,
        MIN(PROCESSED_TIMESTAMP) as first_processed,
        MAX(PROCESSED_TIMESTAMP) as last_processed
    FROM HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS
    """
    
    return execute_query(query, _conn)

def display_environment_status():
    """Display environment status (simplified for faster loading)"""
    st.markdown("### 🔧 Environment Status")
    data_status = get_demo_data_status()
    
    status_items = [
        ("PMC Patients Data", data_status.get("pmc_patients", {}).get("available", False)),
        ("Patient Analysis Table", data_status.get("patient_analysis", {}).get("available", False)),
        ("Demo Scenarios", data_status.get("demo_scenarios", {}).get("available", False)),
        ("Real-time Logs", data_status.get("realtime_logs", {}).get("available", False))
    ]
    
    for item, available in status_items:
        if available:
            st.markdown(f"<span class='status-indicator status-green'></span>✓ {item}", 
                      unsafe_allow_html=True)
        else:
            st.markdown(f"<span class='status-indicator status-red'></span>✗ {item}", 
                      unsafe_allow_html=True)

def main():
    """Main page function"""
    # Header
    st.title("🏥 Healthcare Data Foundation")
    st.markdown("Explore the PMC patients dataset and verify the demo environment is ready for AI analysis.")
    
    # Get connection
    conn = get_snowflake_connection()
    if conn is None:
        st.error("Unable to connect to Snowflake. Please check your configuration.")
        st.stop()
    
    # Environment status
    display_environment_status()
    
    st.markdown("---")
    
    # Data overview
    st.markdown("## 📊 PMC Patients Dataset Overview")
    
    overview_data = get_pmc_overview(conn)
    if not overview_data.empty:
        row = overview_data.iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Add safe access with fallback
            total_patients = row.get('total_patients', row.get('TOTAL_PATIENTS', 0))
            st.metric("Total Patients", f"{total_patients:,}")
        
        with col2:
            unique_articles = row.get('unique_articles', row.get('UNIQUE_ARTICLES', 0))
            st.metric("Unique Articles", f"{unique_articles:,}")
        
        with col3:
            patients_with_similar = row.get('patients_with_similar', row.get('PATIENTS_WITH_SIMILAR', 0))
            st.metric("With Similar Patients", f"{patients_with_similar:,}")
        
        with col4:
            patients_with_articles = row.get('patients_with_articles', row.get('PATIENTS_WITH_ARTICLES', 0))
            st.metric("With Related Articles", f"{patients_with_articles:,}")
        
        # Additional insights with safe access
        min_patient_id = row.get('min_patient_id', row.get('MIN_PATIENT_ID', 0))
        max_patient_id = row.get('max_patient_id', row.get('MAX_PATIENT_ID', 0))
        total_patients_for_calc = row.get('total_patients', row.get('TOTAL_PATIENTS', 1))
        patients_with_similar_for_calc = row.get('patients_with_similar', row.get('PATIENTS_WITH_SIMILAR', 0))
        patients_with_articles_for_calc = row.get('patients_with_articles', row.get('PATIENTS_WITH_ARTICLES', 0))
        
        st.markdown("""
        <div class="data-card">
        <h4>📈 Dataset Insights</h4>
        <div class="metric-row">
            <span>Patient ID Range:</span>
            <strong>{} - {}</strong>
        </div>
        <div class="metric-row">
            <span>Similar Patient Links:</span>
            <strong>{:.1%}</strong>
        </div>
        <div class="metric-row">
            <span>Literature Links:</span>
            <strong>{:.1%}</strong>
        </div>
        </div>
        """.format(
            min_patient_id,
            max_patient_id,
            patients_with_similar_for_calc / total_patients_for_calc if total_patients_for_calc > 0 else 0,
            patients_with_articles_for_calc / total_patients_for_calc if total_patients_for_calc > 0 else 0
        ), unsafe_allow_html=True)
    
    # Demographics
    st.markdown("---")
    st.markdown("## 👥 Patient Demographics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gender distribution
        gender_data = get_gender_distribution(conn)
        if not gender_data.empty:
            # Handle both uppercase and lowercase column names
            values_col = 'COUNT' if 'COUNT' in gender_data.columns else 'count'
            names_col = 'GENDER' if 'GENDER' in gender_data.columns else 'gender'
            
            fig = px.pie(gender_data, values=values_col, names=names_col, 
                        title="Gender Distribution",
                        color_discrete_map={'M': '#0066CC', 'F': '#FF6B6B'})
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Age distribution (simplified)
        st.markdown("### Age Information")
        st.info("""
        Age data in the PMC dataset is stored in a structured format 
        (e.g., [[11.0, 'year']]). The dataset includes patients across 
        all age ranges, from pediatric to geriatric cases, providing 
        comprehensive coverage for various medical scenarios.
        """)
    
    # Sample patients
    st.markdown("---")
    st.markdown("## 🔍 Sample Patient Records")
    
    sample_patients = get_sample_patients(conn)
    if not sample_patients.empty:
        st.markdown("Explore a few patient records to understand the data structure:")
        
        for _, patient in sample_patients.iterrows():
            with st.expander(f"Patient {patient['PATIENT_ID']}: {patient['PATIENT_TITLE'][:80]}..."):
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    st.markdown(f"**Patient ID:** {patient['PATIENT_ID']}")
                    st.markdown(f"**UID:** {patient['PATIENT_UID']}")
                    st.markdown(f"**Gender:** {patient['GENDER']}")
                    st.markdown(f"**Age:** {patient['AGE']}")
                
                with col2:
                    similar_count = patient['SIMILAR_COUNT'] if pd.notna(patient['SIMILAR_COUNT']) else 0
                    article_count = patient['ARTICLE_COUNT'] if pd.notna(patient['ARTICLE_COUNT']) else 0
                    st.markdown(f"**Similar Patients:** {similar_count}")
                    st.markdown(f"**Related Articles:** {article_count}")
                
                with col3:
                    st.markdown("**Clinical Notes Preview:**")
                    st.text(patient['NOTES_PREVIEW'])
    
    # Processing status
    st.markdown("---")
    st.markdown("## ⚙️ Processing Pipeline Status")
    
    processing_data = get_processing_status(conn)
    if not processing_data.empty and processing_data.iloc[0].get('processed_count', processing_data.iloc[0].get('PROCESSED_COUNT', 0)) > 0:
        row = processing_data.iloc[0]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            processed_count_metric = row.get('processed_count', row.get('PROCESSED_COUNT', 0))
            st.metric("Patients Processed", f"{processed_count_metric:,}")
        
        with col2:
            first_processed = row.get('first_processed', row.get('FIRST_PROCESSED'))
            if pd.notna(first_processed):
                st.metric("First Processed", first_processed.strftime('%Y-%m-%d %H:%M'))
        
        with col3:
            last_processed = row.get('last_processed', row.get('LAST_PROCESSED'))
            if pd.notna(last_processed):
                st.metric("Last Processed", last_processed.strftime('%Y-%m-%d %H:%M'))
        
        # Progress bar with safe access
        total_patients_for_progress = 167034  # Default fallback
        if not overview_data.empty:
            overview_row = overview_data.iloc[0]
            total_patients_for_progress = overview_row.get('total_patients', overview_row.get('TOTAL_PATIENTS', 167034))
        
        processed_count = row.get('processed_count', row.get('PROCESSED_COUNT', 0))
        progress = processed_count / total_patients_for_progress if total_patients_for_progress > 0 else 0
        st.progress(progress, text=f"Processing Progress: {progress:.1%}")
    else:
        st.info("""
        📋 **Pipeline Status**: No patients have been processed yet.
        
        To process patients through the AI pipeline:
        1. Run batch processing via stored procedure: `CALL HEALTHCARE_DEMO.MEDICAL_NOTES.BATCH_PROCESS_PATIENTS(10, 1000)` or use the Demo Guide page
        2. This will populate the analysis tables with AI-generated insights
        3. Processing uses Snowflake Cortex AI for clinical summaries, diagnoses, and more
        """)
    
    # Next steps
    st.markdown("---")
    st.markdown("## 🚀 Next Steps")
    
    st.markdown("""
    <div class="data-card">
    <h4>Ready to Explore AI Capabilities?</h4>
    <p>The PMC patients dataset provides a rich foundation for demonstrating healthcare AI:</p>
    <ul>
        <li>✅ <strong>167,034 patient records</strong> with detailed clinical narratives</li>
        <li>✅ <strong>Pre-computed similarity networks</strong> linking related patients</li>
        <li>✅ <strong>Literature connections</strong> to relevant medical articles</li>
        <li>✅ <strong>Diverse medical conditions</strong> across all specialties</li>
    </ul>
    <p><strong>Navigate to the Clinical Decision Support page to see AI in action!</strong></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()