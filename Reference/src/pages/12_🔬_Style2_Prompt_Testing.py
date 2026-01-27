"""
Style 2: Modern Minimalist - Prompt and Model Testing
===================================================

Contemporary, elegant design with generous whitespace and curated components.
Designed for executive presentations and tech-forward organizations.

Features:
- Contemporary card-based layout
- Generous whitespace and subtle shadows
- Muted, sophisticated color palette
- Clean typography and spacious design
- Premium feel with elegant styling
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
    page_title="Style 2: Modern Minimalist - Prompt Testing",
    page_icon="🔬",
    layout="wide"
)

# Modern Minimalist CSS
st.markdown("""
<style>
/* Modern Minimalist Theme */
.minimalist-card {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    margin: 1.5rem 0;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.1);
    border: 1px solid #f0f0f0;
}

.minimalist-header {
    background: linear-gradient(135deg, #5a5a5a 0%, #3d3d3d 100%);
    color: white;
    padding: 3rem 2rem;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 2rem;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.style-badge {
    position: fixed;
    top: 15px;
    right: 15px;
    background: linear-gradient(45deg, #5a5a5a, #3d3d3d);
    color: white;
    padding: 10px 20px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.9rem;
    z-index: 1000;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.model-card {
    background: #fcfcfc;
    border: 2px solid transparent;
    border-radius: 10px;
    padding: 1.5rem;
    text-align: center;
    transition: all 0.3s ease;
    cursor: pointer;
}

.model-card:hover {
    border-color: #5a5a5a;
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.model-card.selected {
    border-color: #5a5a5a;
    background: #f8f9fa;
}

.prompt-input {
    background: #fcfcfc;
    border: 1px solid #e6e6e6;
    border-radius: 8px;
    padding: 1rem;
    font-size: 1rem;
    transition: border-color 0.3s ease;
}

.prompt-input:focus {
    border-color: #5a5a5a;
    outline: none;
    box-shadow: 0 0 0 3px rgba(90, 90, 90, 0.1);
}

.result-card {
    background: #f8f9fa;
    border-left: 4px solid #5a5a5a;
    border-radius: 8px;
    padding: 2rem;
    margin: 1rem 0;
}

.metric-minimal {
    background: white;
    border-radius: 8px;
    padding: 1.5rem;
    text-align: center;
    border: 1px solid #f0f0f0;
    transition: transform 0.2s ease;
}

.metric-minimal:hover {
    transform: translateY(-2px);
}

.btn-minimal {
    background: #5a5a5a;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.75rem 2rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s ease;
}

.btn-minimal:hover {
    background: #3d3d3d;
    transform: translateY(-1px);
}

.section-title {
    color: #2c3e50;
    font-weight: 300;
    font-size: 1.5rem;
    margin-bottom: 1rem;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# Style indicator
st.markdown('<div class="style-badge">⚫ Style 2: Modern Minimalist</div>', unsafe_allow_html=True)

# Header
st.markdown("""
<div class="minimalist-header">
    <h1 style="font-weight: 300; font-size: 3rem; margin: 0;">🔬 AI Model Testing</h1>
    <h3 style="font-weight: 300; margin-top: 1rem; opacity: 0.9;">Modern Minimalist Interface</h3>
    <p style="font-size: 1.1rem; margin-top: 1rem; opacity: 0.8;">Elegant AI Model Evaluation Platform</p>
</div>
""", unsafe_allow_html=True)

# Medical disclaimer with minimal styling
st.markdown("""
<div class="minimalist-card">
    <h4 style="color: #856404; margin-bottom: 1rem;">⚠️ Clinical Disclaimer</h4>
    <p style="color: #6c757d; line-height: 1.6;">This application serves demonstration purposes exclusively. 
    All AI-generated medical content requires review by qualified healthcare professionals. 
    This system supplements but does not replace professional medical judgment.</p>
</div>
""", unsafe_allow_html=True)

# Spacious main layout
st.markdown('<div style="margin: 2rem 0;">', unsafe_allow_html=True)

col1, col2 = st.columns([3, 2], gap="large")

with col1:
    st.markdown("""
    <div class="minimalist-card">
        <h2 class="section-title">AI Model Selection</h2>
    """, unsafe_allow_html=True)
    
    st.markdown('<div style="margin: 2rem 0;">', unsafe_allow_html=True)
    
    # Model selection with elegant cards
    model_col1, model_col2, model_col3 = st.columns(3, gap="medium")
    
    with model_col1:
        mistral_selected = st.checkbox("", value=True, key="mistral_check", label_visibility="collapsed")
        st.markdown(f"""
        <div class="model-card {'selected' if mistral_selected else ''}">
            <h4 style="color: #5a5a5a; margin-bottom: 0.5rem;">Mistral-Large</h4>
            <p style="color: #6c757d; font-size: 0.9rem; margin-bottom: 1rem;">Clinical Summaries</p>
            <p style="font-size: 0.8rem; color: #8b8b8b;">Advanced medical terminology and detailed clinical analysis</p>
        </div>
        """, unsafe_allow_html=True)
    
    with model_col2:
        mixtral_selected = st.checkbox("", value=True, key="mixtral_check", label_visibility="collapsed")
        st.markdown(f"""
        <div class="model-card {'selected' if mixtral_selected else ''}">
            <h4 style="color: #5a5a5a; margin-bottom: 0.5rem;">Mixtral-8x7B</h4>
            <p style="color: #6c757d; font-size: 0.9rem; margin-bottom: 1rem;">Diagnostic Analysis</p>
            <p style="font-size: 0.8rem; color: #8b8b8b;">Pattern recognition and differential diagnosis expertise</p>
        </div>
        """, unsafe_allow_html=True)
    
    with model_col3:
        llama_selected = st.checkbox("", value=False, key="llama_check", label_visibility="collapsed")
        st.markdown(f"""
        <div class="model-card {'selected' if llama_selected else ''}">
            <h4 style="color: #5a5a5a; margin-bottom: 0.5rem;">LLaMA3.1-70B</h4>
            <p style="color: #6c757d; font-size: 0.9rem; margin-bottom: 1rem;">Education Content</p>
            <p style="font-size: 0.8rem; color: #8b8b8b;">Teaching materials and detailed explanations</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Prompt configuration with elegant spacing
    st.markdown("""
    <div class="minimalist-card">
        <h2 class="section-title">Prompt Configuration</h2>
    """, unsafe_allow_html=True)
    
    # Clean form design
    st.markdown('<div style="margin: 1.5rem 0;">', unsafe_allow_html=True)
    
    prompt_type = st.selectbox(
        "Analysis Type",
        ["Clinical Summary", "Differential Diagnosis", "Treatment Recommendations", "Risk Assessment"],
        help="Select the type of medical analysis to perform"
    )
    
    st.markdown('<div style="margin: 1.5rem 0;">', unsafe_allow_html=True)
    
    patient_data = st.text_area(
        "Patient Information",
        placeholder="Chief Complaint: Chest pain and shortness of breath\n\nHistory: 55-year-old male with hypertension, presenting with acute onset symptoms\n\nVital Signs: BP 150/95, HR 102, RR 24, O2 Sat 94%\n\nSymptoms: Started 2 hours ago, radiating to left arm, associated with diaphoresis",
        height=150,
        help="Enter comprehensive but de-identified patient information",
        key="patient_input"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    custom_instructions = st.text_area(
        "Additional Context (Optional)",
        placeholder="Focus on cardiac causes, include severity assessment, consider immediate interventions",
        height=80,
        help="Provide specific instructions to guide the AI analysis"
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Elegant action buttons
    st.markdown('<div style="margin: 2rem 0; text-align: center;">', unsafe_allow_html=True)
    
    button_col1, button_col2, button_col3 = st.columns([1, 2, 1])
    
    with button_col2:
        if st.button("🚀 Generate Analysis", type="primary", use_container_width=True):
            st.session_state.run_analysis = True
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Results section with elegant styling
    if 'run_analysis' in st.session_state and st.session_state.run_analysis:
        st.markdown("""
        <div class="minimalist-card">
            <h2 class="section-title">Analysis Results</h2>
        """, unsafe_allow_html=True)
        
        # Create elegant tabs for results
        if mistral_selected or mixtral_selected or llama_selected:
            tab_names = []
            if mistral_selected:
                tab_names.append("Mistral-Large")
            if mixtral_selected:
                tab_names.append("Mixtral-8x7B")
            if llama_selected:
                tab_names.append("LLaMA3.1-70B")
            
            tabs = st.tabs(tab_names)
            
            for i, tab_name in enumerate(tab_names):
                with tabs[i]:
                    st.markdown(f"""
                    <div class="result-card">
                        <h4 style="color: #5a5a5a; margin-bottom: 1rem;">🤖 {tab_name} Analysis</h4>
                        
                        <div style="display: flex; gap: 2rem; margin-bottom: 1.5rem;">
                            <div style="text-align: center;">
                                <p style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.25rem;">Processing Time</p>
                                <p style="font-weight: 600; color: #5a5a5a;">2.{i+1}s</p>
                            </div>
                            <div style="text-align: center;">
                                <p style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.25rem;">Confidence</p>
                                <p style="font-weight: 600; color: #5a5a5a;">{87+i}%</p>
                            </div>
                            <div style="text-align: center;">
                                <p style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.25rem;">Response Length</p>
                                <p style="font-weight: 600; color: #5a5a5a;">{245+i*20} words</p>
                            </div>
                        </div>
                        
                        <h5 style="color: #2c3e50; margin-bottom: 1rem;">Generated Response:</h5>
                        <p style="line-height: 1.7; color: #4a4a4a; background: white; padding: 1.5rem; border-radius: 8px; border: 1px solid #f0f0f0;">
                        Based on the comprehensive patient presentation of chest pain and shortness of breath in a 55-year-old male with hypertension, 
                        the clinical assessment suggests several differential diagnoses requiring immediate evaluation and intervention. 
                        The combination of symptoms, patient demographics, and vital signs indicates a high-priority cardiac event...</p>
                        
                        <p style="font-style: italic; color: #6c757d; text-align: center; margin-top: 1rem;">
                        [This represents actual AI model output in production implementation]</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # Performance metrics with minimal design
    st.markdown("""
    <div class="minimalist-card">
        <h2 class="section-title">Performance Metrics</h2>
    """, unsafe_allow_html=True)
    
    # Elegant metrics
    st.markdown("""
    <div class="metric-minimal" style="margin-bottom: 1rem;">
        <h3 style="color: #5a5a5a; margin-bottom: 0.5rem;">Avg Response Time</h3>
        <h2 style="color: #2c3e50; font-weight: 300; font-size: 2.5rem; margin: 0;">2.1s</h2>
        <p style="color: #6c757d; margin-top: 0.5rem; font-size: 0.9rem;">Across all models</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="metric-minimal" style="margin-bottom: 1rem;">
        <h3 style="color: #5a5a5a; margin-bottom: 0.5rem;">Success Rate</h3>
        <h2 style="color: #28a745; font-weight: 300; font-size: 2.5rem; margin: 0;">98.5%</h2>
        <p style="color: #6c757d; margin-top: 0.5rem; font-size: 0.9rem;">Valid responses</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="metric-minimal">
        <h3 style="color: #5a5a5a; margin-bottom: 0.5rem;">Tests Today</h3>
        <h2 style="color: #2c3e50; font-weight: 300; font-size: 2.5rem; margin: 0;">47</h2>
        <p style="color: #6c757d; margin-top: 0.5rem; font-size: 0.9rem;">All prompt types</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Model comparison with clean chart
    st.markdown("""
    <div class="minimalist-card">
        <h2 class="section-title">Model Comparison</h2>
    """, unsafe_allow_html=True)
    
    # Clean, minimal chart
    comparison_data = {
        'Model': ['Mistral-Large', 'Mixtral-8x7B', 'LLaMA3.1-70B'],
        'Response Time': [2.1, 1.8, 2.5],
        'Confidence': [0.89, 0.85, 0.82]
    }
    
    fig = px.bar(
        x=comparison_data['Model'],
        y=comparison_data['Response Time'],
        title="",
        color_discrete_sequence=['#5a5a5a']
    )
    fig.update_layout(
        template="plotly_white",
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#4a4a4a'),
        margin=dict(l=20, r=20, t=20, b=20)
    )
    fig.update_traces(marker_color='#5a5a5a', opacity=0.8)
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Clean action buttons
    st.markdown("""
    <div class="minimalist-card">
        <h2 class="section-title">Actions</h2>
    """, unsafe_allow_html=True)
    
    if st.button("📊 Export Results", use_container_width=True):
        st.success("✅ Results exported successfully")
    
    if st.button("🔍 Detailed Analysis", use_container_width=True):
        st.info("📈 Navigate to AI Model Performance for insights")
    
    if st.button("💡 Optimization Tips", use_container_width=True):
        st.info("🎯 AI-powered prompt suggestions available")
    
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Minimal footer
st.markdown('<div style="margin-top: 3rem; text-align: center; color: #6c757d; font-size: 0.9rem;">', unsafe_allow_html=True)
st.markdown("---")
st.markdown(f"**Modern Minimalist Style** • **Prompt & Model Testing** • **Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
st.markdown('</div>', unsafe_allow_html=True)

# Minimal sidebar
with st.sidebar:
    st.markdown("### 🔬 Prompt Testing")
    st.markdown("*Modern Minimalist Style*")
    
    st.markdown("---")
    
    st.markdown("""
    **Style Features:**
    - ✨ Contemporary card-based design
    - 🎨 Muted, sophisticated colors  
    - 📏 Generous whitespace
    - 🎯 Clean typography
    - 💎 Premium aesthetic
    """)
    
    st.markdown("---")
    
    st.markdown("**Compare styles:**")
    st.markdown("• Style1: Corporate Standard")
    st.markdown("• Style3: Data-Dense Powerhouse")
