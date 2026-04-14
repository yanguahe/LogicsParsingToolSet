#!/usr/bin/env bash
#
# Install aiter (editable) and Logics-Parsing dependencies inside a ROCm PyTorch
# container. Run this script from the host; it uses docker exec (or docker run).
#
# Usage:
#   ./install_logics_parsing.sh <container_name>
#       Run the full install inside an existing container named <container_name>.
#
#   ./install_logics_parsing.sh --create <workdir> <container_name>
#       Start a new container (same flags as the reference docker run), then run
#       the install inside it. <workdir> is the host path mounted into the
#       container (used as -v and -w).
#
# Environment (optional):
#   LOGICS_ROOT   Root of Logics-Parsing repo (default: directory containing this script)
#   AITER_REMOTE  Git URL for aiter (default: git@github.com:yanguahe/aiter.git)
#   AITER_BRANCH  Branch for aiter (default: opt_mtp_tt)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGICS_ROOT="${LOGICS_ROOT:-$SCRIPT_DIR}"
AITER_REMOTE="${AITER_REMOTE:-git@github.com:yanguahe/aiter.git}"
AITER_BRANCH="${AITER_BRANCH:-opt_mtp_tt}"

# ROCm / PyTorch base image (must match the intended deployment stack)
readonly DOCKER_IMAGE="${DOCKER_IMAGE:-rocm/pytorch:rocm7.1_ubuntu24.04_py3.12_pytorch_release_2.8.0}"

usage() {
  cat <<EOF
Usage:
  $0 <container_name>
      Install into an already running container.

  $0 --create <workdir> <container_name>
      Create and start a new container, then install. Requires host workdir and container name.

Environment:
  LOGICS_ROOT=$LOGICS_ROOT (override to point at the repo checkout)
  DOCKER_IMAGE=$DOCKER_IMAGE
EOF
  exit 1
}

ensure_aiter_clone() {
  local aiter_dir="$LOGICS_ROOT/aiter"
  if [[ -d "$aiter_dir/.git" ]]; then
    echo "[info] aiter repo already present at $aiter_dir"
    return 0
  fi
  echo "[info] Cloning aiter into $aiter_dir ..."
  git clone -b "$AITER_BRANCH" --recursive "$AITER_REMOTE" "$aiter_dir"
}

docker_run_new_container() {
  local workdir="$1"
  local name="$2"
  if docker ps -a --format '{{.Names}}' | grep -qx "$name"; then
    echo "[error] Container name '$name' already exists. Remove it or use: $0 $name" >&2
    exit 1
  fi
  echo "[info] Starting container '$name' with workdir '$workdir' ..."
  # Detached run so this script can docker exec the install (interactive -it is not suitable for automation)
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
    sleep infinity
}

# Ensure root's ~/.bashrc in the container has Git convenience aliases (idempotent).
ensure_root_bashrc_git_aliases() {
  local container="$1"
  docker exec -i "$container" bash -s <<'ALIASES_EOF'
set -euo pipefail
BASHRC=/root/.bashrc
touch "$BASHRC"
if grep -q "^alias gst='git status'" "$BASHRC" 2>/dev/null; then
  echo "[container] Root ~/.bashrc already has alias gst; skipping git alias block."
  exit 0
fi
cat >> "$BASHRC" <<'EOF'

# Git convenience aliases
alias gst='git status'
alias gsth='git status | head'
alias gstt='git status | tail'
alias glog='git log | head'
alias gb='git branch'
alias gc='git checkout'
alias fomm='git fetch origin master:master'
alias rebhm='git rebase HEAD^ HEAD --onto=master'
alias phhd='git push origin HEAD:refs/for/master'
EOF
echo "[container] Appended Git convenience aliases to $BASHRC"
ALIASES_EOF
}

run_install_in_container() {
  local container="$1"
  if ! docker ps --format '{{.Names}}' | grep -qx "$container"; then
    echo "[error] Container '$container' is not running. Start it first." >&2
    exit 1
  fi

  # Paths inside container match host when workdir is the repo root and mount is host:host
  local aiter_path="$LOGICS_ROOT/aiter"
  local weights_path="$LOGICS_ROOT/weights/Logics-Parsing-v2"

  echo "[info] Running install inside '$container' ..."

  docker exec -i "$container" bash -s <<INSTALL_EOF
set -euo pipefail

export HF_HUB_ENABLE_HF_TRANSFER=0

echo "[container] pip install vcs_versioning ..."
python3 -m pip install -U pip
python3 -m pip install vcs_versioning

echo "[container] git safe.directory for aiter ..."
git config --global --add safe.directory "$aiter_path"

echo "[container] aiter develop install ..."
cd "$aiter_path"
python3 setup.py develop

echo "[container] Logics-Parsing Python dependencies ..."
cd "$LOGICS_ROOT"
python3 -m pip install transformers==4.57.1 accelerate==1.0.0 opencv-python pillow huggingface_hub modelscope
python3 -m pip install flash-attn==2.8.3 --no-build-isolation

echo "[container] download_model_v2.py (Hugging Face) ..."
python3 download_model_v2.py --type huggingface

echo "[container] sample inference ..."
python3 inference_v2.py --image_path "$LOGICS_ROOT/demo_input_output/demo.png" --output_path "$LOGICS_ROOT/demo_input_output/output_demo" --model_path "$weights_path"

echo "[container] Done."
INSTALL_EOF

  ensure_root_bashrc_git_aliases "$container"
}

main() {
  if [[ $# -lt 1 ]]; then
    usage
  fi

  local container_name

  if [[ "$1" == "--create" ]]; then
    if [[ $# -ne 3 ]]; then
      echo "[error] --create requires <workdir> and <container_name>" >&2
      usage
    fi
    local workdir
    workdir="$(cd "$2" && pwd)"
    container_name="$3"
    # Ensure LOGICS_ROOT is under the mounted workdir when using --create
    case "$LOGICS_ROOT" in
      "$workdir"|"$workdir"/*) ;;
      *) echo "[warn] LOGICS_ROOT ($LOGICS_ROOT) is not under workdir ($workdir). Mount may not include the repo." >&2 ;;
    esac
    ensure_aiter_clone
    docker_run_new_container "$workdir" "$container_name"
    run_install_in_container "$container_name"
  else
    container_name="$1"
    ensure_aiter_clone
    run_install_in_container "$container_name"
  fi

  echo "[info] All steps finished for container: $container_name"
}

main "$@"
