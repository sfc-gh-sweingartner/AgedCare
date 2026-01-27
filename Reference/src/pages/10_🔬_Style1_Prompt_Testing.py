"""
Style 1: Corporate Standard - Prompt and Model Testing
====================================================

Professional, stable interface using native Streamlit components only.
Designed for conservative healthcare organizations and regulatory environments.

Features:
- Native Streamlit components exclusively
- Professional blue color scheme
- Clear bordered sections (CSS-based for compatibility)
- Traditional form layouts
- Maximum stability
"""

import streamlit as st
import pandas as pd
import json
import plotly.express as px
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

# Page configuration
st.set_page_config(
    page_title="Style 1: Corporate Standard - Prompt Testing",
    page_icon="🔬",
    layout="wide"
)

# Corporate Standard CSS (compatible with older Streamlit)
st.markdown("""
<style>
/* Corporate Standard Theme */
.corporate-container {
    border: 2px solid #0062df;
    border-radius: 8px;
    padding: 20px;
    margin: 10px 0;
    background-color: #f8f9fa;
}

.corporate-header {
    background: linear-gradient(90deg, #0062df 0%, #004499 100%);
    color: white;
    padding: 15px;
    border-radius: 8px;
    text-align: center;
    margin-bottom: 20px;
}

.style-badge {
    position: fixed;
    top: 10px;
    right: 10px;
    background-color: #0062df;
    color: white;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
    z-index: 1000;
}

.metric-box {
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    margin: 10px 0;
}

.prompt-result {
    background: #e3f2fd;
    border-left: 4px solid #0062df;
    padding: 15px;
    margin: 10px 0;
    border-radius: 4px;
}
</style>
""", unsafe_allow_html=True)

# Style indicator
st.markdown('<div class="style-badge">🔵 Style 1: Corporate Standard</div>', unsafe_allow_html=True)

# Header
st.markdown("""
<div class="corporate-header">
    <h1>🔬 Prompt and Model Testing</h1>
    <h3>Style 1: Corporate Standard</h3>
    <p>Professional AI Model Evaluation Interface</p>
</div>
""", unsafe_allow_html=True)

# Medical disclaimer
st.markdown("""
<div class="corporate-container">
    <h4>⚠️ Medical Disclaimer</h4>
    <p>This application is for <strong>demonstration purposes only</strong> and is not intended for actual clinical use. 
    All AI-generated content should be reviewed by qualified healthcare professionals. 
    This system is not a substitute for professional medical judgment.</p>
</div>
""", unsafe_allow_html=True)

# Main content layout
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('<div class="corporate-container">', unsafe_allow_html=True)
    st.header("🤖 AI Model Comparison")
    
    # Model selection using traditional approach
    st.subheader("Select Models to Compare")
    
    # Model selection checkboxes in a traditional layout
    model_col1, model_col2, model_col3 = st.columns(3)
    
    with model_col1:
        mistral_selected = st.checkbox("mistral-large", value=True, help="Best for clinical summaries")
        st.markdown("**Use Case:** Clinical Summaries")
        st.markdown("**Strengths:** Medical terminology, detailed analysis")
    
    with model_col2:
        mixtral_selected = st.checkbox("mixtral-8x7b", value=True, help="Best for diagnostic analysis")
        st.markdown("**Use Case:** Diagnostic Analysis")  
        st.markdown("**Strengths:** Pattern recognition, differential diagnosis")
    
    with model_col3:
        llama_selected = st.checkbox("llama3.1-70b", value=False, help="Best for education content")
        st.markdown("**Use Case:** Education Content")
        st.markdown("**Strengths:** Teaching materials, explanations")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Prompt testing section
    st.markdown('<div class="corporate-container">', unsafe_allow_html=True)
    st.header("📝 Prompt Engineering")
    
    # Traditional form layout
    st.subheader("Test Prompt Configuration")
    
    # Prompt type selection
    prompt_type = st.selectbox(
        "Select Prompt Type",
        ["Clinical Summary", "Differential Diagnosis", "Treatment Recommendations", "Risk Assessment"],
        help="Choose the type of medical analysis to perform"
    )
    
    # Sample patient data input
    st.subheader("Patient Data Input")
    patient_data = st.text_area(
        "Enter Patient Information",
        placeholder="Chief Complaint: Chest pain and shortness of breath\nHistory: 55-year-old male with hypertension\nSymptoms: Started 2 hours ago, radiating to left arm",
        height=120,
        help="Enter realistic but de-identified patient information for testing"
    )
    
    # Prompt customization
    st.subheader("Prompt Customization")
    custom_instructions = st.text_area(
        "Additional Instructions (Optional)",
        placeholder="Focus on cardiac causes, include severity assessment",
        height=80
    )
    
    # Traditional button layout
    test_col1, test_col2, test_col3 = st.columns(3)
    
    with test_col1:
        if st.button("🚀 Run Test", type="primary", use_container_width=True):
            st.session_state.run_test = True
    
    with test_col2:
        if st.button("💾 Save Configuration", use_container_width=True):
            st.success("✅ Configuration saved!")
    
    with test_col3:
        if st.button("🔄 Clear All", use_container_width=True):
            st.session_state.clear()
            st.experimental_rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Results section
    if 'run_test' in st.session_state and st.session_state.run_test:
        st.markdown('<div class="corporate-container">', unsafe_allow_html=True)
        st.header("📊 Test Results")
        
        # Create tabs for different models
        if mistral_selected or mixtral_selected or llama_selected:
            tab_names = []
            if mistral_selected:
                tab_names.append("Mistral-Large")
            if mixtral_selected:
                tab_names.append("Mixtral-8x7b")
            if llama_selected:
                tab_names.append("LLaMA3.1-70b")
            
            tabs = st.tabs(tab_names)
            
            for i, tab_name in enumerate(tab_names):
                with tabs[i]:
                    st.markdown(f"""
                    <div class="prompt-result">
                        <h4>🤖 {tab_name} Response</h4>
                        <p><strong>Prompt Type:</strong> {prompt_type}</p>
                        <p><strong>Processing Time:</strong> 2.3 seconds</p>
                        <p><strong>Confidence Score:</strong> 0.87</p>
                        
                        <h5>Generated Response:</h5>
                        <p>Based on the patient presentation of chest pain and shortness of breath in a 55-year-old male with hypertension, 
                        the clinical picture suggests several possible diagnoses that require immediate evaluation...</p>
                        
                        <p><em>[This would be the actual AI model response in a real implementation]</em></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Performance metrics in traditional layout
                    perf_col1, perf_col2, perf_col3 = st.columns(3)
                    
                    with perf_col1:
                        st.metric("Response Length", "245 words")
                    with perf_col2:
                        st.metric("Medical Terms", "18 identified")
                    with perf_col3:
                        st.metric("Confidence", "87%")
        
        st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # Performance dashboard
    st.markdown('<div class="corporate-container">', unsafe_allow_html=True)
    st.header("📈 Performance Metrics")
    
    # Traditional metrics display
    st.markdown("""
    <div class="metric-box">
        <h3>Average Response Time</h3>
        <h2 style="color: #0062df;">2.1s</h2>
        <p>Across all models</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="metric-box">
        <h3>Success Rate</h3>
        <h2 style="color: #28a745;">98.5%</h2>
        <p>Valid responses generated</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="metric-box">
        <h3>Tests Run Today</h3>
        <h2 style="color: #0062df;">47</h2>
        <p>Across all prompt types</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Model comparison chart
    st.markdown('<div class="corporate-container">', unsafe_allow_html=True)
    st.header("📊 Model Comparison")
    
    # Simple comparison data
    comparison_data = {
        'Model': ['Mistral-Large', 'Mixtral-8x7b', 'LLaMA3.1-70b'],
        'Avg Response Time (s)': [2.1, 1.8, 2.5],
        'Confidence Score': [0.89, 0.85, 0.82]
    }
    
    # Traditional chart with corporate colors
    fig = px.bar(
        x=comparison_data['Model'],
        y=comparison_data['Avg Response Time (s)'],
        title="Average Response Time by Model",
        color_discrete_sequence=['#0062df']
    )
    fig.update_layout(template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Quick actions
    st.markdown('<div class="corporate-container">', unsafe_allow_html=True)
    st.header("🔧 Quick Actions")
    
    if st.button("📋 Export Results", use_container_width=True):
        st.info("📊 Results exported to CSV")
    
    if st.button("🔍 Detailed Analysis", use_container_width=True):
        st.info("📈 Navigate to AI Model Performance page for detailed analysis")
    
    if st.button("💡 Prompt Suggestions", use_container_width=True):
        st.info("🎯 AI-generated prompt optimization suggestions")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.markdown("**Style:** Corporate Standard")
with footer_col2:
    st.markdown("**Page:** Prompt & Model Testing")
with footer_col3:
    st.markdown(f"**Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# Sidebar info
with st.sidebar:
    st.markdown("### 🔬 Prompt Testing")
    st.markdown("*Corporate Standard Style*")
    
    st.markdown("---")
    
    st.markdown("""
    **Style Features:**
    - ✅ Native Streamlit components only
    - ✅ Professional blue color scheme
    - ✅ Traditional form layouts
    - ✅ Clear bordered sections
    - ✅ Maximum compatibility
    """)
    
    st.markdown("---")
    
    st.markdown("**Compare with other styles:**")
    st.markdown("• Style2: Modern Minimalist")
    st.markdown("• Style3: Data-Dense Powerhouse")
