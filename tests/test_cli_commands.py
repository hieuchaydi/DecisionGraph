from __future__ import annotations

import re
from pathlib import Path

from typer.testing import CliRunner

from decisiongraph.cli import app


def _runner() -> CliRunner:
    return CliRunner()


def _extract_decision_id(output: str) -> str:
    match = re.search(r"Ingested decision:\s+([a-zA-Z0-9_]+)\s+\|", output)
    assert match is not None
    return match.group(1)


def _prepare_data(runner: CliRunner, data_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DECISIONGRAPH_DATA_PATH", str(data_path))
    init = runner.invoke(app, ["init", "--reset"])
    assert init.exit_code == 0
    seed = runner.invoke(app, ["seed-demo"])
    assert seed.exit_code == 0


def test_cli_merge_timeline_quality_and_audit(tmp_path: Path, monkeypatch) -> None:
    runner = _runner()
    data_path = tmp_path / "dg.json"
    _prepare_data(runner, data_path, monkeypatch)

    first = runner.invoke(
        app,
        [
            "ingest-text",
            "--source-id",
            "cli-merge-1",
            "--source-type",
            "rfc",
            "--text",
            "Title: Dedup cache strategy\nSummary: first variant\nOwner: Platform\nAssumption: cache_hit_ratio > 0.9\nRisk: migration overhead",
        ],
    )
    assert first.exit_code == 0
    first_id = _extract_decision_id(first.stdout)

    second = runner.invoke(
        app,
        [
            "ingest-text",
            "--source-id",
            "cli-merge-2",
            "--source-type",
            "rfc",
            "--text",
            "Title: Dedup cache strategy second\nSummary: second variant\nOwner: SRE\nAssumption: cache_hit_ratio > 0.9\nRisk: ops complexity",
        ],
    )
    assert second.exit_code == 0
    second_id = _extract_decision_id(second.stdout)

    merged = runner.invoke(app, ["merge", first_id, second_id, "--note", "cli dedupe"])
    assert merged.exit_code == 0
    assert '"status": "ok"' in merged.stdout

    timeline = runner.invoke(app, ["timeline", "--limit", "20", "--component", "cache"])
    assert timeline.exit_code == 0
    assert '"items"' in timeline.stdout

    quality = runner.invoke(app, ["evidence-quality", "--limit", "20", "--weak-threshold", "0.6"])
    assert quality.exit_code == 0
    assert '"avg_score"' in quality.stdout

    audit = runner.invoke(app, ["audit-log", "--limit", "20"])
    assert audit.exit_code == 0
    assert '"event"' in audit.stdout

    # alias commands should remain functional
    find = runner.invoke(app, ["find", "cache", "--limit", "20"])
    assert find.exit_code == 0

    quality_alias = runner.invoke(app, ["quality", "--limit", "20", "--weak-threshold", "0.6"])
    assert quality_alias.exit_code == 0
    assert '"avg_score"' in quality_alias.stdout

    audit_alias = runner.invoke(app, ["audit", "--limit", "20"])
    assert audit_alias.exit_code == 0
    assert '"event"' in audit_alias.stdout

    watch_alias = runner.invoke(app, ["watch"])
    assert watch_alias.exit_code == 0
    assert '"stale_count"' in watch_alias.stdout


def test_cli_watch_assumptions_invalid_notify_target(tmp_path: Path, monkeypatch) -> None:
    runner = _runner()
    _prepare_data(runner, tmp_path / "dg.json", monkeypatch)

    out = runner.invoke(
        app,
        ["watch-assumptions", "--notify-target", "pagerduty"],
    )
    assert out.exit_code == 1
    assert "Invalid notify_target" in out.stdout


def test_cli_ingest_fails_in_governance_strict_mode(tmp_path: Path, monkeypatch) -> None:
    runner = _runner()
    monkeypatch.setenv("DECISIONGRAPH_DATA_PATH", str(tmp_path / "dg.json"))
    monkeypatch.setenv("DECISIONGRAPH_GOVERNANCE_MODE", "strict")
    monkeypatch.setenv("DECISIONGRAPH_GOVERNANCE_REQUIRED_FIELDS", "owners,assumptions,risks")

    out = runner.invoke(
        app,
        [
            "ingest-text",
            "--source-id",
            "gov-cli-fail",
            "--source-type",
            "note",
            "--text",
            "Title: Missing policy fields\nSummary: note without owner assumption risk",
        ],
    )
    assert out.exit_code == 1
    assert "Governance validation failed" in out.stdout
