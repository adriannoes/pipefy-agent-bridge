#!/usr/bin/env bash
# Apply repository ruleset from .github/rulesets/protect-main.json.
# Requires: gh CLI, repo admin access, and a public repo OR GitHub Pro (rulesets on private free repos are blocked).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RULESET_FILE="${ROOT}/.github/rulesets/protect-main.json"
REPO="${GITHUB_REPOSITORY:-adriannoes/pipefy-agent-bridge}"
RULESET_NAME="Protect main"

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh CLI is required" >&2
  exit 1
fi

if [[ ! -f "${RULESET_FILE}" ]]; then
  echo "error: missing ruleset file: ${RULESET_FILE}" >&2
  exit 1
fi

existing_id="$(
  gh api "repos/${REPO}/rulesets" --jq ".[] | select(.name==\"${RULESET_NAME}\") | .id" 2>/dev/null | head -n1 || true
)"

if [[ -n "${existing_id}" ]]; then
  echo "Updating ruleset id=${existing_id} on ${REPO}"
  gh api "repos/${REPO}/rulesets/${existing_id}" -X PUT --input "${RULESET_FILE}"
else
  echo "Creating ruleset on ${REPO}"
  gh api "repos/${REPO}/rulesets" -X POST --input "${RULESET_FILE}"
fi

echo "Done. Verify at: https://github.com/${REPO}/settings/rules"
