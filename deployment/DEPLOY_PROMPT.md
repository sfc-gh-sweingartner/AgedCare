# DRI Intelligence - CoCo Deployment Prompt

Use this prompt to instruct Cortex Code (CoCo) to deploy DRI Intelligence to a new environment.

## Prompt

```
Deploy DRI Intelligence to the following Snowflake environment:

Connection: <CONNECTION_NAME>
Database: <DATABASE_NAME>
Schema: <SCHEMA_NAME>
Warehouse: <WAREHOUSE_NAME>
Compute Pool: <COMPUTE_POOL_NAME>
External Access Integration: <INTEGRATION_NAME>

Please:
1. Run deployment/setup_infrastructure.sql to create compute pool and external access
2. Run deployment/setup_database.sql to create all tables and views
3. Upload config CSVs from Confidential/deployment/config_data/ to stage
4. Run deployment/load_config_data.sql to load config data
5. Update dri-intelligence/snowflake.yml with the environment settings
6. Deploy the Streamlit app using: snow streamlit deploy -c <CONNECTION_NAME>
7. Verify the deployment by checking table counts and app status
```

## Example for AU_DEMO29

```
Deploy DRI Intelligence to the following Snowflake environment:

Connection: AU_DEMO29
Database: AGEDCARE_TEST
Schema: DRI
Warehouse: COMPUTE_WH
Compute Pool: DRI_COMPUTE_POOL
External Access Integration: ALLOW_ALL_ACCESS_INTEGRATION

Please execute all deployment steps and verify the app is working.
```

## Cleanup Prompt

```
Clean up DRI Intelligence deployment:

Connection: <CONNECTION_NAME>
Database: <DATABASE_NAME>

Please:
1. Drop the Streamlit app: DROP STREAMLIT <DATABASE>.<SCHEMA>.DRI_INTELLIGENCE;
2. Drop the database: DROP DATABASE <DATABASE_NAME>;
3. Optionally drop compute pool: DROP COMPUTE POOL <COMPUTE_POOL_NAME>;
```

## Notes

- The deployment uses SPCS container runtime (SYSTEM$ST_CONTAINER_RUNTIME_PY3_11)
- Streamlit apps with container runtime MUST use `snow streamlit deploy`, not SQL CREATE STREAMLIT
- Config data CSVs are in Confidential/deployment/config_data/ (not committed to public repo)
- The app uses get_active_session() which automatically inherits database/schema context
