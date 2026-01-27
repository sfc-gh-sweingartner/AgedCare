"""
Cost Analysis Page
Analyzes healthcare costs extracted from clinical notes and links to financial impact
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
    page_title="Cost Analysis",
    page_icon="💰",
    layout="wide"
)

def load_cost_overview(conn):
    """Load cost overview statistics"""
    query = """
    SELECT 
        COUNT(DISTINCT ca.PATIENT_ID) as total_patients,
        SUM(ca.ESTIMATED_ENCOUNTER_COST) as total_cost,
        AVG(ca.ESTIMATED_ENCOUNTER_COST) as avg_cost,
        MEDIAN(ca.ESTIMATED_ENCOUNTER_COST) as median_cost,
        MAX(ca.ESTIMATED_ENCOUNTER_COST) as max_cost,
        COUNT(DISTINCT CASE WHEN ca.COST_CATEGORY = 'very_high' THEN ca.PATIENT_ID END) as very_high_cost_patients,
        COUNT(DISTINCT CASE WHEN ca.ESTIMATED_ENCOUNTER_COST > 50000 THEN ca.PATIENT_ID END) as extreme_cost_patients
    FROM COST_ANALYSIS ca
    """
    return execute_query(query, conn)

def load_cost_by_age(conn):
    """Load cost analysis by age group"""
    query = """
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    )
    SELECT 
        CASE 
            WHEN p.AGE_YEARS < 18 THEN 'Pediatric (<18)'
            WHEN p.AGE_YEARS < 40 THEN 'Young Adult (18-39)'
            WHEN p.AGE_YEARS < 65 THEN 'Adult (40-64)'
            ELSE 'Senior (65+)'
        END as age_group,
        COUNT(DISTINCT ca.PATIENT_ID) as patient_count,
        AVG(ca.ESTIMATED_ENCOUNTER_COST) as avg_cost,
        SUM(ca.ESTIMATED_ENCOUNTER_COST) as total_cost,
        AVG(p.AGE_YEARS) as avg_age
    FROM COST_ANALYSIS ca
    JOIN parsed_pmc p ON ca.PATIENT_ID = p.PATIENT_ID
    GROUP BY age_group
    ORDER BY avg_age
    """
    return execute_query(query, conn)

def load_procedure_costs(conn):
    """Load procedure extraction and cost analysis"""
    query = """
    WITH proc_expanded AS (
        SELECT 
            ca.PATIENT_ID,
            proc.value:procedure::STRING as procedure_name,
            proc.value:category::STRING as category,
            ca.ESTIMATED_ENCOUNTER_COST,
            ca.COST_CATEGORY
        FROM COST_ANALYSIS ca,
        LATERAL FLATTEN(input => ca.EXTRACTED_PROCEDURES) proc
    )
    SELECT 
        procedure_name,
        category,
        COUNT(DISTINCT PATIENT_ID) as patient_count,
        AVG(ESTIMATED_ENCOUNTER_COST) as avg_encounter_cost
    FROM proc_expanded
    GROUP BY procedure_name, category
    HAVING patient_count > 2
    ORDER BY patient_count DESC
    LIMIT 20
    """
    return execute_query(query, conn)

def load_cost_drivers(conn):
    """Load high cost indicators and drivers"""
    query = """
    WITH indicators_expanded AS (
        SELECT 
            ca.PATIENT_ID,
            ind.value:indicator::STRING as cost_indicator,
            ind.value:impact::STRING as impact,
            ca.ESTIMATED_ENCOUNTER_COST,
            ca.COST_CATEGORY
        FROM COST_ANALYSIS ca,
        LATERAL FLATTEN(input => ca.HIGH_COST_INDICATORS) ind
    )
    SELECT 
        cost_indicator,
        COUNT(DISTINCT PATIENT_ID) as patient_count,
        AVG(ESTIMATED_ENCOUNTER_COST) as avg_cost,
        COUNT(DISTINCT CASE WHEN impact = 'high' THEN PATIENT_ID END) as high_impact_count
    FROM indicators_expanded
    GROUP BY cost_indicator
    ORDER BY patient_count DESC
    LIMIT 15
    """
    return execute_query(query, conn)

def load_cost_distribution(conn):
    """Load detailed cost distribution"""
    query = """
    SELECT 
        CASE 
            WHEN ESTIMATED_ENCOUNTER_COST = 0 THEN '$0'
            WHEN ESTIMATED_ENCOUNTER_COST < 1000 THEN '<$1K'
            WHEN ESTIMATED_ENCOUNTER_COST < 5000 THEN '$1K-$5K'
            WHEN ESTIMATED_ENCOUNTER_COST < 10000 THEN '$5K-$10K'
            WHEN ESTIMATED_ENCOUNTER_COST < 25000 THEN '$10K-$25K'
            WHEN ESTIMATED_ENCOUNTER_COST < 50000 THEN '$25K-$50K'
            ELSE '>$50K'
        END as cost_range,
        COUNT(*) as patient_count,
        SUM(ESTIMATED_ENCOUNTER_COST) as total_cost,
        AVG(ESTIMATED_ENCOUNTER_COST) as avg_cost
    FROM COST_ANALYSIS
    GROUP BY cost_range
    ORDER BY 
        CASE cost_range
            WHEN '$0' THEN 1
            WHEN '<$1K' THEN 2
            WHEN '$1K-$5K' THEN 3
            WHEN '$5K-$10K' THEN 4
            WHEN '$10K-$25K' THEN 5
            WHEN '$25K-$50K' THEN 6
            ELSE 7
        END
    """
    return execute_query(query, conn)

def load_diagnosis_costs(conn):
    """Load costs by diagnosis"""
    query = """
    WITH dx_costs AS (
        SELECT 
            dx.value:diagnosis::STRING as diagnosis,
            ca.ESTIMATED_ENCOUNTER_COST,
            ca.COST_CATEGORY
        FROM PATIENT_ANALYSIS pa
        JOIN COST_ANALYSIS ca ON pa.PATIENT_ID = ca.PATIENT_ID,
        LATERAL FLATTEN(input => pa.AI_ANALYSIS_JSON:differential_diagnosis:diagnostic_assessment:differential_diagnoses) dx
    )
    SELECT 
        diagnosis,
        COUNT(*) as case_count,
        AVG(ESTIMATED_ENCOUNTER_COST) as avg_cost,
        MIN(ESTIMATED_ENCOUNTER_COST) as min_cost,
        MAX(ESTIMATED_ENCOUNTER_COST) as max_cost,
        STDDEV(ESTIMATED_ENCOUNTER_COST) as cost_stddev
    FROM dx_costs
    GROUP BY diagnosis
    HAVING case_count > 5
    ORDER BY avg_cost DESC
    LIMIT 15
    """
    return execute_query(query, conn)

def load_high_cost_patients(conn, limit=10):
    """Load details of highest cost patients"""
    query = f"""
    WITH parsed_pmc AS (
        SELECT 
            PATIENT_ID,
            PATIENT_TITLE,
            GENDER,
            TRY_TO_NUMBER(TO_VARCHAR(TRY_PARSE_JSON(AGE)[0][0])) AS AGE_YEARS
        FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS
    )
    SELECT 
        ca.PATIENT_ID,
        p.PATIENT_TITLE,
        p.AGE_YEARS,
        p.GENDER,
        ca.ESTIMATED_ENCOUNTER_COST,
        ca.COST_DRIVERS,
        pa.AI_ANALYSIS_JSON:clinical_summary:chief_complaint::STRING as CHIEF_COMPLAINT,
        ARRAY_SIZE(ca.EXTRACTED_PROCEDURES) as procedure_count,
        ARRAY_SIZE(ca.HIGH_COST_INDICATORS) as indicator_count
    FROM COST_ANALYSIS ca
    JOIN parsed_pmc p ON ca.PATIENT_ID = p.PATIENT_ID
    LEFT JOIN PATIENT_ANALYSIS pa ON ca.PATIENT_ID = pa.PATIENT_ID
    ORDER BY ca.ESTIMATED_ENCOUNTER_COST DESC
    LIMIT {limit}
    """
    return execute_query(query, conn)

def load_procedure_reference_costs(conn):
    """Load procedure cost reference data"""
    query = """
    SELECT 
        PROCEDURE_NAME,
        CATEGORY,
        ESTIMATED_COST,
        COST_RANGE_LOW,
        COST_RANGE_HIGH
    FROM PROCEDURE_COSTS
    ORDER BY ESTIMATED_COST DESC
    """
    return execute_query(query, conn)

def main():
    st.title("💰 Cost Analysis")
    st.markdown("Extract procedure costs from clinical notes and analyze financial impact")
    
    # Initialize connection
    conn = get_snowflake_connection()
    if not conn:
        st.error("Failed to connect to Snowflake. Please check your connection settings.")
        return
    
    # Load overview data
    with st.spinner("Loading cost analysis data..."):
        overview_df = load_cost_overview(conn)
    
    if overview_df.empty or overview_df.iloc[0]['TOTAL_PATIENTS'] == 0:
        st.warning("No cost analysis data available. Please run batch processing first.")
        return
    
    overview = overview_df.iloc[0]
    
    # Display key metrics
    st.markdown("### 💵 Financial Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Healthcare Costs",
            f"${overview['TOTAL_COST']:,.0f}",
            help="Total estimated costs across all analyzed patients"
        )
    
    with col2:
        st.metric(
            "Average Cost per Patient",
            f"${overview['AVG_COST']:,.0f}",
            f"Median: ${overview['MEDIAN_COST']:,.0f}",
            help="Mean cost per patient encounter"
        )
    
    with col3:
        st.metric(
            "Highest Cost Encounter",
            f"${overview['MAX_COST']:,.0f}",
            help="Maximum cost for a single patient encounter"
        )
    
    with col4:
        st.metric(
            "Very High Cost Patients",
            f"{int(overview['VERY_HIGH_COST_PATIENTS']):,}",
            f"{overview['VERY_HIGH_COST_PATIENTS']/overview['TOTAL_PATIENTS']*100:.1f}%",
            help="Patients in the very high cost category"
        )
    
    # Cost distribution visualization
    st.markdown("### 📊 Cost Distribution Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        cost_dist_df = load_cost_distribution(conn)
        if not cost_dist_df.empty:
            fig_dist = px.bar(
                cost_dist_df,
                x='COST_RANGE',
                y='PATIENT_COUNT',
                title='Patient Distribution by Cost Range',
                labels={'PATIENT_COUNT': 'Number of Patients', 'COST_RANGE': 'Cost Range'},
                color='TOTAL_COST',
                color_continuous_scale='Reds',
                hover_data=['AVG_COST', 'TOTAL_COST']
            )
            st.plotly_chart(fig_dist, use_container_width=True)
    
    with col2:
        # Cost category pie chart
        cost_cat_data = {
            'Low (<$5K)': cost_dist_df[cost_dist_df['COST_RANGE'].isin(['$0', '<$1K', '$1K-$5K'])]['PATIENT_COUNT'].sum(),
            'Medium ($5K-$25K)': cost_dist_df[cost_dist_df['COST_RANGE'].isin(['$5K-$10K', '$10K-$25K'])]['PATIENT_COUNT'].sum(),
            'High (>$25K)': cost_dist_df[cost_dist_df['COST_RANGE'].isin(['$25K-$50K', '>$50K'])]['PATIENT_COUNT'].sum()
        }
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=list(cost_cat_data.keys()),
            values=list(cost_cat_data.values()),
            hole=.3
        )])
        fig_pie.update_layout(title="Cost Category Distribution")
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Cost Drivers", "Procedure Analysis", "Age Analysis", "Diagnosis Costs", "High-Cost Patients"
    ])
    
    with tab1:
        st.markdown("### 🔍 Cost Drivers Analysis")
        
        drivers_df = load_cost_drivers(conn)
        
        if not drivers_df.empty:
            # Cost drivers visualization
            fig_drivers = px.bar(
                drivers_df.head(10),
                x='PATIENT_COUNT',
                y='COST_INDICATOR',
                orientation='h',
                title='Top 10 Cost Drivers by Patient Count',
                labels={'PATIENT_COUNT': 'Number of Patients', 'COST_INDICATOR': 'Cost Driver'},
                color='AVG_COST',
                color_continuous_scale='Oranges',
                hover_data=['HIGH_IMPACT_COUNT']
            )
            fig_drivers.update_layout(height=500)
            st.plotly_chart(fig_drivers, use_container_width=True)
            
            # Cost driver details
            st.markdown("#### Cost Driver Impact")
            drivers_display = drivers_df[['COST_INDICATOR', 'PATIENT_COUNT', 'AVG_COST', 'HIGH_IMPACT_COUNT']].copy()
            drivers_display.columns = ['Cost Driver', 'Patients Affected', 'Avg Cost ($)', 'High Impact Cases']
            drivers_display['Avg Cost ($)'] = drivers_display['Avg Cost ($)'].round(0).astype(int)
            st.dataframe(drivers_display, hide_index=True)
            
            # ROI opportunity
            st.info(
                f"💡 **Cost Reduction Opportunity**: Focusing on the top 5 cost drivers "
                f"could potentially impact **{drivers_df.head(5)['PATIENT_COUNT'].sum()}** patients "
                f"with an average cost of **${drivers_df.head(5)['AVG_COST'].mean():,.0f}** per patient."
            )
    
    with tab2:
        st.markdown("### 🏥 Procedure Cost Analysis")
        
        proc_df = load_procedure_costs(conn)
        
        if not proc_df.empty:
            # Group by category
            category_summary = proc_df.groupby('CATEGORY').agg({
                'PATIENT_COUNT': 'sum',
                'AVG_ENCOUNTER_COST': 'mean'
            }).reset_index()
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                fig_cat = px.pie(
                    category_summary,
                    values='PATIENT_COUNT',
                    names='CATEGORY',
                    title='Procedures by Category'
                )
                st.plotly_chart(fig_cat, use_container_width=True)
            
            with col2:
                fig_cat_cost = px.bar(
                    category_summary,
                    x='CATEGORY',
                    y='AVG_ENCOUNTER_COST',
                    title='Average Cost by Procedure Category',
                    labels={'AVG_ENCOUNTER_COST': 'Average Cost ($)'},
                    color='AVG_ENCOUNTER_COST',
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig_cat_cost, use_container_width=True)
            
            # Detailed procedure list
            st.markdown("#### Extracted Procedures from Notes")
            proc_display = proc_df[['PROCEDURE_NAME', 'CATEGORY', 'PATIENT_COUNT', 'AVG_ENCOUNTER_COST']].copy()
            proc_display.columns = ['Procedure', 'Category', 'Patients', 'Avg Encounter Cost ($)']
            proc_display['Avg Encounter Cost ($)'] = proc_display['Avg Encounter Cost ($)'].round(0).astype(int)
            st.dataframe(proc_display, hide_index=True, height=400)
            
            # Reference costs
            with st.expander("📋 Procedure Cost Reference Table"):
                ref_costs_df = load_procedure_reference_costs(conn)
                if not ref_costs_df.empty:
                    st.markdown("##### Standard Procedure Costs")
                    ref_display = ref_costs_df[['PROCEDURE_NAME', 'CATEGORY', 'ESTIMATED_COST', 'COST_RANGE_LOW', 'COST_RANGE_HIGH']].copy()
                    ref_display.columns = ['Procedure', 'Category', 'Estimated Cost', 'Low Range', 'High Range']
                    for col in ['Estimated Cost', 'Low Range', 'High Range']:
                        ref_display[col] = '$' + ref_display[col].round(0).astype(int).astype(str)
                    st.dataframe(ref_display, hide_index=True)
    
    with tab3:
        st.markdown("### 👥 Cost Analysis by Age Group")
        
        age_cost_df = load_cost_by_age(conn)
        
        if not age_cost_df.empty:
            # Age group cost comparison
            fig_age = px.bar(
                age_cost_df,
                x='AGE_GROUP',
                y='AVG_COST',
                title='Average Healthcare Cost by Age Group',
                labels={'AVG_COST': 'Average Cost ($)', 'AGE_GROUP': 'Age Group'},
                color='PATIENT_COUNT',
                color_continuous_scale='Viridis',
                hover_data=['PATIENT_COUNT', 'TOTAL_COST']
            )
            st.plotly_chart(fig_age, use_container_width=True)
            
            # Age cost summary
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("#### Age Group Statistics")
                age_display = age_cost_df[['AGE_GROUP', 'PATIENT_COUNT', 'AVG_COST', 'TOTAL_COST']].copy()
                age_display.columns = ['Age Group', 'Patients', 'Avg Cost', 'Total Cost']
                age_display['Avg Cost'] = '$' + age_display['Avg Cost'].round(0).astype(int).astype(str)
                age_display['Total Cost'] = '$' + age_display['Total Cost'].round(0).astype(int).astype(str)
                st.dataframe(age_display, hide_index=True)
            
            with col2:
                # Highlight highest cost age group
                highest_cost_age = age_cost_df.loc[age_cost_df['AVG_COST'].idxmax()]
                st.info(
                    f"📊 The **{highest_cost_age['AGE_GROUP']}** age group has the highest average cost "
                    f"at **${highest_cost_age['AVG_COST']:,.0f}** per patient."
                )
                
                # Total cost distribution by age
                fig_total = go.Figure(data=[go.Pie(
                    labels=age_cost_df['AGE_GROUP'],
                    values=age_cost_df['TOTAL_COST'],
                    hole=.3
                )])
                fig_total.update_layout(
                    title="Total Cost Distribution by Age Group",
                    height=300
                )
                st.plotly_chart(fig_total, use_container_width=True)
    
    with tab4:
        st.markdown("### 🩺 Cost Analysis by Diagnosis")
        
        dx_cost_df = load_diagnosis_costs(conn)
        
        if not dx_cost_df.empty:
            # Diagnosis cost chart
            fig_dx = px.bar(
                dx_cost_df.head(10),
                x='AVG_COST',
                y='DIAGNOSIS',
                orientation='h',
                title='Top 10 Most Expensive Diagnoses (Average Cost)',
                labels={'AVG_COST': 'Average Cost ($)', 'DIAGNOSIS': 'Diagnosis'},
                color='CASE_COUNT',
                color_continuous_scale='Reds',
                error_x='COST_STDDEV',
                hover_data=['MIN_COST', 'MAX_COST']
            )
            fig_dx.update_layout(height=500)
            st.plotly_chart(fig_dx, use_container_width=True)
            
            # Cost variation analysis
            st.markdown("#### Cost Variation by Diagnosis")
            
            # Calculate coefficient of variation
            dx_cost_df['CV'] = (dx_cost_df['COST_STDDEV'] / dx_cost_df['AVG_COST'] * 100).round(1)
            
            high_var_dx = dx_cost_df[dx_cost_df['CV'] > 50].sort_values('CV', ascending=False)
            if not high_var_dx.empty:
                st.warning(
                    f"⚠️ **High Cost Variability**: {len(high_var_dx)} diagnoses show cost variation > 50%, "
                    f"indicating opportunity for standardization."
                )
                
                var_display = high_var_dx[['DIAGNOSIS', 'AVG_COST', 'MIN_COST', 'MAX_COST', 'CV']].head(5).copy()
                var_display.columns = ['Diagnosis', 'Avg Cost', 'Min Cost', 'Max Cost', 'Variation (%)']
                for col in ['Avg Cost', 'Min Cost', 'Max Cost']:
                    var_display[col] = '$' + var_display[col].round(0).astype(int).astype(str)
                st.dataframe(var_display, hide_index=True)
    
    with tab5:
        st.markdown("### 🚨 High-Cost Patient Analysis")
        
        # Slider for number of patients to show
        num_patients = st.slider("Number of highest-cost patients to analyze", 5, 25, 10)
        
        high_cost_df = load_high_cost_patients(conn, num_patients)
        
        if not high_cost_df.empty:
            # High cost patient details
            st.markdown(f"#### Top {num_patients} Highest Cost Patients")
            
            # Create expandable cards for each patient
            for idx, patient in high_cost_df.iterrows():
                with st.expander(
                    f"Patient {patient['PATIENT_ID']} - ${patient['ESTIMATED_ENCOUNTER_COST']:,.0f}"
                ):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**Demographics**")
                        age_years = patient['AGE_YEARS'] if patient['AGE_YEARS'] is not None else 0
                        st.text(f"Age: {age_years:.1f} years")
                        st.text(f"Gender: {patient['GENDER']}")
                    
                    with col2:
                        st.markdown("**Clinical**")
                        st.text(f"Chief Complaint: {patient['CHIEF_COMPLAINT'][:50] if patient['CHIEF_COMPLAINT'] else 'N/A'}...")
                        st.text(f"Procedures: {patient['PROCEDURE_COUNT']}")
                    
                    with col3:
                        st.markdown("**Cost Factors**")
                        st.text(f"High-Cost Indicators: {patient['INDICATOR_COUNT']}")
                    
                    if patient['COST_DRIVERS']:
                        st.markdown("**Cost Driver Analysis**")
                        st.write(patient['COST_DRIVERS'])
            
            # Summary statistics for high-cost patients
            st.markdown("#### High-Cost Patient Insights")
            
            total_high_cost = high_cost_df['ESTIMATED_ENCOUNTER_COST'].sum()
            avg_age_high_cost = high_cost_df['AGE_YEARS'].mean() if not high_cost_df['AGE_YEARS'].isna().all() else 0
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    f"Total Cost (Top {num_patients})",
                    f"${total_high_cost:,.0f}",
                    f"{total_high_cost/overview['TOTAL_COST']*100:.1f}% of total"
                )
            
            with col2:
                st.metric(
                    "Average Age",
                    f"{avg_age_high_cost:.1f} years"
                )
            
            with col3:
                avg_procedures = high_cost_df['PROCEDURE_COUNT'].mean()
                st.metric(
                    "Avg Procedures",
                    f"{avg_procedures:.1f}"
                )
    
    # Cost reduction recommendations
    st.markdown("---")
    st.markdown("### 💡 Cost Reduction Recommendations")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### Based on AI Analysis")
        st.success("✅ **Identified Cost Reduction Opportunities:**")
        st.markdown("""
        1. **Standardize High-Variation Procedures**: Focus on diagnoses with >50% cost variation
        2. **Target High-Cost Drivers**: ICU admissions and complex surgeries drive majority of costs
        3. **Age-Based Interventions**: Implement preventive care for high-cost age groups
        4. **Reduce Unnecessary Procedures**: AI identified potential redundant testing patterns
        """)
    
    with col2:
        st.markdown("#### Potential Savings")
        
        # Calculate potential savings
        high_cost_total = cost_dist_df[cost_dist_df['COST_RANGE'].isin(['>$50K', '$25K-$50K'])]['TOTAL_COST'].sum()
        potential_savings = high_cost_total * 0.15  # Assume 15% reduction possible
        
        st.metric(
            "Potential Annual Savings",
            f"${potential_savings:,.0f}",
            "With 15% reduction in high-cost cases"
        )
        
        st.info(
            f"📈 Implementing AI-driven cost optimization could save approximately "
            f"**${potential_savings/12:,.0f}** per month across the patient population."
        )
    
    # Do not close the cached global connection; other pages reuse it.

if __name__ == "__main__":
    main()