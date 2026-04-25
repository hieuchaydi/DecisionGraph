from __future__ import annotations

import pytest

from decisiongraph.config import (
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
