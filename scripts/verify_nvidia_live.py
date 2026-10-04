#!/usr/bin/env python3
"""
Verify NVIDIA API models work with real API key.
Tests embedding, reranker, and LLM models.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings, NVIDIARerank, ChatNVIDIA
from nim_sentinel.core.config import get_settings, get_model_config


async def test_embedding_model(model_id: str, api_key: str):
    """Test embedding model with real API."""
    print(f"\n{'='*60}")
    print(f"Testing Embedding Model: {model_id}")
    print(f"{'='*60}")

    try:
        embeddings = NVIDIAEmbeddings(model=model_id, api_key=api_key, truncate="END")

        # Test with 2 small texts
        texts = [
            "NIM Sentinel is an enterprise RAG system.",
            "It uses hybrid retrieval with vector and text search."
        ]

        print(f"Embedding {len(texts)} texts...")
        result = await embeddings.aembed_documents(texts)

        print(f"[PASS] Success!")
        print(f"  Number of embeddings: {len(result)}")
        print(f"  Vector dimension: {len(result[0])}")
        print(f"  First vector (first 5 dims): {result[0][:5]}")
        print(f"  Second vector (first 5 dims): {result[1][:5]}")

        # Also test query embedding
        query_emb = await embeddings.aembed_query("What is NIM Sentinel?")
        print(f"  Query embedding dimension: {len(query_emb)}")

        return True, len(result[0])

    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        return False, 0


async def test_reranker_model(model_id: str, api_key: str):
    """Test reranker model with real API."""
    print(f"\n{'='*60}")
    print(f"Testing Reranker Model: {model_id}")
    print(f"{'='*60}")

    try:
        reranker = NVIDIARerank(model=model_id, api_key=api_key, top_n=3)

        query = "What is NIM Sentinel?"
        passages = [
            "NIM Sentinel is an enterprise multi-agent RAG system with NVIDIA NIM integration.",
            "It provides document ingestion, hybrid retrieval, and citation-backed responses.",
            "The system uses MongoDB for storage and supports tenant isolation.",
            "Unrelated passage about cooking recipes and ingredients.",
            "Another unrelated text about weather forecasting and climate models."
        ]

        print(f"Reranking {len(passages)} passages for query: '{query}'")

        # Use acompress_documents which is the async method
        from langchain_core.documents import Document
        docs = [Document(page_content=p, metadata={"source": f"doc_{i}"}) for i, p in enumerate(passages)]

        result = await reranker.acompress_documents(documents=docs, query=query)

        print(f"[PASS] Success!")
        print(f"  Returned {len(result)} reranked passages:")
        for i, doc in enumerate(result):
            score = doc.metadata.get("relevance_score", "N/A")
            print(f"    {i+1}. Score: {score:.4f} - {doc.page_content[:80]}...")

        return True

    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        return False


async def test_llm_model(model_id: str, api_key: str):
    """Test LLM model with real API."""
    print(f"\n{'='*60}")
    print(f"Testing LLM Model: {model_id}")
    print(f"{'='*60}")

    try:
        llm = ChatNVIDIA(model=model_id, api_key=api_key, temperature=0.1, max_tokens=100)

        messages = [
            ("system", "You are a helpful assistant. Answer briefly."),
            ("human", "What is NIM Sentinel in one sentence?")
        ]

        print(f"Sending chat completion request...")
        result = await llm.ainvoke(messages)

        print(f"[PASS] Success!")
        print(f"  Response: {result.content[:200]}")

        return True

    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        return False


async def main():
    """Run all verification tests."""
    settings = get_settings()
    api_key = settings.nvidia_api_key

    if not api_key or api_key.startswith("your_"):
        print("ERROR: NVIDIA_API_KEY not configured in .env")
        return 1

    # Mask key for display - don't print any part of the key
    print("Using NVIDIA API Key: [REDACTED]")

    # Get models from config
    embedding_config = get_model_config("embedding")
    reranker_config = get_model_config("reranker")
    supervisor_config = get_model_config("supervisor_llm")

    print(f"\nConfigured models:")
    print(f"  Embedding: {embedding_config.primary} (fallback: {embedding_config.fallback})")
    print(f"  Reranker: {reranker_config.primary} (fallback: {reranker_config.fallback})")
    print(f"  Supervisor LLM: {supervisor_config.primary} (fallback: {supervisor_config.fallback})")

    results = {}

    # Test embedding
    emb_success, emb_dim = await test_embedding_model(embedding_config.primary, api_key)
    results["embedding"] = {"model": embedding_config.primary, "success": emb_success, "dim": emb_dim}

    if not emb_success and embedding_config.fallback:
        print(f"\nTrying fallback embedding model: {embedding_config.fallback}")
        emb_success, emb_dim = await test_embedding_model(embedding_config.fallback, api_key)
        results["embedding_fallback"] = {"model": embedding_config.fallback, "success": emb_success, "dim": emb_dim}

    # Test reranker
    rerank_success = await test_reranker_model(reranker_config.primary, api_key)
    results["reranker"] = {"model": reranker_config.primary, "success": rerank_success}

    if not rerank_success and reranker_config.fallback:
        print(f"\nTrying fallback reranker model: {reranker_config.fallback}")
        rerank_success = await test_reranker_model(reranker_config.fallback, api_key)
        results["reranker_fallback"] = {"model": reranker_config.fallback, "success": rerank_success}

    # Test supervisor LLM
    llm_success = await test_llm_model(supervisor_config.primary, api_key)
    results["supervisor_llm"] = {"model": supervisor_config.primary, "success": llm_success}

    if not llm_success and supervisor_config.fallback:
        print(f"\nTrying fallback supervisor LLM: {supervisor_config.fallback}")
        llm_success = await test_llm_model(supervisor_config.fallback, api_key)
        results["supervisor_llm_fallback"] = {"model": supervisor_config.fallback, "success": llm_success}

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for key, val in results.items():
        status = "[PASS] PASS" if val["success"] else "[FAIL] FAIL"
        model = val["model"]
        extra = f" (dim: {val['dim']})" if "dim" in val else ""
        print(f"  {status} - {key}: {model}{extra}")

    all_passed = all(v["success"] for v in results.values())
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)