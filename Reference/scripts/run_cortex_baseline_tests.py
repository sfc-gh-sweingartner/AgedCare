import os
import csv
from datetime import datetime
from typing import List, Dict

import pandas as pd

from src.connection_helper import get_snowflake_connection, execute_query


TEST_QUERIES: List[Dict] = [
    {"name": "breast_cancer", "query": "breast cancer"},
    {"name": "her2_positive", "query": "HER2 positive"},
    {"name": "type2_diabetes", "query": "type 2 diabetes"},
    {"name": "myocardial_infarction", "query": "myocardial infarction"},
    {"name": "pneumonia", "query": "pneumonia"},
    {"name": "hypertension_ckd", "query": "hypertension chronic kidney disease"},
    {"name": "seizure_disorder", "query": "seizure disorder"},
]


def run_search_preview(query: str, limit: int = 10) -> pd.DataFrame:
    sql = f"""
    WITH raw AS (
      SELECT PARSE_JSON(
        SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
          'patient_search_service',
          '{{"query":"{query.replace("'","''")}","columns":["PATIENT_ID","PATIENT_UID","PATIENT_TITLE","AGE_YEARS","GENDER"],"limit":{limit}}}'
        )
      ) AS j
    )
    SELECT 
      r.value:"PATIENT_ID"::NUMBER      AS PATIENT_ID,
      r.value:"PATIENT_UID"::STRING     AS PATIENT_UID,
      r.value:"PATIENT_TITLE"::STRING   AS PATIENT_TITLE,
      r.value:"AGE_YEARS"::FLOAT        AS AGE,
      r.value:"GENDER"::STRING          AS GENDER
    FROM raw, LATERAL FLATTEN(input => raw.j:results) r
    LIMIT {limit}
    """
    conn = get_snowflake_connection()
    return execute_query(sql, conn)


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "baseline_results")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_file = os.path.join(out_dir, f"baseline_{timestamp}.csv")

    rows: List[Dict] = []
    for t in TEST_QUERIES:
        df = run_search_preview(t["query"], limit=10)
        for rank, (_, r) in enumerate(df.iterrows(), start=1):
            rows.append({
                "test_name": t["name"],
                "query": t["query"],
                "rank": rank,
                "patient_id": int(r.get("PATIENT_ID", 0)) if pd.notna(r.get("PATIENT_ID")) else None,
                "patient_uid": r.get("PATIENT_UID"),
                "patient_title": r.get("PATIENT_TITLE"),
                "age": float(r.get("AGE")) if pd.notna(r.get("AGE")) else None,
                "gender": r.get("GENDER"),
            })

    # Write CSV
    fieldnames = [
        "test_name", "query", "rank", "patient_id", "patient_uid", "patient_title", "age", "gender"
    ]
    with open(out_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote baseline results to {out_file}")


if __name__ == "__main__":
    main()


