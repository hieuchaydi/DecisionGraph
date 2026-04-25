from __future__ import annotations

from pathlib import Path

from decisiongraph.ops import doctor, release_check, runbook, schema_info, security_audit


def test_ops_doctor_and_security() -> None:
    d = doctor()
    assert "checks" in d
    s = security_audit()
    assert "api_mode" in s
    assert "governance_mode" in s
    assert "alert_webhooks" in s


def test_ops_runbook_and_release_check(tmp_path: Path) -> None:
    (tmp_path / "src" / "decisiongraph").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    out = runbook()
    assert "daily_dev_loop" in out
    rel = release_check(project_root=tmp_path)
    assert "checks" in rel


def test_schema_info() -> None:
    out = schema_info()
    assert "schema_version" in out
    assert "audit_logs" in out
