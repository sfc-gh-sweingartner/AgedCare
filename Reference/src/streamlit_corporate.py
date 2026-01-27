"""
Healthcare AI Demo - Corporate Standard Style
===========================================

Professional, stable interface using native Streamlit components only.
Designed for conservative healthcare organizations and regulatory environments.

Style Features (Streamlit 1.49+):
- Native Streamlit components exclusively  
- st.container(border=True) for clear sections
- Corporate blue color scheme via config.toml
- Traditional sidebar navigation
- Maximum stability and reliability
"""

import streamlit as st
import sys
import os
from datetime import datetime

# Add src and shared directories to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shared'))

# Corporate Standard Style Configuration - Following Style Guide
st.set_page_config(
    page_title="Healthcare AI Demo - Corporate Standard",
    page_icon="🏥",
    layout="wide",  # Professional wide layout
    initial_sidebar_state="expanded",  # Traditional sidebar navigation
    menu_items={
        'About': """
        # Healthcare AI Demo - Corporate Standard Style
        
        This demonstration showcases how Snowflake's AI capabilities can transform 
        medical notes into actionable insights for improved patient care.
        
        **Corporate Standard Style Features:**
        - Professional, stable interface design
        - Native Streamlit components for maximum reliability
        - Clear visual hierarchy with bordered sections
        - Traditional navigation patterns
        
        **For demo purposes only - not for clinical use**
        """,
        'Get help': None,
        'Report a bug': None
    }
)

# Corporate Standard CSS - Minimal and stable as per style guide
st.markdown("""
<style>
/* Corporate Standard Theme - Minimal CSS for maximum stability */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    padding-left: 3rem;
    padding-right: 3rem;
}

/* Professional header styling */
.main-header {
    background: linear-gradient(90deg, #0062df 0%, #004499 100%);
    color: white;
    padding: 1.5rem;
    border-radius: 0.5rem;
    margin-bottom: 2rem;
    text-align: center;
}

/* Style guide indicator */
.style-indicator {
    position: fixed;
    top: 10px;
    right: 10px;
    background-color: #0062df;
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
    font-size: 0.8rem;
    font-weight: bold;
    z-index: 1000;
}
</style>
""", unsafe_allow_html=True)

# Style guide indicator
st.markdown("""
<div class="style-indicator">
    🔵 Corporate Standard
</div>
""", unsafe_allow_html=True)

# Main application header
st.markdown("""
<div class="main-header">
    <h1>🏥 Healthcare AI Demonstration</h1>
    <h3>Corporate Standard Style</h3>
    <p>Professional Medical Intelligence Platform</p>
</div>
""", unsafe_allow_html=True)

# Import shared components
try:
    from data_processors import create_medical_disclaimer, format_medical_value
    from ai_helpers import show_ai_processing_status
    from connection_helper import get_demo_data_status
    
    # Medical disclaimer using Corporate Standard bordered container
    with st.container(border=True):
        st.markdown("### ⚠️ Medical Disclaimer")
        st.markdown(create_medical_disclaimer())

except ImportError as e:
    st.error(f"Import error: {e}")
    st.info("Some shared components may not be available yet. This is normal during initial setup.")

# Main content area using Corporate Standard layout principles
col1, col2 = st.columns([2, 1])

with col1:
    with st.container(border=True):
        st.header("📋 Demo Overview")
        
        st.markdown("""
        **Corporate Standard Style Features:**
        
        ✅ **Maximum Stability**: Uses only native Streamlit components for guaranteed compatibility
        
        ✅ **Professional Appearance**: Clean, corporate-appropriate visual design
        
        ✅ **Clear Structure**: Bordered containers create obvious visual sections
        
        ✅ **Traditional Navigation**: Familiar sidebar-based navigation pattern
        
        ✅ **Regulatory Ready**: Conservative design suitable for healthcare compliance environments
        """)
        
        # Demo navigation using standard Streamlit components
        st.subheader("🗺️ Application Navigation")
        st.markdown("Use the sidebar to navigate through all available pages:")
        
        # Navigation info using native components
        nav_tab1, nav_tab2, nav_tab3 = st.tabs(["Core Features", "Analytics", "Tools"])
        
        with nav_tab1:
            st.markdown("""
            **Essential Clinical Tools:**
            - 🏥 **Data Foundation** - Dataset overview and system status
            - 🩺 **Clinical Decision Support** - AI-powered diagnosis and recommendations
            - 🔬 **Prompt and Model Testing** - AI model comparison and evaluation
            """)
        
        with nav_tab2:
            st.markdown("""
            **Population Health Analytics:**
            - 📊 **Population Health Analytics** - Cohort analysis and trends
            - 💰 **Cost Analysis** - Healthcare economics and financial insights  
            - 📈 **Quality Metrics** - Clinical quality indicators and benchmarking
            """)
        
        with nav_tab3:
            st.markdown("""
            **Advanced Tools:**
            - 💊 **Medication Safety** - Drug interactions and dosing guidance
            - 🤖 **AI Model Performance** - Model evaluation and comparison
            - 📋 **Demo Guide** - Comprehensive demonstration instructions
            """)

with col2:
    with st.container(border=True):
        st.header("📊 System Status")
        
        try:
            # Get system status using shared functions
            status_data = get_demo_data_status()
            
            if status_data:
                st.metric(
                    label="Database Connection", 
                    value="✅ Connected",
                    help="Snowflake connection active"
                )
                st.metric(
                    label="Patient Records", 
                    value=format_medical_value(status_data.get('patient_count', 1000), 'numeric'),
                    help="Available patient records in demo dataset"
                )
                st.metric(
                    label="AI Models Available", 
                    value="3 Models",
                    help="Snowflake Cortex models: mistral-large, mixtral-8x7b, llama3.1-70b"
                )
            else:
                st.warning("System status check in progress...")
                
        except Exception as e:
            st.error(f"Status check error: {e}")
            st.info("Backend systems initializing...")
    
    # Corporate Standard info panel
    with st.container(border=True):
        st.header("💡 Style Guide Info")
        
        st.markdown("""
        **Target Users:**
        - Conservative healthcare organizations  
        - Regulatory compliance environments
        - Traditional enterprise IT departments
        - Clinical staff preferring familiar interfaces
        
        **Key Benefits:**
        - Zero third-party dependencies
        - Maximum update compatibility
        - Professional corporate appearance
        - Proven, stable design patterns
        """)

# Application comparison section using bordered container
st.markdown("---")

with st.container(border=True):
    st.header("🎨 Style Comparison")
    
    comp_col1, comp_col2, comp_col3 = st.columns(3)
    
    with comp_col1:
        st.markdown("""
        **🔵 Corporate Standard** *(Current)*
        - Native Streamlit only
        - Professional blue theme  
        - Bordered containers
        - Maximum stability
        """)
        st.success("✅ Currently Viewing")
    
    with comp_col2:
        st.markdown("""
        **⚫ Modern Minimalist**
        - Contemporary design
        - Horizontal navigation
        - Spacious card layout
        - Premium feel
        """)
        if st.button("View Minimalist", key="view_minimalist"):
            st.info("🌐 Open http://localhost:8502 to view Modern Minimalist style")
    
    with comp_col3:
        st.markdown("""
        **🟡 Data-Dense Powerhouse**
        - Dark theme dashboard
        - Draggable components
        - High information density
        - Expert-focused interface
        """)
        if st.button("View Powerhouse", key="view_powerhouse"):
            st.info("🌐 Open http://localhost:8503 to view Data-Dense Powerhouse style")

# Footer with version and timestamp
st.markdown("---")

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.markdown("**Style:** Corporate Standard")

with footer_col2:
    st.markdown(f"**Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

with footer_col3:
    st.markdown("**Version:** v1.0.0 | Streamlit 1.49+")

# Sidebar content - Corporate Standard uses full sidebar for navigation
with st.sidebar:
    st.markdown("### 🏥 Healthcare AI Demo")
    st.markdown("#### Corporate Standard Style")
    
    st.markdown("---")
    
    # System info in sidebar
    with st.container(border=True):
        st.markdown("**System Information:**")
        st.markdown("• **Port:** 8501")
        st.markdown("• **Style:** Corporate")
        st.markdown("• **Components:** Native Only")
        st.markdown(f"• **Runtime:** Streamlit 1.49+")
    
    st.markdown("---")
    
    st.markdown("""
    **Navigation Instructions:**
    
    Use the pages in this sidebar to navigate through the application. Each page demonstrates the same functionality with Corporate Standard styling.
    
    **Pages Available:**
    - 🏥 Data Foundation
    - 🩺 Clinical Decision Support  
    - 🔬 Prompt and Model Testing
    - 📊 Population Health Analytics
    - 💰 Cost Analysis
    - 💊 Medication Safety
    - 📈 Quality Metrics
    - 🤖 AI Model Performance
    - 📋 Demo Guide
    """)
    
    st.markdown("---")
    
    # Style switching options using Corporate Standard components
    st.markdown("### 🎨 Compare Styles")
    
    if st.button("🌐 Modern Minimalist", use_container_width=True):
        st.info("Open http://localhost:8502")
        
    if st.button("⚡ Data-Dense Powerhouse", use_container_width=True):
        st.info("Open http://localhost:8503")
    
    st.markdown("---")
    
    # Show backend status using shared function
    try:
        show_ai_processing_status("complete", "Backend systems ready")
    except:
        st.info("🔄 Backend initializing...")