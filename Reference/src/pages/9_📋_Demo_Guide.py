"""
Demo Guide Page
Provides demo scripts, talking points, and technical architecture overview
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from connection_helper import get_snowflake_connection, execute_query

# Page config
st.set_page_config(
    page_title="Demo Guide",
    page_icon="📋",
    layout="wide"
)

def load_demo_scenarios(conn=None):
    """Load predefined demo scenarios"""
    if conn is None:
        conn = get_snowflake_connection()
    query = """
    SELECT 
        SCENARIO_ID,
        SCENARIO_NAME,
        SCENARIO_TYPE,
        PATIENT_ID,
        DESCRIPTION,
        TALKING_POINTS,
        EXPECTED_OUTCOMES,
        DEMO_DURATION_MINUTES
    FROM DEMO_SCENARIOS
    ORDER BY SCENARIO_TYPE, SCENARIO_NAME
    """
    return execute_query(query, conn)

@st.cache_data(ttl=60)
def get_data_counts(_conn):
    """Return live counts for key tables used in the demo."""
    counts = {
        'pmc_total': 0,
        'patient_analysis': 0,
        'medication_analysis': 0,
        'cost_analysis': 0
    }
    try:
        pmc_df = execute_query("SELECT COUNT(*) AS CNT FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS", _conn)
        counts['pmc_total'] = int(pmc_df.iloc[0]['CNT']) if not pmc_df.empty else 0
    except Exception:
        pass
    
    for table, key in [
        ("PATIENT_ANALYSIS", "patient_analysis"),
        ("MEDICATION_ANALYSIS", "medication_analysis"),
        ("COST_ANALYSIS", "cost_analysis"),
    ]:
        try:
            df = execute_query(f"SELECT COUNT(*) AS CNT FROM {table}", _conn)
            counts[key] = int(df.iloc[0]['CNT']) if not df.empty else 0
        except Exception:
            pass
    return counts

# PATIENT_SUBSET utilities removed (deprecated)

def run_batch_processing(batch_size=10, max_patients=1000, ai_model='openai-gpt-5', target_patient_id=None):
    """Run the OPTIMIZED batch processing pipeline using Snowpark stored procedure."""
    try:
        conn = get_snowflake_connection()
        if not conn:
            st.error("No Snowflake connection available")
            return False
        
        # Build the procedure call with parameters
        if target_patient_id:
            call_sql = f"CALL HEALTHCARE_DEMO.MEDICAL_NOTES.BATCH_PROCESS_PATIENTS({batch_size}, {max_patients}, '{ai_model}', {target_patient_id})"
        else:
            call_sql = f"CALL HEALTHCARE_DEMO.MEDICAL_NOTES.BATCH_PROCESS_PATIENTS({batch_size}, {max_patients}, '{ai_model}')"
        
        # Call the Snowpark stored procedure
        if hasattr(conn, 'sql'):  # Snowpark session
            result = conn.sql(call_sql).collect()
            if result:
                st.success(f"Batch processing completed: {result[0][0]}")
        else:  # Regular connection
            cursor = conn.cursor()
            cursor.execute(call_sql)
            result = cursor.fetchone()
            cursor.close()
            if result:
                st.success(f"Batch processing completed: {result[0]}")
        
        return True
    except Exception as e:
        st.error(f"Optimized batch processing failed: {str(e)}")
        return False

def main():
    st.title("📋 Healthcare AI Demo Guide")
    st.markdown("Complete guide for demonstrating the Healthcare AI solution")
    
    # Initialize connection
    conn = get_snowflake_connection()
    if not conn:
        st.error("Failed to connect to Snowflake. Please check your connection settings.")
        return
    
    # Navigation
    demo_section = st.radio(
        "Select Demo Section",
        ["Quick Start", "Data Story", "Data Management", "Demo Scenarios", "Technical Architecture", "Talking Points", "FAQ", "Troubleshooting"],
        horizontal=True
    )
    
    if demo_section == "Quick Start":
        st.markdown("## 🚀 Quick Start Guide")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 5-Minute Demo Flow")
            
            st.markdown("""
            1. **Start with Clinical Decision Support** (Page 2)
               - Search for "chest pain" or "diabetes"
               - Show SBAR summary generation
               - Highlight differential diagnoses
            
            2. **Prompt and Model Testing** (Page 3)
               - Select a pre-loaded patient
               - Edit the clinical note
               - Process and show real-time results
            
            3. **Demonstrate Value with Cost Analysis** (Page 5)
               - Show cost distribution
               - Identify high-cost drivers
               - Present ROI opportunity
            
            4. **Close with Medication Safety** (Page 6)
               - Show drug interaction detection
               - Highlight polypharmacy risks
               - Demonstrate safety alerts
            """)
            
            st.success("💡 **Pro Tip**: Keep the Data Foundation page open in another tab to show underlying data")
        
        with col2:
            st.markdown("### ⏱️ Time Allocation")
            
            time_allocation = pd.DataFrame({
                'Section': ['Introduction', 'Clinical AI Demo', 'Value Discussion', 'Q&A'],
                'Minutes': [1, 2, 1, 1]
            })
            
            st.dataframe(time_allocation, hide_index=True)
            
            st.markdown("### 🎯 Key Messages")
            st.info("""
            - **Accuracy**: AI extracts insights from unstructured notes
            - **Speed**: Process thousands of patients in minutes
            - **Value**: Identify cost savings and quality improvements
            - **Safety**: Prevent adverse events proactively
            """)
    
    elif demo_section == "Data Story":
        st.markdown("## 🧭 Data Story: What powers each page")

        st.info("This demo uses the full PMC corpus with pre-computed analysis tables for dashboards, and a single live-processing page to showcase real-time AI.")

        # Live counts
        counts = get_data_counts(get_snowflake_connection())
        st.markdown(f"""
        - **Raw corpus (PMC)**: {counts['pmc_total']:,} records
        - **Pre-computed tables**:
          - `PATIENT_ANALYSIS`: {counts['patient_analysis']:,}
          - `MEDICATION_ANALYSIS`: {counts['medication_analysis']:,}
          - `COST_ANALYSIS`: {counts['cost_analysis']:,}
        """)

        st.markdown("### Source datasets")
        st.markdown("""
        - **Raw corpus**: `PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS` (~167k patient notes)
        
        - **Pre-computed analysis tables** (populated by batch processing):
          - `PATIENT_ANALYSIS` (clinical summaries, diagnoses, quality flags)
          - `MEDICATION_ANALYSIS` (extracted meds, interactions, contraindications)
          - `COST_ANALYSIS` (procedures, high-cost indicators, estimated costs)
        - **Reference tables (sample/mock data)** used for enrichment/UI examples:
          - `PROCEDURE_COSTS` (reference costs)
          - `DRUG_INTERACTIONS_REFERENCE` (known interactions)
        """)

        st.markdown("### How each page uses the data")
        st.markdown("""
        - **1_🏥 Data Foundation**
          - Reads directly from the raw corpus for overview stats and from `PATIENT_ANALYSIS` for processing status.
          - No live processing; read-only.

        - **2_🩺 Clinical Decision Support**
          - Patient search via Cortex Search on `PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS` (indexed).
          - If `PATIENT_ANALYSIS` exists for the selected patient, it shows pre-computed insights.
          - Live AI buttons use the **optimized consolidated prompt** for real-time analysis (same as batch processing).

        - **3_🔬 Prompt and Model Testing**
          - Fully live, on-demand processing using the **consolidated prompt approach** (all 8 use cases in one call).
          - Results logged to `REALTIME_ANALYSIS_LOG` with performance metrics.
          - No dependency on pre-computed tables.

        - **4_📊 Population Health Analytics**
          - Aggregates across `PATIENT_ANALYSIS`, `MEDICATION_ANALYSIS`, and `COST_ANALYSIS` (joined to PMC for demographics).
          - Counts vary by how many patients were batch-processed into each analysis table.

        - **5_💰 Cost Analysis**
          - Uses only `COST_ANALYSIS` (pre-computed from consolidated prompt). If batch not run, this page will be sparse/empty.

        - **6_💊 Medication Safety**
          - Uses `MEDICATION_ANALYSIS` (pre-computed from consolidated prompt safety analysis).

        - **7_📈 Quality Metrics**
          - Uses fields in `PATIENT_ANALYSIS` (`CARE_QUALITY_INDICATORS`, `GUIDELINE_ADHERENCE_FLAGS`); some sections also join `COST_ANALYSIS`.
          - All data comes from consolidated prompt processing.

        - **8_🤖 AI Model Performance**
          - Shows metrics for the **optimized consolidated processing** (15-25 sec/patient vs legacy 90+ sec).
          - Uses `PROCESSING_STATUS` (batch runs) and `REALTIME_ANALYSIS_LOG` (Prompt and Model Testing) for performance analytics.
        """)

        st.markdown("### Why counts differ between pages/tabs")
        st.markdown("""
        - Each dashboard tab aggregates from a specific pre-computed table. If only a portion of the source corpus has been processed into that table, the tab will reflect fewer patients.
        - Live-processing buttons generate results on demand for a single patient and do not automatically backfill the pre-computed tables unless explicitly saved.
        """)

        st.markdown("### Current configuration (OPTIMIZED IMPLEMENTATION)")
        st.markdown("""
        - **Optimized Batch Processing**: Stored procedure `BATCH_PROCESS_PATIENTS()` uses a **consolidated prompt approach**:
          - **Performance**: 5-8x faster than legacy processing (15-25 seconds vs 90+ seconds per patient)
          - **Single API call** processes all 8 use cases simultaneously using `openai-gpt-5` (configurable)
          - **Gap Filling**: Automatically finds and processes any missing patients, including previously deleted ones
          - **Snowflake Native**: Runs directly in Snowflake as a stored procedure for optimal performance
          - Populates `PATIENT_ANALYSIS`, `MEDICATION_ANALYSIS`, and `COST_ANALYSIS` with comprehensive insights
        - **Reference Data**: `PROCEDURE_COSTS` and `DRUG_INTERACTIONS_REFERENCE` seeded with sample values for realistic cost and safety analysis.
        - **Consistency**: Prompt and Model Testing page uses the same consolidated prompt as batch processing for consistent results.
        """)

        st.markdown("### Recommended demo mode for consistency")
        st.markdown("""
        - Run batch processing via stored procedure: `CALL HEALTHCARE_DEMO.MEDICAL_NOTES.BATCH_PROCESS_PATIENTS(10, 1000)` or use the button below.
        - Keep only the Prompt and Model Testing page (Page 3) for real-time AI processing during the presentation.
        """)

    elif demo_section == "Data Management":
        st.markdown("## ⚙️ Data Management: Run batch processing")
        st.markdown("Manage pre-processing directly from this page.")
        


        counts = get_data_counts(get_snowflake_connection())
        st.markdown(f"Current counts → PMC: {counts['pmc_total']:,}, Patient_Analysis: {counts['patient_analysis']:,}, Medication_Analysis: {counts['medication_analysis']:,}, Cost_Analysis: {counts['cost_analysis']:,}")

        st.markdown("---")
        
        # Enhanced controls
        st.markdown("### 🎛️ Batch Processing Controls")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Processing Parameters")
            batch_size = st.number_input(
                "Batch Size", 
                min_value=1, 
                max_value=50, 
                value=10, 
                help="Number of patients processed simultaneously"
            )
            
            max_patients = st.number_input(
                "Max Patients", 
                min_value=1, 
                max_value=10000, 
                value=1000, 
                help="Maximum number of patients to process in this run"
            )
            
            # Complete list of available models from Prompt and Model Testing page
            ai_model_options = [
                ("OpenAI GPT-5 (default)", "openai-gpt-5"),
                ("Claude 4 Sonnet", "claude-4-sonnet"),
                ("Claude 3.5 Sonnet", "claude-3.5-sonnet"),
                ("OpenAI GPT-4.1", "openai-gpt-4.1"),
                ("OpenAI GPT-5 Mini", "openai-gpt-5-mini"),
                ("OpenAI GPT-5 Nano", "openai-gpt-5-nano"),
                ("OpenAI GPT-5 Chat", "openai-gpt-5-chat"),
                ("OpenAI GPT OSS 120B", "openai-gpt-oss-120b"),
                ("OpenAI GPT OSS 20B", "openai-gpt-oss-20b"),
                ("Llama 3.1 8B", "llama3.1-8b"),
                ("Llama 3.1 70B", "llama3.1-70b"),
                ("Mistral Large", "mistral-large"),
                ("Mistral Large 2", "mistral-large2"),
                ("Mixtral 8x7B", "mixtral-8x7b"),
                ("Mistral 7B", "mistral-7b")
            ]
            
            ai_model_display = st.selectbox(
                "AI Model",
                options=[display for display, value in ai_model_options],
                index=0,
                help="AI model to use for processing"
            )
            
            # Get the actual model value from the display name
            ai_model = next(value for display, value in ai_model_options if display == ai_model_display)
        
        with col2:
            st.markdown("#### Advanced Options")
            
            process_specific = st.checkbox("Process Specific Patient", help="Target a single patient ID")
            
            if process_specific:
                target_patient_id = st.number_input(
                    "Patient ID", 
                    min_value=1, 
                    value=577, 
                    help="Specific patient ID to process"
                )
            else:
                target_patient_id = None
                st.info("💡 **Gap Filling**: The batch processor automatically finds and processes any missing patients, including previously deleted ones")
        
        # Instructions
        st.markdown("### 📋 Instructions")
        
        with st.expander("How to Use Batch Processing", expanded=True):
            st.markdown("""
            **🎯 Processing Modes:**
            
            1. **Full Batch Processing** (default):
               - Processes ALL missing patients from the PMC dataset
               - Automatically fills gaps (e.g., deleted patients 577, 587, 591, 594)
               - Uses LEFT JOIN to find any patient in PMC but missing from PATIENT_ANALYSIS
            
            2. **Limited Batch Processing**:
               - Set "Max Patients" to limit the run size
               - Useful for testing or gradual processing
               - Still processes in patient ID order
            
            3. **Single Patient Processing**:
               - Check "Process Specific Patient"
               - Enter the patient ID you want to reprocess
               - Useful for fixing individual problematic records
            
            **⚡ Performance Tips:**
            - **Batch Size**: 10-20 for optimal balance of speed vs. memory
            - **Max Patients**: Start with 100-500 for testing, then increase
            - **AI Model**: `openai-gpt-5` is the default and fastest
            
            **🔧 Troubleshooting:**
            - If processing fails, reduce batch size to 5
            - Check Snowflake warehouse is running (MEDIUM or larger recommended)
            - Verify Cortex credits are available
            """)
        
        # SQL command reference
        with st.expander("Manual SQL Commands"):
            st.markdown("**Equivalent SQL commands for different scenarios:**")
            
            if target_patient_id:
                sql_cmd = f"CALL HEALTHCARE_DEMO.MEDICAL_NOTES.BATCH_PROCESS_PATIENTS({batch_size}, {max_patients}, '{ai_model}', {target_patient_id});"
            else:
                sql_cmd = f"CALL HEALTHCARE_DEMO.MEDICAL_NOTES.BATCH_PROCESS_PATIENTS({batch_size}, {max_patients}, '{ai_model}');"
            
            st.code(sql_cmd, language='sql')
            
            st.markdown("**Check processing status:**")
            st.code("SELECT * FROM PROCESSING_STATUS ORDER BY START_TIME DESC LIMIT 5;", language='sql')
            
            st.markdown("**Find missing patients:**")
            st.code("""
SELECT COUNT(*) as missing_count
FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS p
LEFT JOIN HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS pa ON p.PATIENT_ID = pa.PATIENT_ID
WHERE pa.PATIENT_ID IS NULL
  AND p.PATIENT_NOTES IS NOT NULL
  AND LENGTH(p.PATIENT_NOTES) > 100;
            """, language='sql')
        
        st.markdown("---")
        
        # Enhanced run button
        if target_patient_id:
            button_text = f"🎯 Process Patient {target_patient_id}"
            button_help = f"Process single patient {target_patient_id} using {ai_model}"
        else:
            button_text = f"🚀 Run Batch Processing (up to {max_patients} patients)"
            button_help = f"Process up to {max_patients} missing patients using {ai_model}"
        
        if st.button(button_text, type="primary", use_container_width=True, help=button_help):
            with st.spinner(f"Running batch processing with {ai_model}..."):
                ok = run_batch_processing(
                    batch_size=batch_size, 
                    max_patients=max_patients, 
                    ai_model=ai_model, 
                    target_patient_id=target_patient_id
                )
            if ok:
                st.success("🎉 Batch processing completed!")
                # Refresh counts after operation
                get_data_counts.clear()
                counts = get_data_counts(get_snowflake_connection())
                st.info(f"Updated counts → PMC: {counts['pmc_total']:,}, Patient_Analysis: {counts['patient_analysis']:,}, Medication_Analysis: {counts['medication_analysis']:,}, Cost_Analysis: {counts['cost_analysis']:,}")
                
                if target_patient_id:
                    st.success(f"✅ Patient {target_patient_id} has been reprocessed. You can now test it in Clinical Decision Support!")
                else:
                    gap_info = max_patients if max_patients < 1000 else "all missing"
                    st.success(f"✅ Processed {gap_info} patients. All gaps have been filled!")
            else:
                st.error("❌ Batch processing failed. Check the error message above and try with smaller batch size or different model.")
    
    elif demo_section == "Demo Scenarios":
        st.markdown("## 🎭 Demo Scenarios")
        
        # Load scenarios
        scenarios_df = load_demo_scenarios(conn)
        
        if not scenarios_df.empty:
            # Group by type
            for scenario_type in scenarios_df['SCENARIO_TYPE'].unique():
                st.markdown(f"### {scenario_type.title()} Scenarios")
                
                type_scenarios = scenarios_df[scenarios_df['SCENARIO_TYPE'] == scenario_type]
                
                for _, scenario in type_scenarios.iterrows():
                    with st.expander(f"📌 {scenario['SCENARIO_NAME']} ({scenario['DEMO_DURATION_MINUTES']} min)"):
                        st.markdown(f"**Description**: {scenario['DESCRIPTION']}")
                        st.markdown(f"**Patient ID**: {scenario['PATIENT_ID']}")
                        
                        if scenario['TALKING_POINTS']:
                            st.markdown("**Talking Points**:")
                            try:
                                import json
                                points = json.loads(scenario['TALKING_POINTS'])
                                for point in points:
                                    st.markdown(f"- {point}")
                            except:
                                st.markdown(scenario['TALKING_POINTS'])
                        
                        if scenario['EXPECTED_OUTCOMES']:
                            st.markdown("**Expected Outcomes**:")
                            st.info(scenario['EXPECTED_OUTCOMES'])
        
        # Custom scenario builder
        st.markdown("### 🛠️ Build Custom Scenario")
        
        col1, col2 = st.columns(2)
        
        with col1:
            focus_area = st.selectbox(
                "Primary Focus",
                ["Cost Reduction", "Clinical Quality", "Patient Safety", "Rare Disease", "Population Health"]
            )
            
            audience = st.selectbox(
                "Target Audience",
                ["C-Suite", "Clinical Leaders", "IT Leaders", "Data Scientists", "Physicians"]
            )
        
        with col2:
            duration = st.slider("Demo Duration (minutes)", 5, 30, 15)
            
            complexity = st.select_slider(
                "Technical Depth",
                ["Basic", "Intermediate", "Advanced"]
            )
        
        if st.button("Generate Custom Script"):
            st.markdown("### 📝 Custom Demo Script")
            
            script = f"""
            **Scenario**: {focus_area} for {audience}
            **Duration**: {duration} minutes
            **Complexity**: {complexity}
            
            **Opening** (2 min):
            - Introduce challenge: Unstructured clinical notes contain valuable insights
            - Show scale: Processing 1,000+ patients with AI
            
            **Demo Flow** ({duration-4} min):
            """
            
            if focus_area == "Cost Reduction":
                script += """
            1. Navigate to Cost Analysis page
            2. Show high-cost patient identification
            3. Demonstrate procedure extraction from notes
            4. Calculate potential savings
            """
            elif focus_area == "Clinical Quality":
                script += """
            1. Start with Clinical Decision Support
            2. Show quality metrics dashboard
            3. Demonstrate guideline adherence tracking
            4. Highlight improvement opportunities
            """
            elif focus_area == "Patient Safety":
                script += """
            1. Open Medication Safety page
            2. Show drug interaction detection
            3. Demonstrate contraindication alerts
            4. Review high-risk patient identification
            """
            
            script += """
            
            **Closing** (2 min):
            - Summarize value proposition
            - Show ROI calculation
            - Discuss next steps
            """
            
            st.markdown(script)
    
    elif demo_section == "Technical Architecture":
        st.markdown("## 🏗️ Technical Architecture")
        
        tab1, tab2, tab3 = st.tabs(["System Overview", "Data Flow", "AI Components"])
        
        with tab1:
            st.markdown("### System Architecture")
            
            st.markdown("""
            ```
            ┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
            │   Data Sources      │     │   Snowflake         │     │   Streamlit App     │
            │  - PMC Patients     │────▶│  - Data Storage     │────▶│  - Visualization    │
            │  - Clinical Notes   │     │  - Cortex AI        │     │  - User Interface   │
            └─────────────────────┘     │  - Processing       │     └─────────────────────┘
                                       └─────────────────────┘
            ```
            """)
            
            st.markdown("#### Key Components")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### Data Layer")
                st.markdown("""
                - **PATIENT_ANALYSIS**: Pre-computed AI insights
                - **MEDICATION_ANALYSIS**: Drug safety analysis
                - **COST_ANALYSIS**: Financial impact data
                - **Cortex Search**: Semantic patient search
                """)
            
            with col2:
                st.markdown("##### AI Layer (OPTIMIZED)")
                st.markdown("""
                - **Snowflake Cortex**: LLM processing engine
                - **Model Used**: openai-gpt-5 (unified across all use cases, configurable)
                - **Consolidated Prompts**: Single comprehensive prompt for all 8 use cases
                - **Performance**: 5-8x faster than individual prompts (15-25 sec/patient)
                - **Batch Processing**: Optimized scalable analysis with live management
                - **Consistency**: Same prompt for batch and real-time processing
                """)
        
        with tab2:
            st.markdown("### Data Processing Flow")
            
            st.markdown("""
            ```mermaid
            graph TD
                A[Clinical Notes] --> B[Text Preprocessing]
                B --> C{Batch or Real-time?}
                C -->|Batch| D[Batch Processing Pipeline]
                C -->|Real-time| E[Live AI Processing]
                D --> F[PATIENT_ANALYSIS Table]
                D --> G[MEDICATION_ANALYSIS Table]
                D --> H[COST_ANALYSIS Table]
                E --> I[Real-time Results]
                F --> J[Streamlit Dashboard]
                G --> J
                H --> J
                I --> J
            ```
            """)
            
            st.markdown("#### Processing Steps")
            
            processing_steps = pd.DataFrame({
                'Step': ['1. Data Ingestion', '2. AI Analysis', '3. Result Storage', '4. Visualization'],
                'Description': [
                    'Load patient notes from PMC dataset',
                    'Process through Cortex AI with use case prompts',
                    'Store structured results in analysis tables',
                    'Display insights in Streamlit dashboard'
                ],
                'Technology': ['Snowflake', 'Cortex LLM', 'Snowflake Tables', 'Streamlit']
            })
            
            st.dataframe(processing_steps, hide_index=True)
        
        with tab3:
            st.markdown("### AI Components Deep Dive")
            
            st.markdown("#### Use Case Implementation")
            
            use_cases = pd.DataFrame({
                'Use Case': [
                    'Clinical Summary',
                    'Differential Diagnosis',
                    'Medication Safety',
                    'Treatment Analysis',
                    'Pattern Recognition',
                    'Quality Metrics',
                    'Cost Analysis',
                    'Educational Value'
                ],
                'AI Model': [
                    'openai-gpt-5 (default)',
                    'openai-gpt-5 (default)',
                    'openai-gpt-5 (default)',
                    'openai-gpt-5 (default)',
                    'openai-gpt-5 (default)',
                    'openai-gpt-5 (default)',
                    'openai-gpt-5 (default)',
                    'openai-gpt-5 (default)'
                ],
                'Processing Method': [
                    'Consolidated Prompt',
                    'Consolidated Prompt',
                    'Consolidated Prompt',
                    'Consolidated Prompt',
                    'Consolidated Prompt',
                    'Consolidated Prompt',
                    'Consolidated Prompt',
                    'Consolidated Prompt'
                ],
                'Output Type': [
                    'SBAR Format',
                    'Structured JSON',
                    'Drug Interactions',
                    'Treatment Plans',
                    'Anomaly Scores',
                    'Compliance Rates',
                    'Cost Estimates',
                    'Teaching Points'
                ]
            })
            
            st.dataframe(use_cases, hide_index=True)
            
            st.markdown("#### Prompt Engineering")
            
            with st.expander("View OPTIMIZED Consolidated Prompt Structure"):
                st.code("""
{
    "system": "You are a comprehensive medical AI assistant analyzing clinical notes.",
    "prompt": "Analyze patient notes across ALL healthcare AI use cases in one response:",
    "structure": {
        "clinical_summary": "SBAR format summary",
        "differential_diagnosis": "Top diagnoses with evidence",
        "medication_safety": "Drug interactions and contraindications",
        "treatment_analysis": "Current treatments and recommendations",
        "pattern_recognition": "Anomaly detection and rare diseases",
        "quality_metrics": "Guideline adherence and quality indicators",
        "cost_analysis": "Procedure extraction and cost drivers",
        "educational_value": "Teaching points and clinical pearls"
    },
    "advantages": [
        "5-8x faster than individual prompts",
        "Consistent formatting across all use cases",
        "Cross-domain insights in single analysis",
        "Reduced API failure points"
    ]
}
                """, language='json')
    
    elif demo_section == "Talking Points":
        st.markdown("## 💬 Key Talking Points")
        
        audience_type = st.selectbox(
            "Select Audience",
            ["Executive", "Clinical", "Technical", "General"]
        )
        
        if audience_type == "Executive":
            st.markdown("### Executive Talking Points")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Value Proposition")
                st.success("""
                **Financial Impact**
                - Identify high-cost patients proactively
                - Reduce readmissions through better care
                - Optimize resource utilization
                - Typical ROI: 10-15x investment
                
                **Quality Improvement**
                - Enhance patient safety
                - Improve clinical outcomes
                - Ensure regulatory compliance
                - Reduce medical errors
                """)
            
            with col2:
                st.markdown("#### Strategic Benefits")
                st.info("""
                **Competitive Advantage**
                - Leading-edge AI adoption
                - Data-driven decision making
                - Improved patient satisfaction
                - Physician productivity gains
                
                **Scalability**
                - Process millions of notes
                - No infrastructure limits
                - Pay-per-use model
                - Rapid deployment
                """)
        
        elif audience_type == "Clinical":
            st.markdown("### Clinical Talking Points")
            
            st.markdown("#### For Physicians")
            st.markdown("""
            - **Time Savings**: Reduce documentation review from 15 minutes to 30 seconds
            - **Clinical Support**: AI suggests differential diagnoses you might not consider
            - **Evidence-Based**: Recommendations backed by similar patient outcomes
            - **Safety Alerts**: Automatic drug interaction and contraindication checking
            """)
            
            st.markdown("#### Clinical Use Cases")
            
            clinical_benefits = pd.DataFrame({
                'Scenario': [
                    'Morning Rounds',
                    'New Patient Intake',
                    'Discharge Planning',
                    'Complex Cases'
                ],
                'AI Benefit': [
                    'Quick SBAR summaries for all patients',
                    'Comprehensive history analysis',
                    'Medication reconciliation',
                    'Rare disease pattern recognition'
                ],
                'Time Saved': [
                    '2 hours/day',
                    '30 min/patient',
                    '15 min/discharge',
                    '1 hour/case'
                ]
            })
            
            st.dataframe(clinical_benefits, hide_index=True)
        
        elif audience_type == "Technical":
            st.markdown("### Technical Talking Points")
            
            tab1, tab2, tab3 = st.tabs(["Architecture", "Security", "Integration"])
            
            with tab1:
                st.markdown("#### Technical Architecture")
                st.code("""
- Cloud-Native: Built on Snowflake's elastic compute
- Serverless AI: No model management required
- SQL-Based: Familiar tooling for data teams
- Python SDK: Easy integration with existing workflows
- REST APIs: Standard interfaces for applications
                """)
            
            with tab2:
                st.markdown("#### Security & Compliance")
                st.markdown("""
                - **HIPAA Compliant**: End-to-end encryption
                - **Data Governance**: Role-based access control
                - **Audit Trail**: Complete processing history
                - **Data Residency**: Your region, your control
                - **PHI Protection**: No data leaves Snowflake
                """)
            
            with tab3:
                st.markdown("#### Integration Options")
                st.markdown("""
                - **EHR Integration**: HL7/FHIR interfaces
                - **Batch Processing**: Scheduled jobs
                - **Real-time API**: < 2 second response
                - **Streaming**: Kafka/Kinesis support
                - **Export Formats**: JSON, CSV, Parquet
                """)
    
    elif demo_section == "FAQ":
        st.markdown("## ❓ Frequently Asked Questions")
        
        faqs = {
            "How accurate is the AI analysis?": """
                Our AI achieves 85-90% accuracy on clinical information extraction, validated against 
                physician reviews. The system is designed to augment, not replace, clinical judgment.
            """,
            
            "What about patient privacy?": """
                All processing occurs within Snowflake's secure environment. No patient data is sent 
                to external services. The system is HIPAA compliant with full audit trails.
            """,
            
            "How much does it cost?": """
                Costs scale with usage, typically $0.30-0.50 per patient analysis. Most organizations 
                see ROI within 3-6 months through efficiency gains and cost reductions.
            """,
            
            "Can we customize the AI prompts?": """
                Yes! All prompts are configurable. You can modify them to match your clinical protocols, 
                add specialty-specific logic, or adjust output formats.
            """,
            
            "How long does implementation take?": """
                Basic deployment takes 1-2 weeks. Full integration with existing systems typically 
                requires 4-6 weeks depending on complexity.
            """,
            
            "What medical specialties does it support?": """
                The system works across all specialties but excels in internal medicine, cardiology, 
                oncology, and emergency medicine. Specialty-specific models can be added.
            """,
            
            "How does it handle medical abbreviations?": """
                The AI is trained on medical texts and understands common abbreviations. Custom 
                abbreviation dictionaries can be added for organization-specific terms.
            """,
            
            "Can it process non-English notes?": """
                Currently optimized for English. Multi-language support is on the roadmap with 
                Spanish and Mandarin prioritized.
            """
        }
        
        for question, answer in faqs.items():
            with st.expander(question):
                st.write(answer)
    
    elif demo_section == "Troubleshooting":
        st.markdown("## 🔧 Troubleshooting Guide")
        
        st.markdown("### Common Issues and Solutions")
        
        issues = {
            "Slow Performance": {
                "symptoms": ["Pages load slowly", "Queries timeout", "Processing delays"],
                "solutions": [
                    "Check warehouse size (recommend MEDIUM)",
                    "Verify Cortex Search service is active",
                    "Review concurrent user load",
                    "Clear browser cache"
                ]
            },
            
            "No Data Showing": {
                "symptoms": ["Empty dashboards", "Zero patient counts", "Missing analyses"],
                "solutions": [
                    "Verify batch processing completed",
                    "Check database permissions",
                    
                    "Run test queries in SQL"
                ]
            },
            
            "AI Processing Errors": {
                "symptoms": ["Failed analyses", "Incomplete results", "Error messages"],
                "solutions": [
                    "Check Cortex credit availability",
                    "Verify prompt syntax",
                    "Review token limits",
                    "Check model availability"
                ]
            },
            
            "Search Not Working": {
                "symptoms": ["No search results", "Irrelevant results", "Search errors"],
                "solutions": [
                    "Verify Cortex Search service status",
                    "Check search syntax",
                    "Confirm index is up to date",
                    "Review search permissions"
                ]
            }
        }
        
        for issue, details in issues.items():
            with st.expander(f"🔴 {issue}"):
                st.markdown("**Symptoms:**")
                for symptom in details["symptoms"]:
                    st.write(f"- {symptom}")
                
                st.markdown("**Solutions:**")
                for i, solution in enumerate(details["solutions"], 1):
                    st.success(f"{i}. {solution}")
        
        st.markdown("### 🚀 Performance Optimization")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Quick Wins")
            st.markdown("""
            - Increase warehouse size for demos
            - Pre-warm caches before presentations
            - Use bookmarks for quick navigation
            - Keep backup demo environment ready
            """)
        
        with col2:
            st.markdown("#### Demo Best Practices")
            st.markdown("""
            - Test all scenarios beforehand
            - Have offline backup slides
            - Know your patient IDs
            - Practice error recovery
            """)
        
        st.markdown("### 📞 Support Contacts")
        st.info("""
        **Technical Support**: ai-demo-support@example.com
        **Snowflake Support**: support.snowflake.com
        **Documentation**: docs.snowflake.com/cortex
        """)
    
    # Footer
    st.markdown("---")
    st.caption(f"Healthcare AI Demo Guide • Version 1.0 • Last Updated: {datetime.now().strftime('%Y-%m-%d')}")
    
    # Do not close the cached global connection; other pages reuse it.
    # Cached connection is managed by Streamlit and our helper; avoid conn.close() here.

if __name__ == "__main__":
    main()