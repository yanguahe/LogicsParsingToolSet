#!/usr/bin/env bash
#
# Install SGLang from the vendored ./sglang tree (tag v0.5.10.post1) for ROCm + AMD GPUs.
# Intended to run INSIDE container hyg_trn_rocm7.1 with the Logics-Parsing repo mounted.
#
# Prerequisite: aiter already installed (python setup.py develop) and working ROCm PyTorch.
#
# Usage (run INSIDE the ROCm PyTorch container, e.g. hyg_trn_rocm7.1):
#   cd /path/to/Logics-Parsing
#   bash setup_sglang_rocm_container.sh
#
# If `python3` is not the same env as PyTorch (rare), set:
#   export PYTHON=/opt/conda/bin/python
#
# After install, always enable AITER kernels when running the server:
#   export SGLANG_USE_AITER=1
#
# Reference: sglang/docs/platforms/amd_gpu.md

set -euo pipefail

# Same interpreter for build + pip (avoids "no module named torch" when pip targets another Python).
PYTHON="${PYTHON:-python3}"

ROOT="${LOGICS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
SGLANG_DIR="$ROOT/sglang"

if ! "$PYTHON" -c "import torch" 2>/dev/null; then
  echo "[error] PyTorch is not importable with: $PYTHON" >&2
  echo "  Run this script inside container hyg_trn_rocm7.1 (or your ROCm PyTorch env), not on a bare host." >&2
  echo "  Or set PYTHON to the interpreter that has torch, e.g. export PYTHON=/opt/conda/bin/python" >&2
  exit 1
fi

echo "[info] Using Python: $($PYTHON -c 'import sys; print(sys.executable)')"

if [[ ! -d "$SGLANG_DIR/sgl-kernel" ]]; then
  echo "[error] Missing $SGLANG_DIR/sgl-kernel. Clone sglang at repo root first:" >&2
  echo "  git clone -b v0.5.10.post1 --depth 1 https://github.com/sgl-project/sglang.git sglang" >&2
  exit 1
fi

echo "[info] SGLANG_USE_AITER=1 is required at runtime; adding to current shell."
export SGLANG_USE_AITER=1

echo "[info] Building and installing sgl-kernel (ROCm) ..."
cd "$SGLANG_DIR/sgl-kernel"
"$PYTHON" setup_rocm.py install

echo "[info] Switching python/pyproject to HIP (ROCm) extras ..."
# The vendored python/pyproject uses a fixed version, so we do not need to touch git config here.

cd "$SGLANG_DIR/python"
if [[ -f pyproject.toml ]] && [[ ! -f pyproject.toml.cuda_backup ]]; then
  cp pyproject.toml pyproject.toml.cuda_backup
fi
rm -f pyproject.toml
cp pyproject_other.toml pyproject.toml

echo "[info] pip install -e python[all_hip] (this may take several minutes) ..."
"$PYTHON" -m pip install -U pip
"$PYTHON" -m pip install -e ".[all_hip]"

echo "[info] Installing apache-tvm-ffi (provides tvm_ffi for SGLang JIT kernels; overlap schedule / warmup) ..."
"$PYTHON" -m pip install "apache-tvm-ffi"

echo "[info] Done. Example server (adjust MODEL_PATH / DP_SIZE):"
echo "  export SGLANG_USE_AITER=1"
echo "  bash $ROOT/run_sglang_logics_server.sh"
