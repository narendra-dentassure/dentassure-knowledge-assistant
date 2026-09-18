"""End-to-end RAG pipeline: retrieve, rerank, generate, cite sources."""

from __future__ import annotations

import time
from typing import Any

from src.application.disclaimer import with_customer_care_notice
from src.application.guardrails import guardrail_message, inspect_query
from src.application.platform_tools import try_platform_tools
from src.application.query_rewrite import expand_query
from src.application.roles import role_instruction
from src.application.use_cases import match_use_case
from src.chunking import Chunk
from src.config import Settings
from src.conversation import ConversationMemory
from src.domain.models import PipelineTrace, RAGResult
from src.hybrid_retriever import HybridRetriever
from src.llm_client import LLMError, generate_answer
from src.logging_setup import configure_logging
from src.observability.audit import write_audit
from src.reranker import rerank_hits

logger = configure_logging()

SYSTEM_RULES = """
You are an AI assistant for DentAssure Health Plans.
Answer ONLY from the supplied document excerpts.

Rules:
- If the excerpts do not contain the answer, say clearly that the information
  is not present in the provided documents. Do not invent policies, prices,
  SLAs, or clinical advice.
- Use conversation history only to interpret follow-up questions. Never let
  history override the documents.
- After the answer, add a Sources section listing the file name and page/section
  used, for example: Sources: dentassure_policy_guide.pdf (Page 2)
- Do not repeat a long legal disclaimer. A one-line footer is added automatically.
""".strip()


def is_grounded(hits: list[dict[str, Any]], min_score: float) -> bool:
    """True when the best reranked hit clears the evidence threshold."""
    if not hits:
        return False
    best = max(float(hit.get("relevance_score", 0.0)) for hit in hits)
    return best >= min_score


def confidence_label(best_score: float) -> str:
    if best_score >= 2.0:
        return "high"
    if best_score >= 0.5:
        return "medium"
    if best_score >= 0.18:
        return "low"
    return "none"


def format_context(hits: list[dict[str, Any]]) -> str:
    blocks = []
    for index, hit in enumerate(hits, start=1):
        blocks.append(
            f"[Excerpt {index}] Source: {hit['source']} | Page/Section: {hit['page']}\n"
            f"{hit['text']}"
        )
    return "\n\n".join(blocks)


def source_preview(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, int]] = set()
    sources: list[dict[str, Any]] = []
    for hit in hits:
        key = (hit["source"], int(hit["page"]))
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "source": hit["source"],
                "page": int(hit["page"]),
                "score": round(float(hit.get("relevance_score", 0.0)), 4),
                "snippet": hit["text"][:280] + ("..." if len(hit["text"]) > 280 else ""),
            }
        )
    return sources


def build_prompt(
    question: str,
    hits: list[dict[str, Any]],
    memory: ConversationMemory,
    role: str = "Visitor",
) -> str:
    """Build the grounded generation prompt for a staff role."""
    return (
        f"{SYSTEM_RULES}\n"
        f"Audience: {role_instruction(role)}\n\n"
        f"Conversation history:\n{memory.as_prompt_block()}\n\n"
        f"Document excerpts:\n{format_context(hits)}\n\n"
        f"Current question:\n{question}\n"
    )


def answer_question(
    question: str,
    retriever: HybridRetriever,
    chunks: list[Chunk],
    memory: ConversationMemory,
    settings: Settings,
    role: str = "Visitor",
) -> RAGResult:
    """Run guardrails + hybrid retrieval + rerank + grounded generation."""
    del chunks
    matched = match_use_case(question)
    trace = PipelineTrace()
    question = (question or "").strip()

    blocked = inspect_query(question)
    if blocked:
        trace.guardrail = blocked
        result = RAGResult(
            answer=guardrail_message(blocked),
            sources=[],
            grounded=False,
            warning=blocked,
            role=role,
            use_case_id=matched.use_case_id if matched else None,
            use_case_name=matched.name if matched else None,
            confidence="none",
            guardrail=blocked,
            trace=trace,
        )
        _audit(question, role, result)
        return _with_notice(result)

    live = try_platform_tools(question, history=memory.as_prompt_block())
    if live:
        memory.add("user", question)
        memory.add("assistant", live.answer)
        trace.tool_name = live.intent
        trace.data_mode = live.mode
        trace.best_score = 1.0
        result = RAGResult(
            answer=live.answer,
            sources=live.sources,
            grounded=True,
            warning=None,
            role=role,
            use_case_id=matched.use_case_id if matched else None,
            use_case_name=matched.name if matched else None,
            confidence="high",
            trace=trace,
        )
        _audit(question, role, result)
        return _with_notice(result)

    try:
        started = time.perf_counter()
        search_query = expand_query(question)
        hybrid_hits = retriever.retrieve(search_query, settings.retrieve_k)
        trace.retrieve_ms = round((time.perf_counter() - started) * 1000, 1)
        trace.hybrid_hits = len(hybrid_hits)

        started = time.perf_counter()
        ranked_hits = rerank_hits(question, hybrid_hits, settings.rerank_k)
        ranked_hits = [
            hit
            for hit in ranked_hits
            if float(hit.get("relevance_score", 0.0)) >= settings.min_relevance_score
        ]
        trace.rerank_ms = round((time.perf_counter() - started) * 1000, 1)
        trace.reranked_hits = len(ranked_hits)
        trace.grounded_hits = len(ranked_hits)
        trace.best_score = max(
            (float(hit.get("relevance_score", 0.0)) for hit in ranked_hits),
            default=0.0,
        )
    except Exception:
        logger.exception("Retrieval failed")
        result = RAGResult(
            answer="Retrieval failed. Rebuild the knowledge index from the Documents tab and try again.",
            sources=[],
            grounded=False,
            warning="retrieval_error",
            role=role,
            trace=trace,
        )
        _audit(question, role, result)
        return _with_notice(result)

    if not is_grounded(ranked_hits, settings.min_relevance_score):
        message = (
            "I could not find this information in the provided documents. "
            "Please rephrase the question or add the relevant policy/SOP file "
            "to the data folder and rebuild the index."
        )
        memory.add("user", question)
        memory.add("assistant", message)
        result = RAGResult(
            answer=message,
            sources=[],
            grounded=False,
            warning="not_in_docs",
            role=role,
            use_case_id=matched.use_case_id if matched else None,
            use_case_name=matched.name if matched else None,
            confidence="none",
            trace=trace,
        )
        _audit(question, role, result)
        return _with_notice(result)

    prompt = build_prompt(question, ranked_hits, memory, role=role)
    try:
        started = time.perf_counter()
        answer = generate_answer(prompt, settings)
        trace.generate_ms = round((time.perf_counter() - started) * 1000, 1)
    except LLMError as exc:
        result = RAGResult(
            answer=str(exc),
            sources=source_preview(ranked_hits),
            grounded=True,
            warning="llm_error",
            role=role,
            confidence=confidence_label(trace.best_score),
            trace=trace,
        )
        _audit(question, role, result)
        return _with_notice(result)

    memory.add("user", question)
    memory.add("assistant", answer)
    result = RAGResult(
        answer=answer,
        sources=source_preview(ranked_hits),
        grounded=True,
        role=role,
        use_case_id=matched.use_case_id if matched else None,
        use_case_name=matched.name if matched else None,
        confidence=confidence_label(trace.best_score),
        trace=trace,
    )
    _audit(question, role, result)
    return _with_notice(result)


def _with_notice(result: RAGResult) -> RAGResult:
    result.answer = with_customer_care_notice(result.answer)
    return result


def _audit(question: str, role: str, result: RAGResult) -> None:
    write_audit(
        {
            "question": question[:500],
            "role": role,
            "use_case_id": result.use_case_id,
            "grounded": result.grounded,
            "confidence": result.confidence,
            "warning": result.warning,
            "guardrail": result.guardrail,
            "sources": [f"{item['source']}#p{item['page']}" for item in result.sources],
            "retrieve_ms": result.trace.retrieve_ms,
            "rerank_ms": result.trace.rerank_ms,
            "generate_ms": result.trace.generate_ms,
            "best_score": round(result.trace.best_score, 4),
            "tool": result.trace.tool_name,
            "data_mode": result.trace.data_mode,
        }
    )
