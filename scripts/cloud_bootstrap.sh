#!/usr/bin/env bash
# Idempotent cloud VM bootstrap: install pipefy-mcp-server on PATH.
# Invoked from .cursor/environment.json "install" on every cloud agent boot.
# Mirrors make install-pipefy-tools (pipefy/ai-toolkit @ pinned tag via uv tool install).

set -euo pipefail

PIPEFY_TOOLKIT_REF="${PIPEFY_TOOLKIT_REF:-v0.2.0-beta.2}"
PIPEFY_TOOLKIT_GIT="git+https://github.com/pipefy/ai-toolkit@${PIPEFY_TOOLKIT_REF}"
PIPEFY_SDK_WITH="pipefy-sdk @ ${PIPEFY_TOOLKIT_GIT}#subdirectory=packages/sdk"
PIPEFY_AUTH_WITH="pipefy-auth @ ${PIPEFY_TOOLKIT_GIT}#subdirectory=packages/auth"
PIPEFY_MCP_PKG="${PIPEFY_TOOLKIT_GIT}#subdirectory=packages/mcp"

export PATH="${HOME}/.local/bin:${PATH}"

ensure_uv() {
	if command -v uv >/dev/null 2>&1; then
		return 0
	fi
	echo "cloud_bootstrap: installing uv ..."
	curl -LsSf https://astral.sh/uv/install.sh | sh
	export PATH="${HOME}/.local/bin:${PATH}"
}

ensure_uv

echo "cloud_bootstrap: installing pipefy-mcp-server @ ${PIPEFY_TOOLKIT_REF} ..."
uv tool install \
	--with "${PIPEFY_SDK_WITH}" \
	--with "${PIPEFY_AUTH_WITH}" \
	"${PIPEFY_MCP_PKG}"

if ! command -v pipefy-mcp-server >/dev/null 2>&1; then
	echo "error: pipefy-mcp-server not on PATH after install (expected ${HOME}/.local/bin)" >&2
	exit 1
fi

echo "cloud_bootstrap: ok — $(command -v pipefy-mcp-server)"
