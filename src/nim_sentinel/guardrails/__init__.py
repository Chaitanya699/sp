"""
NIM Sentinel Guardrails

Input and output guardrails for safety, PII protection, and groundedness.
"""

from nim_sentinel.guardrails.groundedness import (
    check_groundedness,
    check_citation_coverage,
    GroundednessResult,
)
from nim_sentinel.guardrails.input_guard import (
    InputGuardrails,
    GuardrailResponse as InputGuardrailResponse,
    GuardResult as InputGuardResult,
    GuardAction,
    GuardCategory,
    get_input_guardrails,
    reset_input_guardrails,
)
from nim_sentinel.guardrails.jailbreak import (
    detect_jailbreak,
    detect_injection,
    detect_all_heuristic,
    JailbreakResult,
    InjectionResult,
    JailbreakType,
    InjectionType,
)
from nim_sentinel.guardrails.nemoguard import (
    NemoGuardClient,
    NemoGuardResult,
    NemoGuardModel,
    NemoGuardAction,
    get_nemo_guard_client,
    reset_nemo_guard_client,
)
from nim_sentinel.guardrails.output_guard import (
    OutputGuardrails,
    GuardrailResponse as OutputGuardrailResponse,
    GuardResult as OutputGuardResult,
    get_output_guardrails,
    reset_output_guardrails,
)
from nim_sentinel.guardrails.pii import (
    detect_pii,
    redact_pii,
    redact_pii_dict,
    PIIResult,
    PII_PATTERNS,
)

__all__ = [
    # PII
    "detect_pii",
    "redact_pii",
    "redact_pii_dict",
    "PIIResult",
    "PII_PATTERNS",
    # Jailbreak/Injection
    "detect_jailbreak",
    "detect_injection",
    "detect_all_heuristic",
    "JailbreakResult",
    "InjectionResult",
    "JailbreakType",
    "InjectionType",
    # NemoGuard
    "NemoGuardClient",
    "NemoGuardResult",
    "NemoGuardModel",
    "NemoGuardAction",
    "get_nemo_guard_client",
    "reset_nemo_guard_client",
    # Input Guard
    "InputGuardrails",
    "InputGuardrailResponse",
    "InputGuardResult",
    "GuardAction",
    "GuardCategory",
    "get_input_guardrails",
    "reset_input_guardrails",
    # Output Guard
    "OutputGuardrails",
    "OutputGuardrailResponse",
    "OutputGuardResult",
    "get_output_guardrails",
    "reset_output_guardrails",
    # Groundedness
    "check_groundedness",
    "check_citation_coverage",
    "GroundednessResult",
]