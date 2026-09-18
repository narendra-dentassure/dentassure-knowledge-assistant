"""Streamlit console for the DentAssure Health Plans knowledge assistant."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.application.disclaimer import (
    COMPOSER_DISCLAIMER,
    CUSTOMER_CARE_EMAIL,
    CUSTOMER_CARE_PHONE,
    CUSTOMER_CARE_WEB,
)
from src.application.roles import list_role_ids, role_label
from src.application.use_cases import get_use_cases
from src.config import get_settings, has_llm_credentials
from src.conversation import ConversationMemory
from src.ingest import ingest_corpus
from src.logging_setup import configure_logging
from src.observability.audit import read_audit
from src.rag_pipeline import answer_question

logger = configure_logging()
ROLES = list_role_ids()

st.set_page_config(
    page_title="DentAssure Knowledge Assistant",
    page_icon="🦷",
    layout="wide",
)


def _init_state() -> None:
    if "memory" not in st.session_state:
        st.session_state.memory = ConversationMemory()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "index" not in st.session_state:
        st.session_state.index = None
    if "index_error" not in st.session_state:
        st.session_state.index_error = None
    if "role" not in st.session_state:
        st.session_state.role = "Visitor"


def _ensure_index(force: bool = False) -> bool:
    try:
        with st.spinner("Building the local knowledge index..."):
            st.session_state.index = ingest_corpus(force=force)
        st.session_state.index_error = None
        logger.info("Index ready: %s files", st.session_state.index["document_count"])
        return True
    except Exception as exc:
        logger.exception("Index build failed")
        st.session_state.index_error = str(exc)
        return False


def _render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander("Cited sources", expanded=True):
        for source in sources:
            st.markdown(
                f"- **{source['source']}** (Page {source['page']}) — score `{source['score']}`"
            )
            st.caption(source["snippet"])


def _render_trace(message: dict) -> None:
    trace = message.get("trace")
    if not trace:
        return
    with st.expander("Pipeline trace"):
        st.json(
            {
                "role": message.get("role"),
                "use_case": message.get("use_case_name"),
                "confidence": message.get("confidence"),
                "guardrail": message.get("guardrail"),
                "retrieve_ms": trace.retrieve_ms,
                "rerank_ms": trace.rerank_ms,
                "generate_ms": trace.generate_ms,
                "hybrid_hits": trace.hybrid_hits,
                "grounded_hits": trace.grounded_hits,
                "best_score": round(trace.best_score, 4),
                "tool": trace.tool_name,
                "data_mode": trace.data_mode,
            }
        )


def _ask(question: str, settings) -> None:
    st.session_state.messages.append({"role": "user", "content": question})
    result = answer_question(
        question=question,
        retriever=st.session_state.index["retriever"],
        chunks=st.session_state.index["chunks"],
        memory=st.session_state.memory,
        settings=settings,
        role=st.session_state.role,
    )
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result.answer,
            "sources": result.sources,
            "grounded": result.grounded,
            "confidence": result.confidence,
            "use_case_name": result.use_case_name,
            "use_case_id": result.use_case_id,
            "guardrail": result.guardrail,
            "trace": result.trace,
        }
    )


def main() -> None:
    _init_state()
    settings = get_settings()
    use_cases = get_use_cases()

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 3.2rem;
            padding-bottom: 3.5rem;
            max-width: 1180px;
        }

        /* Streamlit markdown wrappers clip rounded HTML cards. */
        div[data-testid="stVerticalBlock"] > div,
        div[data-testid="stMarkdownContainer"] {
            overflow: visible !important;
        }
        div[data-testid="stMarkdownContainer"] p { margin: 0; }

        .da-hero {
            display: block;
            box-sizing: border-box;
            width: 100%;
            background: linear-gradient(135deg, #0f172a 0%, #0f766e 100%);
            color: #fff;
            padding: 1.55rem 1.8rem 1.65rem;
            border-radius: 18px;
            margin: 0 0 1.15rem 0;
            overflow: visible;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.18);
        }
        .da-hero-title {
            font-size: 1.7rem;
            line-height: 1.35;
            font-weight: 700;
            color: #fff;
            margin: 0.4rem 0 0.55rem 0;
        }
        .da-hero-sub {
            margin: 0;
            padding-bottom: 0.15rem;
            line-height: 1.5;
            color: #ecfdf5;
            opacity: 0.96;
        }
        .ai-chip {
            display: inline-block;
            font-size: 0.72rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            background: rgba(255,255,255,0.16);
            border: 1px solid rgba(255,255,255,0.28);
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
        }

        div[data-testid="stMetric"] { background: #fff; border: 1px solid #e2e8f0;
            border-radius: 12px; padding: 0.65rem 0.85rem; }
        .stTabs [data-baseweb="tab-list"] { gap: 0.35rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="da-hero">
            <span class="ai-chip">AI assistant</span>
            <div class="da-hero-title">DentAssure Knowledge Assistant</div>
            <div class="da-hero-sub">For patients, website visitors, and clinic front desk — plans, clinics, cashless, and policy.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.index is None and st.session_state.index_error is None:
        _ensure_index(force=False)

    docs = st.session_state.index["document_count"] if st.session_state.index else 0
    chunks = st.session_state.index["chunk_count"] if st.session_state.index else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Source documents", docs)
    c2.metric("Indexed chunks", chunks)
    c3.metric("Scenarios", len(use_cases))
    c4.metric("Who is asking", len(ROLES))

    with st.sidebar:
        st.subheader("Who is asking")
        if st.session_state.role not in ROLES:
            st.session_state.role = "Visitor"
        st.session_state.role = st.selectbox(
            "Audience",
            ROLES,
            index=ROLES.index(st.session_state.role),
            format_func=role_label,
        )
        if st.button("Rebuild index", use_container_width=True):
            _ensure_index(force=True)
            st.success("Index rebuilt.")
        if st.button("Clear conversation", use_container_width=True):
            st.session_state.memory.clear()
            st.session_state.messages = []
            st.rerun()
        st.divider()
        st.caption("LLM")
        st.code(f"{settings.llm_provider} / {settings.gemini_model if settings.llm_provider=='gemini' else settings.openai_model}")
        if has_llm_credentials(settings):
            st.success("Credentials loaded")
        else:
            st.error("Add API key in .env")
        st.caption("Pipeline")
        st.write("Ingest → Chunk → Embed → Hybrid retrieve → Rerank → Ground → Generate → Audit")
        st.divider()
        st.markdown("**Help**")
        st.caption("Talk to a person to confirm a plan")
        st.markdown(
            f"Call [{CUSTOMER_CARE_PHONE}](tel:+918886686850)  \n"
            f"[{CUSTOMER_CARE_EMAIL}](mailto:{CUSTOMER_CARE_EMAIL})  \n"
            f"[dentassureplans.co.in]({CUSTOMER_CARE_WEB})"
        )

    chat_tab, uc_tab, docs_tab, arch_tab, obs_tab, settings_tab = st.tabs(
        ["Chat", "Use Cases", "Documents", "Architecture", "Observability", "Settings"]
    )

    with uc_tab:
        st.subheader("Common questions")
        st.caption("Click Run to send the question to Chat.")
        for item in use_cases:
            with st.expander(f"{item.use_case_id} · {item.name} · {item.brand}"):
                st.write(item.why_it_matters)
                st.markdown(f"**Persona:** {item.persona}  \n**Primary question:** {item.question}")
                if item.follow_up:
                    st.markdown(f"**Follow-up:** {item.follow_up}")
                st.markdown(
                    f"**Expected source:** `{item.expected_source or 'none — must refuse'}`  \n"
                    f"**Refusal test:** {'yes' if item.must_refuse else 'no'}"
                )
                if st.button(f"Run {item.use_case_id}", key=f"run_{item.use_case_id}"):
                    st.session_state.role = item.persona
                    st.session_state.pending_question = item.question
                    st.session_state.active_tab_hint = "chat"

    with docs_tab:
        st.subheader("Knowledge corpus")
        if st.session_state.index_error:
            st.error(st.session_state.index_error)
        elif st.session_state.index:
            for file_info in st.session_state.index["files"]:
                st.markdown(
                    f"- `{file_info['name']}` · {file_info['type'].upper()} · "
                    f"{file_info['pages']} pages/sections"
                )
        st.info("Add PDF, DOCX, or TXT files to `data/sample_docs` and rebuild the index.")

    with arch_tab:
        st.subheader("System architecture")
        st.markdown(
            """
**Presentation** — Streamlit console (`app.py`): chat, use-case runner, observability.

**Application** — use-case catalog, staff roles, guardrails, RAG orchestration.

**Domain** — `RAGResult`, `UseCase`, `PipelineTrace`.

**Infrastructure** — document loaders, chunking, local embeddings, Chroma, BM25, cross-encoder, Gemini/OpenAI.

**Observability** — JSONL audit log under `logs/audit.jsonl` (no API keys).

```text
Staff role + question
        │
        ▼
 Guardrails
        │
        ├── clinic / hours / rating / distance  → DentAssure public clinic API
        │                                         (fallback: data/live_fixtures + clinic directory)
        ├── what plans / our plans              → featured plans public API
        ├── STANDARD STEER / SHIELD / Smart Saver → plan details public API
        ├── STANDARD SECURE / COMPLETE CARE       → local RAG (plan selection guide)
        │                                         (unknown SKUs: ungrounded refuse)
        ├── RCT / scaling / implant / best plan → compare-all-plans public API
        │                                         (fallback: fixture ranked like live)
        └── everything else                     → local RAG (PDF/DOCX/TXT)
```

`PLATFORM_MODE=auto` is the default: live APIs if the network works, otherwise the same answers from sample data. The demo does not depend on dentassureplans.co.in being reachable.
            """
        )
        st.markdown(
            """
Why the layers:

1. Retrieval is never a single LLM call.
2. Policy facts come from documents; prices and clinics can come from public APIs.
3. If the API is down, fixtures keep the demo working.
4. Weak document evidence still refuses instead of guessing.
            """
        )

    with obs_tab:
        st.subheader("Query audit")
        st.caption(
            "Local JSONL log of questions. No API keys. Git-ignored."
        )
        events = read_audit(30)
        if not events:
            st.info("No queries yet. Run a use case from Chat or Use Cases.")
        else:
            st.dataframe(
                [
                    {
                        "time": row.get("ts", "")[:19],
                        "role": row.get("role"),
                        "use_case": row.get("use_case_id"),
                        "grounded": row.get("grounded"),
                        "confidence": row.get("confidence"),
                        "retrieve_ms": row.get("retrieve_ms"),
                        "sources": ", ".join(row.get("sources") or []),
                        "question": row.get("question"),
                    }
                    for row in events
                ],
                use_container_width=True,
            )

    with settings_tab:
        st.subheader("Runtime configuration")
        st.json(
            {
                "llm_provider": settings.llm_provider,
                "openai_model": settings.openai_model,
                "gemini_model": settings.gemini_model,
                "chunk_size": settings.chunk_size,
                "chunk_overlap": settings.chunk_overlap,
                "retrieve_k": settings.retrieve_k,
                "rerank_k": settings.rerank_k,
                "min_relevance_score": settings.min_relevance_score,
                "platform_mode": os.getenv("PLATFORM_MODE", "auto"),
                "embedding_model": settings.embedding_model_name,
                "rerank_model": settings.rerank_model_name,
                "data_dir": str(settings.data_dir),
                "chroma_dir": str(settings.chroma_dir),
            }
        )
        st.caption("Values come from `.env`. Restart the app after changing environment variables.")
        st.markdown("Run tests: `python -m pytest tests -q`")

    with chat_tab:
        if st.session_state.index_error:
            st.error(f"The knowledge index could not be built. {st.session_state.index_error}")
            return
        if not has_llm_credentials(settings):
            st.warning("Add `GEMINI_API_KEY` or `OPENAI_API_KEY` in `.env` before asking questions.")

        with st.expander("Try these questions"):
            st.caption("Covers RAG, memory, citations, missing-info, plus plan and clinic tools.")
            for example in (
                "What are the key guidelines for DentAssure policy renewal?",
                "How to take a DentAssure plan which is the best plan?",
                "What plans do you have?",
                "STANDARD STEER - Explain about this plan",
                "Explain STANDARD SECURE waiting periods and coverage",
                "Root canal and scaling which is the best plan?",
                "Where is a DentAssure clinic in Hyderabad and what are the hours and rating?",
                "How does a patient use DentAssure cashless at a network clinic?",
                "What is the CEO's personal mobile number and home address?",
                "rct scaling konsa plan lena",
                "SUPERIOR SPARKLE explain this plan",
            ):
                st.markdown(f"- {example}")

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    badges = []
                    if message.get("use_case_id"):
                        badges.append(message["use_case_id"])
                    if message.get("confidence"):
                        badges.append(f"confidence: {message['confidence']}")
                    if message.get("grounded") is False:
                        badges.append("ungrounded")
                    if badges:
                        st.caption(" · ".join(badges))
                st.markdown(message["content"])
                if message.get("sources"):
                    _render_sources(message["sources"])
                if message["role"] == "assistant":
                    _render_trace(message)

        st.caption(COMPOSER_DISCLAIMER)
        pending = st.session_state.pop("pending_question", None)
        user_text = st.chat_input("Ask about a plan, clinic, or policy")
        question = pending or user_text
        if question:
            with st.spinner("Checking tools, then documents..."):
                _ask(question, settings)
            st.rerun()


if __name__ == "__main__":
    main()
