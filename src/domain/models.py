"""Shared domain objects for the knowledge assistant."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

RoleName = Literal[
    "Visitor",
    "Front Desk",
    "Claims Desk",
]


@dataclass
class PipelineTrace:
    """Timing and retrieval stats for one query — used in Observability."""

    retrieve_ms: float = 0.0
    rerank_ms: float = 0.0
    generate_ms: float = 0.0
    hybrid_hits: int = 0
    reranked_hits: int = 0
    grounded_hits: int = 0
    best_score: float = 0.0
    guardrail: str | None = None
    tool_name: str | None = None
    data_mode: str | None = None


@dataclass
class UseCase:
    """A named scenario on the Use Cases tab."""

    use_case_id: str
    name: str
    persona: RoleName
    brand: str
    question: str
    follow_up: str | None
    expected_source: str
    expected_keywords: list[str]
    must_refuse: bool = False
    why_it_matters: str = ""


@dataclass
class RAGResult:
    """Structured result returned to the UI and audit log."""

    answer: str
    sources: list[dict[str, Any]]
    grounded: bool
    warning: str | None = None
    role: str = "Visitor"
    use_case_id: str | None = None
    use_case_name: str | None = None
    confidence: str = "low"
    guardrail: str | None = None
    trace: PipelineTrace = field(default_factory=PipelineTrace)
