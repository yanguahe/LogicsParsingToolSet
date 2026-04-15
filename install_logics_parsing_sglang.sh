#!/usr/bin/env bash
#
# One-stop ROCm / AMD deployment helper for Logics-Parsing-v2 with SGLang.
#
# Independent actions:
#   1. --install                    Build the SGLang ROCm inference environment inside a container
#   2. --start-server               Launch the SGLang server in foreground (blocking)
#   3. --install-and-start-server   Convenience action: same as --install --start-server
#   4. --run-demo                   Run `python3 inference_sglang_openai.py` on demo images and
#                                   compare against the base golden files via
#                                   `python3 compare_demo_mmd.py --groups 2`
#
# Examples:
#   ./install_logics_parsing_sglang.sh hyg_trn_rocm7.1
#   ./install_logics_parsing_sglang.sh --install hyg_trn_rocm7.1
#   ./install_logics_parsing_sglang.sh --install-and-start-server hyg_trn_rocm7.1
#   ./install_logics_parsing_sglang.sh --start-server --dp-size 2 --port 30000 hyg_trn_rocm7.1
#   ./install_logics_parsing_sglang.sh --run-demo --port 30000 hyg_trn_rocm7.1
#   ./install_logics_parsing_sglang.sh --create /mnt/raid0/heyanguang/code/Logics-Parsing --dp-size 2 hyg_trn_rocm7.1
#
# Action rules:
#   - `--install` and `--start-server` may be used together
#   - `--run-demo` must be used alone as the only action
#   - If no action flag is provided, default to `--install-and-start-server`
#
# References:
#   - setup_sglang_rocm_container.sh
#   - run_sglang_logics_server.sh
#
# SGLang source used by this script:
#   remote: git@github.com:yanguahe/sglang.git
#   branch: gb.v0.5.6.post2

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGICS_ROOT="${LOGICS_ROOT:-$SCRIPT_DIR}"
LOGICS_ROOT="$(cd "$LOGICS_ROOT" && pwd)"
AITER_REMOTE="${AITER_REMOTE:-git@github.com:yanguahe/aiter.git}"
AITER_BRANCH="${AITER_BRANCH:-opt_mtp_tt}"
SGLANG_REMOTE="${SGLANG_REMOTE:-git@github.com:yanguahe/sglang.git}"
SGLANG_BRANCH="${SGLANG_BRANCH:-gb.v0.5.6.post2}"

readonly DOCKER_IMAGE="${DOCKER_IMAGE:-rocm/pytorch:rocm7.1_ubuntu24.04_py3.12_pytorch_release_2.8.0}"
SERVER_READY_TIMEOUT_SEC="${SERVER_READY_TIMEOUT_SEC:-900}"
SGLANG_PORT="${SGLANG_PORT:-30000}"
SGLANG_DP_SIZE="${SGLANG_DP_SIZE:-2}"
SERVER_LOG_BASENAME="${SERVER_LOG_BASENAME:-sglsv.log}"

usage() {
  cat <<EOF
Usage:
  $0 [--install] [--start-server] [--install-and-start-server] [--run-demo] [--dp-size N] [--port P] <container_name>
  $0 --create <workdir> [--install] [--start-server] [--install-and-start-server] [--run-demo] [--dp-size N] [--port P] <container_name>

Actions:
  --install                    Build the ROCm + SGLang inference environment in the container
  --start-server               Start SGLang server in foreground (blocking)
  --install-and-start-server   Convenience action: run install, then start server
  --run-demo                   Run inference_sglang_openai.py on demo images and compare group 2

Behavior:
  - If no action is specified, the script runs: --install-and-start-server
  - --run-demo is mutually exclusive with install/start actions
  - --create starts a new detached container first, then runs the selected actions

Options:
  --create <workdir>  Create and start a container with <workdir> mounted host:host
  --dp-size <n>       SGLang data parallel size for server startup (default: $SGLANG_DP_SIZE)
  --port, -p <n>      SGLang server port (default: $SGLANG_PORT)
  -h, --help          Show this help

Environment:
  LOGICS_ROOT=$LOGICS_ROOT
  DOCKER_IMAGE=$DOCKER_IMAGE
  AITER_REMOTE=$AITER_REMOTE
  AITER_BRANCH=$AITER_BRANCH
  SGLANG_REMOTE=$SGLANG_REMOTE
  SGLANG_BRANCH=$SGLANG_BRANCH
  SERVER_READY_TIMEOUT_SEC=$SERVER_READY_TIMEOUT_SEC
EOF
}

ensure_aiter_clone() {
  local aiter_dir="$LOGICS_ROOT/aiter"
  local current_branch
  if [[ -d "$aiter_dir/.git" ]]; then
    current_branch="$(git -C "$aiter_dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
    echo "[info] aiter repo already present at $aiter_dir (branch: $current_branch)"
    return 0
  fi
  echo "[info] Cloning aiter (branch: $AITER_BRANCH) into $aiter_dir ..."
  git clone -b "$AITER_BRANCH" --recursive "$AITER_REMOTE" "$aiter_dir"
  current_branch="$(git -C "$aiter_dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  echo "[info] aiter repo ready at $aiter_dir (branch: $current_branch)"
}

ensure_sglang_clone() {
  local sglang_dir="$LOGICS_ROOT/sglang"
  local current_branch
  if [[ ! -d "$sglang_dir/.git" ]]; then
    echo "[info] Cloning sglang (branch: $SGLANG_BRANCH) into $sglang_dir ..."
    git clone -b "$SGLANG_BRANCH" --recursive "$SGLANG_REMOTE" "$sglang_dir"
    current_branch="$(git -C "$sglang_dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
    echo "[info] sglang repo ready at $sglang_dir (branch: $current_branch)"
    return 0
  fi

  local remote_url
  remote_url="$(git -C "$sglang_dir" remote get-url origin 2>/dev/null || true)"
  if [[ -n "$remote_url" && "$remote_url" != "$SGLANG_REMOTE" ]]; then
    echo "[error] Existing sglang checkout uses origin '$remote_url', expected '$SGLANG_REMOTE'." >&2
    echo "        Please fix the checkout manually or remove $sglang_dir and rerun." >&2
    exit 1
  fi

  current_branch="$(git -C "$sglang_dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  if [[ "$current_branch" == "$SGLANG_BRANCH" ]]; then
    echo "[info] sglang repo already present at $sglang_dir (branch: $current_branch)"
    return 0
  fi

  if [[ -n "$(git -C "$sglang_dir" status --porcelain)" ]]; then
    echo "[error] Existing sglang checkout is on '$current_branch' and has local changes." >&2
    echo "        Clean it or manually switch to '$SGLANG_BRANCH' before rerunning." >&2
    exit 1
  fi

  echo "[info] Switching existing sglang checkout at $sglang_dir from $current_branch to $SGLANG_BRANCH ..."
  git -C "$sglang_dir" fetch origin "$SGLANG_BRANCH"
  if git -C "$sglang_dir" show-ref --verify --quiet "refs/heads/$SGLANG_BRANCH"; then
    git -C "$sglang_dir" checkout "$SGLANG_BRANCH"
  else
    git -C "$sglang_dir" checkout -b "$SGLANG_BRANCH" "origin/$SGLANG_BRANCH"
  fi
  current_branch="$(git -C "$sglang_dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  echo "[info] sglang repo ready at $sglang_dir (branch: $current_branch)"
}

docker_run_new_container() {
  local workdir="$1"
  local name="$2"
  if docker ps -a --format '{{.Names}}' | grep -qx "$name"; then
    echo "[error] Container name '$name' already exists. Remove it or reuse it without --create." >&2
    exit 1
  fi
  echo "[info] Starting container '$name' with workdir '$workdir' ..."
  docker run -d \
    --name "$name" \
    --network=host \
    --privileged \
    --shm-size=64G \
    --ulimit memlock=-1 \
    --ulimit stack=67108864 \
    --group-add=video \
    --ipc=host \
    --cap-add=CAP_SYS_ADMIN \
    --cap-add=SYS_PTRACE \
    --security-opt seccomp=unconfined \
    --device=/dev/kfd \
    --device=/dev/dri \
    --device=/dev/mem \
    -v "${workdir}:${workdir}" \
    -w "$workdir" \
    "$DOCKER_IMAGE" \
    sleep infinity >/dev/null
}

require_running_container() {
  local container="$1"
  if ! docker ps --format '{{.Names}}' | grep -qx "$container"; then
    echo "[error] Container '$container' is not running." >&2
    exit 1
  fi
}

ensure_runtime_installed_in_container() {
  local container="$1"
  require_running_container "$container"

  echo "[info] Verifying aiter and sglang are installed inside '$container' ..."
  if ! docker exec "$container" bash -lc "cd /tmp && export LOGICS_ROOT=\"$LOGICS_ROOT\" && python3 - <<'PY'
import os
import sys

repo_root = os.environ['LOGICS_ROOT']
expected_aiter_root = os.path.realpath(os.path.join(repo_root, 'aiter'))
expected_sglang_root = os.path.realpath(os.path.join(repo_root, 'sglang', 'python'))
errors = []

try:
    import aiter
    aiter_file = os.path.realpath(getattr(aiter, '__file__', ''))
    if not aiter_file.startswith(expected_aiter_root + os.sep):
        errors.append(
            f\"aiter is importable, but not from this repo checkout: {aiter_file} (expected under {expected_aiter_root})\"
        )
except Exception as exc:
    errors.append(f\"aiter is not installed/importable in the container: {exc}\")

try:
    import sglang
    sglang_file = os.path.realpath(getattr(sglang, '__file__', ''))
    if not sglang_file.startswith(expected_sglang_root + os.sep):
        errors.append(
            f\"sglang is importable, but not from this repo checkout: {sglang_file} (expected under {expected_sglang_root})\"
        )
except Exception as exc:
    errors.append(f\"sglang is not installed/importable in the container: {exc}\")

if errors:
    for item in errors:
        print('[container]', item, file=sys.stderr)
    sys.exit(1)

print('[container] runtime preflight ok')
PY"; then
    echo "[error] Container '$container' does not have the required installed aiter/sglang runtime." >&2
    echo "        Run: $0 --install $container" >&2
    exit 1
  fi
}

server_is_ready() {
  local container="$1"
  local port="$2"
  docker exec "$container" bash -lc "python3 - <<'PY'
import sys
from urllib import request, error

try:
    with request.urlopen('http://127.0.0.1:${port}/model_info', timeout=3) as resp:
        sys.exit(0 if resp.status == 200 else 1)
except Exception:
    sys.exit(1)
PY" >/dev/null 2>&1
}

wait_for_server() {
  local container="$1"
  local port="$2"
  local waited=0
  local interval=5

  echo "[info] Waiting for SGLang server on port $port ..."
  while (( waited < SERVER_READY_TIMEOUT_SEC )); do
    if server_is_ready "$container" "$port"; then
      echo "[info] SGLang server is ready on http://127.0.0.1:$port"
      return 0
    fi
    sleep "$interval"
    waited=$((waited + interval))
  done

  echo "[error] Timed out waiting for SGLang server after ${SERVER_READY_TIMEOUT_SEC}s." >&2
  echo "[error] Inspect log: $LOGICS_ROOT/$SERVER_LOG_BASENAME" >&2
  docker exec "$container" bash -lc "test -f '$LOGICS_ROOT/$SERVER_LOG_BASENAME' && tail -80 '$LOGICS_ROOT/$SERVER_LOG_BASENAME' || true" >&2 || true
  return 1
}

run_install_in_container() {
  local container="$1"
  require_running_container "$container"

  local aiter_path="$LOGICS_ROOT/aiter"
  local sglang_path="$LOGICS_ROOT/sglang"
  local weights_path="$LOGICS_ROOT/weights/Logics-Parsing-v2"

  echo "[info] Installing SGLang ROCm inference environment inside '$container' ..."
  docker exec -i "$container" bash -s <<INSTALL_EOF
set -euo pipefail

export HF_HUB_ENABLE_HF_TRANSFER=0

echo "[container] pip install vcs_versioning ..."
python3 -m pip install -U pip
python3 -m pip install vcs_versioning

echo "[container] git safe.directory for aiter ..."
git config --global --add safe.directory "$aiter_path"
git config --global --add safe.directory "$sglang_path"

echo "[container] aiter develop install ..."
cd "$aiter_path"
python3 setup.py develop

echo "[container] setup_sglang_rocm_container.sh ..."
cd "$LOGICS_ROOT"
bash setup_sglang_rocm_container.sh

echo "[container] install PDF/demo post-processing dependencies ..."
python3 -m pip install opencv-python PyMuPDF

if [[ -f "$weights_path/config.json" ]]; then
  echo "[container] weights already present at $weights_path"
else
  echo "[container] download_model_v2.py (Hugging Face) ..."
  python3 download_model_v2.py --type huggingface
fi

echo "[container] install step done."
INSTALL_EOF
}

start_server_in_container() {
  local container="$1"
  local port="$2"
  local dp_size="$3"
  require_running_container "$container"
  ensure_runtime_installed_in_container "$container"

  if server_is_ready "$container" "$port"; then
    echo "[info] SGLang server is already serving on port $port; skip starting."
    return 0
  fi

  local server_log_path="$LOGICS_ROOT/$SERVER_LOG_BASENAME"
  echo "[info] Starting SGLang server in '$container' (port=$port, dp-size=$dp_size) ..."
  docker exec "$container" bash -lc "set -o pipefail && cd \"$LOGICS_ROOT\" && bash run_sglang_logics_server.sh --port \"$port\" --dp-size \"$dp_size\" 2>&1 | tee \"$server_log_path\""
}

run_demo_in_container() {
  local container="$1"
  local port="$2"
  require_running_container "$container"
  wait_for_server "$container" "$port"

  echo "[info] Running demo inference and comparison inside '$container' ..."
  docker exec -i "$container" bash -s <<DEMO_EOF
set -euo pipefail

export OPENAI_BASE_URL="http://127.0.0.1:${port}/v1"

cd "$LOGICS_ROOT"
echo "[container] python3 inference_sglang_openai.py ..."
python3 inference_sglang_openai.py

echo "[container] python3 compare_demo_mmd.py --groups 2 ..."
python3 compare_demo_mmd.py --groups 2

echo "[container] demo validation done."
DEMO_EOF
}

main() {
  local create_mode=0
  local create_workdir=""
  local do_install=0
  local do_start_server=0
  local do_run_demo=0
  local do_install_and_start_server=0
  local dp_size="$SGLANG_DP_SIZE"
  local port="$SGLANG_PORT"
  local -a positionals=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --create)
        create_mode=1
        create_workdir="${2:-}"
        if [[ -z "$create_workdir" ]]; then
          echo "[error] --create requires <workdir>" >&2
          usage
          exit 1
        fi
        shift 2
        ;;
      --install)
        do_install=1
        shift
        ;;
      --start-server)
        do_start_server=1
        shift
        ;;
      --install-and-start-server)
        do_install_and_start_server=1
        do_install=1
        do_start_server=1
        shift
        ;;
      --run-demo)
        do_run_demo=1
        shift
        ;;
      --dp-size)
        dp_size="${2:?--dp-size requires a value}"
        shift 2
        ;;
      --port|-p)
        port="${2:?--port requires a value}"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      -*)
        echo "[error] Unknown option: $1" >&2
        usage
        exit 1
        ;;
      *)
        positionals+=("$1")
        shift
        ;;
    esac
  done

  if (( do_install == 0 && do_start_server == 0 && do_run_demo == 0 )); then
    do_install=1
    do_start_server=1
    do_install_and_start_server=1
  fi

  if (( do_run_demo && (do_install || do_start_server || do_install_and_start_server) )); then
    echo "[error] --run-demo must be used alone and cannot be combined with install/start actions." >&2
    usage
    exit 1
  fi

  if [[ "${#positionals[@]}" -ne 1 ]]; then
    echo "[error] Expected exactly one <container_name>." >&2
    usage
    exit 1
  fi
  local container_name="${positionals[0]}"

  if (( do_install || do_start_server )); then
    ensure_sglang_clone
    ensure_aiter_clone
  fi

  if (( create_mode )); then
    local workdir
    workdir="$(cd "$create_workdir" && pwd)"
    case "$LOGICS_ROOT" in
      "$workdir"|"$workdir"/*) ;;
      *)
        echo "[warn] LOGICS_ROOT ($LOGICS_ROOT) is not under workdir ($workdir). Mount may not include the repo." >&2
        ;;
    esac
    docker_run_new_container "$workdir" "$container_name"
  fi

  if (( do_install )); then
    run_install_in_container "$container_name"
  fi
  if (( do_start_server )); then
    start_server_in_container "$container_name" "$port" "$dp_size"
  fi
  if (( do_run_demo )); then
    run_demo_in_container "$container_name" "$port"
  fi

  echo "[info] All requested steps finished for container: $container_name"
}

main "$@"
