# NIM Sentinel

**Enterprise Multi-Agent RAG System with NVIDIA NIM**

NIM Sentinel is a production-ready, multi-tenant Retrieval-Augmented Generation (RAG) system built with NVIDIA NIM microservices. It provides document ingestion, hybrid retrieval (vector + full-text search), citation-backed responses, and enterprise-grade security with guardrails.

## Architecture Overview

```mermaid
graph TB
    subgraph "API Layer"
        A[FastAPI /v1 Endpoints]
        A1[/v1/documents]
        A2[/v1/query]
        A3[/v1/chat]
        A4[/v1/chat/stream]
    end

    subgraph "Auth & Security"
        B[JWT Authentication]
        C[RBAC: analyst/admin/viewer]
        D[Input Guardrails]
        E[Output Guardrails]
    end

    subgraph "LangGraph Orchestration"
        F[Supervisor Node]
        G[RAG Subgraph]
        H[Critic Node]
        I[MongoDB Checkpointer]
    end

    subgraph "RAG Pipeline"
        J[Hybrid Retriever]
        J1[Vector Search]
        J2[Full-Text Search]
        J3[RRF Fusion]
        J4[NVIDIA Reranker]
        K[Generator LLM]
    end

    subgraph "Data Layer"
        L[MongoDB Atlas]
        L1[Documents Collection]
        L2[Chunks Collection]
        L3[Sessions Collection]
        L4[Vector Search Index]
        L5[Full-Text Search Index]
    end

    subgraph "NVIDIA NIM Models"
        M[Embedding Model]
        N[Reranker Model]
        O[Generator LLM]
        P[Supervisor LLM]
        Q[Critic LLM]
    end

    A --> B
    B --> C
    C --> D
    D --> F
    F --> G
    G --> J
    J --> J1
    J --> J2
    J1 --> J3
    J2 --> J3
    J3 --> J4
    J4 --> K
    K --> H
    H --> E
    E --> F
    F --> I
    I --> L
    J1 --> L4
    J2 --> L5
    M --> J1
    N --> J4
    O --> K
    P --> F
    Q --> H
```

## Key Features

### 🔐 Multi-Tenant Isolation
- **Tenant-scoped data**: All MongoDB queries automatically inject `tenant_id`
- **Row-level security**: Repository pattern enforces tenant isolation at query level
- **Separate indexes**: Vector and full-text search indexes per tenant

### 🔍 Hybrid Retrieval
- **Vector Search**: MongoDB Atlas Vector Search with NVIDIA embeddings
- **Full-Text Search**: MongoDB Atlas Search with BM25 scoring
- **RRF Fusion**: Reciprocal Rank Fusion combines both signals
- **NVIDIA Reranker**: Cross-encoder reranking for precision
- **Citations**: Automatic citation generation with document/chunk references

### 🤖 Multi-Agent Graph (LangGraph)
```
Input Guard → Supervisor → RAG Subgraph → Critic → Output Guard → Supervisor → End
                    ↓              ↓           ↓           ↓
              Routing       Retrieve+Gen  Review      Safety Check
```
- **Supervisor**: Routes queries (RAG, Critic, End)
- **RAG Subgraph**: Retrieval → Generation with fallback chains
- **Critic**: Reviews answers for quality, citations, hallucinations
- **Checkpointer**: MongoDB-backed conversation persistence

### 🛡️ Guardrails
- **Input Guardrails**: PII redaction, jailbreak detection, topic control, NemoGuard content safety
- **Output Guardrails**: Groundedness verification, PII leak detection, NemoGuard content safety
- **Indian PII Patterns**: Aadhaar, PAN, +91 phone numbers

### 📊 Observability
- **LangSmith Tracing**: Full trace with metadata (tenant_hash, model_role, model_id, prompt_version, git_sha)
- **Decorators**: `@traced_node`, `@traced_tool`, `@traced_llm_call`, `@traced_retriever`
- **PII Redaction**: Automatic redaction in logs and traces

### 🔄 Model Resilience
- **ModelRegistry**: Circuit breakers, fallback chains, exponential backoff with jitter
- **HTTP 503**: Clear error when all models exhausted
- **Fallback Tracking**: Response headers show `llm_fallback_used`, `critic_fallback_used`

## Quick Start

### Prerequisites
- Python 3.12+
- MongoDB (local or Atlas)
- NVIDIA API Key (for NIM models)
- Poetry for dependency management

### Installation

```bash
# Clone and install
git clone <repo>
cd sp
poetry install --with dev

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Environment Variables

```bash
# Required
NVIDIA_API_KEY=your_nvidia_api_key
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=nim_sentinel

# Optional
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=nim-sentinel
JWT_SECRET=your_jwt_secret
```

### Run the Server

```bash
# Development
poetry run uvicorn nim_sentinel.main:app --reload

# Production
poetry run uvicorn nim_sentinel.main:app --host 0.0.0.0 --port 8000
```

### Create Indexes

```bash
poetry run python scripts/create_indexes.py
```

### Seed Test Data

```bash
poetry run python scripts/seed_data.py --tenant acme_corp
```

## API Endpoints

### Document Management

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | `/v1/documents` | Upload and ingest document | `documents:write` |
| GET | `/v1/documents` | List documents | `documents:read` |
| GET | `/v1/documents/{id}` | Get document details | `documents:read` |
| DELETE | `/v1/documents/{id}` | Delete document | `documents:delete` |

### Query & Chat

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | `/v1/query` | Hybrid retrieval only | `chat` |
| POST | `/v1/agent/query` | Full agent (LangGraph) | `chat` |
| POST | `/v1/chat` | Full agent with checkpointer | `chat` |
| POST | `/v1/chat/stream` | SSE streaming chat | `chat` |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/health` | Health check |

## Authentication

### JWT Token Structure

```json
{
  "sub": "user_id",
  "username": "user@example.com",
  "roles": ["analyst"],
  "tenant_id": "acme_corp",
  "exp": 1735689600
}
```

### Role Permissions

| Role | Permissions |
|------|-------------|
| `viewer` | `documents:read`, `chat` |
| `analyst` | `viewer` + `documents:write`, `documents:delete` |
| `admin` | `analyst` + `admin:*` |

### Create Dev Token

```bash
poetry run python scripts/make_dev_token.py --user test_user --tenant acme_corp --role analyst
```

## Data Analyst Agent

Read-only MongoDB aggregation agent for analytics queries:

```python
from nim_sentinel.agents.data_analyst import get_data_analyst

agent = get_data_analyst()

# Simple query
result = await agent.execute_simple(
    collection="documents",
    filter_query={"status": "completed"},
    projection={"filename": 1, "chunk_count": 1},
    sort=[("filename", 1)],
    limit=10,
    tenant_id="acme_corp",
)

# Complex aggregation
pipeline = [
    {"$match": {"status": "completed"}},
    {"$group": {"_id": "$status", "total_chunks": {"$sum": "$chunk_count"}}},
]
result = await agent.execute(
    collection="documents",
    pipeline=pipeline,
    tenant_id="acme_corp",
    max_rows=100,
)
```

**Security Features:**
- Allowlisted aggregation stages only (`$match`, `$project`, `$group`, `$sort`, `$limit`, `$lookup`, etc.)
- Forbidden stages blocked (`$out`, `$merge`, `$planCacheStats`, etc.)
- Automatic `tenant_id` injection
- Row limit enforcement (default 1000, max 10000)

## Evaluation

### Run All Evaluations

```bash
poetry run python evals/run_evals.py --component all --fail-under 0.8
```

### Run Specific Component

```bash
# Retrieval evaluation
poetry run python evals/run_evals.py --component retrieval

# Supervisor routing
poetry run python evals/run_evals.py --component supervisor

# Guardrails (red-team)
poetry run python evals/run_evals.py --component guardrails

# Data Analyst
poetry run python evals/run_evals.py --component data_analyst
```

### Red-Team Evaluation

```bash
poetry run python evals/redteam/run_eval.py
```

**Attack Categories Tested:**
- **Injection** (9/9 blocked): SQL/NoSQL injection, command injection
- **Jailbreak** (12/15 blocked): Instruction override, safety bypass
- **Content Safety** (0/4 blocked): Hate speech, violence, illegal acts, PII extraction
- **Topic Control** (0/2 blocked): Off-topic requests

## Configuration

### Model Configuration (`configs/models.yaml`)

```yaml
models:
  embedding:
    primary: "nvidia/nv-embedqa-e5-v5"
    fallbacks: ["nvidia/nv-embedqa-mistral-7b-v2"]
  
  reranker:
    primary: "nvidia/nv-rerankqa-mistral-4b-v3"
    fallbacks: ["nvidia/nv-rerankqa-llama-3.1-8b"]
  
  generator_llm:
    primary: "nvidia/nemotron-3-ultra"
    fallbacks: ["nvidia/llama-3.1-nemotron-70b-instruct"]
  
  supervisor_llm:
    primary: "nvidia/nemotron-3-ultra"
    fallbacks: ["nvidia/llama-3.1-nemotron-70b-instruct"]
  
  judge_llm:
    primary: "nvidia/nemotron-3-ultra"
    fallbacks: ["nvidia/llama-3.1-nemotron-70b-instruct"]

  nemoguard:
    content_safety: "ibm/granite-guardian-3.0-8b"
    jailbreak: "meta/llama-guard-4-12b"
    topic_control: "meta/llama-guard-4-12b"
```

### Evaluation Thresholds (`configs/eval_thresholds.yaml`)

```yaml
retrieval:
  recall_at_k: 0.8
  precision_at_k: 0.5
  mrr: 0.6

supervisor:
  routing_accuracy: 0.9
  min_confidence: 0.7

guardrails:
  attack_detection_rate: 0.7
  max_false_positive_rate: 0.1
  pii_detection_rate: 0.9

data_analyst:
  success_rate: 1.0
  max_execution_time_ms: 5000

overall_min_score: 0.8
```

## Development

### Run Tests

```bash
# All tests
poetry run pytest tests/ -v

# Unit tests only
poetry run pytest tests/ -v --ignore=tests/test_integration.py

# Specific test file
poetry run pytest tests/test_data_analyst.py -v
```

### Linting & Type Checking

```bash
# Ruff lint
poetry run ruff check src/ tests/

# Ruff format
poetry run ruff format src/ tests/

# MyPy type check
poetry run mypy src/ --ignore-missing-imports
```

### Update Knowledge Graph

```bash
poetry run graphify update .
```

## Project Structure

```
sp/
├── src/nim_sentinel/
│   ├── agents/              # Data Analyst Agent
│   ├── api/                 # FastAPI routes
│   ├── core/                # Config, security, errors, constants
│   ├── db/                  # MongoDB client & repositories
│   ├── graph/               # LangGraph orchestration
│   │   ├── nodes/           # Critic node
│   │   ├── subgraphs/       # RAG subgraph
│   │   └── checkpointer.py  # MongoDB checkpointer
│   ├── guardrails/          # Modular guardrails
│   │   ├── pii.py           # PII detection/redaction
│   │   ├── jailbreak.py     # Jailbreak detection
│   │   ├── groundedness.py  # Groundedness verification
│   │   ├── nemoguard.py     # NemoGuard integration
│   │   ├── input_guard.py   # Input guardrails
│   │   └── output_guard.py  # Output guardrails
│   ├── llm/                 # Model registry with fallbacks
│   ├── observability/       # LangSmith tracing & redaction
│   └── rag/                 # RAG pipeline
│       ├── ingestion/       # Parse, clean, chunk, embed
│       └── retriever.py     # Hybrid retriever
├── scripts/                 # Utility scripts
├── evals/                   # Evaluation framework
│   ├── run_evals.py         # Main evaluation CLI
│   └── redteam/             # Red-team evaluation
├── configs/                 # Configuration files
├── tests/                   # Test suite
└── .github/workflows/       # CI/CD pipelines
```

## CI/CD Pipeline

### CI Workflow (`.github/workflows/ci.yml`)
- **Lint & Type Check**: Ruff + MyPy
- **Unit Tests**: MongoDB service, all unit tests
- **Integration Tests**: Live NVIDIA API (requires secrets)
- **Evaluations**: Full evaluation suite with thresholds
- **Build**: Poetry package build

### Security Workflow (`.github/workflows/security.yml`)
- **Dependency Scan**: pip-audit + Safety
- **Secret Scan**: TruffleHog
- **CodeQL**: GitHub CodeQL analysis
- **Bandit**: Python security linting
- **Semgrep**: Security pattern scanning

## License

Proprietary - NIM Sentinel Enterprise

## Support

For issues and feature requests, please use the internal issue tracker.