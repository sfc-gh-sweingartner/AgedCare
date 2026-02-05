# DRI Intelligence

AI-powered clinical analysis for aged care facilities.

## Deployment

This app uses SPCS Container Runtime with `pyproject.toml` + `uv.lock` for dependency management.

### Prerequisites
- Snowflake CLI (`snow`) installed
- A Snowflake connection configured
- SPCS compute pool available

### Deploy
```bash
cd dri-intelligence
snow streamlit deploy -c <connection_name>
```

### Required Snowflake Objects
- Compute Pool: `STREAMLIT_COMPUTE_POOL`
- External Access Integration: `PYPI_ACCESS_INTEGRATION`
- Warehouse: `COMPUTE_WH`

## Evaluation Job (AI Observability)

Quality evaluations run in a separate SPCS container. See `evaluation_job/` for Docker setup and job specs.
