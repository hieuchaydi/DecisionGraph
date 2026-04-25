from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from decisiongraph.api_schemas import DesignPartnerProgressRequest, EvalDatasetRequest, ResearchScoreRequest
from decisiongraph.insights import evaluate_dataset, kpi_snapshot, run_scenarios, score_problem_validation
from decisiongraph.insights import design_partner_progress, interview_script
from decisiongraph.ops import doctor, release_check, runbook, schema_info, security_audit
from decisiongraph.service import DecisionGraphService
from decisiongraph.strategy import get_section, list_sections, search_sections


def create_intelligence_router(service: DecisionGraphService) -> APIRouter:
    router = APIRouter()

    @router.get('/api/scenarios/run')
    def scenario_run() -> dict[str, object]:
        return run_scenarios(service)

    @router.get('/api/kpi/snapshot')
    def api_kpi_snapshot() -> dict[str, object]:
        return kpi_snapshot(service)

    @router.post('/api/eval/dataset')
    def api_eval_dataset(payload: EvalDatasetRequest) -> dict[str, object]:
        path = Path(payload.path).expanduser().resolve()
        try:
            return evaluate_dataset(service, dataset_path=path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post('/api/research/scorecard')
    def api_research_scorecard(payload: ResearchScoreRequest) -> dict[str, object]:
        return score_problem_validation(
            pain_frequency=payload.pain_frequency,
            impact=payload.impact,
            ownership_urgency=payload.ownership_urgency,
            workaround_weakness=payload.workaround_weakness,
            budget_willingness=payload.budget_willingness,
        )

    @router.get('/api/research/interview-script')
    def api_research_interview_script() -> dict[str, object]:
        return interview_script()

    @router.post('/api/research/design-partner-progress')
    def api_research_design_partner_progress(payload: DesignPartnerProgressRequest) -> dict[str, object]:
        return design_partner_progress(
            target_partners=payload.target_partners,
            current_partners=payload.current_partners,
            validated_queries_per_week=payload.validated_queries_per_week,
            time_to_answer_reduction_pct=payload.time_to_answer_reduction_pct,
        )

    @router.get('/api/strategy/sections')
    def api_strategy_sections() -> dict[str, object]:
        return {'items': list_sections()}

    @router.get('/api/strategy/section/{section_id}')
    def api_strategy_section(section_id: str) -> dict[str, object]:
        try:
            return get_section(section_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get('/api/strategy/search')
    def api_strategy_search(q: str = '') -> dict[str, object]:
        return {'items': search_sections(q)}

    @router.get('/api/ops/doctor')
    def api_ops_doctor() -> dict[str, object]:
        return doctor()

    @router.get('/api/ops/runbook')
    def api_ops_runbook() -> dict[str, object]:
        return runbook()

    @router.get('/api/ops/release-check')
    def api_ops_release_check(project_root: str = '.') -> dict[str, object]:
        root = Path(project_root).expanduser().resolve()
        return release_check(project_root=root)

    @router.get('/api/ops/security-audit')
    def api_ops_security_audit() -> dict[str, object]:
        return security_audit()

    @router.get('/api/schema/info')
    def api_schema_info() -> dict[str, object]:
        return schema_info()

    return router
