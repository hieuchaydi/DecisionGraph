from __future__ import annotations

from fastapi import APIRouter, HTTPException

from decisiongraph.api_schemas import GuardrailRequest, MetricUpsertRequest, QueryRequest
from decisiongraph.service import DecisionGraphService


def create_decision_router(service: DecisionGraphService) -> APIRouter:
    router = APIRouter()

    @router.get('/api/decisions')
    def list_decisions(limit: int = 20) -> dict[str, object]:
        rows = [item.to_dict() for item in service.list_decisions(limit=limit)]
        return {'count': len(rows), 'items': rows}

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
