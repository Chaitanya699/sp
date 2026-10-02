# Graph Report - sp  (2026-10-03)

## Corpus Check
- 32 files · ~36,129 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 4, .graphify-bak 1, .lock 1)

## Summary
- 911 nodes · 1535 edges · 70 communities (55 shown, 15 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 173 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3624fa95`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AggregatedCosts
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
- ._initialize
- Completed Tasks
- errors.py
- ModelMetrics
- DatabaseError
- patch
- with_fallback
- Any
- RivaTTSAdapter
- ModelRole
- GuardrailViolationError
- DocumentError
- llm/__init__.py
- reset_model_registry
- get_settings
- ModelFactory
- Communities (57 total, 7 thin omitted)
- TestCostTracker
- CostTracker
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
- CorrelationContext
- test_cost_tracker.py
- graphify reference: query, path, explain
- load_yaml_config
- RivaConfig
- TestModelPricing
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- riva_adapter.py
- CLAUDE.md
- extraction-spec.md
- Graph Report - sp  (2026-10-02)
- nim-sentinel
- TestCostTrackerThreadSafety
- .tracker
- .test_tracked_call_success
- .test_calculate_cost_known_model
- .test_calculate_cost_embedding_model
- .test_record_call
- .test_get_snapshots_no_filters
- .test_get_snapshots_role_filter
- .test_get_snapshots_since_filter
- .test_get_summary
- .test_reset

## God Nodes (most connected - your core abstractions)
1. `Communities (57 total, 7 thin omitted)` - 51 edges
2. `ModelRegistry` - 32 edges
3. `CircuitBreaker` - 29 edges
4. `RivaConfig` - 26 edges
5. `ModelRole` - 24 edges
6. `TestModelRegistry` - 22 edges
7. `NIMException` - 20 edges
8. `TestCostTracker` - 20 edges
9. `ModelMetrics` - 19 edges
10. `RivaASRAdapter` - 18 edges

## Surprising Connections (you probably didn't know these)
- `2. USE ALL TYPES OF NVIDIA MODELS (config-driven model registry)` --references--> `ModelRegistry`  [INFERRED]
  CLAUDE_CODE_MASTER_PROMPT.md → src/nim_sentinel/llm/model_registry.py
- `9. CI/CD (GitHub Actions)` --references--> `main()`  [INFERRED]
  CLAUDE_CODE_MASTER_PROMPT.md → scripts/check_models.py
- `Surprising Connections (you probably didn't know these)` --references--> `main()`  [INFERRED]
  docs/graph/GRAPH_REPORT.md → scripts/check_models.py
- `God Nodes (most connected - your core abstractions)` --references--> `get_model_config()`  [INFERRED]
  docs/graph/GRAPH_REPORT.md → src/nim_sentinel/core/config.py
- `Suggested Questions` --references--> `get_model_config()`  [INFERRED]
  docs/graph/GRAPH_REPORT.md → src/nim_sentinel/core/config.py

## Import Cycles
- None detected.

## Communities (70 total, 15 thin omitted)

### Community 0 - "AggregatedCosts"
Cohesion: 0.09
Nodes (20): Interpreter guard for subcommands, AggregatedCosts, CostSnapshot, Snapshot of cost metrics at a point in time., Aggregated cost metrics for a role., Add a snapshot to aggregates., Test adding a failed snapshot., Test adding multiple snapshots for the same model. (+12 more)

### Community 1 - "logging.py"
Cohesion: 0.17
Nodes (14): contextvars, logging_config, re, add_correlation_id(), hash_user_id(), log_audit(), Any, NIM Sentinel Core Logging Module Structured logging with PII redaction,… (+6 more)

### Community 2 - "core/__init__.py"
Cohesion: 0.08
Nodes (36): BaseModel, hashlib, jose, passlib_context, secrets, NIM Sentinel Core Package Core configuration, logging, errors, security, and…, check_all_permissions(), check_any_permission() (+28 more)

### Community 3 - "=== PROMPT START ==="
Cohesion: 0.07
Nodes (28): 0. WORKING RULES (follow strictly), 10. DEPLOYMENT AND PRODUCTION READINESS, 11. DOCUMENTATION AND DIAGRAMS, 12. EXECUTION PLAN (phases; stop after each for my approval), 13. DEFINITION OF DONE, 1. TECH STACK, 2. USE ALL TYPES OF NVIDIA MODELS (config-driven model registry), 3. REPOSITORY STRUCTURE (+20 more)

### Community 4 - "config.py"
Cohesion: 0.13
Nodes (19): BaseSettings, functools, pydantic, pydantic_settings, AgentsConfig, get_available_model_roles(), get_guardrails_config(), get_model_registry() (+11 more)

### Community 5 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (25): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents) (+17 more)

### Community 6 - "RivaASRAdapter"
Cohesion: 0.14
Nodes (13): Adapter for NVIDIA Riva Automatic Speech Recognition (ASR) via gRPC. Requires a…, Initialize Riva ASR service connection., RivaASRAdapter, patch, Test successful offline transcription., Test offline transcription with empty results., Test offline transcription error handling., Tests for RivaASRAdapter. (+5 more)

### Community 7 - "CircuitBreaker"
Cohesion: 0.10
Nodes (17): Suggested Questions, CircuitBreaker, CircuitState, StrEnum, Circuit breaker states., Circuit breaker for model endpoints., Record a successful call., Record a failed call. (+9 more)

### Community 8 - ".__init__"
Cohesion: 0.12
Nodes (14): ApprovalRejectedError, HumanApprovalRequiredError, Base class for tool errors., Raised when a tool is not found., Raised when tool execution fails., Raised when tool arguments fail validation., Raised when human approval is required for a tool., Raised when human approval is rejected. (+6 more)

### Community 9 - "get_riva_asr"
Cohesion: 0.12
Nodes (14): get_riva_asr(), get_riva_tts(), Get global Riva ASR adapter instance., Get global Riva TTS adapter instance., Reset global Riva adapters (for testing)., reset_riva_adapters(), Reset global adapters before each test., Tests for global adapter instances. (+6 more)

### Community 10 - "check_models.py"
Cohesion: 0.17
Nodes (17): 9. CI/CD (GitHub Actions), dataclasses, dotenv, os, fetch_available_models(), generate_models_yaml(), load_configured_roles(), main() (+9 more)

### Community 11 - "constants.py"
Cohesion: 0.15
Nodes (18): enum, ApprovalStatus, DocumentStatus, GuardrailAction, GuardrailType, IntentType, MessageRole, StrEnum (+10 more)

### Community 12 - "TestModelRegistry"
Cohesion: 0.12
Nodes (9): Tests for ModelRegistry., Reset global registry before each test., Test registry initialization., Test getting rerank model., Test getting metrics., Test getting circuit states., Test resetting a circuit breaker., Test resetting all circuit breakers. (+1 more)

### Community 13 - "._initialize"
Cohesion: 0.13
Nodes (9): AudioEncoding, Path, Transcribe audio using streaming recognition. Args: audio_chunks: Async…, Transcribe audio from a WAV file. Args: file_path: Path to WAV file…, Initialize Riva TTS service connection., Synthesize speech from text (offline/batch). Args: text: Text to synthesize…, Synthesize speech with streaming output (online). Args: text: Text or list of…, Synthesize speech and save to WAV file. Args: text: Text to synthesize… (+1 more)

### Community 14 - "Completed Tasks"
Cohesion: 0.11
Nodes (17): 10. Environment & Security ✅, 11. Code Quality ✅, 12. Post-Phase 1 Fixes (6 items) ✅, 1. Repository Scaffold ✅, 2. Tooling Configuration ✅, 3. Configuration System ✅, 4. Core Modules ✅, 5. Model Registry ✅ (+9 more)

### Community 15 - "errors.py"
Cohesion: 0.15
Nodes (11): ContentSafetyError, InputGuardrailError, JailbreakDetectedError, PIIDetectedError, NIM Sentinel Core Errors Module Custom exception hierarchy for the application., Raised when input guardrail fails., Raised when PII is detected in input., Raised when jailbreak attempt is detected. (+3 more)

### Community 16 - "ModelMetrics"
Cohesion: 0.14
Nodes (9): God Nodes (most connected - your core abstractions), ModelMetrics, Get metrics for all models or a specific role., Test recording failed call., Test average latency calculation., Test success rate calculation., Tests for ModelMetrics., Test recording successful call. (+1 more)

### Community 17 - "DatabaseError"
Cohesion: 0.17
Nodes (8): DatabaseError, MongoConnectionError, MongoQueryError, Base class for database errors., Raised when MongoDB connection fails., Raised when a MongoDB query fails., Raised when vector index operations fail., VectorIndexError

### Community 18 - "patch"
Cohesion: 0.13
Nodes (9): patch, Test getting primary chat model., Test getting embedding model., Test tracked call context manager failure., Tests for convenience functions., Test get_chat_model convenience function., Test get_embedding_model convenience function., Test get_rerank_model convenience function. (+1 more)

### Community 19 - "with_fallback"
Cohesion: 0.14
Nodes (9): F, Decorator to automatically retry with fallback on failure., with_fallback(), Tests for with_fallback decorator., Test decorator when primary succeeds., Test decorator when primary fails but fallback succeeds., Test decorator when both primary and fallback fail., Test decorator when no fallback configured. (+1 more)

### Community 20 - "Any"
Cohesion: 0.13
Nodes (12): Exception, AuthorizationError, EvaluationError, NIMException, Any, RateLimitError, Raised when rate limit is exceeded., Base exception for NIM Sentinel. (+4 more)

### Community 21 - "RivaTTSAdapter"
Cohesion: 0.21
Nodes (8): Adapter for NVIDIA Riva Text-to-Speech (TTS) via gRPC. Requires a running Riva…, RivaTTSAdapter, Tests for RivaTTSAdapter., Test initialization with default config., Test adapter initialization., Test successful speech synthesis., Test speech synthesis error handling., TestRivaTTSAdapter

### Community 22 - "ModelRole"
Cohesion: 0.18
Nodes (14): BaseChatModel, ChatNVIDIA, Embeddings, NVIDIARerank, ModelRole, Model roles in the registry., ModelUnavailableError, Raised when a model is unavailable. (+6 more)

### Community 23 - "GuardrailViolationError"
Cohesion: 0.17
Nodes (8): CitationRequiredError, GroundednessError, GuardrailViolationError, OutputGuardrailError, Raised when a guardrail check fails., Raised when output guardrail fails., Raised when groundedness check fails., Raised when citations are required but missing.

### Community 24 - "DocumentError"
Cohesion: 0.17
Nodes (8): DocumentError, DocumentParseError, DocumentTooLargeError, Base class for document processing errors., Raised when document parsing fails., Raised when document exceeds size limit., Raised when file type is not supported., UnsupportedFileTypeError

### Community 25 - "llm/__init__.py"
Cohesion: 0.19
Nodes (14): Surprising Connections (you probably didn't know these), NVIDIAEmbeddings, NIM Sentinel LLM Package Model registry, factories, fallbacks, callbacks, cost…, get_embedding_model(), get_model_registry(), Get an embedding model., Get the global model registry instance., Get an embedding model from the global registry. (+6 more)

### Community 26 - "reset_model_registry"
Cohesion: 0.13
Nodes (10): Reset the global model registry (for testing)., reset_model_registry(), Tests for tracked call context managers., Test tracked_chat_call., Test tracked_embedding_call., Test tracked_rerank_call., TestTrackedCallFunctions, test() (+2 more)

### Community 27 - "get_settings"
Cohesion: 0.22
Nodes (8): field_validator, get_settings(), Get cached settings instance., Main application settings loaded from environment and .env file., Settings, create_access_token(), Create a JWT access token., timedelta

### Community 28 - "ModelFactory"
Cohesion: 0.14
Nodes (11): ModelFactory, Any, Factory for creating model instances., Create a ChatNVIDIA instance., Create an NVIDIAEmbeddings instance., Create an NVIDIARerank instance., Tests for ModelFactory., Test chat model creation. (+3 more)

### Community 29 - "Communities (57 total, 7 thin omitted)"
Cohesion: 0.04
Nodes (51): Communities (57 total, 7 thin omitted), Community 0 - "CostTracker", Community 10 - "check_models.py", Community 11 - "constants.py", Community 12 - "TestModelRegistry", Community 13 - "ModelUnavailableError", Community 14 - "Completed Tasks", Community 15 - "Any" (+43 more)

### Community 30 - "TestCostTracker"
Cohesion: 0.11
Nodes (10): Tests for CostTracker class., Test cost calculation for unknown model returns 0., Test recording a failed call., Test getting all aggregates., Test getting aggregates for a specific role., Test getting aggregates for nonexistent role returns empty AggregatedCosts., Test getting snapshots with model filter., Test getting snapshots with limit. (+2 more)

### Community 31 - "CostTracker"
Cohesion: 0.17
Nodes (7): CostTracker, Any, Tracks cost, latency, and token usage per model role. Thread-safe for…, Calculate cost for a model call., Get aggregated costs., Get cost summary across all roles., Reset all tracked data.

### Community 32 - "ModelRegistry"
Cohesion: 0.12
Nodes (9): ModelRegistry, Central model registry with fallback chains, circuit breakers, and metrics., Initialize the registry with configured models., Get current circuit breaker states., Manually reset a circuit breaker., Reset all circuit breakers., Test getting fallback chat model., Test circuit open on primary tries fallback. (+1 more)

### Community 33 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 34 - "create_riva_config_from_env"
Cohesion: 0.28
Nodes (7): dict, create_riva_config_from_env(), Create RivaConfig from environment variables., Tests for create_riva_config_from_env function., Test creating config from environment variables., Test creating config with defaults when env vars not set., TestCreateRivaConfigFromEnv

### Community 35 - "model_registry.py"
Cohesion: 0.13
Nodes (17): collections_abc, contextlib, datetime, langchain_core_embeddings, langchain_core_language_models, get_model_config(), Get model configuration for a specific role., FallbackExhaustedError (+9 more)

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
Cohesion: 0.22
Nodes (6): ModelError, ModelRateLimitError, ModelTimeoutError, Base class for model-related errors., Raised when a model request times out., Raised when model API rate limit is hit.

### Community 40 - "RateLimiter"
Cohesion: 0.22
Nodes (5): RateLimiter, Simple in-memory rate limiter (use Redis in production)., Check if request is allowed under rate limit., Get remaining requests in window., Reset rate limit for a key.

### Community 41 - "AuthenticationError"
Cohesion: 0.20
Nodes (8): AuthenticationError, InvalidTokenError, Raised when authentication fails., Raised when JWT token is expired., Raised when JWT token is invalid., TokenExpiredError, decode_token(), Decode and validate a JWT token.

### Community 42 - "CorrelationContext"
Cohesion: 0.20
Nodes (5): LogRecord, CorrelationContext, PIIRedactionFilter, Context manager for setting correlation IDs., Logging filter to redact PII and secrets from log records.

### Community 43 - "test_cost_tracker.py"
Cohesion: 0.06
Nodes (36): asyncio, langchain_nvidia_ai_endpoints, nim_sentinel_core, nim_sentinel_llm_cost_tracker, nim_sentinel_llm_model_registry, nim_sentinel_llm_riva_adapter, pytest, get_cost_tracker() (+28 more)

### Community 44 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 45 - "load_yaml_config"
Cohesion: 0.20
Nodes (10): EvalThresholdsConfig, get_agents_config(), get_eval_thresholds(), load_yaml_config(), Any, Path, Load YAML configuration file., Load agents configuration from YAML. (+2 more)

### Community 46 - "RivaConfig"
Cohesion: 0.32
Nodes (6): Configuration for Riva gRPC connection., RivaConfig, Tests for RivaConfig dataclass., Test default configuration values., Test custom configuration values., TestRivaConfig

### Community 47 - "TestModelPricing"
Cohesion: 0.20
Nodes (6): Tests for MODEL_PRICING dictionary., Test that pricing includes chat models., Test that pricing includes embedding models., Test that pricing includes rerank models., Test that pricing entries have correct structure., TestModelPricing

### Community 48 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 49 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 50 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 53 - "riva_adapter.py"
Cohesion: 0.25
Nodes (7): BoundLogger, grpc, pathlib, riva_client, get_logger(), Get a structured logger instance., NIM Sentinel Riva ASR/TTS Adapter Provides gRPC-based adapters for NVIDIA Riva…

### Community 56 - "Graph Report - sp  (2026-10-02)"
Cohesion: 0.25
Nodes (7): Community Hubs (Navigation), Corpus Check, Graph Freshness, Graph Report - sp  (2026-10-02), Import Cycles, Knowledge Gaps, Summary

### Community 59 - "TestCostTrackerThreadSafety"
Cohesion: 0.25
Nodes (4): Tests for thread safety of CostTracker., Test concurrent record_call calls., Test concurrent get_aggregates calls., TestCostTrackerThreadSafety

### Community 60 - ".tracker"
Cohesion: 0.40
Nodes (3): fixture, Create a fresh CostTracker for each test., Create a fresh CostTracker for each test.

## Knowledge Gaps
- **136 isolated node(s):** `nim-sentinel`, `graphify`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)` (+131 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 486 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Graph Report - sp  (2026-10-02)` connect `Graph Report - sp  (2026-10-02)` to `ModelMetrics`, `llm/__init__.py`, `Communities (57 total, 7 thin omitted)`, `CircuitBreaker`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Why does `Suggested Questions` connect `CircuitBreaker` to `ModelRegistry`, `model_registry.py`, `get_riva_asr`, `TestModelRegistry`, `RivaConfig`, `ModelMetrics`, `ModelRole`, `Graph Report - sp  (2026-10-02)`, `CostTracker`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `CostTracker` connect `CostTracker` to `model_registry.py`, `CircuitBreaker`, `test_cost_tracker.py`, `TestCostTrackerThreadSafety`, `.tracker`, `TestCostTracker`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `ModelRegistry` (e.g. with `2. USE ALL TYPES OF NVIDIA MODELS (config-driven model registry)` and `God Nodes (most connected - your core abstractions)`) actually correct?**
  _`ModelRegistry` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `CircuitBreaker` (e.g. with `God Nodes (most connected - your core abstractions)` and `Suggested Questions`) actually correct?**
  _`CircuitBreaker` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `RivaConfig` (e.g. with `God Nodes (most connected - your core abstractions)` and `Suggested Questions`) actually correct?**
  _`RivaConfig` has 20 INFERRED edges - model-reasoned connections that need verification._
- **What connects `nim-sentinel`, `graphify`, `Usage` to the rest of the system?**
  _136 weakly-connected nodes found - possible documentation gaps or missing edges._