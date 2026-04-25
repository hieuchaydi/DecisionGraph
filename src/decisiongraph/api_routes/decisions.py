from __future__ import annotations

from fastapi import APIRouter, HTTPException

from decisiongraph.api_schemas import (
    AssumptionWatchRequest,
    GuardrailRequest,
    MergeDecisionRequest,
    MetricUpsertRequest,
    QueryRequest,
    SupersedeRequest,
)
from decisiongraph.service import DecisionGraphService


def create_decision_router(service: DecisionGraphService) -> APIRouter:
    router = APIRouter()

    @router.get('/api/decisions')
    def list_decisions(
        limit: int = 20,
        q: str | None = None,
        tag: str | None = None,
        component: str | None = None,
        owner: str | None = None,
        decision_type: str | None = None,
    ) -> dict[str, object]:
        rows = [
            item.to_dict()
            for item in service.list_decisions(
                limit=limit,
                query=q,
                tag=tag,
                component=component,
                owner=owner,
                decision_type=decision_type,
            )
        ]
        return {'count': len(rows), 'items': rows}

    @router.post('/api/decisions/supersede')
    def supersede(payload: SupersedeRequest) -> dict[str, object]:
        try:
            row = service.supersede_decision(
                decision_id=payload.decision_id,
                superseded_decision_id=payload.superseded_decision_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {'status': 'ok', 'decision': row.to_dict()}

    @router.post('/api/decisions/merge')
    def merge_decision(payload: MergeDecisionRequest) -> dict[str, object]:
        try:
            row = service.merge_decisions(
                primary_decision_id=payload.primary_decision_id,
                duplicate_decision_id=payload.duplicate_decision_id,
                note=payload.note,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {'status': 'ok', 'decision': row.to_dict()}

    @router.get('/api/decisions/timeline')
    def decision_timeline(
        limit: int = 200,
        component: str | None = None,
        tag: str | None = None,
        owner: str | None = None,
        decision_type: str | None = None,
        include_superseded: bool = True,
    ) -> dict[str, object]:
        return service.decision_timeline(
            limit=limit,
            component=component,
            tag=tag,
            owner=owner,
            decision_type=decision_type,
            include_superseded=include_superseded,
        )

    @router.get('/api/decisions/evidence-quality')
    def evidence_quality(limit: int = 200, weak_threshold: float = 0.45) -> dict[str, object]:
        return service.evidence_quality_report(limit=limit, weak_threshold=weak_threshold)

    @router.get('/api/decisions/{decision_id}')
    def get_decision(decision_id: str) -> dict[str, object]:
        row = service.get_decision(decision_id)
        if not row:
            raise HTTPException(status_code=404, detail='Decision not found')
        return row.to_dict()

    @router.post('/api/query')
    def query(payload: QueryRequest) -> dict[str, object]:
        return service.query(payload.question).to_dict()

    @router.post('/api/guardrail')
    def guardrail(payload: GuardrailRequest) -> dict[str, object]:
        return service.guardrail(change_request=payload.change_request, limit=payload.limit).to_dict()

    @router.get('/api/contradictions')
    def contradictions() -> dict[str, object]:
        rows = service.detect_contradictions()
        return {'count': len(rows), 'items': [item.to_dict() for item in rows]}

    @router.get('/api/assumptions/stale')
    def stale_assumptions() -> dict[str, object]:
        rows = service.detect_stale_assumptions()
        return {'count': len(rows), 'items': [item.to_dict() for item in rows]}

    @router.post('/api/assumptions/watch')
    def assumption_watch(payload: AssumptionWatchRequest) -> dict[str, object]:
        try:
            return service.run_assumption_watch(
                warn_severities=payload.warn_severities,
                critical_severities=payload.critical_severities,
                notify=payload.notify,
                notify_target=payload.notify_target,
                webhook_url=payload.webhook_url,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get('/api/audit/logs')
    def audit_logs(limit: int = 100, event: str | None = None) -> dict[str, object]:
        rows = service.list_audit_logs(limit=limit, event_type=event)
        return {'count': len(rows), 'items': rows}

    @router.get('/api/metrics')
    def list_metrics() -> dict[str, object]:
        rows = service.list_metrics()
        return {'count': len(rows), 'items': [item.to_dict() for item in rows]}

    @router.post('/api/metrics')
    def upsert_metric(payload: MetricUpsertRequest) -> dict[str, object]:
        snapshot = service.set_metric(key=payload.key, value=payload.value, unit=payload.unit)
        return {'status': 'ok', 'metric': snapshot.to_dict()}

    @router.get('/api/graph')
    def graph_snapshot() -> dict[str, object]:
        return service.graph_snapshot()

    return router
