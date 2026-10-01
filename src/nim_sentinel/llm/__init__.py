"""
NIM Sentinel LLM Package

Model registry, factories, fallbacks, callbacks, cost tracking, and Riva ASR/TTS adapters.
"""

from nim_sentinel.llm.model_registry import (
    CircuitBreaker,
    CircuitState,
    ModelFactory,
    ModelMetrics,
    ModelRegistry,
    get_chat_model,
    get_embedding_model,
    get_model_registry,
    get_rerank_model,
    reset_model_registry,
    tracked_chat_call,
    tracked_embedding_call,
    tracked_rerank_call,
    with_fallback,
)
from nim_sentinel.llm.riva_adapter import (
    RivaASRAdapter,
    RivaConfig,
    RivaTTSAdapter,
    create_riva_config_from_env,
    get_riva_asr,
    get_riva_tts,
    reset_riva_adapters,
)

__all__ = [
    "ModelRegistry",
    "ModelFactory",
    "CircuitBreaker",
    "CircuitState",
    "ModelMetrics",
    "get_model_registry",
    "reset_model_registry",
    "get_chat_model",
    "get_embedding_model",
    "get_rerank_model",
    "tracked_chat_call",
    "tracked_embedding_call",
    "tracked_rerank_call",
    "with_fallback",
    # Riva ASR/TTS
    "RivaASRAdapter",
    "RivaTTSAdapter",
    "RivaConfig",
    "create_riva_config_from_env",
    "get_riva_asr",
    "get_riva_tts",
    "reset_riva_adapters",
]
