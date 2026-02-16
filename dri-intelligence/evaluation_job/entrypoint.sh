#!/bin/bash
set -e

echo "Starting DRI Evaluation Job"
echo "Parameters: RUN_NAME=$RUN_NAME, PROMPT_VERSION=$PROMPT_VERSION, MODEL=$MODEL, SAMPLE_SIZE=$SAMPLE_SIZE"
echo "Note: Parameters from DRI_EVAL_RUNS table will override environment variables"

python /app/evaluate_dri.py \
    --prompt-version "${PROMPT_VERSION:-v1.0}" \
    --model "${MODEL:-claude-sonnet-4-5}" \
    --sample-size "${SAMPLE_SIZE:-10}"

echo "Evaluation complete"
