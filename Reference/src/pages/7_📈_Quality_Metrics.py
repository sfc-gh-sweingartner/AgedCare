"""
Quality Metrics Page
Analyzes care quality indicators and guideline adherence
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from connection_helper import get_snowflake_connection, execute_query

# Page config
st.set_page_config(
    page_title="Quality Metrics",
    page_icon="📈",
    layout="wide"
)

def load_quality_overview(conn):
    """Load quality metrics overview"""
    query = """
    WITH quality_stats AS (
        SELECT 
            pa.PATIENT_ID,
            ARRAY_SIZE(pa.AI_ANALYSIS_JSON:quality_metrics:care_quality:quality_indicators) as indicator_count,
            ARRAY_SIZE(pa.AI_ANALYSIS_JSON:quality_metrics:care_quality:guideline_adherence) as guideline_count
        FROM PATIENT_ANALYSIS pa
    )
    SELECT 
        COUNT(DISTINCT PATIENT_ID) as total_patients,
        AVG(indicator_count) as avg_indicators_per_patient,
        AVG(guideline_count) as avg_guidelines_per_patient,
        SUM(indicator_count) as total_quality_checks,
        SUM(guideline_count) as total_guideline_checks
    FROM quality_stats
    """
    return execute_query(query, conn)

def load_quality_indicators(conn):
    """Load quality indicator compliance rates"""
    query = """
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS,
            GENDER
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    ), indicators_expanded AS (
        SELECT 
            pa.PATIENT_ID,
            qi.value:indicator::STRING as quality_indicator,
            CASE 
                WHEN UPPER(qi.value:met::STRING) IN ('TRUE', '1', 'YES', 'Y') THEN TRUE
                WHEN UPPER(qi.value:met::STRING) IN ('FALSE', '0', 'NO', 'N') THEN FALSE
                ELSE NULL
            END as met,
            qi.value:details::STRING as details,
            p.AGE_YEARS,
            p.GENDER
        FROM PATIENT_ANALYSIS pa
        JOIN parsed_pmc p ON pa.PATIENT_ID = p.PATIENT_ID,
        LATERAL FLATTEN(input => pa.AI_ANALYSIS_JSON:quality_metrics:care_quality:quality_indicators) qi
        WHERE qi.value:met::STRING IS NOT NULL 
        AND UPPER(qi.value:met::STRING) NOT IN ('NOT SPECIFIED', 'UNKNOWN', 'N/A', '')
    )
    SELECT 
        quality_indicator,
        COUNT(DISTINCT PATIENT_ID) as total_patients,
        COUNT(DISTINCT CASE WHEN met THEN PATIENT_ID END) as compliant_patients,
        ROUND(100.0 * compliant_patients / total_patients, 1) as compliance_rate,
        AVG(CASE WHEN met THEN AGE_YEARS END) as avg_age_compliant,
        AVG(CASE WHEN NOT met THEN AGE_YEARS END) as avg_age_non_compliant
    FROM indicators_expanded
    GROUP BY quality_indicator
    HAVING total_patients > 5
    ORDER BY compliance_rate DESC
    """
    return execute_query(query, conn)

def load_guideline_adherence(conn):
    """Load guideline adherence data"""
    query = """
    WITH guidelines_expanded AS (
        SELECT 
            pa.PATIENT_ID,
            ga.value:guideline::STRING as guideline,
            CASE 
                WHEN UPPER(ga.value:adherent::STRING) IN ('TRUE', '1', 'YES', 'Y') THEN TRUE
                WHEN UPPER(ga.value:adherent::STRING) IN ('FALSE', '0', 'NO', 'N') THEN FALSE
                ELSE NULL
            END as adherent,
            ga.value:gaps::ARRAY as gaps,
            ARRAY_SIZE(ga.value:gaps) as gap_count,
            pa.AI_ANALYSIS_JSON:pattern_recognition:clinical_patterns:presentation_type::STRING as PRESENTATION_TYPE,
            pa.AI_ANALYSIS_JSON:cost_analysis:financial_impact:estimated_cost_category::STRING as ESTIMATED_COST_CATEGORY
        FROM PATIENT_ANALYSIS pa,
        LATERAL FLATTEN(input => pa.AI_ANALYSIS_JSON:quality_metrics:care_quality:guideline_adherence) ga
        WHERE ga.value:adherent::STRING IS NOT NULL 
        AND UPPER(ga.value:adherent::STRING) NOT IN ('NOT SPECIFIED', 'UNKNOWN', 'N/A', '')
    )
    SELECT 
        guideline,
        COUNT(DISTINCT PATIENT_ID) as patient_count,
        COUNT(DISTINCT CASE WHEN adherent THEN PATIENT_ID END) as adherent_count,
        ROUND(100.0 * adherent_count / patient_count, 1) as adherence_rate,
        AVG(gap_count) as avg_gaps_per_patient,
        COUNT(DISTINCT CASE WHEN ESTIMATED_COST_CATEGORY IN ('high', 'very_high') THEN PATIENT_ID END) as high_cost_patients
    FROM guidelines_expanded
    GROUP BY guideline
    ORDER BY adherence_rate ASC
    """
    return execute_query(query, conn)

def load_quality_by_diagnosis(conn):
    """Load quality metrics by diagnosis"""
    query = """
    WITH dx_quality AS (
        SELECT 
            dx.value:diagnosis::STRING as diagnosis,
            pa.PATIENT_ID,
            ARRAY_SIZE(pa.AI_ANALYSIS_JSON:quality_metrics:care_quality:quality_indicators) as quality_checks,
            ARRAY_SIZE(pa.AI_ANALYSIS_JSON:quality_metrics:care_quality:guideline_adherence) as guideline_checks
        FROM PATIENT_ANALYSIS pa,
        LATERAL FLATTEN(input => pa.AI_ANALYSIS_JSON:differential_diagnosis:diagnostic_assessment:differential_diagnoses) dx
        WHERE dx.value:confidence::STRING = 'high'
    )
    SELECT 
        diagnosis,
        COUNT(DISTINCT PATIENT_ID) as patient_count,
        AVG(quality_checks) as avg_quality_checks,
        AVG(guideline_checks) as avg_guideline_checks,
        SUM(quality_checks + guideline_checks) as total_checks
    FROM dx_quality
    GROUP BY diagnosis
    HAVING patient_count > 5
    ORDER BY total_checks DESC
    LIMIT 15
    """
    return execute_query(query, conn)

def load_improvement_opportunities(conn):
    """Load quality improvement opportunities"""
    query = """
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    ), opportunities AS (
        SELECT 
            pa.PATIENT_ID,
            p.AGE_YEARS,
            pa.AI_ANALYSIS_JSON:cost_analysis:financial_impact:estimated_cost_category::STRING as ESTIMATED_COST_CATEGORY,
            gap.value::STRING as opportunities
        FROM PATIENT_ANALYSIS pa
        JOIN parsed_pmc p ON pa.PATIENT_ID = p.PATIENT_ID,
        LATERAL FLATTEN(input => pa.AI_ANALYSIS_JSON:quality_metrics:care_quality:guideline_adherence) ga,
        LATERAL FLATTEN(input => ga.value:gaps, OUTER => TRUE) gap
    )
    SELECT 
        opportunities::STRING as improvement_opportunity,
        COUNT(DISTINCT PATIENT_ID) as affected_patients,
        AVG(AGE_YEARS) as avg_age,
        COUNT(DISTINCT CASE WHEN ESTIMATED_COST_CATEGORY IN ('high', 'very_high') THEN PATIENT_ID END) as high_cost_patients
    FROM opportunities
    WHERE opportunities IS NOT NULL
    GROUP BY improvement_opportunity
    ORDER BY affected_patients DESC
    LIMIT 20
    """
    return execute_query(query, conn)

def load_quality_trends(conn):
    """Load quality metrics by patient characteristics"""
    query = """
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    ), quality_by_age AS (
        SELECT 
            CASE 
                WHEN p.AGE_YEARS < 18 THEN 'Pediatric'
                WHEN p.AGE_YEARS < 40 THEN 'Young Adult'
                WHEN p.AGE_YEARS < 65 THEN 'Adult'
                ELSE 'Senior'
            END as age_group,
            pa.PATIENT_ID,
            ARRAY_SIZE(pa.AI_ANALYSIS_JSON:quality_metrics:care_quality:quality_indicators) as quality_indicators,
            ARRAY_SIZE(pa.AI_ANALYSIS_JSON:quality_metrics:care_quality:guideline_adherence) as guidelines
        FROM PATIENT_ANALYSIS pa
        JOIN parsed_pmc p ON pa.PATIENT_ID = p.PATIENT_ID
    )
    SELECT 
        age_group,
        COUNT(DISTINCT PATIENT_ID) as patient_count,
        AVG(quality_indicators) as avg_quality_indicators,
        AVG(guidelines) as avg_guidelines,
        SUM(quality_indicators) as total_quality_checks,
        SUM(guidelines) as total_guideline_checks
    FROM quality_by_age
    GROUP BY age_group
    ORDER BY 
        CASE age_group
            WHEN 'Pediatric' THEN 1
            WHEN 'Young Adult' THEN 2
            WHEN 'Adult' THEN 3
            ELSE 4
        END
    """
    return execute_query(query, conn)

def load_safety_events(conn):
    """Load safety events and near misses with parsed finding details"""
    query = """
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    ), safety_events_parsed AS (
        SELECT 
            pa.PATIENT_ID,
            finding.value:category::STRING as category,
            finding.value:finding::STRING as finding_text,
            finding.value:severity::STRING as severity,
            p.AGE_YEARS,
            pa.AI_ANALYSIS_JSON:cost_analysis:financial_impact:estimated_cost_category::STRING as ESTIMATED_COST_CATEGORY,
            ca.ESTIMATED_ENCOUNTER_COST
        FROM PATIENT_ANALYSIS pa
        JOIN parsed_pmc p ON pa.PATIENT_ID = p.PATIENT_ID
        LEFT JOIN COST_ANALYSIS ca ON pa.PATIENT_ID = ca.PATIENT_ID,
        LATERAL FLATTEN(input => pa.AI_ANALYSIS_JSON:differential_diagnosis:clinical_findings:key_findings) finding
        WHERE finding.value:finding::STRING IS NOT NULL
        AND finding.value:category::STRING IS NOT NULL
        AND finding.value:severity::STRING IS NOT NULL
    )
    SELECT 
        category,
        finding_text,
        severity,
        COUNT(DISTINCT PATIENT_ID) as incident_count,
        AVG(AGE_YEARS) as avg_age,
        AVG(ESTIMATED_ENCOUNTER_COST) as avg_cost,
        -- Create a combined key for grouping similar findings
        CONCAT('{\"category\":\"', category, '\",\"finding\":\"', LEFT(finding_text, 50), 
               CASE WHEN LENGTH(finding_text) > 50 THEN '...' ELSE '' END, 
               '\",\"severity\":\"', severity, '\"}') as event_summary
    FROM safety_events_parsed
    WHERE category IS NOT NULL 
    AND finding_text IS NOT NULL 
    AND severity IS NOT NULL
    GROUP BY category, finding_text, severity
    HAVING incident_count >= 1
    ORDER BY incident_count DESC, avg_cost DESC NULLS LAST
    LIMIT 50
    """
    return execute_query(query, conn)

def calculate_quality_score(row):
    """Calculate composite quality score"""
    if pd.isna(row['COMPLIANCE_RATE']):
        return 0
    
    # Weight different factors
    compliance_weight = 0.4
    consistency_weight = 0.3
    coverage_weight = 0.3
    
    # Normalize values
    compliance_score = row['COMPLIANCE_RATE'] / 100
    consistency_score = 1 - (abs(row.get('AVG_AGE_COMPLIANT', 50) - row.get('AVG_AGE_NON_COMPLIANT', 50)) / 50)
    coverage_score = min(row['TOTAL_PATIENTS'] / 100, 1)  # Cap at 100 patients
    
    return (compliance_score * compliance_weight + 
            consistency_score * consistency_weight + 
            coverage_score * coverage_weight) * 100

def main():
    st.title("📈 Quality Metrics Dashboard")
    st.markdown("Monitor care quality indicators and clinical guideline adherence")
    
    # Initialize connection
    conn = get_snowflake_connection()
    if not conn:
        st.error("Failed to connect to Snowflake. Please check your connection settings.")
        return
    
    # Load overview data
    with st.spinner("Loading quality metrics data..."):
        overview_df = load_quality_overview(conn)
    
    if overview_df.empty or overview_df.iloc[0]['TOTAL_PATIENTS'] == 0:
        st.warning("No quality metrics data available. Please run batch processing first.")
        return
    
    overview = overview_df.iloc[0]
    
    # Display key metrics
    st.markdown("### 🏥 Quality Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Patients Analyzed",
            f"{int(overview['TOTAL_PATIENTS']):,}",
            help="Total patients with quality metrics"
        )
    
    with col2:
        st.metric(
            "Quality Checks",
            f"{int(overview['TOTAL_QUALITY_CHECKS']):,}",
            f"Avg {overview['AVG_INDICATORS_PER_PATIENT']:.1f} per patient",
            help="Total quality indicators evaluated"
        )
    
    with col3:
        st.metric(
            "Guideline Checks",
            f"{int(overview['TOTAL_GUIDELINE_CHECKS']):,}",
            f"Avg {overview['AVG_GUIDELINES_PER_PATIENT']:.1f} per patient",
            help="Total guideline adherence checks"
        )
    
    with col4:
        total_checks = overview['TOTAL_QUALITY_CHECKS'] + overview['TOTAL_GUIDELINE_CHECKS']
        st.metric(
            "Total Assessments",
            f"{int(total_checks):,}",
            help="Combined quality and guideline assessments"
        )
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Quality Indicators", "Guidelines", "By Diagnosis", "Trends", "Improvements", "Safety"
    ])
    
    with tab1:
        st.markdown("### 📊 Quality Indicator Compliance")
        
        indicators_df = load_quality_indicators(conn)
        
        if not indicators_df.empty:
            # Calculate composite quality scores
            indicators_df['QUALITY_SCORE'] = indicators_df.apply(calculate_quality_score, axis=1)
            
            # Compliance rate visualization
            fig_compliance = px.bar(
                indicators_df.sort_values('COMPLIANCE_RATE', ascending=True),
                x='COMPLIANCE_RATE',
                y='QUALITY_INDICATOR',
                orientation='h',
                title='Quality Indicator Compliance Rates',
                labels={'COMPLIANCE_RATE': 'Compliance Rate (%)', 'QUALITY_INDICATOR': 'Quality Indicator'},
                color='COMPLIANCE_RATE',
                color_continuous_scale='RdYlGn',
                range_color=[0, 100],
                hover_data=['TOTAL_PATIENTS', 'COMPLIANT_PATIENTS']
            )
            fig_compliance.update_layout(height=600)
            fig_compliance.add_vline(x=80, line_dash="dash", line_color="gray", 
                                   annotation_text="Target: 80%")
            st.plotly_chart(fig_compliance, use_container_width=True)
            
            # Performance summary
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # High performers
                high_performers = indicators_df[indicators_df['COMPLIANCE_RATE'] >= 80]
                if not high_performers.empty:
                    st.success(f"✅ **{len(high_performers)} indicators** meet or exceed 80% target")
                    
                    with st.expander("View High-Performing Indicators"):
                        st.dataframe(
                            high_performers[['QUALITY_INDICATOR', 'COMPLIANCE_RATE', 'TOTAL_PATIENTS']],
                            hide_index=True
                        )
            
            with col2:
                # Low performers
                low_performers = indicators_df[indicators_df['COMPLIANCE_RATE'] < 60]
                if not low_performers.empty:
                    st.error(f"⚠️ **{len(low_performers)} indicators** below 60% compliance")
                    
                    with st.expander("View Low-Performing Indicators"):
                        st.dataframe(
                            low_performers[['QUALITY_INDICATOR', 'COMPLIANCE_RATE', 'TOTAL_PATIENTS']],
                            hide_index=True
                        )
            
            # Composite quality score
            st.markdown("#### Composite Quality Scores")
            
            fig_quality = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = indicators_df['QUALITY_SCORE'].mean(),
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Overall Quality Score"},
                delta = {'reference': 75},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 75], 'color': "yellow"},
                        {'range': [75, 100], 'color': "lightgreen"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig_quality.update_layout(height=300)
            st.plotly_chart(fig_quality, use_container_width=True)
    
    with tab2:
        st.markdown("### 📋 Clinical Guideline Adherence")
        
        guidelines_df = load_guideline_adherence(conn)
        
        if not guidelines_df.empty:
            # Guideline adherence chart
            fig_guidelines = px.scatter(
                guidelines_df,
                x='ADHERENCE_RATE',
                y='AVG_GAPS_PER_PATIENT',
                size='PATIENT_COUNT',
                color='HIGH_COST_PATIENTS',
                title='Guideline Adherence vs. Care Gaps',
                labels={
                    'ADHERENCE_RATE': 'Adherence Rate (%)',
                    'AVG_GAPS_PER_PATIENT': 'Average Gaps per Patient',
                    'HIGH_COST_PATIENTS': 'High-Cost Patients'
                },
                hover_data=['GUIDELINE'],
                color_continuous_scale='Reds',
                render_mode='svg'
            )
            fig_guidelines.add_vline(x=70, line_dash="dash", line_color="gray")
            fig_guidelines.add_hline(y=2, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_guidelines, use_container_width=True)
            
            # Guideline details
            st.markdown("#### Guideline Performance Details")
            
            # Sort by adherence rate (ascending to show worst first)
            guidelines_sorted = guidelines_df.sort_values('ADHERENCE_RATE')
            
            # Color code based on performance
            def adherence_color(rate):
                if rate >= 80:
                    return "🟢"
                elif rate >= 60:
                    return "🟡"
                else:
                    return "🔴"
            
            guidelines_sorted['Status'] = guidelines_sorted['ADHERENCE_RATE'].apply(adherence_color)
            
            display_cols = ['Status', 'GUIDELINE', 'ADHERENCE_RATE', 'PATIENT_COUNT', 'AVG_GAPS_PER_PATIENT']
            guidelines_display = guidelines_sorted[display_cols].copy()
            guidelines_display.columns = ['Status', 'Guideline', 'Adherence %', 'Patients', 'Avg Gaps']
            
            st.dataframe(guidelines_display, hide_index=True)
            
            # Gap analysis
            total_gaps = (guidelines_df['AVG_GAPS_PER_PATIENT'] * guidelines_df['PATIENT_COUNT']).sum()
            st.warning(f"📊 Total care gaps identified: {int(total_gaps):,} across all guidelines")
    
    with tab3:
        st.markdown("### 🩺 Quality Metrics by Diagnosis")
        
        dx_quality_df = load_quality_by_diagnosis(conn)
        
        if not dx_quality_df.empty:
            # Diagnosis quality bubble chart
            fig_dx = px.scatter(
                dx_quality_df,
                x='AVG_QUALITY_CHECKS',
                y='AVG_GUIDELINE_CHECKS',
                size='PATIENT_COUNT',
                color='TOTAL_CHECKS',
                text='DIAGNOSIS',
                title='Quality Assessment Coverage by Diagnosis',
                labels={
                    'AVG_QUALITY_CHECKS': 'Avg Quality Indicators',
                    'AVG_GUIDELINE_CHECKS': 'Avg Guidelines Checked'
                },
                color_continuous_scale='Viridis'
            )
            fig_dx.update_traces(textposition='top center')
            st.plotly_chart(fig_dx, use_container_width=True)
            
            # Diagnosis ranking
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("#### Most Monitored Diagnoses")
                top_monitored = dx_quality_df.nlargest(5, 'TOTAL_CHECKS')
                st.dataframe(
                    top_monitored[['DIAGNOSIS', 'TOTAL_CHECKS', 'PATIENT_COUNT']],
                    hide_index=True
                )
            
            with col2:
                st.markdown("#### Least Monitored Diagnoses")
                least_monitored = dx_quality_df.nsmallest(5, 'TOTAL_CHECKS')
                if not least_monitored.empty:
                    st.warning("⚠️ These diagnoses may need more quality oversight")
                    st.dataframe(
                        least_monitored[['DIAGNOSIS', 'TOTAL_CHECKS', 'PATIENT_COUNT']],
                        hide_index=True
                    )
    
    with tab4:
        st.markdown("### 📈 Quality Trends Analysis")
        
        trends_df = load_quality_trends(conn)
        
        if not trends_df.empty:
            # Age group quality metrics
            fig_trends = go.Figure()
            
            fig_trends.add_trace(go.Bar(
                name='Quality Indicators',
                x=trends_df['AGE_GROUP'],
                y=trends_df['AVG_QUALITY_INDICATORS'],
                marker_color='lightblue',
                yaxis='y'
            ))
            
            fig_trends.add_trace(go.Bar(
                name='Guidelines',
                x=trends_df['AGE_GROUP'],
                y=trends_df['AVG_GUIDELINES'],
                marker_color='lightgreen',
                yaxis='y'
            ))
            
            fig_trends.update_layout(
                title='Average Quality Assessments by Age Group',
                xaxis_title='Age Group',
                yaxis_title='Average Assessments per Patient',
                barmode='group',
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_trends, use_container_width=True)
            
            # Insights
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Find age group with most assessments
                max_assessments = trends_df.loc[trends_df['TOTAL_QUALITY_CHECKS'].idxmax()]
                st.info(
                    f"📊 **{max_assessments['AGE_GROUP']}** patients receive the most quality assessments "
                    f"({max_assessments['AVG_QUALITY_INDICATORS']:.1f} indicators per patient)"
                )
            
            with col2:
                # Total coverage
                total_assessments = trends_df['TOTAL_QUALITY_CHECKS'].sum() + trends_df['TOTAL_GUIDELINE_CHECKS'].sum()
                total_patients = trends_df['PATIENT_COUNT'].sum()
                avg_per_patient = total_assessments / total_patients if total_patients > 0 else 0
                
                st.metric(
                    "Average Assessments per Patient",
                    f"{avg_per_patient:.1f}",
                    help="Combined quality indicators and guidelines per patient"
                )
    
    with tab5:
        st.markdown("### 💡 Improvement Opportunities")
        
        improvements_df = load_improvement_opportunities(conn)
        
        if not improvements_df.empty:
            # Improvement opportunities visualization
            fig_improve = px.treemap(
                improvements_df,
                path=['IMPROVEMENT_OPPORTUNITY'],
                values='AFFECTED_PATIENTS',
                color='HIGH_COST_PATIENTS',
                title='Quality Improvement Opportunities by Impact',
                color_continuous_scale='Oranges'
            )
            fig_improve.update_layout(height=500)
            st.plotly_chart(fig_improve, use_container_width=True)
            
            # Priority improvements
            st.markdown("#### Priority Improvement Areas")
            
            # Calculate impact score
            improvements_df['IMPACT_SCORE'] = (
                improvements_df['AFFECTED_PATIENTS'] * 0.6 +
                improvements_df['HIGH_COST_PATIENTS'] * 0.4
            )
            
            priority_improvements = improvements_df.nlargest(10, 'IMPACT_SCORE')
            
            for idx, improvement in priority_improvements.iterrows():
                impact_level = "🔴 High" if improvement['HIGH_COST_PATIENTS'] > 5 else "🟡 Medium"
                
                with st.expander(f"{improvement['IMPROVEMENT_OPPORTUNITY'][:50]}... ({improvement['AFFECTED_PATIENTS']} patients)"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Affected Patients", improvement['AFFECTED_PATIENTS'])
                    
                    with col2:
                        st.metric("High-Cost Patients", improvement['HIGH_COST_PATIENTS'])
                    
                    with col3:
                        st.metric("Impact Level", impact_level)
                    
                    st.write(f"Average age of affected patients: {improvement['AVG_AGE']:.1f} years")
        else:
            st.info("No specific improvement opportunities identified in the current data.")
    
    with tab6:
        st.markdown("### 🚨 Safety Events & Near Misses")
        
        safety_df = load_safety_events(conn)
        
        if not safety_df.empty and len(safety_df) > 0:
            # Create severity mapping for bubble sizes
            severity_size_map = {'mild': 10, 'moderate': 20, 'severe': 30}
            safety_df['bubble_size'] = safety_df['SEVERITY'].map(severity_size_map).fillna(15)
            
            # Create category color mapping
            category_colors = {
                'symptom': '#1f77b4',      # Blue
                'sign': '#ff7f0e',         # Orange  
                'imaging': '#2ca02c',      # Green
                'lab': '#d62728',          # Red
                'psychiatric symptom': '#9467bd',  # Purple
                'functional': '#8c564b',   # Brown
                'cognitive assessment': '#e377c2',  # Pink
                'comorbidity': '#7f7f7f'   # Gray
            }
            
            # Safety events bubble chart
            fig_safety = px.scatter(
                safety_df,
                x='INCIDENT_COUNT',
                y='AVG_COST',
                size='bubble_size',
                color='CATEGORY',
                hover_name='FINDING_TEXT',
                title='Safety Events & Near Misses Analysis',
                labels={
                    'INCIDENT_COUNT': 'Number of Incidents', 
                    'AVG_COST': 'Average Cost ($)',
                    'CATEGORY': 'Category',
                    'FINDING_TEXT': 'Finding'
                },
                color_discrete_map=category_colors,
                hover_data={
                    'SEVERITY': True,
                    'AVG_AGE': ':.1f',
                    'bubble_size': False
                },
                size_max=40
            )
            
            # Customize the bubble chart
            fig_safety.update_layout(
                height=600,
                showlegend=True,
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=1.01
                )
            )
            
            # Add grid lines for better readability
            fig_safety.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            fig_safety.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
            
            st.plotly_chart(fig_safety, use_container_width=True)
            
            # Add legend explanation
            st.markdown("""
            **Chart Legend:**
            - **Bubble Size**: Severity (Larger = More Severe)
            - **Color**: Clinical Category 
            - **X-axis**: Number of Incidents
            - **Y-axis**: Average Cost when Event Occurs
            """)
            
            # Safety metrics summary
            total_events = safety_df['INCIDENT_COUNT'].sum()
            avg_cost_with_event = safety_df['AVG_COST'].mean()
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                st.error(f"⚠️ Total safety events: {int(total_events)}")
                
            with col2:
                st.metric(
                    "Average cost when safety event occurs",
                    f"${avg_cost_with_event:,.0f}" if not pd.isna(avg_cost_with_event) else "N/A"
                )
            
            with col3:
                # Most common events by category
                if len(safety_df) > 0:
                    top_event = safety_df.iloc[0]
                    st.warning(
                        f"Most common: **{top_event['CATEGORY']}** findings "
                        f"({top_event['INCIDENT_COUNT']} occurrences)"
                    )
            
            # Detailed breakdown by category and severity
            st.markdown("#### Event Breakdown by Category and Severity")
            
            # Create summary tables
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("**By Category**")
                category_summary = safety_df.groupby('CATEGORY').agg({
                    'INCIDENT_COUNT': 'sum',
                    'AVG_COST': 'mean'
                }).reset_index()
                category_summary = category_summary.sort_values('INCIDENT_COUNT', ascending=False)
                category_summary['AVG_COST'] = category_summary['AVG_COST'].round(0)
                st.dataframe(category_summary, hide_index=True)
            
            with col2:
                st.markdown("**By Severity**")
                severity_summary = safety_df.groupby('SEVERITY').agg({
                    'INCIDENT_COUNT': 'sum',
                    'AVG_COST': 'mean'
                }).reset_index()
                severity_summary = severity_summary.sort_values('INCIDENT_COUNT', ascending=False)
                severity_summary['AVG_COST'] = severity_summary['AVG_COST'].round(0)
                st.dataframe(severity_summary, hide_index=True)
                
        else:
            st.success("✅ No safety events or near misses reported in the current data.")
    
    # Action Plan Section
    st.markdown("---")
    st.markdown("### 📋 Quality Improvement Action Plan")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### Immediate Actions")
        st.markdown("""
        1. **Address Low-Compliance Indicators**
           - Focus on indicators below 60% compliance
           - Implement targeted education programs
           - Create automated reminders
        
        2. **Close Care Gaps**
           - Prioritize guidelines with highest gap counts
           - Develop standardized protocols
           - Monitor adherence weekly
        
        3. **Safety Event Prevention**
           - Analyze root causes of reported events
           - Implement preventive measures
           - Create safety checklists
        """)
    
    with col2:
        st.markdown("#### Long-term Strategy")
        st.markdown("""
        1. **Quality Culture Development**
           - Regular quality rounds
           - Staff training programs
           - Recognition for high performers
        
        2. **Technology Enhancement**
           - Real-time quality dashboards
           - Automated compliance tracking
           - Predictive quality analytics
        
        3. **Continuous Improvement**
           - Monthly quality reviews
           - Benchmark against best practices
           - Patient outcome tracking
        """)
    
    # Generate report button
    st.markdown("---")
    if st.button("📄 Generate Quality Report", type="primary"):
        st.success("Quality report generated! (In production, this would create a comprehensive PDF report)")
    
    # Do not close the cached global connection; other pages reuse it.

if __name__ == "__main__":
    main()