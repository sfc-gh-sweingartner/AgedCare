# DRI Evaluation Job - Snowflake AI Observability Integration

SPCS Job container for running TruLens-based AI Observability evaluations of the DRI Intelligence system.

## Key Integration Points

This job properly integrates with **Snowflake AI Observability** so results appear in:
- **Snowsight > AI & ML > Evaluations**
- Application: `DRI_INTELLIGENCE_AGENT`
- Runs appear with metrics: groundedness, context_relevance, answer_relevance, coherence

## Architecture

```
┌─────────────────────┐     EXECUTE JOB SERVICE      ┌──────────────────────────────┐
│  Streamlit App      │ ─────────────────────────▶   │  This SPCS Job               │
│  (Quality Metrics)  │                              │  (TruLens + TruApp Pattern)  │
└─────────────────────┘                              └──────────────────────────────┘
         │                                                      │
         │  SELECT FROM                                         │ TruApp registers to
         ▼                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    Snowflake AI Observability                                       │
│                    (SNOWFLAKE.LOCAL.AI_OBSERVABILITY_EVENTS)                        │
│                    + Custom Tables (DRI_EVALUATION_METRICS/DETAIL)                  │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
                              ┌─────────────────────┐
                              │   Snowsight UI      │
                              │   AI & ML >         │
                              │   Evaluations       │
                              └─────────────────────┘
```

## How It Works

The evaluation follows the official Snowflake AI Observability pattern:

1. **SnowflakeConnector**: Creates connection to Snowflake AI Observability
2. **TruApp**: Registers the DRIAnalyzer application with proper instrumentation
3. **RunConfig**: Specifies dataset mapping (`input` key maps to `input_query` column)
4. **run.start()**: Executes analysis for each resident, capturing traces
5. **run.compute_metrics()**: Triggers LLM-as-judge evaluation for:
   - Groundedness (is the response supported by context?)
   - Context Relevance (is the retrieved data relevant?)
   - Answer Relevance (does the response address the query?)
   - Coherence (is the response logically consistent?)

## Deployment

### 1. Run Setup Script

```bash
snow sql -f setup_evaluation_job.sql -c DEMO_SWEINGARTNER
```

This grants the required AI Observability privileges:
- `SNOWFLAKE.CORTEX_USER` database role
- `SNOWFLAKE.AI_OBSERVABILITY_EVENTS_LOOKUP` application role
- `CREATE EXTERNAL AGENT` on schema
- `CREATE TASK` and `EXECUTE TASK` privileges

### 2. Build and Push Docker Image

**CRITICAL: Build for linux/amd64 architecture (required for SPCS)**

```bash
cd dri-intelligence/evaluation_job

# Login to Snowflake registry using snow CLI
snow spcs image-registry login --connection DEMO_SWEINGARTNER

# Build for linux/amd64 (REQUIRED - SPCS only supports amd64)
docker buildx build --platform linux/amd64 -t dri-evaluation:latest --load .

# Get registry URL
snow spcs image-registry url --connection DEMO_SWEINGARTNER
# Example output: sfseapac-demo-sweingartner.registry.snowflakecomputing.com

# Tag for your registry (replace <registry> with your URL)
docker tag dri-evaluation:latest <registry>/agedcare/agedcare/dri_images/dri-evaluation:latest

# Push (this will take 30-60 minutes for the ~1.5GB image)
docker push <registry>/agedcare/agedcare/dri_images/dri-evaluation:latest
```

**Common Issues:**
- If push hangs, ensure Docker Desktop is running and logged in
- If you see "SPCS only supports image for amd64 architecture", rebuild with `--platform linux/amd64`
- The large layer (~1.5GB) contains TruLens dependencies and takes time to push

### 3. Upload Job Spec to Stage

```bash
snow stage copy job-run-spec.yaml @AGEDCARE.AGEDCARE.DRI_EVAL_STAGE -c DEMO_SWEINGARTNER
```

## Usage

### From Streamlit App

The Batch Testing page has a "Run Quality Evaluation" button that triggers this job.

### From SQL

```sql
-- Drop any existing job run first
DROP SERVICE IF EXISTS AGEDCARE.AGEDCARE.DRI_EVAL_RUN;

-- Execute the evaluation job
EXECUTE JOB SERVICE
IN COMPUTE POOL FULLSTACK_COMPUTE_POOL
FROM @AGEDCARE.AGEDCARE.DRI_EVAL_STAGE
SPEC = 'job-run-spec.yaml'
NAME = AGEDCARE.AGEDCARE.DRI_EVAL_RUN
QUERY_WAREHOUSE = COMPUTE_WH;
```

### With Custom Parameters

The job accepts these environment variables (set in job-run-spec.yaml):
- `RUN_NAME`: Name for this evaluation run (auto-generated if not provided)
- `PROMPT_VERSION`: Prompt version to evaluate (default: v1.0)
- `MODEL`: LLM model to use (default: claude-sonnet-4-5)
- `SAMPLE_SIZE`: Number of residents to evaluate (default: 5)
- `TRULENS_OTEL_TRACING`: Set to "1" to enable tracing (required)

### Scheduled Evaluation (via Task)

```sql
CREATE OR REPLACE TASK DRI_WEEKLY_EVALUATION
    WAREHOUSE = COMPUTE_WH
    SCHEDULE = 'USING CRON 0 6 * * MON UTC'  -- Every Monday at 6am UTC
AS
CALL SYSTEM$EXECUTE_JOB_SERVICE(
    'FULLSTACK_COMPUTE_POOL',
    '@AGEDCARE.AGEDCARE.DRI_EVAL_STAGE',
    'job-run-spec.yaml',
    'AGEDCARE.AGEDCARE.DRI_WEEKLY_EVAL',
    'COMPUTE_WH'
);

ALTER TASK DRI_WEEKLY_EVALUATION RESUME;
```

## Viewing Results

### In Snowsight (Primary)

Navigate to **AI & ML > Evaluations** to see:
- Application: `DRI_INTELLIGENCE_AGENT`
- All evaluation runs with aggregated metrics
- Detailed traces with inputs/outputs for each resident
- LLM judge explanations for scores
- Side-by-side comparison of runs
- Cost and latency breakdowns

### In Streamlit App (Secondary)

Navigate to **Batch Testing** page to see:
- Latest evaluation status
- Job execution logs
- Run history

### Via SQL

```sql
-- View AI Observability SPAN data (TruLens traces)
SELECT 
    TIMESTAMP,
    RECORD_TYPE,
    RECORD_ATTRIBUTES:"snow.ai.observability.object.name"::VARCHAR as OBJECT_NAME,
    RECORD_ATTRIBUTES:"ai.observability.span_type"::VARCHAR as SPAN_TYPE
FROM SNOWFLAKE.LOCAL.AI_OBSERVABILITY_EVENTS 
WHERE RECORD_TYPE = 'SPAN'
ORDER BY TIMESTAMP DESC
LIMIT 100;

-- View custom evaluation summary (always accessible)
SELECT * FROM AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS
ORDER BY CREATED_TIMESTAMP DESC LIMIT 10;
```

## Troubleshooting

### Check Job Logs

```sql
SELECT SYSTEM$GET_SERVICE_LOGS('AGEDCARE.AGEDCARE.DRI_EVAL_RUN', 0, 'dri-evaluation', 500);
```

### Check Job Status

```sql
SELECT SYSTEM$GET_SERVICE_STATUS('AGEDCARE.AGEDCARE.DRI_EVAL_RUN');
```

### Common Issues

| Issue | Solution |
|-------|----------|
| "SPCS only supports image for amd64 architecture" | Rebuild with `docker buildx build --platform linux/amd64` |
| "EXTERNAL AGENT privilege required" | Run `setup_evaluation_job.sql` to grant privileges |
| "Application role not granted" | Grant `AI_OBSERVABILITY_EVENTS_LOOKUP` to your role |
| Evaluations don't appear in Snowsight | Check SPAN records in `SNOWFLAKE.LOCAL.AI_OBSERVABILITY_EVENTS` |
| Image not found | Verify docker push completed, check image path in spec |
| Auth errors | Re-run `snow spcs image-registry login --connection <your_connection>` |
| Out of memory | Increase `resources.limits.memory` in job spec |
| Timeout | Reduce `SAMPLE_SIZE` or increase job timeout |
| "str object has no attribute 'get'" | Known evaluator warning - traces still recorded |

### Verify Privileges

```sql
-- Check you have the required roles
SHOW GRANTS TO USER CURRENT_USER();

-- Should see:
-- - SNOWFLAKE.CORTEX_USER database role
-- - SNOWFLAKE.AI_OBSERVABILITY_EVENTS_LOOKUP application role
-- - CREATE EXTERNAL AGENT on AGEDCARE.AGEDCARE schema
```

### Verify Image Architecture

```bash
# Check the image is built for amd64
docker inspect dri-evaluation:latest | grep Architecture
# Should show: "Architecture": "amd64"
```

## TruLens Integration Details

### Required Packages

The requirements.txt includes separate TruLens packages per official Snowflake quickstart:

```
trulens-core>=2.1.2
trulens-connectors-snowflake>=2.1.2
trulens-providers-cortex>=2.1.2
```

### Key Implementation Patterns

1. **TruApp Creation** - Use positional argument, not `test_app=`:
```python
tru_app = TruApp(
    analyzer,  # positional, NOT test_app=analyzer
    app_name=app_name,
    app_version=app_version,
    connector=connector
)
```

2. **Dataset Spec Mapping** - Use lowercase keys:
```python
run_config = RunConfig(
    dataset_spec={
        "input": "input_query",  # NOT "RECORD_ROOT.INPUT"
    },
    ...
)
```

3. **Run Type Annotation**:
```python
run: Run = tru_app.add_run(run_config=run_config)
```

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Container image definition |
| `requirements.txt` | Python dependencies (includes TruLens packages) |
| `evaluate_dri.py` | Main evaluation script with TruApp pattern |
| `entrypoint.sh` | Container entry point |
| `job-spec.yaml` | SPCS job specification (persistent service) |
| `job-run-spec.yaml` | SPCS job specification (on-demand execution) |
| `setup_evaluation_job.sql` | SQL setup script with AI Observability privileges |

## Why a Separate Container?

The TruLens packages (`trulens-core`, `trulens-connectors-snowflake`, `trulens-providers-cortex`) have heavy dependencies (~1.5GB total). These exceed the package resolution timeout in the standard Streamlit container runtime.

Benefits of dedicated SPCS Job container:
- Full PyPI access (any package)
- Longer timeouts for ML workloads
- Results integrate with Snowsight AI Observability UI
- Can be scheduled via Snowflake Tasks
- Reusable by other Streamlit apps in your account
- Callable from any app via `EXECUTE JOB SERVICE`

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-05 | Initial implementation |
| 1.1 | 2026-02-06 | Fixed TruApp pattern, dataset_spec mapping, amd64 build |
