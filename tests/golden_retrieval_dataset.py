"""
Golden Retrieval Dataset for NIM Sentinel Retrieval Evaluation

This dataset contains query-document pairs with relevance judgments
for evaluating retrieval quality (recall@k, MRR).
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class RetrievalGoldenExample:
    """A single golden example for retrieval evaluation."""
    query: str
    relevant_doc_ids: list[str]  # Document IDs that should be retrieved
    relevant_chunk_indices: list[int]  # Chunk indices within those docs
    category: str
    description: str


# Golden retrieval dataset with 10 examples
GOLDEN_RETRIEVAL_EXAMPLES = [
    RetrievalGoldenExample(
        query="What is NIM Sentinel?",
        relevant_doc_ids=["6ac4a67b682ec73ee2fbf5de", "6ac4a646086abafcfe0de936"],
        relevant_chunk_indices=[0, 0],
        category="factual",
        description="Basic system definition query"
    ),
    RetrievalGoldenExample(
        query="How does hybrid retrieval work in NIM Sentinel?",
        relevant_doc_ids=["6ac4a67b682ec73ee2fbf5de"],
        relevant_chunk_indices=[0],
        category="technical",
        description="Technical architecture question"
    ),
    RetrievalGoldenExample(
        query="What are the key features of NIM Sentinel?",
        relevant_doc_ids=["6ac4a67b682ec73ee2fbf5de", "6ac4a646086abafcfe0de936"],
        relevant_chunk_indices=[0, 0],
        category="factual",
        description="Feature overview question"
    ),
    RetrievalGoldenExample(
        query="Explain tenant isolation in NIM Sentinel",
        relevant_doc_ids=["6ac4a67b682ec73ee2fbf5de"],
        relevant_chunk_indices=[0],
        category="technical",
        description="Multi-tenancy question"
    ),
    RetrievalGoldenExample(
        query="Which NVIDIA models does NIM Sentinel use for embeddings?",
        relevant_doc_ids=["6ac4a67b682ec73ee2fbf5de"],
        relevant_chunk_indices=[0],
        category="technical",
        description="Model configuration question"
    ),
    RetrievalGoldenExample(
        query="How do I upload a document to NIM Sentinel?",
        relevant_doc_ids=["6ac4a67b682ec73ee2fbf5de"],
        relevant_chunk_indices=[0],
        category="howto",
        description="Document upload procedure"
    ),
    RetrievalGoldenExample(
        query="What is the process for document ingestion?",
        relevant_doc_ids=["6ac4a67b682ec73ee2fbf5de"],
        relevant_chunk_indices=[0],
        category="howto",
        description="Ingestion pipeline question"
    ),
    RetrievalGoldenExample(
        query="What's the difference between vector search and full-text search?",
        relevant_doc_ids=["6ac4a67b682ec73ee2fbf5de"],
        relevant_chunk_indices=[0],
        category="comparison",
        description="Technical comparison question"
    ),
    RetrievalGoldenExample(
        query="How to fix authentication errors in NIM Sentinel?",
        relevant_doc_ids=["6ac4a67b682ec73ee2fbf5de"],
        relevant_chunk_indices=[0],
        category="troubleshooting",
        description="Auth troubleshooting question"
    ),
    RetrievalGoldenExample(
        query="What are the best practices for optimizing retrieval accuracy?",
        relevant_doc_ids=["6ac4a67b682ec73ee2fbf5de"],
        relevant_chunk_indices=[0],
        category="analytical",
        description="Best practices question"
    ),
]


def get_golden_retrieval_examples() -> list[RetrievalGoldenExample]:
    """Get all golden retrieval examples."""
    return GOLDEN_RETRIEVAL_EXAMPLES


def get_retrieval_examples_by_category(category: str) -> list[RetrievalGoldenExample]:
    """Get golden retrieval examples filtered by category."""
    return [ex for ex in GOLDEN_RETRIEVAL_EXAMPLES if ex.category == category]


def get_retrieval_categories() -> list[str]:
    """Get all unique categories."""
    return list(set(ex.category for ex in GOLDEN_RETRIEVAL_EXAMPLES))


if __name__ == "__main__":
    print(f"Total golden retrieval examples: {len(GOLDEN_RETRIEVAL_EXAMPLES)}")
    print(f"Categories: {get_retrieval_categories()}")
    for cat in get_retrieval_categories():
        examples = get_retrieval_examples_by_category(cat)
        print(f"  {cat}: {len(examples)} examples")
    print("\nAll examples:")
    for i, ex in enumerate(GOLDEN_RETRIEVAL_EXAMPLES, 1):
        print(f"  {i}. [{ex.category}] {ex.query[:60]}... -> {len(ex.relevant_doc_ids)} relevant docs")