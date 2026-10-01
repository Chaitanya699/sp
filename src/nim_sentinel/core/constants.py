"""
NIM Sentinel Core Constants

Application-wide constants and enums.
"""

from enum import StrEnum
from typing import Final


class ModelRole(StrEnum):
    """Model roles in the registry."""
    SUPERVISOR_LLM = "supervisor_llm"
    REASONING_LLM = "reasoning_llm"
    GENERATOR_LLM = "generator_llm"
    CODE_LLM = "code_llm"
    EMBEDDING = "embedding"
    RERANKER = "reranker"
    VISION_LLM = "vision_llm"
    OCR = "ocr"
    ASR = "asr"
    TTS = "tts"
    SAFETY_CONTENT = "safety_content"
    SAFETY_TOPIC = "safety_topic"
    SAFETY_JAILBREAK = "safety_jailbreak"
    JUDGE_LLM = "judge_llm"


class IntentType(StrEnum):
    """User intent classification."""
    KNOWLEDGE_QUESTION = "knowledge_question"
    DATA_ANALYTICS = "data_analytics"
    DOCUMENT_ANALYSIS = "document_analysis"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    WEB_RESEARCH = "web_research"
    ACTION = "action"
    CLARIFICATION = "clarification"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class GuardrailAction(StrEnum):
    """Guardrail action types."""
    BLOCK = "block"
    FLAG = "flag"
    LOG = "log"
    REDACT = "redact"
    REGENERATE = "regenerate"


class GuardrailType(StrEnum):
    """Guardrail types."""
    INPUT = "input"
    OUTPUT = "output"
    TOOL = "tool"


class MessageRole(StrEnum):
    """Message roles in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class DocumentStatus(StrEnum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ThreadStatus(StrEnum):
    """Conversation thread status."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ApprovalStatus(StrEnum):
    """Human approval status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ToolRiskLevel(StrEnum):
    """Tool risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# API Constants
API_VERSION: Final[str] = "v1"
API_PREFIX: Final[str] = f"/api/{API_VERSION}"

# Default limits
DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 100
DEFAULT_TIMEOUT_SECONDS: Final[int] = 30
MAX_TOKENS_PER_REQUEST: Final[int] = 100000
MAX_COST_PER_REQUEST_USD: Final[float] = 5.0

# MongoDB Collections
COLLECTION_DOCUMENTS: Final[str] = "documents"
COLLECTION_CHUNKS: Final[str] = "chunks"
COLLECTION_SESSIONS: Final[str] = "sessions"
COLLECTION_CHECKPOINTS: Final[str] = "checkpoints"
COLLECTION_MEMORY: Final[str] = "long_term_memory"
COLLECTION_AUDIT_LOGS: Final[str] = "audit_logs"
COLLECTION_EVAL_RESULTS: Final[str] = "eval_results"
COLLECTION_USERS: Final[str] = "users"
COLLECTION_API_KEYS: Final[str] = "api_keys"

# Vector Search
VECTOR_INDEX_NAME: Final[str] = "vector_index"
VECTOR_DIMENSIONS: Final[int] = 1024  # NV-Embed-QA dimensions
FULLTEXT_INDEX_NAME: Final[str] = "fulltext_index"

# Redis Keys
REDIS_RATE_LIMIT_PREFIX: Final[str] = "ratelimit:"
REDIS_CACHE_PREFIX: Final[str] = "cache:"
REDIS_SESSION_PREFIX: Final[str] = "session:"
REDIS_CHECKPOINT_PREFIX: Final[str] = "checkpoint:"

# LangSmith
LANGSMITH_PROJECT_DEV: Final[str] = "nim-sentinel-dev"
LANGSMITH_PROJECT_STAGING: Final[str] = "nim-sentinel-staging"
LANGSMITH_PROJECT_PROD: Final[str] = "nim-sentinel-prod"

# Tracing
TRACE_SAMPLING_RATE_DEV: Final[float] = 1.0
TRACE_SAMPLING_RATE_STAGING: Final[float] = 1.0
TRACE_SAMPLING_RATE_PROD: Final[float] = 0.2
TRACE_SAMPLING_RATE_ERRORS: Final[float] = 1.0

# Evaluation
EVAL_DETERMINISTIC_SEED: Final[int] = 42
EVAL_TEMPERATURE: Final[float] = 0.0

# File Processing
MAX_FILE_SIZE_MB: Final[int] = 50
MAX_FILES_PER_REQUEST: Final[int] = 10
SUPPORTED_DOCUMENT_TYPES: Final[list[str]] = [
    "pdf",
    "txt",
    "docx",
    "xlsx",
    "csv",
]
SUPPORTED_IMAGE_TYPES: Final[list[str]] = [
    "png",
    "jpg",
    "jpeg",
    "webp",
]
SUPPORTED_AUDIO_TYPES: Final[list[str]] = [
    "wav",
    "mp3",
    "m4a",
    "flac",
]

# Chunking
DEFAULT_CHUNK_SIZE: Final[int] = 1000
DEFAULT_CHUNK_OVERLAP: Final[int] = 200
MIN_CHUNK_SIZE: Final[int] = 100
MAX_CHUNK_SIZE: Final[int] = 4000

# Retrieval
DEFAULT_TOP_K: Final[int] = 20
DEFAULT_RERANK_TOP_K: Final[int] = 5
DEFAULT_RELEVANCE_THRESHOLD: Final[float] = 0.6
MAX_REWRITE_ATTEMPTS: Final[int] = 2

# Graph
MAX_GRAPH_STEPS: Final[int] = 50
MAX_GRAPH_RETRIES: Final[int] = 3
CRITIC_MAX_RETRIES: Final[int] = 2
CRITIC_SCORE_THRESHOLD: Final[float] = 0.7

# HITL
HITL_DEFAULT_TIMEOUT_MINUTES: Final[int] = 30
HITL_DEFAULT_DECISION: Final[str] = "reject"

# Memory
SHORT_TERM_TOKEN_LIMIT: Final[int] = 8000
LONG_TERM_EMBEDDING_MODEL: Final[str] = "embedding"

# PII Entities
PII_ENTITIES: Final[list[str]] = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "US_SSN",
    "IN_AADHAAR",
    "IN_PAN",
    "IP_ADDRESS",
    "API_KEY",
    "PASSWORD",
    "CRYPTO_WALLET",
    "IBAN",
    "PASSPORT_NUMBER",
    "DRIVER_LICENSE",
]

# Secret Patterns
SECRET_PATTERNS: Final[list[str]] = [
    r"api[_-]?key\s*[:=]\s*[^\s]+",
    r"secret[_-]?key\s*[:=]\s*[^\s]+",
    r"access[_-]?token\s*[:=]\s*[^\s]+",
    r"password\s*[:=]\s*[^\s]+",
    r"bearer\s+[a-zA-Z0-9_-]+",
    r"sk-[a-zA-Z0-9]{48}",
    r"nvapi-[a-zA-Z0-9_-]+",
    r"ghp_[a-zA-Z0-9]{36}",
    r"glpat-[a-zA-Z0-9_-]{20}",
]

# Health Check
HEALTH_CHECK_TIMEOUT: Final[int] = 5

# Version
VERSION: Final[str] = "0.1.0"
