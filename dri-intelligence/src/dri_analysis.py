import json
import time
from datetime import datetime

def run_llm_analysis(session, resident_id: int, client_system_key: str, prompt_version: str = None):
    resident_context = get_resident_context(session, resident_id)
    if not resident_context:
        return None, "Failed to retrieve resident context"
    
    rag_indicators = get_rag_indicators(session)
    
    if prompt_version:
        prompt_result = session.sql(f"""
            SELECT PROMPT_TEXT FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS 
            WHERE VERSION_NUMBER = '{prompt_version}'
        """).collect()
    else:
        prompt_result = session.sql("""
            SELECT PROMPT_TEXT FROM AGEDCARE.AGEDCARE.DRI_PROMPT_VERSIONS 
            WHERE IS_ACTIVE = TRUE LIMIT 1
        """).collect()
    
    if not prompt_result:
        return None, "No prompt template found"
    
    prompt_template = prompt_result[0]['PROMPT_TEXT']
    
    config_result = session.sql(f"""
        SELECT CONFIG_JSON FROM AGEDCARE.AGEDCARE.DRI_CLIENT_CONFIG 
        WHERE CLIENT_SYSTEM_KEY = '{client_system_key}' AND IS_ACTIVE = TRUE
    """).collect()
    
    client_config = config_result[0]['CONFIG_JSON'] if config_result else "{}"
    
    final_prompt = prompt_template.replace(
        '{client_form_mappings}', str(client_config)
    ).replace(
        '{resident_context}', resident_context
    ).replace(
        '{rag_indicator_context}', rag_indicators
    )
    
    start_time = time.time()
    
    escaped_prompt = final_prompt.replace("'", "''")
    
    try:
        result = session.sql(f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'claude-3-5-sonnet',
                '{escaped_prompt}'
            ) AS RESPONSE
        """).collect()
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        if result:
            response_text = result[0]['RESPONSE']
            
            session.sql(f"""
                INSERT INTO AGEDCARE.AGEDCARE.DRI_LLM_ANALYSIS 
                (RESIDENT_ID, CLIENT_SYSTEM_KEY, MODEL_USED, PROMPT_VERSION, RAW_RESPONSE, PROCESSING_TIME_MS)
                SELECT 
                    {resident_id},
                    '{client_system_key}',
                    'claude-3-5-sonnet',
                    '{prompt_version or "v1.0"}',
                    PARSE_JSON($${response_text}$$),
                    {processing_time_ms}
            """).collect()
            
            return response_text, None
        else:
            return None, "No response from LLM"
            
    except Exception as e:
        return None, str(e)

def get_resident_context(session, resident_id: int, max_notes: int = 15, max_obs: int = 30, max_forms: int = 30) -> str:
    context_parts = []
    
    notes = session.sql(f"""
        SELECT PROGRESS_NOTE, EVENT_DATE, ENTERED_BY_USER, NOTE_TYPE
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES 
        WHERE RESIDENT_ID = {resident_id}
        ORDER BY EVENT_DATE DESC
        LIMIT {max_notes}
    """).collect()
    
    if notes:
        context_parts.append("=== PROGRESS NOTES ===")
        for note in notes:
            note_text = str(note['PROGRESS_NOTE'])[:500]
            context_parts.append(f"Date: {note['EVENT_DATE']}, Type: {note['NOTE_TYPE']}")
            context_parts.append(f"Note: {note_text}")
            context_parts.append("---")
    
    meds = session.sql(f"""
        SELECT MED_NAME, MED_ROUTE, MED_STATUS, MED_START_DATE
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION 
        WHERE RESIDENT_ID = {resident_id}
        LIMIT 20
    """).collect()
    
    if meds:
        context_parts.append("\n=== MEDICATIONS ===")
        for med in meds:
            context_parts.append(f"- {med['MED_NAME']} ({med['MED_ROUTE']}) - Status: {med['MED_STATUS']}")
    
    obs = session.sql(f"""
        SELECT CHART_NAME, CHART_LABEL, OBSERVATION_VALUE, EVENT_DATE
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS 
        WHERE RESIDENT_ID = {resident_id}
        ORDER BY EVENT_DATE DESC
        LIMIT {max_obs}
    """).collect()
    
    if obs:
        context_parts.append("\n=== OBSERVATIONS ===")
        for o in obs:
            obs_val = str(o['OBSERVATION_VALUE'])[:100]
            context_parts.append(f"- {o['CHART_NAME']}/{o['CHART_LABEL']}: {obs_val} ({o['EVENT_DATE']})")
    
    forms = session.sql(f"""
        SELECT FORM_NAME, ELEMENT_NAME, RESPONSE, EVENT_DATE
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_ASSESSMENT_FORMS 
        WHERE RESIDENT_ID = {resident_id}
        ORDER BY EVENT_DATE DESC
        LIMIT {max_forms}
    """).collect()
    
    if forms:
        context_parts.append("\n=== ASSESSMENT FORMS ===")
        for f in forms:
            response_text = str(f['RESPONSE'])[:200]
            context_parts.append(f"- {f['FORM_NAME']}: {f['ELEMENT_NAME']} = {response_text}")
    
    return "\n".join(context_parts)

def get_rag_indicators(session) -> str:
    indicators = session.sql("""
        SELECT INDICATOR_ID, INDICATOR_NAME, DEFINITION, TEMPORAL_TYPE, 
               DEFAULT_EXPIRY_DAYS, INCLUSION_CRITERIA, EXCLUSION_CRITERIA
        FROM AGEDCARE.AGEDCARE.DRI_RAG_INDICATORS
        ORDER BY INDICATOR_ID
    """).collect()
    
    indicator_text = []
    for ind in indicators:
        indicator_text.append(f"""
{ind['INDICATOR_ID']} - {ind['INDICATOR_NAME']}
  Type: {ind['TEMPORAL_TYPE']}
  Definition: {ind['DEFINITION']}
  Expiry Days: {ind['DEFAULT_EXPIRY_DAYS'] or 'N/A (chronic)'}
  Include when: {ind['INCLUSION_CRITERIA']}
  Exclude when: {ind['EXCLUSION_CRITERIA']}
""")
    return "\n".join(indicator_text)

def calculate_dri_score(session, resident_id: int):
    result = session.sql(f"""
        SELECT COUNT(*) as ACTIVE_DEFICITS
        FROM AGEDCARE.AGEDCARE.DRI_DEFICIT_STATUS
        WHERE RESIDENT_ID = {resident_id} AND DEFICIT_STATUS = 'ACTIVE'
    """).collect()
    
    if result:
        active_deficits = result[0]['ACTIVE_DEFICITS']
        dri_score = active_deficits / 33.0
        
        if dri_score <= 0.2:
            severity_band = 'Low'
        elif dri_score <= 0.4:
            severity_band = 'Medium'
        elif dri_score <= 0.6:
            severity_band = 'High'
        else:
            severity_band = 'Very High'
        
        return dri_score, severity_band, active_deficits
    
    return 0.0, 'Low', 0
