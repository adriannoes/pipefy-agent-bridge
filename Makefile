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

# Cursor SDK harness
CURSOR_SDK_VERSION ?= 0.1.6
PYTHON_DOTENV_VERSION ?= 1.2.2

# NVIDIA NAT harness (react_agent requires langchain extra)
NVIDIA_NAT_VERSION ?= 1.7.0

K ?= 5

.PHONY: help doctor install-pipefy-tools install-cursor-demo install-nat-demo ensure-nat-profiler demo-cursor demo-cloud demo-nat profile-nat tour eval similar

help:
	@echo "pipefy-agent-bridge — three-act tour"
	@echo ""
	@echo "  Act 1 — See the data:     Pipefy CLI (ground truth)"
	@echo "  Act 2 — Let Cursor drive: make demo-cursor  (Cursor SDK + Pipefy MCP, local)"
	@echo "  Act 2b — Cursor Cloud VM:  make demo-cloud  (same scenarios, hosted VM)"
	@echo "  Act 3 — Let NVIDIA drive: make demo-nat     (NAT + NIM + Pipefy MCP)"
	@echo "  Encore — Same bridge:     make tour         (Acts 1–3 + eval/compare)"
	@echo ""
	@echo "Scenarios: inventory (default) | stale_cards | summary"
	@echo "  Override with: make demo-cursor SCENARIO=stale_cards"
	@echo ""
	@echo "Cloud (demo-cloud): CLOUD_REPO_URL required in .env; CLOUD_STARTING_REF optional (default: main)"
	@echo ""
	@echo "Targets:"
	@echo "  help                  — this message (default)"
	@echo "  doctor                — preflight: binaries, env, read-only Pipefy ping"
	@echo "  install-pipefy-tools  — install pipefy CLI + pipefy-mcp-server @ pinned tag"
	@echo "  install-cursor-demo   — install cursor-sdk (+ python-dotenv)"
	@echo "  install-nat-demo      — install nvidia-nat[mcp,langchain] (react_agent)"
	@echo "  demo-cursor           — Cursor SDK harness, local (SCENARIO=$(SCENARIO))"
	@echo "  demo-cloud            — Cursor SDK harness, cloud VM (SCENARIO=$(SCENARIO))"
	@echo "  demo-nat              — NVIDIA NAT harness (SCENARIO=$(SCENARIO))"
	@echo "  profile-nat           — NAT eval + profiler → eval/profiles/ (operator-only)"
	@echo "  tour                  — full operator tour + fact check (inventory)"
	@echo "  eval                  — reliability runner (EVAL_ARGS=--help for flags)"
	@echo "  similar               — semantic top-k cards (QUERY=..., K=$(K); needs embeddings extra)"

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

ensure-nat-profiler:
	@uv run python -c "import importlib.metadata as m; m.version('nvidia-nat-profiler')" >/dev/null 2>&1 \
		|| uv pip install "nvidia-nat-profiler==$(NVIDIA_NAT_VERSION)"
	@echo "Profiler extra ready (nvidia-nat-profiler $(NVIDIA_NAT_VERSION))"

ensure-nat-demo:
	@uv run nat --help >/dev/null 2>&1 || $(MAKE) install-nat-demo

ensure-cursor-demo:
	@uv run python -c "import cursor_sdk, dotenv" >/dev/null 2>&1 || $(MAKE) install-cursor-demo

demo-cursor: ensure-cursor-demo
	@test -f .env \
		|| { echo "error: .env missing — run: cp .env.example .env"; exit 1; }
	@set -a && . ./.env && set +a \
		&& PYTHONPATH=. uv run python demos/01_cursor_pipefy_ops.py --scenario $(SCENARIO)

demo-cloud: ensure-cursor-demo
	@test -f .env \
		|| { echo "error: .env missing — run: cp .env.example .env"; exit 1; }
	@set -a && . ./.env && set +a \
		&& PYTHONPATH=. uv run python demos/03_cursor_cloud_ops.py --scenario $(SCENARIO)

demo-nat: ensure-nat-demo
	@test -f .env \
		|| { echo "error: .env missing — run: cp .env.example .env"; exit 1; }
	@set -a && . ./.env && set +a \
		&& ./demos/02_nat_smoke.sh $(SCENARIO)

profile-nat: ensure-nat-demo ensure-nat-profiler
	@test -f .env \
		|| { echo "error: .env missing — run: cp .env.example .env"; exit 1; }
	@set -a && . ./.env && set +a \
		&& ./eval/profile_nat.sh $(SCENARIO)

tour: ensure-nat-demo ensure-cursor-demo
	@test -f .env \
		|| { echo "error: .env missing — run: cp .env.example .env"; exit 1; }
	@set -a && . ./.env && set +a && ./scripts/tour.sh

# EVAL_ARGS: pass-through flags for eval/run_eval.py (e.g. --runs 5 --harness nat --model meta/llama-3.1-70b-instruct)
eval:
	@test -f .env \
		|| { echo "error: .env missing — run: cp .env.example .env"; exit 1; }
	@set -a && . ./.env && set +a \
		&& uv run python eval/run_eval.py $(EVAL_ARGS)

# Semantic search over DEMO_PIPE_ID (CPU default; EMBED_BACKEND=gpu opt-in)
similar:
	@test -n "$(QUERY)" \
		|| { echo 'error: QUERY is required, e.g. make similar QUERY="late invoice"'; exit 1; }
	@test -f .env \
		|| { echo "error: .env missing — run: cp .env.example .env"; exit 1; }
	@PYTHONPATH=. uv run --extra embeddings python -c "import faiss" 2>/dev/null \
		|| { echo "error: embeddings extra not installed — run: uv sync --extra embeddings"; exit 1; }
	@set -a && . ./.env && set +a \
		&& PYTHONPATH=. uv run --extra embeddings python -m embeddings.find_similar \
			--query "$(QUERY)" --k $(K)
