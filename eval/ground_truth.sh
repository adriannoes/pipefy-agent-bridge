#!/bin/sh
# Snapshot Pipefy CLI JSON baselines for eval (see product PRD FR-20).
# Example: ./eval/ground_truth.sh inventory

set -eu

REPO_ROOT="$(CDPATH= cd "$(dirname "$0")/.." && pwd)"
FIXTURES_LIVE_DIR="$REPO_ROOT/eval/fixtures/live"
DEFAULT_SCENARIO=inventory

SCENARIO=${1:-$DEFAULT_SCENARIO}

env_is_set() {
	eval "v=\${$1:-}"
	[ -n "$v" ]
}

die() {
	printf 'error: %s\n' "$1" >&2
	exit 1
}

load_repo_env() {
	if [ ! -f "$REPO_ROOT/.env" ]; then
		die ".env missing — run: cp .env.example .env"
	fi
	# Do not clobber vars already exported by the caller (matches python-dotenv override=False).
	while IFS= read -r line || [ -n "$line" ]; do
		case "$line" in
		'' | '#'*) continue ;;
		*=*) ;;
		*) continue ;;
		esac
		name=${line%%=*}
		value=${line#*=}
		case "$value" in
		\"*) value=${value#\"}; value=${value%\"} ;;
		esac
		if ! env_is_set "$name"; then
			export "$name=$value"
		fi
	done <"$REPO_ROOT/.env"
}

require_env() {
	missing=
	for name in "$@"; do
		if ! env_is_set "$name"; then
			missing="${missing:+$missing, }$name"
		fi
	done
	if [ -n "$missing" ]; then
		die "missing required environment variable(s): $missing (copy .env.example to .env)"
	fi
}

require_pipefy_cli() {
	if ! command -v pipefy >/dev/null 2>&1; then
		die "pipefy CLI not on PATH — run: make install-pipefy-tools"
	fi
}

validate_nonempty_json() {
	json=$1
	label=$2
	printf '%s' "$json" | python3 -c '
import json
import sys

raw = sys.stdin.read()
if not raw.strip():
    sys.stderr.write("empty JSON output\n")
    sys.exit(1)
try:
    json.loads(raw)
except json.JSONDecodeError as exc:
    sys.stderr.write(f"invalid JSON: {exc}\n")
    sys.exit(1)
sys.exit(0)
' || die "$label returned empty or invalid JSON"
}

capture_inventory_baseline() {
	require_env \
		PIPEFY_SERVICE_ACCOUNT_CLIENT_ID \
		PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET

	json=$(pipefy pipe list --json 2>&1) || die "pipefy pipe list --json failed"
	validate_nonempty_json "$json" "pipefy pipe list --json"
	printf '%s' "$json"
}

capture_card_scenario_baseline() {
	require_env \
		PIPEFY_SERVICE_ACCOUNT_CLIENT_ID \
		PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET \
		DEMO_PIPE_ID

	case "$SCENARIO" in
	stale_cards)
		require_env DEMO_PHASE_NAME
		;;
	summary) ;;
	esac

	json=$(
		PYTHONPATH="$REPO_ROOT" python3 "$REPO_ROOT/eval/capture_scenario_baseline.py" "$SCENARIO" 2>&1
	) || die "capture_scenario_baseline.py $SCENARIO failed"
	validate_nonempty_json "$json" "capture_scenario_baseline.py $SCENARIO"
	printf '%s' "$json"
}

write_baseline_fixture() {
	json=$1
	out_path="$FIXTURES_LIVE_DIR/${SCENARIO}.json"
	mkdir -p "$FIXTURES_LIVE_DIR"
	printf '%s\n' "$json" >"$out_path"
	printf 'wrote baseline: %s\n' "$out_path"
	if [ "${VERBOSE:-0}" = "1" ]; then
		printf '\n%s\n' "$json"
	fi
}

main() {
	load_repo_env
	require_pipefy_cli

	case "$SCENARIO" in
	inventory)
		require_env DEMO_ORG_ID
		json=$(capture_inventory_baseline)
		;;
	stale_cards | summary)
		json=$(capture_card_scenario_baseline)
		;;
	*)
		die "unknown scenario: $SCENARIO (supported: inventory, stale_cards, summary)"
		;;
	esac

	write_baseline_fixture "$json"
}

main "$@"
