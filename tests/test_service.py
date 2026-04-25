from __future__ import annotations

from pathlib import Path

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
