from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from decisiongraph.models import QueryAnswer
from decisiongraph.service import DecisionGraphService


@dataclass
class ScenarioSpec:
    name: str
    question: str
    expected_keywords: list[str]


DEFAULT_SCENARIOS: list[ScenarioSpec] = [
    ScenarioSpec(
        name="redis-vs-rabbitmq",
        question="Why did we choose Redis instead of RabbitMQ for async workflows?",
        expected_keywords=["redis", "rabbitmq", "trade-offs", "assumptions"],
    ),
    ScenarioSpec(
        name="payment-retry-cap",
        question="Why is payment retry logic capped at 2 retries?",
        expected_keywords=["payment", "retry", "risks"],
    ),
    ScenarioSpec(
        name="monolith-reversion",
        question="Why did we revert from microservices back to monolith?",
        expected_keywords=["revert", "microservices", "incident"],
    ),
    ScenarioSpec(
        name="auth-incident-guardrail",
        question="Can we simplify refresh token rotation in auth layer?",
        expected_keywords=["auth", "risks", "evidence"],
    ),
]


def _contains_keywords(answer: QueryAnswer, keywords: list[str]) -> tuple[bool, list[str]]:
    text = answer.answer.lower()
    missing = [item for item in keywords if item.lower() not in text]
    return len(missing) == 0, missing


def run_scenarios(service: DecisionGraphService, scenarios: list[ScenarioSpec] | None = None) -> dict[str, Any]:
    rows = scenarios or DEFAULT_SCENARIOS
    results: list[dict[str, Any]] = []
    passed = 0
    for spec in rows:
        out = service.query(spec.question)
        ok, missing = _contains_keywords(out, spec.expected_keywords)
        if ok:
            passed += 1
        results.append(
            {
                "name": spec.name,
                "question": spec.question,
                "passed": ok,
                "missing_keywords": missing,
                "confidence": out.confidence,
                "decision_id": out.decision.id if out.decision else None,
            }
        )
    total = len(rows)
    return {
        "total": total,
        "passed": passed,
        "pass_rate": round((passed / total), 3) if total else 0.0,
        "items": results,
    }


def kpi_snapshot(service: DecisionGraphService) -> dict[str, Any]:
    decisions = service.list_decisions(limit=10000)
    total = len(decisions)
    with_evidence = sum(1 for row in decisions if row.evidence_ids)
    sensitive = sum(
        1
        for row in decisions
        if {tag.lower() for tag in row.tags}.intersection({"auth", "security", "payments", "billing", "compliance"})
    )
    stale = service.detect_stale_assumptions(decisions=decisions)
    contradictions = service.detect_contradictions()
    scenario = run_scenarios(service)
    return {
        "total_decisions": total,
        "evidence_coverage": round((with_evidence / total), 3) if total else 0.0,
        "sensitive_decisions": sensitive,
        "stale_assumption_count": len(stale),
        "contradiction_count": len(contradictions),
        "scenario_pass_rate": scenario["pass_rate"],
        "scenario_passed": scenario["passed"],
        "scenario_total": scenario["total"],
    }


def _parse_dataset(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise ValueError(f"Invalid dataset path: {path}")
    rows: list[dict[str, Any]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at line {lineno}: {exc}") from exc
        rows.append(payload)
    return rows


def evaluate_dataset(service: DecisionGraphService, dataset_path: Path) -> dict[str, Any]:
    rows = _parse_dataset(dataset_path)
    if not rows:
        return {"total": 0, "top1_accuracy": 0.0, "keyword_coverage": 0.0, "avg_latency_ms": 0.0, "items": []}

    correct_top1 = 0
    keyword_hits = 0
    total_keywords = 0
    total_latency = 0.0
    items: list[dict[str, Any]] = []
    for row in rows:
        question = str(row.get("question") or "").strip()
        if not question:
            continue
        expected_title_contains = str(row.get("expected_title_contains") or "").strip().lower()
        expected_keywords = [str(x).strip().lower() for x in row.get("expected_keywords", []) if str(x).strip()]

        started = perf_counter()
        out = service.query(question)
        elapsed_ms = (perf_counter() - started) * 1000.0
        total_latency += elapsed_ms

        predicted_title = (out.decision.title if out.decision else "").lower()
        top1_ok = expected_title_contains in predicted_title if expected_title_contains else True
        if top1_ok:
            correct_top1 += 1

        text = out.answer.lower()
        hits = sum(1 for kw in expected_keywords if kw in text)
        keyword_hits += hits
        total_keywords += len(expected_keywords)
        items.append(
            {
                "question": question,
                "top1_ok": top1_ok,
                "expected_title_contains": expected_title_contains,
                "predicted_title": out.decision.title if out.decision else None,
                "keyword_hit_ratio": round((hits / len(expected_keywords)), 3) if expected_keywords else 1.0,
                "latency_ms": round(elapsed_ms, 3),
                "confidence": out.confidence,
            }
        )

    total = len(items)
    return {
        "total": total,
        "top1_accuracy": round((correct_top1 / total), 3) if total else 0.0,
        "keyword_coverage": round((keyword_hits / total_keywords), 3) if total_keywords else 1.0,
        "avg_latency_ms": round((total_latency / total), 3) if total else 0.0,
        "items": items,
    }


def benchmark_gate(
    report: dict[str, Any],
    *,
    min_top1_accuracy: float = 0.7,
    min_keyword_coverage: float = 0.7,
    max_avg_latency_ms: float = 0.0,
) -> dict[str, Any]:
    failures: list[str] = []
    total = int(report.get("total", 0))
    top1 = float(report.get("top1_accuracy", 0.0))
    keyword = float(report.get("keyword_coverage", 0.0))
    latency = float(report.get("avg_latency_ms", 0.0))

    if total <= 0:
        failures.append("dataset_is_empty")
    if top1 < min_top1_accuracy:
        failures.append(f"top1_accuracy_below_threshold:{top1}<{min_top1_accuracy}")
    if keyword < min_keyword_coverage:
        failures.append(f"keyword_coverage_below_threshold:{keyword}<{min_keyword_coverage}")
    if max_avg_latency_ms > 0 and latency > max_avg_latency_ms:
        failures.append(f"avg_latency_above_threshold:{latency}>{max_avg_latency_ms}")

    return {
        "ok": len(failures) == 0,
        "failures": failures,
        "thresholds": {
            "min_top1_accuracy": min_top1_accuracy,
            "min_keyword_coverage": min_keyword_coverage,
            "max_avg_latency_ms": max_avg_latency_ms,
        },
        "metrics": {
            "total": total,
            "top1_accuracy": top1,
            "keyword_coverage": keyword,
            "avg_latency_ms": latency,
        },
    }


def score_problem_validation(
    *,
    pain_frequency: int,
    impact: int,
    ownership_urgency: int,
    workaround_weakness: int,
    budget_willingness: int,
) -> dict[str, Any]:
    values = [pain_frequency, impact, ownership_urgency, workaround_weakness, budget_willingness]
    for value in values:
        if value < 0 or value > 5:
            raise ValueError("All score dimensions must be in range 0..5")
    total = sum(values)
    if total >= 18:
        segment = "strong_pain_segment"
    elif total >= 12:
        segment = "needs_sharper_wedge"
    else:
        segment = "pivot_recommended"
    return {
        "total": total,
        "segment": segment,
        "dimensions": {
            "pain_frequency": pain_frequency,
            "impact": impact,
            "ownership_urgency": ownership_urgency,
            "workaround_weakness": workaround_weakness,
            "budget_willingness": budget_willingness,
        },
    }


def interview_script() -> dict[str, Any]:
    return {
        "objective": "Validate if decision-memory pain is severe enough to pay for.",
        "questions": [
            "Last time your team asked why the system is like this?",
            "How long did it take to get a reliable answer?",
            "What changed because context was missing?",
            "Did you repeat a previously failed technical direction?",
            "What tools store this context today?",
            "What is broken in those tools?",
            "If solved, what metric improves first?",
            "Would you pay for this in the current budget cycle?",
        ],
        "success_signal": "At least 7/10 interviews describe repeated, costly memory loss events.",
    }


def design_partner_progress(
    *,
    target_partners: int,
    current_partners: int,
    validated_queries_per_week: int,
    time_to_answer_reduction_pct: float,
) -> dict[str, Any]:
    if target_partners <= 0:
        raise ValueError("target_partners must be > 0")
    if current_partners < 0:
        raise ValueError("current_partners must be >= 0")
    if validated_queries_per_week < 0:
        raise ValueError("validated_queries_per_week must be >= 0")
    if time_to_answer_reduction_pct < 0:
        raise ValueError("time_to_answer_reduction_pct must be >= 0")

    partner_ratio = min(1.0, current_partners / target_partners)
    query_ratio = min(1.0, validated_queries_per_week / 10.0)
    speed_ratio = min(1.0, time_to_answer_reduction_pct / 30.0)
    readiness = round((0.5 * partner_ratio) + (0.3 * query_ratio) + (0.2 * speed_ratio), 3)
    status = "on_track" if readiness >= 0.7 else ("at_risk" if readiness >= 0.4 else "off_track")
    return {
        "target_partners": target_partners,
        "current_partners": current_partners,
        "validated_queries_per_week": validated_queries_per_week,
        "time_to_answer_reduction_pct": time_to_answer_reduction_pct,
        "readiness_score": readiness,
        "status": status,
    }
