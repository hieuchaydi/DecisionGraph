from __future__ import annotations

import pytest

from decisiongraph.config import (
    alert_webhook_for_target,
    audit_log_retention_limit,
    governance_mode,
    governance_required_fields,
    github_base_url,
    rate_limit_per_minute,
    validate_runtime_configuration,
)


def test_github_base_url_fallback_to_legacy_env(monkeypatch) -> None:
    monkeypatch.delenv("DECISIONGRAPH_GITHUB_BASE_URL", raising=False)
    monkeypatch.setenv("SE_URL", "https://ghe.internal/api/v3")
    assert github_base_url() == "https://ghe.internal/api/v3"


def test_validate_runtime_configuration_requires_token_in_production(monkeypatch) -> None:
    monkeypatch.setenv("DECISIONGRAPH_ENV", "production")
    monkeypatch.delenv("DECISIONGRAPH_API_TOKEN", raising=False)
    monkeypatch.setenv("DECISIONGRAPH_REQUIRE_TOKEN_IN_PRODUCTION", "true")
    with pytest.raises(RuntimeError):
        validate_runtime_configuration()


def test_rate_limit_per_minute_uses_default_on_invalid_value(monkeypatch) -> None:
    monkeypatch.setenv("DECISIONGRAPH_RATE_LIMIT_PER_MINUTE", "abc")
    assert rate_limit_per_minute() == 240


def test_governance_mode_and_required_fields(monkeypatch) -> None:
    monkeypatch.setenv("DECISIONGRAPH_GOVERNANCE_MODE", "strict")
    monkeypatch.setenv("DECISIONGRAPH_GOVERNANCE_REQUIRED_FIELDS", "owners, assumptions ,risks")
    assert governance_mode() == "strict"
    assert governance_required_fields() == ["owners", "assumptions", "risks"]


def test_alert_webhook_target_lookup(monkeypatch) -> None:
    monkeypatch.setenv("DECISIONGRAPH_ALERT_SLACK_WEBHOOK", "https://hooks.slack.local/demo")
    assert alert_webhook_for_target("slack") == "https://hooks.slack.local/demo"


def test_audit_log_retention_limit(monkeypatch) -> None:
    monkeypatch.setenv("DECISIONGRAPH_AUDIT_LOG_RETENTION", "321")
    assert audit_log_retention_limit() == 321
    monkeypatch.setenv("DECISIONGRAPH_AUDIT_LOG_RETENTION", "invalid")
    assert audit_log_retention_limit() == 5000
