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

1. **TruSession**: Creates connection to Snowflake AI Observability via SnowflakeConnector
2. **TruApp**: Registers the DRIAnalyzer application with proper instrumentation
3. **RunConfig**: Specifies dataset mapping (RECORD_ROOT.INPUT, INPUT_ID)
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

```bash
cd dri-intelligence/evaluation_job

# Login to Snowflake registry
snow spcs image-registry login --connection DEMO_SWEINGARTNER

# Build for linux/amd64 (required for SPCS)
docker build --platform linux/amd64 -t dri-evaluation:latest .

# Get registry URL
snow sql -q "SHOW IMAGE REPOSITORIES IN SCHEMA AGEDCARE.AGEDCARE" -c DEMO_SWEINGARTNER

# Tag and push (replace <registry> with your account's registry URL)
docker tag dri-evaluation:latest <registry>/AGEDCARE/AGEDCARE/DRI_IMAGES/dri-evaluation:latest
docker push <registry>/AGEDCARE/AGEDCARE/DRI_IMAGES/dri-evaluation:latest
```

### 3. Upload Job Spec to Stage

```bash
snow stage copy job-run-spec.yaml @AGEDCARE.AGEDCARE.DRI_EVAL_STAGE -c DEMO_SWEINGARTNER
```

## Usage

### From Streamlit App

The Quality Metrics page has a "Run Quality Evaluation" button that triggers this job.

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

The job accepts these arguments:
- `--run-name`: Name for this evaluation run (auto-generated if not provided)
- `--prompt-version`: Prompt version to evaluate (default: v1.0)
- `--model`: LLM model to use (default: claude-sonnet-4-5)
- `--sample-size`: Number of residents to evaluate (default: 10)
- `--app-name`: Application name in AI Observability (default: DRI_INTELLIGENCE_AGENT)

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

Navigate to **Quality Metrics** page to see:
- Latest evaluation status
- False positive rate trend
- Evaluation history with per-resident details

### Via SQL

```sql
-- View AI Observability data (requires AI_OBSERVABILITY_EVENTS_LOOKUP role)
-- This is the native AI Observability event table
SELECT * FROM SNOWFLAKE.LOCAL.AI_OBSERVABILITY_EVENTS
WHERE app_name = 'DRI_INTELLIGENCE_AGENT'
ORDER BY timestamp DESC
LIMIT 100;

-- View custom evaluation summary (always accessible)
SELECT * FROM AGEDCARE.AGEDCARE.DRI_EVALUATION_METRICS
ORDER BY CREATED_TIMESTAMP DESC LIMIT 10;
```

## Troubleshooting

### Check Job Logs

```sql
SELECT SYSTEM$GET_SERVICE_LOGS('AGEDCARE.AGEDCARE.DRI_EVAL_RUN', 0, 'dri-evaluation');
```

### Check Job Status

```sql
SELECT SYSTEM$GET_SERVICE_STATUS('AGEDCARE.AGEDCARE.DRI_EVAL_RUN');
```

### Common Issues

| Issue | Solution |
|-------|----------|
| "EXTERNAL AGENT privilege required" | Run `setup_evaluation_job.sql` to grant privileges |
| "Application role not granted" | Grant `AI_OBSERVABILITY_EVENTS_LOOKUP` to your role |
| Evaluations don't appear in Snowsight | Check that TruApp registration succeeded in logs |
| Image not found | Verify docker push completed, check image path in spec |
| Auth errors | Re-run `snow spcs image-registry login` |
| Out of memory | Increase `resources.limits.memory` in job spec |
| Timeout | Reduce `--sample-size` or increase job timeout |

### Verify Privileges

```sql
-- Check you have the required roles
SHOW GRANTS TO USER CURRENT_USER();

-- Should see:
-- - SNOWFLAKE.CORTEX_USER database role
-- - SNOWFLAKE.AI_OBSERVABILITY_EVENTS_LOOKUP application role
-- - CREATE EXTERNAL AGENT on AGEDCARE.AGEDCARE schema
```

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Container image definition |
| `requirements.txt` | Python dependencies (includes TruLens) |
| `evaluate_dri.py` | Main evaluation script with TruApp pattern |
| `entrypoint.sh` | Container entry point |
| `job-spec.yaml` | SPCS job specification (persistent service) |
| `job-run-spec.yaml` | SPCS job specification (on-demand execution) |
| `setup_evaluation_job.sql` | SQL setup script with AI Observability privileges |

## Why a Separate Container?

The TruLens packages (`trulens-core`, `trulens-connectors-snowflake`, `trulens-apps-custom`) have heavy dependencies (~500MB total). These exceed the package resolution timeout in the standard Streamlit container runtime.

Benefits of dedicated SPCS Job container:
- ✅ Full PyPI access (any package)
- ✅ Longer timeouts for ML workloads
- ✅ Results integrate with Snowsight AI Observability UI
- ✅ Can be scheduled via Snowflake Tasks
- ✅ Reusable by other Streamlit apps in your account
- ✅ Callable from any app via `EXECUTE JOB SERVICE`
