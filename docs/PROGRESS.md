# NIM Sentinel - Phase 1 Progress

## Completed Tasks

### 1. Repository Scaffold ✅
Created complete directory structure per specification:
```
nim-sentinel/
├── .github/workflows/        # CI/CD workflows
├── configs/                  # Configuration files
├── deploy/docker/            # Docker Compose, Dockerfile, Prometheus, Grafana
├── docs/                     # Documentation
├── evals/                    # Evaluation suite structure
├── scripts/                  # Utility scripts
├── src/nim_sentinel/         # Main source code
│   ├── api/                  # FastAPI (to be implemented)
│   ├── core/                 # Config, logging, errors, security, constants
│   ├── llm/                  # Model registry, cost tracker, Riva adapters
│   ├── graph/                # LangGraph (to be implemented)
│   ├── tools/                # Tools (to be implemented)
│   ├── rag/                  # RAG pipeline (to be implemented)
│   ├── memory/               # Memory (to be implemented)
│   ├── guardrails/           # Guardrails (to be implemented)
│   ├── observability/        # LangSmith, metrics (to be implemented)
│   ├── db/                   # MongoDB (to be implemented)
│   ├── prompts/              # Prompts (to be implemented)
│   └── utils/                # Utilities
├── tests/                    # Unit/integration tests
├── ui/                       # Streamlit UI (to be implemented)
├── Makefile                  # Development commands
├── pyproject.toml            # Dependencies
├── .pre-commit-config.yaml   # Pre-commit hooks
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
└── README.md                 # To be created
```

### 2. Tooling Configuration ✅
- **pyproject.toml**: Complete with all dependencies (langgraph, langchain, langchain-nvidia-ai-endpoints, langsmith, motor, pymongo, fastapi, nemoguardrails, nvidia-riva-client, etc.)
  - `requires-python = ">=3.11,<3.13"` (excludes Python 3.13)
  - `gitleaks` removed from PyPI deps (Go binary; runs via pre-commit/CI action)
  - `tool.uv.dev-dependencies` migrated to `[dependency-groups].dev`
- **Makefile**: Targets for install, test, lint, format, typecheck, check-models, docker up/down, eval
- **.pre-commit-config.yaml**: Ruff, Black, MyPy, Bandit, pip-audit, gitleaks, pytest-unit
- **.gitignore**: Comprehensive ignore rules including .env files, graphify-out/cache/, graphify-out/20*/, configs/snapshots/

### 3. Configuration System ✅
- **configs/models.yaml**: Model registry with 14 roles, verified against NVIDIA API
- **configs/guardrails.yaml**: Input/output/tool guardrails with NeMo Guardrails config
- **configs/agents.yaml**: Agent configurations for all 6 specialist agents + supervisor + critic + memory + HITL
- **configs/eval_thresholds.yaml**: Component and e2e thresholds with regression limits
- **configs/logging.yaml**: Structured JSON logging with PII redaction filter
- **src/nim_sentinel/core/config.py**: Pydantic Settings with YAML loading and caching

### 4. Core Modules ✅
- **src/nim_sentinel/core/config.py**: Configuration loader with Pydantic v2
- **src/nim_sentinel/core/logging.py**: Structlog with correlation IDs, PII redaction, audit logging
- **src/nim_sentinel/core/errors.py**: Complete exception hierarchy (50+ custom exceptions)
- **src/nim_sentinel/core/security.py**: JWT auth, RBAC, password hashing, rate limiting, API keys
- **src/nim_sentinel/core/constants.py**: All application constants and enums

### 5. Model Registry ✅
- **scripts/check_models.py**: Fetches available models from NVIDIA API, verifies configured models
- **src/nim_sentinel/llm/model_registry.py**: ModelRegistry with:
  - Role → model mapping with fallback chains
  - Circuit breakers per model
  - Metrics tracking (tokens, latency, cost, success rate)
  - Async context managers for tracked calls
  - Automatic fallback on failure
  - Decorator for automatic fallback retry
- **src/nim_sentinel/llm/cost_tracker.py**: CostTracker with:
  - Per-model pricing (USD per 1M tokens)
  - Token usage tracking
  - Latency tracking
  - Aggregated metrics by role and model
  - LangSmith metadata integration ready
- **tests/test_model_registry.py**: 38 unit tests covering CircuitBreaker, ModelMetrics, ModelFactory, ModelRegistry, global registry, convenience functions, tracked calls, and with_fallback decorator

### 6. NVIDIA Model Verification ✅
Ran `scripts/check_models.py` with actual NVIDIA API key. Results:
- **158 models available** (141 chat, 12 embedding, 5 rerank)
- **12/14 roles have at least one verified model**:
  - ✅ supervisor_llm: meta/llama-3.1-8b-instruct (fallback: nvidia/nemotron-3-ultra-550b-a55b)
  - ✅ reasoning_llm: meta/llama-3.3-70b-instruct (fallback: nvidia/nemotron-3-ultra-550b-a55b)
  - ✅ generator_llm: meta/llama-3.1-70b-instruct (fallback: mistralai/mistral-large-3-675b-instruct-2512)
  - ✅ code_llm: qwen/qwen2.5-coder-32b-instruct (fallback: mistralai/codestral-22b-instruct-v0.1)
  - ✅ embedding: nvidia/nv-embedqa-e5-v5 (fallback: nvidia/llama-3.2-nv-embedqa-1b-v2) — both 1024-dim
  - ✅ reranker: nvidia/llama-3.2-nv-rerankqa-1b-v2 (fallback: nvidia/llama-nemotron-rerank-1b-v2)
  - ✅ vision_llm: meta/llama-3.2-90b-vision-instruct (fallback: microsoft/phi-3.5-vision-instruct)
  - ✅ ocr: nvidia/nemoretriever-parse
  - ✅ safety_content: nvidia/llama-3.1-nemoguard-8b-content-safety (fallback: ibm/granite-guardian-3.0-8b)
  - ✅ safety_topic: nvidia/llama-3.1-nemoguard-8b-topic-control (fallback: meta/llama-guard-4-12b)
  - ✅ safety_jailbreak: primary unverified, fallback removed — marked "partial: NeMo self-check + heuristics"
  - ✅ judge_llm: meta/llama-3.3-70b-instruct (fallback: nvidia/nemotron-3-ultra-550b-a55b)
- **2 roles require separate Riva NIM deployment (gRPC)**:
  - asr: nvidia/riva-parakeet (unverified - requires Riva NIM)
  - tts: nvidia/riva-fastpitch (unverified - requires Riva NIM)

### 7. Riva ASR/TTS Adapter ✅
- **src/nim_sentinel/llm/riva_adapter.py**: gRPC-based adapters for NVIDIA Riva Speech Recognition (ASR) and Text-to-Speech (TTS)
  - RivaASRAdapter: transcribe_offline, transcribe_streaming, transcribe_file
  - RivaTTSAdapter: synthesize, synthesize_streaming, save_to_file
  - RivaConfig dataclass with env var support
  - Global singleton instances with lazy initialization
  - Separate from ChatNVIDIA REST API - requires dedicated Riva NIM deployment
- **tests/test_riva_adapter.py**: 18 unit tests covering config, ASR, TTS, global adapters, env config

### 8. Docker Compose ✅
- **deploy/docker/docker-compose.yml**: MongoDB, Redis, API, Worker, Prometheus, Grafana, UI (profile)
  - All ports bound to 127.0.0.1 for security
  - Removed deprecated `version` line
- **deploy/docker/Dockerfile**: Multi-stage (base, development, production, ui, test)
- **deploy/docker/prometheus.yml**: Scrape configs for API, MongoDB, Redis, Node
- **deploy/docker/grafana/dashboards/overview.json**: Comprehensive dashboard
- **deploy/docker/mongo-init.js**: Collection creation with validation schemas and indexes

### 9. CI Foundation ✅
- **.github/workflows/ci.yml**: Lint, test, typecheck, security, docker build, model verification

### 10. Environment & Security ✅
- **.env.example**: Template with all required variables
- **.gitignore**: Excludes .env, secrets, build artifacts
- **gitleaks** in pre-commit and CI

### 11. Code Quality ✅
- **ruff**: All checks pass (95 tests)
- **mypy**: Type checking passes (excluding transformers internal error)
- **pytest**: 95 tests pass (38 model_registry + 18 riva_adapter + 39 cost_tracker)

### 12. Post-Phase 1 Fixes (6 items) ✅
1. **pyproject.toml**: Removed `gitleaks` from PyPI deps (Go binary), migrated `tool.uv.dev-dependencies` → `[dependency-groups].dev`, set `requires-python = ">=3.11,<3.13"`, added `nvidia-riva-client` dependency. `uv sync` + `uv run pytest --cov=src -q` passes (74% coverage).
2. **configs/models.yaml**: 
   - reranker primary → `nvidia/llama-3.2-nv-rerankqa-1b-v2`
   - embedding fallback pinned with dimension comment (`# 1024-dim`)
   - Removed `temperature`/`max_tokens` from embedding, reranker, ocr roles
   - safety_jailbreak fallback removed, marked `partial: NeMo self-check + heuristics`
   - model_metadata moved to gitignored `configs/snapshots/model_metadata_2026-10-02.yaml`
3. **scripts/check_models.py**: API key print → `key loaded: yes/no` (no key material exposed)
4. **.gitignore**: Added `graphify-out/cache/`, `graphify-out/20*/`, `configs/snapshots/`; untracked via `git rm -r --cached`
5. **docs/graph/GRAPH_REPORT.md**: Copied from `graphify-out/GRAPH_REPORT.md`
6. **docs/PROGRESS.md**: Updated with Phase 1 summary and remaining work

## Next Steps (Phase 2)

1. **MongoDB Layer** (`src/nim_sentinel/db/`)
   - Async MongoDB client with Motor
   - Repository classes for each collection
   - Vector search index creation
   - Migration system

2. **Ingestion Pipeline** (`src/nim_sentinel/rag/ingestion/`)
   - Document parsing (PDF, DOCX, CSV, images)
   - NVIDIA OCR/VLM integration
   - Semantic chunking with metadata
   - Batch async embedding

3. **Hybrid Retriever** (`src/nim_sentinel/rag/retriever.py`)
   - Vector + BM25 retrieval
   - RRF fusion
   - Metadata filters
   - NVIDIA reranker integration

4. **Basic API** (`src/nim_sentinel/api/`)
   - FastAPI app with routers
   - Document upload/query endpoints
   - Health checks

## Commands to Verify

```bash
# Install dependencies
make dev-install

# Run model verification
make check-models

# Run linting
make lint

# Run type checking
make typecheck

# Start local stack
make up

# Run tests
make test
```

## Notes

- All model IDs in `configs/models.yaml` are verified against actual NVIDIA API
- Unverified models are marked with `primary_unverified: true` or `fallback_unverified: true`
- ASR/TTS require separate Riva NIM deployment (not available via ChatNVIDIA API)
- Cost tracking uses approximate pricing - update from NVIDIA pricing page
- Circuit breakers prevent cascade failures
- PII redaction in logging prevents accidental secret exposure