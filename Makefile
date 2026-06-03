# pipefy-agent-bridge — operator entrypoints (see docs/ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md §16.4)

.DEFAULT_GOAL := help

SCENARIO ?= inventory

# Pinned upstream: https://github.com/pipefy/ai-toolkit (never @latest)
PIPEFY_TOOLKIT_REF ?= v0.2.0-beta.2
# Make treats '#' as comment — use $(hash) for git subdirectory pins
hash := \#
PIPEFY_TOOLKIT_GIT := git+https://github.com/pipefy/ai-toolkit@$(PIPEFY_TOOLKIT_REF)
PIPEFY_SDK_WITH := pipefy-sdk @ $(PIPEFY_TOOLKIT_GIT)$(hash)subdirectory=packages/sdk
PIPEFY_AUTH_WITH := pipefy-auth @ $(PIPEFY_TOOLKIT_GIT)$(hash)subdirectory=packages/auth
PIPEFY_CLI_PKG := $(PIPEFY_TOOLKIT_GIT)$(hash)subdirectory=packages/cli
PIPEFY_MCP_PKG := $(PIPEFY_TOOLKIT_GIT)$(hash)subdirectory=packages/mcp

# Cursor SDK harness (verified in task 3.2)
CURSOR_SDK_VERSION ?= 0.1.6
PYTHON_DOTENV_VERSION ?= 1.2.2

# NVIDIA NAT harness (verified in task 4.3; react_agent requires langchain extra)
NVIDIA_NAT_VERSION ?= 1.7.0

.PHONY: help doctor install-pipefy-tools install-cursor-demo install-nat-demo demo-cursor demo-nat tour

define NOT_IMPL
	@echo "not implemented yet (task $(1))"
	@exit 1
endef

help:
	@echo "pipefy-agent-bridge — three-act tour"
	@echo ""
	@echo "  Act 1 — See the data:     Pipefy CLI (ground truth)"
	@echo "  Act 2 — Let Cursor drive: make demo-cursor  (Cursor SDK + Pipefy MCP)"
	@echo "  Act 3 — Let NVIDIA drive: make demo-nat     (NAT + NIM + Pipefy MCP)"
	@echo "  Encore — Same bridge:     make tour         (Acts 1–3 + eval/compare)"
	@echo ""
	@echo "Scenarios: inventory (default) | stale_cards | summary"
	@echo "  Override with: make demo-cursor SCENARIO=stale_cards"
	@echo ""
	@echo "Targets:"
	@echo "  help                  — this message (default)"
	@echo "  doctor                — preflight: binaries, env, read-only Pipefy ping"
	@echo "  install-pipefy-tools  — install pipefy CLI + pipefy-mcp-server @ pinned tag"
	@echo "  install-cursor-demo   — install cursor-sdk (+ python-dotenv)"
	@echo "  install-nat-demo      — install nvidia-nat[mcp,langchain] (react_agent)"
	@echo "  demo-cursor           — Cursor SDK harness (SCENARIO=$(SCENARIO))"
	@echo "  demo-nat              — NVIDIA NAT harness (SCENARIO=$(SCENARIO))"
	@echo "  tour                  — full operator tour + fact check (inventory)"

doctor:
	@test -f .env \
		|| { echo "error: .env missing — run: cp .env.example .env"; exit 1; }
	@set -a && . ./.env && set +a && ./scripts/doctor.sh

install-pipefy-tools:
	@echo "Installing pipefy CLI + pipefy-mcp-server from pipefy/ai-toolkit@$(PIPEFY_TOOLKIT_REF) ..."
	@command -v uv >/dev/null \
		|| { echo "error: uv not on PATH — install from https://docs.astral.sh/uv/"; exit 1; }
	uv tool install \
		--with "$(PIPEFY_SDK_WITH)" \
		--with "$(PIPEFY_AUTH_WITH)" \
		"$(PIPEFY_CLI_PKG)"
	uv tool install \
		--with "$(PIPEFY_SDK_WITH)" \
		--with "$(PIPEFY_AUTH_WITH)" \
		"$(PIPEFY_MCP_PKG)"
	@command -v pipefy >/dev/null \
		|| { echo "error: pipefy not on PATH after install (add \$$HOME/.local/bin to PATH)"; exit 1; }
	@command -v pipefy-mcp-server >/dev/null \
		|| { echo "error: pipefy-mcp-server not on PATH after install (add \$$HOME/.local/bin to PATH)"; exit 1; }
	@echo "Installed: $$(pipefy --version) ($$(command -v pipefy))"
	@echo "Installed: pipefy-mcp-server ($$(command -v pipefy-mcp-server))"

install-cursor-demo:
	@echo "Installing cursor-sdk ($(CURSOR_SDK_VERSION)) + python-dotenv ($(PYTHON_DOTENV_VERSION)) ..."
	@command -v uv >/dev/null \
		|| { echo "error: uv not on PATH — install from https://docs.astral.sh/uv/"; exit 1; }
	uv pip install \
		"cursor-sdk==$(CURSOR_SDK_VERSION)" \
		"python-dotenv==$(PYTHON_DOTENV_VERSION)"
	@uv run python -c "import cursor_sdk, dotenv"
	@echo "Installed: cursor-sdk $(CURSOR_SDK_VERSION), python-dotenv $(PYTHON_DOTENV_VERSION)"

install-nat-demo:
	@echo "Installing nvidia-nat[langchain,mcp]==$(NVIDIA_NAT_VERSION) ..."
	@command -v uv >/dev/null \
		|| { echo "error: uv not on PATH — install from https://docs.astral.sh/uv/"; exit 1; }
	uv pip install "nvidia-nat[langchain,mcp]==$(NVIDIA_NAT_VERSION)"
	@uv run nat --help >/dev/null
	@uv run nat info components -t function 2>/dev/null | grep -q react_agent \
		|| { echo "error: react_agent function not registered — check nvidia-nat[langchain] install"; exit 1; }
	@echo "Installed: nvidia-nat $(NVIDIA_NAT_VERSION) with langchain + mcp extras (react_agent ready)"

ensure-nat-demo:
	@uv run nat --help >/dev/null 2>&1 || $(MAKE) install-nat-demo

ensure-cursor-demo:
	@uv run python -c "import cursor_sdk, dotenv" >/dev/null 2>&1 || $(MAKE) install-cursor-demo

demo-cursor: ensure-cursor-demo
	@test -f .env \
		|| { echo "error: .env missing — run: cp .env.example .env"; exit 1; }
	@set -a && . ./.env && set +a \
		&& uv run python demos/01_cursor_pipefy_ops.py --scenario $(SCENARIO)

demo-nat: ensure-nat-demo
	@test -f .env \
		|| { echo "error: .env missing — run: cp .env.example .env"; exit 1; }
	@set -a && . ./.env && set +a \
		&& ./demos/02_nat_smoke.sh $(SCENARIO)

tour: ensure-nat-demo ensure-cursor-demo
	@test -f .env \
		|| { echo "error: .env missing — run: cp .env.example .env"; exit 1; }
	@set -a && . ./.env && set +a && ./scripts/tour.sh
