# DRI Intelligence

AI-powered clinical analysis for aged care facilities using Snowflake Cortex and AI Observability.

## Overview

DRI Intelligence uses LLM-based analysis to identify Deteriorating Resident Indicators (DRI) from clinical data. The system includes:

- **Streamlit Application**: Interactive UI for prompt engineering, review workflows, and configuration
- **Evaluation Job**: SPCS container for AI Observability integration with TruLens

## Quick Start

### Prerequisites
- Snowflake CLI (`snow`) installed and configured
- Docker Desktop (for building evaluation job container)
- A Snowflake connection with appropriate privileges

### Deploy Streamlit App
```bash
cd dri-intelligence
snow streamlit deploy -c <connection_name>
```

### Required Snowflake Objects
- Compute Pool: `STREAMLIT_COMPUTE_POOL` or `FULLSTACK_COMPUTE_POOL`
- External Access Integration: `PYPI_ACCESS_INTEGRATION`
- Warehouse: `COMPUTE_WH`

## Evaluation Job (AI Observability)

Quality evaluations run in a separate SPCS container that integrates with Snowflake AI Observability. Results appear in **Snowsight > AI & ML > Evaluations**.

### Deploy Evaluation Job

```bash
cd dri-intelligence/evaluation_job

# 1. Login to Snowflake image registry
snow spcs image-registry login --connection DEMO_SWEINGARTNER

# 2. Build Docker image for amd64 (REQUIRED for SPCS)
docker buildx build --platform linux/amd64 -t dri-evaluation:latest --load .

# 3. Tag for your registry
# Get your registry URL:
snow spcs image-registry url --connection DEMO_SWEINGARTNER
# Tag the image:
docker tag dri-evaluation:latest <registry>/agedcare/agedcare/dri_images/dri-evaluation:latest

# 4. Push to registry (takes 30-60 minutes for ~1.5GB image)
docker push <registry>/agedcare/agedcare/dri_images/dri-evaluation:latest

# 5. Upload job spec to stage
snow stage copy job-run-spec.yaml @AGEDCARE.AGEDCARE.DRI_EVAL_STAGE -c DEMO_SWEINGARTNER
```

### Run Evaluation

```sql
EXECUTE JOB SERVICE
IN COMPUTE POOL FULLSTACK_COMPUTE_POOL
FROM @AGEDCARE.AGEDCARE.DRI_EVAL_STAGE
SPEC = 'job-run-spec.yaml'
NAME = AGEDCARE.AGEDCARE.DRI_EVAL_RUN
QUERY_WAREHOUSE = COMPUTE_WH;
```

### View Results

1. **Snowsight**: Navigate to **AI & ML > Evaluations > DRI_INTELLIGENCE_AGENT**
2. **SQL**: Query `SNOWFLAKE.LOCAL.AI_OBSERVABILITY_EVENTS` for SPAN records

See `evaluation_job/README.md` for detailed deployment and troubleshooting instructions.

## Project Structure

```
dri-intelligence/
├── streamlit_app.py           # Main Streamlit entry point
├── pyproject.toml             # Dependencies for Streamlit app
├── pages/                     # Streamlit pages
│   ├── 1_📊_Dashboard.py      # Overview metrics
│   ├── 2_🔬_Prompt_Engineering.py  # Test/tune prompts
│   ├── 3_📋_Review_Queue.py   # Approval workflow
│   ├── 4_📈_Analysis_Results.py    # View LLM output
│   ├── 5_⚙️_Configuration.py  # Client settings
│   ├── 6_🔄_Claude_vs_Regex_Comparison.py  # Demo only
│   └── 7_🧪_Batch_Testing.py  # Run evaluations
├── src/
│   ├── connection_helper.py   # Snowflake session management
│   └── dri_analysis.py        # LLM analysis functions
└── evaluation_job/            # SPCS evaluation container
    ├── Dockerfile             # Container definition
    ├── requirements.txt       # TruLens dependencies
    ├── evaluate_dri.py        # TruLens evaluation script
    ├── job-run-spec.yaml      # SPCS job specification
    └── README.md              # Deployment instructions
```

## Key Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| LLM Analysis | Snowflake Cortex Complete | Claude 4.5 for clinical analysis |
| RAG | Cortex Search | Indicator definition lookup |
| AI Observability | TruLens SDK | Evaluation metrics & traces |
| App Hosting | SPCS | Streamlit and evaluation jobs |

## Documentation

- `DesignDocs/01_Functional_Design.md` - Business requirements
- `DesignDocs/02_Technical_Design.md` - Technical architecture
- `evaluation_job/README.md` - Evaluation deployment guide

## Troubleshooting

### Docker Build Issues
- Always use `--platform linux/amd64` for SPCS compatibility
- Use `docker buildx build` instead of `docker build`

### Registry Login
```bash
# Use snow CLI for authentication
snow spcs image-registry login --connection <connection_name>
```

### Image Push Slow
The TruLens layer is ~1.5GB. Push can take 30-60 minutes on typical connections.

### Evaluations Not Appearing
1. Check job completed: `SELECT SYSTEM$GET_SERVICE_STATUS('...')`
2. Check logs: `SELECT SYSTEM$GET_SERVICE_LOGS('...', 0, 'dri-evaluation', 500)`
3. Verify SPAN records exist in `SNOWFLAKE.LOCAL.AI_OBSERVABILITY_EVENTS`

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-03 | Initial release |
| 1.1 | 2026-02-06 | Fixed AI Observability integration, TruLens patterns |
