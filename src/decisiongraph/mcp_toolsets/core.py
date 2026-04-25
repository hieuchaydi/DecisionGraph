from __future__ import annotations

from decisiongraph.service import DecisionGraphService


def register_core_tools(mcp, service: DecisionGraphService) -> None:
    @mcp.tool()
    def query_decision(question: str) -> dict:
        """Answer a why-question using stored engineering decisions."""
        return service.query(question).to_dict()

    @mcp.tool()
    def list_decisions(
        limit: int = 20,
        query: str = "",
        tag: str = "",
        component: str = "",
        owner: str = "",
        decision_type: str = "",
    ) -> list[dict]:
        """List decisions with optional search/filter controls."""
        rows = service.list_decisions(
            limit=limit,
            query=query or None,
            tag=tag or None,
            component=component or None,
            owner=owner or None,
            decision_type=decision_type or None,
        )
        return [row.to_dict() for row in rows]

    @mcp.tool()
    def supersede_decision(decision_id: str, superseded_decision_id: str) -> dict:
        """Mark decision_id as superseding superseded_decision_id."""
        row = service.supersede_decision(
            decision_id=decision_id,
            superseded_decision_id=superseded_decision_id,
        )
        return row.to_dict()

    @mcp.tool()
    def merge_decisions(primary_decision_id: str, duplicate_decision_id: str, note: str = "") -> dict:
        """Merge duplicate decision into a primary decision."""
        row = service.merge_decisions(
            primary_decision_id=primary_decision_id,
            duplicate_decision_id=duplicate_decision_id,
            note=note,
        )
        return row.to_dict()

    @mcp.tool()
    def ingest_text(source_id: str, text: str, source_type: str = 'note') -> dict:
        """Ingest raw reasoning text and extract a decision."""
        row = service.ingest_text(source_id=source_id, text=text, source_type=source_type)
        return row.to_dict()

    @mcp.tool()
    def guardrail(change_request: str, limit: int = 3) -> dict:
        """Run pre-change guardrail checks on proposed code modifications."""
        return service.guardrail(change_request=change_request, limit=limit).to_dict()

    @mcp.tool()
    def detect_contradictions() -> list[dict]:
        """Find potential contradictory decisions in decision history."""
        return [item.to_dict() for item in service.detect_contradictions()]

    @mcp.tool()
    def stale_assumptions() -> list[dict]:
        """List assumptions that are violated by current metric snapshots."""
        return [item.to_dict() for item in service.detect_stale_assumptions()]

    @mcp.tool()
    def watch_assumptions(
        warn_severities: str = "medium,high",
        critical_severities: str = "high",
        notify: bool = False,
        notify_target: str = "webhook",
        webhook_url: str = "",
    ) -> dict:
        """Run assumption watcher and emit alerts for new/escalated stale assumptions."""
        warn_list = [entry.strip() for entry in warn_severities.split(",") if entry.strip()]
        critical_list = [entry.strip() for entry in critical_severities.split(",") if entry.strip()]
        return service.run_assumption_watch(
            warn_severities=warn_list,
            critical_severities=critical_list,
            notify=notify,
            notify_target=notify_target,
            webhook_url=webhook_url or None,
        )

    @mcp.tool()
    def decision_timeline(
        limit: int = 200,
        component: str = "",
        tag: str = "",
        owner: str = "",
        decision_type: str = "",
        include_superseded: bool = True,
    ) -> dict:
        """Return chronological timeline of decisions."""
        return service.decision_timeline(
            limit=limit,
            component=component or None,
            tag=tag or None,
            owner=owner or None,
            decision_type=decision_type or None,
            include_superseded=include_superseded,
        )

    @mcp.tool()
    def evidence_quality(limit: int = 200, weak_threshold: float = 0.45) -> dict:
        """Score evidence quality and flag weak decisions."""
        return service.evidence_quality_report(limit=limit, weak_threshold=weak_threshold)

    @mcp.tool()
    def audit_logs(limit: int = 100, event: str = "") -> list[dict]:
        """Return latest audit log events."""
        return service.list_audit_logs(limit=limit, event_type=event or None)

    @mcp.tool()
    def set_metric(key: str, value: float, unit: str = '') -> dict:
        """Set a current metric value used for stale-assumption detection."""
        metric = service.set_metric(key=key, value=value, unit=unit or None)
        return metric.to_dict()

    @mcp.tool()
    def graph_snapshot() -> dict:
        """Return the current decision/evidence graph snapshot."""
        return service.graph_snapshot()

    @mcp.tool()
    def summary_report(format: str = 'json') -> dict | str:
        """Generate a summary report for decision memory health."""
        report = service.summary_report()
        if format.lower() == 'markdown':
            return report['markdown']
        return report['json']
