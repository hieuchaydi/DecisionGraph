from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from decisiongraph.api import app, SERVICE


def test_api_health() -> None:
    client = TestClient(app)
    out = client.get("/health")
    assert out.status_code == 200
    assert out.json()["status"] == "ok"


def test_api_query_and_guardrail_roundtrip() -> None:
    SERVICE.seed_demo()
    client = TestClient(app)

    q = client.post("/api/query", json={"question": "Why retries are capped at 2?"})
    assert q.status_code == 200
    payload = q.json()
    assert "answer" in payload

    g = client.post("/api/guardrail", json={"change_request": "Change payment retry and auth behavior"})
    assert g.status_code == 200
    guardrail = g.json()
    assert "warnings" in guardrail
    assert "blocked" in guardrail


def test_api_report_and_jsonl_ingest(tmp_path: Path) -> None:
    client = TestClient(app)
    source = tmp_path / "import.jsonl"
    source.write_text(
        '{"source_id":"RFC-7","text":"Title: Use feature flags\\nSummary: safer rollout path"}\n',
        encoding="utf-8",
    )
    ing = client.post("/api/ingest/jsonl", json={"path": str(source), "source_type": "external"})
    assert ing.status_code == 200
    out = client.get("/api/report/summary")
    assert out.status_code == 200
    assert "total_decisions" in out.json()


def test_api_auth_middleware(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setenv("DECISIONGRAPH_API_TOKEN", "secret-token")
    unauthorized = client.post("/api/query", json={"question": "Why?"})
    assert unauthorized.status_code == 401
    authorized = client.post("/api/query", headers={"x-api-key": "secret-token"}, json={"question": "Why?"})
    assert authorized.status_code == 200


def test_api_ingest_github_with_mock(monkeypatch) -> None:
    client = TestClient(app)

    def fake_ingest_github(**kwargs):
        return []

    monkeypatch.setattr(SERVICE, "ingest_github", fake_ingest_github)
    out = client.post(
        "/api/ingest/github",
        json={"owner": "acme", "repo": "payments", "max_prs": 5, "max_issues": 5, "state": "all"},
    )
    assert out.status_code == 200
    assert out.json()["count"] == 0


def test_api_ingest_slack_and_jira(tmp_path: Path) -> None:
    client = TestClient(app)
    slack_dir = tmp_path / "slack"
    ch = slack_dir / "engineering"
    ch.mkdir(parents=True, exist_ok=True)
    (ch / "2026-01-02.json").write_text(
        '[{"user":"u2","ts":"1714100000.000100","text":"We decided to keep Redis queues for now due to team size."}]',
        encoding="utf-8",
    )
    jira_path = tmp_path / "jira.json"
    jira_path.write_text(
        '{"issues":[{"key":"ARCH-10","fields":{"summary":"Revert microservice rollout","description":"Too much ops overhead","updated":"2026-02-10"}}]}',
        encoding="utf-8",
    )

    s = client.post("/api/ingest/slack-export", json={"export_dir": str(slack_dir), "max_messages": 100})
    assert s.status_code == 200
    j = client.post("/api/ingest/jira-json", json={"path": str(jira_path)})
    assert j.status_code == 200


def test_api_kpi_scenarios_eval_and_research(tmp_path: Path) -> None:
    SERVICE.seed_demo()
    client = TestClient(app)
    k = client.get("/api/kpi/snapshot")
    assert k.status_code == 200
    assert "total_decisions" in k.json()

    s = client.get("/api/scenarios/run")
    assert s.status_code == 200
    assert "pass_rate" in s.json()

    ds = tmp_path / "eval.jsonl"
    ds.write_text(
        '{"question":"Why did we choose Redis instead of RabbitMQ?","expected_title_contains":"redis","expected_keywords":["redis","rabbitmq"]}\n',
        encoding="utf-8",
    )
    e = client.post("/api/eval/dataset", json={"path": str(ds)})
    assert e.status_code == 200
    assert "top1_accuracy" in e.json()

    r = client.post(
        "/api/research/scorecard",
        json={
            "pain_frequency": 4,
            "impact": 4,
            "ownership_urgency": 3,
            "workaround_weakness": 3,
            "budget_willingness": 3,
        },
    )
    assert r.status_code == 200
    assert "segment" in r.json()

    script = client.get("/api/research/interview-script")
    assert script.status_code == 200
    assert "questions" in script.json()

    dp = client.post(
        "/api/research/design-partner-progress",
        json={
            "target_partners": 5,
            "current_partners": 2,
            "validated_queries_per_week": 7,
            "time_to_answer_reduction_pct": 18.0,
        },
    )
    assert dp.status_code == 200
    assert "readiness_score" in dp.json()

    sections = client.get("/api/strategy/sections")
    assert sections.status_code == 200
    assert sections.json()["items"]

    section = client.get("/api/strategy/section/pricing")
    assert section.status_code == 200
    assert section.json()["id"] == "pricing_packaging"

    search = client.get("/api/strategy/search?q=incident")
    assert search.status_code == 200
    assert "items" in search.json()

    ops = client.get("/api/ops/doctor")
    assert ops.status_code == 200
    assert "checks" in ops.json()

    rb = client.get("/api/ops/runbook")
    assert rb.status_code == 200
    assert "daily_dev_loop" in rb.json()

    sec = client.get("/api/ops/security-audit")
    assert sec.status_code == 200
    assert "api_mode" in sec.json()

    schema = client.get("/api/schema/info")
    assert schema.status_code == 200
    assert "schema_version" in schema.json()


def test_api_decisions_support_query_and_filters() -> None:
    SERVICE.seed_demo()
    client = TestClient(app)

    search = client.get("/api/decisions", params={"q": "rabbitmq", "tag": "queues", "limit": 5})
    assert search.status_code == 200
    payload = search.json()
    assert payload["count"] >= 1
    assert any("rabbitmq" in item["title"].lower() for item in payload["items"])

    filtered = client.get("/api/decisions", params={"owner": "finance", "decision_type": "risk-policy"})
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert filtered_payload["count"] >= 1
    assert all(item["decision_type"] == "risk-policy" for item in filtered_payload["items"])
    assert all(any("finance" in owner.lower() for owner in item["owners"]) for item in filtered_payload["items"])


def test_api_supersede_flow() -> None:
    SERVICE.seed_demo()
    client = TestClient(app)

    ing = client.post(
        "/api/ingest",
        json={
            "source_id": "rfc-payment-retry-2026",
            "source_type": "rfc",
            "text": (
                "Title: Keep payment retry cap at 2 attempts with stronger auditing\n"
                "Summary: We keep retry cap at 2 to reduce duplicate-charge risk while adding audit visibility."
            ),
        },
    )
    assert ing.status_code == 200
    new_id = ing.json()["decision"]["id"]
    old = next(item for item in SERVICE.list_decisions(limit=200) if item.title == "Cap payment retries at 2 attempts")

    sup = client.post(
        "/api/decisions/supersede",
        json={"decision_id": new_id, "superseded_decision_id": old.id},
    )
    assert sup.status_code == 200
    assert old.id in sup.json()["decision"]["supersedes"]


def test_api_assumption_watch_and_benchmark_gate(tmp_path: Path) -> None:
    SERVICE.seed_demo()
    client = TestClient(app)

    watch = client.post("/api/assumptions/watch", json={})
    assert watch.status_code == 200
    watch_payload = watch.json()
    assert "alerts" in watch_payload
    assert "critical_count" in watch_payload

    ds = tmp_path / "eval.jsonl"
    ds.write_text(
        '{"question":"Why did we choose Redis instead of RabbitMQ?","expected_title_contains":"redis","expected_keywords":["redis","rabbitmq"]}\n',
        encoding="utf-8",
    )
    gate = client.post(
        "/api/eval/benchmark-check",
        json={
            "path": str(ds),
            "min_top1_accuracy": 0.1,
            "min_keyword_coverage": 0.1,
            "max_avg_latency_ms": 0.0,
        },
    )
    assert gate.status_code == 200
    gate_payload = gate.json()
    assert "report" in gate_payload
    assert "gate" in gate_payload


def test_api_assumption_watch_notify_requires_webhook() -> None:
    client = TestClient(app)
    out = client.post("/api/assumptions/watch", json={"notify": True})
    assert out.status_code == 400


def test_api_assumption_watch_with_notify_target_env(monkeypatch) -> None:
    SERVICE.seed_demo()
    monkeypatch.setenv("DECISIONGRAPH_ALERT_SLACK_WEBHOOK", "https://hooks.slack.local/test")
    monkeypatch.setattr(SERVICE, "_dispatch_watch_notification", lambda webhook_url, payload: (True, None))
    client = TestClient(app)
    out = client.post("/api/assumptions/watch", json={"notify": True, "notify_target": "slack"})
    assert out.status_code == 200
    assert out.json()["notification"]["target"] == "slack"


def test_api_merge_timeline_quality_and_audit() -> None:
    SERVICE.seed_demo()
    client = TestClient(app)
    run_id = uuid4().hex[:8]

    first = client.post(
        "/api/ingest",
        json={
            "source_id": f"merge-api-1-{run_id}",
            "source_type": "rfc",
            "text": "Title: Introduce dedicated cache cluster\nSummary: isolate noisy workloads\nOwner: Platform\nAssumption: cache_hit_ratio > 0.9\nRisk: migration overhead",
        },
    )
    second = client.post(
        "/api/ingest",
        json={
            "source_id": f"merge-api-2-{run_id}",
            "source_type": "rfc",
            "text": "Title: Introduce dedicated cache cluster for workloads\nSummary: same direction\nOwner: SRE\nAssumption: cache_hit_ratio > 0.9\nRisk: operational complexity",
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200
    first_id = first.json()["decision"]["id"]
    second_id = second.json()["decision"]["id"]

    merged = client.post(
        "/api/decisions/merge",
        json={"primary_decision_id": first_id, "duplicate_decision_id": second_id, "note": "api dedupe"},
    )
    assert merged.status_code == 200
    assert second_id in merged.json()["decision"]["supersedes"]

    timeline = client.get("/api/decisions/timeline", params={"limit": 20, "component": "cache"})
    assert timeline.status_code == 200
    assert "items" in timeline.json()

    quality = client.get("/api/decisions/evidence-quality", params={"limit": 20, "weak_threshold": 0.6})
    assert quality.status_code == 200
    assert "avg_score" in quality.json()

    audit = client.get("/api/audit/logs", params={"limit": 50})
    assert audit.status_code == 200
    assert audit.json()["count"] >= 1


def test_api_governance_strict_blocks_loose_ingest(monkeypatch) -> None:
    monkeypatch.setenv("DECISIONGRAPH_GOVERNANCE_MODE", "strict")
    monkeypatch.setenv("DECISIONGRAPH_GOVERNANCE_REQUIRED_FIELDS", "owners,assumptions,risks")
    client = TestClient(app)
    out = client.post(
        "/api/ingest",
        json={
            "source_id": "governance-api-fail",
            "source_type": "note",
            "text": "Title: Missing governance fields\nSummary: no owner assumption risk lines",
        },
    )
    assert out.status_code == 400
