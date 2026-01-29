#!/usr/bin/env python3
"""
Standalone regex verification script to double-check indicator detection
for Resident 871 against ALL data (no truncation).
"""

import os
import re
import snowflake.connector

conn = snowflake.connector.connect(connection_name=os.getenv("SNOWFLAKE_CONNECTION_NAME") or "coco-snowflake")

KEYWORDS_BY_INDICATOR = {
    "CARD_01": ["heart failure", "chf", "congestive cardiac failure", "ejection fraction", "cardiac insufficiency"],
    "CARD_02": ["atrial fibrillation", "afib", "af ", "anticoagulant", "warfarin", "eliquis", "xarelto", "noac"],
    "CARD_03": ["hypertension", "high blood pressure", "antihypertensive", "uncontrolled bp"],
    "CONT_01": ["urinary incontinence", "continence aid", "bladder", "incontinence pad", "urine leak"],
    "CONT_02": ["fecal incontinence", "bowel incontinence", "bowel accident", "faecal"],
    "CONT_03": ["uti", "urinary tract infection", "urine culture", "recurrent uti"],
    "DM_01": ["type 1 diabetes", "insulin dependent", "t1dm", "iddm"],
    "DM_02": ["type 2 diabetes", "diabetes", "bgl", "blood glucose", "metformin", "hypoglycemic", "hba1c", "novorapid", "insulin"],
    "DM_03": ["diabetic retinopathy", "diabetic neuropathy", "diabetic nephropathy", "diabetic foot", "diabetic ulcer"],
    "FALL_01": ["fall risk", "fall ", "falls", "fell", "uwf", "unwitnessed fall", "mobility aid", "4wf", "walker"],
    "FALL_02": ["fracture", "broken bone", "x-ray", "surgical repair"],
    "FUNC_01": ["functional decline", "adl decline", "increased assistance", "declining independence"],
    "INF_01": ["infection", "antibiotic", "cellulitis", "sepsis", "infected", "abs for"],
    "MED_01": ["polypharmacy", "9 medications", "medication review", "multiple medications"],
    "MED_02": ["warfarin", "opioid", "insulin", "novorapid", "fentanyl", "morphine", "oxycodone", "anticoagulant"],
    "MH_01": ["depression", "depressed", "antidepressant", "ssri", "low mood"],
    "MH_02": ["anxiety", "anxious", "anxiolytic", "benzodiazepine"],
    "MH_03": ["behaviour", "behavior", "bpsd", "agitation", "aggression", "antipsychotic"],
    "NEURO_01": ["dementia", "alzheimer", "cognitive decline", "memory loss", "donepezil", "aricept"],
    "NEURO_02": ["stroke", "cva", "cerebrovascular", "tia", "transient ischemic"],
    "NEURO_03": ["parkinson", "dopaminergic", "tremor", "bradykinesia"],
    "NEURO_04": ["seizure", "epilepsy", "anticonvulsant", "convulsion"],
    "NUTR_01": ["malnutrition", "underweight", "nutritional risk", "low albumin", "poor intake", "weight loss"],
    "NUTR_02": ["weight loss", "losing weight", "unintentional weight"],
    "NUTR_03": ["dysphagia", "swallowing difficulty", "modified diet", "thickened fluid", "speech pathology"],
    "PAIN_01": ["chronic pain", "pain management", "analgesia", "pain >3 months", "ongoing pain"],
    "PAIN_02": ["pain score", "pain assessment", "breakthrough pain", "severe pain"],
    "RESP_01": ["copd", "emphysema", "chronic bronchitis", "spiriva", "tiotropium", "oxygen therapy"],
    "RESP_02": ["asthma", "bronchodilator", "inhaler", "puffer", "ventolin", "salbutamol"],
    "RESP_03": ["pneumonia", "bronchitis", "respiratory infection", "chest infection"],
    "SKIN_01": ["pressure injury", "pressure ulcer", "bedsore", "decubitus", "pressure wound"],
    "SKIN_02": ["skin tear", "wound", "dressing", "fragile skin", "laceration", "abrasion"],
    "SKIN_03": ["chronic wound", "non-healing", "wound care specialist", "negative pressure"],
}

INDICATOR_NAMES = {
    "CARD_01": "Heart Failure",
    "CARD_02": "Atrial Fibrillation", 
    "CARD_03": "Hypertension",
    "CONT_01": "Urinary Incontinence",
    "CONT_02": "Fecal Incontinence",
    "CONT_03": "UTI Recurrent",
    "DM_01": "Diabetes Type 1",
    "DM_02": "Diabetes Type 2",
    "DM_03": "Diabetic Complications",
    "FALL_01": "Fall Risk - High",
    "FALL_02": "Fracture History",
    "FUNC_01": "Functional Decline",
    "INF_01": "Infection Current",
    "MED_01": "Polypharmacy",
    "MED_02": "High-Risk Medications",
    "MH_01": "Depression",
    "MH_02": "Anxiety",
    "MH_03": "Behavioral Symptoms",
    "NEURO_01": "Dementia",
    "NEURO_02": "Stroke/CVA",
    "NEURO_03": "Parkinsons Disease",
    "NEURO_04": "Epilepsy/Seizures",
    "NUTR_01": "Malnutrition Risk",
    "NUTR_02": "Weight Loss >5%",
    "NUTR_03": "Dysphagia",
    "PAIN_01": "Chronic Pain",
    "PAIN_02": "Pain Assessment High",
    "RESP_01": "COPD/Emphysema",
    "RESP_02": "Asthma",
    "RESP_03": "Respiratory Infection",
    "SKIN_01": "Pressure Injury",
    "SKIN_02": "Skin Tear",
    "SKIN_03": "Chronic Wound",
}

def get_all_resident_data(resident_id):
    """Get ALL data for a resident without truncation."""
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT PROGRESS_NOTE, NOTE_TYPE, EVENT_DATE 
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_NOTES 
        WHERE RESIDENT_ID = {resident_id}
    """)
    notes = cursor.fetchall()
    
    cursor.execute(f"""
        SELECT MED_NAME, MED_STATUS, ROUTE
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_MEDICATION 
        WHERE RESIDENT_ID = {resident_id}
    """)
    meds = cursor.fetchall()
    
    cursor.execute(f"""
        SELECT CHART_NAME, OBSERVATION_VALUE
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_OBSERVATIONS 
        WHERE RESIDENT_ID = {resident_id}
    """)
    obs = cursor.fetchall()
    
    cursor.execute(f"""
        SELECT FORM_NAME, ELEMENT_NAME, RESPONSE
        FROM AGEDCARE.AGEDCARE.ACTIVE_RESIDENT_ASSESSMENT_FORMS 
        WHERE RESIDENT_ID = {resident_id}
    """)
    forms = cursor.fetchall()
    
    return notes, meds, obs, forms

def run_regex_detection(text):
    """Run keyword/regex matching for each indicator."""
    text_lower = text.lower()
    detected = {}
    
    for ind_id, keywords in KEYWORDS_BY_INDICATOR.items():
        matches = []
        for kw in keywords:
            if kw in text_lower:
                idx = text_lower.find(kw)
                context = text[max(0,idx-50):min(len(text),idx+len(kw)+50)]
                matches.append((kw, context))
        
        if matches:
            detected[ind_id] = {
                "name": INDICATOR_NAMES[ind_id],
                "keywords_matched": [m[0] for m in matches],
                "sample_context": matches[0][1]
            }
    
    return detected

def main():
    print("=" * 80)
    print("REGEX VERIFICATION SCRIPT - Resident 871")
    print("=" * 80)
    
    print("\n[1] Fetching ALL resident data (no limits)...")
    notes, meds, obs, forms = get_all_resident_data(871)
    
    print(f"   - Notes: {len(notes)} records")
    print(f"   - Medications: {len(meds)} records")  
    print(f"   - Observations: {len(obs)} records")
    print(f"   - Assessment Forms: {len(forms)} records")
    
    full_text = ""
    full_text += " ".join([str(n[0] or "") for n in notes])
    full_text += " " + " ".join([f"{m[0]} {m[1]}" for m in meds])
    full_text += " " + " ".join([f"{o[0]} {o[1]}" for o in obs])
    full_text += " " + " ".join([f"{f[0]} {f[1]} {f[2]}" for f in forms])
    
    print(f"\n[2] Total text length: {len(full_text)} characters")
    
    print("\n[3] Running keyword/regex detection...")
    detected = run_regex_detection(full_text)
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {len(detected)} indicators detected by regex")
    print("=" * 80)
    
    for ind_id in sorted(detected.keys()):
        info = detected[ind_id]
        print(f"\n[{ind_id}] {info['name']}")
        print(f"   Keywords matched: {', '.join(info['keywords_matched'])}")
        print(f"   Sample context: ...{info['sample_context'][:100]}...")
    
    print("\n" + "=" * 80)
    print("INDICATORS NOT DETECTED:")
    print("=" * 80)
    not_detected = set(KEYWORDS_BY_INDICATOR.keys()) - set(detected.keys())
    for ind_id in sorted(not_detected):
        print(f"   [ ] {ind_id} - {INDICATOR_NAMES[ind_id]}")
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: {len(detected)}/33 indicators detected via regex/keywords")
    print("=" * 80)
    
    return detected

if __name__ == "__main__":
    main()
