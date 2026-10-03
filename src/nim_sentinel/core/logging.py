"""
NIM Sentinel Core Logging Module

Structured logging with PII redaction, correlation IDs, and LangSmith integration.
"""

import logging
import logging.config
import re
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Callable, Mapping, MutableMapping

import structlog
import yaml
from nim_sentinel.core.config import get_settings

# Context variables for correlation tracking
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
session_id_var: ContextVar[str | None] = ContextVar("session_id", default=None)
tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)
trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


class PIIRedactionFilter(logging.Filter):
    """Logging filter to redact PII and secrets from log records."""

    def __init__(self, patterns: list[str] | None = None):
        super().__init__()
        self.patterns = patterns or [
            r"api[_-]?key\s*[:=]\s*[^\s]+",
            r"secret[_-]?key\s*[:=]\s*[^\s]+",
            r"access[_-]?token\s*[:=]\s*[^\s]+",
            r"password\s*[:=]\s*[^\s]+",
            r"bearer\s+[a-zA-Z0-9_-]+",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{12}\b",  # Aadhaar
            r"\b[A-Z]{5}\d{4}[A-Z]\b",  # PAN
            r"sk-[a-zA-Z0-9]{48}",  # OpenAI-style keys
            r"nvapi-[a-zA-Z0-9_-]+",  # NVIDIA API keys
        ]
        self.compiled = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    def filter(self, record: logging.LogRecord) -> bool:
        # Redact from message
        if hasattr(record, "msg") and isinstance(record.msg, str):
            record.msg = self._redact(record.msg)

        # Redact from args
        if record.args:
            record.args = tuple(
                self._redact(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )

        return True

    def _redact(self, text: str) -> str:
        for pattern in self.compiled:
            text = pattern.sub("[REDACTED]", text)
        return text


def add_correlation_id(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> Mapping[str, Any] | str | bytes | bytearray | tuple[Any, ...]:
    """Add correlation ID and context to log events."""
    corr_id = correlation_id_var.get()
    if corr_id:
        event_dict["correlation_id"] = corr_id

    user_id = user_id_var.get()
    if user_id:
        event_dict["user_id_hash"] = hash_user_id(user_id)

    session_id = session_id_var.get()
    if session_id:
        event_dict["session_id"] = session_id

    tenant_id = tenant_id_var.get()
    if tenant_id:
        event_dict["tenant_id"] = tenant_id

    trace_id = trace_id_var.get()
    if trace_id:
        event_dict["trace_id"] = trace_id

    return event_dict


def hash_user_id(user_id: str) -> str:
    """Hash user ID for privacy-preserving logging."""
    import hashlib
    return hashlib.sha256(user_id.encode()).hexdigest()[:16]


def setup_logging(config_path: str | None = None) -> None:
    """Configure structured logging from YAML config."""
    settings = get_settings()

    if config_path is None:
        config_path = str(settings.config_dir / "logging.yaml")

    # Ensure log directory exists
    Path("logs").mkdir(exist_ok=True)

    # Load YAML config
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Apply logging config
    logging.config.dictConfig(config)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            add_correlation_id,
            structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer(),  # type: ignore[list-item]
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]


class CorrelationContext:
    """Context manager for setting correlation IDs."""

    def __init__(
        self,
        correlation_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        tenant_id: str | None = None,
        trace_id: str | None = None,
    ):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = session_id
        self.tenant_id = tenant_id
        self.trace_id = trace_id
        self._tokens: list[Any] = []

    def __enter__(self) -> "CorrelationContext":
        self._tokens.append(correlation_id_var.set(self.correlation_id))
        if self.user_id:
            self._tokens.append(user_id_var.set(self.user_id))
        if self.session_id:
            self._tokens.append(session_id_var.set(self.session_id))
        if self.tenant_id:
            self._tokens.append(tenant_id_var.set(self.tenant_id))
        if self.trace_id:
            self._tokens.append(trace_id_var.set(self.trace_id))
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        for token in reversed(self._tokens):
            if token.var is correlation_id_var:
                correlation_id_var.reset(token)
            elif token.var is user_id_var:
                user_id_var.reset(token)
            elif token.var is session_id_var:
                session_id_var.reset(token)
            elif token.var is tenant_id_var:
                tenant_id_var.reset(token)
            elif token.var is trace_id_var:
                trace_id_var.reset(token)


def log_audit(
    action: str,
    user_id: str,
    resource: str,
    resource_id: str,
    outcome: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Log an audit event."""
    logger = get_logger("nim_sentinel.audit")
    logger.info(
        "audit_event",
        action=action,
        user_id_hash=hash_user_id(user_id),
        resource=resource,
        resource_id=resource_id,
        outcome=outcome,
        details=details or {},
    )
