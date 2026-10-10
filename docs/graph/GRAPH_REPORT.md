# Graph Report - sp  (2026-10-10)

## Corpus Check
- 98 files · ~87,554 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .jsonl 2, .graphify-bak 1)

## Summary
- 2707 nodes · 4921 edges · 144 communities (129 shown, 15 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 623 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b7baab65`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AggregatedCosts
- logging.py
- security.py
- === PROMPT START ===
- get_settings
- What You Must Do When Invoked
- RivaConfig
- TestCircuitBreaker
- errors.py
- test_graph_checkpointer.py
- check_models.py
- core/__init__.py
- ModelRegistry
- TextParser
- Completed Tasks
- .__init__
- TestModelMetrics
- ModelError
- MongoDBCheckpointer
- test_model_registry.py
- NIMException
- create_indexes.py
- ModelRole
- TestHybridRetriever
- upload_document
- TokenChunker
- TestTrackedCallFunctions
- SupervisorDecision
- TestModelFactory
- Communities (70 total, 15 thin omitted)
- TestCostTracker
- main.py
- model_registry.py
- graphify reference: extra exports and benchmark
- guardrails/__init__.py
- TestOutputGuardrails
- ConfigurationError
- EmbeddingClient
- GraphError
- TestIngestionPipeline
- RateLimiter
- Any
- repositories.py
- get_cost_tracker
- graphify reference: query, path, explain
- MongoConnectionError
- CriticOutput
- TestModelPricing
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- MongoClient
- CLAUDE.md
- extraction-spec.md
- redact_for_logging
- nim-sentinel
- TestCostTrackerThreadSafety
- routes.py
- IngestionPipeline
- ChunkRepository
- TestTextCleaner
- fixture
- detect_jailbreak
- asyncio
- TestSessionRepository
- decorators.py
- CorrelationContext
- AgentState
- SessionRepository
- TestInputGuardrails
- .find_many
- TestBaseRepository
- riva_adapter.py
- db/__init__.py
- test_ingestion.py
- asyncio
- ExternalServiceError
- TestDataAnalystAgent
- CostTracker
- TestNemoGuardClient
- close_mongo_client
- EmbeddingResult
- pytest
- create_dev_token
- test_integration.py
- clean_text
- DocumentRepository
- detect_injection
- redact_messages_for_logging
- TestCreateInitialState
- create_async_client
- TestAtlasConnection
- test_api_routes.py
- test_cost_tracker.py
- make_dev_token.py
- Current Phase: Phase 2 - MongoDB + RAG Implementation
- WordEmbeddingMock
- test_golden_retrieval.py
- TestPIIPatterns
- motor_motor_asyncio
- TestSupervisorGoldenDataset
- reset_input_guardrails
- DataAnalystAgent
- TestTracedNode
- benchmark_model
- TestRedactPII
- TestCheckGroundedness
- GuardResult
- redact_pii_dict
- ._get_model
- TestGoldenRetrievalDataset
- TestTracedTool
- TestTracedLLMCall
- TestTracedRetriever
- unittest_mock
- check_citation_coverage
- ._embed_batch
- detect_all_heuristic
- detect_pii
- test_data_analyst.py
- test_riva_adapter.py
- .get_parser
- .agent
- fixture
- TestEndToEndRAG
- BaseParser
- ParserRegistry
- TestEstimateCost
- .test_execute_with_mock
- get_golden_examples
- TestAgentState
- TestIngestionConfig
- NemoGuardAction
- .test_upload_document_validation
- test_guardrails_jailbreak.py
- .client
- .record_success
- .test_inject_tenant_filter_existing_match_with_and
- .test_enforce_row_limit_keeps_smaller
- .test_validate_pipeline_forbidden_stage
- .test_validate_pipeline_multiple_keys

## God Nodes (most connected - your core abstractions)
1. `AgentState` - 65 edges
2. `Communities (70 total, 15 thin omitted)` - 56 edges
3. `ModelRegistry` - 44 edges
4. `get_settings()` - 41 edges
5. `CircuitBreaker` - 38 edges
6. `IngestionPipeline` - 31 edges
7. `get_model_config()` - 29 edges
8. `MongoClient` - 29 edges
9. `ModelMetrics` - 28 edges
10. `RivaConfig` - 26 edges

## Surprising Connections (you probably didn't know these)
- `2. USE ALL TYPES OF NVIDIA MODELS (config-driven model registry)` --references--> `ModelRegistry`  [INFERRED]
  CLAUDE_CODE_MASTER_PROMPT.md → src/nim_sentinel/llm/model_registry.py
- `Surprising Connections (you probably didn't know these)` --references--> `get_model_config()`  [INFERRED]
  docs/graph/GRAPH_REPORT.md → src/nim_sentinel/core/config.py
- `God Nodes (most connected - your core abstractions)` --references--> `ModelRole`  [INFERRED]
  docs/graph/GRAPH_REPORT.md → src/nim_sentinel/core/constants.py
- `Suggested Questions` --references--> `ModelRole`  [INFERRED]
  docs/graph/GRAPH_REPORT.md → src/nim_sentinel/core/constants.py
- `God Nodes (most connected - your core abstractions)` --references--> `NIMException`  [INFERRED]
  docs/graph/GRAPH_REPORT.md → src/nim_sentinel/core/errors.py

## Import Cycles
- None detected.

## Communities (144 total, 15 thin omitted)

### Community 0 - "AggregatedCosts"
Cohesion: 0.11
Nodes (16): Interpreter guard for subcommands, AggregatedCosts, CostSnapshot, Snapshot of cost metrics at a point in time., Aggregated cost metrics for a role., Add a snapshot to aggregates., Test adding a failed snapshot., Test adding multiple snapshots for the same model. (+8 more)

### Community 1 - "logging.py"
Cohesion: 0.12
Nodes (19): BoundLogger, contextvars, logging_config, pathlib, pypdf, add_correlation_id(), get_logger(), hash_user_id() (+11 more)

### Community 2 - "security.py"
Cohesion: 0.07
Nodes (39): HTTPAuthorizationCredentials, jose, passlib_context, secrets, get_current_user(), get_tenant_id(), Extract and validate JWT token from Authorization header., Dependency factory to check if user has required permission. (+31 more)

### Community 3 - "=== PROMPT START ==="
Cohesion: 0.07
Nodes (29): 0. WORKING RULES (follow strictly), 10. DEPLOYMENT AND PRODUCTION READINESS, 11. DOCUMENTATION AND DIAGRAMS, 12. EXECUTION PLAN (phases; stop after each for my approval), 13. DEFINITION OF DONE, 1. TECH STACK, 2. USE ALL TYPES OF NVIDIA MODELS (config-driven model registry), 3. REPOSITORY STRUCTURE (+21 more)

### Community 4 - "get_settings"
Cohesion: 0.03
Nodes (93): BaseSettings, field_validator, hashlib, pydantic_settings, pymongo, pymongo_asynchronous_client_session, pymongo_asynchronous_database, pymongo_errors (+85 more)

### Community 5 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (25): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents) (+17 more)

### Community 6 - "RivaConfig"
Cohesion: 0.06
Nodes (36): AudioEncoding, Path, Transcribe audio using streaming recognition. Args: audio_chunks: Async…, Transcribe audio from a WAV file. Args: file_path: Path to WAV file…, Adapter for NVIDIA Riva Text-to-Speech (TTS) via gRPC. Requires a running Riva…, Initialize Riva TTS service connection., Synthesize speech from text (offline/batch). Args: text: Text to synthesize…, Synthesize speech with streaming output (online). Args: text: Text or list of… (+28 more)

### Community 7 - "TestCircuitBreaker"
Cohesion: 0.11
Nodes (11): CircuitState, StrEnum, Get current circuit breaker states., Circuit breaker states., Tests for CircuitBreaker., Test initial state is closed., Test circuit opens after failure threshold., Test circuit enters half-open after recovery timeout. (+3 more)

### Community 8 - "errors.py"
Cohesion: 0.10
Nodes (17): ApprovalRejectedError, EvaluationError, HumanApprovalRequiredError, NIM Sentinel Core Errors Module Custom exception hierarchy for the application., Base class for tool errors., Raised when a tool is not found., Raised when tool execution fails., Raised when tool arguments fail validation. (+9 more)

### Community 9 - "test_graph_checkpointer.py"
Cohesion: 0.50
Nodes (3): nim_sentinel_graph_checkpointer, pymongo_asynchronous_collection, Tests for NIM Sentinel Graph Checkpointer Module (B5)

### Community 10 - "check_models.py"
Cohesion: 0.17
Nodes (16): dotenv, fetch_available_models(), generate_models_yaml(), load_configured_roles(), main(), ModelInfo, Check if a model ID exists in the fetched list (exact or prefix match)., Load the proposed role-to-model mapping from the master prompt. Uses model IDs… (+8 more)

### Community 11 - "core/__init__.py"
Cohesion: 0.13
Nodes (23): ApprovalStatus, DocumentStatus, GuardrailAction, GuardrailType, IntentType, MessageRole, StrEnum, NIM Sentinel Core Constants Application-wide constants and enums. (+15 more)

### Community 12 - "ModelRegistry"
Cohesion: 0.04
Nodes (49): Community Hubs (Navigation), Corpus Check, God Nodes (most connected - your core abstractions), Graph Freshness, Graph Report - sp  (2026-10-03), Import Cycles, Knowledge Gaps, Suggested Questions (+41 more)

### Community 13 - "TextParser"
Cohesion: 0.21
Nodes (8): PDFParser, Parser for plain text files., Parser for PDF files using pypdf., TextParser, Tests for document parsers., Test text parser encoding fallback., Test global parser registry singleton., TestParsers

### Community 14 - "Completed Tasks"
Cohesion: 0.11
Nodes (17): 10. Environment & Security ✅, 11. Code Quality ✅, 12. Post-Phase 1 Fixes (6 items) ✅, 1. Repository Scaffold ✅, 2. Tooling Configuration ✅, 3. Configuration System ✅, 4. Core Modules ✅, 5. Model Registry ✅ (+9 more)

### Community 15 - ".__init__"
Cohesion: 0.08
Nodes (23): CitationRequiredError, ContentSafetyError, GroundednessError, GuardrailViolationError, InputGuardrailError, JailbreakDetectedError, MongoQueryError, OutputGuardrailError (+15 more)

### Community 16 - "TestModelMetrics"
Cohesion: 0.20
Nodes (6): Test recording failed call., Test average latency calculation., Test success rate calculation., Tests for ModelMetrics., Test recording successful call., TestModelMetrics

### Community 17 - "ModelError"
Cohesion: 0.14
Nodes (9): FallbackExhaustedError, ModelError, ModelRateLimitError, ModelTimeoutError, Base class for model-related errors., Raised when a model request times out., Raised when model API rate limit is hit., Raised when all model fallbacks are exhausted. (+1 more)

### Community 18 - "MongoDBCheckpointer"
Cohesion: 0.06
Nodes (32): Checkpoint, CheckpointMetadata, CheckpointTuple, RunnableConfig, get_checkpointer(), MongoDBCheckpointer, serialize_value(), Any (+24 more)

### Community 19 - "test_model_registry.py"
Cohesion: 0.05
Nodes (24): nim_sentinel_llm_model_registry, F, Reset the global model registry (for testing)., Decorator to automatically retry with fallback on failure., reset_model_registry(), with_fallback(), decorator(), wrapper() (+16 more)

### Community 20 - "NIMException"
Cohesion: 0.14
Nodes (9): AuthorizationError, NIMException, Exception, RateLimitError, Raised when rate limit is exceeded., Base exception for NIM Sentinel., Raised when input validation fails., Raised when authorization fails. (+1 more)

### Community 21 - "create_indexes.py"
Cohesion: 0.13
Nodes (20): check_index_status(), create_local_indexes(), get_embedding_dimension(), is_atlas_deployment(), load_index_definitions(), load_models_config(), print_manual_instructions(), Print manual index creation instructions for Atlas UI. (+12 more)

### Community 22 - "ModelRole"
Cohesion: 0.07
Nodes (37): BaseChatModel, Embeddings, ModelRole, Model roles in the registry., ModelUnavailableError, Raised when a model is unavailable., NIM Sentinel LLM Package Model registry, factories, fallbacks, callbacks, cost…, get_chat_model() (+29 more)

### Community 23 - "TestHybridRetriever"
Cohesion: 0.05
Nodes (31): Any, NVIDIARerank, Perform hybrid retrieval with RRF fusion and reranking. Args: query: Original…, Perform vector search., Perform full-text search., Reciprocal Rank Fusion (RRF) to combine search results. RRF score = sum(1 / (k…, Rerank candidates using NVIDIA reranker., Result of a retrieval operation with citation metadata. (+23 more)

### Community 24 - "upload_document"
Cohesion: 0.11
Nodes (15): Upload and ingest a document. Supported formats: txt, pdf, md, docx, csv, json…, upload_document(), DocumentError, DocumentNotFoundError, DocumentParseError, Base class for document processing errors., Raised when a document is not found., Raised when document parsing fails. (+7 more)

### Community 25 - "TokenChunker"
Cohesion: 0.05
Nodes (28): Chunk, Any, Fallback character-based chunking., Represents a document chunk with metadata., Chunk text semantically by paragraphs and sentences., Convert to dictionary for storage., Split text into paragraphs., Split text into sentences (simple heuristic). (+20 more)

### Community 26 - "TestTrackedCallFunctions"
Cohesion: 0.17
Nodes (8): Tests for tracked call context managers., Test tracked_chat_call., Test tracked_embedding_call., Test tracked_rerank_call., TestTrackedCallFunctions, test(), test(), test()

### Community 27 - "SupervisorDecision"
Cohesion: 0.07
Nodes (21): Decision output from supervisor node., SupervisorDecision, Analyze state using LLM and decide next node (for complex routing)., Analyze state and decide next node., Tests for SupervisorDecision dataclass., Test SupervisorDecision with valid values., Test all valid next_node values., TestSupervisorDecision (+13 more)

### Community 28 - "TestModelFactory"
Cohesion: 0.20
Nodes (6): Tests for ModelFactory., Create factory instance before each test., Test chat model creation., Test embedding model creation., Test rerank model creation., TestModelFactory

### Community 29 - "Communities (70 total, 15 thin omitted)"
Cohesion: 0.04
Nodes (56): Communities (70 total, 15 thin omitted), Community 0 - "AggregatedCosts", Community 10 - "check_models.py", Community 11 - "constants.py", Community 12 - "TestModelRegistry", Community 13 - "._initialize", Community 14 - "Completed Tasks", Community 15 - "errors.py" (+48 more)

### Community 30 - "TestCostTracker"
Cohesion: 0.06
Nodes (18): Tests for CostTracker class., Test cost calculation for a known model., Test cost calculation for unknown model returns 0., Test cost calculation for embedding model (output cost = 0)., Test recording a call., Test recording a failed call., Test getting all aggregates., Test getting aggregates for a specific role. (+10 more)

### Community 31 - "main.py"
Cohesion: 0.15
Nodes (15): FastAPI, fastapi_middleware_cors, NIM Sentinel API Module FastAPI endpoints for document ingestion and RAG…, close_mongo_connection(), connect_to_mongo(), Connect to MongoDB on startup., Close MongoDB connection on shutdown., check_model_health() (+7 more)

### Community 32 - "model_registry.py"
Cohesion: 0.07
Nodes (32): asyncio, collections_abc, contextlib, datetime, Red-team evaluation script for NIM Sentinel guardrails. Runs 30 attack queries…, functools, json, langchain_core_embeddings (+24 more)

### Community 33 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 34 - "guardrails/__init__.py"
Cohesion: 0.04
Nodes (70): dataclasses, enum, re, check_groundedness(), GroundednessResult, NIM Sentinel Guardrails - Groundedness Checking Checks if generated answers are…, Result of groundedness check., Check if answer is grounded in citations. Simple heuristic: if answer has… (+62 more)

### Community 35 - "TestOutputGuardrails"
Cohesion: 0.06
Nodes (27): GuardAction, GuardCategory, StrEnum, Reset global OutputGuardrails (for testing)., Action to take when guardrail triggers., Categories of guardrail checks., reset_output_guardrails(), asyncio (+19 more)

### Community 36 - "ConfigurationError"
Cohesion: 0.22
Nodes (6): ConfigurationError, ModelNotConfiguredError, ModelUnverifiedError, Raised when configuration is invalid or missing., Raised when a model role is not configured., Raised when attempting to use an unverified model.

### Community 37 - "EmbeddingClient"
Cohesion: 0.13
Nodes (11): EmbeddingClient, Update rate limit info from response headers., Async embedding client with batching, rate limiting, and retries., Get embedding client (lazy init)., Tests for embedding client., Test successful embedding., Test embedding empty list., Test embedding with rate limit retry. (+3 more)

### Community 38 - "GraphError"
Cohesion: 0.22
Nodes (6): GraphError, GraphInterruptError, GraphTimeoutError, Base class for LangGraph errors., Raised when graph execution is interrupted (HITL)., Raised when graph execution times out.

### Community 39 - "TestIngestionPipeline"
Cohesion: 0.13
Nodes (12): asyncio, Test global embedding client singleton., Tests for ingestion pipeline., Test successful file ingestion., Test duplicate file skipping., Test file size limit., Test ingestion with parse error., Test directory ingestion. (+4 more)

### Community 40 - "RateLimiter"
Cohesion: 0.22
Nodes (5): RateLimiter, Simple in-memory rate limiter (use Redis in production)., Check if request is allowed under rate limit., Get remaining requests in window., Reset rate limit for a key.

### Community 41 - "Any"
Cohesion: 0.16
Nodes (9): Any, Update multiple documents with tenant isolation., Delete single document with tenant isolation., Delete multiple documents with tenant isolation., Get document by content hash (for deduplication)., Add tenant_id filter to query. Raises if query already has conflicting…, Get session by thread_id., Find single document with tenant isolation. (+1 more)

### Community 42 - "repositories.py"
Cohesion: 0.15
Nodes (12): DatabaseError, Base class for database errors., Raised when tenant isolation is violated., TenantIsolationError, BaseRepository, ABC, AsyncCollection, NIM Sentinel MongoDB Repositories Repository classes for documents, chunks, and… (+4 more)

### Community 43 - "get_cost_tracker"
Cohesion: 0.15
Nodes (16): get_cost_tracker(), Get the global cost tracker instance., Reset the global cost tracker (for testing)., Context manager to track cost of an operation. Yields a dict to populate with…, reset_cost_tracker(), track_cost(), asyncio, Tests for global cost tracker functions. (+8 more)

### Community 44 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 45 - "MongoConnectionError"
Cohesion: 0.12
Nodes (11): AsyncClientSession, AsyncMongoClient, MongoConnectionError, Raised when MongoDB connection fails., Any, AsyncDatabase, Perform health check., Create a client session for transactions. (+3 more)

### Community 46 - "CriticOutput"
Cohesion: 0.08
Nodes (22): Review the generated answer., CriticOutput, Output from critic node., asyncio, fixture, Tests for Critic class., Test that critic rejects incomplete answer., Tests for critic_node function. (+14 more)

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

### Community 53 - "MongoClient"
Cohesion: 0.13
Nodes (12): MongoClient, Async MongoDB client wrapper with connection pooling and health checks.…, Close MongoDB connection., Test health check when connected., Test health check when disconnected., Test database property raises when not connected., Test session context manager., Tests for MongoClient. (+4 more)

### Community 56 - "redact_for_logging"
Cohesion: 0.10
Nodes (28): _get_git_sha(), _get_model_metadata(), _get_prompt_version(), Any, Get current git SHA for trace metadata., Decorator for tracing LLM calls with cost tracking. Args: name: Custom trace…, Get prompt/graph version from environment or config., Get standard metadata for traces. (+20 more)

### Community 59 - "TestCostTrackerThreadSafety"
Cohesion: 0.25
Nodes (4): Tests for thread safety of CostTracker., Test concurrent record_call calls., Test concurrent get_aggregates calls., TestCostTrackerThreadSafety

### Community 60 - "routes.py"
Cohesion: 0.07
Nodes (40): fastapi_responses, fastapi_security, post, pydantic, agent_query(), AgentQueryRequest, AgentQueryResponse, chat() (+32 more)

### Community 61 - "IngestionPipeline"
Cohesion: 0.13
Nodes (16): DocumentTooLargeError, Raised when document exceeds size limit., extract_metadata_from_text(), Any, Extract basic metadata from text content. Args: text: Text content Returns:…, IngestionPipeline, ingest_with_semaphore(), Any (+8 more)

### Community 62 - "ChunkRepository"
Cohesion: 0.15
Nodes (9): ChunkRepository, Run aggregation pipeline with tenant isolation injected at first $match., Repository for chunks collection with vector search support., Create multiple chunks for a document., Update embeddings for multiple chunks., Perform vector search using MongoDB Atlas Vector Search. Falls back to manual…, Manual cosine similarity search for local MongoDB without Atlas Search., Perform full-text search using MongoDB Atlas Search. Falls back to regex search… (+1 more)

### Community 63 - "TestTextCleaner"
Cohesion: 0.10
Nodes (11): Test paragraph splitting with min length., Tests for text cleaning functions., Test basic text cleaning., Test unicode normalization., Test control character removal., Test hyphenation fix., Test whitespace collapsing., Test empty line removal. (+3 more)

### Community 64 - "fixture"
Cohesion: 0.14
Nodes (7): fixture, Mock database with collection., Create DocumentRepository., Mock settings for testing., Mock database with collection., Create ChunkRepository., Create SessionRepository.

### Community 65 - "detect_jailbreak"
Cohesion: 0.09
Nodes (18): detect_jailbreak(), Detect jailbreak attempts in text using heuristic patterns. Args: text: Text to…, Test case insensitive detection., Tests for detect_jailbreak function., Test ignore instructions detection., Test forget everything detection., Test roleplay detection., Test DAN mode detection. (+10 more)

### Community 66 - "asyncio"
Cohesion: 0.10
Nodes (15): asyncio, Tests for DocumentRepository., Test creating a document., Test getting document by ID., Test updating document status., Test updating document stats., Test listing documents., Test getting document by content hash. (+7 more)

### Community 67 - "TestSessionRepository"
Cohesion: 0.14
Nodes (8): Tests for SessionRepository., Mock database with collection., Test creating a session., Test getting session by thread_id., Test getting user sessions., Test incrementing message count., Test archiving session., TestSessionRepository

### Community 68 - "decorators.py"
Cohesion: 0.15
Nodes (26): langsmith, F, NIM Sentinel Observability - Decorators Tracing decorators for LangGraph nodes,…, Decorator for tracing tool calls. Args: name: Custom trace name (defaults to…, Decorator for tracing retriever calls. Args: name: Custom trace name (defaults…, Decorator for supervisor node with standard config., Decorator for RAG subgraph nodes with standard config., Decorator for critic node with standard config. (+18 more)

### Community 69 - "CorrelationContext"
Cohesion: 0.22
Nodes (5): LogRecord, CorrelationContext, PIIRedactionFilter, Context manager for setting correlation IDs., Logging filter to redact PII and secrets from log records.

### Community 70 - "AgentState"
Cohesion: 0.05
Nodes (61): BaseCheckpointSaver, BaseMessage, CompiledStateGraph, langchain_core_messages, langchain_core_runnables, langgraph_checkpoint_base, langgraph_graph, langgraph_graph_state (+53 more)

### Community 71 - "SessionRepository"
Cohesion: 0.21
Nodes (6): Update single document with tenant isolation., Repository for conversation sessions., Create a new session., Increment message count and update last_message_at., Delete a session (soft delete - mark as deleted)., SessionRepository

### Community 72 - "TestInputGuardrails"
Cohesion: 0.09
Nodes (15): asyncio, Test check_all with heuristic only., Test check_all blocks on jailbreak., Test check_all redacts PII., Test check_all without PII redaction., Tests for InputGuardrails class., Test heuristic checks on clean text., Test heuristic detects jailbreak. (+7 more)

### Community 73 - ".find_many"
Cohesion: 0.25
Nodes (4): List documents with optional filters., Get all chunks for a document., Get sessions for a user., Find multiple documents with tenant isolation.

### Community 74 - "TestBaseRepository"
Cohesion: 0.15
Nodes (7): Tests for BaseRepository tenant isolation., Create a test repository., Test that tenant_id is required., Test tenant filter is added to query., Test tenant filter with matching existing tenant_id., Test tenant filter raises on conflicting tenant_id., TestBaseRepository

### Community 75 - "riva_adapter.py"
Cohesion: 0.10
Nodes (19): grpc, riva_client, create_riva_config_from_env(), get_riva_asr(), get_riva_tts(), NIM Sentinel Riva ASR/TTS Adapter Provides gRPC-based adapters for NVIDIA Riva…, Create RivaConfig from environment variables., Get global Riva ASR adapter instance. (+11 more)

### Community 76 - "db/__init__.py"
Cohesion: 0.11
Nodes (19): delete, test(), delete_document(), Delete a document and its chunks., NIM Sentinel Database Module MongoDB async client and repositories with tenant…, get_chunk_repository(), get_document_repository(), get_session_repository() (+11 more)

### Community 77 - "test_ingestion.py"
Cohesion: 0.18
Nodes (12): bson, fastapi_testclient, nim_sentinel_core_errors, nim_sentinel_db_client, nim_sentinel_rag_ingestion_chunker, nim_sentinel_rag_ingestion_cleaner, nim_sentinel_rag_ingestion_embedder, nim_sentinel_rag_ingestion_parsers (+4 more)

### Community 78 - "asyncio"
Cohesion: 0.09
Nodes (11): asyncio, Tests for convenience decorators., Test traced_supervisor_node., Test traced_rag_node., Test traced_critic_node., Test traced_embedder., Test traced_reranker., Test traced_vector_search. (+3 more)

### Community 79 - "ExternalServiceError"
Cohesion: 0.22
Nodes (6): ExternalServiceError, LangSmithError, NVIDIAAPIError, Base class for external service errors., Raised when NVIDIA API returns an error., Raised when LangSmith API returns an error.

### Community 80 - "TestDataAnalystAgent"
Cohesion: 0.08
Nodes (14): Test row limit enforcement adds $limit when missing., Test row limit enforcement caps existing $limit., Test full pipeline sanitization., Test sanitize_pipeline raises on invalid pipeline., Tests for DataAnalystAgent class., Test validation of valid pipeline., Test validation rejects non-allowlisted stages., Test validation rejects non-list pipeline. (+6 more)

### Community 81 - "CostTracker"
Cohesion: 0.11
Nodes (11): CostTracker, Any, Tracks cost, latency, and token usage per model role. Thread-safe for…, Calculate cost for a model call., Get aggregated costs., Get recent snapshots with optional filters., Get cost summary across all roles., Reset all tracked data. (+3 more)

### Community 82 - "TestNemoGuardClient"
Cohesion: 0.11
Nodes (14): asyncio, Test jailbreak detected., Test topic returns ON_TOPIC., Test topic returns OFF_TOPIC., Test check_all runs all checks., Test check_all handles exceptions., Tests for NemoGuardClient class., Test content safety when model unavailable. (+6 more)

### Community 83 - "close_mongo_client"
Cohesion: 0.25
Nodes (6): close_mongo_client(), Close the global MongoDB client., Tests for global client functions., Test global client singleton., Test closing global client., TestGlobalClient

### Community 84 - "EmbeddingResult"
Cohesion: 0.18
Nodes (10): mock_embed(), MockEmbeddingClient, Generate deterministic mock embedding for testing using word vectors., Mock embedding client for testing., Run smoke test with mock embeddings., test_smoke(), mock_embedding_client_prop(), mock_get_embedding_client() (+2 more)

### Community 85 - "pytest"
Cohesion: 0.14
Nodes (12): nim_sentinel_graph_nodes_critic, nim_sentinel_graph_state, nim_sentinel_graph_subgraphs_rag, nim_sentinel_graph_supervisor, nim_sentinel_guardrails_groundedness, pytest, Tests for NIM Sentinel Graph Critic Module (B4), Tests for NIM Sentinel Graph RAG Subgraph Module (B3) (+4 more)

### Community 86 - "create_dev_token"
Cohesion: 0.16
Nodes (12): Test /v1/chat endpoint with real NVIDIA models., test_chat_endpoint(), create_access_token(), create_dev_token(), Create a development JWT token for testing., Create a JWT access token., Test FastAPI endpoints with live services., Test that dev JWT token can be generated. (+4 more)

### Community 87 - "test_integration.py"
Cohesion: 0.17
Nodes (9): integration, pytest_asyncio, check_integration_prerequisites(), Integration tests for NIM Sentinel with live MongoDB Atlas and NVIDIA API.…, Test NVIDIA embedding model integration., Test that the configured embedding model is available in NVIDIA API., Test generating embeddings with the configured model., Check if all required environment variables are set for integration tests. (+1 more)

### Community 88 - "clean_text"
Cohesion: 0.25
Nodes (8): clean_text(), NIM Sentinel Text Cleaning Text cleaning and normalization for document…, Clean and normalize text content. Args: text: Raw text to clean options:…, Split text into paragraphs. Args: text: Input text min_paragraph_length:…, Remove lines that appear repeatedly (likely headers/footers). Args: text: Input…, _remove_repeated_lines(), split_into_paragraphs(), unicodedata

### Community 89 - "DocumentRepository"
Cohesion: 0.25
Nodes (5): DocumentRepository, Repository for documents collection., Create a new document record., Update document processing status., Update document chunk and token counts.

### Community 90 - "detect_injection"
Cohesion: 0.12
Nodes (14): detect_injection(), Detect prompt injection attempts in text using heuristic patterns. Args: text:…, Tests for detect_injection function., Test script tag detection., Test javascript: protocol detection., Test event handler detection., Test eval/exec detection., Test system call detection. (+6 more)

### Community 91 - "redact_messages_for_logging"
Cohesion: 0.11
Nodes (15): nim_sentinel_observability_redaction, Any, Redact PII from LangGraph state for logging. Args: state: AgentState dict…, Redact PII from message list for logging. Args: messages: List of messages…, redact_messages_for_logging(), redact_state_for_logging(), Tests for Observability - Redaction module, Tests for redact_state_for_logging function. (+7 more)

### Community 92 - "TestCreateInitialState"
Cohesion: 0.33
Nodes (4): Tests for create_initial_state factory function., Test creating initial state with required params., Test creating initial state with message history., TestCreateInitialState

### Community 93 - "create_async_client"
Cohesion: 0.13
Nodes (14): create_async_client(), asyncio, Test that /v1/chat validates request body., Test that /v1/chat/stream validates request body., Create async test client., Test that /v1/chat/stream returns SSE headers., Test /v1/agent/query endpoint., Test /v1/query endpoint. (+6 more)

### Community 94 - "TestAtlasConnection"
Cohesion: 0.25
Nodes (5): Test that fulltext_index exists and is READY on Atlas., Test MongoDB Atlas connection and index status., Test connection to MongoDB Atlas., Test that vector_index exists and is READY on Atlas., TestAtlasConnection

### Community 95 - "test_api_routes.py"
Cohesion: 0.14
Nodes (18): httpx, nim_sentinel_core_security, auth_headers(), auth_headers_chat_only(), auth_headers_invalid(), auth_headers_no_tenant(), auth_headers_read(), auth_headers_write() (+10 more)

### Community 96 - "test_cost_tracker.py"
Cohesion: 0.20
Nodes (7): nim_sentinel_core, nim_sentinel_llm_cost_tracker, Unit tests for CostTracker module., Tests for CostSnapshot dataclass., Test creating a CostSnapshot., Test CostSnapshot with error., TestCostSnapshot

### Community 97 - "make_dev_token.py"
Cohesion: 0.50
Nodes (3): argparse, main(), Generate a development JWT token for testing. Usage: python…

### Community 98 - "Current Phase: Phase 2 - MongoDB + RAG Implementation"
Cohesion: 0.40
Nodes (4): Completed Tasks:, Current Phase: Phase 2 - MongoDB + RAG Implementation, NIM Sentinel - Project Rules, Pending Tasks:

### Community 100 - "test_golden_retrieval.py"
Cohesion: 0.17
Nodes (11): langchain_core_documents, nim_sentinel_db_repositories, nim_sentinel_rag_retriever, get_golden_retrieval_examples(), get_retrieval_examples_by_category(), Get golden retrieval examples filtered by category., A single golden example for retrieval evaluation., Get all golden retrieval examples. (+3 more)

### Community 101 - "TestPIIPatterns"
Cohesion: 0.10
Nodes (10): Tests for PII detection patterns., Test email detection., Test phone number detection., Test credit card detection., Test IP address detection., Test API key detection., Test Aadhaar detection (Indian 12-digit)., Test PAN detection (Indian). (+2 more)

### Community 103 - "TestSupervisorGoldenDataset"
Cohesion: 0.13
Nodes (12): asyncio, fixture, Test that greetings route to end., Test supervisor routing against golden dataset., Test that factual queries route to rag_subgraph., Test that existing answer routes to critic., Create supervisor instance., Test that max retries routes to end. (+4 more)

### Community 104 - "reset_input_guardrails"
Cohesion: 0.12
Nodes (16): evaluate_guardrails(), load_queries(), main(), Any, Path, Evaluate guardrails on a set of queries., Load queries from JSONL file., Run red-team evaluation. (+8 more)

### Community 105 - "DataAnalystAgent"
Cohesion: 0.18
Nodes (11): AnalystResult, DataAnalystAgent, Any, Validate that pipeline only uses allowed stages. Returns: (is_valid,…, Inject tenant_id filter into the pipeline. Adds $match stage at the beginning…, Ensure pipeline has a $limit stage within bounds., Full pipeline sanitization: validate, inject tenant filter, enforce row limit., Execute a read-only aggregation query. Args: collection: Collection name (e.g.,… (+3 more)

### Community 106 - "TestTracedNode"
Cohesion: 0.12
Nodes (7): Tests for traced_node decorator., Test traced_node with async function., Test traced_node with sync function., Test traced_node redacts PII in inputs., Test traced_node without redaction., Test traced_node propagates exceptions., TestTracedNode

### Community 107 - "benchmark_model"
Cohesion: 0.17
Nodes (16): AsyncClient, benchmark_model(), call_model(), CallResult, estimate_cost(), main(), ModelSummary, print_summary_table() (+8 more)

### Community 108 - "TestRedactPII"
Cohesion: 0.12
Nodes (9): nim_sentinel_guardrails_pii, Tests for Guardrails - PII module, Tests for redact_pii function., Test email redaction., Test multiple PII redaction., Test Indian PII redaction., Test custom replacement string., Test no PII to redact. (+1 more)

### Community 109 - "TestCheckGroundedness"
Cohesion: 0.12
Nodes (9): Tests for check_groundedness function., Test groundedness fails with no citations., Test groundedness fails with empty citations., Test groundedness passes with citations but no specific claims., Test groundedness passes with specific claims and sufficient citations., Test groundedness fails with specific claims but sparse citations., Test groundedness with numeric claims., Test groundedness with entity claims. (+1 more)

### Community 110 - "GuardResult"
Cohesion: 0.18
Nodes (9): GuardrailResponse, GuardResult, Any, Check if answer leaks PII., Check content safety using NemoGuard., Run all output guardrails. Args: answer: Generated answer to check citations:…, Result of a guardrail check., Combined response from multiple guardrails. (+1 more)

### Community 111 - "redact_pii_dict"
Cohesion: 0.17
Nodes (10): Any, Recursively redact PII from dictionary values. Args: data: Dictionary to redact…, redact_pii_dict(), Tests for redact_pii_dict function., Test dict redaction with string values., Test dict redaction with nested dict., Test dict redaction with list of strings., Test dict redaction with list of dicts. (+2 more)

### Community 112 - "._get_model"
Cohesion: 0.19
Nodes (8): Any, ChatNVIDIA, Check for jailbreak attempts using NemoGuard., Check topic control using NemoGuard. Allowed topics: document queries, system…, Run all NemoGuard checks. Args: text: Text to check Returns: Dictionary with…, Get NemoGuard model from registry., Extract string content from LLM response., Check content safety using NemoGuard. Categories: hate speech, harassment,…

### Community 113 - "TestGoldenRetrievalDataset"
Cohesion: 0.18
Nodes (9): asyncio, fixture, Test retrieval quality against golden dataset., Test that retrieval results include proper citation metadata., Create a mock ChunkRepository with test data., Create a HybridRetriever with mocked dependencies., Create mock search results., Test recall@k for golden retrieval dataset. (+1 more)

### Community 114 - "TestTracedTool"
Cohesion: 0.14
Nodes (6): Test traced_tool redacts PII in kwargs., Test traced_tool propagates exceptions., Tests for traced_tool decorator., Test traced_tool with async function., Test traced_tool with sync function., TestTracedTool

### Community 115 - "TestTracedLLMCall"
Cohesion: 0.14
Nodes (6): Tests for traced_llm_call decorator., Test traced_llm_call with async function., Test traced_llm_call with sync function., Test traced_llm_call redacts PII in prompt., Test traced_llm_call propagates exceptions., TestTracedLLMCall

### Community 116 - "TestTracedRetriever"
Cohesion: 0.14
Nodes (6): Tests for traced_retriever decorator., Test traced_retriever with async function., Test traced_retriever with sync function., Test traced_retriever redacts PII in query., Test traced_retriever propagates exceptions., TestTracedRetriever

### Community 117 - "unittest_mock"
Cohesion: 0.18
Nodes (9): nim_sentinel_guardrails_input_guard, nim_sentinel_guardrails_nemoguard, nim_sentinel_guardrails_output_guard, nim_sentinel_observability_decorators, Tests for Guardrails - Input Guard module, Tests for Guardrails - NemoGuard module, Tests for Guardrails - Output Guard module, Tests for Observability - Decorators module (+1 more)

### Community 118 - "check_citation_coverage"
Cohesion: 0.19
Nodes (9): check_citation_coverage(), Any, Check if key terms from answer appear in citations. Args: answer: Generated…, Tests for check_citation_coverage function., Test full coverage of key terms., Test partial coverage., Test with no key terms., Test with custom key terms. (+1 more)

### Community 119 - "._embed_batch"
Cohesion: 0.18
Nodes (7): NVIDIAEmbeddings, Embed a batch with retry logic., Embed a single batch., Check and wait for rate limit if needed., Embed a single query text., Get or create NVIDIAEmbeddings instance., Embed a list of texts with batching and retries. Args: texts: List of texts to…

### Community 120 - "detect_all_heuristic"
Cohesion: 0.21
Nodes (8): detect_all_heuristic(), Any, Run all heuristic detections. Args: text: Text to scan Returns: Dictionary with…, Tests for detect_all_heuristic function., Test jailbreak detection only., Test injection detection only., Test both jailbreak and injection., TestDetectAllHeuristic

### Community 121 - "detect_pii"
Cohesion: 0.23
Nodes (7): detect_pii(), Detect PII in text. Args: text: Text to scan Returns: List of PIIResult for…, Test multiple PII types., Test Indian PII formats., Tests for detect_pii function., Test email detection., TestDetectPII

### Community 122 - "test_data_analyst.py"
Cohesion: 0.18
Nodes (7): nim_sentinel_agents_data_analyst, Tests for Data Analyst Agent, Tests for allowed/forbidden stage lists., Test basic stages are allowed., Test write stages are forbidden., Test no stage is both allowed and forbidden., TestAllowedStages

### Community 123 - "test_riva_adapter.py"
Cohesion: 0.22
Nodes (7): dict, nim_sentinel_llm_riva_adapter, Tests for Riva ASR/TTS Adapter, Tests for create_riva_config_from_env function., Test creating config from environment variables., Test creating config with defaults when env vars not set., TestCreateRivaConfigFromEnv

### Community 124 - ".get_parser"
Cohesion: 0.29
Nodes (5): Any, Path, Get appropriate parser for file., Parse file using appropriate parser., Parse document and return (content, metadata).

### Community 125 - ".agent"
Cohesion: 0.22
Nodes (7): get_data_analyst(), Get the global DataAnalystAgent instance., Reset the global DataAnalystAgent (for testing)., reset_data_analyst(), fixture, Test global instance getter., Create a DataAnalystAgent instance.

### Community 126 - "fixture"
Cohesion: 0.22
Nodes (5): fixture, Mock NVIDIAEmbeddings., Mock document repository., Mock chunk repository., Mock embedding client.

### Community 127 - "TestEndToEndRAG"
Cohesion: 0.22
Nodes (6): fixture, End-to-end RAG pipeline test: upload document -> ingest -> query with…, Setup MongoDB client and repositories., Test document upload and ingestion pipeline., Test that $vectorSearch aggregation runs on Atlas and returns scores., TestEndToEndRAG

### Community 128 - "BaseParser"
Cohesion: 0.29
Nodes (5): BaseParser, ABC, Register a new parser., Base parser interface., Check if parser supports this file type.

### Community 129 - "ParserRegistry"
Cohesion: 0.29
Nodes (4): ParserRegistry, Registry of document parsers., Test parser registry., Test parser registry with unsupported file.

### Community 130 - "TestEstimateCost"
Cohesion: 0.33
Nodes (5): patch, Tests for estimate_cost function., Test cost estimation., Test cost estimation with string role., TestEstimateCost

### Community 131 - ".test_execute_with_mock"
Cohesion: 0.33
Nodes (4): asyncio, Test execute_simple builds correct pipeline., Test execute with mocked MongoDB., mock_aiter()

### Community 132 - "get_golden_examples"
Cohesion: 0.33
Nodes (6): get_examples_by_category(), get_golden_examples(), GoldenExample, A single golden example for supervisor evaluation., Get all golden examples., Get golden examples filtered by category.

### Community 133 - "TestAgentState"
Cohesion: 0.33
Nodes (4): Tests for AgentState dataclass., Test AgentState initializes with defaults., Test AgentState with custom values., TestAgentState

### Community 134 - "TestIngestionConfig"
Cohesion: 0.33
Nodes (4): Tests for ingestion configuration., Test default configuration., Test custom configuration., TestIngestionConfig

### Community 135 - "NemoGuardAction"
Cohesion: 0.40
Nodes (5): NemoGuardAction, NemoGuardModel, StrEnum, NemoGuard model types., Actions from NemoGuard.

### Community 136 - ".test_upload_document_validation"
Cohesion: 0.50
Nodes (3): Test document endpoints., Test upload validation., TestDocumentEndpoints

## Knowledge Gaps
- **144 isolated node(s):** `nim-sentinel`, `graphify`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)` (+139 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1351 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_settings()` connect `get_settings` to `model_registry.py`, `logging.py`, `security.py`, `AgentState`, `DataAnalystAgent`, `core/__init__.py`, `MongoConnectionError`, `._embed_batch`, `create_indexes.py`, `create_dev_token`, `ModelRole`, `TestHybridRetriever`, `IngestionPipeline`, `main.py`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Why does `AgentState` connect `AgentState` to `get_settings`, `TestAgentState`, `TestSupervisorGoldenDataset`, `CriticOutput`, `TestHybridRetriever`, `SupervisorDecision`, `routes.py`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `Graph Report - sp  (2026-10-03)` connect `ModelRegistry` to `Communities (70 total, 15 thin omitted)`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 52 inferred relationships involving `AgentState` (e.g. with `chat_stream()` and `create_graph()`) actually correct?**
  _`AgentState` has 52 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `ModelRegistry` (e.g. with `2. USE ALL TYPES OF NVIDIA MODELS (config-driven model registry)` and `God Nodes (most connected - your core abstractions)`) actually correct?**
  _`ModelRegistry` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `get_settings()` (e.g. with `validate_indexes()` and `main()`) actually correct?**
  _`get_settings()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `CircuitBreaker` (e.g. with `God Nodes (most connected - your core abstractions)` and `Suggested Questions`) actually correct?**
  _`CircuitBreaker` has 30 INFERRED edges - model-reasoned connections that need verification._