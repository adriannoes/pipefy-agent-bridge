#!/bin/sh
# Preflight checks before Pipefy agent demos (see docs/ARCHITECTURE §16.4).
# Expects required env vars to be exported by the caller (e.g. make doctor loads .env).
# Never prints secret values — only "set" / "missing".

set -eu

FAILURES=0

ok() {
	printf '✓ %s\n' "$1"
}

warn() {
	printf '⚠ %s\n' "$1" >&2
}

fail() {
	printf '✗ %s\n' "$1"
	FAILURES=$((FAILURES + 1))
}

env_is_set() {
	# Usage: env_is_set VAR_NAME
	eval "v=\${$1:-}"
	[ -n "$v" ]
}

check_env_required() {
	name=$1
	if env_is_set "$name"; then
		ok "ENV $name: set"
	else
		fail "ENV $name: missing"
	fi
}

check_env_optional_warn() {
	name=$1
	if env_is_set "$name"; then
		ok "ENV $name: set (optional)"
	else
		warn "ENV $name: missing — required only for the matching harness (demo-cursor / demo-nat)"
	fi
}

check_uv() {
	if command -v uv >/dev/null 2>&1 && uv --version >/dev/null 2>&1; then
		ok "uv on PATH ($(uv --version 2>&1 | head -n 1))"
	else
		fail "uv not on PATH or uv --version failed"
	fi
}

check_pipefy_cli() {
	if ! command -v pipefy >/dev/null 2>&1; then
		fail "pipefy CLI not on PATH"
		return
	fi
	if ver=$(pipefy --version 2>/dev/null); then
		ok "pipefy CLI on PATH ($ver)"
	else
		fail "pipefy on PATH but pipefy --version failed"
	fi
}

check_pipefy_mcp_server() {
	if path=$(command -v pipefy-mcp-server 2>/dev/null); then
		ok "pipefy-mcp-server on PATH ($path)"
	else
		fail "pipefy-mcp-server not on PATH"
	fi
}

check_pipefy_ping() {
	if ! command -v pipefy >/dev/null 2>&1; then
		fail "Pipefy ping: skipped (pipefy not on PATH)"
		return
	fi
	if ! env_is_set PIPEFY_SERVICE_ACCOUNT_CLIENT_ID \
		|| ! env_is_set PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET; then
		fail "Pipefy ping: skipped (service account env vars missing)"
		return
	fi

	json=$(pipefy pipe list --json 2>/dev/null) || {
		fail "Pipefy ping: pipefy pipe list --json failed"
		return
	}

	if printf '%s' "$json" | python3 -c '
import json
import sys


def pipe_count(payload: object) -> int:
    """Count pipes in pipefy pipe list --json (array or organizations wrapper)."""
    if isinstance(payload, list):
        return len(payload)
    if not isinstance(payload, dict):
        return 0
    organizations = payload.get("organizations")
    if not isinstance(organizations, list):
        return 0
    total = 0
    for org in organizations:
        if not isinstance(org, dict):
            continue
        pipes = org.get("pipes")
        if isinstance(pipes, list):
            total += len(pipes)
    return total


raw = sys.stdin.read()
try:
    data = json.loads(raw)
except json.JSONDecodeError as exc:
    sys.stderr.write(f"invalid JSON: {exc}\n")
    sys.exit(1)
count = pipe_count(data)
if count < 1:
    sys.stderr.write("expected at least one pipe in pipe list JSON\n")
    sys.exit(1)
sys.exit(0)
'; then
		ok "Pipefy ping: pipe list returned at least one pipe"
	else
		fail "Pipefy ping: empty pipe list or invalid JSON (check credentials and pipe access)"
	fi
}

main() {
	printf 'pipefy-agent-bridge doctor\n\n'

	check_uv
	check_pipefy_cli
	check_pipefy_mcp_server

	check_env_required PIPEFY_SERVICE_ACCOUNT_CLIENT_ID
	check_env_required PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET
	check_env_required DEMO_PIPE_ID
	check_env_required DEMO_ORG_ID

	check_env_optional_warn CURSOR_API_KEY
	check_env_optional_warn NVIDIA_API_KEY

	check_pipefy_ping

	printf '\n'
	if [ "$FAILURES" -gt 0 ]; then
		printf '%d required check(s) failed.\n' "$FAILURES" >&2
		exit 1
	fi
	printf 'All required checks passed.\n'
}

main "$@"
