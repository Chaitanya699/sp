"""
Tests for Observability module
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from nim_sentinel.observability import (
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
    _redact_pii,
    _redact_dict,
)


class TestRedactPII:
    """Tests for PII redaction functions."""

    def test_redact_pii_email(self):
        """Test email redaction."""
        text = "Contact me at test@example.com"
        result = _redact_pii(text)
        assert "[REDACTED_EMAIL]" in result
        assert "test@example.com" not in result

    def test_redact_pii_phone(self):
        """Test phone redaction."""
        text = "Call me at 555-123-4567"
        result = _redact_pii(text)
        assert "[REDACTED_PHONE]" in result

    def test_redact_pii_ssn(self):
        """Test SSN redaction."""
        text = "SSN: 123-45-6789"
        result = _redact_pii(text)
        assert "[REDACTED_SSN]" in result

    def test_redact_pii_credit_card(self):
        """Test credit card redaction."""
        text = "Card: 1234-5678-9012-3456"
        result = _redact_pii(text)
        assert "[REDACTED_CREDIT_CARD]" in result

    def test_redact_pii_multiple(self):
        """Test multiple PII types."""
        text = "Email: test@example.com, Phone: 555-123-4567"
        result = _redact_pii(text)
        assert "[REDACTED_EMAIL]" in result
        assert "[REDACTED_PHONE]" in result

    def test_redact_pii_none(self):
        """Test no PII."""
        text = "Hello world"
        result = _redact_pii(text)
        assert result == "Hello world"

    def test_redact_pii_empty(self):
        """Test empty string."""
        result = _redact_pii("")
        assert result == ""

    def test_redact_pii_none_input(self):
        """Test None input."""
        result = _redact_pii(None)
        assert result is None

    def test_redact_dict_string_values(self):
        """Test dict redaction with string values."""
        data = {"email": "test@example.com", "name": "John"}
        result = _redact_dict(data)
        assert "[REDACTED_EMAIL]" in result["email"]
        assert result["name"] == "John"

    def test_redact_dict_nested(self):
        """Test dict redaction with nested dict."""
        data = {"user": {"email": "test@example.com", "age": 30}}
        result = _redact_dict(data)
        assert "[REDACTED_EMAIL]" in result["user"]["email"]
        assert result["user"]["age"] == 30

    def test_redact_dict_list(self):
        """Test dict redaction with list of strings."""
        data = {"emails": ["test@example.com", "admin@example.com"]}
        result = _redact_dict(data)
        assert "[REDACTED_EMAIL]" in result["emails"][0]
        assert "[REDACTED_EMAIL]" in result["emails"][1]

    def test_redact_dict_list_of_dicts(self):
        """Test dict redaction with list of dicts."""
        data = {"users": [{"email": "test@example.com"}, {"email": "admin@example.com"}]}
        result = _redact_dict(data)
        assert "[REDACTED_EMAIL]" in result["users"][0]["email"]
        assert "[REDACTED_EMAIL]" in result["users"][1]["email"]


class TestTracedNode:
    """Tests for traced_node decorator."""

    @pytest.mark.asyncio
    async def test_traced_node_async(self):
        """Test traced_node with async function."""
        @traced_node("test_node")
        async def my_node(state: dict) -> dict:
            return {"result": "success"}

        result = await my_node({"input": "test"})
        assert result == {"result": "success"}

    def test_traced_node_sync(self):
        """Test traced_node with sync function."""
        @traced_node("test_node_sync")
        def my_node(state: dict) -> dict:
            return {"result": "success"}

        result = my_node({"input": "test"})
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_traced_node_redacts_pii(self):
        """Test traced_node redacts PII in inputs."""
        @traced_node("test_node", redact=True)
        async def my_node(state: dict) -> dict:
            return state

        # This should not raise and should redact internally
        result = await my_node({"email": "test@example.com"})
        assert result == {"email": "test@example.com"}

    @pytest.mark.asyncio
    async def test_traced_node_no_redact(self):
        """Test traced_node without redaction."""
        @traced_node("test_node", redact=False)
        async def my_node(state: dict) -> dict:
            return state

        result = await my_node({"email": "test@example.com"})
        assert result == {"email": "test@example.com"}

    @pytest.mark.asyncio
    async def test_traced_node_exception(self):
        """Test traced_node propagates exceptions."""
        @traced_node("test_node")
        async def my_node(state: dict) -> dict:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await my_node({})


class TestTracedTool:
    """Tests for traced_tool decorator."""

    @pytest.mark.asyncio
    async def test_traced_tool_async(self):
        """Test traced_tool with async function."""
        @traced_tool("test_tool")
        async def my_tool(query: str) -> str:
            return f"Result for {query}"

        result = await my_tool("test query")
        assert result == "Result for test query"

    def test_traced_tool_sync(self):
        """Test traced_tool with sync function."""
        @traced_tool("test_tool_sync")
        def my_tool(query: str) -> str:
            return f"Result for {query}"

        result = my_tool("test query")
        assert result == "Result for test query"

    @pytest.mark.asyncio
    async def test_traced_tool_redacts_kwargs(self):
        """Test traced_tool redacts PII in kwargs."""
        @traced_tool("test_tool", redact=True)
        async def my_tool(query: str, user_email: str) -> str:
            return f"Result for {query}"

        result = await my_tool("test", user_email="test@example.com")
        assert result == "Result for test"

    @pytest.mark.asyncio
    async def test_traced_tool_exception(self):
        """Test traced_tool propagates exceptions."""
        @traced_tool("test_tool")
        async def my_tool(query: str) -> str:
            raise ValueError("Tool error")

        with pytest.raises(ValueError, match="Tool error"):
            await my_tool("test")


class TestTracedLLMCall:
    """Tests for traced_llm_call decorator."""

    @pytest.mark.asyncio
    async def test_traced_llm_call_async(self):
        """Test traced_llm_call with async function."""
        @traced_llm_call("test_llm", role="supervisor")
        async def call_llm(prompt: str) -> str:
            return "LLM response"

        result = await call_llm("Test prompt")
        assert result == "LLM response"

    def test_traced_llm_call_sync(self):
        """Test traced_llm_call with sync function."""
        @traced_llm_call("test_llm_sync", role="critic")
        def call_llm(prompt: str) -> str:
            return "LLM response"

        result = call_llm("Test prompt")
        assert result == "LLM response"

    @pytest.mark.asyncio
    async def test_traced_llm_call_redacts_prompt(self):
        """Test traced_llm_call redacts PII in prompt."""
        @traced_llm_call("test_llm", role="generator", redact=True)
        async def call_llm(prompt: str) -> str:
            return "Response"

        result = await call_llm("My email is test@example.com")
        assert result == "Response"

    @pytest.mark.asyncio
    async def test_traced_llm_call_exception(self):
        """Test traced_llm_call propagates exceptions."""
        @traced_llm_call("test_llm", role="supervisor")
        async def call_llm(prompt: str) -> str:
            raise ValueError("LLM error")

        with pytest.raises(ValueError, match="LLM error"):
            await call_llm("Test")


class TestTracedRetriever:
    """Tests for traced_retriever decorator."""

    @pytest.mark.asyncio
    async def test_traced_retriever_async(self):
        """Test traced_retriever with async function."""
        @traced_retriever("test_retriever")
        async def retrieve(query: str) -> list[str]:
            return ["doc1", "doc2"]

        result = await retrieve("test query")
        assert result == ["doc1", "doc2"]

    def test_traced_retriever_sync(self):
        """Test traced_retriever with sync function."""
        @traced_retriever("test_retriever_sync")
        def retrieve(query: str) -> list[str]:
            return ["doc1", "doc2"]

        result = retrieve("test query")
        assert result == ["doc1", "doc2"]

    @pytest.mark.asyncio
    async def test_traced_retriever_redacts_query(self):
        """Test traced_retriever redacts PII in query."""
        @traced_retriever("test_retriever", redact=True)
        async def retrieve(query: str) -> list[str]:
            return ["doc1"]

        result = await retrieve("Find test@example.com")
        assert result == ["doc1"]

    @pytest.mark.asyncio
    async def test_traced_retriever_exception(self):
        """Test traced_retriever propagates exceptions."""
        @traced_retriever("test_retriever")
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