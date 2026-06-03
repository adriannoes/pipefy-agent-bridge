#!/bin/sh
# Full operator tour: Acts 1–3 + eval fact check (ARCHITECTURE §16.5, task 5.5).
# Expects .env loaded by the caller (e.g. make tour). Never prints secret values.

set -eu

REPO_ROOT="$(CDPATH= cd "$(dirname "$0")/.." && pwd)"
TOUR_SCENARIO=inventory
BASELINE_PATH="$REPO_ROOT/eval/fixtures/live/${TOUR_SCENARIO}.json"
CURSOR_ANSWER_PATH=
NAT_ANSWER_RAW_PATH=
NAT_ANSWER_PATH=
TOUR_TMPDIR=
TOUR_FAILURES=0

env_is_set() {
	eval "v=\${$1:-}"
	[ -n "$v" ]
}

ok() {
	printf '✓ %s\n' "$1"
}

warn() {
	printf '⚠ %s\n' "$1" >&2
}

fail() {
	printf '✗ %s\n' "$1"
	TOUR_FAILURES=$((TOUR_FAILURES + 1))
}

die() {
	printf 'error: %s\n' "$1" >&2
	exit 1
}

cleanup_tour_tmpdir() {
	if [ -n "${TOUR_KEEP_TMP:-}" ]; then
		printf 'tour artifacts kept at: %s\n' "$TOUR_TMPDIR" >&2
		return
	fi
	if [ -n "$TOUR_TMPDIR" ] && [ -d "$TOUR_TMPDIR" ]; then
		rm -rf "$TOUR_TMPDIR"
	fi
}

setup_tour_tmpdir() {
	TOUR_TMPDIR=$(mktemp -d "${TMPDIR:-/tmp}/pipefy-agent-bridge-tour.XXXXXX")
	trap cleanup_tour_tmpdir EXIT INT TERM
	CURSOR_ANSWER_PATH="$TOUR_TMPDIR/cursor_answer.txt"
	NAT_ANSWER_RAW_PATH="$TOUR_TMPDIR/nat_answer_raw.txt"
	NAT_ANSWER_PATH="$TOUR_TMPDIR/nat_answer.txt"
}

print_tour_intro() {
	printf 'pipefy-agent-bridge tour (scenario: %s)\n\n' "$TOUR_SCENARIO"
	printf 'This tour runs the CLI baseline plus two LLM harnesses (Cursor, NVIDIA NAT).\n'
	printf 'Expect several minutes when API keys are set; each demo calls a remote model.\n\n'
	printf 'Required: Pipefy service account (see make doctor).\n'
	printf 'Per act: CURSOR_API_KEY (Act 2), NVIDIA_API_KEY (Act 3).\n\n'
}

require_env_or_die() {
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

require_tour_llm_keys() {
	missing=
	if ! env_is_set CURSOR_API_KEY; then
		missing="${missing:+$missing, }CURSOR_API_KEY"
	fi
	if ! env_is_set NVIDIA_API_KEY; then
		missing="${missing:+$missing, }NVIDIA_API_KEY"
	fi
	if [ -n "$missing" ]; then
		die "cannot run full tour — missing: $missing (set in .env; run make doctor to verify)"
	fi
}

summarize_inventory_baseline() {
	if [ ! -f "$BASELINE_PATH" ]; then
		fail "baseline file missing: $BASELINE_PATH"
		return
	fi
	if ! summary=$(BASELINE_PATH="$BASELINE_PATH" python3 -c '
import json
import os
from pathlib import Path

path = Path(os.environ["BASELINE_PATH"])
data = json.loads(path.read_text(encoding="utf-8"))

def pipe_names(payload: object) -> list[str]:
    if isinstance(payload, list):
        pipes = payload
    elif isinstance(payload, dict):
        orgs = payload.get("organizations")
        if not isinstance(orgs, list):
            return []
        pipes = []
        for org in orgs:
            if isinstance(org, dict) and isinstance(org.get("pipes"), list):
                pipes.extend(org["pipes"])
    else:
        return []
    names: list[str] = []
    for pipe in pipes:
        if isinstance(pipe, dict):
            name = pipe.get("name")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
    return names

names = pipe_names(data)
preview = ", ".join(names[:5])
if len(names) > 5:
    preview = f"{preview} …"
print(f"baseline: {len(names)} pipe(s) — {preview}")
'); then
		fail "could not summarize baseline JSON at $BASELINE_PATH"
		return
	fi
	ok "$summary"
	if [ "${VERBOSE:-0}" = "1" ]; then
		printf '\n%s\n\n' "$(cat "$BASELINE_PATH")"
	fi
}

run_act1_ground_truth() {
	printf '=== Act 1: Pipefy CLI (ground truth) ===\n'
	"$REPO_ROOT/eval/ground_truth.sh" "$TOUR_SCENARIO"
	summarize_inventory_baseline
	printf '\n'
}

run_demo_cursor_once() {
	uv run python "$REPO_ROOT/demos/01_cursor_pipefy_ops.py" --scenario "$TOUR_SCENARIO" \
		>"$CURSOR_ANSWER_PATH"
}

run_act2_cursor() {
	printf '=== Act 2: Cursor SDK → Pipefy MCP ===\n'
	ok "ENV CURSOR_API_KEY: set"
	printf 'running demo-cursor (inventory) …\n'
	if run_demo_cursor_once; then
		ok "demo-cursor finished"
	else
		warn "demo-cursor failed; retrying once …"
		if run_demo_cursor_once; then
			ok "demo-cursor finished (after retry)"
		else
			fail "demo-cursor exited non-zero"
		fi
	fi
	if [ ! -s "$CURSOR_ANSWER_PATH" ]; then
		warn "demo-cursor produced empty stdout (fact check likely fails)"
	fi
	if [ "${VERBOSE:-0}" = "1" ]; then
		printf '\n--- cursor answer ---\n'
		cat "$CURSOR_ANSWER_PATH"
		printf '\n--- end cursor answer ---\n\n'
	fi
	printf '\n'
}

run_demo_nat_once() {
	# NAT logs agent steps on stderr; capture both streams for Final Answer extraction.
	"$REPO_ROOT/demos/02_nat_smoke.sh" "$TOUR_SCENARIO" >"$NAT_ANSWER_RAW_PATH" 2>&1
}

nat_answer_passes_compare() {
	[ -f "$BASELINE_PATH" ] && [ -s "$NAT_ANSWER_PATH" ] \
		&& uv run python "$REPO_ROOT/eval/compare.py" \
			--baseline "$BASELINE_PATH" \
			--answer "$NAT_ANSWER_PATH" >/dev/null 2>&1
}

run_act3_nat() {
	printf '=== Act 3: NVIDIA NAT + NIM → Pipefy MCP ===\n'
	ok "ENV NVIDIA_API_KEY: set"
	printf 'running demo-nat (inventory) …\n'
	attempt=1
	max_attempts=3
	nat_ok=0
	while [ "$attempt" -le "$max_attempts" ]; do
		if [ "$attempt" -gt 1 ]; then
			warn "demo-nat retry $attempt/$max_attempts …"
		fi
		if run_demo_nat_once; then
			finalize_nat_answer_for_compare
			if nat_answer_passes_compare; then
				if [ "$attempt" -eq 1 ]; then
					ok "demo-nat finished"
				else
					ok "demo-nat finished (attempt $attempt)"
				fi
				nat_ok=1
				break
			fi
			warn "demo-nat answer failed inventory fact check (attempt $attempt)"
		else
			warn "demo-nat exited non-zero (attempt $attempt)"
		fi
		attempt=$((attempt + 1))
	done
	if [ "$nat_ok" -eq 0 ]; then
		fail "demo-nat did not produce a passing inventory answer after $max_attempts attempts"
	fi
	if [ "${VERBOSE:-0}" = "1" ]; then
		printf '\n--- nat answer (extracted) ---\n'
		cat "$NAT_ANSWER_PATH"
		printf '\n--- end nat answer ---\n\n'
	fi
	printf '\n'
}

compare_answer() {
	label=$1
	answer_path=$2
	printf '%s: ' "$label"
	if [ ! -f "$answer_path" ]; then
		printf '✗\n'
		fail "$label — answer file missing"
		return
	fi
	if uv run python "$REPO_ROOT/eval/compare.py" \
		--baseline "$BASELINE_PATH" \
		--answer "$answer_path"; then
		return 0
	fi
	TOUR_FAILURES=$((TOUR_FAILURES + 1))
	return 1
}

finalize_nat_answer_for_compare() {
	uv run python "$REPO_ROOT/scripts/extract_nat_answer.py" "$NAT_ANSWER_RAW_PATH" >"$NAT_ANSWER_PATH" \
		|| fail "could not extract NAT Final Answer from demo-nat stdout"
}

run_encore_fact_check() {
	printf '=== Encore: fact check (eval/compare.py) ===\n'
	if [ ! -f "$BASELINE_PATH" ]; then
		die "baseline missing at $BASELINE_PATH — Act 1 must succeed first"
	fi
	compare_answer "inventory vs Cursor answer" "$CURSOR_ANSWER_PATH" || true
	compare_answer "inventory vs NAT answer" "$NAT_ANSWER_PATH" || true
	printf '\n'
}

main() {
	cd "$REPO_ROOT"
	setup_tour_tmpdir
	print_tour_intro

	require_env_or_die \
		PIPEFY_SERVICE_ACCOUNT_CLIENT_ID \
		PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET \
		DEMO_ORG_ID
	require_tour_llm_keys

	run_act1_ground_truth
	run_act2_cursor
	run_act3_nat
	run_encore_fact_check

	if [ "$TOUR_FAILURES" -gt 0 ]; then
		printf '%d tour step(s) failed.\n' "$TOUR_FAILURES" >&2
		exit 1
	fi
	printf 'Tour complete — all fact checks passed.\n'
}

main "$@"
