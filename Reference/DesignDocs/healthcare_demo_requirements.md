# Healthcare AI Demo - Multi-Style Technical Requirements & Cursor Rules

## Project Overview  
You are building a healthcare demonstration for Snowflake featuring **three distinct UI styles** of the same application. This shows how medical professionals can leverage AI to analyze patient notes for improved clinical decision-making, population health management, and medical research. This is a DEMO for healthcare customers, showcasing both practical AI applications and different UI approaches.

## Multi-Style Architecture Decision
**THREE-STYLE APPROACH**: Build one shared backend with three complete UI implementations:
1. **Corporate Standard** (Native Streamlit, maximum stability)
2. **Modern Minimalist** (Contemporary design, curated components) 
3. **Data-Dense Powerhouse** (Expert dashboard, high information density)

**SHARED BACKEND**: All styles use identical hybrid architecture combining pre-processed insights (for performance) with real-time AI demonstrations (for impact)

## Cursor Development Rules

### 1. Decision Making
- For complex medical/clinical decisions, ask for clarification
- For technical implementation choices, proceed with best practices
- When medical accuracy matters, err on the side of caution
- Document assumptions about medical workflows

### 2. Development Phases
- **Foundation Phase**: Focus on robust data structures and connections
- **AI Development**: Prioritize prompt accuracy and medical relevance  
- **UI Development**: Emphasize physician-friendly interfaces
- **Testing Phase**: Ensure medical scenarios are realistic and valuable

### 3. Healthcare-Specific Guidelines
- Never generate fake medical advice in demos
- Always include disclaimers about demo vs production use
- Respect medical terminology and clinical workflows
- Focus on augmenting, not replacing, clinical judgment

## Technical Requirements

### Snowflake Environment
- **Database**: HEALTHCARE_DEMO
- **Schema**: MEDICAL_NOTES  
- **Source Data**: PMC_PATIENTS.PMC_PATIENTS.PMC_PATIENTS (167k records)
- **Warehouse**: COMPUTE_WH (or as specified)
- **Stage**: MEDICAL_NOTES_STAGE

### Platform Specifications
- **Primary Deployment**: Streamlit in Snowflake SPCS (all three styles)
- **Secondary**: Local development with parallel apps
- **Python Libraries**: SPCS allows full PyPI access via uv
- **Connection Pattern**: Dual-environment (Reference pattern from superannuation demo)
- **Development Ports**: Corporate (8501), Minimalist (8502), Powerhouse (8503)

### Multi-Style File Structure
```
src/
├── connection_helper.py          # Shared across all apps
├── shared/                       # Shared business logic
│   ├── data_processors.py       
│   ├── ai_helpers.py             
│   └── chart_data.py             
├── streamlit_main.py            # Current/fallback app
├── streamlit_corporate.py       # Corporate Standard style
├── streamlit_minimalist.py      # Modern Minimalist style  
├── streamlit_powerhouse.py      # Data-Dense Powerhouse style
├── pages/                       # Current pages (backup)
├── pages_corporate/            # Corporate Standard pages
├── pages_minimalist/           # Modern Minimalist pages
└── pages_powerhouse/           # Data-Dense Powerhouse pages
```

### AI/ML Integration
- **Primary AI**: Snowflake Cortex 
- **Models to Use**:
  - mistral-large (clinical summaries)
  - mixtral-8x7b (diagnostic analysis) 
  - llama3.1-70b (education content)
- **Fallback**: Pre-computed results for demo reliability

### Data Architecture
- **Input**: PMC patient notes with SIMILAR_PATIENTS and RELEVANT_ARTICLES
- **Processing**: Hybrid batch + real-time
- **Storage**: Enriched analysis tables
- **Output**: Multi-persona Streamlit application

## Use Case Implementation Priority

### Must-Have Use Cases (Days 1-10)
1. **On-Demand Patient Summary** - SBAR format generation
2. **Differential Diagnosis Support** - Leveraging similar patients
3. **Evidence-Based Treatment Analysis** - Treatment comparisons
4. **Rare Disease Pattern Recognition** - Anomaly detection

### Should-Have Use Cases (Days 11-15) 
5. **High-Cost Patient Analysis** - Cost driver identification
6. **Drug Interaction Analysis** - Medication safety

### Nice-to-Have Use Cases (Days 16-20)
7. **Quality of Care Audits** - Guideline adherence
8. **Educational Case Generation** - Quiz creation

## Streamlit Application Requirements

### Page Structure (Priority Order)
1. 🏥 Data Foundation - Overview and stats
2. 🩺 Clinical Decision Support - PRIMARY physician interface
3. 🔬 AI Processing Live Demo - Real-time showcase (like superannuation page 2)
4. 📊 Population Health Analytics - Administrative view
5. 🎓 Medical Education - Teaching tools
6. 💊 Medication Safety - Drug interactions
7. 📈 Quality Metrics - Performance dashboards
8. 🤖 AI Model Performance - Technical details
9. 📋 Demo Guide - Instructions and scripts

### UI/UX Requirements
- **Design**: Clean, medical-grade interface
- **Colors**: Professional healthcare palette (blues, whites, subtle accents)
- **Layout**: Intuitive navigation for non-technical users
- **Responsiveness**: Works on various screen sizes
- **Performance**: Page loads < 2 seconds

### Real-Time Demo Requirements (Page 3)
- Based on Reference/src/pages/2_🤖_AI_Processing_Demo.py
- Allow free text editing of patient notes
- Show processing steps with progress indicators
- Display results progressively
- Complete in ~30 seconds
- Include error handling for failed AI calls

## Development Guidelines

### Code Standards
```python
# Every medical analysis function must include:
# 1. Purpose documentation
# 2. Medical context
# 3. Error handling
# 4. Result validation

def analyze_patient_notes(patient_notes: str) -> dict:
    """
    Analyze patient notes for clinical insights.
    
    Medical Context: Generates differential diagnoses based on 
    presenting symptoms and clinical findings.
    
    Args:
        patient_notes: Unstructured clinical notes
        
    Returns:
        Dictionary containing diagnoses, confidence scores, and evidence
    """
    try:
        # Implementation
        pass
    except Exception as e:
        # Always gracefully handle errors in medical context
        return {"error": str(e), "fallback": get_cached_result()}
```

### Prompt Engineering Standards
- Start with role definition ("You are a board-certified physician...")
- Include clear medical context
- Request structured output
- Specify confidence levels
- Ask for evidence/reasoning

### Error Handling
- Never show raw errors to demo users
- Always have fallback content ready
- Log errors for debugging
- Provide helpful user messages
- Maintain demo flow despite failures

## Demo-Specific Allowances

### Acceptable Shortcuts
- Pre-computed results for complex analyses
- Simplified medical scoring (vs full clinical algorithms)
- Representative patient samples (vs processing all 167k)
- Mock processing delays for realism
- Curated demo scenarios

### Not Acceptable
- Inventing medical facts or studies
- Showing impossible processing speeds
- Making definitive medical diagnoses
- Ignoring medical safety/ethics
- Using non-medical terminology

## Performance Requirements

### Batch Processing
- Process 1000 patients/hour minimum
- Store results in enriched tables
- Track processing status
- Handle failures gracefully

### Real-Time Processing  
- Response within 30 seconds
- Show progress indicators
- Cache results for reuse
- Fallback to pre-computed if needed

### Dashboard Performance
- Initial load < 2 seconds
- Interactions < 500ms response
- Smooth animations/transitions
- Efficient data aggregations

## Demo Success Criteria

### Technical Success
- All pages load without errors
- AI processing completes reliably  
- Data visualizations render properly
- Navigation is intuitive
- Performance meets targets

### Business Value Demonstration
- Clear time savings shown (e.g., 15 min → 2 min for summaries)
- Quality improvements highlighted
- Cost reduction opportunities identified
- Scalability demonstrated
- ROI calculator included

### Medical Relevance
- Scenarios resonate with physicians
- Workflows match clinical reality
- Terminology is accurate
- Value propositions are credible
- Safety is emphasized

## Security & Compliance Notes

### Data Handling
- No real PHI in demos
- Data remains in Snowflake
- Audit trails implemented
- Access controls demonstrated
- HIPAA compliance mentioned (not implemented)

### Demo Disclaimers
- "Demo purposes only"
- "Not for clinical use"
- "Simulated data"
- "Consult medical professionals"
- "Not FDA approved"

## File Organization
```
/healthcare_demo/
├── sql/
│   ├── 01_create_schema.sql
│   ├── 02_create_tables.sql
│   ├── 03_batch_processing.sql
│   └── 04_demo_queries.sql
├── src/
│   ├── streamlit_main.py
│   ├── connection_helper.py
│   ├── ai_processing/
│   │   ├── clinical_summary.py
│   │   ├── diagnosis_engine.py
│   │   └── treatment_analysis.py
│   └── pages/
│       ├── 1_🏥_Data_Foundation.py
│       └── ... (other pages)
├── prompts/
│   ├── clinical_summaries.txt
│   ├── differential_diagnosis.txt
│   └── treatment_analysis.txt
└── docs/
    ├── demo_scripts.md
    ├── medical_glossary.md
    └── roi_calculations.md
```

## Testing Requirements

### Medical Scenario Testing
- Test with known diagnoses
- Verify treatment recommendations
- Check drug interactions
- Validate cost calculations
- Ensure education content accuracy

### Technical Testing
- Load testing with concurrent users
- Failover testing for AI services
- Cross-browser compatibility
- Mobile responsiveness
- Data refresh testing

## Git Commit Standards
```
[component] Clear description

Components: data, ai, ui, demo, docs, test
Examples:
- [ai] Add differential diagnosis prompt optimization
- [ui] Implement physician dashboard layout  
- [data] Create patient analysis enrichment pipeline
- [demo] Add cardiology scenario for live demo
```

## Daily Development Checklist
- [ ] Review medical accuracy of new features
- [ ] Test error handling paths
- [ ] Update documentation
- [ ] Commit with clear messages
- [ ] Verify demo scenarios still work
- [ ] Check performance metrics

## Questions to Ask When Stuck
1. "Would a physician find this valuable?"
2. "Is this medically accurate?"
3. "Does this improve patient care?"
4. "Is the ROI clear?"
5. "Will this work reliably in a demo?"

---

*These requirements guide all development decisions. When in doubt, optimize for demo impact while maintaining medical credibility.*