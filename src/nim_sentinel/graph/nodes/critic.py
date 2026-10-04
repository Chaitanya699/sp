"""
NIM Sentinel Critic Node

Reviews generated answers for quality, accuracy, and citation correctness.
"""

import logging
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from nim_sentinel.core.config import get_model_config, get_settings
from nim_sentinel.graph.state import AgentState, CriticOutput

logger = logging.getLogger(__name__)


class Critic:
    """
    Critic node that reviews generated answers.

    Checks:
    - Answer relevance to query
    - Citation accuracy (citations match retrieved content)
    - Factual consistency
    - Completeness
    """

    def __init__(self) -> None:
        settings = get_settings()
        judge_config = get_model_config("judge_llm")

        self.llm = ChatNVIDIA(
            model=judge_config.primary,
            api_key=settings.nvidia_api_key,
            temperature=judge_config.temperature,
            max_tokens=judge_config.max_tokens,
            timeout=judge_config.timeout_seconds,
        )

        self.system_prompt = """You are a critic for NIM Sentinel, an enterprise RAG system.
Review the generated answer for quality and accuracy.

Evaluation criteria:
1. RELEVANCE: Does the answer address the user's query?
2. CITATION ACCURACY: Do citations match the retrieved content? Are they properly formatted?
3. FACTUAL CONSISTENCY: Does the answer contradict retrieved sources?
4. COMPLETENESS: Does the answer cover the key points from retrieved sources?
5. CONCISENESS: Is the answer concise without losing important information?

Respond with a JSON object:
{
  "approved": true/false,
  "feedback": "detailed feedback explaining decision",
  "confidence": 0.0-1.0,
  "suggested_changes": ["list of specific improvements if not approved"]
}

If approved is true, the answer is ready for the user.
If approved is false, the answer will be regenerated with your feedback."""

    async def review(self, state: AgentState) -> CriticOutput:
        """Review the generated answer."""
        if not state.answer:
            return CriticOutput(
                approved=False,
                feedback="No answer to review",
                confidence=0.0,
                suggested_changes=["Generate an answer first"],
            )

        # Build context from retrieval results
        context_parts = []
        for i, result in enumerate(state.retrieval_results):
            context_parts.append(
                f"[Source {i+1}] {result.content}"
            )
        context = "\n\n".join(context_parts) if context_parts else "No sources retrieved."

        # Build citations summary
        citations_summary = "\n".join(
            f"  Citation {i+1}: doc={c.get('document_id')}, chunk={c.get('chunk_index')}, score={c.get('score', 0):.3f}"
            for i, c in enumerate(state.citations)
        )

        user_prompt = f"""Query: {state.query}

Retrieved Context:
{context}

Citations Used:
{citations_summary}

Generated Answer:
{state.answer}

Review this answer and provide your evaluation."""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = await self.llm.ainvoke(messages)

            # Parse JSON response
            import json
            # Handle response.content which can be str or list
            content = response.content
            if isinstance(content, list):
                content = " ".join(str(c) for c in content)
            try:
                result_dict: dict[str, Any] = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code block
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                result_dict = json.loads(content.strip())

            return CriticOutput(
                approved=result_dict.get("approved", False),
                feedback=result_dict.get("feedback", "No feedback provided"),
                confidence=result_dict.get("confidence", 0.5),
                suggested_changes=result_dict.get("suggested_changes", []),
            )

        except Exception as e:
            logger.error("Critic review failed: %s", e)
            return CriticOutput(
                approved=False,
                feedback=f"Critic error: {str(e)}",
                confidence=0.0,
                suggested_changes=["Fix critic error and retry"],
            )


async def critic_node(state: AgentState) -> AgentState:
    """LangGraph node function for critic."""
    logger.info("Critic: Reviewing answer (retry %d)", state.retry_count)

    critic = Critic()
    output = await critic.review(state)

    state.critique_feedback = output.feedback
    state.metadata["critic_output"] = {
        "approved": output.approved,
        "feedback": output.feedback,
        "confidence": output.confidence,
        "suggested_changes": output.suggested_changes,
    }

    if output.approved:
        state.needs_critique = False
        logger.info("Critic: Answer approved (confidence: %.2f)", output.confidence)
    else:
        state.retry_count += 1
        state.needs_critique = True
        logger.info("Critic: Answer rejected, retry %d: %s", state.retry_count, output.feedback)

    state.updated_at = __import__("datetime").datetime.utcnow()
    return state