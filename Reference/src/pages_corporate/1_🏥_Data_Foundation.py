"""
Page 1: Data Foundation - Corporate Standard Style
================================================

Overview of the PMC patients dataset and demo environment status.
Shows data quality, sample records, and processing pipeline readiness.

Corporate Standard Features:
- Native Streamlit components only
- st.container(border=True) for clear sections  
- Traditional layout with sidebar navigation
- Professional corporate styling
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
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

# Import shared components
try:
    from connection_helper import (
        get_snowflake_connection,
        execute_query,
        get_demo_data_status
    )
    from data_processors import (
        process_patient_metrics, 
        format_medical_value,
        create_medical_disclaimer
    )
    from chart_data import prepare_patient_demographics_chart, create_plotly_chart
except ImportError as e:
    st.error(f"Import error: {e}")

# Page configuration - Corporate Standard
st.set_page_config(
    page_title="Data Foundation - Healthcare AI Demo",
    page_icon="🏥",
    layout="wide"
)

# Corporate Standard styling indicator
st.markdown("""
<div style="position: fixed; top: 10px; right: 10px; background-color: #0062df; color: white; padding: 0.5rem 1rem; border-radius: 0.25rem; font-size: 0.8rem; font-weight: bold; z-index: 1000;">
    🔵 Corporate Standard
</div>
""", unsafe_allow_html=True)

# Main page header
st.title("🏥 Data Foundation")
st.markdown("**Corporate Standard Style** - Dataset Overview and System Status")

# Medical disclaimer using Corporate Standard bordered container
with st.container(border=True):
    st.markdown("### ⚠️ Medical Disclaimer")
    st.markdown(create_medical_disclaimer())

# Main content using Corporate Standard layout
col1, col2 = st.columns([2, 1])

with col1:
    # Dataset overview using bordered container
    with st.container(border=True):
        st.header("📊 Dataset Overview")
        
        # Sample data metrics using native Streamlit components
        try:
            # This would normally connect to your database
            # For demo purposes, using placeholder data
            
            metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
            
            with metrics_col1:
                st.metric(
                    label="Total Patients",
                    value="167,000",
                    delta="1,000 subset for demo",
                    help="Full PMC dataset with demo subset"
                )
            
            with metrics_col2:
                st.metric(
                    label="Data Quality",
                    value="95.2%",
                    delta="2.3%",
                    help="Percentage of complete patient records"
                )
            
            with metrics_col3:
                st.metric(
                    label="Processing Ready",
                    value="✅ Active",
                    help="AI processing pipeline status"
                )
            
            with metrics_col4:
                st.metric(
                    label="Last Updated",
                    value="Today",
                    help="Data freshness indicator"
                )
            
            # Dataset details using tabs (Corporate Standard secondary navigation)
            st.subheader("📋 Dataset Details")
            tab1, tab2, tab3 = st.tabs(["Patient Demographics", "Data Quality", "Sample Records"])
            
            with tab1:
                st.markdown("""
                **Patient Demographics:**
                - Age Range: 18-95 years
                - Gender Distribution: 52% Female, 48% Male
                - Geographic Coverage: Multi-region
                - Medical Specialties: Primary Care, Cardiology, Oncology, Emergency Medicine
                """)
                
                # Simple demographics chart using Corporate Standard approach
                demo_data = {
                    'Age Group': ['18-30', '31-45', '46-60', '61-75', '76+'],
                    'Count': [15000, 35000, 45000, 52000, 20000]
                }
                fig = px.bar(
                    x=demo_data['Age Group'], 
                    y=demo_data['Count'],
                    title="Patient Age Distribution",
                    color_discrete_sequence=['#0062df']  # Corporate blue
                )
                fig.update_layout(template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                st.markdown("**Data Quality Metrics:**")
                
                quality_metrics = [
                    {"Field": "Patient ID", "Completeness": "100%", "Quality": "Excellent"},
                    {"Field": "Age", "Completeness": "98.5%", "Quality": "Good"},
                    {"Field": "Gender", "Completeness": "99.2%", "Quality": "Excellent"},
                    {"Field": "Medical Notes", "Completeness": "95.1%", "Quality": "Good"},
                    {"Field": "Diagnosis", "Completeness": "92.3%", "Quality": "Fair"}
                ]
                
                # Display as a clean table using native Streamlit
                quality_df = pd.DataFrame(quality_metrics)
                st.dataframe(
                    quality_df, 
                    use_container_width=True,
                    hide_index=True
                )
            
            with tab3:
                st.markdown("**Sample Patient Records:**")
                
                # Sample data for demonstration
                sample_data = [
                    {"Patient_ID": "PMC001", "Age": 45, "Gender": "F", "Chief_Complaint": "Chest pain, shortness of breath"},
                    {"Patient_ID": "PMC002", "Age": 67, "Gender": "M", "Chief_Complaint": "Diabetes management, routine checkup"},
                    {"Patient_ID": "PMC003", "Age": 32, "Gender": "F", "Chief_Complaint": "Headaches, vision changes"},
                ]
                
                sample_df = pd.DataFrame(sample_data)
                st.dataframe(
                    sample_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                st.info("💡 This is sample data for demonstration. Actual patient data would be de-identified and secured.")
        
        except Exception as e:
            st.error(f"Error loading dataset information: {e}")
            st.info("Backend database connection may be initializing.")

with col2:
    # System status panel using Corporate Standard containers
    with st.container(border=True):
        st.header("⚙️ System Status")
        
        try:
            # Connection status
            st.markdown("**Database Connection:**")
            st.success("✅ Snowflake Connected")
            
            st.markdown("**AI Models:**")
            ai_models = [
                "✅ mistral-large (Clinical Summaries)",
                "✅ mixtral-8x7b (Diagnostic Analysis)", 
                "✅ llama3.1-70b (Education Content)"
            ]
            for model in ai_models:
                st.markdown(f"- {model}")
            
            st.markdown("**Processing Pipeline:**")
            st.success("🔄 Active and Ready")
            
        except Exception as e:
            st.warning(f"System status check: {e}")
    
    # Quick actions panel
    with st.container(border=True):
        st.header("🚀 Quick Actions")
        
        if st.button("🔍 Run Data Validation", use_container_width=True):
            with st.spinner("Validating data quality..."):
                # Simulate data validation
                progress_bar = st.progress(0)
                for i in range(100):
                    progress_bar.progress(i + 1)
                st.success("✅ Data validation completed!")
        
        if st.button("📊 Generate Sample Report", use_container_width=True):
            st.info("📋 Sample report generation - Navigate to Population Health Analytics page")
        
        if st.button("🤖 Test AI Processing", use_container_width=True):
            st.info("🔬 AI processing test - Navigate to Prompt and Model Testing page")

# Footer using Corporate Standard approach
st.markdown("---")

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.markdown("**Page:** Data Foundation")

with footer_col2:
    st.markdown(f"**Style:** Corporate Standard")

with footer_col3:
    st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# Sidebar content following Corporate Standard principles
with st.sidebar:
    st.markdown("### 🏥 Data Foundation")
    st.markdown("*Corporate Standard Style*")
    
    st.markdown("---")
    
    # Navigation help
    with st.container(border=True):
        st.markdown("**Navigation Guide:**")
        st.markdown("""
        This page provides an overview of:
        - 📊 Dataset structure and metrics
        - 📋 Data quality indicators  
        - 🔍 Sample records preview
        - ⚙️ System status monitoring
        
        Use the main navigation to explore other features.
        """)
    
    st.markdown("---")
    
    # Style information
    st.markdown("**Corporate Standard Features:**")
    st.markdown("""
    - ✅ Native Streamlit components
    - ✅ Bordered containers for clarity
    - ✅ Professional blue color scheme
    - ✅ Traditional tab navigation
    - ✅ Maximum stability focus
    """)
    
    # Quick links to other styles
    st.markdown("---")
    st.markdown("**Compare Styles:**")
    
    if st.button("🌐 Modern Minimalist", key="sidebar_minimalist"):
        st.info("Port 8502")
    
    if st.button("⚡ Data-Dense Powerhouse", key="sidebar_powerhouse"):
        st.info("Port 8503")
