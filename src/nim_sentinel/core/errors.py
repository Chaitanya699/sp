"""
NIM Sentinel Core Errors Module

Custom exception hierarchy for the application.
"""

from typing import Any


class NIMException(Exception):
    """Base exception for NIM Sentinel."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
        status_code: int = 500,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


# Configuration Errors
class ConfigurationError(NIMException):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="CONFIGURATION_ERROR", details=details, status_code=500)


class ModelNotConfiguredError(ConfigurationError):
    """Raised when a model role is not configured."""

    def __init__(self, role: str):
        super().__init__(
            f"Model role '{role}' is not configured",
            details={"role": role},
        )


class ModelUnverifiedError(ConfigurationError):
    """Raised when attempting to use an unverified model."""

    def __init__(self, role: str, model_id: str):
        super().__init__(
            f"Model '{model_id}' for role '{role}' is not verified in NVIDIA API",
            details={"role": role, "model_id": model_id},
        )


# Authentication & Authorization Errors
class AuthenticationError(NIMException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, Any] | None = None,
        code: str = "AUTHENTICATION_ERROR",
        status_code: int = 401,
    ):
        super().__init__(message, code=code, details=details, status_code=status_code)


class AuthorizationError(NIMException):
    """Raised when authorization fails."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: dict[str, Any] | None = None,
        code: str = "AUTHORIZATION_ERROR",
        status_code: int = 403,
    ):
        super().__init__(message, code=code, details=details, status_code=status_code)


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token is expired."""

    def __init__(self) -> None:
        super().__init__("Token has expired", code="TOKEN_EXPIRED", status_code=401)


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid."""

    def __init__(self, reason: str = "Invalid token") -> None:
        super().__init__(reason, code="INVALID_TOKEN", status_code=401)


# Rate Limiting Errors
class RateLimitError(NIMException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60, details: dict[str, Any] | None = None):
        super().__init__(
            message,
            code="RATE_LIMIT_EXCEEDED",
            details={**(details or {}), "retry_after": retry_after},
            status_code=429,
        )


# Validation Errors
class ValidationError(NIMException):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(
            message,
            code="VALIDATION_ERROR",
            details={**(details or {}), "field": field} if field else details,
            status_code=400,
        )


# Guardrails Errors
class GuardrailViolationError(NIMException):
    """Raised when a guardrail check fails."""

    def __init__(
        self,
        message: str,
        guardrail: str,
        action: str = "block",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message,
            code="GUARDRAIL_VIOLATION",
            details={**(details or {}), "guardrail": guardrail, "action": action},
            status_code=400,
        )


class InputGuardrailError(GuardrailViolationError):
    """Raised when input guardrail fails."""

    def __init__(self, guardrail: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message,
            guardrail=guardrail,
            action="block",
            details=details,
        )


class OutputGuardrailError(GuardrailViolationError):
    """Raised when output guardrail fails."""

    def __init__(self, guardrail: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message,
            guardrail=guardrail,
            action="regenerate",
            details=details,
        )


class PIIDetectedError(InputGuardrailError):
    """Raised when PII is detected in input."""

    def __init__(self, entities: list[str], details: dict[str, Any] | None = None):
        super().__init__(
            guardrail="pii_detection",
            message=f"PII detected: {', '.join(entities)}",
            details={**(details or {}), "entities": entities},
        )


class JailbreakDetectedError(InputGuardrailError):
    """Raised when jailbreak attempt is detected."""

    def __init__(self, score: float, details: dict[str, Any] | None = None):
        super().__init__(
            guardrail="jailbreak",
            message=f"Jailbreak attempt detected (score: {score:.2f})",
            details={**(details or {}), "score": score},
        )


class ContentSafetyError(InputGuardrailError):
    """Raised when content safety check fails."""

    def __init__(self, categories: list[str], details: dict[str, Any] | None = None):
        super().__init__(
            guardrail="content_safety",
            message=f"Content safety violation: {', '.join(categories)}",
            details={**(details or {}), "categories": categories},
        )


class TopicViolationError(InputGuardrailError):
    """Raised when topic control check fails."""

    def __init__(self, topic: str, details: dict[str, Any] | None = None):
        super().__init__(
            guardrail="topic_control",
            message=f"Topic not allowed: {topic}",
            details={**(details or {}), "topic": topic},
        )


class GroundednessError(OutputGuardrailError):
    """Raised when groundedness check fails."""

    def __init__(self, score: float, details: dict[str, Any] | None = None):
        super().__init__(
            guardrail="groundedness",
            message=f"Response not grounded (score: {score:.2f})",
            details={**(details or {}), "score": score},
        )


class CitationRequiredError(OutputGuardrailError):
    """Raised when citations are required but missing."""

    def __init__(self, details: dict[str, Any] | None = None):
        super().__init__(
            guardrail="citations",
            message="Citations required for knowledge-based answers",
            details=details,
        )


# Model/LLM Errors
class ModelError(NIMException):
    """Base class for model-related errors."""

    def __init__(self, message: str, model_role: str, model_id: str, details: dict[str, Any] | None = None):
        super().__init__(
            message,
            code="MODEL_ERROR",
            details={**(details or {}), "model_role": model_role, "model_id": model_id},
            status_code=502,
        )


class ModelUnavailableError(ModelError):
    """Raised when a model is unavailable."""

    def __init__(self, model_role: str, model_id: str, details: dict[str, Any] | None = None):
        super().__init__(
            f"Model '{model_id}' for role '{model_role}' is unavailable",
            model_role=model_role,
            model_id=model_id,
            details=details,
        )


class ModelTimeoutError(ModelError):
    """Raised when a model request times out."""

    def __init__(self, model_role: str, model_id: str, timeout: int, details: dict[str, Any] | None = None):
        super().__init__(
            f"Model '{model_id}' request timed out after {timeout}s",
            model_role=model_role,
            model_id=model_id,
            details={**(details or {}), "timeout": timeout},
        )


class ModelRateLimitError(ModelError):
    """Raised when model API rate limit is hit."""

    def __init__(self, model_role: str, model_id: str, retry_after: int = 60, details: dict[str, Any] | None = None):
        super().__init__(
            f"Model '{model_id}' rate limit exceeded",
            model_role=model_role,
            model_id=model_id,
            details={**(details or {}), "retry_after": retry_after},
        )
        self.status_code = 429


class FallbackExhaustedError(ModelError):
    """Raised when all model fallbacks are exhausted."""

    def __init__(self, model_role: str, tried_models: list[str], details: dict[str, Any] | None = None):
        super().__init__(
            f"All fallbacks exhausted for role '{model_role}': {', '.join(tried_models)}",
            model_role=model_role,
            model_id="",
            details={**(details or {}), "tried_models": tried_models},
        )

    @property
    def models(self) -> list[str]:
        """Get the list of models that were tried."""
        tried = self.details.get("tried_models", [])
        return tried if isinstance(tried, list) else []


# Database Errors
class DatabaseError(NIMException):
    """Base class for database errors."""

    def __init__(self, message: str, operation: str, details: dict[str, Any] | None = None):
        super().__init__(
            message,
            code="DATABASE_ERROR",
            details={**(details or {}), "operation": operation},
            status_code=503,
        )


class TenantIsolationError(DatabaseError):
    """Raised when tenant isolation is violated."""

    def __init__(self, message: str):
        super().__init__(message, "tenant_isolation")
        self.status_code = 403


class MongoConnectionError(DatabaseError):
    """Raised when MongoDB connection fails."""

    def __init__(self, message: str = "Failed to connect to MongoDB", details: dict[str, Any] | None = None):
        super().__init__(message, "connect", details)


class MongoQueryError(DatabaseError):
    """Raised when a MongoDB query fails."""

    def __init__(self, query: str, details: dict[str, Any] | None = None):
        super().__init__("MongoDB query failed", "query", {**(details or {}), "query": query})


class VectorIndexError(DatabaseError):
    """Raised when vector index operations fail."""

    def __init__(self, operation: str, details: dict[str, Any] | None = None):
        super().__init__(f"Vector index {operation} failed", operation, details)
        self.status_code = 503


# Tool/Action Errors
class ToolError(NIMException):
    """Base class for tool errors."""

    def __init__(self, message: str, tool_name: str, details: dict[str, Any] | None = None):
        super().__init__(
            message,
            code="TOOL_ERROR",
            details={**(details or {}), "tool_name": tool_name},
            status_code=500,
        )


class ToolNotFoundError(ToolError):
    """Raised when a tool is not found."""

    def __init__(self, tool_name: str):
        super().__init__(f"Tool '{tool_name}' not found", tool_name)
        self.status_code = 404


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""

    def __init__(self, tool_name: str, error: str, details: dict[str, Any] | None = None):
        super().__init__(
            f"Tool '{tool_name}' execution failed: {error}",
            tool_name,
            {**(details or {}), "error": error},
        )
        self.status_code = 500


class ToolValidationError(ToolError):
    """Raised when tool arguments fail validation."""

    def __init__(self, tool_name: str, errors: list[str], details: dict[str, Any] | None = None):
        super().__init__(
            f"Tool '{tool_name}' validation failed: {'; '.join(errors)}",
            tool_name,
            {**(details or {}), "validation_errors": errors},
        )
        self.status_code = 400


class HumanApprovalRequiredError(ToolError):
    """Raised when human approval is required for a tool."""

    def __init__(self, tool_name: str, approval_id: str, details: dict[str, Any] | None = None):
        super().__init__(
            f"Tool '{tool_name}' requires human approval",
            tool_name,
            {**(details or {}), "approval_id": approval_id, "requires_approval": True},
        )
        self.status_code = 402


class ApprovalRejectedError(ToolError):
    """Raised when human approval is rejected."""

    def __init__(self, tool_name: str, approval_id: str, reason: str = ""):
        super().__init__(
            f"Tool '{tool_name}' approval rejected: {reason}",
            tool_name,
            {"approval_id": approval_id, "reason": reason, "rejected": True},
        )
        self.status_code = 403


# Document Processing Errors
class DocumentError(NIMException):
    """Base class for document processing errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="DOCUMENT_ERROR", details=details, status_code=500)


class DocumentNotFoundError(DocumentError):
    """Raised when a document is not found."""

    def __init__(self, document_id: str):
        super().__init__(
            f"Document not found: {document_id}",
            {"document_id": document_id},
        )
        self.status_code = 404


class DocumentParseError(DocumentError):
    """Raised when document parsing fails."""

    def __init__(self, file_type: str, error: str, details: dict[str, Any] | None = None):
        super().__init__(
            f"Failed to parse {file_type} document: {error}",
            {**(details or {}), "file_type": file_type, "error": error},
        )


class DocumentTooLargeError(DocumentError):
    """Raised when document exceeds size limit."""

    def __init__(self, size_mb: float, limit_mb: float):
        super().__init__(
            f"Document size {size_mb:.1f}MB exceeds limit {limit_mb}MB",
            {"size_mb": size_mb, "limit_mb": limit_mb},
        )
        self.status_code = 413


class UnsupportedFileTypeError(DocumentError):
    """Raised when file type is not supported."""

    def __init__(self, mime_type: str, allowed: list[str]):
        super().__init__(
            f"Unsupported file type: {mime_type}",
            {"mime_type": mime_type, "allowed_types": allowed},
        )
        self.status_code = 415


# External Service Errors
class ExternalServiceError(NIMException):
    """Base class for external service errors."""

    def __init__(self, service: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            f"{service} error: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            details={**(details or {}), "service": service},
            status_code=502,
        )


class NVIDIAAPIError(ExternalServiceError):
    """Raised when NVIDIA API returns an error."""

    def __init__(self, message: str, status_code: int = 502, details: dict[str, Any] | None = None):
        super().__init__("NVIDIA API", message, {**(details or {}), "status_code": status_code})
        self.status_code = status_code


class LangSmithError(ExternalServiceError):
    """Raised when LangSmith API returns an error."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__("LangSmith", message, details)


# Graph/Workflow Errors
class GraphError(NIMException):
    """Base class for LangGraph errors."""

    def __init__(self, message: str, node: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(
            message,
            code="GRAPH_ERROR",
            details={**(details or {}), "node": node} if node else details,
            status_code=500,
        )


class GraphInterruptError(GraphError):
    """Raised when graph execution is interrupted (HITL)."""

    def __init__(self, interrupt_id: str, node: str, message: str = "Human approval required"):
        super().__init__(
            message,
            node=node,
            details={"interrupt_id": interrupt_id, "interrupted": True},
        )
        self.status_code = 402


class GraphTimeoutError(GraphError):
    """Raised when graph execution times out."""

    def __init__(self, timeout: int, node: str | None = None):
        super().__init__(
            f"Graph execution timed out after {timeout}s",
            node=node,
            details={"timeout": timeout},
        )
        self.status_code = 504


# Evaluation Errors
class EvaluationError(NIMException):
    """Raised when evaluation fails."""

    def __init__(self, message: str, component: str, details: dict[str, Any] | None = None):
        super().__init__(
            message,
            code="EVALUATION_ERROR",
            details={**(details or {}), "component": component},
            status_code=500,
        )


class ThresholdNotMetError(EvaluationError):
    """Raised when evaluation threshold is not met."""

    def __init__(self, component: str, metric: str, actual: float, threshold: float):
        super().__init__(
            f"Threshold not met for {component}.{metric}: {actual:.3f} < {threshold:.3f}",
            component,
            {"metric": metric, "actual": actual, "threshold": threshold},
        )
