from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Evidence:
    id: str
    source_type: str
    source_id: str
    excerpt: str
    url: str | None = None
    content_hash: str | None = None
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "excerpt": self.excerpt,
            "url": self.url,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Evidence":
        return Evidence(
            id=data["id"],
            source_type=data["source_type"],
            source_id=data["source_id"],
            excerpt=data.get("excerpt", ""),
            url=data.get("url"),
            content_hash=data.get("content_hash"),
            created_at=data.get("created_at", utc_now_iso()),
        )


@dataclass
class Decision:
    id: str
    title: str
    summary: str
    date: str
    owners: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    tradeoffs: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    consequences: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    component: str | None = None
    decision_type: str = "technical"
    supersedes: list[str] = field(default_factory=list)
    superseded_by: str | None = None
    confidence: float = 0.6
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def searchable_text(self) -> str:
        chunks = [
            self.title,
            self.summary,
            " ".join(self.owners),
            " ".join(self.alternatives),
            " ".join(self.tradeoffs),
            " ".join(self.assumptions),
            " ".join(self.risks),
            " ".join(self.consequences),
            " ".join(self.tags),
            self.component or "",
            self.decision_type,
        ]
        return " ".join(chunks).lower()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "date": self.date,
            "owners": self.owners,
            "alternatives": self.alternatives,
            "tradeoffs": self.tradeoffs,
            "assumptions": self.assumptions,
            "risks": self.risks,
            "consequences": self.consequences,
            "evidence_ids": self.evidence_ids,
            "tags": self.tags,
            "component": self.component,
            "decision_type": self.decision_type,
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Decision":
        return Decision(
            id=data["id"],
            title=data.get("title", "Untitled decision"),
            summary=data.get("summary", ""),
            date=data.get("date", ""),
            owners=data.get("owners", []),
            alternatives=data.get("alternatives", []),
            tradeoffs=data.get("tradeoffs", []),
            assumptions=data.get("assumptions", []),
            risks=data.get("risks", []),
            consequences=data.get("consequences", []),
            evidence_ids=data.get("evidence_ids", []),
            tags=data.get("tags", []),
            component=data.get("component"),
            decision_type=data.get("decision_type", "technical"),
            supersedes=data.get("supersedes", []),
            superseded_by=data.get("superseded_by"),
            confidence=float(data.get("confidence", 0.6)),
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", utc_now_iso()),
        )


@dataclass
class MetricSnapshot:
    key: str
    value: float
    unit: str | None = None
    recorded_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "unit": self.unit,
            "recorded_at": self.recorded_at,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "MetricSnapshot":
        return MetricSnapshot(
            key=data["key"],
            value=float(data["value"]),
            unit=data.get("unit"),
            recorded_at=data.get("recorded_at", utc_now_iso()),
        )


@dataclass
class Contradiction:
    decision_a_id: str
    decision_b_id: str
    reason: str
    topic: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_a_id": self.decision_a_id,
            "decision_b_id": self.decision_b_id,
            "reason": self.reason,
            "topic": self.topic,
            "confidence": self.confidence,
        }


@dataclass
class StaleAssumption:
    decision_id: str
    assumption: str
    metric_key: str
    operator: str
    threshold: float
    actual: float
    severity: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "assumption": self.assumption,
            "metric_key": self.metric_key,
            "operator": self.operator,
            "threshold": self.threshold,
            "actual": self.actual,
            "severity": self.severity,
        }


@dataclass
class GuardrailResult:
    change_request: str
    blocked: bool
    warnings: list[str]
    related_decisions: list[Decision]
    stale_assumptions: list[StaleAssumption]

    def to_dict(self) -> dict[str, Any]:
        return {
            "change_request": self.change_request,
            "blocked": self.blocked,
            "warnings": self.warnings,
            "related_decisions": [item.to_dict() for item in self.related_decisions],
            "stale_assumptions": [item.to_dict() for item in self.stale_assumptions],
        }


@dataclass
class QueryAnswer:
    question: str
    answer: str
    confidence: float
    warnings: list[str]
    decision: Decision | None
    evidence: list[Evidence]
    related: list[Decision] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "decision": self.decision.to_dict() if self.decision else None,
            "evidence": [item.to_dict() for item in self.evidence],
            "related": [item.to_dict() for item in self.related],
        }
