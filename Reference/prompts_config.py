"""
Configurable prompts for healthcare AI analysis
This allows easy modification of prompts without changing code
"""

# Use Case 1: Differential Diagnosis
DIFFERENTIAL_DIAGNOSIS_PROMPT = """
Analyze these patient notes and provide differential diagnoses:

{patient_notes}

Create a JSON response with the following structure:
{{
    "chief_complaint": "Main presenting complaint",
    "key_findings": [
        {{"finding": "specific finding", "category": "symptom/sign/lab", "severity": "mild/moderate/severe"}}
    ],
    "differential_diagnoses": [
        {{
            "diagnosis": "diagnosis name",
            "confidence": "high/medium/low",
            "evidence": ["supporting finding 1", "supporting finding 2"],
            "icd10_code": "ICD-10 code if known"
        }}
    ],
    "diagnostic_reasoning": "Brief explanation of diagnostic thinking",
    "recommended_tests": ["test1", "test2"]
}}

Focus on the most likely diagnoses based on the clinical presentation.
"""

# Use Case 2: Treatment Analysis
TREATMENT_ANALYSIS_PROMPT = """
Analyze the treatments mentioned in these patient notes:

{patient_notes}

Similar patients were treated with: {similar_treatments}

Create a JSON response with:
{{
    "current_treatments": [
        {{"treatment": "name", "category": "medication/procedure/therapy", "effectiveness": "noted outcome if mentioned"}}
    ],
    "treatment_effectiveness": "Overall assessment of treatment response",
    "evidence_based_recommendations": [
        {{"recommendation": "specific recommendation", "rationale": "clinical reasoning", "evidence_level": "high/moderate/low"}}
    ],
    "contraindications": ["any treatments to avoid based on patient condition"]
}}
"""

# Use Case 3: Clinical Summary (SBAR)
CLINICAL_SUMMARY_PROMPT = """
Create a comprehensive clinical summary in SBAR format from these notes:

{patient_notes}

Format as JSON:
{{
    "situation": "Current clinical situation and reason for encounter",
    "background": "Relevant medical history, medications, allergies",
    "assessment": "Clinical assessment including vital signs and key findings",
    "recommendation": "Treatment plan and follow-up recommendations",
    "clinical_summary": "One paragraph narrative summary",
    "chief_complaint": "Primary reason for visit"
}}
"""

# Use Case 4: Pattern Recognition & Rare Disease
PATTERN_RECOGNITION_PROMPT = """
Analyze this patient presentation for unusual patterns or rare disease indicators:

{patient_notes}

Create a JSON response:
{{
    "presentation_type": "typical/atypical/rare",
    "symptom_pattern": "Description of the symptom constellation",
    "rare_disease_indicators": [
        {{"indicator": "specific finding", "associated_conditions": ["condition1", "condition2"], "significance": "explanation"}}
    ],
    "anomaly_score": 0.0,  // 0-1 scale, higher = more unusual
    "similar_rare_conditions": ["condition name with brief description"],
    "recommended_specialist": "Suggested specialist consultation if needed"
}}

Consider genetic conditions, metabolic disorders, and rare syndromes.
"""

# Use Case 5: Cost Analysis
COST_ANALYSIS_PROMPT = """
Extract procedures, tests, and high-cost indicators from these clinical notes:

{patient_notes}

Create a JSON response:
{{
    "extracted_procedures": [
        {{"procedure": "procedure name", "category": "imaging/lab/surgery/other", "potential_cpt": "CPT code if identifiable"}}
    ],
    "high_cost_indicators": [
        {{"indicator": "ICU admission/complex surgery/etc", "impact": "high/medium", "details": "specific details"}}
    ],
    "resource_utilization": {{
        "imaging_studies": ["list of imaging"],
        "laboratory_tests": ["list of labs"],
        "specialist_consults": ["specialties involved"],
        "length_of_stay_indicators": "inpatient/outpatient/prolonged"
    }},
    "complications": ["any complications that would increase cost"],
    "cost_drivers": "Narrative explanation of main cost drivers"
}}
"""

# Use Case 6: Medication Safety
MEDICATION_SAFETY_PROMPT = """
Extract all medications and analyze for safety concerns:

{patient_notes}

Create a JSON response:
{{
    "extracted_medications": [
        {{
            "name": "medication name",
            "dosage": "dose if mentioned",
            "frequency": "frequency if mentioned",
            "route": "oral/IV/etc if mentioned",
            "indication": "reason for medication if clear"
        }}
    ],
    "polypharmacy_count": 0,  // total number of medications
    "potential_interactions": [
        {{"drug1": "name", "drug2": "name", "severity": "major/moderate/minor", "effect": "description"}}
    ],
    "contraindications": [
        {{"medication": "name", "condition": "patient condition", "risk": "description of risk"}}
    ],
    "high_risk_medications": ["medications requiring special monitoring"],
    "recommendations": ["safety recommendations"]
}}

Consider drug-drug interactions, drug-disease interactions, and age-related concerns.
"""

# Use Case 7: Quality Metrics
QUALITY_METRICS_PROMPT = """
Assess quality of care indicators and guideline adherence:

{patient_notes}

Create a JSON response:
{{
    "quality_indicators": [
        {{"indicator": "specific quality measure", "met": true/false, "details": "explanation"}}
    ],
    "guideline_adherence": [
        {{"guideline": "relevant clinical guideline", "adherent": true/false, "gaps": ["any gaps identified"]}}
    ],
    "preventive_care": [
        {{"measure": "screening/vaccination/etc", "status": "completed/due/overdue"}}
    ],
    "safety_events": ["any safety issues or near misses"],
    "care_coordination": "Assessment of care coordination quality",
    "improvement_opportunities": ["specific improvement suggestions"]
}}
"""

# Use Case 8: Educational Value
EDUCATIONAL_VALUE_PROMPT = """
Extract educational value from this clinical case:

{patient_notes}

Create a JSON response:
{{
    "teaching_points": [
        {{"concept": "key clinical concept", "explanation": "why it's important", "pearls": "clinical pearl"}}
    ],
    "clinical_pearls": "Key takeaway message for learners",
    "quiz_questions": [
        {{
            "question": "Clinical question based on the case",
            "options": ["A) option 1", "B) option 2", "C) option 3", "D) option 4"],
            "correct_answer": "Letter of correct option",
            "explanation": "Why this answer is correct"
        }}
    ],
    "differential_teaching": "How to approach the differential diagnosis",
    "evidence_discussion": "Key evidence-based medicine points",
    "complexity_level": "medical student/resident/fellow"
}}
"""

# Model selection for each use case
MODEL_SELECTION = {
    "differential_diagnosis": "claude-4-sonnet",
    "treatment_analysis": "claude-4-sonnet", 
    "clinical_summary": "claude-4-sonnet",
    "pattern_recognition": "claude-4-sonnet",
    "cost_analysis": "claude-4-sonnet",
    "medication_safety": "claude-4-sonnet",
    "quality_metrics": "claude-4-sonnet",
    "educational_value": "claude-4-sonnet"
}

# Batch processing configuration
BATCH_CONFIG = {
    "batch_size": 10,  # Process 10 patients at a time
    "max_retries": 3,
    "retry_delay": 2,  # seconds
    "parallel_requests": 5,  # Number of concurrent AI requests
    "progress_update_frequency": 10  # Update progress every N patients
}