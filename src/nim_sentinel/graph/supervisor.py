"""
NIM Sentinel Supervisor Node

Routes queries to appropriate subgraphs based on query analysis.
"""

import json
import logging
from typing import Any, Literal
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from nim_sentinel.core.config import get_model_config, get_settings
from nim_sentinel.graph.state import AgentState, SupervisorDecision, create_initial_state
from nim_sentinel.llm.model_registry import get_model_registry

logger = logging.getLogger(__name__)


class Supervisor:
    """
    Supervisor node that analyzes queries and routes to appropriate handlers.

    For Phase 3, routes to RAG subgraph for all queries.
    Future: can route to different subgraphs (code, analysis, etc.)
    """

    def __init__(self) -> None:
        settings = get_settings()
        supervisor_config = get_model_config("supervisor_llm")

        self.llm = ChatNVIDIA(
            model=supervisor_config.primary,
            api_key=settings.nvidia_api_key,
            temperature=supervisor_config.temperature,
            max_tokens=supervisor_config.max_tokens,
            timeout=supervisor_config.timeout_seconds,
        )

        self.system_prompt = """You are the supervisor for NIM Sentinel, an enterprise multi-agent RAG system.
Your job is to analyze the user's query and decide the next action.

Available actions:
1. "rag_subgraph" - Route to RAG retrieval and generation (default for most queries)
2. "critic" - Send to critic for review (when answer exists but needs validation)
3. "end" - End the conversation (for greetings, simple acknowledgments)

For this phase, almost all queries should route to "rag_subgraph".
Only route to "end" for simple greetings like "hello", "hi", "thanks".
Route to "critic" only when an answer already exists in state and needs review.

Respond with a JSON object:
{
  "next_node": "rag_subgraph" | "critic" | "end",
  "reasoning": "brief explanation",
  "confidence": 0.0-1.0
}"""

    async def decide(self, state: AgentState) -> SupervisorDecision:
        """Analyze state and decide next node."""
        # If we already have an answer and haven't critiqued yet, send to critic
        if state.answer and state.needs_critique and state.retry_count < 3:
            return SupervisorDecision(
                next_node="critic",
                reasoning="Answer generated, sending to critic for review",
                confidence=0.9,
            )

        # If we've retried too many times, end
        if state.retry_count >= 3:
            return SupervisorDecision(
                next_node="end",
                reasoning="Max retries reached, ending",
                confidence=0.95,
            )

        # If critic already reviewed and approved, end
        critic_output = state.metadata.get("critic_output", {})
        if critic_output.get("approved", False):
            return SupervisorDecision(
                next_node="end",
                reasoning="Critic approved the answer",
                confidence=0.95,
            )

        # For simple greetings, end directly
        query_lower = state.query.lower().strip()
        greeting_keywords = ("hello", "hi", "hey", "thanks", "thank you", "bye", "goodbye")
        if query_lower in greeting_keywords or any(query_lower.startswith(g + " ") for g in greeting_keywords):
            return SupervisorDecision(
                next_node="end",
                reasoning="Simple greeting, no RAG needed",
                confidence=0.99,
            )

        # Default: route to RAG subgraph
        return SupervisorDecision(
            next_node="rag_subgraph",
            reasoning="Query requires RAG retrieval and generation",
            confidence=0.9,
        )

    async def decide_with_llm(self, state: AgentState) -> SupervisorDecision:
        """Analyze state using LLM and decide next node (for complex routing)."""
        try:
            registry = get_model_registry()

            async def _decide(model: ChatNVIDIA) -> dict[str, Any]:
                messages = [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=f"Query: {state.query}\n\nCurrent state: answer_exists={bool(state.answer)}, needs_critique={state.needs_critique}, retry_count={state.retry_count}"),
                ]
                response = await model.ainvoke(messages)
                content = response.content
                if isinstance(content, list):
                    content = " ".join(str(c) for c in content)
                import json
                try:
                    result: dict[str, Any] = json.loads(content)
                except json.JSONDecodeError:
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    result = json.loads(content.strip())
                return result

            result = await registry.call_with_retry_and_fallback(
                role="supervisor_llm",
                model_type="chat",
                func=_decide,
            )

            fallback_used = False
            result_dict: dict[str, Any] = {}
            if isinstance(result, dict):
                fallback_used = result.get("llm_fallback_used", False)
                # Remove the fallback indicator from the result
                result_dict = {k: v for k, v in result.items() if k != "llm_fallback_used"}

            return SupervisorDecision(
                next_node=result_dict.get("next_node", "rag_subgraph"),
                reasoning=result_dict.get("reasoning", "LLM routing decision"),
                confidence=result_dict.get("confidence", 0.9),
            )

        except Exception as e:
            logger.error("Supervisor LLM decision failed, using rule-based: %s", e)
            return await self.decide(state)


async def supervisor_node(state: AgentState) -> AgentState:
    """LangGraph node function for supervisor."""
    supervisor = Supervisor()
    decision = await supervisor.decide(state)

    logger.info(
        "Supervisor decision: next=%s, reasoning=%s, confidence=%.2f",
        decision.next_node, decision.reasoning, decision.confidence
    )

    # Update state with decision
    state.metadata["supervisor_decision"] = {
        "next_node": decision.next_node,
        "reasoning": decision.reasoning,
        "confidence": decision.confidence,
    }
    state.updated_at = __import__("datetime").datetime.utcnow()

    return state


def get_next_node(state: AgentState) -> Literal["rag_subgraph", "critic", "end"]:
    """Get next node from supervisor decision in state metadata."""
    decision = state.metadata.get("supervisor_decision", {})
    next_node: str = decision.get("next_node", "rag_subgraph")
    # Type assertion for mypy
    if next_node not in ("rag_subgraph", "critic", "end"):
        next_node = "rag_subgraph"
    return next_node  # type: ignore[return-value]