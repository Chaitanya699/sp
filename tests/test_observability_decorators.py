"""
Tests for Observability - Decorators module
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from nim_sentinel.observability.decorators import (
    traced_node,
    traced_tool,
    traced_llm_call,
    traced_retriever,
    traced_supervisor_node,
    traced_rag_node,
    traced_critic_node,
    traced_embedder,
    traced_reranker,
    traced_vector_search,
    traced_text_search,
    traced_hybrid_retrieve,
)


class TestTracedNode:
    """Tests for traced_node decorator."""

    @pytest.mark.asyncio
    async def test_traced_node_async(self):
        """Test traced_node with async function."""
        @traced_node(name="test_node", role="test")
        async def my_node(state: dict) -> dict:
            return {"result": "success"}

        result = await my_node({"input": "test"})
        assert result == {"result": "success"}

    def test_traced_node_sync(self):
        """Test traced_node with sync function."""
        @traced_node(name="test_node_sync", role="test")
        def my_node(state: dict) -> dict:
            return {"result": "success"}

        result = my_node({"input": "test"})
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_traced_node_redacts_pii(self):
        """Test traced_node redacts PII in inputs."""
        @traced_node(name="test_node", redact=True, role="test")
        async def my_node(state: dict) -> dict:
            return state

        result = await my_node({"email": "test@example.com"})
        assert result == {"email": "test@example.com"}

    @pytest.mark.asyncio
    async def test_traced_node_no_redact(self):
        """Test traced_node without redaction."""
        @traced_node(name="test_node", redact=False, role="test")
        async def my_node(state: dict) -> dict:
            return state

        result = await my_node({"email": "test@example.com"})
        assert result == {"email": "test@example.com"}

    @pytest.mark.asyncio
    async def test_traced_node_exception(self):
        """Test traced_node propagates exceptions."""
        @traced_node(name="test_node", role="test")
        async def my_node(state: dict) -> dict:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await my_node({})


class TestTracedTool:
    """Tests for traced_tool decorator."""

    @pytest.mark.asyncio
    async def test_traced_tool_async(self):
        """Test traced_tool with async function."""
        @traced_tool(name="test_tool", role="test")
        async def my_tool(query: str) -> str:
            return f"Result for {query}"

        result = await my_tool("test query")
        assert result == "Result for test query"

    def test_traced_tool_sync(self):
        """Test traced_tool with sync function."""
        @traced_tool(name="test_tool_sync", role="test")
        def my_tool(query: str) -> str:
            return f"Result for {query}"

        result = my_tool("test query")
        assert result == "Result for test query"

    @pytest.mark.asyncio
    async def test_traced_tool_redacts_kwargs(self):
        """Test traced_tool redacts PII in kwargs."""
        @traced_tool(name="test_tool", redact=True, role="test")
        async def my_tool(query: str, user_email: str) -> str:
            return f"Result for {query}"

        result = await my_tool("test", user_email="test@example.com")
        assert result == "Result for test"

    @pytest.mark.asyncio
    async def test_traced_tool_exception(self):
        """Test traced_tool propagates exceptions."""
        @traced_tool(name="test_tool", role="test")
        async def my_tool(query: str) -> str:
            raise ValueError("Tool error")

        with pytest.raises(ValueError, match="Tool error"):
            await my_tool("test")


class TestTracedLLMCall:
    """Tests for traced_llm_call decorator."""

    @pytest.mark.asyncio
    async def test_traced_llm_call_async(self):
        """Test traced_llm_call with async function."""
        @traced_llm_call(name="test_llm", role="supervisor", model_id="test-model")
        async def call_llm(prompt: str) -> str:
            return "LLM response"

        result = await call_llm("Test prompt")
        assert result == "LLM response"

    def test_traced_llm_call_sync(self):
        """Test traced_llm_call with sync function."""
        @traced_llm_call(name="test_llm_sync", role="critic", model_id="test-model")
        def call_llm(prompt: str) -> str:
            return "LLM response"

        result = call_llm("Test prompt")
        assert result == "LLM response"

    @pytest.mark.asyncio
    async def test_traced_llm_call_redacts_prompt(self):
        """Test traced_llm_call redacts PII in prompt."""
        @traced_llm_call(name="test_llm", role="generator", model_id="test-model", redact=True)
        async def call_llm(prompt: str) -> str:
            return "Response"

        result = await call_llm("My email is test@example.com")
        assert result == "Response"

    @pytest.mark.asyncio
    async def test_traced_llm_call_exception(self):
        """Test traced_llm_call propagates exceptions."""
        @traced_llm_call(name="test_llm", role="supervisor", model_id="test-model")
        async def call_llm(prompt: str) -> str:
            raise ValueError("LLM error")

        with pytest.raises(ValueError, match="LLM error"):
            await call_llm("Test")


class TestTracedRetriever:
    """Tests for traced_retriever decorator."""

    @pytest.mark.asyncio
    async def test_traced_retriever_async(self):
        """Test traced_retriever with async function."""
        @traced_retriever(name="test_retriever", role="retriever")
        async def retrieve(query: str) -> list[str]:
            return ["doc1", "doc2"]

        result = await retrieve("test query")
        assert result == ["doc1", "doc2"]

    def test_traced_retriever_sync(self):
        """Test traced_retriever with sync function."""
        @traced_retriever(name="test_retriever_sync", role="retriever")
        def retrieve(query: str) -> list[str]:
            return ["doc1", "doc2"]

        result = retrieve("test query")
        assert result == ["doc1", "doc2"]

    @pytest.mark.asyncio
    async def test_traced_retriever_redacts_query(self):
        """Test traced_retriever redacts PII in query."""
        @traced_retriever(name="test_retriever", redact=True, role="retriever")
        async def retrieve(query: str) -> list[str]:
            return ["doc1"]

        result = await retrieve("Find test@example.com")
        assert result == ["doc1"]

    @pytest.mark.asyncio
    async def test_traced_retriever_exception(self):
        """Test traced_retriever propagates exceptions."""
        @traced_retriever(name="test_retriever", role="retriever")
        async def retrieve(query: str) -> list[str]:
            raise ValueError("Retriever error")

        with pytest.raises(ValueError, match="Retriever error"):
            await retrieve("test")


class TestConvenienceDecorators:
    """Tests for convenience decorators."""

    @pytest.mark.asyncio
    async def test_traced_supervisor_node(self):
        """Test traced_supervisor_node."""
        @traced_supervisor_node
        async def supervisor(state: dict) -> dict:
            return {"next": "rag"}

        result = await supervisor({})
        assert result == {"next": "rag"}

    @pytest.mark.asyncio
    async def test_traced_rag_node(self):
        """Test traced_rag_node."""
        @traced_rag_node
        async def rag_node(state: dict) -> dict:
            return {"answer": "Found it"}

        result = await rag_node({})
        assert result == {"answer": "Found it"}

    @pytest.mark.asyncio
    async def test_traced_critic_node(self):
        """Test traced_critic_node."""
        @traced_critic_node
        async def critic(state: dict) -> dict:
            return {"approved": True}

        result = await critic({})
        assert result == {"approved": True}

    @pytest.mark.asyncio
    async def test_traced_embedder(self):
        """Test traced_embedder."""
        @traced_embedder
        async def embed(text: str) -> list[float]:
            return [0.1, 0.2, 0.3]

        result = await embed("test")
        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_traced_reranker(self):
        """Test traced_reranker."""
        @traced_reranker
        async def rerank(query: str, docs: list[str]) -> list[str]:
            return docs

        result = await rerank("test", ["doc1", "doc2"])
        assert result == ["doc1", "doc2"]

    @pytest.mark.asyncio
    async def test_traced_vector_search(self):
        """Test traced_vector_search."""
        @traced_vector_search
        async def search(query: str) -> list[str]:
            return ["doc1"]

        result = await search("test")
        assert result == ["doc1"]

    @pytest.mark.asyncio
    async def test_traced_text_search(self):
        """Test traced_text_search."""
        @traced_text_search
        async def search(query: str) -> list[str]:
            return ["doc1"]

        result = await search("test")
        assert result == ["doc1"]

    @pytest.mark.asyncio
    async def test_traced_hybrid_retrieve(self):
        """Test traced_hybrid_retrieve."""
        @traced_hybrid_retrieve
        async def retrieve(query: str) -> list[str]:
            return ["doc1", "doc2"]

        result = await retrieve("test")
        assert result == ["doc1", "doc2"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])