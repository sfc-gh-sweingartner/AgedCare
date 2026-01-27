"""
Style 2: Modern Minimalist - Cost Analysis
==========================================

Contemporary, elegant design with generous whitespace and curated components.
Designed for executive presentations and tech-forward organizations.

Features:
- Contemporary card-based layout
- Generous whitespace and subtle shadows
- Muted, sophisticated color palette  
- Clean typography and spacious design
- Premium feel with elegant financial visualizations
"""

import streamlit as st
import pandas as pd
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
    page_title="Style 2: Modern Minimalist - Cost Analysis",
    page_icon="💰",
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

.kpi-card {
    background: #fcfcfc;
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    border: 1px solid #f0f0f0;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}

.kpi-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #5a5a5a, #3d3d3d);
}

.kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.kpi-value {
    font-size: 2.5rem;
    font-weight: 300;
    color: #2c3e50;
    margin: 0.5rem 0;
}

.kpi-label {
    color: #6c757d;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.5rem;
}

.kpi-delta {
    font-size: 0.85rem;
    font-weight: 500;
    padding: 0.25rem 0.75rem;
    border-radius: 15px;
    display: inline-block;
    margin-top: 0.5rem;
}

.delta-positive {
    background: #d4edda;
    color: #155724;
}

.delta-negative {
    background: #f8d7da;
    color: #721c24;
}

.alert-minimal {
    background: #fff9e6;
    border: 1px solid #fff2cc;
    border-left: 4px solid #ffcc02;
    border-radius: 8px;
    padding: 1.5rem;
    margin: 1rem 0;
}

.savings-minimal {
    background: #e8f5e8;
    border: 1px solid #d4edda;
    border-left: 4px solid #28a745;
    border-radius: 8px;
    padding: 1.5rem;
    margin: 1rem 0;
}

.section-title {
    color: #2c3e50;
    font-weight: 300;
    font-size: 1.8rem;
    margin-bottom: 1.5rem;
    text-align: center;
}

.chart-container {
    background: white;
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# Style indicator
st.markdown('<div class="style-badge">⚫ Style 2: Modern Minimalist</div>', unsafe_allow_html=True)

# Header
st.markdown("""
<div class="minimalist-header">
    <h1 style="font-weight: 300; font-size: 3rem; margin: 0;">💰 Cost Intelligence</h1>
    <h3 style="font-weight: 300; margin-top: 1rem; opacity: 0.9;">Modern Minimalist Dashboard</h3>
    <p style="font-size: 1.1rem; margin-top: 1rem; opacity: 0.8;">Executive Financial Analytics Platform</p>
</div>
""", unsafe_allow_html=True)

# Financial disclaimer with minimal styling
st.markdown("""
<div class="minimalist-card">
    <h4 style="color: #856404; margin-bottom: 1rem; font-weight: 400;">⚠️ Financial Disclaimer</h4>
    <p style="color: #6c757d; line-height: 1.6;">This application serves demonstration purposes exclusively. 
    Cost estimates and financial analyses are illustrative examples and should not guide actual financial planning or billing decisions. 
    Consult qualified healthcare financial professionals for operational cost management.</p>
</div>
""", unsafe_allow_html=True)

# Generate sample cost data
@st.cache_data
def generate_cost_data():
    """Generate realistic sample healthcare cost data"""
    
    # Department cost data
    departments = ['Emergency', 'Cardiology', 'Oncology', 'Surgery', 'ICU', 'General Medicine']
    dept_costs = {
        'Department': departments,
        'Monthly_Cost': [450000, 320000, 280000, 520000, 380000, 240000],
        'Budget_Variance': [-5.2, 2.1, -8.3, 1.4, -12.1, 3.2],
        'Patient_Volume': [1200, 850, 600, 400, 300, 1800]
    }
    
    # Time series cost data
    dates = pd.date_range(start='2024-01-01', end='2024-08-31', freq='M')
    monthly_costs = {
        'Month': dates,
        'Total_Cost': [2100000 + np.random.normal(0, 50000) for _ in dates],
        'AI_Savings': [15000 + np.random.normal(0, 2000) for _ in dates],
        'Efficiency_Score': [85 + np.random.normal(0, 3) for _ in dates]
    }
    
    return pd.DataFrame(dept_costs), pd.DataFrame(monthly_costs)

dept_df, monthly_df = generate_cost_data()

# Spacious main layout
st.markdown('<div style="margin: 2rem 0;">', unsafe_allow_html=True)

# Executive KPI Dashboard
st.markdown("""
<div class="minimalist-card">
    <h2 class="section-title">Executive Overview</h2>
""", unsafe_allow_html=True)

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4, gap="large")

with kpi_col1:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Total Monthly Cost</div>
        <div class="kpi-value">$2.19M</div>
        <div class="kpi-delta delta-positive">↓ 2.3% vs last month</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col2:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">AI-Driven Savings</div>
        <div class="kpi-value">$127K</div>
        <div class="kpi-delta delta-positive">↑ 15% vs last month</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col3:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Cost per Patient</div>
        <div class="kpi-value">$3,940</div>
        <div class="kpi-delta delta-positive">↓ $120 vs benchmark</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col4:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Efficiency Score</div>
        <div class="kpi-value">87%</div>
        <div class="kpi-delta delta-positive">↑ 3 points vs target</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Main content with elegant spacing
col1, col2 = st.columns([2, 1], gap="large")

with col1:
    # Department analysis with minimal design
    st.markdown("""
    <div class="minimalist-card">
        <h2 class="section-title">Department Performance</h2>
    """, unsafe_allow_html=True)
    
    # Clean, minimal chart
    fig = px.bar(
        dept_df,
        x='Department',
        y='Monthly_Cost',
        title="",
        color_discrete_sequence=['#5a5a5a'],
        text='Monthly_Cost'
    )
    
    fig.update_layout(
        template="plotly_white",
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#4a4a4a'),
        margin=dict(l=20, r=20, t=20, b=60),
        xaxis_title="",
        yaxis_title=""
    )
    
    fig.update_traces(
        texttemplate='$%{text:,.0f}K', 
        textposition='outside',
        marker_color='#5a5a5a',
        opacity=0.8
    )
    
    fig.update_xaxes(tickangle=45)
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Budget variance analysis
    st.markdown("""
    <div class="minimalist-card">
        <h2 class="section-title">Budget Variance Analysis</h2>
    """, unsafe_allow_html=True)
    
    # Elegant variance chart
    colors = ['#dc3545' if x < -5 else '#28a745' if x > 5 else '#5a5a5a' for x in dept_df['Budget_Variance']]
    
    fig = px.bar(
        dept_df,
        x='Department',
        y='Budget_Variance',
        title="",
        color_discrete_sequence=colors
    )
    
    fig.update_layout(
        template="plotly_white",
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#4a4a4a'),
        margin=dict(l=20, r=20, t=20, b=60),
        xaxis_title="",
        yaxis_title=""
    )
    
    fig.update_xaxes(tickangle=45)
    fig.update_traces(opacity=0.8)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Variance insights
    high_variance_depts = dept_df[abs(dept_df['Budget_Variance']) > 8]
    if not high_variance_depts.empty:
        for _, dept in high_variance_depts.iterrows():
            if dept['Budget_Variance'] < -8:
                st.markdown(f"""
                <div class="alert-minimal">
                    <h5 style="color: #856404; margin-bottom: 0.5rem;">⚠️ Budget Alert: {dept['Department']}</h5>
                    <p style="margin: 0; color: #6c757d;">
                    Over budget by {abs(dept['Budget_Variance']):.1f}% (${abs(dept['Monthly_Cost'] * dept['Budget_Variance'] / 100):,.0f})
                    </p>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # AI Impact Visualization
    st.markdown("""
    <div class="minimalist-card">
        <h2 class="section-title">AI Impact Trends</h2>
    """, unsafe_allow_html=True)
    
    # Elegant dual-axis chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=monthly_df['Month'],
        y=monthly_df['Total_Cost'],
        mode='lines+markers',
        name='Total Costs',
        line=dict(color='#5a5a5a', width=3),
        marker=dict(size=6),
        opacity=0.8
    ))
    
    fig.add_trace(go.Scatter(
        x=monthly_df['Month'],
        y=monthly_df['AI_Savings'],
        mode='lines+markers',
        name='AI Savings',
        line=dict(color='#28a745', width=3),
        marker=dict(size=6),
        yaxis='y2',
        opacity=0.8
    ))
    
    fig.update_layout(
        template="plotly_white",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#4a4a4a'),
        margin=dict(l=20, r=20, t=20, b=20),
        yaxis=dict(title="Total Costs ($)", side="left"),
        yaxis2=dict(title="AI Savings ($)", side="right", overlaying="y"),
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # AI savings summary with elegant styling
    total_savings = monthly_df['AI_Savings'].sum()
    st.markdown(f"""
    <div class="savings-minimal">
        <h4 style="color: #155724; margin-bottom: 1rem; font-weight: 400;">💡 AI Impact Summary</h4>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; text-align: center;">
            <div>
                <p style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.25rem;">Total Savings (YTD)</p>
                <p style="font-size: 1.5rem; font-weight: 300; color: #155724; margin: 0;">${total_savings:,.0f}</p>
            </div>
            <div>
                <p style="color: #6c757d; font-size: 0.9rem; margin-bottom: 0.25rem;">Projected Annual</p>
                <p style="font-size: 1.5rem; font-weight: 300; color: #155724; margin: 0;">${(total_savings/len(monthly_df))*12:,.0f}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # Executive alerts with minimal design
    st.markdown("""
    <div class="minimalist-card">
        <h2 class="section-title">Priority Alerts</h2>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="alert-minimal">
        <h5 style="color: #856404; margin-bottom: 0.75rem; font-weight: 500;">⚠️ Critical</h5>
        <p style="margin: 0; color: #6c757d; line-height: 1.5;">
        <strong>ICU Department:</strong><br>
        12.1% over budget<br>
        <em>Recommend staffing optimization review</em>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="alert-minimal">
        <h5 style="color: #856404; margin-bottom: 0.75rem; font-weight: 500;">⚠️ Monitor</h5>
        <p style="margin: 0; color: #6c757d; line-height: 1.5;">
        <strong>Oncology Department:</strong><br>
        8.3% over budget<br>
        <em>Treatment cost analysis needed</em>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="savings-minimal">
        <h5 style="color: #155724; margin-bottom: 0.75rem; font-weight: 500;">✅ Positive</h5>
        <p style="margin: 0; color: #6c757d; line-height: 1.5;">
        <strong>AI Efficiency:</strong><br>
        15% savings increase<br>
        <em>Continue current initiatives</em>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Executive actions
    st.markdown("""
    <div class="minimalist-card">
        <h2 class="section-title">Executive Actions</h2>
    """, unsafe_allow_html=True)
    
    if st.button("📊 Generate Executive Report", use_container_width=True):
        st.success("✅ Executive summary generated and distributed")
    
    if st.button("📈 Budget Forecast", use_container_width=True):
        st.info("📋 Predictive analytics dashboard launched")
    
    if st.button("💡 Cost Optimization", use_container_width=True):
        st.info("🎯 AI recommendations compiled")
    
    if st.button("🚨 Alert Management", use_container_width=True):
        st.success("📨 Stakeholder notifications sent")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Performance benchmarks with elegant design
    st.markdown("""
    <div class="minimalist-card">
        <h2 class="section-title">Benchmarks</h2>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="space-y: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem 0; border-bottom: 1px solid #f0f0f0;">
            <span style="color: #6c757d; font-size: 0.9rem;">Industry Average</span>
            <span style="font-weight: 500; color: #4a4a4a;">$4,200</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem 0; border-bottom: 1px solid #f0f0f0;">
            <span style="color: #6c757d; font-size: 0.9rem;">Top Performers</span>
            <span style="font-weight: 500; color: #4a4a4a;">$3,600</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem 0;">
            <span style="color: #6c757d; font-size: 0.9rem;">Our Performance</span>
            <span style="font-weight: 600; color: #28a745; font-size: 1.1rem;">$3,940</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Minimal footer
st.markdown('<div style="margin-top: 3rem; text-align: center; color: #6c757d; font-size: 0.9rem;">', unsafe_allow_html=True)
st.markdown("---")
st.markdown(f"**Modern Minimalist Style** • **Cost Intelligence Dashboard** • **Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
st.markdown('</div>', unsafe_allow_html=True)

# Minimal sidebar
with st.sidebar:
    st.markdown("### 💰 Cost Analysis")
    st.markdown("*Modern Minimalist Style*")
    
    st.markdown("---")
    
    st.markdown("""
    **Key Insights:**
    - 📊 Department performance tracking
    - 📈 Budget variance monitoring
    - 🤖 AI impact measurement
    - 🚨 Executive alert system
    - 📏 Industry benchmarking
    """)
    
    st.markdown("---")
    
    st.markdown("""
    **Style Features:**
    - ✨ Contemporary executive design
    - 🎨 Sophisticated color palette
    - 📏 Generous whitespace
    - 💎 Premium visual hierarchy
    - 📱 Clean, responsive layouts
    """)
    
    st.markdown("---")
    
    st.markdown("**Compare styles:**")
    st.markdown("• Style1: Corporate Standard")
    st.markdown("• Style3: Data-Dense Powerhouse")
