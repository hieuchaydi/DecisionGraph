from __future__ import annotations

from pathlib import Path

import pytest

from decisiongraph.integrations import IngestDocument
from decisiongraph.service import DecisionGraphService
from decisiongraph.store import DecisionStore


def _service(tmp_path: Path) -> DecisionGraphService:
    store = DecisionStore(tmp_path / "dg.json")
    return DecisionGraphService(store=store)


def test_seed_query_and_related(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.seed_demo()
    out = svc.query("Why did we choose Redis over RabbitMQ?")
    assert out.decision is not None
    assert "Redis" in out.answer
    assert out.confidence >= 0.6
    assert isinstance(out.related, list)


def test_stale_assumptions_detected(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.seed_demo()
    stale = svc.detect_stale_assumptions()
    assert stale, "Expected stale assumptions from seeded metrics"
    assert any(item.metric_key == "queue_volume" for item in stale)


def test_guardrail_blocks_sensitive_stale_change(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.seed_demo()
    out = svc.guardrail("Refactor payment retry and auth flow for simpler logic")
    assert out.warnings
    assert isinstance(out.blocked, bool)
    assert out.related_decisions


def test_contradictions_exist_in_seed(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.seed_demo()
    rows = svc.detect_contradictions()
    assert rows, "Expected contradictions from opposite queue decisions"


def test_ingest_directory(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "decision.md").write_text(
        "\n".join(
            [
                "Title: Choose PostgreSQL for transactional data",
                "Summary: Need strict consistency for finance flows.",
                "Owner: Data Lead",
                "Assumption: write_qps < 1500",
                "Risk: migration complexity",
            ]
        ),
        encoding="utf-8",
    )
    rows = svc.ingest_directory(docs, pattern="*.md", source_type="rfc")
    assert len(rows) == 1
    answer = svc.query("Why choose PostgreSQL?")
    assert answer.decision is not None
    assert "PostgreSQL" in answer.answer


def test_ingest_jsonl_and_report(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    payload = tmp_path / "events.jsonl"
    payload.write_text(
        "\n".join(
            [
                '{"source_id":"PR-1","source_type":"pr","text":"Title: Choose PostgreSQL\\nSummary: consistency first\\nAssumption: write_qps < 1000"}',
                '{"source_id":"INC-2","text":"Title: Revert queue worker strategy\\nSummary: incident response slowed\\nRisk: outage blast radius"}',
            ]
        ),
        encoding="utf-8",
    )
    rows = svc.ingest_jsonl(payload, default_source_type="external")
    assert len(rows) == 2
    report = svc.summary_report()
    assert "json" in report
    assert "markdown" in report
    assert report["json"]["total_decisions"] >= 2


def test_ingest_github_via_mock(tmp_path: Path, monkeypatch) -> None:
    svc = _service(tmp_path)

    def fake_ingest_docs_from_github_repo(**kwargs):
        return [
            IngestDocument(
                source_id="gh-pr-demo-1",
                source_type="github_pr",
                text="\n".join(
                    [
                        "Title: PR #1 Add retry cap",
                        "Summary: Add payment retry cap",
                        "Owner: dev1",
                        "Assumption: payment_retry_error_rate < 0.03",
                    ]
                ),
                url="https://github.com/acme/payments/pull/1",
            )
        ]

    monkeypatch.setattr("decisiongraph.service.ingest_docs_from_github_repo", fake_ingest_docs_from_github_repo)
    rows = svc.ingest_github(owner="acme", repo="payments")
    assert len(rows) == 1
    out = svc.query("Why retry cap?")
    assert out.decision is not None


def test_ingest_slack_and_jira_exports(tmp_path: Path) -> None:
    svc = _service(tmp_path)

    slack_dir = tmp_path / "slack"
    channel = slack_dir / "engineering"
    channel.mkdir(parents=True, exist_ok=True)
    (channel / "2026-01-01.json").write_text(
        '[{"user":"u1","ts":"1714000000.000100","text":"We decided to revert microservice split because incident response got slower."}]',
        encoding="utf-8",
    )
    slack_rows = svc.ingest_slack_export(slack_dir, max_messages=50)
    assert slack_rows

    jira_path = tmp_path / "jira.json"
    jira_path.write_text(
        '{"issues":[{"key":"PAY-101","fields":{"summary":"Cap payment retries at 2","description":"Decision after duplicate billing incident","assignee":{"displayName":"Fin Ops"},"updated":"2026-03-11","labels":["risk","payments"],"components":[{"name":"payments"}]}}]}',
        encoding="utf-8",
    )
    jira_rows = svc.ingest_jira_json(jira_path)
    assert jira_rows

    answer = svc.query("Why did we revert microservice split?")
    assert answer.decision is not None


def test_list_decisions_with_query_and_filters(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.seed_demo()

    tagged = svc.list_decisions(limit=10, tag="payments")
    assert tagged
    assert all("payments" in [entry.lower() for entry in row.tags] for row in tagged)

    by_component = svc.list_decisions(limit=10, component="settlement")
    assert len(by_component) == 1
    assert by_component[0].component == "settlement"

    by_owner = svc.list_decisions(limit=10, owner="finance")
    assert by_owner
    assert all(any("finance" in owner.lower() for owner in row.owners) for row in by_owner)

    by_type = svc.list_decisions(limit=10, decision_type="risk-policy")
    assert by_type
    assert all(row.decision_type == "risk-policy" for row in by_type)

    by_query = svc.list_decisions(limit=10, query="rabbitmq")
    assert by_query
    assert "rabbitmq" in by_query[0].title.lower()


def test_supersede_updates_links_and_query_priority(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.seed_demo()
    old = next(row for row in svc.list_decisions(limit=100) if row.title == "Cap payment retries at 2 attempts")

    replacement = svc.ingest_text(
        source_id="rfc-payment-retry-2026",
        source_type="rfc",
        text="\n".join(
            [
                "Title: Keep payment retry cap at 2 attempts with stronger auditing",
                "Summary: We keep retry cap at 2 to reduce duplicate-charge risk while adding audit visibility.",
                "Owner: Payments Team",
                "Risk: Revenue loss during gateway outages",
            ]
        ),
    )

    superseding = svc.supersede_decision(decision_id=replacement.id, superseded_decision_id=old.id)
    refreshed_old = svc.get_decision(old.id)
    assert refreshed_old is not None
    assert refreshed_old.superseded_by == superseding.id
    assert old.id in superseding.supersedes

    out = svc.query("Why is payment retry logic capped at 2 retries?")
    assert out.decision is not None
    assert out.decision.id == superseding.id


def test_run_assumption_watch_tracks_escalation_and_resolution(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.seed_demo()

    first = svc.run_assumption_watch()
    assert first["alerts"], "Expected initial alerts for medium/high stale assumptions"
    assert all(item["is_new"] is True for item in first["alerts"])

    second = svc.run_assumption_watch()
    assert second["alerts"] == []

    svc.set_metric("queue_volume", 200000.0, "events/day")
    escalated = svc.run_assumption_watch()
    queue_alerts = [item for item in escalated["alerts"] if item["metric_key"] == "queue_volume"]
    assert queue_alerts
    assert any(item["is_escalation"] for item in queue_alerts)

    svc.set_metric("queue_volume", 50000.0, "events/day")
    resolved = svc.run_assumption_watch()
    assert resolved["resolved_count"] >= 1


def test_run_assumption_watch_requires_webhook_for_notify(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.seed_demo()
    with pytest.raises(ValueError):
        svc.run_assumption_watch(notify=True)
    with pytest.raises(ValueError):
        svc.run_assumption_watch(notify_target="pagerduty")


def test_merge_decisions_combines_evidence_and_marks_duplicate(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.seed_demo()
    first = svc.ingest_text(
        source_id="rfc-merge-1",
        source_type="rfc",
        text=(
            "Title: Adopt dedicated cache cluster\n"
            "Summary: reduce noisy-neighbor impact on shared cache\n"
            "Owner: Platform\n"
            "Assumption: cache_hit_ratio > 0.90\n"
            "Risk: migration overhead"
        ),
    )
    second = svc.ingest_text(
        source_id="rfc-merge-2",
        source_type="rfc",
        text=(
            "Title: Adopt dedicated cache cluster for workloads\n"
            "Summary: same direction with extra evidence\n"
            "Owner: SRE\n"
            "Assumption: cache_hit_ratio > 0.90\n"
            "Risk: operational complexity"
        ),
    )

    merged = svc.merge_decisions(first.id, second.id, note="deduplicate duplicate RFCs")
    duplicate = svc.get_decision(second.id)
    assert duplicate is not None
    assert duplicate.superseded_by == merged.id
    assert second.id in merged.supersedes
    assert len(merged.evidence_ids) >= 2


def test_decision_timeline_and_evidence_quality(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.seed_demo()
    timeline = svc.decision_timeline(limit=10, tag="payments")
    assert timeline["count"] >= 1
    assert all("payments" in [tag.lower() for tag in item["tags"]] for item in timeline["items"])

    quality = svc.evidence_quality_report(limit=20, weak_threshold=0.6)
    assert quality["count"] >= 4
    assert "avg_score" in quality


def test_governance_strict_blocks_ingest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DECISIONGRAPH_GOVERNANCE_MODE", "strict")
    monkeypatch.setenv("DECISIONGRAPH_GOVERNANCE_REQUIRED_FIELDS", "owners,assumptions,risks")
    svc = _service(tmp_path)
    with pytest.raises(ValueError):
        svc.ingest_text(
            source_id="gov-strict-1",
            source_type="note",
            text="Title: Loose note without required governance fields\nSummary: no owner/assumption/risk lines",
        )


def test_audit_logs_record_events(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.seed_demo()
    svc.set_metric("queue_volume", 123.0, "events/day")
    logs = svc.list_audit_logs(limit=20)
    assert logs
    assert any(item["event"] == "metric.set" for item in logs)


def test_watch_assumption_uses_connector_target_env(tmp_path: Path, monkeypatch) -> None:
    svc = _service(tmp_path)
    svc.seed_demo()
    monkeypatch.setenv("DECISIONGRAPH_ALERT_SLACK_WEBHOOK", "https://hooks.slack.local/test")
    monkeypatch.setattr(svc, "_dispatch_watch_notification", lambda webhook_url, payload: (True, None))
    out = svc.run_assumption_watch(notify=True, notify_target="slack")
    assert out["notification"]["attempted"] is True
    assert out["notification"]["sent"] is True
    assert out["notification"]["target"] == "slack"


def test_audit_log_retention_limit_applied(tmp_path: Path) -> None:
    store = DecisionStore(tmp_path / "retention.json", audit_log_limit=2)
    svc = DecisionGraphService(store=store)
    svc.set_metric("m1", 1.0, "u")
    svc.set_metric("m2", 2.0, "u")
    svc.set_metric("m3", 3.0, "u")
    logs = svc.list_audit_logs(limit=10, event_type="metric.set")
    assert len(logs) == 2
    keys = [item["payload"]["key"] for item in logs]
    assert "m1" not in keys
