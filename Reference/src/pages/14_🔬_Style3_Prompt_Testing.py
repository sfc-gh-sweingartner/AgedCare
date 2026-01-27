"""
Style 3: Data-Dense Powerhouse - Prompt and Model Testing
========================================================

High-density dashboard interface designed for expert users.
Maximum information density with operational dashboard feel.

Features:
- Dark theme interface for reduced eye strain
- Compact, high-density information display
- Multiple data panels and metrics
- Expert-focused design with advanced controls
- Operational monitoring dashboard aesthetics
"""

import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

# Page configuration
st.set_page_config(
    page_title="Style 3: Data-Dense Powerhouse - Prompt Testing",
    page_icon="🔬",
    layout="wide"
)

# Data-Dense Powerhouse CSS (Dark Theme)
st.markdown("""
<style>
/* Data-Dense Powerhouse Dark Theme */
.stApp {
    background-color: #0e1117;
    color: #fafafa;
}

.powerhouse-panel {
    background: #262730;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 1rem;
    margin: 0.5rem 0;
}

.powerhouse-header {
    background: linear-gradient(90deg, #1c83e1 0%, #1a73c7 100%);
    color: white;
    padding: 1rem 2rem;
    margin-bottom: 1rem;
    border-radius: 4px;
    text-align: center;
}

.style-badge {
    position: fixed;
    top: 10px;
    right: 10px;
    background: #1c83e1;
    color: white;
    padding: 6px 12px;
    border-radius: 3px;
    font-weight: bold;
    font-size: 0.8rem;
    z-index: 1000;
}

.metric-dense {
    background: #1a1a1a;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 0.8rem;
    text-align: center;
    margin: 0.3rem 0;
}

.metric-value {
    color: #1c83e1;
    font-size: 1.8rem;
    font-weight: bold;
    margin: 0;
}

.metric-label {
    color: #8b8b8b;
    font-size: 0.75rem;
    text-transform: uppercase;
    margin-bottom: 0.2rem;
}

.status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.5rem;
    margin: 0.5rem 0;
}

.status-item {
    background: #1a1a1a;
    border: 1px solid #3d3d3d;
    border-radius: 3px;
    padding: 0.5rem;
    text-align: center;
    font-size: 0.8rem;
}

.status-active {
    border-color: #28a745;
    background: #0f2b0f;
}

.status-warning {
    border-color: #ffc107;
    background: #2b2401;
}

.status-error {
    border-color: #dc3545;
    background: #2b0b0f;
}

.data-table {
    background: #1a1a1a;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 0.8rem;
    margin: 0.5rem 0;
}

.prompt-config {
    background: #262730;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 1rem;
    margin: 0.5rem 0;
}

.result-panel {
    background: #1a1a1a;
    border-left: 3px solid #1c83e1;
    padding: 1rem;
    margin: 0.5rem 0;
    font-family: 'Courier New', monospace;
    font-size: 0.85rem;
}

.compact-header {
    color: #fafafa;
    font-size: 1rem;
    font-weight: 600;
    margin: 0.5rem 0;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid #3d3d3d;
}

/* Override Streamlit dark theme elements */
.stSelectbox > div > div {
    background-color: #262730;
    color: #fafafa;
    border: 1px solid #3d3d3d;
}

.stTextArea textarea {
    background-color: #262730;
    color: #fafafa;
    border: 1px solid #3d3d3d;
}

.stButton > button {
    background-color: #1c83e1;
    color: white;
    border: none;
    border-radius: 3px;
}

.stMetric {
    background: #262730;
}
</style>
""", unsafe_allow_html=True)

# Style indicator
st.markdown('<div class="style-badge">🟡 Style 3: Data-Dense Powerhouse</div>', unsafe_allow_html=True)

# Compact header
st.markdown("""
<div class="powerhouse-header">
    <h2 style="margin: 0; font-weight: 600;">🔬 AI Model Testing Dashboard</h2>
    <p style="margin: 0.3rem 0 0 0; font-size: 0.9rem; opacity: 0.8;">Data-Dense Powerhouse Interface</p>
</div>
""", unsafe_allow_html=True)

# Generate real-time metrics
@st.cache_data(ttl=30)
def get_realtime_metrics():
    return {
        'active_tests': np.random.randint(15, 25),
        'queue_size': np.random.randint(0, 8),
        'success_rate': np.random.uniform(96, 99.5),
        'avg_response_time': np.random.uniform(1.8, 2.5),
        'total_today': np.random.randint(180, 220),
        'cpu_usage': np.random.uniform(45, 75),
        'memory_usage': np.random.uniform(60, 85)
    }

metrics = get_realtime_metrics()

# Compact disclaimer
st.markdown("""
<div class="powerhouse-panel">
    <strong style="color: #ffc107;">⚠️ DEMO SYSTEM</strong> - 
    <span style="color: #8b8b8b; font-size: 0.85rem;">For demonstration only. Not for clinical use. All outputs require professional review.</span>
</div>
""", unsafe_allow_html=True)

# Multi-column dense layout
col1, col2, col3, col4 = st.columns([2, 1, 1, 1], gap="small")

with col1:
    # Main testing interface
    st.markdown('<div class="compact-header">MODEL TESTING INTERFACE</div>', unsafe_allow_html=True)
    
    # Compact model selection
    st.markdown("""
    <div class="powerhouse-panel">
        <strong style="color: #1c83e1;">Active Models</strong>
        <div class="status-grid" style="margin-top: 0.5rem;">
            <div class="status-item status-active">
                <div>MISTRAL-L</div>
                <div style="color: #28a745; font-size: 0.7rem;">ACTIVE</div>
            </div>
            <div class="status-item status-active">
                <div>MIXTRAL-8x7B</div>
                <div style="color: #28a745; font-size: 0.7rem;">ACTIVE</div>
            </div>
            <div class="status-item">
                <div>LLAMA3.1-70B</div>
                <div style="color: #6c757d; font-size: 0.7rem;">STANDBY</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Compact prompt configuration
    prompt_col1, prompt_col2 = st.columns([1, 2], gap="small")
    
    with prompt_col1:
        prompt_type = st.selectbox("Type", ["Clinical Summary", "Differential Dx", "Treatment Rec", "Risk Assessment"], key="prompt_type_dense")
    
    with prompt_col2:
        priority = st.selectbox("Priority", ["Normal", "High", "Critical"], key="priority_dense")
    
    # Compact input area
    patient_data = st.text_area(
        "Patient Data",
        placeholder="CC: Chest pain, SOB\nHx: 55M, HTN\nVS: BP 150/95, HR 102\nOnset: 2h ago, L arm radiation",
        height=100,
        key="patient_dense"
    )
    
    # Compact controls
    test_col1, test_col2, test_col3, test_col4 = st.columns(4, gap="small")
    
    with test_col1:
        if st.button("🚀 RUN", use_container_width=True, key="run_dense"):
            st.session_state.run_test_dense = True
    
    with test_col2:
        if st.button("⏸️ QUEUE", use_container_width=True, key="queue_dense"):
            st.info("Added to queue")
    
    with test_col3:
        if st.button("💾 SAVE", use_container_width=True, key="save_dense"):
            st.success("Config saved")
    
    with test_col4:
        if st.button("🔄 CLEAR", use_container_width=True, key="clear_dense"):
            st.session_state.clear()
    
    # Results section
    if 'run_test_dense' in st.session_state and st.session_state.run_test_dense:
        st.markdown('<div class="compact-header">LIVE RESULTS</div>', unsafe_allow_html=True)
        
        # Compact results for each model
        results_data = {
            'Model': ['MISTRAL-L', 'MIXTRAL-8x7B'],
            'Time': ['2.1s', '1.8s'],
            'Confidence': ['87%', '85%'],
            'Tokens': ['245', '223'],
            'Status': ['✅ Complete', '✅ Complete']
        }
        
        results_df = pd.DataFrame(results_data)
        
        st.markdown("""
        <div class="data-table">
            <table style="width: 100%; color: #fafafa; font-size: 0.8rem;">
                <tr style="border-bottom: 1px solid #3d3d3d;">
                    <th style="text-align: left; padding: 0.3rem;">Model</th>
                    <th style="text-align: center; padding: 0.3rem;">Time</th>
                    <th style="text-align: center; padding: 0.3rem;">Conf</th>
                    <th style="text-align: center; padding: 0.3rem;">Tokens</th>
                    <th style="text-align: center; padding: 0.3rem;">Status</th>
                </tr>
                <tr>
                    <td style="padding: 0.3rem; color: #1c83e1;">MISTRAL-L</td>
                    <td style="text-align: center; padding: 0.3rem;">2.1s</td>
                    <td style="text-align: center; padding: 0.3rem; color: #28a745;">87%</td>
                    <td style="text-align: center; padding: 0.3rem;">245</td>
                    <td style="text-align: center; padding: 0.3rem; color: #28a745;">✅ Complete</td>
                </tr>
                <tr>
                    <td style="padding: 0.3rem; color: #1c83e1;">MIXTRAL-8x7B</td>
                    <td style="text-align: center; padding: 0.3rem;">1.8s</td>
                    <td style="text-align: center; padding: 0.3rem; color: #28a745;">85%</td>
                    <td style="text-align: center; padding: 0.3rem;">223</td>
                    <td style="text-align: center; padding: 0.3rem; color: #28a745;">✅ Complete</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
        
        # Sample result output
        st.markdown("""
        <div class="result-panel">
            <strong style="color: #1c83e1;">[MISTRAL-L OUTPUT]</strong><br>
            Clinical Assessment: 55M w/ acute chest pain + SOB. HTN hx + presentation suggests ACS. 
            Recommend: ECG, troponins, CXR. Consider STEMI protocol if ST elevation present.
            DDx: STEMI/NSTEMI, unstable angina, aortic dissection, PE...
            <br><br>
            <strong style="color: #1c83e1;">[CONFIDENCE: 87% | PROCESSING: 2.1s]</strong>
        </div>
        """, unsafe_allow_html=True)

with col2:
    # System monitoring
    st.markdown('<div class="compact-header">SYSTEM STATUS</div>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="metric-dense">
        <div class="metric-label">Active Tests</div>
        <div class="metric-value">{metrics['active_tests']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="metric-dense">
        <div class="metric-label">Queue Size</div>
        <div class="metric-value">{metrics['queue_size']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="metric-dense">
        <div class="metric-label">Success Rate</div>
        <div class="metric-value">{metrics['success_rate']:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="metric-dense">
        <div class="metric-label">Avg Response</div>
        <div class="metric-value">{metrics['avg_response_time']:.1f}s</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Resource monitoring
    st.markdown('<div class="compact-header">RESOURCES</div>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="metric-dense">
        <div class="metric-label">CPU Usage</div>
        <div class="metric-value">{metrics['cpu_usage']:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="metric-dense">
        <div class="metric-label">Memory</div>
        <div class="metric-value">{metrics['memory_usage']:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    # Model performance metrics
    st.markdown('<div class="compact-header">PERFORMANCE</div>', unsafe_allow_html=True)
    
    # Compact performance data
    perf_data = {
        'Model': ['MISTRAL-L', 'MIXTRAL-8x7B', 'LLAMA3.1-70B'],
        'Avg_Time': [2.1, 1.8, 2.5],
        'Success': [98.5, 97.2, 96.8],
        'Queue': [3, 2, 0]
    }
    
    st.markdown("""
    <div class="data-table">
        <table style="width: 100%; color: #fafafa; font-size: 0.75rem;">
            <tr style="border-bottom: 1px solid #3d3d3d;">
                <th style="text-align: left; padding: 0.2rem;">Model</th>
                <th style="text-align: center; padding: 0.2rem;">Time</th>
                <th style="text-align: center; padding: 0.2rem;">Success</th>
            </tr>
            <tr>
                <td style="padding: 0.2rem; color: #1c83e1;">MISTRAL-L</td>
                <td style="text-align: center; padding: 0.2rem;">2.1s</td>
                <td style="text-align: center; padding: 0.2rem;">98.5%</td>
            </tr>
            <tr>
                <td style="padding: 0.2rem; color: #1c83e1;">MIXTRAL-8x7B</td>
                <td style="text-align: center; padding: 0.2rem;">1.8s</td>
                <td style="text-align: center; padding: 0.2rem;">97.2%</td>
            </tr>
            <tr>
                <td style="padding: 0.2rem; color: #6c757d;">LLAMA3.1-70B</td>
                <td style="text-align: center; padding: 0.2rem;">2.5s</td>
                <td style="text-align: center; padding: 0.2rem;">96.8%</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)
    
    # Performance trend (mini chart)
    trend_data = [85, 87, 89, 86, 88, 90, 87]
    trend_fig = go.Figure(data=go.Scatter(
        y=trend_data,
        mode='lines',
        line=dict(color='#1c83e1', width=2),
        showlegend=False
    ))
    
    trend_fig.update_layout(
        template="plotly_dark",
        height=120,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, showticklabels=False),
        plot_bgcolor='#262730',
        paper_bgcolor='#262730'
    )
    
    st.plotly_chart(trend_fig, use_container_width=True, key="trend_mini")

with col4:
    # Activity log
    st.markdown('<div class="compact-header">ACTIVITY LOG</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="data-table" style="height: 400px; overflow-y: auto;">
        <div style="font-size: 0.7rem; line-height: 1.2;">
            <div style="margin-bottom: 0.3rem; color: #28a745;">
                12:45:23 - MISTRAL-L completed [2.1s]
            </div>
            <div style="margin-bottom: 0.3rem; color: #28a745;">
                12:45:21 - MIXTRAL-8x7B completed [1.8s]
            </div>
            <div style="margin-bottom: 0.3rem; color: #1c83e1;">
                12:45:19 - Test queued: Clinical Summary
            </div>
            <div style="margin-bottom: 0.3rem; color: #28a745;">
                12:44:58 - MISTRAL-L completed [2.3s]
            </div>
            <div style="margin-bottom: 0.3rem; color: #ffc107;">
                12:44:45 - Queue size increased to 5
            </div>
            <div style="margin-bottom: 0.3rem; color: #28a745;">
                12:44:32 - MIXTRAL-8x7B completed [1.7s]
            </div>
            <div style="margin-bottom: 0.3rem; color: #1c83e1;">
                12:44:20 - Test queued: Risk Assessment
            </div>
            <div style="margin-bottom: 0.3rem; color: #28a745;">
                12:44:01 - MISTRAL-L completed [2.0s]
            </div>
            <div style="margin-bottom: 0.3rem; color: #dc3545;">
                12:43:45 - LLAMA3.1-70B timeout error
            </div>
            <div style="margin-bottom: 0.3rem; color: #28a745;">
                12:43:30 - MIXTRAL-8x7B completed [1.9s]
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Compact footer
st.markdown('<div style="margin-top: 1rem; text-align: center; color: #6c757d; font-size: 0.8rem; border-top: 1px solid #3d3d3d; padding-top: 0.5rem;">', unsafe_allow_html=True)
st.markdown(f"Data-Dense Powerhouse • Prompt Testing • {datetime.now().strftime('%H:%M:%S')}")
st.markdown('</div>', unsafe_allow_html=True)

# Compact sidebar
with st.sidebar:
    st.markdown("### 🔬 Testing Dashboard")
    st.markdown("*Data-Dense Powerhouse*")
    
    st.markdown("---")
    
    st.markdown(f"""
    **Live Metrics:**
    - Tests Active: {metrics['active_tests']}
    - Queue Size: {metrics['queue_size']}
    - Success Rate: {metrics['success_rate']:.1f}%
    - Avg Response: {metrics['avg_response_time']:.1f}s
    - Total Today: {metrics['total_today']}
    """)
    
    st.markdown("---")
    
    st.markdown("""
    **Style Features:**
    - 🌃 Dark theme interface
    - 📊 High information density
    - ⚡ Real-time monitoring
    - 📈 Live performance metrics
    - 🎛️ Expert controls
    """)
    
    st.markdown("---")
    
    st.markdown("**Compare styles:**")
    st.markdown("• Style1: Corporate Standard")
    st.markdown("• Style2: Modern Minimalist")
    
    # Auto-refresh
    if st.button("🔄 Refresh Metrics", use_container_width=True):
        st.cache_data.clear()
        st.experimental_rerun()
