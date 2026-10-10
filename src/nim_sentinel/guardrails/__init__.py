"""
NIM Sentinel Guardrails

Input and output guardrails for safety, PII protection, and groundedness.
"""

from nim_sentinel.guardrails.groundedness import (
    GroundednessResult,
    check_citation_coverage,
    check_groundedness,
)
from nim_sentinel.guardrails.input_guard import (
    GuardAction,
    GuardCategory,
    InputGuardrails,
    get_input_guardrails,
    reset_input_guardrails,
)
from nim_sentinel.guardrails.input_guard import (
    GuardrailResponse as InputGuardrailResponse,
)
from nim_sentinel.guardrails.input_guard import (
    GuardResult as InputGuardResult,
)
from nim_sentinel.guardrails.jailbreak import (
    InjectionResult,
    InjectionType,
    JailbreakResult,
    JailbreakType,
    detect_all_heuristic,
    detect_injection,
    detect_jailbreak,
)
from nim_sentinel.guardrails.nemoguard import (
    NemoGuardAction,
    NemoGuardClient,
    NemoGuardModel,
    NemoGuardResult,
    get_nemo_guard_client,
    reset_nemo_guard_client,
)
from nim_sentinel.guardrails.output_guard import (
    GuardrailResponse as OutputGuardrailResponse,
)
from nim_sentinel.guardrails.output_guard import (
    GuardResult as OutputGuardResult,
)
from nim_sentinel.guardrails.output_guard import (
    OutputGuardrails,
    get_output_guardrails,
    reset_output_guardrails,
)
from nim_sentinel.guardrails.pii import (
    PII_PATTERNS,
    PIIResult,
    detect_pii,
    redact_pii,
    redact_pii_dict,
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
