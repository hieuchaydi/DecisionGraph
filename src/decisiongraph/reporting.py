from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from decisiongraph.models import Contradiction, Decision, StaleAssumption


@dataclass
class SummaryReport:
    generated_at: str
    total_decisions: int
    by_component: dict[str, int]
    by_type: dict[str, int]
    sensitive_decisions: int
    decisions_without_evidence: int
    stale_assumptions: list[StaleAssumption]
    contradictions: list[Contradiction]

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "total_decisions": self.total_decisions,
            "by_component": self.by_component,
            "by_type": self.by_type,
            "sensitive_decisions": self.sensitive_decisions,
            "decisions_without_evidence": self.decisions_without_evidence,
            "stale_assumptions": [item.to_dict() for item in self.stale_assumptions],
            "contradictions": [item.to_dict() for item in self.contradictions],
        }

    def to_markdown(self) -> str:
        lines = [
            "# DecisionGraph Summary Report",
            "",
            f"- Generated at: `{self.generated_at}`",
            f"- Total decisions: `{self.total_decisions}`",
            f"- Sensitive decisions: `{self.sensitive_decisions}`",
            f"- Decisions without evidence: `{self.decisions_without_evidence}`",
            "",
            "## Component Breakdown",
        ]
        if not self.by_component:
            lines.append("- None")
        else:
            for name, count in sorted(self.by_component.items(), key=lambda row: row[1], reverse=True):
                lines.append(f"- `{name}`: {count}")

        lines.append("")
        lines.append("## Type Breakdown")
        if not self.by_type:
            lines.append("- None")
        else:
            for name, count in sorted(self.by_type.items(), key=lambda row: row[1], reverse=True):
                lines.append(f"- `{name}`: {count}")

        lines.append("")
        lines.append("## Top Stale Assumptions")
        if not self.stale_assumptions:
            lines.append("- None")
        else:
            for item in self.stale_assumptions[:10]:
                lines.append(
                    f"- `{item.decision_id}` `{item.metric_key}`: `{item.assumption}` (actual `{item.actual}`, severity `{item.severity}`)"
                )

        lines.append("")
        lines.append("## Top Contradictions")
        if not self.contradictions:
            lines.append("- None")
        else:
            for item in self.contradictions[:10]:
                lines.append(
                    f"- `{item.topic}`: {item.reason} (`{item.decision_a_id}` vs `{item.decision_b_id}`)"
                )
        return "\n".join(lines)


def build_summary_report(
    generated_at: str,
    decisions: list[Decision],
    stale_assumptions: list[StaleAssumption],
    contradictions: list[Contradiction],
) -> SummaryReport:
    components = Counter((item.component or "unknown") for item in decisions)
    types = Counter((item.decision_type or "unknown") for item in decisions)
    sensitive = 0
    no_evidence = 0
    for item in decisions:
        tags = {tag.lower() for tag in item.tags}
        if tags.intersection({"security", "auth", "payments", "billing", "compliance"}):
            sensitive += 1
        if not item.evidence_ids:
            no_evidence += 1
    return SummaryReport(
        generated_at=generated_at,
        total_decisions=len(decisions),
        by_component=dict(components),
        by_type=dict(types),
        sensitive_decisions=sensitive,
        decisions_without_evidence=no_evidence,
        stale_assumptions=stale_assumptions,
        contradictions=contradictions,
    )
