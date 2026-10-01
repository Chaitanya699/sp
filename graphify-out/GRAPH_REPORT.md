# Graph Report - sp  (2026-10-02)

## Corpus Check
- 30 files · ~32,886 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 4, .graphify-bak 1)

## Summary
- 744 nodes · 1303 edges · 57 communities (50 shown, 7 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 105 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7a4f2e1a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- CostTracker
- logging.py
- core/__init__.py
- === PROMPT START ===
- config.py
- What You Must Do When Invoked
- RivaASRAdapter
- CircuitBreaker
- .__init__
- get_riva_asr
- check_models.py
- constants.py
- TestModelRegistry
- ModelUnavailableError
- Completed Tasks
- Any
- ModelMetrics
- DatabaseError
- patch
- with_fallback
- NIMException
- RivaTTSAdapter
- ModelRole
- GuardrailViolationError
- errors.py
- llm/__init__.py
- TestTrackedCallFunctions
- get_settings
- get_embedding_model
- TestModelFactory
- CircuitState
- get_model_config
- ModelRegistry
- graphify reference: extra exports and benchmark
- create_riva_config_from_env
- model_registry.py
- ConfigurationError
- ExternalServiceError
- GraphError
- ModelError
- RateLimiter
- AuthenticationError
- reset_model_registry
- graphify reference: query, path, explain
- check_permission
- RivaConfig
- EvaluationError
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- .test_tracked_call_failure
- CLAUDE.md
- extraction-spec.md
- nim-sentinel

## God Nodes (most connected - your core abstractions)
1. `ModelRegistry` - 29 edges
2. `CircuitBreaker` - 27 edges
3. `RivaConfig` - 24 edges
4. `ModelRole` - 23 edges
5. `TestModelRegistry` - 20 edges
6. `NIMException` - 19 edges
7. `ModelMetrics` - 17 edges
8. `RivaASRAdapter` - 17 edges
9. `=== PROMPT START ===` - 15 edges
10. `get_model_config()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `9. CI/CD (GitHub Actions)` --references--> `main()`  [INFERRED]
  CLAUDE_CODE_MASTER_PROMPT.md → scripts/check_models.py
- `2. USE ALL TYPES OF NVIDIA MODELS (config-driven model registry)` --references--> `ModelRegistry`  [INFERRED]
  CLAUDE_CODE_MASTER_PROMPT.md → src/nim_sentinel/llm/model_registry.py
- `test()` --calls--> `tracked_chat_call()`  [INFERRED]
  tests/test_model_registry.py → src/nim_sentinel/llm/model_registry.py
- `test()` --calls--> `tracked_embedding_call()`  [INFERRED]
  tests/test_model_registry.py → src/nim_sentinel/llm/model_registry.py
- `test()` --calls--> `tracked_rerank_call()`  [INFERRED]
  tests/test_model_registry.py → src/nim_sentinel/llm/model_registry.py

## Import Cycles
- None detected.

## Communities (57 total, 7 thin omitted)

### Community 0 - "CostTracker"
Cohesion: 0.09
Nodes (14): Interpreter guard for subcommands, AggregatedCosts, CostSnapshot, CostTracker, Any, Tracks cost, latency, and token usage per model role. Thread-safe for…, Calculate cost for a model call., Get aggregated costs. (+6 more)

### Community 1 - "logging.py"
Cohesion: 0.07
Nodes (26): asyncio, BoundLogger, contextvars, grpc, logging_config, LogRecord, pathlib, re (+18 more)

### Community 2 - "core/__init__.py"
Cohesion: 0.09
Nodes (30): BaseModel, hashlib, jose, passlib_context, secrets, NIM Sentinel Core Package Core configuration, logging, errors, security, and…, constant_time_compare(), generate_api_key() (+22 more)

### Community 3 - "=== PROMPT START ==="
Cohesion: 0.07
Nodes (29): 0. WORKING RULES (follow strictly), 10. DEPLOYMENT AND PRODUCTION READINESS, 11. DOCUMENTATION AND DIAGRAMS, 12. EXECUTION PLAN (phases; stop after each for my approval), 13. DEFINITION OF DONE, 1. TECH STACK, 2. USE ALL TYPES OF NVIDIA MODELS (config-driven model registry), 3. REPOSITORY STRUCTURE (+21 more)

### Community 4 - "config.py"
Cohesion: 0.11
Nodes (27): BaseSettings, pydantic, pydantic_settings, AgentsConfig, EvalThresholdsConfig, get_agents_config(), get_available_model_roles(), get_eval_thresholds() (+19 more)

### Community 5 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (25): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents) (+17 more)

### Community 6 - "RivaASRAdapter"
Cohesion: 0.14
Nodes (13): Adapter for NVIDIA Riva Automatic Speech Recognition (ASR) via gRPC. Requires a…, Initialize Riva ASR service connection., RivaASRAdapter, patch, Test successful offline transcription., Test offline transcription with empty results., Test offline transcription error handling., Tests for RivaASRAdapter. (+5 more)

### Community 7 - "CircuitBreaker"
Cohesion: 0.11
Nodes (13): CircuitBreaker, Circuit breaker for model endpoints., Record a successful call., Record a failed call., Check if a call can be executed., Reset circuit breaker to closed state., Tests for CircuitBreaker., Test initial state is closed. (+5 more)

### Community 8 - ".__init__"
Cohesion: 0.12
Nodes (12): ApprovalRejectedError, HumanApprovalRequiredError, Base class for tool errors., Raised when a tool is not found., Raised when tool execution fails., Raised when tool arguments fail validation., Raised when human approval is required for a tool., Raised when human approval is rejected. (+4 more)

### Community 9 - "get_riva_asr"
Cohesion: 0.12
Nodes (14): get_riva_asr(), get_riva_tts(), Get global Riva ASR adapter instance., Get global Riva TTS adapter instance., Reset global Riva adapters (for testing)., reset_riva_adapters(), Reset global adapters before each test., Tests for global adapter instances. (+6 more)

### Community 10 - "check_models.py"
Cohesion: 0.11
Nodes (23): dotenv, langchain_nvidia_ai_endpoints, nim_sentinel_core, nim_sentinel_llm_model_registry, nim_sentinel_llm_riva_adapter, os, pytest, fetch_available_models() (+15 more)

### Community 11 - "constants.py"
Cohesion: 0.21
Nodes (17): ApprovalStatus, DocumentStatus, GuardrailAction, GuardrailType, IntentType, MessageRole, Enum, str (+9 more)

### Community 12 - "TestModelRegistry"
Cohesion: 0.13
Nodes (8): Tests for ModelRegistry., Test getting fallback chat model., Test getting embedding model., Test tracked call context manager success., Test getting circuit states., Test resetting a circuit breaker., Test resetting all circuit breakers., TestModelRegistry

### Community 13 - "ModelUnavailableError"
Cohesion: 0.13
Nodes (11): AudioEncoding, ModelUnavailableError, Raised when a model is unavailable., Path, Transcribe audio using streaming recognition. Args: audio_chunks: Async…, Transcribe audio from a WAV file. Args: file_path: Path to WAV file…, Initialize Riva TTS service connection., Synthesize speech from text (offline/batch). Args: text: Text to synthesize… (+3 more)

### Community 14 - "Completed Tasks"
Cohesion: 0.12
Nodes (16): 10. Environment & Security ✅, 11. Code Quality ✅, 1. Repository Scaffold ✅, 2. Tooling Configuration ✅, 3. Configuration System ✅, 4. Core Modules ✅, 5. Model Registry ✅, 6. NVIDIA Model Verification ✅ (+8 more)

### Community 15 - "Any"
Cohesion: 0.15
Nodes (11): ContentSafetyError, InputGuardrailError, JailbreakDetectedError, PIIDetectedError, Any, Raised when input guardrail fails., Raised when PII is detected in input., Raised when jailbreak attempt is detected. (+3 more)

### Community 16 - "ModelMetrics"
Cohesion: 0.15
Nodes (8): ModelMetrics, Test recording failed call., Test average latency calculation., Test success rate calculation., Test getting metrics., Tests for ModelMetrics., Test recording successful call., TestModelMetrics

### Community 17 - "DatabaseError"
Cohesion: 0.17
Nodes (8): DatabaseError, MongoConnectionError, MongoQueryError, Base class for database errors., Raised when MongoDB connection fails., Raised when a MongoDB query fails., Raised when vector index operations fail., VectorIndexError

### Community 18 - "patch"
Cohesion: 0.11
Nodes (11): patch, Test registry initialization., Test getting primary chat model., Test circuit open on primary tries fallback., Test fallback exhausted raises error., Test getting rerank model., Tests for convenience functions., Test get_chat_model convenience function. (+3 more)

### Community 19 - "with_fallback"
Cohesion: 0.13
Nodes (9): F, Decorator to automatically retry with fallback on failure., with_fallback(), Tests for with_fallback decorator., Test decorator when primary succeeds., Test decorator when primary fails but fallback succeeds., Test decorator when both primary and fallback fail., Test decorator when no fallback configured. (+1 more)

### Community 20 - "NIMException"
Cohesion: 0.14
Nodes (9): Exception, AuthorizationError, NIMException, RateLimitError, Raised when rate limit is exceeded., Base exception for NIM Sentinel., Raised when input validation fails., Raised when authorization fails. (+1 more)

### Community 21 - "RivaTTSAdapter"
Cohesion: 0.21
Nodes (8): Adapter for NVIDIA Riva Text-to-Speech (TTS) via gRPC. Requires a running Riva…, RivaTTSAdapter, Tests for RivaTTSAdapter., Test initialization with default config., Test adapter initialization., Test successful speech synthesis., Test speech synthesis error handling., TestRivaTTSAdapter

### Community 22 - "ModelRole"
Cohesion: 0.24
Nodes (10): BaseChatModel, Embeddings, NVIDIARerank, ModelRole, Model roles in the registry., get_rerank_model(), Context manager for tracked model calls with automatic metrics and circuit…, Get a rerank model from the global registry. (+2 more)

### Community 23 - "GuardrailViolationError"
Cohesion: 0.17
Nodes (8): CitationRequiredError, GroundednessError, GuardrailViolationError, OutputGuardrailError, Raised when a guardrail check fails., Raised when output guardrail fails., Raised when groundedness check fails., Raised when citations are required but missing.

### Community 24 - "errors.py"
Cohesion: 0.18
Nodes (9): DocumentError, DocumentParseError, DocumentTooLargeError, NIM Sentinel Core Errors Module Custom exception hierarchy for the application., Base class for document processing errors., Raised when document parsing fails., Raised when document exceeds size limit., Raised when file type is not supported. (+1 more)

### Community 25 - "llm/__init__.py"
Cohesion: 0.22
Nodes (11): ChatNVIDIA, NIM Sentinel LLM Package Model registry, factories, fallbacks, callbacks, cost…, get_chat_model(), get_model_registry(), Get a chat model for the given role., Get the global model registry instance., Get a chat model from the global registry., Tracked chat model call. (+3 more)

### Community 26 - "TestTrackedCallFunctions"
Cohesion: 0.17
Nodes (8): Tests for tracked call context managers., Test tracked_chat_call., Test tracked_embedding_call., Test tracked_rerank_call., TestTrackedCallFunctions, test(), test(), test()

### Community 27 - "get_settings"
Cohesion: 0.18
Nodes (10): field_validator, get_settings(), Get cached settings instance., Main application settings loaded from environment and .env file., Settings, Configure structured logging from YAML config., setup_logging(), create_access_token() (+2 more)

### Community 28 - "get_embedding_model"
Cohesion: 0.16
Nodes (10): NVIDIAEmbeddings, get_embedding_model(), ModelFactory, Any, Factory for creating model instances., Create a ChatNVIDIA instance., Create an NVIDIAEmbeddings instance., Create an NVIDIARerank instance. (+2 more)

### Community 29 - "TestModelFactory"
Cohesion: 0.25
Nodes (5): Tests for ModelFactory., Test chat model creation., Test embedding model creation., Test rerank model creation., TestModelFactory

### Community 30 - "CircuitState"
Cohesion: 0.33
Nodes (5): CircuitState, Enum, str, Circuit breaker states., Get current circuit breaker states.

### Community 31 - "get_model_config"
Cohesion: 0.17
Nodes (11): get_model_config(), Get model configuration for a specific role., estimate_cost(), get_cost_tracker(), Get the global cost tracker instance., Context manager to track cost of an operation. Yields a dict to populate with…, Estimate cost for a model call., track_cost() (+3 more)

### Community 32 - "ModelRegistry"
Cohesion: 0.25
Nodes (5): ModelRegistry, Central model registry with fallback chains, circuit breakers, and metrics., Get metrics for all models or a specific role., Manually reset a circuit breaker., Reset all circuit breakers.

### Community 33 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 34 - "create_riva_config_from_env"
Cohesion: 0.28
Nodes (7): dict, create_riva_config_from_env(), Create RivaConfig from environment variables., Tests for create_riva_config_from_env function., Test creating config from environment variables., Test creating config with defaults when env vars not set., TestCreateRivaConfigFromEnv

### Community 35 - "model_registry.py"
Cohesion: 0.17
Nodes (14): collections_abc, contextlib, dataclasses, datetime, functools, langchain_core_embeddings, langchain_core_language_models, NIM Sentinel Cost Tracker Tracks token usage, latency, and cost per model role.… (+6 more)

### Community 36 - "ConfigurationError"
Cohesion: 0.22
Nodes (6): ConfigurationError, ModelNotConfiguredError, ModelUnverifiedError, Raised when configuration is invalid or missing., Raised when a model role is not configured., Raised when attempting to use an unverified model.

### Community 37 - "ExternalServiceError"
Cohesion: 0.22
Nodes (6): ExternalServiceError, LangSmithError, NVIDIAAPIError, Base class for external service errors., Raised when NVIDIA API returns an error., Raised when LangSmith API returns an error.

### Community 38 - "GraphError"
Cohesion: 0.22
Nodes (6): GraphError, GraphInterruptError, GraphTimeoutError, Base class for LangGraph errors., Raised when graph execution is interrupted (HITL)., Raised when graph execution times out.

### Community 39 - "ModelError"
Cohesion: 0.17
Nodes (8): FallbackExhaustedError, ModelError, ModelRateLimitError, ModelTimeoutError, Base class for model-related errors., Raised when a model request times out., Raised when model API rate limit is hit., Raised when all model fallbacks are exhausted.

### Community 40 - "RateLimiter"
Cohesion: 0.22
Nodes (5): RateLimiter, Simple in-memory rate limiter (use Redis in production)., Check if request is allowed under rate limit., Get remaining requests in window., Reset rate limit for a key.

### Community 41 - "AuthenticationError"
Cohesion: 0.29
Nodes (8): AuthenticationError, InvalidTokenError, Raised when authentication fails., Raised when JWT token is expired., Raised when JWT token is invalid., TokenExpiredError, decode_token(), Decode and validate a JWT token.

### Community 43 - "reset_model_registry"
Cohesion: 0.20
Nodes (7): Reset the global model registry (for testing)., reset_model_registry(), Reset global registry before each test., Tests for global registry functions., Test global registry is singleton., Test reset clears singleton., TestGlobalRegistry

### Community 44 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 45 - "check_permission"
Cohesion: 0.33
Nodes (6): check_all_permissions(), check_any_permission(), check_permission(), Check if user has a specific permission., Check if user has any of the required permissions., Check if user has all required permissions.

### Community 46 - "RivaConfig"
Cohesion: 0.32
Nodes (6): Configuration for Riva gRPC connection., RivaConfig, Tests for RivaConfig dataclass., Test default configuration values., Test custom configuration values., TestRivaConfig

### Community 47 - "EvaluationError"
Cohesion: 0.40
Nodes (4): EvaluationError, Raised when evaluation fails., Raised when evaluation threshold is not met., ThresholdNotMetError

### Community 48 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 49 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 50 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

## Knowledge Gaps
- **79 isolated node(s):** `nim-sentinel`, `graphify`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)` (+74 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 376 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ModelRegistry` connect `ModelRegistry` to `=== PROMPT START ===`, `model_registry.py`, `TestModelRegistry`, `ModelMetrics`, `patch`, `.test_tracked_call_failure`, `ModelRole`, `llm/__init__.py`, `get_embedding_model`, `CircuitState`, `get_model_config`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Why does `CircuitBreaker` connect `CircuitBreaker` to `model_registry.py`, `TestModelRegistry`, `patch`, `.test_tracked_call_failure`, `llm/__init__.py`, `get_model_config`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `ModelRegistry` (e.g. with `2. USE ALL TYPES OF NVIDIA MODELS (config-driven model registry)` and `TestModelRegistry`) actually correct?**
  _`ModelRegistry` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `CircuitBreaker` (e.g. with `TestCircuitBreaker` and `.test_closes_after_half_open_successes()`) actually correct?**
  _`CircuitBreaker` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `RivaConfig` (e.g. with `TestGlobalAdapters` and `.test_get_riva_asr_singleton()`) actually correct?**
  _`RivaConfig` has 18 INFERRED edges - model-reasoned connections that need verification._
- **What connects `nim-sentinel`, `graphify`, `Usage` to the rest of the system?**
  _79 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `CostTracker` be split into smaller, more focused modules?**
  _Cohesion score 0.09333333333333334 - nodes in this community are weakly interconnected._