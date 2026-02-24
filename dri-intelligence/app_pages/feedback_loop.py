import streamlit as st
import json
from datetime import datetime, timedelta

from src.connection_helper import get_snowflake_session, execute_query_df, execute_query

with st.expander("How to use this page", expanded=False, icon=":material/help:"):
    st.markdown("""
### Purpose
This is the **continuous improvement hub** for LLM prompt accuracy. It closes the feedback loop by analyzing rejection patterns and using AI to suggest targeted prompt improvements.

### Sections

| Section | Purpose |
|---------|---------|
| **Indicator Rejection Stats** | Overview metrics and bar chart showing which indicators are most frequently rejected |
| **Detailed Rejections** | Drill-down table with full context: indicator ID, name, LLM reasoning, confidence, and human rejection reason |
| **AI Prompt Analysis** | Cortex AI analyzes rejection patterns against the current prompt and suggests specific improvements |

### Key Features
- **Time Period Filter**: Analyze rejections from All Time, Last 7/30/90 days
- **Facility Filter**: Focus on specific facilities or view all
- **Prompt Version Filter**: Compare rejection rates across prompt versions
- **RAG Context Included**: AI sees both the prompt text AND the indicator definitions, so it can suggest fixes to either

### AI Suggestion Output
The AI provides actionable improvements:
- **📝 Prompt Fixes**: Specific text to modify in the prompt
- **📚 RAG Definition Fixes**: Suggested improvements to indicator definitions
- **Expected Impact**: Estimated reduction in rejection rate

### Workflow
1. Run batch tests in **Batch Testing**
2. Review and approve/reject indicators in **Review Queue**
3. Come here to analyze why indicators were rejected
4. Apply AI suggestions in **Prompt Engineering** or **Configuration > DRI Rules**
5. Re-test to measure improvement

### Tips
- Focus on indicators with >10% rejection rate first
- Look for patterns: same rejection reason across multiple indicators
- After making changes, re-run batch tests and compare approval rates
    """)

session = get_snowflake_session()

if session:
    st.caption("Analyze rejection patterns and get AI suggestions to improve prompt accuracy.")
    
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        prompt_versions = execute_query_df("""
            SELECT DISTINCT PROMPT_VERSION 
            FROM AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS
            WHERE PROMPT_VERSION IS NOT NULL
            ORDER BY PROMPT_VERSION DESC
        """, session)
        
        version_options = []
        if prompt_versions is not None and len(prompt_versions) > 0:
            version_options = prompt_versions['PROMPT_VERSION'].tolist()
        
        default_idx = 0
        if 'v1.6' in version_options:
            default_idx = version_options.index('v1.6')
        
        selected_version = st.selectbox("Select prompt version", version_options, index=default_idx)
    
    with col_filter2:
        facilities = execute_query_df("""
            SELECT DISTINCT CLIENT_SYSTEM_KEY 
            FROM AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE
            WHERE CLIENT_SYSTEM_KEY IS NOT NULL
            ORDER BY CLIENT_SYSTEM_KEY
        """, session)
        
        facility_options = ["All Facilities"]
        if facilities is not None and len(facilities) > 0:
            facility_options += facilities['CLIENT_SYSTEM_KEY'].tolist()
        
        selected_facility = st.selectbox("Filter by facility", facility_options)
    
    with col_filter3:
        time_options = {
            "All Time": None,
            "Last 7 days": 7,
            "Last 30 days": 30,
            "Last 90 days": 90
        }
        selected_time = st.selectbox("Time period", list(time_options.keys()))
        time_days = time_options[selected_time]
    
    where_clauses = []
    if selected_version:
        where_clauses.append(f"PROMPT_VERSION = '{selected_version}'")
    if selected_facility != "All Facilities":
        where_clauses.append(f"CLIENT_SYSTEM_KEY = '{selected_facility}'")
    
    time_filter_sql = ""
    if time_days:
        time_filter_sql = f"ir.REJECTED_TIMESTAMP >= DATEADD(day, -{time_days}, CURRENT_TIMESTAMP())"
    
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    st.markdown("---")
    
    st.subheader(":material/bar_chart: Indicator Rejection Rates")
    
    review_stats = execute_query_df(f"""
        SELECT 
            INDICATOR_ID,
            INDICATOR_NAME,
            PROMPT_VERSION,
            CLIENT_SYSTEM_KEY,
            TOTAL_REVIEWS,
            ACCEPTED_COUNT,
            REJECTED_COUNT,
            REJECTION_RATE_PCT
        FROM AGEDCARE.AGEDCARE.V_INDICATOR_REVIEW_STATS
        {where_sql}
        ORDER BY REJECTION_RATE_PCT DESC, TOTAL_REVIEWS DESC
    """, session)
    
    if review_stats is not None and len(review_stats) > 0:
        total_reviews = review_stats['TOTAL_REVIEWS'].sum()
        total_accepted = review_stats['ACCEPTED_COUNT'].sum()
        total_rejected = review_stats['REJECTED_COUNT'].sum()
        overall_reject_rate = round(100.0 * total_rejected / total_reviews, 1) if total_reviews > 0 else 0
        
        with st.container(border=True):
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Total Indicator Reviews", total_reviews)
            col_m2.metric("Accepted", total_accepted, delta=f"{round(100*total_accepted/total_reviews,1)}%")
            col_m3.metric("Rejected", total_rejected, delta=f"-{overall_reject_rate}%", delta_color="inverse")
            col_m4.metric("Overall Reject Rate", f"{overall_reject_rate}%")
        
        chart_data = review_stats[['INDICATOR_ID', 'REJECTION_RATE_PCT', 'TOTAL_REVIEWS']].copy()
        chart_data = chart_data.sort_values('REJECTION_RATE_PCT', ascending=True)
        
        st.bar_chart(
            chart_data.set_index('INDICATOR_ID')['REJECTION_RATE_PCT'],
            horizontal=True,
            color="#ff6b6b"
        )
        
        st.markdown("**Indicator Details:**")
        for idx, row in review_stats.iterrows():
            rate = row['REJECTION_RATE_PCT']
            status_emoji = "🔴" if rate >= 50 else "🟡" if rate >= 20 else "🟢"
            
            with st.expander(f"{status_emoji} {row['INDICATOR_ID']} - {row['INDICATOR_NAME']} ({rate}% reject rate)"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Reviews", row['TOTAL_REVIEWS'])
                    st.metric("Accepted", row['ACCEPTED_COUNT'])
                with col2:
                    st.metric("Rejected", row['REJECTED_COUNT'])
                    st.metric("Reject Rate", f"{rate}%")
                
                rejections = execute_query_df(f"""
                    SELECT 
                        ir.REJECTION_REASON,
                        ir.REJECTED_BY,
                        ir.REJECTED_TIMESTAMP,
                        rq.RESIDENT_ID
                    FROM AGEDCARE.AGEDCARE.DRI_INDICATOR_REJECTIONS ir
                    JOIN AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE rq ON ir.QUEUE_ID = rq.QUEUE_ID
                    WHERE ir.INDICATOR_ID = '{row['INDICATOR_ID']}'
                    ORDER BY ir.REJECTED_TIMESTAMP DESC
                    LIMIT 10
                """, session)
                
                if rejections is not None and len(rejections) > 0:
                    st.markdown("**Recent Rejection Reasons:**")
                    for _, rej in rejections.iterrows():
                        st.markdown(f"- **Resident {rej['RESIDENT_ID']}**: _{rej['REJECTION_REASON']}_")
    else:
        st.info("No reviewed indicators found. Run batch tests and review them in the Review Queue first.", icon=":material/info:")
    
    st.markdown("---")
    
    st.subheader(":material/category: Rejection Reason Themes")
    
    rejection_base_query = f"""
        SELECT 
            ir.INDICATOR_ID,
            ir.INDICATOR_NAME,
            ir.REJECTION_REASON,
            ir.REJECTED_TIMESTAMP,
            rq.RESIDENT_ID,
            lla.ANALYSIS_ID,
            lla.RAW_RESPONSE
        FROM AGEDCARE.AGEDCARE.DRI_INDICATOR_REJECTIONS ir
        JOIN AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE rq ON ir.QUEUE_ID = rq.QUEUE_ID
        JOIN AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS lla ON rq.ANALYSIS_ID = lla.ANALYSIS_ID
        WHERE 1=1
        {f" AND lla.PROMPT_VERSION = '{selected_version}'" if selected_version else ""}
        {f" AND rq.CLIENT_SYSTEM_KEY = '{selected_facility}'" if selected_facility != "All Facilities" else ""}
        {f" AND {time_filter_sql}" if time_filter_sql else ""}
        ORDER BY ir.REJECTED_TIMESTAMP DESC
        LIMIT 500
    """
    
    rejection_data = execute_query_df(rejection_base_query, session)
    
    if rejection_data is not None and len(rejection_data) > 0:
        st.caption(f"Analyzing **{len(rejection_data)}** rejections from selected filters")
        
        all_reasons = rejection_data['REJECTION_REASON'].tolist()
        reasons_text = "\n".join([f"- {r}" for r in all_reasons[:100]])
        
        if st.button("🤖 Analyze Rejection Themes", use_container_width=True):
            with st.spinner("Analyzing rejection patterns with Cortex AI..."):
                theme_prompt = f"""Analyze these rejection reasons from DRI indicator reviews and cluster them into 2-5 common themes.

REJECTION REASONS:
{reasons_text}

Return a JSON array where each theme has:
- "theme_name": short descriptive name (e.g., "Medicine-based diagnosis")
- "description": what this theme means
- "count": estimated number of rejections in this theme
- "example_reasons": array of 2-3 example rejection reasons from the list
- "affected_indicators": which indicator types this theme applies to

Return ONLY valid JSON array, no other text."""
                
                try:
                    theme_result = execute_query(f"""
                        SELECT SNOWFLAKE.CORTEX.COMPLETE(
                            'claude-3-5-sonnet',
                            '{theme_prompt.replace("'", "''")}'
                        ) AS RESPONSE
                    """, session)
                    
                    if theme_result and theme_result[0]['RESPONSE']:
                        response_text = theme_result[0]['RESPONSE']
                        
                        try:
                            if '```json' in response_text:
                                response_text = response_text.split('```json')[1].split('```')[0]
                            elif '```' in response_text:
                                response_text = response_text.split('```')[1].split('```')[0]
                            
                            themes = json.loads(response_text.strip())
                            
                            st.session_state['rejection_themes'] = themes
                        except json.JSONDecodeError:
                            st.error("Could not parse AI response. Raw response:")
                            st.code(response_text)
                except Exception as e:
                    st.error(f"Error analyzing themes: {str(e)}")
        
        if 'rejection_themes' in st.session_state:
            themes = st.session_state['rejection_themes']
            
            for theme in themes:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**🏷️ {theme.get('theme_name', 'Unknown Theme')}**")
                        st.caption(theme.get('description', ''))
                    with col2:
                        st.metric("Count", theme.get('count', '?'))
                    
                    if theme.get('example_reasons'):
                        st.markdown("*Example reasons:*")
                        for ex in theme.get('example_reasons', [])[:3]:
                            st.markdown(f"- _{ex}_")
                    
                    if theme.get('affected_indicators'):
                        st.markdown(f"*Affects:* `{', '.join(theme.get('affected_indicators', []))}`")
    else:
        st.info("No rejection data available yet. Reject some indicators in the Review Queue first.", icon=":material/info:")
    
    st.markdown("---")
    
    st.subheader(":material/lightbulb: AI Prompt Improvement Suggestions")
    
    if rejection_data is not None and len(rejection_data) > 0:
        current_prompt_text = None
        current_prompt_version = selected_version
        
        prompt_query = f"""
            SELECT VERSION_NUMBER, PROMPT_TEXT 
            FROM DRI_PROMPT_VERSIONS 
            WHERE VERSION_NUMBER = '{selected_version}'
            LIMIT 1
        """
        prompt_result = execute_query(prompt_query, session)
        
        dri_rules = execute_query("""
            SELECT DEFICIT_ID, DEFICIT_NAME, DEFINITION, DEFICIT_TYPE, 
                   EXPIRY_DAYS, KEYWORDS
            FROM AGEDCARE.AGEDCARE.DRI_RULES
            WHERE IS_CURRENT_VERSION = TRUE AND IS_ACTIVE = TRUE
            ORDER BY DEFICIT_ID
        """, session)
        
        rag_indicator_text = ""
        if dri_rules:
            rag_parts = []
            for ind in dri_rules:
                keywords_str = ', '.join(ind['KEYWORDS']) if ind['KEYWORDS'] else 'N/A'
                rag_parts.append(f"""
{ind['DEFICIT_ID']} - {ind['DEFICIT_NAME']}
  Type: {ind['DEFICIT_TYPE']}
  Definition: {ind['DEFINITION']}
  Expiry Days: {ind['EXPIRY_DAYS'] or 'N/A (chronic)'}
  Keywords: {keywords_str}
""")
            rag_indicator_text = "\n".join(rag_parts)
        
        if prompt_result and len(prompt_result) > 0:
            current_prompt_text = prompt_result[0]['PROMPT_TEXT']
            current_prompt_version = prompt_result[0]['VERSION_NUMBER']
            
            filled_prompt = current_prompt_text.replace(
                '{rag_indicator_context}', rag_indicator_text
            ).replace(
                '{client_form_mappings}', '[Client-specific form mappings]'
            ).replace(
                '{resident_context}', '[Resident clinical data]'
            )
            
            with st.expander(f"📄 Selected Prompt ({current_prompt_version}) - with RAG content filled in", expanded=False):
                st.code(filled_prompt, language=None)
        
        detailed_rejections_query = f"""
            SELECT 
                ir.INDICATOR_ID,
                ir.INDICATOR_NAME,
                ir.REJECTION_REASON,
                rq.RESIDENT_ID,
                f.value:reasoning::STRING as LLM_REASONING,
                f.value:confidence::STRING as LLM_CONFIDENCE,
                f.value:temporal_status:type::STRING as TEMPORAL_TYPE
            FROM AGEDCARE.AGEDCARE.DRI_INDICATOR_REJECTIONS ir
            JOIN AGEDCARE.AGEDCARE.DRI_REVIEW_QUEUE rq ON ir.QUEUE_ID = rq.QUEUE_ID
            JOIN AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS lla ON rq.ANALYSIS_ID = lla.ANALYSIS_ID,
            LATERAL FLATTEN(input => lla.RAW_RESPONSE:indicators) f
            WHERE f.value:deficit_id::STRING = ir.INDICATOR_ID
            {f" AND lla.PROMPT_VERSION = '{selected_version}'" if selected_version else ""}
            {f" AND rq.CLIENT_SYSTEM_KEY = '{selected_facility}'" if selected_facility != "All Facilities" else ""}
            {f" AND {time_filter_sql}" if time_filter_sql else ""}
            ORDER BY ir.REJECTED_TIMESTAMP DESC
            LIMIT 200
        """
        
        detailed_rejections = execute_query_df(detailed_rejections_query, session)
        
        if st.button("🤖 Analyze Prompt & Generate Improvement Suggestions", use_container_width=True, type="primary"):
            with st.spinner("Analyzing rejection patterns against current prompt..."):
                if detailed_rejections is not None and len(detailed_rejections) > 0:
                    rejection_count = len(detailed_rejections)
                    st.info(f"Analyzing **{rejection_count}** rejections with full indicator context...")
                    
                    reasons_for_ai = []
                    for _, r in detailed_rejections.iterrows():
                        entry = f"""
---
INDICATOR: {r['INDICATOR_ID']} - {r['INDICATOR_NAME']}
RESIDENT: {r['RESIDENT_ID']}
LLM CONFIDENCE: {r['LLM_CONFIDENCE'] or 'N/A'}
LLM REASONING: {r['LLM_REASONING'] or 'N/A'}
HUMAN REJECTION REASON: {r['REJECTION_REASON']}
---"""
                        reasons_for_ai.append(entry)
                    
                    reasons_text = "\n".join(reasons_for_ai[:150])
                    
                    indicators_affected = detailed_rejections['INDICATOR_ID'].unique().tolist()
                else:
                    rejection_count = len(rejection_data)
                    st.info(f"Analyzing **{rejection_count}** rejections...")
                    reasons_text = "\n".join([f"- [{r['INDICATOR_ID']}] {r['REJECTION_REASON']}" for _, r in rejection_data.head(150).iterrows()])
                    indicators_affected = rejection_data['INDICATOR_ID'].unique().tolist()
                
                prompt_context = ""
                if current_prompt_text:
                    filled_prompt_for_ai = current_prompt_text.replace(
                        '{rag_indicator_context}', rag_indicator_text
                    ).replace(
                        '{client_form_mappings}', '[Client-specific form mappings - varies per facility]'
                    ).replace(
                        '{resident_context}', '[Resident clinical data - varies per resident]'
                    )
                    
                    prompt_context = f"""
CURRENT PROMPT TEXT (version {current_prompt_version}) WITH RAG INDICATOR DEFINITIONS FILLED IN:
---
{filled_prompt_for_ai}
---

"""
                
                suggestion_prompt = f"""You are an expert at improving LLM prompts for clinical analysis.

{prompt_context}REJECTED INDICATORS WITH CONTEXT:
Each entry shows the indicator, the LLM's reasoning for detecting it, and why the human reviewer rejected it.

{reasons_text}

AFFECTED INDICATORS: {', '.join(indicators_affected)}

Your task:
1. Compare the LLM's reasoning against the human's rejection reason to understand WHY the LLM made errors
2. Examine the CURRENT PROMPT TEXT (including the RAG indicator definitions) to identify instructions that may be CAUSING the errors
3. Note that the prompt has RAG lookups for indicator definitions - suggest changes to EITHER the prompt instructions OR the RAG indicator definitions
4. Suggest SPECIFIC EDITS - including text to REMOVE or REPLACE, not just additions

Return JSON with this structure:
{{
    "problem_summary": "Clear 1-2 sentence description of the main issue causing rejections",
    "root_causes": ["cause 1", "cause 2"],
    "problematic_prompt_sections": [
        {{
            "original_text": "The exact text from the current prompt that is problematic (copy verbatim)",
            "problem": "Why this text is causing issues",
            "suggested_replacement": "The new text to replace it with (or 'DELETE' if it should be removed entirely)",
            "affected_indicators": ["D008", "D025"],
            "location": "prompt_instructions OR rag_indicator_definitions"
        }}
    ],
    "suggested_additions": [
        {{
            "instruction": "New text to ADD to the prompt (only if nothing needs to be replaced)",
            "rationale": "Why this will help",
            "where_to_add": "Where in the prompt this should be added",
            "affected_indicators": ["D008"],
            "location": "prompt_instructions OR rag_indicator_definitions"
        }}
    ],
    "expected_impact": "Estimate of how much this could reduce rejections"
}}

IMPORTANT: 
- Prioritize identifying problematic_prompt_sections over suggesting additions
- Indicate whether the fix should be in prompt_instructions or rag_indicator_definitions
- Copy original_text EXACTLY as it appears so users can find and replace it

Return ONLY valid JSON."""
                
                try:
                    suggestion_result = execute_query(f"""
                        SELECT SNOWFLAKE.CORTEX.COMPLETE(
                            'claude-3-5-sonnet',
                            '{suggestion_prompt.replace("'", "''")}'
                        ) AS RESPONSE
                    """, session)
                    
                    if suggestion_result and suggestion_result[0]['RESPONSE']:
                        response_text = suggestion_result[0]['RESPONSE']
                        
                        try:
                            if '```json' in response_text:
                                response_text = response_text.split('```json')[1].split('```')[0]
                            elif '```' in response_text:
                                response_text = response_text.split('```')[1].split('```')[0]
                            
                            suggestions = json.loads(response_text.strip())
                            st.session_state['prompt_suggestions'] = suggestions
                        except json.JSONDecodeError:
                            st.error("Could not parse AI response. Raw response:")
                            st.code(response_text)
                except Exception as e:
                    st.error(f"Error generating suggestions: {str(e)}")
        
        if 'prompt_suggestions' in st.session_state:
            suggestions = st.session_state['prompt_suggestions']
            
            with st.container(border=True):
                st.markdown("### 📋 Problem Summary")
                st.warning(suggestions.get('problem_summary', 'No summary available'))
                
                if suggestions.get('root_causes'):
                    st.markdown("**Root Causes:**")
                    for cause in suggestions.get('root_causes', []):
                        st.markdown(f"- {cause}")
            
            if suggestions.get('problematic_prompt_sections'):
                st.markdown("### 🔧 Prompt Text to Edit/Replace")
                st.caption("These sections of the current prompt or RAG definitions may be causing the rejections:")
                
                for i, section in enumerate(suggestions.get('problematic_prompt_sections', []), 1):
                    with st.container(border=True):
                        location = section.get('location', 'prompt_instructions')
                        location_badge = "📝 Prompt" if location == 'prompt_instructions' else "📚 RAG Definitions"
                        st.markdown(f"**Issue {i}** ({location_badge}): {section.get('problem', '')}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**❌ Current Text (remove/replace):**")
                            st.code(section.get('original_text', ''), language=None)
                        with col2:
                            replacement = section.get('suggested_replacement', '')
                            if replacement.upper() == 'DELETE':
                                st.markdown("**🗑️ Action: DELETE this text**")
                            else:
                                st.markdown("**✅ Replace with:**")
                                st.code(replacement, language=None)
                        
                        if section.get('affected_indicators'):
                            st.caption(f"*Affects:* {', '.join(section.get('affected_indicators', []))}")
            
            if suggestions.get('suggested_additions'):
                st.markdown("### ➕ Additional Text to Add")
                st.caption("New instructions to add (only if replacement suggestions above are not sufficient):")
                
                for i, addition in enumerate(suggestions.get('suggested_additions', []), 1):
                    with st.container(border=True):
                        location = addition.get('location', 'prompt_instructions')
                        location_badge = "📝 Prompt" if location == 'prompt_instructions' else "📚 RAG Definitions"
                        st.markdown(f"**Addition {i}** ({location_badge}):")
                        st.code(addition.get('instruction', ''), language=None)
                        st.caption(f"*Where:* {addition.get('where_to_add', 'End of prompt')}")
                        st.caption(f"*Rationale:* {addition.get('rationale', '')}")
                        if addition.get('affected_indicators'):
                            st.caption(f"*Affects:* {', '.join(addition.get('affected_indicators', []))}")
            
            if suggestions.get('expected_impact'):
                st.markdown("### 📈 Expected Impact")
                st.success(suggestions.get('expected_impact', 'Unknown'))
            
            st.info("💡 **Next Step:** Go to the **Prompt Engineering** page to edit the prompt, or update RAG indicator definitions in the Configuration page.", icon=":material/arrow_forward:")
    else:
        st.info("No rejection data available yet. Complete some reviews in the Review Queue first.", icon=":material/info:")

else:
    st.error("Failed to connect to Snowflake", icon=":material/error:")
