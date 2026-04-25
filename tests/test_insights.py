from __future__ import annotations

import json
from pathlib import Path

from decisiongraph.insights import (
    design_partner_progress,
    evaluate_dataset,
    interview_script,
    kpi_snapshot,
    run_scenarios,
    score_problem_validation,
)
from decisiongraph.service import DecisionGraphService
from decisiongraph.store import DecisionStore


def _service(tmp_path: Path) -> DecisionGraphService:
    return DecisionGraphService(DecisionStore(tmp_path / "dg.json"))


def test_scenarios_and_kpi(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.seed_demo()
    scenarios = run_scenarios(svc)
    assert scenarios["total"] >= 4
    kpi = kpi_snapshot(svc)
    assert "total_decisions" in kpi
    assert kpi["total_decisions"] >= 4


def test_eval_dataset(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.seed_demo()
    ds = tmp_path / "eval.jsonl"
    ds.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "question": "Why did we choose Redis instead of RabbitMQ?",
                        "expected_title_contains": "redis",
                        "expected_keywords": ["redis", "rabbitmq"],
                    }
                ),
                json.dumps(
                    {
                        "question": "Why payment retry capped at 2?",
                        "expected_title_contains": "payment",
                        "expected_keywords": ["payment", "retry"],
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    out = evaluate_dataset(svc, dataset_path=ds)
    assert out["total"] == 2
    assert "top1_accuracy" in out


def test_problem_validation_scorecard() -> None:
    out = score_problem_validation(
        pain_frequency=5,
        impact=4,
        ownership_urgency=4,
        workaround_weakness=3,
        budget_willingness=3,
    )
    assert out["total"] == 19
    assert out["segment"] == "strong_pain_segment"


def test_interview_script_and_design_partner_progress() -> None:
    script = interview_script()
    assert script["questions"]
    progress = design_partner_progress(
        target_partners=5,
        current_partners=3,
        validated_queries_per_week=8,
        time_to_answer_reduction_pct=25.0,
    )
    assert progress["status"] in {"on_track", "at_risk", "off_track"}
