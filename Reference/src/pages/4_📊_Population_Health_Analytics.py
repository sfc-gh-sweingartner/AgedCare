"""
Population Health Analytics Page
Analyzes patterns across the patient population for insights
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
    page_title="Population Health Analytics",
    page_icon="📊",
    layout="wide"
)

@st.cache_data(ttl=600)
def load_population_overview(_conn):
    """Load overview statistics for the population"""
    query = """
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS,
            GENDER
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
        WHERE PATIENT_ID IS NOT NULL
    )
    SELECT 
        COUNT(DISTINCT pa.PATIENT_ID) as total_patients,
        AVG(p.AGE_YEARS) as avg_age,
        STDDEV(p.AGE_YEARS) as age_stddev,
        COUNT(DISTINCT CASE WHEN pa.AI_ANALYSIS_JSON:pattern_recognition:clinical_patterns:presentation_type::STRING = 'rare' THEN pa.PATIENT_ID END) as rare_presentations,
        COUNT(DISTINCT CASE WHEN pa.AI_ANALYSIS_JSON:cost_analysis:financial_impact:estimated_cost_category::STRING IN ('high', 'very_high') THEN pa.PATIENT_ID END) as high_cost_patients,
        AVG(TRY_TO_NUMBER(pa.AI_ANALYSIS_JSON:pattern_recognition:anomaly_detection:anomaly_score::STRING)) as avg_anomaly_score,
        AVG(ARRAY_SIZE(ma.EXTRACTED_MEDICATIONS)) as avg_medications,
        COUNT(DISTINCT CASE WHEN ma.POLYPHARMACY_RISK_SCORE > 5 THEN pa.PATIENT_ID END) as polypharmacy_patients
    FROM parsed_pmc p
    INNER JOIN HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS pa ON p.PATIENT_ID = pa.PATIENT_ID
    LEFT JOIN HEALTHCARE_DEMO.MEDICAL_NOTES.MEDICATION_ANALYSIS ma ON p.PATIENT_ID = ma.PATIENT_ID
    """
    return execute_query(query, _conn)

@st.cache_data(ttl=600)
def load_age_distribution(_conn):
    """Load age distribution data"""
    query = """
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    ), age_data AS (
        SELECT p.AGE_YEARS
        FROM parsed_pmc p
        INNER JOIN PATIENT_ANALYSIS pa ON p.PATIENT_ID = pa.PATIENT_ID
        WHERE p.AGE_YEARS IS NOT NULL
    )
    SELECT 
        CASE 
            WHEN AGE_YEARS < 18 THEN 'Pediatric (<18)'
            WHEN AGE_YEARS < 40 THEN 'Young Adult (18-39)'
            WHEN AGE_YEARS < 65 THEN 'Adult (40-64)'
            ELSE 'Senior (65+)'
        END as age_group,
        COUNT(*) as patient_count,
        AVG(AGE_YEARS) as avg_age
    FROM age_data
    GROUP BY age_group
    ORDER BY avg_age
    """
    return execute_query(query, _conn)

@st.cache_data(ttl=600)
def load_diagnosis_patterns(_conn):
    """Load common diagnosis patterns"""
    query = """
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS,
            GENDER
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    ), dx_expanded AS (
        SELECT 
            p.PATIENT_ID,
            dx.value:diagnosis::STRING as diagnosis,
            dx.value:confidence::STRING as confidence,
            p.AGE_YEARS,
            p.GENDER
        FROM parsed_pmc p
        INNER JOIN PATIENT_ANALYSIS pa ON p.PATIENT_ID = pa.PATIENT_ID,
        LATERAL FLATTEN(input => pa.AI_ANALYSIS_JSON:differential_diagnosis:diagnostic_assessment:differential_diagnoses) dx
        WHERE pa.AI_ANALYSIS_JSON:differential_diagnosis:diagnostic_assessment:differential_diagnoses IS NOT NULL
    )
    SELECT 
        diagnosis,
        COUNT(DISTINCT PATIENT_ID) as patient_count,
        AVG(AGE_YEARS) as avg_age,
        COUNT(DISTINCT CASE WHEN confidence = 'high' THEN PATIENT_ID END) as high_confidence_count
    FROM dx_expanded
    GROUP BY diagnosis
    HAVING patient_count > 5
    ORDER BY patient_count DESC
    LIMIT 20
    """
    return execute_query(query, _conn)

@st.cache_data(ttl=600)
def load_cost_analysis(_conn):
    """Load cost distribution analysis"""
    query = """
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    )
    SELECT 
        ca.COST_CATEGORY,
        COUNT(DISTINCT p.PATIENT_ID) as patient_count,
        AVG(ca.ESTIMATED_ENCOUNTER_COST) as avg_cost,
        SUM(ca.ESTIMATED_ENCOUNTER_COST) as total_cost,
        AVG(p.AGE_YEARS) as avg_age
    FROM parsed_pmc p
    INNER JOIN PATIENT_ANALYSIS pa ON p.PATIENT_ID = pa.PATIENT_ID
    LEFT JOIN COST_ANALYSIS ca ON p.PATIENT_ID = ca.PATIENT_ID
    WHERE ca.COST_CATEGORY IS NOT NULL
    GROUP BY ca.COST_CATEGORY
    ORDER BY 
        CASE ca.COST_CATEGORY 
            WHEN 'low' THEN 1
            WHEN 'medium' THEN 2
            WHEN 'high' THEN 3
            WHEN 'very_high' THEN 4
        END
    """
    return execute_query(query, _conn)

@st.cache_data(ttl=600)
def load_medication_patterns(_conn):
    """Load medication usage patterns"""
    query = """
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    ), med_expanded AS (
        SELECT 
            p.PATIENT_ID,
            med.value:medication::STRING as medication_name,
            ma.POLYPHARMACY_RISK_SCORE,
            p.AGE_YEARS
        FROM parsed_pmc p
        INNER JOIN PATIENT_ANALYSIS pa ON p.PATIENT_ID = pa.PATIENT_ID
        LEFT JOIN MEDICATION_ANALYSIS ma ON p.PATIENT_ID = ma.PATIENT_ID,
        LATERAL FLATTEN(input => ma.EXTRACTED_MEDICATIONS) med
        WHERE ma.EXTRACTED_MEDICATIONS IS NOT NULL
    )
    SELECT 
        medication_name,
        COUNT(DISTINCT PATIENT_ID) as patient_count,
        AVG(AGE_YEARS) as avg_age,
        AVG(POLYPHARMACY_RISK_SCORE) as avg_polypharmacy_risk
    FROM med_expanded
    GROUP BY medication_name
    HAVING patient_count >= 1
    ORDER BY patient_count DESC
    LIMIT 15
    """
    return execute_query(query, _conn)

@st.cache_data(ttl=600)
def load_quality_metrics_summary(_conn):
    """Load quality metrics summary"""
    query = """
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    ), quality_expanded AS (
        SELECT 
            p.PATIENT_ID,
            qi.value:indicator::STRING as quality_indicator,
            CASE 
                WHEN UPPER(qi.value:met::STRING) IN ('TRUE', '1', 'YES', 'Y') THEN TRUE
                WHEN UPPER(qi.value:met::STRING) IN ('FALSE', '0', 'NO', 'N') THEN FALSE
                ELSE NULL
            END as met,
            p.AGE_YEARS
        FROM parsed_pmc p
        INNER JOIN PATIENT_ANALYSIS pa ON p.PATIENT_ID = pa.PATIENT_ID,
        LATERAL FLATTEN(input => pa.AI_ANALYSIS_JSON:quality_metrics:care_quality:quality_indicators) qi
        WHERE pa.AI_ANALYSIS_JSON:quality_metrics:care_quality:quality_indicators IS NOT NULL
        AND qi.value:met::STRING IS NOT NULL 
        AND UPPER(qi.value:met::STRING) NOT IN ('NOT SPECIFIED', 'UNKNOWN', 'N/A', '')
    )
    SELECT 
        quality_indicator,
        COUNT(DISTINCT PATIENT_ID) as total_patients,
        COUNT(DISTINCT CASE WHEN met THEN PATIENT_ID END) as met_count,
        ROUND(100.0 * met_count / total_patients, 1) as compliance_rate
    FROM quality_expanded
    GROUP BY quality_indicator
    HAVING total_patients > 10
    ORDER BY compliance_rate DESC
    """
    return execute_query(query, _conn)

@st.cache_data(ttl=600)
def load_anomaly_distribution(_conn):
    """Load anomaly score distribution"""
    query = """
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    )
    SELECT 
        ROUND(TRY_TO_NUMBER(pa.AI_ANALYSIS_JSON:pattern_recognition:anomaly_detection:anomaly_score::STRING), 1) as anomaly_bucket,
        COUNT(*) as patient_count,
        pa.AI_ANALYSIS_JSON:pattern_recognition:clinical_patterns:presentation_type::STRING as PRESENTATION_TYPE,
        AVG(ca.ESTIMATED_ENCOUNTER_COST) as avg_cost
    FROM parsed_pmc p
    INNER JOIN PATIENT_ANALYSIS pa ON p.PATIENT_ID = pa.PATIENT_ID
    LEFT JOIN COST_ANALYSIS ca ON p.PATIENT_ID = ca.PATIENT_ID
    WHERE pa.AI_ANALYSIS_JSON:pattern_recognition:anomaly_detection:anomaly_score IS NOT NULL
    GROUP BY anomaly_bucket, pa.AI_ANALYSIS_JSON:pattern_recognition:clinical_patterns:presentation_type::STRING
    ORDER BY anomaly_bucket
    """
    return execute_query(query, _conn)

def main():
    st.title("📊 Population Health Analytics")
    st.markdown("Analyze patterns and trends across the patient population")
    
    # Initialize connection
    conn = get_snowflake_connection()
    if not conn:
        st.error("Failed to connect to Snowflake. Please check your connection settings.")
        return
    
    # Load overview data
    with st.spinner("Loading population data..."):
        overview_df = load_population_overview(conn)
    
    if overview_df.empty:
        st.warning("No population data available. Please run batch processing first.")
        return
    
    # Display key metrics
    st.markdown("### 📈 Population Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    overview = overview_df.iloc[0]
    
    with col1:
        st.metric(
            "Total Patients",
            f"{int(overview['TOTAL_PATIENTS']):,}",
            help="Total number of patients analyzed"
        )
    
    with col2:
        avg_age = overview['AVG_AGE'] if overview['AVG_AGE'] is not None else 0
        age_stddev = overview['AGE_STDDEV'] if overview['AGE_STDDEV'] is not None else 0
        st.metric(
            "Average Age",
            f"{avg_age:.1f} years",
            f"±{age_stddev:.1f}",
            help="Mean age with standard deviation"
        )
    
    with col3:
        high_cost = int(overview['HIGH_COST_PATIENTS']) if overview['HIGH_COST_PATIENTS'] is not None else 0
        total_patients = int(overview['TOTAL_PATIENTS']) if overview['TOTAL_PATIENTS'] is not None else 1
        high_cost_pct = (high_cost / total_patients * 100) if total_patients > 0 else 0
        st.metric(
            "High-Cost Patients",
            f"{high_cost:,}",
            f"{high_cost_pct:.1f}%",
            help="Patients in high or very high cost categories"
        )
    
    with col4:
        rare_presentations = int(overview['RARE_PRESENTATIONS']) if overview['RARE_PRESENTATIONS'] is not None else 0
        rare_pct = (rare_presentations / total_patients * 100) if total_patients > 0 else 0
        st.metric(
            "Rare Presentations",
            f"{rare_presentations:,}",
            f"{rare_pct:.1f}%",
            help="Patients with rare or unusual presentations"
        )
    
    # Create tabs for different analyses
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Demographics", "Diagnoses", "Costs", "Medications", "Quality"
    ])
    
    with tab1:
        st.markdown("### Age Distribution")
        
        age_df = load_age_distribution(conn)
        
        if not age_df.empty:
            # Age group bar chart
            fig_age = px.bar(
                age_df,
                x='AGE_GROUP',
                y='PATIENT_COUNT',
                title='Patient Distribution by Age Group',
                labels={'PATIENT_COUNT': 'Number of Patients', 'AGE_GROUP': 'Age Group'},
                color='PATIENT_COUNT',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_age, use_container_width=True)
            
            # Age statistics table
            st.markdown("#### Age Group Statistics")
            age_stats = age_df[['AGE_GROUP', 'PATIENT_COUNT', 'AVG_AGE']].copy()
            age_stats['Percentage'] = (age_stats['PATIENT_COUNT'] / age_stats['PATIENT_COUNT'].sum() * 100).round(1)
            age_stats.columns = ['Age Group', 'Patient Count', 'Average Age', 'Percentage (%)']
            st.dataframe(age_stats, hide_index=True)
    
    with tab2:
        st.markdown("### Common Diagnoses")
        
        dx_df = load_diagnosis_patterns(conn)
        
        if not dx_df.empty:
            # Top diagnoses bar chart
            fig_dx = px.bar(
                dx_df.head(10),
                x='PATIENT_COUNT',
                y='DIAGNOSIS',
                orientation='h',
                title='Top 10 Most Common Diagnoses',
                labels={'PATIENT_COUNT': 'Number of Patients', 'DIAGNOSIS': 'Diagnosis'},
                color='HIGH_CONFIDENCE_COUNT',
                color_continuous_scale='Viridis',
                hover_data=['AVG_AGE']
            )
            fig_dx.update_layout(height=500)
            st.plotly_chart(fig_dx, use_container_width=True)
            
            # Diagnosis details
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("#### Diagnosis Patterns")
                dx_display = dx_df[['DIAGNOSIS', 'PATIENT_COUNT', 'AVG_AGE', 'HIGH_CONFIDENCE_COUNT']].copy()
                dx_display.columns = ['Diagnosis', 'Patient Count', 'Avg Age', 'High Confidence']
                dx_display['Avg Age'] = dx_display['Avg Age'].fillna(0).round(1)
                st.dataframe(dx_display, hide_index=True, height=300)
            
            with col2:
                # Confidence distribution pie chart
                total_dx = dx_df['PATIENT_COUNT'].sum()
                high_conf = dx_df['HIGH_CONFIDENCE_COUNT'].sum()
                
                fig_conf = go.Figure(data=[go.Pie(
                    labels=['High Confidence', 'Medium/Low Confidence'],
                    values=[high_conf, total_dx - high_conf],
                    hole=.3
                )])
                fig_conf.update_layout(
                    title="Diagnosis Confidence Distribution",
                    height=300
                )
                st.plotly_chart(fig_conf, use_container_width=True)
    
    with tab3:
        st.markdown("### Cost Analysis")
        
        cost_df = load_cost_analysis(conn)
        
        if not cost_df.empty:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Cost category distribution
                fig_cost_dist = px.pie(
                    cost_df,
                    values='PATIENT_COUNT',
                    names='COST_CATEGORY',
                    title='Patient Distribution by Cost Category',
                    color_discrete_map={
                        'low': '#2E7D32',
                        'medium': '#FFA726',
                        'high': '#EF5350',
                        'very_high': '#B71C1C'
                    }
                )
                st.plotly_chart(fig_cost_dist, use_container_width=True)
            
            with col2:
                # Average cost by category
                fig_avg_cost = px.bar(
                    cost_df,
                    x='COST_CATEGORY',
                    y='AVG_COST',
                    title='Average Encounter Cost by Category',
                    labels={'AVG_COST': 'Average Cost ($)', 'COST_CATEGORY': 'Cost Category'},
                    color='COST_CATEGORY',
                    color_discrete_map={
                        'low': '#2E7D32',
                        'medium': '#FFA726', 
                        'high': '#EF5350',
                        'very_high': '#B71C1C'
                    }
                )
                fig_avg_cost.update_layout(showlegend=False)
                st.plotly_chart(fig_avg_cost, use_container_width=True)
            
            # Cost summary metrics
            st.markdown("#### Cost Summary")
            total_cost = cost_df['TOTAL_COST'].sum()
            avg_cost_overall = total_cost / cost_df['PATIENT_COUNT'].sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Healthcare Costs", f"${total_cost:,.0f}")
            with col2:
                st.metric("Average Cost per Patient", f"${avg_cost_overall:,.0f}")
            with col3:
                high_cost_pct = cost_df[cost_df['COST_CATEGORY'].isin(['high', 'very_high'])]['PATIENT_COUNT'].sum()
                high_cost_pct = high_cost_pct / cost_df['PATIENT_COUNT'].sum() * 100
                st.metric("High-Cost Patients", f"{high_cost_pct:.1f}%")
    
    with tab4:
        st.markdown("### Medication Patterns")
        
        med_df = load_medication_patterns(conn)
        
        if not med_df.empty:
            # Most common medications
            fig_meds = px.bar(
                med_df.head(10),
                x='PATIENT_COUNT',
                y='MEDICATION_NAME',
                orientation='h',
                title='Top 10 Most Common Medications',
                labels={'PATIENT_COUNT': 'Number of Patients', 'MEDICATION_NAME': 'Medication'},
                color='AVG_POLYPHARMACY_RISK',
                color_continuous_scale='Reds',
                hover_data=['AVG_AGE']
            )
            fig_meds.update_layout(height=500)
            st.plotly_chart(fig_meds, use_container_width=True)
            
            # Polypharmacy analysis
            st.markdown("#### Polypharmacy Risk Analysis")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.info(f"**{int(overview['POLYPHARMACY_PATIENTS'])}** patients have high polypharmacy risk (score > 5)")
                avg_meds = overview['AVG_MEDICATIONS'] if overview['AVG_MEDICATIONS'] is not None else 0
                st.metric("Average Medications per Patient", f"{avg_meds:.1f}")
            
            with col2:
                # Medication details table
                med_display = med_df[['MEDICATION_NAME', 'PATIENT_COUNT', 'AVG_AGE']].head(10).copy()
                med_display.columns = ['Medication', 'Patients', 'Avg Age']
                med_display['Avg Age'] = med_display['Avg Age'].fillna(0).round(1)
                st.dataframe(med_display, hide_index=True)
    
    with tab5:
        st.markdown("### Quality Metrics")
        
        quality_df = load_quality_metrics_summary(conn)
        
        if not quality_df.empty:
            # Quality compliance chart
            fig_quality = px.bar(
                quality_df,
                x='COMPLIANCE_RATE',
                y='QUALITY_INDICATOR',
                orientation='h',
                title='Quality Indicator Compliance Rates',
                labels={'COMPLIANCE_RATE': 'Compliance Rate (%)', 'QUALITY_INDICATOR': 'Quality Indicator'},
                color='COMPLIANCE_RATE',
                color_continuous_scale='RdYlGn',
                range_color=[0, 100]
            )
            fig_quality.update_layout(height=400)
            st.plotly_chart(fig_quality, use_container_width=True)
            
            # Quality summary
            avg_compliance = quality_df['COMPLIANCE_RATE'].mean()
            st.metric("Average Compliance Rate", f"{avg_compliance:.1f}%")
            
            # Areas for improvement
            low_compliance = quality_df[quality_df['COMPLIANCE_RATE'] < 70]
            if not low_compliance.empty:
                st.warning(f"**{len(low_compliance)}** quality indicators have compliance rates below 70%")
                st.dataframe(
                    low_compliance[['QUALITY_INDICATOR', 'COMPLIANCE_RATE']].rename(
                        columns={'QUALITY_INDICATOR': 'Indicator', 'COMPLIANCE_RATE': 'Compliance (%)'}
                    ),
                    hide_index=True
                )
    
    # Anomaly Analysis Section
    st.markdown("---")
    st.markdown("### 🔍 Anomaly Detection")
    
    anomaly_df = load_anomaly_distribution(conn)
    
    if not anomaly_df.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Anomaly score distribution
            fig_anomaly = px.scatter(
                anomaly_df,
                x='ANOMALY_BUCKET',
                y='PATIENT_COUNT',
                color='PRESENTATION_TYPE',
                size='AVG_COST',
                title='Anomaly Score Distribution',
                labels={'ANOMALY_BUCKET': 'Anomaly Score', 'PATIENT_COUNT': 'Number of Patients'},
                hover_data=['AVG_COST']
            )
            st.plotly_chart(fig_anomaly, use_container_width=True)
        
        with col2:
            st.markdown("#### Anomaly Insights")
            high_anomaly = anomaly_df[anomaly_df['ANOMALY_BUCKET'] > 0.7]
            if not high_anomaly.empty:
                high_anomaly_patients = high_anomaly['PATIENT_COUNT'].sum()
                st.metric("High Anomaly Patients", high_anomaly_patients)
                st.info(
                    f"Patients with anomaly scores > 0.7 may represent rare diseases "
                    f"or unusual presentations requiring special attention."
                )
    


if __name__ == "__main__":
    main()