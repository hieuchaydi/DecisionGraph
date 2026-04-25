from __future__ import annotations

from pathlib import Path

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
