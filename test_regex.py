import re

context = """antibiotics cellulitis wound BGL insulin Metformin Donepezil Spiriva inhaler Ryzodeg injection blood glucose monitoring incontinence skin tear dressing pain mobility aid behaviour aggression dementia"""

keywords = {
    "DM_02": ["diabetes", "insulin", "metformin", "blood glucose", "bgl", "oral hypoglycemic"],
    "NEURO_01": ["dementia", "donepezil", "alzheimer", "cognitive"],
    "INF_01": ["infection", "antibiotic", "cellulitis", "sepsis"],
    "SKIN_02": ["skin tear", "wound", "dressing", "fragile skin"],
    "MED_02": ["insulin", "warfarin", "opioid", "anticoagulant"],
    "RESP_01": ["copd", "spiriva", "emphysema", "bronchodilator", "inhaler"],
    "MH_03": ["behaviour", "aggression", "bpsd", "antipsychotic"],
    "CONT_01": ["incontinence", "continence", "bladder"],
    "PAIN_01": ["pain", "analgesia"],
    "FALL_01": ["fall", "mobility aid"],
}

text_lower = context.lower()
detected = []

for ind_id, terms in keywords.items():
    for term in terms:
        if term in text_lower:
            detected.append((ind_id, term))
            print(f"FOUND: {ind_id} via '{term}'")
            break

print(f"\nTotal detected: {len(detected)}")
