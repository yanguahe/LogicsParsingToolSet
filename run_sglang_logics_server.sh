#!/usr/bin/env bash
#
# Launch SGLang HTTP server for Logics-Parsing (Qwen3-VL) weights with data parallelism.
# Run inside container hyg_trn_rocm7.1 after setup_sglang_rocm_container.sh.
# This script sets SGLANG_USE_AITER=1 (required for ROCm + aiter).
#
# Environment (optional; overridden by CLI flags below):
#   LOGICS_ROOT          Repo root (default: this script's directory)
#   MODEL_PATH           Model directory (default: $LOGICS_ROOT/weights/Logics-Parsing-v2)
#   SGLANG_PORT          Listen port (default: 30000)
#   SGLANG_TP_SIZE       Tensor-parallel size (default: 1)
#   SGLANG_DP_SIZE       Data-parallel size (default: 2) — replicas; total GPUs used ~= tp * dp
#   SGLANG_LAUNCH_CWD    Process cwd for python (default: /tmp). Repo root often has a sibling
#                        `aiter/` source tree; Python puts cwd on sys.path and would import that
#                        folder instead of the installed aiter package — wrong imports / missing symbols.
#   CUDA_VISIBLE_DEVICES   Limit GPUs if needed (e.g. 0,1)
#   SGLANG_SERVED_MODEL_NAME   Model id exposed by /v1/models (default: basename of MODEL_PATH)
#   SGLANG_QWEN_VL_IMAGE_MIN_PIXELS
#   SGLANG_QWEN_VL_IMAGE_MAX_PIXELS
#                        Override Qwen-VL processor resize bounds. Defaults below match
#                        inference_v2.py for Logics-Parsing-v2: min=3136, max=7200*32*32.
#
# Usage:
#   bash run_sglang_logics_server.sh --port 30000 --dp-size 2
#   bash run_sglang_logics_server.sh -p 8080 --dp-size 4
#   bash run_sglang_logics_server.sh --port 30001 -- --mem-fraction-static 0.85
#
# OpenAI-compatible base URL: http://127.0.0.1:<port>/v1
# Docs: https://docs.sglang.io/  |  Upstream tag: https://github.com/sgl-project/sglang/commits/v0.5.10.post1

set -euo pipefail

export SGLANG_USE_AITER=1

ROOT="${LOGICS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
MODEL_PATH="${MODEL_PATH:-$ROOT/weights/Logics-Parsing-v2}"
PORT="${SGLANG_PORT:-30000}"
TP="${SGLANG_TP_SIZE:-1}"
DP="${SGLANG_DP_SIZE:-2}"
PASSTHROUGH=()

usage() {
  cat <<EOF
Usage: $(basename "$0") [options] [-- extra sglang.launch_server args]

Options:
  --port, -p <n>   Listen port (default: 30000, or \$SGLANG_PORT)
  --dp-size <n>    Data-parallel size (default: 2, or \$SGLANG_DP_SIZE)
  -h, --help       Show this help

CLI options override environment. Remaining args after -- are passed to sglang.launch_server.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port|-p)
      PORT="${2:?--port requires a value}"
      shift 2
      ;;
    --dp-size)
      DP="${2:?--dp-size requires a value}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      PASSTHROUGH+=("$@")
      break
      ;;
    *)
      PASSTHROUGH+=("$1")
      shift
      ;;
  esac
done

# Absolute model path so we can launch from a neutral cwd (see SGLANG_LAUNCH_CWD above).
case "$MODEL_PATH" in
  /*) ;;
  *) MODEL_PATH="$ROOT/$MODEL_PATH" ;;
esac

SERVED_MODEL_NAME="${SGLANG_SERVED_MODEL_NAME:-$(basename "$MODEL_PATH")}"
export SGLANG_QWEN_VL_IMAGE_MIN_PIXELS="${SGLANG_QWEN_VL_IMAGE_MIN_PIXELS:-3136}"
export SGLANG_QWEN_VL_IMAGE_MAX_PIXELS="${SGLANG_QWEN_VL_IMAGE_MAX_PIXELS:-7372800}"

LAUNCH_CWD="${SGLANG_LAUNCH_CWD:-/tmp}"
cd "$LAUNCH_CWD"

exec python3 -m sglang.launch_server \
  --model-path "$MODEL_PATH" \
  --served-model-name "$SERVED_MODEL_NAME" \
  --host 0.0.0.0 \
  --port "$PORT" \
  --tp-size "$TP" \
  --dp-size "$DP" \
  "${PASSTHROUGH[@]}"
