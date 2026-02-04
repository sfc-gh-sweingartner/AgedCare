# DRI Evaluation Job

SPCS Job container for running TruLens-based AI Observability evaluations of the DRI Intelligence system.

## Why a Separate Container?

The TruLens packages (`trulens-core`, `trulens-connectors-snowflake`, `trulens-providers-cortex`) have heavy dependencies including `snowflake-ml-python`, `xgboost`, and `scipy` (~200MB total). These exceed the package resolution timeout in the standard Streamlit container runtime.

By running evaluations in a dedicated SPCS Job container:
- ✅ Full PyPI access (any package)
- ✅ Longer timeouts for ML workloads
- ✅ Results integrate with Snowsight AI Observability UI
- ✅ Can be scheduled via Snowflake Tasks
- ✅ Callable from the Streamlit app via `EXECUTE JOB SERVICE`

## Architecture

```
┌─────────────────────┐     EXECUTE JOB SERVICE      ┌──────────────────────┐
│  Streamlit App      │ ─────────────────────────▶   │  This SPCS Job       │
│  (Quality Metrics)  │                              │  (TruLens + Python)  │
└─────────────────────┘                              └──────────────────────┘
         │                                                      │
         │  SELECT FROM                                         │ Writes to
         ▼                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Snowflake AI Observability Tables                        │
│                    + DRI_EVALUATION_METRICS/DETAIL                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Deployment

### 1. Login to Snowflake Registry

```bash
snow spcs image-registry login --connection DEMO_SWEINGARTNER
```

### 2. Build and Push Docker Image

```bash
cd dri-intelligence/evaluation_job

# Build for linux/amd64 (required for SPCS)
docker build --platform linux/amd64 -t dri-evaluation:latest .

# Get registry URL
snow sql -q "SHOW IMAGE REPOSITORIES IN SCHEMA AGEDCARE.AGEDCARE" -c DEMO_SWEINGARTNER

# Tag and push (replace <registry> with your account's registry URL)
docker tag dri-evaluation:latest <registry>/AGEDCARE/AGEDCARE/DRI_IMAGES/dri-evaluation:latest
docker push <registry>/AGEDCARE/AGEDCARE/DRI_IMAGES/dri-evaluation:latest
```

### 3. Run Setup Script

```bash
snow sql -f setup_evaluation_job.sql -c DEMO_SWEINGARTNER
```

Or in Snowsight, open a worksheet and run `setup_evaluation_job.sql`.

### 4. Verify Deployment

```sql
SHOW SERVICES LIKE 'DRI_EVALUATION%';
SELECT SYSTEM$GET_SERVICE_STATUS('DRI_EVALUATION_JOB');
```

## Usage

### From Streamlit App

The Quality Metrics page in the Streamlit app has a "Run Evaluation" button that triggers this job.

### From SQL

```sql
EXECUTE JOB SERVICE AGEDCARE.AGEDCARE.DRI_EVALUATION_JOB
    WITH PARAMETERS (
        RUN_NAME => 'WeeklyEval_2026-02-04',
        PROMPT_VERSION => 'v1.4',
        MODEL => 'claude-3-5-sonnet',
        SAMPLE_SIZE => 25
    );
```

### Scheduled Evaluation (via Task)

```sql
CREATE OR REPLACE TASK DRI_WEEKLY_EVALUATION
    WAREHOUSE = COMPUTE_WH
    SCHEDULE = 'USING CRON 0 6 * * MON UTC'  -- Every Monday at 6am UTC
AS
    EXECUTE JOB SERVICE AGEDCARE.AGEDCARE.DRI_EVALUATION_JOB
    WITH PARAMETERS (
        RUN_NAME => 'Weekly_' || CURRENT_DATE()::VARCHAR,
        PROMPT_VERSION => 'v1.4',
        MODEL => 'claude-3-5-sonnet',
        SAMPLE_SIZE => 50
    );

ALTER TASK DRI_WEEKLY_EVALUATION RESUME;
```

## Viewing Results

### In Streamlit App

Navigate to **Quality Metrics** page to see:
- Latest evaluation status
- False positive rate trend
- Evaluation history with per-resident details

### In Snowsight

Navigate to **AI & ML → Evaluations** to see:
- Detailed traces with inputs/outputs
- LLM judge explanations for scores
- Side-by-side comparison of runs
- Cost and latency breakdowns

### Via SQL

```sql
-- Latest evaluation summary
SELECT * FROM AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS
ORDER BY CREATED_TIMESTAMP DESC LIMIT 10;

-- Per-resident details for an evaluation
SELECT * FROM AGEDCARE.AGEDCARE.DRI_EVALUATION_DETAIL
WHERE EVALUATION_ID = '<evaluation_id>'
ORDER BY RECORD_INDEX;
```

## Troubleshooting

### Check Job Logs

```sql
SELECT SYSTEM$GET_SERVICE_LOGS('DRI_EVALUATION_JOB', 0, 'dri-evaluation');
```

### Check Job Status

```sql
SELECT SYSTEM$GET_SERVICE_STATUS('DRI_EVALUATION_JOB');
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Image not found | Verify docker push completed, check image path in spec |
| Auth errors | Re-run `snow spcs image-registry login` |
| Out of memory | Increase `resources.limits.memory` in job spec |
| Timeout | Reduce `SAMPLE_SIZE` or increase job timeout |

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Container image definition |
| `requirements.txt` | Python dependencies (includes TruLens) |
| `evaluate_dri.py` | Main evaluation script with TruLens instrumentation |
| `entrypoint.sh` | Container entry point |
| `job-spec.yaml` | SPCS job specification |
| `setup_evaluation_job.sql` | SQL setup script |
