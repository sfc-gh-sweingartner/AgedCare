import streamlit as st
from datetime import datetime, timedelta
import uuid

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

session = get_snowflake_session()

if session:
    with st.expander("How to use this page", expanded=False, icon=":material/help:"):
        st.markdown("""
### Purpose
This page provides **testing utilities** for the temporal processing system - generate test data for threshold/expiry testing, and reset data during development.

### Terminology
- **Deficit**: A clinical condition being tracked (D001-D032)
- **Occurrence**: Evidence that a deficit may exist (individual detection)
- **Flag**: When a deficit becomes active after approval

### Features
- **Generate Test Scenarios**: Create historic approval data to test time/count based thresholds
- **Clear Review Decisions**: Remove approval/rejection decisions from the review queue
- **Clear Analysis Results**: Remove LLM analysis records
- **Clear Deficit Status**: Reset deficit status for residents

### Test Scenario Types
| Scenario | Purpose |
|----------|---------|
| **Just Under Threshold** | Generate threshold-1 occurrences (deficit should NOT be flagged) |
| **Meets Threshold** | Generate exactly threshold occurrences (deficit SHOULD be flagged) |
| **Outside Lookback** | Occurrences older than lookback period (should NOT count) |
| **Mixed Window** | Some inside, some outside lookback window |
| **Near Expiry** | Active deficit flag approaching expiry date |
| **Already Expired** | Historic deficit flag that should have expired |

### ⚠️ Warning
Clear operations **permanently delete** data. Use with caution in production environments.
        """)

    st.title("Testing Tools")
    st.caption("Reset analysis data for re-testing after prompt improvements")
    
    st.warning("⚠️ These operations permanently delete data. Use for development/testing only.", icon=":material/warning:")
    
    residents = execute_query_df("""
        SELECT DISTINCT r.RESIDENT_ID,
               COUNT(DISTINCT rq.QUEUE_ID) as REVIEW_COUNT,
               COUNT(DISTINCT lla.ANALYSIS_ID) as ANALYSIS_COUNT,
               COUNT(DISTINCT ds.DEFICIT_ID) as DEFICIT_COUNT
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES r
        LEFT JOIN AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE rq ON r.RESIDENT_ID = rq.RESIDENT_ID
        LEFT JOIN AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS lla ON r.RESIDENT_ID = lla.RESIDENT_ID
        LEFT JOIN AGEDCARE.AGEDCARE.DRI_DEFICIT_STATUS ds ON r.RESIDENT_ID = ds.RESIDENT_ID
        GROUP BY r.RESIDENT_ID
        ORDER BY r.RESIDENT_ID
    """, session)
    
    if residents is not None and len(residents) > 0:
        tab1, tab2, tab3, tab4 = st.tabs([
            "🧪 Generate Test Data",
            "🗑️ Clear by Resident", 
            "🧹 Clear All Data",
            "📊 Data Summary"
        ])
        
        with tab1:
            st.subheader("Generate Historic Approval Data")
            st.caption("Create test occurrences to validate threshold and expiry logic")
            
            rules_df = execute_query_df("""
                SELECT 
                    DEFICIT_ID, 
                    DEFICIT_NAME, 
                    DEFICIT_TYPE,
                    LOOKBACK_DAYS_HISTORIC,
                    EXPIRY_DAYS,
                    COALESCE(RULES_JSON[0]:threshold::NUMBER, 1) as THRESHOLD,
                    RENEWAL_REMINDER_DAYS
                FROM AGEDCARE.AGEDCARE.DRI_RULES 
                WHERE IS_CURRENT_VERSION = TRUE
                ORDER BY DEFICIT_TYPE, DEFICIT_ID
            """, session)
            
            if rules_df is not None and len(rules_df) > 0:
                scenario_tab1, scenario_tab2 = st.tabs(["📋 Quick Scenarios", "🔧 Custom Generator"])
                
                with scenario_tab1:
                    st.markdown("#### Pre-built Test Scenarios")
                    st.caption("Select a scenario to auto-configure test data generation")
                    
                    col_res, col_fac = st.columns(2)
                    with col_res:
                        resident_options = execute_query_df("""
                            SELECT DISTINCT RESIDENT_ID, SYSTEM_KEY 
                            FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES 
                            WHERE SYSTEM_KEY IS NOT NULL
                            ORDER BY RESIDENT_ID
                        """, session)
                        
                        if resident_options is not None and len(resident_options) > 0:
                            resident_list = resident_options['RESIDENT_ID'].tolist()
                            test_resident_id = st.selectbox("Select Resident", resident_list, key="scenario_resident_select")
                            facility_row = resident_options[resident_options['RESIDENT_ID'] == test_resident_id]
                            test_facility = facility_row['SYSTEM_KEY'].iloc[0] if len(facility_row) > 0 else "TEST_FACILITY"
                        else:
                            test_resident_id = st.number_input("Resident ID", value=9001, min_value=1, step=1, key="scenario_resident")
                            test_facility = "TEST_FACILITY"
                    with col_fac:
                        st.text_input("Facility (auto-detected)", value=test_facility, disabled=True, key="scenario_facility_display")
                    
                    st.markdown("---")
                    
                    fluctuating_rules = rules_df[rules_df['DEFICIT_TYPE'] == 'FLUCTUATING']
                    high_threshold_rules = rules_df[rules_df['THRESHOLD'] > 1]
                    short_lookback_rules = rules_df[(rules_df['LOOKBACK_DAYS_HISTORIC'] != 'all') & (rules_df['LOOKBACK_DAYS_HISTORIC'].astype(str).str.isnumeric())]
                    
                    scenarios = {
                        "threshold_under": {
                            "name": "🔢 Just Under Threshold",
                            "description": "Generate threshold-1 occurrences within lookback window. Deficit should NOT be flagged.",
                            "best_for": "D023 (Incontinence, threshold=50) or D014 (Polypharmacy, threshold=5)",
                            "rules": high_threshold_rules if len(high_threshold_rules) > 0 else rules_df
                        },
                        "threshold_meets": {
                            "name": "✅ Meets Threshold",
                            "description": "Generate exactly threshold occurrences within lookback window. Deficit SHOULD be flagged.",
                            "best_for": "Any deficit - tests flagging logic",
                            "rules": rules_df
                        },
                        "threshold_exceeds": {
                            "name": "📈 Exceeds Threshold",
                            "description": "Generate threshold+2 occurrences within lookback window. Tests high-frequency detection.",
                            "best_for": "Any deficit",
                            "rules": rules_df
                        },
                        "outside_lookback": {
                            "name": "⏰ Outside Lookback Window",
                            "description": "All occurrences older than lookback period. Should NOT count toward threshold.",
                            "best_for": "D016/D022 (7-day), D020 (90-day lookback)",
                            "rules": short_lookback_rules if len(short_lookback_rules) > 0 else fluctuating_rules
                        },
                        "mixed_window": {
                            "name": "🔀 Mixed Window (Partial Count)",
                            "description": "Some occurrences inside, some outside lookback. Tests window boundary logic.",
                            "best_for": "D020 (90-day), D024-D026 (90-day)",
                            "rules": short_lookback_rules if len(short_lookback_rules) > 0 else fluctuating_rules
                        },
                        "near_expiry": {
                            "name": "⚠️ Near Expiry",
                            "description": "Active deficit flag within renewal_reminder_days of expiry. Tests renewal alerts.",
                            "best_for": "D021 (3-day expiry), D022 (7-day expiry)",
                            "rules": fluctuating_rules
                        },
                        "already_expired": {
                            "name": "❌ Already Expired",
                            "description": "Occurrences that flagged a deficit which has now expired. Tests expiry logic.",
                            "best_for": "D012 (1-day expiry), D021 (3-day expiry)",
                            "rules": fluctuating_rules
                        }
                    }
                    
                    selected_scenario = st.selectbox(
                        "Choose test scenario",
                        options=list(scenarios.keys()),
                        format_func=lambda x: scenarios[x]["name"]
                    )
                    
                    scenario = scenarios[selected_scenario]
                    
                    with st.container(border=True):
                        st.markdown(f"**{scenario['name']}**")
                        st.caption(scenario['description'])
                        st.markdown(f"*Best for:* {scenario['best_for']}")
                    
                    rule_options = scenario['rules']
                    indicator_options = {f"{r['DEFICIT_ID']} - {r['DEFICIT_NAME']} ({r['DEFICIT_TYPE']}, thresh={r['THRESHOLD']}, lookback={r['LOOKBACK_DAYS_HISTORIC']})": r['DEFICIT_ID'] 
                                        for _, r in rule_options.iterrows()}
                    
                    selected_indicator_label = st.selectbox("Select deficit", list(indicator_options.keys()), key="scenario_indicator")
                    selected_indicator_id = indicator_options[selected_indicator_label]
                    
                    rule_row = rules_df[rules_df['DEFICIT_ID'] == selected_indicator_id].iloc[0]
                    threshold = int(rule_row['THRESHOLD'])
                    lookback = rule_row['LOOKBACK_DAYS_HISTORIC']
                    lookback_days = 9999 if lookback == 'all' else int(lookback)
                    expiry_days = int(rule_row['EXPIRY_DAYS']) if rule_row['EXPIRY_DAYS'] else 0
                    deficit_name = rule_row['DEFICIT_NAME']
                    deficit_type = rule_row['DEFICIT_TYPE']
                    
                    if selected_scenario == "threshold_under":
                        num_occurrences = max(1, threshold - 1)
                        days_ago_start = min(lookback_days - 1, 30)
                        days_ago_end = 0
                        expected_result = "NOT flag (under threshold)"
                    elif selected_scenario == "threshold_meets":
                        num_occurrences = threshold
                        days_ago_start = min(lookback_days - 1, 60)
                        days_ago_end = 0
                        expected_result = "FLAG (meets threshold)"
                    elif selected_scenario == "threshold_exceeds":
                        num_occurrences = threshold + 2
                        days_ago_start = min(lookback_days - 1, 60)
                        days_ago_end = 0
                        expected_result = "FLAG (exceeds threshold)"
                    elif selected_scenario == "outside_lookback":
                        num_occurrences = threshold + 1
                        days_ago_start = lookback_days + 30
                        days_ago_end = lookback_days + 1
                        expected_result = "NOT flag (all outside window)"
                    elif selected_scenario == "mixed_window":
                        num_occurrences = threshold + 2
                        days_ago_start = lookback_days + 10
                        days_ago_end = 0
                        expected_result = f"Depends on how many fall inside {lookback_days}-day window"
                    elif selected_scenario == "near_expiry":
                        num_occurrences = threshold
                        days_ago_start = expiry_days - 2 if expiry_days > 2 else 1
                        days_ago_end = expiry_days - 2 if expiry_days > 2 else 1
                        expected_result = "FLAG then show renewal warning"
                    elif selected_scenario == "already_expired":
                        num_occurrences = threshold
                        days_ago_start = expiry_days + 10
                        days_ago_end = expiry_days + 5
                        expected_result = "Should show as EXPIRED"
                    
                    st.markdown("---")
                    st.markdown("**Generated Configuration:**")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Occurrences to create", num_occurrences)
                    with col2:
                        st.metric("Date range", f"{days_ago_start} to {days_ago_end} days ago")
                    with col3:
                        st.metric("Expected result", expected_result)
                    
                    if st.button("🚀 Generate Test Data", type="primary", key="generate_scenario_btn"):
                        try:
                            today = datetime.now().date()
                            
                            if num_occurrences == 1:
                                dates = [today - timedelta(days=days_ago_start)]
                            else:
                                date_spread = days_ago_start - days_ago_end
                                interval = date_spread / (num_occurrences - 1) if num_occurrences > 1 else 0
                                dates = [today - timedelta(days=int(days_ago_start - (i * interval))) for i in range(num_occurrences)]
                            
                            for occ_date in dates:
                                occ_id = str(uuid.uuid4())
                                execute_query(f"""
                                    INSERT INTO AGEDCARE.AGEDCARE.DRI_INDICATOR_OCCURRENCES
                                    (OCCURRENCE_ID, RESIDENT_ID, CLIENT_SYSTEM_KEY, DEFICIT_ID, DEFICIT_NAME,
                                     OCCURRENCE_DATE, SOURCE_ID, SOURCE_TABLE, EVIDENCE_TEXT,
                                     APPROVED_BY, APPROVAL_DATE)
                                    VALUES (
                                        '{occ_id}',
                                        {test_resident_id},
                                        '{test_facility}',
                                        '{selected_indicator_id}',
                                        '{deficit_name}',
                                        '{occ_date}',
                                        'TEST_SCENARIO',
                                        'TEST_DATA',
                                        'Auto-generated test data for scenario: {scenario["name"]}',
                                        'TEST_GENERATOR',
                                        CURRENT_TIMESTAMP()
                                    )
                                """, session)
                            
                            st.success(f"✅ Created {num_occurrences} occurrence(s) for {selected_indicator_id} on resident {test_resident_id}")
                            st.info(f"**Expected behavior:** {expected_result}")
                            st.caption("Use 'Clear by Resident' tab to remove test data when done")
                            
                        except Exception as e:
                            st.error(f"Error generating test data: {e}")
                
                with scenario_tab2:
                    st.markdown("#### Custom Test Data Generator")
                    st.caption("Full control over test data generation")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        custom_resident_options = execute_query_df("""
                            SELECT DISTINCT RESIDENT_ID, SYSTEM_KEY 
                            FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES 
                            WHERE SYSTEM_KEY IS NOT NULL
                            ORDER BY RESIDENT_ID
                        """, session)
                        
                        if custom_resident_options is not None and len(custom_resident_options) > 0:
                            custom_resident_list = custom_resident_options['RESIDENT_ID'].tolist()
                            custom_resident = st.selectbox("Select Resident", custom_resident_list, key="custom_resident_select")
                            custom_facility_row = custom_resident_options[custom_resident_options['RESIDENT_ID'] == custom_resident]
                            custom_facility = custom_facility_row['SYSTEM_KEY'].iloc[0] if len(custom_facility_row) > 0 else "TEST_FACILITY"
                        else:
                            custom_resident = st.number_input("Resident ID", value=9002, min_value=1, step=1, key="custom_resident")
                            custom_facility = "TEST_FACILITY"
                        st.text_input("Facility (auto-detected)", value=custom_facility, disabled=True, key="custom_facility_display")
                    
                    with col2:
                    all_indicators = {f"{r['DEFICIT_ID']} - {r['DEFICIT_NAME']}": r['DEFICIT_ID'] for _, r in rules_df.iterrows()}
                        custom_indicator_label = st.selectbox("Deficit", list(all_indicators.keys()), key="custom_indicator")
                        custom_indicator_id = all_indicators[custom_indicator_label]
                        
                        custom_rule = rules_df[rules_df['DEFICIT_ID'] == custom_indicator_id].iloc[0]
                                st.caption(f"Type: {custom_rule['DEFICIT_TYPE']} | Threshold: {custom_rule['THRESHOLD']} | Lookback: {custom_rule['LOOKBACK_DAYS_HISTORIC']} | Expiry: {custom_rule['EXPIRY_DAYS']} days")
                    
                    st.markdown("---")
                    
                    col_count, col_spread = st.columns(2)
                    with col_count:
                        custom_count = st.number_input("Number of occurrences", value=1, min_value=1, max_value=100, key="custom_count")
                    with col_spread:
                        spread_method = st.selectbox("Date distribution", 
                                                    ["Even spread", "All on same day", "Random within range"],
                                                    key="custom_spread")
                    
                    col_start, col_end = st.columns(2)
                    with col_start:
                        days_ago_custom_start = st.number_input("Start (days ago)", value=30, min_value=0, max_value=365, key="custom_start")
                    with col_end:
                        days_ago_custom_end = st.number_input("End (days ago)", value=0, min_value=0, max_value=365, key="custom_end")
                    
                    custom_evidence = st.text_input("Evidence text", value="Custom test occurrence", key="custom_evidence")
                    
                    st.markdown("---")
                    
                    if st.button("🔧 Generate Custom Data", type="primary", key="generate_custom_btn"):
                        try:
                            today = datetime.now().date()
                            custom_deficit_name = custom_rule['DEFICIT_NAME']
                            
                            if spread_method == "All on same day":
                                dates = [today - timedelta(days=days_ago_custom_start)] * custom_count
                            elif spread_method == "Random within range":
                                import random
                                dates = [today - timedelta(days=random.randint(days_ago_custom_end, days_ago_custom_start)) for _ in range(custom_count)]
                            else:
                                date_spread = days_ago_custom_start - days_ago_custom_end
                                interval = date_spread / (custom_count - 1) if custom_count > 1 else 0
                                dates = [today - timedelta(days=int(days_ago_custom_start - (i * interval))) for i in range(custom_count)]
                            
                            for occ_date in dates:
                                occ_id = str(uuid.uuid4())
                                execute_query(f"""
                                    INSERT INTO AGEDCARE.AGEDCARE.DRI_INDICATOR_OCCURRENCES
                                    (OCCURRENCE_ID, RESIDENT_ID, CLIENT_SYSTEM_KEY, DEFICIT_ID, DEFICIT_NAME,
                                     OCCURRENCE_DATE, SOURCE_ID, SOURCE_TABLE, EVIDENCE_TEXT,
                                     APPROVED_BY, APPROVAL_DATE)
                                    VALUES (
                                        '{occ_id}',
                                        {custom_resident},
                                        '{custom_facility}',
                                        '{custom_indicator_id}',
                                        '{custom_deficit_name}',
                                        '{occ_date}',
                                        'CUSTOM_TEST',
                                        'TEST_DATA',
                                        '{custom_evidence.replace("'", "''")}',
                                        'TEST_GENERATOR',
                                        CURRENT_TIMESTAMP()
                                    )
                                """, session)
                            
                            st.success(f"✅ Created {custom_count} occurrence(s) for {custom_indicator_id}")
                            
                            date_list = sorted(set(dates))
                            st.caption(f"Dates: {', '.join([d.strftime('%Y-%m-%d') for d in date_list[:5]])}{'...' if len(date_list) > 5 else ''}")
                            
                        except Exception as e:
                            st.error(f"Error: {e}")
                    
                    st.markdown("---")
                    st.markdown("#### Bulk Scenario Generator")
                    st.caption("Generate multiple test scenarios at once for comprehensive testing")
                    
                    bulk_resident_start = st.number_input("Starting Resident ID", value=9100, min_value=1, key="bulk_start")
                    
                    bulk_scenarios = st.multiselect(
                        "Select scenarios to generate",
                        options=["threshold_under", "threshold_meets", "outside_lookback", "mixed_window", "near_expiry"],
                        format_func=lambda x: scenarios[x]["name"],
                        default=["threshold_under", "threshold_meets"],
                        key="bulk_scenarios"
                    )
                    
                    bulk_indicators = st.multiselect(
                        "Select deficits",
                        options=[f"{r['DEFICIT_ID']} - {r['DEFICIT_NAME']}" for _, r in rules_df.iterrows()],
                        default=[f"{rules_df.iloc[0]['DEFICIT_ID']} - {rules_df.iloc[0]['DEFICIT_NAME']}"],
                        key="bulk_indicators"
                    )
                    
                    if st.button("🚀 Generate Bulk Test Data", key="bulk_generate_btn"):
                        if bulk_scenarios and bulk_indicators:
                            total_created = 0
                            resident_id = bulk_resident_start
                            
                            for ind_label in bulk_indicators:
                                ind_id = ind_label.split(" - ")[0]
                                ind_rule = rules_df[rules_df['DEFICIT_ID'] == ind_id].iloc[0]
                                
                                for scenario_key in bulk_scenarios:
                                    threshold = int(ind_rule['THRESHOLD'])
                                    lookback = ind_rule['LOOKBACK_DAYS_HISTORIC']
                                    lookback_days = 9999 if lookback == 'all' else int(lookback)
                                    expiry_days = int(ind_rule['EXPIRY_DAYS']) if ind_rule['EXPIRY_DAYS'] else 0
                                    
                                    if scenario_key == "threshold_under":
                                        num_occ = max(1, threshold - 1)
                                        start, end = min(lookback_days - 1, 30), 0
                                    elif scenario_key == "threshold_meets":
                                        num_occ = threshold
                                        start, end = min(lookback_days - 1, 60), 0
                                    elif scenario_key == "outside_lookback":
                                        num_occ = threshold
                                        start, end = lookback_days + 30, lookback_days + 1
                                    elif scenario_key == "mixed_window":
                                        num_occ = threshold + 2
                                        start, end = lookback_days + 10, 0
                                    elif scenario_key == "near_expiry":
                                        num_occ = threshold
                                        start = end = max(1, expiry_days - 2)
                                    else:
                                        continue
                                    
                                    today = datetime.now().date()
                                    interval = (start - end) / (num_occ - 1) if num_occ > 1 else 0
                                    dates = [today - timedelta(days=int(start - (i * interval))) for i in range(num_occ)]
                                    
                                    for occ_date in dates:
                                        occ_id = str(uuid.uuid4())
                                        execute_query(f"""
                                            INSERT INTO AGEDCARE.AGEDCARE.DRI_INDICATOR_OCCURRENCES
                                            (OCCURRENCE_ID, RESIDENT_ID, CLIENT_SYSTEM_KEY, DEFICIT_ID, DEFICIT_NAME,
                                             OCCURRENCE_DATE, SOURCE_ID, SOURCE_TABLE, EVIDENCE_TEXT,
                                             APPROVED_BY, APPROVAL_DATE)
                                            VALUES (
                                                '{occ_id}',
                                                {resident_id},
                                                'BULK_TEST',
                                                '{ind_id}',
                                                '{ind_rule["DEFICIT_NAME"]}',
                                                '{occ_date}',
                                                'BULK_{scenario_key.upper()}',
                                                'TEST_DATA',
                                                'Bulk test: {scenarios[scenario_key]["name"]}',
                                                'BULK_GENERATOR',
                                                CURRENT_TIMESTAMP()
                                            )
                                        """, session)
                                        total_created += 1
                                    
                                    resident_id += 1
                            
                            st.success(f"✅ Created {total_created} occurrences across {resident_id - bulk_resident_start} test residents")
                            st.caption(f"Resident IDs: {bulk_resident_start} to {resident_id - 1}")
                        else:
                            st.warning("Select at least one scenario and one deficit")
            else:
                st.warning("Could not load indicator rules")
        
        with tab2:
            st.subheader("Clear Data for Selected Residents")
            
            resident_list = residents['RESIDENT_ID'].tolist()
            
            col1, col2 = st.columns([2, 1])
            with col1:
                selected_residents = st.multiselect(
                    "Select residents to clear",
                    resident_list,
                    help="Choose one or more residents"
                )
            with col2:
                if st.button("Select All", key="select_all_btn"):
                    st.session_state['selected_residents_clear'] = resident_list
                    st.rerun()
            
            if selected_residents:
                st.markdown(f"**Selected:** {len(selected_residents)} resident(s)")
                
                selected_data = residents[residents['RESIDENT_ID'].isin(selected_residents)]
                total_reviews = selected_data['REVIEW_COUNT'].sum()
                total_analyses = selected_data['ANALYSIS_COUNT'].sum()
                total_deficits = selected_data['DEFICIT_COUNT'].sum()
                
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("Review Queue Items", int(total_reviews))
                with col_m2:
                    st.metric("Analysis Records", int(total_analyses))
                with col_m3:
                    st.metric("Deficit Status Records", int(total_deficits))
                
                st.markdown("---")
                st.markdown("**Select what to clear:**")
                
                clear_reviews = st.checkbox("Clear Review Queue (approvals/rejections)", value=True, key="clear_reviews_cb")
                clear_analyses = st.checkbox("Clear LLM Analysis results", value=True, key="clear_analyses_cb")
                clear_occurrences = st.checkbox("Clear Indicator Occurrences (test data)", value=True, key="clear_occurrences_cb")
                clear_deficits = st.checkbox("Clear Deficit Status", value=False, key="clear_deficits_cb")
                clear_decisions = st.checkbox("Clear Clinical Decisions", value=False, key="clear_decisions_cb")
                
                st.markdown("---")
                
                resident_ids_str = ",".join([str(r) for r in selected_residents])
                
                confirm_text = st.text_input(
                    "Type 'CONFIRM' to enable the clear button",
                    key="confirm_resident_clear"
                )
                
                if st.button("🗑️ Clear Selected Data", type="primary", 
                           disabled=confirm_text != "CONFIRM",
                           key="clear_resident_btn"):
                    try:
                        deleted_counts = []
                        
                        if clear_reviews:
                            result = execute_query(f"""
                                DELETE FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE 
                                WHERE RESIDENT_ID IN ({resident_ids_str})
                            """, session)
                            deleted_counts.append(f"Review Queue: cleared")
                        
                        if clear_analyses:
                            result = execute_query(f"""
                                DELETE FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS 
                                WHERE RESIDENT_ID IN ({resident_ids_str})
                            """, session)
                            deleted_counts.append(f"LLM Analysis: cleared")
                        
                        if clear_occurrences:
                            result = execute_query(f"""
                                DELETE FROM AGEDCARE.AGEDCARE.DRI_INDICATOR_OCCURRENCES 
                                WHERE RESIDENT_ID IN ({resident_ids_str})
                            """, session)
                            deleted_counts.append(f"Indicator Occurrences: cleared")
                        
                        if clear_deficits:
                            result = execute_query(f"""
                                DELETE FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_STATUS 
                                WHERE RESIDENT_ID IN ({resident_ids_str})
                            """, session)
                            result = execute_query(f"""
                                DELETE FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_DETAIL 
                                WHERE RESIDENT_ID IN ({resident_ids_str})
                            """, session)
                            deleted_counts.append(f"Deficit Status/Detail: cleared")
                        
                        if clear_decisions:
                            result = execute_query(f"""
                                DELETE FROM AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS 
                                WHERE RESIDENT_ID IN ({resident_ids_str})
                            """, session)
                            deleted_counts.append(f"Clinical Decisions: cleared")
                        
                        st.success(f"✅ Cleared data for {len(selected_residents)} resident(s): {', '.join(deleted_counts)}")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error clearing data: {e}")
            else:
                st.info("Select one or more residents to clear their data", icon=":material/info:")
        
        with tab2:
            st.subheader("Clear All Testing Data")
            st.error("⚠️ This will delete ALL analysis and review data across ALL residents!", icon=":material/dangerous:")
            
            summary = execute_query("""
                SELECT 
                    (SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE) as REVIEW_COUNT,
                    (SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS) as ANALYSIS_COUNT,
                    (SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_STATUS) as DEFICIT_STATUS_COUNT,
                    (SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_DETAIL) as DEFICIT_DETAIL_COUNT,
                    (SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS) as DECISION_COUNT,
                    (SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_INDICATOR_OCCURRENCES) as OCCURRENCE_COUNT,
                    (SELECT COUNT(*) FROM AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH) as GROUND_TRUTH_COUNT
            """, session)
            
            if summary:
                st.markdown("**Current data counts:**")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Review Queue", summary[0]['REVIEW_COUNT'])
                    st.metric("Clinical Decisions", summary[0]['DECISION_COUNT'])
                with col2:
                    st.metric("LLM Analysis", summary[0]['ANALYSIS_COUNT'])
                    st.metric("Ground Truth", summary[0]['GROUND_TRUTH_COUNT'])
                with col3:
                    st.metric("Deficit Status", summary[0]['DEFICIT_STATUS_COUNT'])
                    st.metric("Deficit Detail", summary[0]['DEFICIT_DETAIL_COUNT'])
                with col4:
                    st.metric("Indicator Occurrences", summary[0]['OCCURRENCE_COUNT'])
            
            st.markdown("---")
            st.markdown("**Select tables to clear:**")
            
            clear_all_reviews = st.checkbox("Clear ALL Review Queue", value=False, key="clear_all_reviews")
            clear_all_analyses = st.checkbox("Clear ALL LLM Analysis", value=False, key="clear_all_analyses")
            clear_all_occurrences = st.checkbox("Clear ALL Indicator Occurrences", value=False, key="clear_all_occurrences")
            clear_all_deficits = st.checkbox("Clear ALL Deficit Status & Detail", value=False, key="clear_all_deficits")
            clear_all_decisions = st.checkbox("Clear ALL Clinical Decisions", value=False, key="clear_all_decisions")
            clear_all_ground_truth = st.checkbox("Clear ALL Ground Truth", value=False, key="clear_all_gt")
            
            st.markdown("---")
            
            confirm_all = st.text_input(
                "Type 'DELETE ALL' to enable the clear button",
                key="confirm_all_clear"
            )
            
            if st.button("🗑️ Clear All Selected Tables", type="primary",
                       disabled=confirm_all != "DELETE ALL",
                       key="clear_all_btn"):
                try:
                    cleared = []
                    
                    if clear_all_reviews:
                        execute_query("DELETE FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE", session)
                        cleared.append("Review Queue")
                    
                    if clear_all_analyses:
                        execute_query("DELETE FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS", session)
                        cleared.append("LLM Analysis")
                    
                    if clear_all_occurrences:
                        execute_query("DELETE FROM AGEDCARE.AGEDCARE.DRI_INDICATOR_OCCURRENCES", session)
                        cleared.append("Indicator Occurrences")
                    
                    if clear_all_deficits:
                        execute_query("DELETE FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_STATUS", session)
                        execute_query("DELETE FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_DETAIL", session)
                        cleared.append("Deficit Status/Detail")
                    
                    if clear_all_decisions:
                        execute_query("DELETE FROM AGEDCARE.AGEDCARE.DRI_CLINICAL_DECISIONS", session)
                        cleared.append("Clinical Decisions")
                    
                    if clear_all_ground_truth:
                        execute_query("DELETE FROM AGEDCARE.AGEDCARE.DRI_GROUND_TRUTH", session)
                        cleared.append("Ground Truth")
                    
                    if cleared:
                        st.success(f"✅ Cleared: {', '.join(cleared)}")
                        st.rerun()
                    else:
                        st.warning("No tables selected to clear")
                        
                except Exception as e:
                    st.error(f"Error: {e}")
        
        with tab3:
            st.subheader("Data Summary")
            
            st.markdown("**Records by Resident:**")
            st.dataframe(
                residents.rename(columns={
                    'RESIDENT_ID': 'Resident',
                    'REVIEW_COUNT': 'Reviews',
                    'ANALYSIS_COUNT': 'Analyses',
                    'DEFICIT_COUNT': 'Deficits'
                }),
                use_container_width=True,
                hide_index=True
            )
            
            st.markdown("---")
            st.markdown("**Review Status Breakdown:**")
            
            review_status = execute_query_df("""
                SELECT STATUS, COUNT(*) as COUNT
                FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE
                GROUP BY STATUS
                ORDER BY COUNT DESC
            """, session)
            
            if review_status is not None and len(review_status) > 0:
                st.dataframe(review_status, use_container_width=True, hide_index=True)
            else:
                st.info("No review queue data", icon=":material/info:")
            
            st.markdown("---")
            st.markdown("**Analysis by Prompt Version:**")
            
            analysis_by_version = execute_query_df("""
                SELECT PROMPT_VERSION, COUNT(*) as COUNT, 
                       COUNT(DISTINCT RESIDENT_ID) as RESIDENTS
                FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS
                GROUP BY PROMPT_VERSION
                ORDER BY COUNT DESC
            """, session)
            
            if analysis_by_version is not None and len(analysis_by_version) > 0:
                st.dataframe(analysis_by_version, use_container_width=True, hide_index=True)
            else:
                st.info("No analysis data", icon=":material/info:")
    else:
        st.info("No resident data found", icon=":material/info:")

else:
    st.error("Failed to connect to Snowflake")
