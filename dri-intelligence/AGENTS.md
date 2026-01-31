# DRI Intelligence - Agent Instructions

## Auto-Deploy to SPCS

After any code changes to the Streamlit app, automatically deploy to SPCS:

```bash
cd /Users/sweingartner/CoCo/AgedCare/dri-intelligence
/opt/anaconda3/bin/snow streamlit deploy --replace -c DEMO_SWEINGARTNER
```

**Important:** Use `/opt/anaconda3/bin/snow` (v3.14.0), not the default `snow` (v3.2.0).

## App Details

- **App Name:** AGED_CARE_DRI
- **Location:** AGEDCARE.AGEDCARE
- **URL:** https://app.snowflake.com/SFSEAPAC/demo_sweingartner/#/streamlit-apps/AGEDCARE.AGEDCARE.AGED_CARE_DRI
- **Compute Pool:** STREAMLIT_COMPUTE_POOL
- **Connection:** DEMO_SWEINGARTNER

## File Structure

All files in `artifacts` section of `snowflake.yml` are uploaded directly to Snowflake stage (not via Git).

When adding new Python files, update `snowflake.yml` artifacts list.
