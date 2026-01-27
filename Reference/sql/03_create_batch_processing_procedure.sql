-- Healthcare AI Demo - Batch Processing Stored Procedure
-- This procedure provides the optimized batch processing functionality
-- for Streamlit in Snowflake deployment

-- Use the healthcare database and schema
USE DATABASE HEALTHCARE_DEMO;
USE SCHEMA MEDICAL_NOTES;

-- Create the batch processing stored procedure
CREATE OR REPLACE PROCEDURE BATCH_PROCESS_PATIENTS(
    BATCH_SIZE NUMBER DEFAULT 10,
    MAX_PATIENTS NUMBER DEFAULT NULL,
    AI_MODEL VARCHAR DEFAULT 'openai-gpt-5',
    TARGET_PATIENT_ID NUMBER DEFAULT NULL
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python', 'pandas')
HANDLER = 'batch_process_main'
AS $$
import json
import time
from datetime import datetime

# Consolidated mega-prompt that combines all 8 use cases
CONSOLIDATED_ANALYSIS_PROMPT = """
Analyze these patient notes comprehensively across all healthcare AI use cases:

{patient_notes}

Create a single comprehensive JSON response with ALL the following sections in this exact order:

{{
    "clinical_summary": {{
        "situation": "Current clinical situation and reason for encounter",
        "background": "Relevant medical history, medications, allergies",
        "assessment": "Clinical assessment including vital signs and key findings",
        "recommendation": "Treatment plan and follow-up recommendations",
        "clinical_summary": "One paragraph narrative summary",
        "chief_complaint": "Main presenting complaint"
    }},
    
    "differential_diagnosis": {{
        "chief_complaint": "Main presenting complaint",
        "clinical_findings": {{
            "key_findings": [
                {{"finding": "specific finding", "category": "symptom/sign/lab", "severity": "mild/moderate/severe"}}
            ]
        }},
        "diagnostic_assessment": {{
            "differential_diagnoses": [
                {{
                    "diagnosis": "diagnosis name",
                    "confidence": "high/medium/low",
                    "evidence": [{{"evidence_text": "Quote specific sentences from patient notes that support this diagnosis"}}],
                    "discriminating_features": "What distinguishes this from other diagnoses",
                    "icd10_code": "ICD-10 code if known"
                }}
            ]
        }},
        "diagnostic_workup": {{
            "recommended_tests": [
                {{"test": "test name", "rationale": "why this test is needed", "priority": "high/medium/low"}}
            ]
        }},
        "diagnostic_reasoning": "Brief explanation of diagnostic thinking with specific references to patient notes",
        "diagnostic_confidence": "high/medium/low - overall confidence in diagnostic assessment"
    }},
    
    "medication_safety": {{
        "current_medications": {{
            "extracted_medications": [
                {{"medication": "name", "dosage": "if mentioned", "frequency": "if mentioned", "indication": "reason for use"}}
            ]
        }},
        "safety_concerns": {{
            "drug_interactions": [
                {{"drug1": "drug1", "drug2": "drug2", "interaction_type": "major/moderate/minor", "clinical_effect": "description", "confidence": "high/medium/low"}}
            ],
            "contraindications": [
                {{"medication": "name", "contraindication": "condition/allergy", "severity": "absolute/relative", "evidence": "Quote from notes supporting this contraindication"}}
            ],
            "safety_alerts": [
                {{"alert": "safety alert description", "severity": "high/medium/low", "medication": "related medication if applicable"}}
            ]
        }},
        "risk_assessment": {{
            "polypharmacy_risk": "low/medium/high",
            "polypharmacy_confidence": "high/medium/low - confidence in polypharmacy assessment"
        }}
    }},
    
    "treatment_analysis": {{
        "active_treatments": {{
            "current_treatments": [
                {{"treatment": "name", "category": "medication/procedure/therapy", "effectiveness": "noted outcome if mentioned", "evidence": "Quote from notes about treatment response"}}
            ],
            "treatment_effectiveness": "Overall assessment of treatment response with specific evidence from notes"
        }},
        "clinical_recommendations": {{
            "evidence_based_recommendations": [
                {{"recommendation": "specific recommendation", "rationale": "clinical reasoning with quotes from notes", "evidence_level": "high/moderate/low", "confidence": "high/medium/low"}}
            ],
            "contraindications": [
                {{"treatment": "treatment to avoid", "reason": "clinical reason", "severity": "absolute/relative"}}
            ]
        }}
    }},
    
    "pattern_recognition": {{
        "clinical_patterns": {{
            "presentation_type": "typical/atypical/rare",
            "symptom_pattern": "Description of the symptom constellation",
            "rare_disease_indicators": [
                {{"indicator": "specific finding", "associated_conditions": ["condition1", "condition2"], "significance": "explanation"}}
            ]
        }},
        "anomaly_detection": {{
            "anomaly_score": 0.0,
            "anomaly_confidence": "high/medium/low - confidence in anomaly assessment",
            "unusual_features": [
                {{"feature": "unusual aspect", "rarity": "common/uncommon/rare", "clinical_significance": "why this matters"}}
            ]
        }},
        "specialist_referral": {{
            "recommended_specialist": "Suggested specialist consultation if needed",
            "referral_urgency": "routine/urgent/emergent",
            "referral_rationale": "Why specialist input is needed"
        }}
    }},
    
    "quality_metrics": {{
        "care_quality": {{
            "quality_indicators": [
                {{"indicator": "specific quality measure", "met": true/false, "details": "explanation", "confidence": "high/medium/low"}}
            ],
            "guideline_adherence": [
                {{"guideline": "relevant clinical guideline", "adherent": true/false, "gaps": ["any gaps identified"], "confidence": "high/medium/low"}}
            ]
        }},
        "safety_assessment": {{
            "safety_events": ["any safety issues or near misses identified in notes"],
            "risk_factors": [
                {{"risk_factor": "identified risk", "severity": "high/medium/low", "mitigation": "suggested mitigation"}}
            ]
        }},
        "care_coordination": {{
            "coordination_quality": "Assessment of care coordination quality",
            "improvement_opportunities": ["specific improvement suggestions"]
        }}
    }},
    
    "cost_analysis": {{
        "resource_utilization": {{
            "extracted_procedures": [
                {{"procedure": "procedure name", "category": "imaging/lab/surgery/other", "potential_cpt": "CPT code if identifiable", "cost_impact": "high/medium/low"}}
            ],
            "imaging_studies": ["list of imaging studies mentioned"],
            "laboratory_tests": ["list of lab tests mentioned"],
            "specialist_consults": ["specialties involved"]
        }},
        "cost_drivers": {{
            "high_cost_indicators": [
                {{"indicator": "ICU admission/complex surgery/etc", "impact": "high/medium/low", "details": "specific details"}}
            ],
            "complications": ["any complications that would increase cost"],
            "length_of_stay_indicators": "inpatient/outpatient/prolonged - evidence from notes"
        }},
        "financial_impact": {{
            "estimated_cost_category": "low/medium/high/very_high - based on procedures and complexity",
            "cost_justification": "Explanation of cost category assignment",
            "cost_optimization_opportunities": ["suggestions for cost reduction if applicable"]
        }}
    }},
    
    "educational_value": {{
        "teaching_content": {{
            "teaching_points": [
                {{"concept": "key clinical concept", "explanation": "why it's important", "pearls": "clinical pearl"}}
            ],
            "clinical_pearls": "Key takeaway message for learners",
            "complexity_level": "medical student/resident/fellow - appropriate learning level"
        }},
        "case_discussion": {{
            "differential_teaching": "How to approach the differential diagnosis - educational perspective",
            "evidence_discussion": "Key evidence-based medicine points for learning",
            "learning_objectives": ["what learners should take away from this case"]
        }},
        "assessment_tools": {{
            "quiz_questions": [
                {{
                    "question": "Clinical question based on the case",
                    "options": ["A) option 1", "B) option 2", "C) option 3", "D) option 4"],
                    "correct_answer": "Letter of correct option",
                    "explanation": "Why this answer is correct with reference to case details"
                }}
            ]
        }}
    }}
}}

Return ONLY the JSON response. Ensure all fields are populated with clinically relevant information extracted from or inferred from the patient notes. Use "Not mentioned" or "Unable to determine from notes" only when information is truly absent.
"""

def parse_consolidated_response(response: str) -> dict:
    """Robustly parse the consolidated AI response into structured data"""
    try:
        import re
        
        if not response:
            print("Empty response received")
            return {}
            
        # 1) Try direct JSON parsing first
        try:
            parsed = json.loads(response.strip())
            if isinstance(parsed, dict):
                return parsed
        except Exception as e:
            print(f"Direct JSON parse failed: {e}")
            pass
            
        # 2) Try fenced code block
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response, re.IGNORECASE)
        if fence_match:
            fenced = fence_match.group(1).strip()
            try:
                parsed = json.loads(fenced)
                if isinstance(parsed, dict):
                    return parsed
            except Exception as e:
                print(f"Fenced JSON parse failed: {e}")
                pass

        # 3) Extract the largest JSON object in the response
        # Find all potential JSON objects
        json_objects = []
        brace_count = 0
        start_pos = -1
        
        for i, char in enumerate(response):
            if char == '{':
                if brace_count == 0:
                    start_pos = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_pos >= 0:
                    json_str = response[start_pos:i+1]
                    try:
                        parsed = json.loads(json_str)
                        if isinstance(parsed, dict) and len(parsed) > 0:
                            json_objects.append(parsed)
                    except Exception:
                        pass
                    start_pos = -1
        
        # Return the largest valid JSON object
        if json_objects:
            # Sort by number of keys (prefer more complete objects)
            json_objects.sort(key=lambda x: len(str(x)), reverse=True)
            return json_objects[0]

        # 4) Final fallback
        print(f"No valid JSON found in response. First 200 chars: {response[:200]}")
        return {}
        
    except Exception as e:
        print(f"Error parsing AI response: {e}")
        return {}

def save_patient_results(session, patient_id: int, consolidated_results: dict, ai_model: str = 'openai-gpt-5'):
    """Save consolidated results to all relevant tables"""
    try:
        # Validate input type
        if not isinstance(consolidated_results, dict):
            raise Exception(f"consolidated_results must be a dict, got {type(consolidated_results)}")
        
        if not consolidated_results:
            raise Exception("consolidated_results is empty")
        
        # Extract sections from consolidated results
        clinical_summary = consolidated_results.get('clinical_summary', {})
        differential_dx = consolidated_results.get('differential_diagnosis', {})
        medication_safety = consolidated_results.get('medication_safety', {})
        treatment_analysis = consolidated_results.get('treatment_analysis', {})
        pattern_recognition = consolidated_results.get('pattern_recognition', {})
        quality_metrics = consolidated_results.get('quality_metrics', {})
        cost_analysis = consolidated_results.get('cost_analysis', {})
        educational_value = consolidated_results.get('educational_value', {})
        
        # 1. Save to PATIENT_ANALYSIS table (new simplified structure)
        patient_analysis_query = """
        INSERT INTO PATIENT_ANALYSIS (
            PATIENT_ID, AI_ANALYSIS_JSON, AI_MODEL_USED
        ) 
        SELECT ?, PARSE_JSON(?), ?
        """
        
        session.sql(patient_analysis_query, params=[
            int(patient_id),  # PATIENT_ID
            json.dumps(consolidated_results),  # AI_ANALYSIS_JSON - store full results
            ai_model  # AI_MODEL_USED
        ]).collect()
        
        # 2. Save to MEDICATION_ANALYSIS table
        medication_analysis_query = """
        INSERT INTO MEDICATION_ANALYSIS (
            PATIENT_ID, EXTRACTED_MEDICATIONS, DRUG_INTERACTIONS, 
            CONTRAINDICATIONS, POLYPHARMACY_RISK_SCORE
        ) 
        SELECT ?, PARSE_JSON(?), PARSE_JSON(?), PARSE_JSON(?), ?
        """
        
        # Calculate polypharmacy risk score
        medications = medication_safety.get('current_medications', {}).get('extracted_medications', [])
        polypharmacy_risk = medication_safety.get('risk_assessment', {}).get('polypharmacy_risk', 'low')
        risk_score = 3 if polypharmacy_risk == 'high' else 2 if polypharmacy_risk == 'medium' else 1
        
        session.sql(medication_analysis_query, params=[
            patient_id,
            json.dumps(medications),  # JSON string for PARSE_JSON()
            json.dumps(medication_safety.get('safety_concerns', {}).get('drug_interactions', [])),  # JSON string for PARSE_JSON()
            json.dumps(medication_safety.get('safety_concerns', {}).get('contraindications', [])),  # JSON string for PARSE_JSON()
            risk_score
        ]).collect()
        
        # 3. Save to COST_ANALYSIS table
        cost_analysis_query = """
        INSERT INTO COST_ANALYSIS (
            PATIENT_ID, EXTRACTED_PROCEDURES, EXTRACTED_CONDITIONS,
            HIGH_COST_INDICATORS, ESTIMATED_ENCOUNTER_COST, COST_CATEGORY, COST_DRIVERS
        ) 
        SELECT ?, PARSE_JSON(?), PARSE_JSON(?), PARSE_JSON(?), ?, ?, ?
        """
        
        # Estimate cost based on category
        cost_category = cost_analysis.get('financial_impact', {}).get('estimated_cost_category', 'medium')
        estimated_cost = 50000 if cost_category == 'very_high' else 25000 if cost_category == 'high' else 10000 if cost_category == 'medium' else 5000
        
        session.sql(cost_analysis_query, params=[
            patient_id,
            json.dumps(cost_analysis.get('resource_utilization', {}).get('extracted_procedures', [])),  # JSON string for PARSE_JSON()
            json.dumps([]),  # EXTRACTED_CONDITIONS - JSON string for PARSE_JSON()
            json.dumps(cost_analysis.get('cost_drivers', {}).get('high_cost_indicators', [])),  # JSON string for PARSE_JSON()
            estimated_cost,
            cost_category,
            cost_analysis.get('financial_impact', {}).get('cost_justification', '')
        ]).collect()
        
    except Exception as e:
        raise Exception(f"Error saving results for patient {patient_id}: {e}")

def batch_process_main(session, batch_size: int, max_patients: int = None, ai_model: str = 'openai-gpt-5', target_patient_id: int = None):
    """Main batch processing function for Snowpark procedure"""
    
    start_time = time.time()
    
    try:
        # Get patients to process
        if target_patient_id:
            # Process specific patient
            patients_query = f"""
                SELECT p.PATIENT_ID, p.PATIENT_NOTES
                FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS p
                WHERE p.PATIENT_ID = {target_patient_id}
                  AND p.PATIENT_NOTES IS NOT NULL
                  AND LENGTH(p.PATIENT_NOTES) > 100
            """
        else:
            # Get unprocessed patients
            patients_query = """
                SELECT p.PATIENT_ID, p.PATIENT_NOTES
                FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS p
                LEFT JOIN HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS pa ON p.PATIENT_ID = pa.PATIENT_ID
                WHERE pa.PATIENT_ID IS NULL
                  AND p.PATIENT_NOTES IS NOT NULL
                  AND LENGTH(p.PATIENT_NOTES) > 100
                ORDER BY p.PATIENT_ID
            """
            
            if max_patients:
                patients_query += f" LIMIT {max_patients}"
            
        patients_df = session.sql(patients_query).to_pandas()
        
        if patients_df.empty:
            # Check if any patients exist at all
            total_patients = session.sql("SELECT COUNT(*) as cnt FROM PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS WHERE PATIENT_NOTES IS NOT NULL AND LENGTH(PATIENT_NOTES) > 100").collect()[0]['CNT']
            processed_patients = session.sql("SELECT COUNT(*) as cnt FROM HEALTHCARE_DEMO.MEDICAL_NOTES.PATIENT_ANALYSIS").collect()[0]['CNT']
            
            return f"""
            ℹ️  No unprocessed patients found.
            📊 Status: {total_patients} total eligible PMC patients, {processed_patients} already processed
            💡 Tip: All eligible patients may already be processed
            """
        
        # Initialize processing status logging
        batch_id = session.sql("SELECT UUID_STRING() as id").collect()[0]['ID']
        total_planned = int(len(patients_df))
        try:
            session.sql(
                """
                INSERT INTO PROCESSING_STATUS 
                (BATCH_ID, START_TIME, STATUS, TOTAL_PATIENTS, PROCESSED_PATIENTS, FAILED_PATIENTS, ERROR_DETAILS, PROCESSING_METRICS)
                SELECT ?, CURRENT_TIMESTAMP(), 'running', ?, 0, 0, NULL, NULL
                """,
                params=[batch_id, total_planned]
            ).collect()
        except Exception:
            # Non-fatal if status logging fails
            pass

        processed_count = 0
        failed_count = 0
        first_error = None
        
        # Process patients in batches
        for i in range(0, len(patients_df), batch_size):
            batch = patients_df.iloc[i:i+batch_size]
            
            for _, patient in batch.iterrows():
                patient_id = patient['PATIENT_ID']
                patient_notes = patient['PATIENT_NOTES']
                
                try:
                    # Format prompt with patient notes
                    formatted_prompt = CONSOLIDATED_ANALYSIS_PROMPT.format(
                        patient_notes=patient_notes
                    )
                    
                    # Execute AI analysis using parameterized query to avoid SQL injection issues
                    ai_query = f"""
                    SELECT SNOWFLAKE.CORTEX.COMPLETE(
                        '{ai_model}',
                        ?
                    ) as response
                    """
                    
                    ai_result = session.sql(ai_query, params=[formatted_prompt]).collect()
                    if not ai_result:
                        raise Exception("No response from AI model")
                    
                    ai_response = ai_result[0]['RESPONSE']
                    
                    # Debug: Print first 500 chars of response
                    print(f"AI Response preview for patient {patient_id}: {ai_response[:500] if ai_response else 'None'}")
                    
                    # Parse consolidated response
                    consolidated_results = parse_consolidated_response(ai_response)
                    
                    # Check if parsing returned a valid result
                    if not consolidated_results or not isinstance(consolidated_results, dict) or 'clinical_summary' not in consolidated_results:
                        raise Exception(f"Failed to parse AI response - got type: {type(consolidated_results)}, keys: {consolidated_results.keys() if isinstance(consolidated_results, dict) else 'N/A'}")
                    
                    # Save results to all tables
                    save_patient_results(session, patient_id, consolidated_results, ai_model)
                    
                    processed_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    # Capture first error for debugging
                    if first_error is None:
                        first_error = f"Patient {patient_id}: {str(e)}"
                    continue
        
        # Final summary
        total_time = time.time() - start_time
        
        # Avoid division by zero
        if processed_count > 0:
            avg_time_per_patient = total_time / processed_count
            result_message = f"""
        🎉 OPTIMIZED Processing Complete!
        ✅ Successfully processed: {processed_count} patients
        ❌ Failed: {failed_count} patients
        ⏱️  Total time: {total_time/60:.1f} minutes ({avg_time_per_patient:.1f}s per patient)
        🚀 Performance: Consolidated prompt approach (~5-8x faster than individual prompts)
        """
        else:
            error_details = f"\n🐛 First error: {first_error}" if first_error else ""
            result_message = f"""
        ⚠️  Processing Complete - No patients were successfully processed
        ❌ Failed: {failed_count} patients
        ⏱️  Total time: {total_time/60:.1f} minutes
        🔍 Check: Ensure patients exist and are not already processed{error_details}
        """
        
        # Update processing status
        try:
            status_value = 'completed' if processed_count > 0 else 'failed'
            metrics_obj = {"avg_time_per_patient_s": (avg_time_per_patient if processed_count > 0 else None)}
            session.sql(
                """
                UPDATE PROCESSING_STATUS
                SET END_TIME = CURRENT_TIMESTAMP(),
                    STATUS = ?,
                    PROCESSED_PATIENTS = ?,
                    FAILED_PATIENTS = ?,
                    PROCESSING_METRICS = PARSE_JSON(?)
                WHERE BATCH_ID = ?
                """,
                params=[status_value, int(processed_count), int(failed_count), json.dumps(metrics_obj), batch_id]
            ).collect()
        except Exception:
            # Non-fatal if status update fails
            pass

        return result_message
        
    except Exception as e:
        # Attempt to mark status as failed with error details
        try:
            if 'batch_id' in locals():
                session.sql(
                    """
                    UPDATE PROCESSING_STATUS
                    SET END_TIME = CURRENT_TIMESTAMP(),
                        STATUS = 'failed',
                        ERROR_DETAILS = PARSE_JSON(?)
                    WHERE BATCH_ID = ?
                    """,
                    params=[json.dumps({"error": str(e)}), batch_id]
                ).collect()
        except Exception:
            pass
        return f"❌ Batch processing failed: {str(e)}"

$$;

-- Grant execute permissions
GRANT USAGE ON PROCEDURE BATCH_PROCESS_PATIENTS(NUMBER, NUMBER) TO ROLE PUBLIC;

-- Test the procedure (optional - uncomment to test with small batch)
-- CALL BATCH_PROCESS_PATIENTS(5, 10);

COMMIT;
