#!/bin/sh
# Operator-only: run NAT eval with profiler enabled and bundle JSON under eval/profiles/.
# Requires: .env (NVIDIA_API_KEY, Pipefy creds, DEMO_ORG_ID), make install-nat-demo, nvidia-nat-profiler.
# Example: make profile-nat
#          make profile-nat SCENARIO=inventory NIM_MODEL=meta/llama-3.1-70b-instruct

set -eu

REPO_ROOT="$(CDPATH= cd "$(dirname "$0")/.." && pwd)"
SCENARIO=${1:-inventory}
NAT_PROFILE_CONFIG=${NAT_PROFILE_CONFIG:-configs/pipefy_nat_workflow_profile.yml}
PROFILES_DIR="$REPO_ROOT/eval/profiles"

die() {
	printf 'error: %s\n' "$1" >&2
	exit 1
}

load_repo_env() {
	if [ ! -f "$REPO_ROOT/.env" ]; then
		die ".env missing — run: cp .env.example .env"
	fi
	# shellcheck disable=SC1091
	set -a
	. "$REPO_ROOT/.env"
	set +a
}

ensure_profiler_extra() {
	if ! uv run python -c "import importlib.metadata as m; m.version('nvidia-nat-profiler')" >/dev/null 2>&1; then
		printf 'Installing nvidia-nat-profiler (opt-in profiling extra)...\n'
		uv pip install "nvidia-nat-profiler==${NVIDIA_NAT_VERSION:-1.7.0}"
	fi
}

main() {
	cd "$REPO_ROOT"
	load_repo_env
	ensure_profiler_extra

	case "$SCENARIO" in
	inventory) ;;
	*) die "only inventory is supported for profiling (got: $SCENARIO)" ;;
	esac

	for name in NVIDIA_API_KEY PIPEFY_SERVICE_ACCOUNT_CLIENT_ID PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET DEMO_ORG_ID; do
		eval "v=\${$name:-}"
		[ -n "$v" ] || die "missing $name in .env"
	done

	if ! command -v uv >/dev/null 2>&1; then
		die "uv not on PATH"
	fi
	if ! command -v pipefy-mcp-server >/dev/null 2>&1; then
		die "pipefy-mcp-server not on PATH — run: make install-pipefy-tools"
	fi

	config_path="$REPO_ROOT/$NAT_PROFILE_CONFIG"
	[ -f "$config_path" ] || die "NAT profile config not found: $config_path"

	TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
	RUN_DIR="$PROFILES_DIR/.runs/$TIMESTAMP"
	DATASET_PATH="$RUN_DIR/dataset.json"
	BUNDLE_PATH="$PROFILES_DIR/$TIMESTAMP.json"
	mkdir -p "$RUN_DIR"

	uv run python "$REPO_ROOT/eval/nat_inventory_eval_prompt.py" \
		--write-dataset "$DATASET_PATH" \
		--demo-org-id "$DEMO_ORG_ID"

	nim_model=${NIM_MODEL:-meta/llama-3.1-8b-instruct}

	printf '=== NAT profiler: %s ===\n' "$SCENARIO"
	printf 'config:  %s\n' "$NAT_PROFILE_CONFIG"
	printf 'run_dir: %s\n' "$RUN_DIR"
	printf 'bundle:  %s\n' "$BUNDLE_PATH"
	printf 'model:   %s\n\n' "$nim_model"

	set +e
	uv run nat eval \
		--config_file "$NAT_PROFILE_CONFIG" \
		--override eval.general.output_dir "$RUN_DIR" \
		--override eval.general.dataset.file_path "$DATASET_PATH" \
		--override "llms.nim_llm.model_name" "$nim_model" >"$RUN_DIR/nat_eval.log" 2>&1
	nat_status=$?
	set -e
	cat "$RUN_DIR/nat_eval.log"
	if [ "$nat_status" -ne 0 ]; then
		exit "$nat_status"
	fi

	bundle_status=0
	uv run python "$REPO_ROOT/eval/bundle_nat_profile.py" \
		--run-dir "$RUN_DIR" \
		--out "$BUNDLE_PATH" \
		--scenario "$SCENARIO" \
		--workflow-config "$NAT_PROFILE_CONFIG" \
		--model "$nim_model" \
		--organization-id "$DEMO_ORG_ID" || bundle_status=$?

	if [ "$bundle_status" -ne 0 ]; then
		die "profiler bundle failed (see $RUN_DIR)"
	fi

	printf '\nProfiler bundle: %s\n' "$BUNDLE_PATH"
	printf 'Raw NAT output:  %s\n' "$RUN_DIR"
}

main "$@"
