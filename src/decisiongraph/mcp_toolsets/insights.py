from __future__ import annotations

from pathlib import Path

from decisiongraph.insights import benchmark_gate, evaluate_dataset, kpi_snapshot, run_scenarios, score_problem_validation
from decisiongraph.insights import design_partner_progress, interview_script
from decisiongraph.service import DecisionGraphService


def register_insight_tools(mcp, service: DecisionGraphService) -> None:
    @mcp.tool()
    def run_scenarios_tool() -> dict:
        """Run default decision query scenarios and return pass/fail report."""
        return run_scenarios(service)

    @mcp.tool()
    def kpi_snapshot_tool() -> dict:
        """Return KPI snapshot for decision memory health."""
        return kpi_snapshot(service)

    @mcp.tool()
    def eval_dataset(path: str) -> dict:
        """Evaluate query quality against a JSONL dataset."""
        return evaluate_dataset(service, dataset_path=Path(path).expanduser().resolve())

    @mcp.tool()
    def benchmark_check(
        path: str,
        min_top1_accuracy: float = 0.7,
        min_keyword_coverage: float = 0.7,
        max_avg_latency_ms: float = 0.0,
    ) -> dict:
        """Run dataset evaluation and apply release gate thresholds."""
        report = evaluate_dataset(service, dataset_path=Path(path).expanduser().resolve())
        gate = benchmark_gate(
            report,
            min_top1_accuracy=min_top1_accuracy,
            min_keyword_coverage=min_keyword_coverage,
            max_avg_latency_ms=max_avg_latency_ms,
        )
        return {"report": report, "gate": gate}

    @mcp.tool()
    def research_scorecard(
        pain_frequency: int,
        impact: int,
        ownership_urgency: int,
        workaround_weakness: int,
        budget_willingness: int,
    ) -> dict:
        """Score problem-validation interview using the 5-dimension scorecard."""
        return score_problem_validation(
            pain_frequency=pain_frequency,
            impact=impact,
            ownership_urgency=ownership_urgency,
            workaround_weakness=workaround_weakness,
            budget_willingness=budget_willingness,
        )

    @mcp.tool()
    def research_interview_script() -> dict:
        """Return customer interview script for problem validation."""
        return interview_script()

    @mcp.tool()
    def design_partner_progress_tool(
        target_partners: int = 5,
        current_partners: int = 0,
        validated_queries_per_week: int = 0,
        time_to_answer_reduction_pct: float = 0.0,
    ) -> dict:
        """Score current design partner program progress."""
        return design_partner_progress(
            target_partners=target_partners,
            current_partners=current_partners,
            validated_queries_per_week=validated_queries_per_week,
            time_to_answer_reduction_pct=time_to_answer_reduction_pct,
        )
