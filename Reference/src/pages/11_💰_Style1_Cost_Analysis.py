"""
Style 1: Corporate Standard - Cost Analysis
==========================================

Professional, stable interface using native Streamlit components only.
Designed for conservative healthcare organizations and regulatory environments.

Features:
- Native Streamlit components exclusively
- Professional blue color scheme
- Clear bordered sections (CSS-based for compatibility)
- Traditional table and chart layouts
- Maximum stability
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
    page_title="Style 1: Corporate Standard - Cost Analysis",
    page_icon="💰",
    layout="wide"
)

# Corporate Standard CSS
st.markdown("""
<style>
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

.cost-metric {
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    margin: 10px 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.cost-alert {
    background: #fff3cd;
    border: 1px solid #ffeaa7;
    border-left: 4px solid #f39c12;
    border-radius: 4px;
    padding: 15px;
    margin: 10px 0;
}

.cost-savings {
    background: #d4edda;
    border: 1px solid #c3e6cb;
    border-left: 4px solid #28a745;
    border-radius: 4px;
    padding: 15px;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

# Style indicator
st.markdown('<div class="style-badge">🔵 Style 1: Corporate Standard</div>', unsafe_allow_html=True)

# Header
st.markdown("""
<div class="corporate-header">
    <h1>💰 Healthcare Cost Analysis</h1>
    <h3>Style 1: Corporate Standard</h3>
    <p>Professional Financial Intelligence Dashboard</p>
</div>
""", unsafe_allow_html=True)

# Medical disclaimer
st.markdown("""
<div class="corporate-container">
    <h4>⚠️ Financial Disclaimer</h4>
    <p>This application is for <strong>demonstration purposes only</strong>. 
    Cost estimates and financial analyses are illustrative and should not be used for actual financial planning or billing. 
    Consult qualified healthcare financial professionals for actual cost management.</p>
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

# Main content layout
col1, col2 = st.columns([2, 1])

with col1:
    # Cost overview section
    st.markdown('<div class="corporate-container">', unsafe_allow_html=True)
    st.header("📊 Cost Overview")
    
    # KPI metrics in traditional layout
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    with kpi_col1:
        st.markdown("""
        <div class="cost-metric">
            <h3>Total Monthly Cost</h3>
            <h2 style="color: #0062df;">$2.19M</h2>
            <p>↓ 2.3% vs last month</p>
        </div>
        """, unsafe_allow_html=True)
    
    with kpi_col2:
        st.markdown("""
        <div class="cost-metric">
            <h3>AI-Driven Savings</h3>
            <h2 style="color: #28a745;">$127K</h2>
            <p>↑ 15% vs last month</p>
        </div>
        """, unsafe_allow_html=True)
    
    with kpi_col3:
        st.markdown("""
        <div class="cost-metric">
            <h3>Cost per Patient</h3>
            <h2 style="color: #0062df;">$3,940</h2>
            <p>↓ $120 vs benchmark</p>
        </div>
        """, unsafe_allow_html=True)
    
    with kpi_col4:
        st.markdown("""
        <div class="cost-metric">
            <h3>Efficiency Score</h3>
            <h2 style="color: #28a745;">87%</h2>
            <p>↑ 3 points vs target</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Department cost analysis
    st.markdown('<div class="corporate-container">', unsafe_allow_html=True)
    st.header("🏥 Department Cost Analysis")
    
    # Traditional tabs for different views
    tab1, tab2, tab3 = st.tabs(["Cost by Department", "Budget Variance", "Cost per Patient"])
    
    with tab1:
        # Department cost bar chart
        fig = px.bar(
            dept_df,
            x='Department',
            y='Monthly_Cost',
            title="Monthly Cost by Department",
            color_discrete_sequence=['#0062df'],
            text='Monthly_Cost'
        )
        fig.update_layout(template="plotly_white")
        fig.update_traces(texttemplate='$%{text:,.0f}K', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
        # Cost breakdown table
        st.subheader("Detailed Cost Breakdown")
        
        # Format the data for display
        display_df = dept_df.copy()
        display_df['Monthly_Cost'] = display_df['Monthly_Cost'].apply(lambda x: f"${x:,.0f}")
        display_df['Budget_Variance'] = display_df['Budget_Variance'].apply(lambda x: f"{x:+.1f}%")
        display_df['Cost_per_Patient'] = (dept_df['Monthly_Cost'] / dept_df['Patient_Volume']).apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(
            display_df[['Department', 'Monthly_Cost', 'Budget_Variance', 'Patient_Volume', 'Cost_per_Patient']],
            use_container_width=True,
            hide_index=True
        )
    
    with tab2:
        # Budget variance analysis
        fig = px.bar(
            dept_df,
            x='Department',
            y='Budget_Variance',
            title="Budget Variance by Department (%)",
            color='Budget_Variance',
            color_continuous_scale=['#dc3545', '#ffffff', '#28a745'],
            color_continuous_midpoint=0
        )
        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
        
        # Variance alerts
        for _, row in dept_df.iterrows():
            if abs(row['Budget_Variance']) > 10:
                st.markdown(f"""
                <div class="cost-alert">
                    <strong>⚠️ Budget Alert: {row['Department']}</strong><br>
                    Variance: {row['Budget_Variance']:+.1f}% (${abs(row['Monthly_Cost'] * row['Budget_Variance'] / 100):,.0f})
                </div>
                """, unsafe_allow_html=True)
    
    with tab3:
        # Cost per patient analysis
        dept_df['Cost_per_Patient'] = dept_df['Monthly_Cost'] / dept_df['Patient_Volume']
        
        fig = px.scatter(
            dept_df,
            x='Patient_Volume',
            y='Cost_per_Patient',
            size='Monthly_Cost',
            hover_name='Department',
            title="Cost per Patient vs Patient Volume",
            color_discrete_sequence=['#0062df']
        )
        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # AI impact analysis
    st.markdown('<div class="corporate-container">', unsafe_allow_html=True)
    st.header("🤖 AI Impact on Healthcare Costs")
    
    # Monthly trend
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=monthly_df['Month'],
        y=monthly_df['Total_Cost'],
        mode='lines+markers',
        name='Total Costs',
        line=dict(color='#0062df', width=3),
        marker=dict(size=8)
    ))
    
    fig.add_trace(go.Scatter(
        x=monthly_df['Month'],
        y=monthly_df['AI_Savings'],
        mode='lines+markers',
        name='AI Savings',
        line=dict(color='#28a745', width=3),
        marker=dict(size=8),
        yaxis='y2'
    ))
    
    fig.update_layout(
        title="Monthly Cost Trends and AI Savings",
        template="plotly_white",
        yaxis=dict(title="Total Costs ($)", side="left"),
        yaxis2=dict(title="AI Savings ($)", side="right", overlaying="y"),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # AI savings summary
    total_savings = monthly_df['AI_Savings'].sum()
    st.markdown(f"""
    <div class="cost-savings">
        <h4>💡 AI-Driven Cost Savings Summary</h4>
        <ul>
            <li><strong>Total AI Savings (YTD):</strong> ${total_savings:,.0f}</li>
            <li><strong>Average Monthly Savings:</strong> ${total_savings/len(monthly_df):,.0f}</li>
            <li><strong>Projected Annual Savings:</strong> ${(total_savings/len(monthly_df))*12:,.0f}</li>
            <li><strong>ROI on AI Investment:</strong> 340%</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # Cost alerts and recommendations
    st.markdown('<div class="corporate-container">', unsafe_allow_html=True)
    st.header("🚨 Cost Alerts")
    
    # High-priority alerts
    st.markdown("""
    <div class="cost-alert">
        <h4>⚠️ High Priority</h4>
        <p><strong>ICU Department:</strong><br>
        12.1% over budget<br>
        Action: Review staffing levels</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="cost-alert">
        <h4>⚠️ Medium Priority</h4>
        <p><strong>Oncology Department:</strong><br>
        8.3% over budget<br>
        Action: Analyze treatment costs</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="cost-savings">
        <h4>✅ Positive Trend</h4>
        <p><strong>AI Efficiency:</strong><br>
        15% savings increase<br>
        Continue current initiatives</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Quick actions
    st.markdown('<div class="corporate-container">', unsafe_allow_html=True)
    st.header("🔧 Quick Actions")
    
    if st.button("📊 Generate Cost Report", use_container_width=True):
        st.success("✅ Comprehensive cost report generated")
    
    if st.button("📈 Budget Forecast", use_container_width=True):
        st.info("📋 Navigate to predictive analytics dashboard")
    
    if st.button("💡 Cost Optimization", use_container_width=True):
        st.info("🎯 AI-powered optimization recommendations")
    
    if st.button("📧 Send Alert Summary", use_container_width=True):
        st.success("📨 Alert summary sent to stakeholders")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Performance benchmarks
    st.markdown('<div class="corporate-container">', unsafe_allow_html=True)
    st.header("📏 Benchmarks")
    
    benchmarks = {
        'Industry Average': '$4,200',
        'Top Performers': '$3,600',
        'Our Performance': '$3,940'
    }
    
    for label, value in benchmarks.items():
        color = '#28a745' if label == 'Our Performance' else '#6c757d'
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
            <span>{label}:</span>
            <span style="color: {color}; font-weight: bold;">{value}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.markdown("**Style:** Corporate Standard")
with footer_col2:
    st.markdown("**Page:** Cost Analysis")
with footer_col3:
    st.markdown(f"**Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# Sidebar info
with st.sidebar:
    st.markdown("### 💰 Cost Analysis")
    st.markdown("*Corporate Standard Style*")
    
    st.markdown("---")
    
    st.markdown("""
    **Key Features:**
    - 📊 Department cost breakdowns
    - 📈 Budget variance tracking
    - 🤖 AI impact measurement
    - 🚨 Automated cost alerts
    - 📏 Industry benchmarking
    """)
    
    st.markdown("---")
    
    st.markdown("""
    **Style Features:**
    - ✅ Traditional charts and tables
    - ✅ Professional blue color scheme
    - ✅ Clear bordered sections
    - ✅ Native Streamlit components
    - ✅ Maximum compatibility
    """)
    
    st.markdown("---")
    
    st.markdown("**Compare with other styles:**")
    st.markdown("• Style2: Modern Minimalist")
    st.markdown("• Style3: Data-Dense Powerhouse")
