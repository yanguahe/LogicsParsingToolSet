#!/usr/bin/env bash
#
# Gracefully stop an SGLang server running inside a Docker container.
#
# This targets the server launched by:
#   - run_sglang_logics_server.sh
#   - install_logics_parsing_sglang.sh --start-server
#
# If the server was started in the current terminal, pressing Ctrl+C there is the
# safest option. This helper is for stopping it from another terminal/session.
#
# Behavior:
#   1. Find the `sglang.launch_server` root process for the specified port
#   2. Send SIGINT to its process group (closest to Ctrl+C)
#   3. If still alive after a timeout, escalate to SIGTERM
#   4. As a last resort, escalate to SIGKILL
#
# Usage:
#   ./kill_sglang_logics_server.sh hyg_trn_rocm7.1
#   ./kill_sglang_logics_server.sh --port 33157 hyg_trn_rocm7.1

set -euo pipefail

PORT="${SGLANG_PORT:-30000}"
INT_TIMEOUT_SEC="${INT_TIMEOUT_SEC:-20}"
TERM_TIMEOUT_SEC="${TERM_TIMEOUT_SEC:-10}"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options] <container_name>

Options:
  --port, -p <n>         Server port to stop (default: 30000, or \$SGLANG_PORT)
  --int-timeout <sec>    Wait after SIGINT before escalating (default: $INT_TIMEOUT_SEC)
  --term-timeout <sec>   Wait after SIGTERM before SIGKILL (default: $TERM_TIMEOUT_SEC)
  -h, --help             Show this help

Examples:
  $0 hyg_trn_rocm7.1
  $0 --port 33157 hyg_trn_rocm7.1
EOF
}

main() {
  local -a positionals=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --port|-p)
        PORT="${2:?--port requires a value}"
        shift 2
        ;;
      --int-timeout)
        INT_TIMEOUT_SEC="${2:?--int-timeout requires a value}"
        shift 2
        ;;
      --term-timeout)
        TERM_TIMEOUT_SEC="${2:?--term-timeout requires a value}"
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

  if [[ "${#positionals[@]}" -ne 1 ]]; then
    echo "[error] Expected exactly one <container_name>." >&2
    usage
    exit 1
  fi

  local container_name="${positionals[0]}"
  if ! docker ps --format '{{.Names}}' | grep -qx "$container_name"; then
    echo "[error] Container '$container_name' is not running." >&2
    exit 1
  fi

  echo "[info] Stopping SGLang server in '$container_name' on port $PORT ..."
  docker exec -i \
    -e TARGET_PORT="$PORT" \
    -e INT_TIMEOUT_SEC="$INT_TIMEOUT_SEC" \
    -e TERM_TIMEOUT_SEC="$TERM_TIMEOUT_SEC" \
    "$container_name" \
    python3 - <<'PY'
import os
import shlex
import signal
import subprocess
import sys
import time
from collections import defaultdict
from urllib import request as urllib_request

PORT = int(os.environ["TARGET_PORT"])
INT_TIMEOUT_SEC = float(os.environ["INT_TIMEOUT_SEC"])
TERM_TIMEOUT_SEC = float(os.environ["TERM_TIMEOUT_SEC"])


def command_has_port(args: str, port: int) -> bool:
    try:
        tokens = shlex.split(args)
    except ValueError:
        tokens = args.split()

    for i, token in enumerate(tokens):
        if token == "--port" and i + 1 < len(tokens) and tokens[i + 1] == str(port):
            return True
        if token.startswith("--port=") and token.split("=", 1)[1] == str(port):
            return True
    return False


def list_processes():
    result = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,pgid=,args="],
        check=True,
        text=True,
        capture_output=True,
    )
    rows = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid, ppid, pgid, args = parts
        rows.append(
            {
                "pid": int(pid),
                "ppid": int(ppid),
                "pgid": int(pgid),
                "args": args,
            }
        )
    return rows


def port_is_open(port: int) -> bool:
    try:
        with urllib_request.urlopen(f"http://127.0.0.1:{port}/model_info", timeout=2):
            return True
    except Exception:
        return False


def pid_exists(pid: int) -> bool:
    return os.path.exists(f"/proc/{pid}")


def collect_descendants(root_pids, rows):
    children = defaultdict(list)
    for row in rows:
        children[row["ppid"]].append(row["pid"])

    seen = set()
    stack = list(root_pids)
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        stack.extend(children.get(pid, []))
    return seen


def wait_for_shutdown(target_pids, timeout_sec: float) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if not any(pid_exists(pid) for pid in target_pids) and not port_is_open(PORT):
            return True
        time.sleep(1)
    return not any(pid_exists(pid) for pid in target_pids) and not port_is_open(PORT)


rows = list_processes()
root_rows = [
    row
    for row in rows
    if "sglang.launch_server" in row["args"] and command_has_port(row["args"], PORT)
]

if not root_rows:
    if port_is_open(PORT):
        print(
            f"[container] port {PORT} is serving, but no matching sglang.launch_server root was found; refusing broad kill",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"[container] no SGLang server found on port {PORT}; nothing to stop")
    sys.exit(0)

root_pids = sorted({row["pid"] for row in root_rows})
target_pids = sorted(collect_descendants(root_pids, rows))
root_pgids = sorted({row["pgid"] for row in root_rows})

print(f"[container] matched {len(root_rows)} launch_server root process(es) for port {PORT}:")
for row in root_rows:
    print(f"[container]   pid={row['pid']} pgid={row['pgid']} cmd={row['args']}")
print(f"[container] tracked {len(target_pids)} process(es) in the server tree")

for pgid in root_pgids:
    try:
        os.killpg(pgid, signal.SIGINT)
        print(f"[container] sent SIGINT to process group {pgid}")
    except ProcessLookupError:
        pass

if wait_for_shutdown(target_pids, INT_TIMEOUT_SEC):
    print(f"[container] SGLang server on port {PORT} stopped cleanly after SIGINT")
    sys.exit(0)

alive_after_int = [pid for pid in target_pids if pid_exists(pid)]
print(
    f"[container] still alive after {INT_TIMEOUT_SEC:.0f}s; escalating to SIGTERM for {len(alive_after_int)} pid(s)"
)
for pid in alive_after_int:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass

if wait_for_shutdown(target_pids, TERM_TIMEOUT_SEC):
    print(f"[container] SGLang server on port {PORT} stopped after SIGTERM")
    sys.exit(0)

alive_after_term = [pid for pid in target_pids if pid_exists(pid)]
print(
    f"[container] still alive after {TERM_TIMEOUT_SEC:.0f}s; escalating to SIGKILL for {len(alive_after_term)} pid(s)"
)
for pid in alive_after_term:
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass

time.sleep(1)
remaining = [pid for pid in target_pids if pid_exists(pid)]
if remaining or port_is_open(PORT):
    print(
        f"[container] failed to fully stop SGLang server on port {PORT}; remaining pids: {remaining}",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"[container] SGLang server on port {PORT} stopped after SIGKILL")
PY
}

main "$@"
