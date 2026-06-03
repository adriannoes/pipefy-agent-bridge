#!/bin/sh
# NAT smoke harness: run a fixed scenario prompt via `nat run` + Pipefy MCP (stdio).
# Example: ./demos/02_nat_smoke.sh inventory

set -eu

REPO_ROOT="$(CDPATH= cd "$(dirname "$0")/.." && pwd)"
PROMPTS_DIR="$REPO_ROOT/demos/prompts"
DEFAULT_SCENARIO=inventory
DEFAULT_NAT_CONFIG=configs/pipefy_nat_workflow.yml

SCENARIO=${1:-$DEFAULT_SCENARIO}
NAT_CONFIG_FILE=${NAT_CONFIG_FILE:-$DEFAULT_NAT_CONFIG}

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

load_scenario_prompt() {
	prompt_file="$PROMPTS_DIR/${SCENARIO}.txt"
	if [ ! -f "$prompt_file" ]; then
		die "prompt file not found: $prompt_file"
	fi
	prompt=$(tr -d '\r' <"$prompt_file")
	prompt=$(printf '%s' "$prompt" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
	if [ -z "$prompt" ]; then
		die "prompt file is empty: $prompt_file"
	fi
	printf '%s' "$prompt"
}

# Prefer org/pipe ids from Act 1 baseline (correct) over DEMO_ORG_ID when they differ.
inventory_org_id_for_prompt() {
	baseline_path="$REPO_ROOT/eval/fixtures/live/inventory.json"
	if [ -f "$baseline_path" ]; then
		resolved=$(uv run python -c "
import json
from pathlib import Path
data = json.loads(Path('$baseline_path').read_text(encoding='utf-8'))
orgs = data.get('organizations') or []
if orgs and isinstance(orgs[0], dict) and orgs[0].get('id') is not None:
    print(str(orgs[0]['id']).strip())
" 2>/dev/null || true)
		if [ -n "$resolved" ]; then
			printf '%s' "$resolved"
			return 0
		fi
	fi
	printf '%s' "$DEMO_ORG_ID"
}

# Inventory: bake org id + concrete pipe_id examples into nat input for 8b tool args.
append_inventory_nat_hints() {
	base_prompt=$1
	org_id=$2
	pipe_hints=
	baseline_path="$REPO_ROOT/eval/fixtures/live/inventory.json"
	if [ -f "$baseline_path" ]; then
		pipe_hints=$(uv run python -c "
import json
from pathlib import Path
data = json.loads(Path('$baseline_path').read_text(encoding='utf-8'))
pipes = (data.get('organizations') or [{}])[0].get('pipes') or []
ids = [str(p['id']) for p in pipes if isinstance(p, dict) and p.get('id')]
if ids:
    print('get_cards once per pipe_id (first=50): ' + ', '.join(ids))
" 2>/dev/null || true)
	fi
	printf '%s\n\nPipefy MCP (inventory):\n- search_pipes once: organization_id integer %s, max_pipes_per_org 500. Do not pass pipe_name.\n- get_cards: pipe_id must be the numeric id string only (never English placeholders).\n%s\n- Reply with one line per pipe (Name → N open cards) after all get_cards calls.' \
		"$base_prompt" "$org_id" "${pipe_hints:-  - Use each id field from the search_pipes pipes array.}"
}

resolve_inventory_prompt() {
	base_prompt=$1
	org_id=$(inventory_org_id_for_prompt)
	append_inventory_nat_hints "$base_prompt" "$org_id"
}

# True when MCP tool output shows a non-empty pipes list (search_pipes succeeded).
nat_log_has_pipe_evidence() {
	log=$1
	if grep -qE '"pipes"\s*:\s*\[\s*\{' "$log"; then
		return 0
	fi
	if grep -qE '"pipesCount"\s*:\s*[1-9]' "$log"; then
		return 0
	fi
	return 1
}

main() {
	load_repo_env

	require_env \
		NVIDIA_API_KEY \
		PIPEFY_SERVICE_ACCOUNT_CLIENT_ID \
		PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET

	case "$SCENARIO" in
	inventory) require_env DEMO_ORG_ID ;;
	esac

	if ! command -v uv >/dev/null 2>&1; then
		die "uv not on PATH — install from https://docs.astral.sh/uv/"
	fi

	if ! command -v pipefy-mcp-server >/dev/null 2>&1; then
		die "pipefy-mcp-server not on PATH — run: make install-pipefy-tools"
	fi

	config_path="$REPO_ROOT/$NAT_CONFIG_FILE"
	if [ ! -f "$config_path" ]; then
		die "NAT config not found: $config_path"
	fi

	prompt=$(load_scenario_prompt)
	if [ "$SCENARIO" = "inventory" ]; then
		prompt=$(resolve_inventory_prompt "$prompt")
	fi
	prompt_rel="demos/prompts/${SCENARIO}.txt"

	printf '=== Act 3: NVIDIA NAT + NIM → Pipefy MCP ===\n'
	printf 'scenario: %s\n' "$SCENARIO"
	printf 'config:   %s\n' "$NAT_CONFIG_FILE"
	printf 'prompt:   %s\n' "$prompt_rel"
	printf '\n=== nat run ===\n'

	cd "$REPO_ROOT"
	# BSD mktemp requires XXXXXX at end of basename (no ".log" suffix after Xs).
	nat_log=$(mktemp "${TMPDIR:-/tmp}/nat-smoke.XXXXXX")
	trap 'rm -f "$nat_log"' EXIT INT TERM

	nim_model=${NIM_MODEL:-meta/llama-3.1-8b-instruct}

	set +e
	uv run nat run \
		--config_file "$NAT_CONFIG_FILE" \
		--input "$prompt" \
		--override "llms.nim_llm.model_name" "$nim_model" >"$nat_log" 2>&1
	nat_status=$?
	set -e

	cat "$nat_log"

	if [ "$nat_status" -ne 0 ]; then
		exit "$nat_status"
	fi
	if grep -Eq \
		'ReAct Agent failed|Failed to initialize workflow|Recursion limit of|GRAPH_RECURSION_LIMIT|GraphRecursionError|ToolException|Error executing tool|Invalid Format:' \
		"$nat_log"; then
		die "nat run reported agent/workflow failure (see log above)"
	fi
	extracted_answer=$(uv run python "$REPO_ROOT/scripts/extract_nat_answer.py" "$nat_log")
	if [ -z "$extracted_answer" ]; then
		die "nat run produced no extractable inventory answer (missing Final Answer / Workflow Result prose)"
	fi
	inventory_pipe_count=$(printf '%s' "$extracted_answer" | uv run python -c "
import re, sys
text = sys.stdin.read().replace('\\\\n', '\n')
lines = len(re.findall(r'.+→.+open cards', text, re.IGNORECASE))
lines += len(re.findall(r'.+->.+open cards', text, re.IGNORECASE))
arrows = text.count('→') + text.count('->')
print(max(lines, arrows))
")
	if [ "$inventory_pipe_count" -lt 3 ]; then
		die "nat extracted answer lists $inventory_pipe_count pipe(s); need at least 3 (Name → N open cards)"
	fi
	if printf '%s' "$extracted_answer" | grep -qiE 'no pipes found|found no pipes|there are no pipes'; then
		if nat_log_has_pipe_evidence "$nat_log"; then
			die "nat Final Answer claims no pipes but search_pipes returned pipes (check tool args)"
		else
			die "nat Final Answer incorrectly claims no pipes (check search_pipes inputs)"
		fi
	fi
	if [ "$SCENARIO" = "inventory" ]; then
		baseline_path="$REPO_ROOT/eval/fixtures/live/inventory.json"
		if [ ! -f "$baseline_path" ]; then
			die "missing $baseline_path — run: ./eval/ground_truth.sh inventory"
		fi
		extracted_file=$(mktemp "${TMPDIR:-/tmp}/nat-extracted.XXXXXX")
		printf '%s' "$extracted_answer" >"$extracted_file"
		if ! uv run python "$REPO_ROOT/eval/compare.py" \
			--baseline "$baseline_path" \
			--answer "$extracted_file" >/dev/null; then
			rm -f "$extracted_file"
			die "nat Final Answer failed inventory fact check (eval/compare.py)"
		fi
		rm -f "$extracted_file"
	fi
}

main "$@"
