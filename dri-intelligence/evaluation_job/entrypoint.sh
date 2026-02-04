#!/bin/bash
set -e

echo "Starting DRI Evaluation Job"
echo "Parameters: RUN_NAME=$RUN_NAME, PROMPT_VERSION=$PROMPT_VERSION, MODEL=$MODEL, SAMPLE_SIZE=$SAMPLE_SIZE"

python /app/evaluate_dri.py \
    --run-name "${RUN_NAME:-Evaluation}" \
    --prompt-version "${PROMPT_VERSION:-v1.0}" \
    --model "${MODEL:-claude-3-5-sonnet}" \
    --sample-size "${SAMPLE_SIZE:-10}"

echo "Evaluation complete"
