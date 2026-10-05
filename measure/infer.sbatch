#!/usr/bin/env bash
#SBATCH --job-name=trial-measurement
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:2
#SBATCH --time=24:00:00
set -euo pipefail

# Supply scheduler resources and activate a vLLM 0.23.0 environment before submission.
: "${MODEL:?Set MODEL to Qwen/Qwen3.8-27B-FP8}"
: "${PACKETS:?Set PACKETS to the private packet JSONL}"
: "${PROMPT:?Set PROMPT to the frozen prompt file}"
: "${SCHEMA:?Set SCHEMA to the corresponding JSON schema}"
: "${LABEL_DIR:?Set LABEL_DIR to a private output directory}"

CUDA_VISIBLE_DEVICES=0 vllm serve "$MODEL" --host 127.0.0.1 --port 8000 --max-model-len 16384 &
server_a=$!
CUDA_VISIBLE_DEVICES=1 vllm serve "$MODEL" --host 127.0.0.1 --port 8001 --max-model-len 16384 &
server_b=$!
trap 'kill "$server_a" "$server_b"' EXIT
# Readiness is checked without sending any study packet.
for port in 8000 8001; do
    until curl --fail --silent "http://127.0.0.1:$port/health" >/dev/null; do
        kill -0 "$server_a" "$server_b"
        sleep 5
    done
done
python -m measure.infer --packets "$PACKETS" --prompt "$PROMPT" --schema "$SCHEMA" \
    --out "$LABEL_DIR" --urls http://127.0.0.1:8000/v1 http://127.0.0.1:8001/v1 --model "$MODEL"
