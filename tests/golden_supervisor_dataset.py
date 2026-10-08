"""
Golden Retrieval Dataset for NIM Sentinel Supervisor Evaluation

This dataset contains 20 query examples with expected routing decisions
for evaluating the supervisor's routing accuracy.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class GoldenExample:
    """A single golden example for supervisor evaluation."""
    query: str
    expected_route: Literal["rag_subgraph", "critic", "end"]
    expected_reasoning_contains: list[str]  # Keywords that should appear in reasoning
    category: str  # Category for analysis
    description: str  # Human-readable description


# Golden dataset with 20 examples
GOLDEN_EXAMPLES = [
    # Simple greetings -> end
    GoldenExample(
        query="Hello",
        expected_route="end",
        expected_reasoning_contains=["greeting", "simple"],
        category="greeting",
        description="Simple greeting should end conversation"
    ),
    GoldenExample(
        query="Hi there!",
        expected_route="end",
        expected_reasoning_contains=["greeting", "simple"],
        category="greeting",
        description="Casual greeting should end conversation"
    ),
    GoldenExample(
        query="Thanks",
        expected_route="end",
        expected_reasoning_contains=["greeting", "simple"],
        category="greeting",
        description="Thank you should end conversation"
    ),
    GoldenExample(
        query="Goodbye",
        expected_route="end",
        expected_reasoning_contains=["greeting", "simple"],
        category="greeting",
        description="Farewell should end conversation"
    ),

    # Factual queries -> rag_subgraph
    GoldenExample(
        query="What is NIM Sentinel?",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="factual",
        description="Factual question about the system"
    ),
    GoldenExample(
        query="How does hybrid retrieval work in NIM Sentinel?",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="factual",
        description="Technical question about retrieval architecture"
    ),
    GoldenExample(
        query="What are the key features of NIM Sentinel?",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="factual",
        description="Feature overview question"
    ),
    GoldenExample(
        query="Explain tenant isolation in NIM Sentinel",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="factual",
        description="Technical question about multi-tenancy"
    ),
    GoldenExample(
        query="Which NVIDIA models does NIM Sentinel use for embeddings?",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="factual",
        description="Model configuration question"
    ),

    # How-to queries -> rag_subgraph
    GoldenExample(
        query="How do I upload a document to NIM Sentinel?",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="howto",
        description="Document upload procedure question"
    ),
    GoldenExample(
        query="How to query documents using the API?",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="howto",
        description="API usage question"
    ),
    GoldenExample(
        query="What is the process for document ingestion?",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="howto",
        description="Ingestion pipeline question"
    ),

    # Comparison queries -> rag_subgraph
    GoldenExample(
        query="What's the difference between vector search and full-text search?",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="comparison",
        description="Technical comparison question"
    ),
    GoldenExample(
        query="Compare RRF fusion with simple concatenation for hybrid search",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="comparison",
        description="Algorithm comparison question"
    ),

    # Troubleshooting queries -> rag_subgraph
    GoldenExample(
        query="Why is my document upload failing?",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="troubleshooting",
        description="Error diagnosis question"
    ),
    GoldenExample(
        query="How to fix authentication errors in NIM Sentinel?",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="troubleshooting",
        description="Auth troubleshooting question"
    ),

    # Complex analytical queries -> rag_subgraph
    GoldenExample(
        query="Analyze the performance tradeoffs of semantic chunking vs fixed-size chunking",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="analytical",
        description="Performance analysis question"
    ),
    GoldenExample(
        query="What are the best practices for optimizing retrieval accuracy?",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="analytical",
        description="Best practices question"
    ),

    # Edge cases
    GoldenExample(
        query="Can you help me?",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="ambiguous",
        description="Ambiguous help request - should route to RAG"
    ),
    GoldenExample(
        query="Tell me about the system architecture",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="architectural",
        description="Architecture overview question"
    ),
    GoldenExample(
        query="What is the latency of the reranker?",
        expected_route="rag_subgraph",
        expected_reasoning_contains=["RAG", "retrieval", "generation"],
        category="performance",
        description="Performance metric question"
    ),
]


def get_golden_examples() -> list[GoldenExample]:
    """Get all golden examples."""
    return GOLDEN_EXAMPLES


def get_examples_by_category(category: str) -> list[GoldenExample]:
    """Get golden examples filtered by category."""
    return [ex for ex in GOLDEN_EXAMPLES if ex.category == category]


def get_categories() -> list[str]:
    """Get all unique categories."""
    return list(set(ex.category for ex in GOLDEN_EXAMPLES))


if __name__ == "__main__":
    print(f"Total golden examples: {len(GOLDEN_EXAMPLES)}")
    print(f"Categories: {get_categories()}")
    for cat in get_categories():
        examples = get_examples_by_category(cat)
        print(f"  {cat}: {len(examples)} examples")
    print("\nAll examples:")
    for i, ex in enumerate(GOLDEN_EXAMPLES, 1):
        print(f"  {i}. [{ex.category}] {ex.query[:60]}... -> {ex.expected_route}")