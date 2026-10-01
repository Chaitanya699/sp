#!/usr/bin/env python3
"""
NVIDIA Model Health Check Script

Fetches available models from NVIDIA API and verifies configured models.
Run with: python scripts/check_models.py
Requires NVIDIA_API_KEY in environment or .env file.
"""

import asyncio
import os
import sys
from dataclasses import dataclass

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings, NVIDIARerank
except ImportError as e:
    print(f"ERROR: Missing langchain-nvidia-ai-endpoints: {e}")
    print("Install with: pip install langchain-nvidia-ai-endpoints")
    sys.exit(1)


@dataclass
class ModelInfo:
    id: str
    name: str
    type: str  # chat, embedding, rerank, vision, etc.
    owned_by: str = ""
    verified: bool = True


@dataclass
class RoleVerification:
    role: str
    primary_model: str
    fallback_model: str
    primary_verified: bool
    fallback_verified: bool
    primary_in_list: bool
    fallback_in_list: bool
    notes: str = ""


async def fetch_available_models() -> dict[str, list[ModelInfo]]:
    """Fetch all available models from NVIDIA API categorized by type."""
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("ERROR: NVIDIA_API_KEY not set in environment or .env")
        sys.exit(1)

    print(f"Using NVIDIA API key: {api_key[:8]}...{api_key[-4:]}")
    print("Fetching available models from NVIDIA...")

    results = {"chat": [], "embedding": [], "rerank": [], "vision": [], "other": []}

    # Fetch chat models
    try:
        chat_models = ChatNVIDIA.get_available_models()
        for m in chat_models:
            # Handle both dict and Model object responses
            if hasattr(m, 'id'):
                model_id = m.id
                name = getattr(m, 'name', model_id)
                owned_by = getattr(m, 'owned_by', 'nvidia')
            else:
                model_id = m.get("id", m.get("model", ""))
                name = m.get("name", model_id)
                owned_by = m.get("owned_by", "nvidia")
            if model_id:
                results["chat"].append(ModelInfo(
                    id=model_id,
                    name=name,
                    type="chat",
                    owned_by=owned_by
                ))
        print(f"  Chat models: {len(results['chat'])}")
    except Exception as e:
        print(f"  WARNING: Failed to fetch chat models: {e}")

    # Fetch embedding models
    try:
        embed_models = NVIDIAEmbeddings.get_available_models()
        for m in embed_models:
            if hasattr(m, 'id'):
                model_id = m.id
                name = getattr(m, 'name', model_id)
                owned_by = getattr(m, 'owned_by', 'nvidia')
            else:
                model_id = m.get("id", m.get("model", ""))
                name = m.get("name", model_id)
                owned_by = m.get("owned_by", "nvidia")
            if model_id:
                results["embedding"].append(ModelInfo(
                    id=model_id,
                    name=name,
                    type="embedding",
                    owned_by=owned_by
                ))
        print(f"  Embedding models: {len(results['embedding'])}")
    except Exception as e:
        print(f"  WARNING: Failed to fetch embedding models: {e}")

    # Fetch rerank models
    try:
        rerank_models = NVIDIARerank.get_available_models()
        for m in rerank_models:
            if hasattr(m, 'id'):
                model_id = m.id
                name = getattr(m, 'name', model_id)
                owned_by = getattr(m, 'owned_by', 'nvidia')
            else:
                model_id = m.get("id", m.get("model", ""))
                name = m.get("name", model_id)
                owned_by = m.get("owned_by", "nvidia")
            if model_id:
                results["rerank"].append(ModelInfo(
                    id=model_id,
                    name=name,
                    type="rerank",
                    owned_by=owned_by
                ))
        print(f"  Rerank models: {len(results['rerank'])}")
    except Exception as e:
        print(f"  WARNING: Failed to fetch rerank models: {e}")

    return results


def verify_model_in_list(model_id: str, model_list: list[ModelInfo]) -> bool:
    """Check if a model ID exists in the fetched list (exact or prefix match)."""
    for m in model_list:
        if m.id == model_id or m.id.startswith(model_id + "/") or model_id.startswith(m.id + "/"):
            return True
    return False


def load_configured_roles() -> dict[str, dict[str, str]]:
    """Load the proposed role-to-model mapping from the master prompt.

    Uses model IDs verified against NVIDIA API list.
    Riva ASR/TTS models require separate NIM deployment (gRPC), not available via ChatNVIDIA API.
    """
    return {
        "supervisor_llm": {
            "primary": "meta/llama-3.1-8b-instruct",
            "fallback": "nvidia/nemotron-3-ultra-550b-a55b",
        },
        "reasoning_llm": {
            "primary": "meta/llama-3.3-70b-instruct",
            "fallback": "nvidia/nemotron-3-ultra-550b-a55b",
        },
        "generator_llm": {
            "primary": "meta/llama-3.1-70b-instruct",
            "fallback": "mistralai/mistral-large-3-675b-instruct-2512",
        },
        "code_llm": {
            "primary": "qwen/qwen2.5-coder-32b-instruct",
            "fallback": "mistralai/codestral-22b-instruct-v0.1",
        },
        "embedding": {
            "primary": "nvidia/nv-embedqa-e5-v5",
            "fallback": "nvidia/llama-3.2-nv-embedqa-1b-v2",
        },
        "reranker": {
            "primary": "nvidia/llama-3.2-nv-rerankqa-1b-v1",
            "fallback": "nvidia/llama-nemotron-rerank-1b-v2",
        },
        "vision_llm": {
            "primary": "meta/llama-3.2-90b-vision-instruct",
            "fallback": "microsoft/phi-3.5-vision-instruct",
        },
        "ocr": {
            "primary": "nvidia/nemoretriever-parse",
            "fallback": "",
        },
        "asr": {
            "primary": "nvidia/riva-parakeet",
            "fallback": "",
            "note": "Requires separate Riva NIM deployment (gRPC), not available via ChatNVIDIA API"
        },
        "tts": {
            "primary": "nvidia/riva-fastpitch",
            "fallback": "",
            "note": "Requires separate Riva NIM deployment (gRPC), not available via ChatNVIDIA API"
        },
        "safety_content": {
            "primary": "nvidia/llama-3.1-nemoguard-8b-content-safety",
            "fallback": "ibm/granite-guardian-3.0-8b",
        },
        "safety_topic": {
            "primary": "nvidia/llama-3.1-nemoguard-8b-topic-control",
            "fallback": "meta/llama-guard-4-12b",
        },
        "safety_jailbreak": {
            "primary": "nvidia/llama-3.1-nemoguard-8b-jailbreak-detect",
            "fallback": "meta/llama-guard-4-12b",
            "note": "Jailbreak detect model not explicitly listed; using llama-guard as fallback"
        },
        "judge_llm": {
            "primary": "meta/llama-3.3-70b-instruct",
            "fallback": "nvidia/nemotron-3-ultra-550b-a55b",
        },
    }


async def main():
    print("=" * 60)
    print("NIM Sentinel - NVIDIA Model Verification")
    print("=" * 60)

    # Fetch available models
    available = await fetch_available_models()

    # Flatten all models for searching
    all_models = []
    for _cat in available.values():
        all_models.extend(_cat)

    print(f"\nTotal models available: {len(all_models)}")

    # Load configured roles
    roles = load_configured_roles()

    # Verify each role
    verifications: list[RoleVerification] = []
    print("\n" + "=" * 60)
    print("ROLE VERIFICATION RESULTS")
    print("=" * 60)

    for role, models in roles.items():
        primary = models["primary"]
        fallback = models["fallback"]
        note = models.get("note", "")

        # Determine which category to search
        if role in ["embedding"]:
            search_list = available["embedding"]
        elif role in ["reranker"]:
            search_list = available["rerank"]
        elif role in ["vision_llm", "ocr"]:
            search_list = available["vision"] + available["chat"]  # vision models may be in chat
        else:
            search_list = available["chat"] + available["vision"]

        primary_verified = verify_model_in_list(primary, search_list) if primary else False
        fallback_verified = verify_model_in_list(fallback, search_list) if fallback else False

        # Also check in all models as fallback
        if not primary_verified and primary:
            primary_verified = verify_model_in_list(primary, all_models)
        if not fallback_verified and fallback:
            fallback_verified = verify_model_in_list(fallback, all_models)

        primary_in_list = primary_verified
        fallback_in_list = fallback_verified

        notes = note
        if not primary_verified and primary and not note:
            notes += f" PRIMARY NOT FOUND: {primary};"
        if fallback and not fallback_verified and not note:
            notes += f" FALLBACK NOT FOUND: {fallback};"
        if not primary and not fallback:
            notes = "NO MODELS CONFIGURED"

        v = RoleVerification(
            role=role,
            primary_model=primary,
            fallback_model=fallback,
            primary_verified=primary_verified,
            fallback_verified=fallback_verified,
            primary_in_list=primary_in_list,
            fallback_in_list=fallback_in_list,
            notes=notes.strip()
        )
        verifications.append(v)

        # Print result
        status = "[OK]" if (primary_verified or (fallback and fallback_verified)) else "[FAIL]"
        print(f"\n{status} {role}")
        print(f"    Primary:   {primary}  {'[OK]' if primary_verified else '[FAIL] NOT IN API LIST'}")
        if fallback:
            print(f"    Fallback:  {fallback}  {'[OK]' if fallback_verified else '[FAIL] NOT IN API LIST'}")
        if notes:
            print(f"    Notes:     {notes}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    verified_count = sum(1 for v in verifications if v.primary_verified or v.fallback_verified)
    total_count = len(verifications)
    print(f"Roles with at least one verified model: {verified_count}/{total_count}")

    unverified_roles = [v.role for v in verifications if not v.primary_verified and not v.fallback_verified]
    if unverified_roles:
        print(f"Roles with NO verified models: {', '.join(unverified_roles)}")

    # Output JSON for models.yaml generation
    print("\n" + "=" * 60)
    print("MODELS.YAML CONFIG (copy to configs/models.yaml)")
    print("=" * 60)

    yaml_output = generate_models_yaml(verifications, available)
    print(yaml_output)

    # Save to file
    output_path = "configs/models.yaml"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(yaml_output)
    print(f"\nSaved to {output_path}")

    # Exit code: 0 if all critical roles have at least one verified model
    critical_roles = ["supervisor_llm", "reasoning_llm", "generator_llm", "embedding", "reranker"]
    critical_ok = all(
        any(v.role == r and (v.primary_verified or v.fallback_verified) for v in verifications)
        for r in critical_roles
    )
    sys.exit(0 if critical_ok else 1)


def generate_models_yaml(verifications: list[RoleVerification], available: dict[str, list[ModelInfo]]) -> str:
    """Generate models.yaml content with verified/unverified markers."""
    lines = [
        "# NIM Sentinel Model Registry",
        "# Generated by scripts/check_models.py",
        "# Models marked 'unverified: true' were NOT found in NVIDIA API list",
        "# Replace with verified alternatives before production use",
        "",
        "model_registry:",
    ]

    for v in verifications:
        primary_unverified = not v.primary_verified and v.primary_model
        fallback_unverified = not v.fallback_verified and v.fallback_model

        lines.append(f"  {v.role}:")
        lines.append(f"    primary: \"{v.primary_model}\"")
        if primary_unverified:
            lines.append("    primary_unverified: true")
        lines.append(f"    fallback: \"{v.fallback_model}\"")
        if fallback_unverified:
            lines.append("    fallback_unverified: true")
        lines.append("    temperature: 0.1")
        lines.append("    max_tokens: 4096")
        lines.append("    timeout_seconds: 30")
        lines.append("    max_retries: 3")
        if v.notes:
            lines.append(f"    note: \"{v.notes}\"")
        lines.append("")

    # Add model metadata section
    lines.append("# Model metadata (auto-populated from API)")
    lines.append("model_metadata:")
    for _cat, models in available.items():
        for m in models:
            lines.append(f"  {m.id}:")
            lines.append(f"    name: \"{m.name}\"")
            lines.append(f"    type: \"{m.type}\"")
            lines.append(f"    owned_by: \"{m.owned_by}\"")
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    asyncio.run(main())
