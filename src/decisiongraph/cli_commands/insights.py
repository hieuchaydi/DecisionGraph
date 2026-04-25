from __future__ import annotations

from pathlib import Path

import typer

from decisiongraph.insights import (
    benchmark_gate,
    design_partner_progress,
    evaluate_dataset,
    interview_script,
    kpi_snapshot,
    run_scenarios,
    score_problem_validation,
)
from decisiongraph.cli_commands.service_factory import build_service
from decisiongraph.cli_commands.utils import echo_json


def register_insight_commands(app: typer.Typer) -> None:
    @app.command('scenarios')
    def scenarios() -> None:
        service = build_service()
        echo_json(run_scenarios(service))

    @app.command('kpi')
    def kpi() -> None:
        service = build_service()
        echo_json(kpi_snapshot(service))

    @app.command('eval-dataset')
    def eval_dataset(
        dataset: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False, help='JSONL evaluation dataset'),
    ) -> None:
        service = build_service()
        echo_json(evaluate_dataset(service, dataset_path=dataset))

    @app.command('benchmark-check')
    def benchmark_check(
        dataset: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False, help='JSONL evaluation dataset'),
        min_top1: float = typer.Option(0.7, min=0.0, max=1.0, help='Minimum top-1 accuracy'),
        min_keyword_coverage: float = typer.Option(0.7, min=0.0, max=1.0, help='Minimum keyword coverage'),
        max_avg_latency_ms: float = typer.Option(0.0, min=0.0, help='Maximum average latency in ms (0 disables)'),
        seed_demo: bool = typer.Option(
            False,
            '--seed-demo/--no-seed-demo',
            help='Seed demo decisions before benchmark run',
        ),
    ) -> None:
        service = build_service()
        if seed_demo:
            service.seed_demo()
        report = evaluate_dataset(service, dataset_path=dataset)
        gate = benchmark_gate(
            report,
            min_top1_accuracy=min_top1,
            min_keyword_coverage=min_keyword_coverage,
            max_avg_latency_ms=max_avg_latency_ms,
        )
        echo_json({'report': report, 'gate': gate})
        if not gate['ok']:
            raise typer.Exit(code=1)

    @app.command('research-score')
    def research_score(
        pain_frequency: int = typer.Option(..., min=0, max=5),
        impact: int = typer.Option(..., min=0, max=5),
        ownership_urgency: int = typer.Option(..., min=0, max=5),
        workaround_weakness: int = typer.Option(..., min=0, max=5),
        budget_willingness: int = typer.Option(..., min=0, max=5),
    ) -> None:
        echo_json(
            score_problem_validation(
                pain_frequency=pain_frequency,
                impact=impact,
                ownership_urgency=ownership_urgency,
                workaround_weakness=workaround_weakness,
                budget_willingness=budget_willingness,
            )
        )

    @app.command('research-script')
    def research_script() -> None:
        echo_json(interview_script())

    @app.command('design-partner-progress')
    def design_partner_progress_cmd(
        target_partners: int = typer.Option(5, min=1),
        current_partners: int = typer.Option(0, min=0),
        validated_queries_per_week: int = typer.Option(0, min=0),
        time_to_answer_reduction_pct: float = typer.Option(0.0, min=0.0),
    ) -> None:
        echo_json(
            design_partner_progress(
                target_partners=target_partners,
                current_partners=current_partners,
                validated_queries_per_week=validated_queries_per_week,
                time_to_answer_reduction_pct=time_to_answer_reduction_pct,
            )
        )
