# Embeddings — semantic search over Pipefy cards

Optional module: fetch bounded card text via the `pipefy` CLI, embed (NIM or local CPU), index with **FAISS-CPU by default**, return top-k similar cards. **Read-only**; no org ids or secrets in this doc.

---

## Operator guide

### Prerequisites

1. **Core tour env** — copy `.env.example` to `.env` (gitignored). You need at least `PIPEFY_API_TOKEN`, `DEMO_PIPE_ID`, and for the default path `NVIDIA_API_KEY`.
2. **Dependencies** — install the optional embeddings extra (not required for lint-only CI):

```bash
uv sync --extra embeddings
```

Installs `faiss-cpu`, `numpy`, and `sentence-transformers` (local fallback only).

### NVIDIA embedding API key (tier note — mirrors D18)

| Concern | Detail |
|---------|--------|
| **Key** | `NVIDIA_API_KEY` in `.env` — same variable as NAT chat; embedding access is a **separate** entitlement on your NVIDIA account. |
| **Tier (D18 parallel)** | Chat models (`meta/llama-3.1-8b-instruct`, opt-in `70b`) do **not** prove embedding access. Confirm models at [build.nvidia.com](https://build.nvidia.com/) → Embeddings / NeMo Retriever. |
| **No embed tier** | Set `EMBED_PROVIDER=local` — uses `sentence-transformers/all-MiniLM-L6-v2` on CPU (384-dim); no NIM embedding call. |

### Configuration (env)

| Variable | Default | Purpose |
|----------|---------|---------|
| `EMBED_PROVIDER` | `nim` | `nim` = NIM HTTP API; `local` = sentence-transformers on CPU. |
| `EMBED_MODEL` | `nvidia/nv-embedqa-e5-v5` | NIM model id. Opt-in: `nvidia/nv-embed-v1`. |
| `EMBED_DIM` | *(derived)* | **1024** (e5-v5), **4096** (nv-embed-v1), **384** (local). Override only if needed. |
| `EMBED_BACKEND` | `cpu` | Index backend: `cpu` = FAISS-CPU (default); `gpu` = FAISS-GPU opt-in (extra install; see D16). |
| `CARD_TEXT_LIMIT` | `100` | Max cards ingested from the demo pipe (hard cap 100). |
| `EMBED_CACHE_DIR` | *(unset)* | Optional directory to cache passage embeddings + card metadata between runs. Invalidates when `pipe_id`, `CARD_TEXT_LIMIT`, or card text (`card_id`+`text`) changes; also when `EMBED_PROVIDER` / `EMBED_MODEL` changes. Query is embedded every run. Cache files are read-only metadata (no secrets). |
| `DEMO_PIPE_ID` | *(required)* | Demo pipe only — set in `.env`, never commit real ids here. |

Vectors are L2-normalized before indexing so cosine similarity matches dot product in `rank.py`.

### Run semantic search (CPU default)

```bash
# Loads .env; K defaults to 5
make similar QUERY="late invoice from vendor"

# Optional top-k
make similar QUERY="stale approval" K=10
```

Equivalent: `set -a && source .env && set +a && PYTHONPATH=. uv run --extra embeddings python -m embeddings.find_similar --query "..." --k 5`

**Output:** `card_id`, title snippet, similarity score (stdout).

**Cold start:** The first `make similar` in a fresh environment may be slow: NIM embeds every card plus the query over HTTP, or `EMBED_PROVIDER=local` downloads `sentence-transformers/all-MiniLM-L6-v2` on first use. Later runs reuse the loaded local model. Set `EMBED_CACHE_DIR` (e.g. `.cache/embeddings`, gitignored) to skip re-embedding unchanged card passages on subsequent runs; the query is still embedded each time.

**GPU index (opt-in):** `EMBED_BACKEND=gpu make similar QUERY="..."` — requires a GPU-enabled FAISS install; errors clearly if missing.

### `rank.py` vs FAISS (`index.py`)

| Path | Role |
|------|------|
| `embeddings/rank.py` | Pure cosine top-k over in-memory vectors — offline reference, no FAISS import. |
| `embeddings/index.py` | Production operator path: FAISS `IndexFlatIP` on L2-normalized rows (CPU default). |
| `tests/test_rank_faiss_parity.py` | CI guard: same top-k order and scores for `rank.top_k` and `index.query` on synthetic data. |

`find_similar.py` uses **FAISS** end-to-end; do not swap the CPU default to `rank.top_k` without reopening D16.

### Card cap

At most **100** cards are fetched from `DEMO_PIPE_ID` per run (`DEFAULT_CARD_TEXT_LIMIT` in `embeddings/card_text.py`). Title + description are normalized into one `text` field per card via `pipefy card list`. Override with `CARD_TEXT_LIMIT` (still clamped to 100).

### Offline tests (no API key)

```bash
uv run pytest tests/test_rank.py tests/test_card_text.py tests/test_embed_index.py \
  tests/test_embed.py tests/test_rank_faiss_parity.py tests/test_find_similar.py \
  tests/test_passage_cache.py -v
```

---

## Embedding model selection

**Date:** 2026-06-04  
**Operator probe:** one live call per candidate with `NVIDIA_API_KEY` against `POST https://integrate.api.nvidia.com/v1/embeddings` (OpenAI-compatible NIM API).

### NIM embedding tier

| Model | Result | Vector dim | Notes |
|-------|--------|------------|--------|
| `nvidia/nv-embedqa-e5-v5` | **OK** | **1024** | Retrieval-oriented; requires `input_type`: `passage` when indexing card text, `query` when embedding the user query. **Default.** |
| `nvidia/nv-embed-v1` | **OK** | **4096** | Generalist embed model; no `input_type`. **Opt-in** when the operator wants higher-dimensional vectors and tier allows. |
| `nvidia/nv-embedqa-mistral-7b-v2` | 404 | — | Not enabled on this account tier. |
| `nvidia/embed-qa-4` | 404 | — | Not enabled on this account tier. |

**Conclusion:** NIM is the default path; **local CPU fallback** documented for keys without embedding models (same pattern as D18: 8b default, 70b opt-in).

### Local CPU fallback (no NIM embedding tier)

| Setting | Value |
|---------|--------|
| `EMBED_PROVIDER` | `local` |
| `EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` |
| `EMBED_DIM` | **384** |

### Sample probe (operator)

```bash
set -a && source .env && set +a
curl -sS "https://integrate.api.nvidia.com/v1/embeddings" \
  -H "Authorization: Bearer ${NVIDIA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"nvidia/nv-embedqa-e5-v5","input":["late invoice from vendor X"],"input_type":"query"}' \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(len(d["data"][0]["embedding"]))'
# Expected: 1024
```

### Module map

| Module | Role |
|--------|------|
| `embeddings/card_text.py` | Bounded `{card_id, text}` from CLI |
| `embeddings/embed.py` | `embed_texts()` — NIM or local; `input_type` for e5-v5 |
| `embeddings/index.py` | `build_index` / `query` — FAISS-CPU default, `EMBED_BACKEND=gpu` opt-in |
| `embeddings/rank.py` | Pure cosine top-k (offline-testable) |
| `embeddings/find_similar.py` | Operator pipeline + CLI |
| `embeddings/passage_cache.py` | Optional `EMBED_CACHE_DIR` passage vector cache |

**Decisions:** D16 resolved — CPU FAISS default, GPU opt-in ([`docs/OPEN_DECISIONS.md`](../docs/OPEN_DECISIONS.md)).
