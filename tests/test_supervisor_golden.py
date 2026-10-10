"""
Tests for Supervisor Golden Dataset Evaluation

Evaluates the supervisor's routing accuracy against the golden dataset.
"""

import pytest
from nim_sentinel.graph.state import AgentState, create_initial_state
from nim_sentinel.graph.supervisor import Supervisor

from tests.golden_supervisor_dataset import get_golden_examples


class TestSupervisorGoldenDataset:
    """Test supervisor routing against golden dataset."""

    @pytest.fixture
    def supervisor(self):
        """Create supervisor instance."""
        return Supervisor()

    @pytest.fixture
    def base_state(self):
        """Create base state for testing."""
        return create_initial_state(
            query="",
            tenant_id="test_tenant",
            user_id="test_user",
            session_id="test_session",
        )

    @pytest.mark.asyncio
    async def test_golden_dataset_routing(self, supervisor, base_state):
        """Test supervisor routing matches golden dataset expectations."""
        examples = get_golden_examples()
        results = []

        for example in examples:
            # Create state with the query
            state = AgentState(
                messages=base_state.messages,
                query=example.query,
                tenant_id=base_state.tenant_id,
                user_id=base_state.user_id,
                session_id=base_state.session_id,
                retrieval_results=base_state.retrieval_results,
                citations=base_state.citations,
                answer=base_state.answer,
                confidence=base_state.confidence,
                needs_critique=base_state.needs_critique,
                critique_feedback=base_state.critique_feedback,
                retry_count=base_state.retry_count,
                metadata=base_state.metadata.copy(),
                created_at=base_state.created_at,
                updated_at=base_state.updated_at,
            )

            # Get supervisor decision
            decision = await supervisor.decide(state)

            # Check if routing matches expected
            passed = decision.next_node == example.expected_route

            # Check if reasoning contains expected keywords
            reasoning_lower = decision.reasoning.lower()
            reasoning_matches = all(
                keyword.lower() in reasoning_lower
                for keyword in example.expected_reasoning_contains
            )

            results.append(
                {
                    "query": example.query,
                    "category": example.category,
                    "expected_route": example.expected_route,
                    "actual_route": decision.next_node,
                    "route_match": passed,
                    "reasoning": decision.reasoning,
                    "reasoning_matches": reasoning_matches,
                    "confidence": decision.confidence,
                }
            )

            # Assert routing matches
            assert passed, (
                f"Routing mismatch for query: '{example.query}'\n"
                f"  Expected: {example.expected_route}\n"
                f"  Actual: {decision.next_node}\n"
                f"  Reasoning: {decision.reasoning}"
            )

        # Print summary
        total = len(results)
        correct = sum(1 for r in results if r["route_match"])
        reasoning_correct = sum(1 for r in results if r["reasoning_matches"])

        print(f"\n{'='*60}")
        print("SUPERVISOR GOLDEN DATASET EVALUATION")
        print(f"{'='*60}")
        print(f"Total examples: {total}")
        print(f"Routing accuracy: {correct}/{total} ({correct/total*100:.1f}%)")
        print(
            f"Reasoning keyword match: {reasoning_correct}/{total} ({reasoning_correct/total*100:.1f}%)"
        )

        # Per-category breakdown
        categories = set(r["category"] for r in results)
        for cat in sorted(categories):
            cat_results = [r for r in results if r["category"] == cat]
            cat_correct = sum(1 for r in cat_results if r["route_match"])
            print(
                f"  {cat}: {cat_correct}/{len(cat_results)} ({cat_correct/len(cat_results)*100:.1f}%)"
            )

        print(f"{'='*60}")

        # Require at least 90% accuracy
        assert (
            correct / total >= 0.9
        ), f"Routing accuracy {correct/total*100:.1f}% below 90% threshold"

    @pytest.mark.asyncio
    async def test_greeting_routes_to_end(self, supervisor, base_state):
        """Test that greetings route to end."""
        greetings = ["hello", "hi", "hey", "thanks", "thank you", "bye", "goodbye"]

        for greeting in greetings:
            state = AgentState(
                messages=base_state.messages,
                query=greeting,
                tenant_id=base_state.tenant_id,
                user_id=base_state.user_id,
                session_id=base_state.session_id,
                retrieval_results=base_state.retrieval_results,
                citations=base_state.citations,
                answer=base_state.answer,
                confidence=base_state.confidence,
                needs_critique=base_state.needs_critique,
                critique_feedback=base_state.critique_feedback,
                retry_count=base_state.retry_count,
                metadata=base_state.metadata.copy(),
                created_at=base_state.created_at,
                updated_at=base_state.updated_at,
            )

            decision = await supervisor.decide(state)
            assert (
                decision.next_node == "end"
            ), f"Greeting '{greeting}' should route to end, got {decision.next_node}"

    @pytest.mark.asyncio
    async def test_factual_queries_route_to_rag(self, supervisor, base_state):
        """Test that factual queries route to rag_subgraph."""
        queries = [
            "What is NIM Sentinel?",
            "How does hybrid retrieval work?",
            "What are the key features?",
            "Explain tenant isolation",
            "Which models are used for embeddings?",
        ]

        for query in queries:
            state = AgentState(
                messages=base_state.messages,
                query=query,
                tenant_id=base_state.tenant_id,
                user_id=base_state.user_id,
                session_id=base_state.session_id,
                retrieval_results=base_state.retrieval_results,
                citations=base_state.citations,
                answer=base_state.answer,
                confidence=base_state.confidence,
                needs_critique=base_state.needs_critique,
                critique_feedback=base_state.critique_feedback,
                retry_count=base_state.retry_count,
                metadata=base_state.metadata.copy(),
                created_at=base_state.created_at,
                updated_at=base_state.updated_at,
            )

            decision = await supervisor.decide(state)
            assert (
                decision.next_node == "rag_subgraph"
            ), f"Query '{query}' should route to rag_subgraph, got {decision.next_node}"

    @pytest.mark.asyncio
    async def test_answer_exists_routes_to_critic(self, supervisor, base_state):
        """Test that existing answer routes to critic."""
        state = AgentState(
            messages=base_state.messages,
            query="What is NIM Sentinel?",
            tenant_id=base_state.tenant_id,
            user_id=base_state.user_id,
            session_id=base_state.session_id,
            retrieval_results=base_state.retrieval_results,
            citations=base_state.citations,
            answer="NIM Sentinel is an enterprise RAG system.",  # Answer exists
            confidence=0.8,
            needs_critique=True,
            critique_feedback=base_state.critique_feedback,
            retry_count=0,
            metadata=base_state.metadata.copy(),
            created_at=base_state.created_at,
            updated_at=base_state.updated_at,
        )

        decision = await supervisor.decide(state)
        assert (
            decision.next_node == "critic"
        ), f"Answer exists should route to critic, got {decision.next_node}"

    @pytest.mark.asyncio
    async def test_max_retries_routes_to_end(self, supervisor, base_state):
        """Test that max retries routes to end."""
        state = AgentState(
            messages=base_state.messages,
            query="What is NIM Sentinel?",
            tenant_id=base_state.tenant_id,
            user_id=base_state.user_id,
            session_id=base_state.session_id,
            retrieval_results=base_state.retrieval_results,
            citations=base_state.citations,
            answer="NIM Sentinel is an enterprise RAG system.",
            confidence=0.8,
            needs_critique=True,
            critique_feedback=base_state.critique_feedback,
            retry_count=3,  # Max retries reached
            metadata=base_state.metadata.copy(),
            created_at=base_state.created_at,
            updated_at=base_state.updated_at,
        )

        decision = await supervisor.decide(state)
        assert (
            decision.next_node == "end"
        ), f"Max retries should route to end, got {decision.next_node}"

    @pytest.mark.asyncio
    async def test_critic_approved_routes_to_end(self, supervisor, base_state):
        """Test that critic approval routes to end."""
        state = AgentState(
            messages=base_state.messages,
            query="What is NIM Sentinel?",
            tenant_id=base_state.tenant_id,
            user_id=base_state.user_id,
            session_id=base_state.session_id,
            retrieval_results=base_state.retrieval_results,
            citations=base_state.citations,
            answer="NIM Sentinel is an enterprise RAG system.",
            confidence=0.8,
            needs_critique=False,
            critique_feedback="Approved: Answer is accurate and well-cited.",
            retry_count=0,
            metadata={
                "critic_output": {
                    "approved": True,
                    "feedback": "Approved: Answer is accurate and well-cited.",
                    "confidence": 0.9,
                }
            },
            created_at=base_state.created_at,
            updated_at=base_state.updated_at,
        )

        decision = await supervisor.decide(state)
        assert (
            decision.next_node == "end"
        ), f"Critic approved should route to end, got {decision.next_node}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
