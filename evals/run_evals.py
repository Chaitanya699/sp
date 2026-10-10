#!/usr/bin/env python3
"""
NIM Sentinel Evaluation CLI

Run evaluations for different components with configurable thresholds.
"""

import argparse
import asyncio
import sys
import yaml
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def load_thresholds(config_path: str = "configs/eval_thresholds.yaml") -> dict[str, Any]:
    """Load evaluation thresholds from config file."""
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


async def run_retrieval_eval(thresholds: dict[str, Any], fail_under: float | None = None) -> dict[str, Any]:
    """Run retrieval evaluation."""
    from tests.test_golden_retrieval import get_golden_examples
    from nim_sentinel.rag.retriever import HybridRetriever, get_hybrid_retriever
    from nim_sentinel.db.client import get_database
    from nim_sentinel.db.repositories import get_chunk_repository
    from nim_sentinel.rag.ingestion.embedder import get_embedding_client

    print("Running retrieval evaluation...")

    # Get golden examples
    examples = get_golden_examples()

    # Setup retriever
    db = await get_database()
    chunk_repo = get_chunk_repository(db, "test_tenant")
    retriever = await get_hybrid_retriever(chunk_repo)
    embedding_client = await get_embedding_client()

    results = {
        "total": len(examples),
        "passed": 0,
        "failed": 0,
        "details": [],
    }

    for example in examples:
        query_embedding = await embedding_client.embed_query(example.query)
        retrieved = await retriever.retrieve(
            query=example.query,
            query_embedding=query_embedding,
            top_k=example.top_k,
        )

        # Check if expected documents are in results
        retrieved_doc_ids = {r.document_id for r in retrieved}
        expected_found = sum(1 for doc_id in example.expected_doc_ids if doc_id in retrieved_doc_ids)
        recall = expected_found / len(example.expected_doc_ids) if example.expected_doc_ids else 1.0

        threshold = thresholds.get("retrieval", {}).get("recall_at_k", 0.8)
        passed = recall >= threshold

        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1

        results["details"].append({
            "query": example.query,
            "recall": recall,
            "threshold": threshold,
            "passed": passed,
            "expected_docs": example.expected_doc_ids,
            "retrieved_docs": list(retrieved_doc_ids),
        })

    print(f"Retrieval: {results['passed']}/{results['total']} passed")
    return results


async def run_supervisor_eval(thresholds: dict[str, Any], fail_under: float | None = None) -> dict[str, Any]:
    """Run supervisor routing evaluation."""
    from tests.golden_supervisor_dataset import get_golden_examples
    from nim_sentinel.graph.supervisor import Supervisor
    from nim_sentinel.graph.state import create_initial_state

    print("Running supervisor evaluation...")

    examples = get_golden_examples()
    supervisor = Supervisor()

    results = {
        "total": len(examples),
        "passed": 0,
        "failed": 0,
        "details": [],
    }

    for example in examples:
        state = create_initial_state(
            query=example.query,
            tenant_id="test_tenant",
            user_id="test_user",
            session_id="test_session",
        )
        decision = await supervisor.decide(state)

        passed = decision.next_node == example.expected_route

        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1

        results["details"].append({
            "query": example.query,
            "expected_route": example.expected_route,
            "actual_route": decision.next_node,
            "passed": passed,
            "reasoning": decision.reasoning,
        })

    print(f"Supervisor: {results['passed']}/{results['total']} passed")
    return results


async def run_guardrails_eval(thresholds: dict[str, Any], fail_under: float | None = None) -> dict[str, Any]:
    """Run guardrails evaluation."""
    from evals.redteam.run_eval import main as run_redteam

    print("Running guardrails evaluation (red-team)...")

    # Run the red-team evaluation
    import subprocess
    result = subprocess.run(
        [sys.executable, "evals/redteam/run_eval.py"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    # Parse results
    output = result.stdout
    lines = output.split("\n")

    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "details": [],
    }

    for line in lines:
        if "ATTACKS (" in line:
            parts = line.split()
            results["total"] = int(parts[1].rstrip("):"))
        elif "Blocked:" in line and "ATTACKS" in " ".join(lines[max(0, lines.index(line)-2):lines.index(line)+1]):
            parts = line.split()
            results["passed"] = int(parts[1].rstrip("("))
        elif "Allowed:" in line and "ATTACKS" in " ".join(lines[max(0, lines.index(line)-3):lines.index(line)+1]):
            parts = line.split()
            results["failed"] = int(parts[1])

    print(f"Guardrails: {results['passed']}/{results['total']} attacks blocked")
    return results


async def run_data_analyst_eval(thresholds: dict[str, Any], fail_under: float | None = None) -> dict[str, Any]:
    """Run data analyst evaluation."""
    from nim_sentinel.agents.data_analyst import get_data_analyst

    print("Running data analyst evaluation...")

    agent = get_data_analyst()

    # Test queries
    test_queries = [
        {
            "name": "list_documents",
            "collection": "documents",
            "filter_query": {"status": "completed"},
            "projection": {"filename": 1, "chunk_count": 1},
            "sort": [("filename", 1)],
            "limit": 10,
        },
        {
            "name": "aggregate_chunks",
            "collection": "documents",
            "pipeline": [
                {"$match": {"status": "completed"}},
                {"$group": {"_id": "$status", "total_chunks": {"$sum": "$chunk_count"}, "doc_count": {"$sum": 1}}},
            ],
        },
    ]

    results = {
        "total": len(test_queries),
        "passed": 0,
        "failed": 0,
        "details": [],
    }

    for test in test_queries:
        try:
            if "pipeline" in test:
                result = await agent.execute(
                    collection=test["collection"],
                    pipeline=test["pipeline"],
                    tenant_id="acme_corp",
                    max_rows=10,
                )
            else:
                result = await agent.execute_simple(
                    collection=test["collection"],
                    filter_query=test.get("filter_query"),
                    projection=test.get("projection"),
                    sort=test.get("sort"),
                    limit=test.get("limit"),
                    tenant_id="acme_corp",
                )

            passed = result.row_count > 0
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1

            results["details"].append({
                "test": test["name"],
                "row_count": result.row_count,
                "execution_time_ms": result.execution_time_ms,
                "passed": passed,
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "test": test["name"],
                "error": str(e),
                "passed": False,
            })

    print(f"Data Analyst: {results['passed']}/{results['total']} passed")
    return results


async def main():
    parser = argparse.ArgumentParser(description="NIM Sentinel Evaluation CLI")
    parser.add_argument(
        "--component",
        choices=["retrieval", "supervisor", "guardrails", "data_analyst", "all"],
        default="all",
        help="Component to evaluate",
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        help="Fail if overall score is below this threshold (0-1)",
    )
    parser.add_argument(
        "--config",
        default="configs/eval_thresholds.yaml",
        help="Path to evaluation thresholds config",
    )
    parser.add_argument(
        "--output",
        help="Output file for results (JSON)",
    )
    args = parser.parse_args()

    thresholds = load_thresholds(args.config)

    all_results = {}

    if args.component in ("retrieval", "all"):
        all_results["retrieval"] = await run_retrieval_eval(thresholds, args.fail_under)

    if args.component in ("supervisor", "all"):
        all_results["supervisor"] = await run_supervisor_eval(thresholds, args.fail_under)

    if args.component in ("guardrails", "all"):
        all_results["guardrails"] = await run_guardrails_eval(thresholds, args.fail_under)

    if args.component in ("data_analyst", "all"):
        all_results["data_analyst"] = await run_data_analyst_eval(thresholds, args.fail_under)

    # Calculate overall score
    total_passed = sum(r["passed"] for r in all_results.values())
    total_tests = sum(r["total"] for r in all_results.values())
    overall_score = total_passed / total_tests if total_tests > 0 else 0

    print(f"\n{'='*50}")
    print(f"OVERALL: {total_passed}/{total_tests} passed ({overall_score*100:.1f}%)")
    print(f"{'='*50}")

    # Check fail-under threshold
    if args.fail_under is not None and overall_score < args.fail_under:
        print(f"FAIL: Overall score {overall_score*100:.1f}% below threshold {args.fail_under*100:.1f}%")
        sys.exit(1)

    # Save results if output specified
    if args.output:
        import json
        with open(args.output, "w") as f:
            json.dump({
                "overall_score": overall_score,
                "total_passed": total_passed,
                "total_tests": total_tests,
                "components": all_results,
            }, f, indent=2)
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())