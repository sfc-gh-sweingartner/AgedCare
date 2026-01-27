"""
Style 3: Data-Dense Powerhouse - Cost Analysis
==============================================

High-density financial dashboard interface designed for expert analysts.
Maximum information density with operational monitoring feel.

Features:
- Dark theme interface for extended monitoring
- Compact, high-density financial displays
- Multiple data panels and real-time metrics
- Expert-focused design with advanced analytics
- Operational financial monitoring dashboard
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
    page_title="Style 3: Data-Dense Powerhouse - Cost Analysis",
    page_icon="💰",
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

.cost-metric {
    background: #1a1a1a;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 0.8rem;
    text-align: center;
    margin: 0.3rem 0;
    position: relative;
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

.metric-delta {
    color: #28a745;
    font-size: 0.7rem;
    margin-top: 0.2rem;
}

.metric-delta.negative {
    color: #dc3545;
}

.dept-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.5rem;
    margin: 0.5rem 0;
}

.dept-card {
    background: #1a1a1a;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 0.8rem;
    text-align: center;
}

.dept-over-budget {
    border-color: #dc3545;
    background: #2b0b0f;
}

.dept-under-budget {
    border-color: #28a745;
    background: #0f2b0f;
}

.alert-critical {
    background: #2b0b0f;
    border: 1px solid #dc3545;
    border-left: 4px solid #dc3545;
    border-radius: 4px;
    padding: 0.8rem;
    margin: 0.3rem 0;
    font-size: 0.85rem;
}

.alert-warning {
    background: #2b2401;
    border: 1px solid #ffc107;
    border-left: 4px solid #ffc107;
    border-radius: 4px;
    padding: 0.8rem;
    margin: 0.3rem 0;
    font-size: 0.85rem;
}

.savings-highlight {
    background: #0f2b0f;
    border: 1px solid #28a745;
    border-left: 4px solid #28a745;
    border-radius: 4px;
    padding: 0.8rem;
    margin: 0.3rem 0;
    font-size: 0.85rem;
}

.data-table-dense {
    background: #1a1a1a;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 0.8rem;
    margin: 0.5rem 0;
    font-family: 'Courier New', monospace;
    font-size: 0.75rem;
}

.compact-header {
    color: #fafafa;
    font-size: 1rem;
    font-weight: 600;
    margin: 0.5rem 0;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid #3d3d3d;
}

.trend-indicator {
    position: absolute;
    top: 0.3rem;
    right: 0.3rem;
    font-size: 0.7rem;
}

.trend-up { color: #28a745; }
.trend-down { color: #dc3545; }
.trend-flat { color: #6c757d; }
</style>
""", unsafe_allow_html=True)

# Style indicator
st.markdown('<div class="style-badge">🟡 Style 3: Data-Dense Powerhouse</div>', unsafe_allow_html=True)

# Compact header
st.markdown("""
<div class="powerhouse-header">
    <h2 style="margin: 0; font-weight: 600;">💰 Financial Operations Dashboard</h2>
    <p style="margin: 0.3rem 0 0 0; font-size: 0.9rem; opacity: 0.8;">Data-Dense Powerhouse Interface</p>
</div>
""", unsafe_allow_html=True)

# Generate comprehensive financial data
@st.cache_data(ttl=60)
def generate_financial_data():
    """Generate comprehensive real-time financial data"""
    
    # Department data with real-time fluctuations
    departments = ['Emergency', 'Cardiology', 'Oncology', 'Surgery', 'ICU', 'General Med', 'Radiology', 'Lab']
    dept_data = {
        'Department': departments,
        'Current_Cost': [450000 + np.random.randint(-20000, 20000) for _ in departments],
        'Budget': [480000, 320000, 280000, 520000, 380000, 240000, 180000, 150000],
        'Variance': [np.random.uniform(-15, 10) for _ in departments],
        'Trend': [np.random.choice(['↗', '↘', '→']) for _ in departments],
        'Patients': [np.random.randint(800, 1400) if d == 'Emergency' else np.random.randint(200, 900) for d in departments],
        'Cost_per_Patient': []
    }
    
    # Calculate cost per patient
    for i in range(len(departments)):
        dept_data['Cost_per_Patient'].append(dept_data['Current_Cost'][i] / dept_data['Patients'][i])
    
    # Real-time metrics
    total_cost = sum(dept_data['Current_Cost'])
    metrics = {
        'total_monthly': total_cost,
        'daily_burn': total_cost / 30 + np.random.randint(-5000, 5000),
        'ai_savings': np.random.randint(120000, 135000),
        'efficiency_score': np.random.uniform(84, 91),
        'budget_utilization': (total_cost / sum(dept_data['Budget'])) * 100,
        'cost_per_patient': total_cost / sum(dept_data['Patients']),
        'alerts_critical': np.random.randint(1, 4),
        'alerts_warning': np.random.randint(3, 8),
        'variance_total': np.random.uniform(-3.2, 1.8)
    }
    
    # Time series for trends
    hours = [datetime.now() - timedelta(hours=x) for x in range(24, 0, -1)]
    hourly_costs = [total_cost/24 + np.random.normal(0, total_cost/100) for _ in hours]
    
    return dept_data, metrics, {'hours': hours, 'costs': hourly_costs}

dept_data, metrics, trends = generate_financial_data()

# Compact disclaimer
st.markdown("""
<div class="powerhouse-panel">
    <strong style="color: #ffc107;">⚠️ DEMO SYSTEM</strong> - 
    <span style="color: #8b8b8b; font-size: 0.85rem;">Financial data simulated for demonstration. Not for actual financial planning or operational decisions.</span>
</div>
""", unsafe_allow_html=True)

# Multi-column ultra-dense layout
col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1], gap="small")

with col1:
    # Main financial overview
    st.markdown('<div class="compact-header">DEPARTMENT COST ANALYSIS</div>', unsafe_allow_html=True)
    
    # Department grid with status
    st.markdown('<div class="dept-grid">', unsafe_allow_html=True)
    
    for i, dept in enumerate(dept_data['Department']):
        cost = dept_data['Current_Cost'][i]
        budget = dept_data['Budget'][i]
        variance = dept_data['Variance'][i]
        trend = dept_data['Trend'][i]
        
        status_class = 'dept-over-budget' if variance < -5 else 'dept-under-budget' if variance > 5 else ''
        
        st.markdown(f"""
        <div class="dept-card {status_class}">
            <div style="font-size: 0.8rem; font-weight: bold; color: #1c83e1;">{dept[:8]}</div>
            <div style="color: #fafafa; font-size: 1.2rem; font-weight: bold;">${cost/1000:.0f}K</div>
            <div style="color: {'#dc3545' if variance < 0 else '#28a745'}; font-size: 0.7rem;">
                {variance:+.1f}% {trend}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Detailed financial table
    st.markdown('<div class="compact-header">DETAILED BREAKDOWN</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="data-table-dense">
        <table style="width: 100%; color: #fafafa; font-size: 0.7rem;">
            <tr style="border-bottom: 1px solid #3d3d3d; color: #8b8b8b;">
                <th style="text-align: left; padding: 0.2rem;">DEPT</th>
                <th style="text-align: right; padding: 0.2rem;">ACTUAL</th>
                <th style="text-align: right; padding: 0.2rem;">BUDGET</th>
                <th style="text-align: right; padding: 0.2rem;">VAR%</th>
                <th style="text-align: right; padding: 0.2rem;">$/PT</th>
                <th style="text-align: center; padding: 0.2rem;">TREND</th>
            </tr>
    """, unsafe_allow_html=True)
    
    for i, dept in enumerate(dept_data['Department']):
        cost = dept_data['Current_Cost'][i]
        budget = dept_data['Budget'][i]
        variance = dept_data['Variance'][i]
        cost_per_pt = dept_data['Cost_per_Patient'][i]
        trend = dept_data['Trend'][i]
        
        var_color = '#dc3545' if variance < -5 else '#28a745' if variance > 0 else '#fafafa'
        
        st.markdown(f"""
            <tr>
                <td style="padding: 0.2rem; color: #1c83e1;">{dept[:10]}</td>
                <td style="text-align: right; padding: 0.2rem;">${cost:,.0f}</td>
                <td style="text-align: right; padding: 0.2rem;">${budget:,.0f}</td>
                <td style="text-align: right; padding: 0.2rem; color: {var_color};">{variance:+.1f}%</td>
                <td style="text-align: right; padding: 0.2rem;">${cost_per_pt:.0f}</td>
                <td style="text-align: center; padding: 0.2rem;">{trend}</td>
            </tr>
        """, unsafe_allow_html=True)
    
    st.markdown("""
        </table>
    </div>
    """, unsafe_allow_html=True)

with col2:
    # Real-time financial metrics
    st.markdown('<div class="compact-header">LIVE METRICS</div>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="cost-metric">
        <div class="trend-indicator trend-{'down' if metrics['variance_total'] < 0 else 'up'}">
            {'↘' if metrics['variance_total'] < 0 else '↗'}
        </div>
        <div class="metric-label">Total Monthly</div>
        <div class="metric-value">${metrics['total_monthly']/1000000:.2f}M</div>
        <div class="metric-delta {'negative' if metrics['variance_total'] < 0 else ''}">
            {metrics['variance_total']:+.1f}% vs budget
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="cost-metric">
        <div class="metric-label">Daily Burn Rate</div>
        <div class="metric-value">${metrics['daily_burn']/1000:.0f}K</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="cost-metric">
        <div class="metric-label">Budget Util.</div>
        <div class="metric-value">{metrics['budget_utilization']:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="cost-metric">
        <div class="metric-label">Cost/Patient</div>
        <div class="metric-value">${metrics['cost_per_patient']:.0f}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="cost-metric">
        <div class="metric-label">Efficiency</div>
        <div class="metric-value">{metrics['efficiency_score']:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    # AI impact and savings
    st.markdown('<div class="compact-header">AI IMPACT</div>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="cost-metric">
        <div class="metric-label">AI Savings MTD</div>
        <div class="metric-value">${metrics['ai_savings']/1000:.0f}K</div>
        <div class="metric-delta">↗ +15% vs last month</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="cost-metric">
        <div class="metric-label">ROI on AI</div>
        <div class="metric-value">340%</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Mini AI impact chart
    ai_impact_data = [12, 14, 13, 15, 16, 18, 17]
    fig_ai = go.Figure(data=go.Scatter(
        y=ai_impact_data,
        mode='lines+markers',
        line=dict(color='#28a745', width=2),
        marker=dict(size=4),
        showlegend=False
    ))
    
    fig_ai.update_layout(
        template="plotly_dark",
        height=100,
        margin=dict(l=5, r=5, t=5, b=5),
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, showticklabels=False),
        plot_bgcolor='#262730',
        paper_bgcolor='#262730'
    )
    
    st.plotly_chart(fig_ai, use_container_width=True, key="ai_mini")
    
    # AI opportunities
    st.markdown("""
    <div class="powerhouse-panel" style="padding: 0.5rem;">
        <div style="font-size: 0.8rem; font-weight: bold; color: #1c83e1; margin-bottom: 0.5rem;">AI OPPORTUNITIES</div>
        <div style="font-size: 0.7rem; color: #8b8b8b;">
            • Automated scheduling: $45K<br>
            • Predictive maintenance: $23K<br>
            • Resource optimization: $38K
        </div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    # Alerts and monitoring
    st.markdown('<div class="compact-header">ALERTS</div>', unsafe_allow_html=True)
    
    # Critical alerts
    st.markdown(f"""
    <div class="alert-critical">
        <strong>🔴 CRITICAL ({metrics['alerts_critical']})</strong><br>
        <div style="font-size: 0.7rem; margin-top: 0.3rem;">
            ICU: 12.1% over budget<br>
            Oncology: 8.3% over budget
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Warning alerts
    st.markdown(f"""
    <div class="alert-warning">
        <strong>🟡 WARNING ({metrics['alerts_warning']})</strong><br>
        <div style="font-size: 0.7rem; margin-top: 0.3rem;">
            Emergency: High volume<br>
            Surgery: Equipment costs up<br>
            Lab: Overtime trending up
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Positive indicators
    st.markdown("""
    <div class="savings-highlight">
        <strong>✅ POSITIVE</strong><br>
        <div style="font-size: 0.7rem; margin-top: 0.3rem;">
            Cardiology: 2.1% under budget<br>
            General Med: 3.2% under budget<br>
            AI systems: +15% savings
        </div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    # Trend analysis and actions
    st.markdown('<div class="compact-header">TRENDS</div>', unsafe_allow_html=True)
    
    # 24-hour cost trend
    trend_fig = go.Figure(data=go.Scatter(
        x=trends['hours'],
        y=trends['costs'],
        mode='lines',
        line=dict(color='#1c83e1', width=1.5),
        fill='tozeroy',
        fillcolor='rgba(28, 131, 225, 0.1)',
        showlegend=False
    ))
    
    trend_fig.update_layout(
        template="plotly_dark",
        height=120,
        margin=dict(l=10, r=10, t=5, b=20),
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, showticklabels=False),
        plot_bgcolor='#262730',
        paper_bgcolor='#262730'
    )
    
    st.plotly_chart(trend_fig, use_container_width=True, key="trend_24h")
    
    # Quick actions
    st.markdown('<div style="font-size: 0.8rem; margin-top: 0.5rem;">', unsafe_allow_html=True)
    
    if st.button("🚨 Alert Mgmt", use_container_width=True, key="alerts_mgmt"):
        st.success("Alert dashboard opened")
    
    if st.button("📊 Deep Dive", use_container_width=True, key="deep_dive"):
        st.info("Analytics module launched")
    
    if st.button("⚡ Auto-Fix", use_container_width=True, key="auto_fix"):
        st.info("AI optimization initiated")
    
    if st.button("📈 Forecast", use_container_width=True, key="forecast"):
        st.info("Predictive model launched")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Bottom row - comprehensive analytics
st.markdown('<div class="compact-header">COMPREHENSIVE COST ANALYTICS</div>', unsafe_allow_html=True)

chart_col1, chart_col2 = st.columns(2, gap="small")

with chart_col1:
    # Department comparison radar chart
    categories = ['Cost Efficiency', 'Budget Adherence', 'Patient Volume', 'Quality Score', 'AI Utilization']
    
    fig_radar = go.Figure()
    
    # Sample data for top 3 departments
    for i, dept in enumerate(['Emergency', 'Cardiology', 'Surgery']):
        values = [np.random.uniform(60, 95) for _ in categories]
        values.append(values[0])  # Complete the circle
        
        fig_radar.add_trace(go.Scatterpolar(
            r=values,
            theta=categories + [categories[0]],
            fill='toself',
            name=dept,
            opacity=0.6
        ))
    
    fig_radar.update_layout(
        template="plotly_dark",
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        ),
        showlegend=True,
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor='#262730',
        paper_bgcolor='#262730'
    )
    
    st.plotly_chart(fig_radar, use_container_width=True)

with chart_col2:
    # Cost distribution and variance heatmap
    dept_short = [d[:6] for d in dept_data['Department']]
    variance_data = [[dept_data['Variance'][i]] for i in range(len(dept_short))]
    
    fig_heat = go.Figure(data=go.Heatmap(
        z=variance_data,
        x=['Budget Variance %'],
        y=dept_short,
        colorscale=[
            [0, '#dc3545'],      # Red for negative
            [0.5, '#ffc107'],    # Yellow for neutral  
            [1, '#28a745']       # Green for positive
        ],
        zmid=0,
        colorbar=dict(title="Variance %")
    ))
    
    fig_heat.update_layout(
        template="plotly_dark",
        height=300,
        margin=dict(l=80, r=20, t=20, b=20),
        plot_bgcolor='#262730',
        paper_bgcolor='#262730'
    )
    
    st.plotly_chart(fig_heat, use_container_width=True)

# Ultra-compact footer
st.markdown('<div style="margin-top: 1rem; text-align: center; color: #6c757d; font-size: 0.8rem; border-top: 1px solid #3d3d3d; padding-top: 0.5rem;">', unsafe_allow_html=True)
st.markdown(f"Data-Dense Powerhouse • Financial Operations • Live Data • {datetime.now().strftime('%H:%M:%S')}")
st.markdown('</div>', unsafe_allow_html=True)

# Compact sidebar with live metrics
with st.sidebar:
    st.markdown("### 💰 Financial Ops")
    st.markdown("*Data-Dense Powerhouse*")
    
    st.markdown("---")
    
    st.markdown(f"""
    **Live Financial Metrics:**
    - Total Cost: ${metrics['total_monthly']/1000000:.2f}M
    - Daily Burn: ${metrics['daily_burn']/1000:.0f}K
    - AI Savings: ${metrics['ai_savings']/1000:.0f}K
    - Efficiency: {metrics['efficiency_score']:.1f}%
    - Budget Util: {metrics['budget_utilization']:.1f}%
    """)
    
    st.markdown("---")
    
    st.markdown(f"""
    **Alert Summary:**
    - 🔴 Critical: {metrics['alerts_critical']}
    - 🟡 Warning: {metrics['alerts_warning']}
    - ✅ Positive: 3
    """)
    
    st.markdown("---")
    
    st.markdown("""
    **Style Features:**
    - 🌃 Dark monitoring theme
    - 📊 Ultra-high data density
    - ⚡ Real-time financial metrics
    - 🎛️ Expert analyst controls
    - 📈 Live trend analysis
    """)
    
    st.markdown("---")
    
    st.markdown("**Compare styles:**")
    st.markdown("• Style1: Corporate Standard")
    st.markdown("• Style2: Modern Minimalist")
    
    # Auto-refresh controls
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.experimental_rerun()
    
    if st.button("📊 Export Dashboard", use_container_width=True):
        st.success("Dashboard exported")
