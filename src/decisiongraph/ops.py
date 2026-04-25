from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import Any

from decisiongraph.config import (
    api_token,
    cors_origins,
    environment_name,
    github_base_url,
    github_token,
    groq_api_key,
    groq_models,
    rate_limit_per_minute,
    require_token_in_production,
    resolve_data_path,
)
from decisiongraph.store import DecisionStore


def doctor() -> dict[str, Any]:
    data_path = resolve_data_path()
    checks = []
    checks.append({"name": "python_version", "ok": sys.version_info >= (3, 10), "value": platform.python_version()})
    checks.append({"name": "data_path_exists", "ok": data_path.exists(), "value": str(data_path)})
    checks.append({"name": "env_name", "ok": True, "value": environment_name()})
    checks.append({"name": "package_imports", "ok": True, "value": "decisiongraph"})
    ok = all(item["ok"] for item in checks)
    return {"ok": ok, "checks": checks}


def runbook() -> dict[str, Any]:
    return {
        "daily_dev_loop": [
            "Ingest latest notes/commits/issues",
            "Run top why-queries for active modules",
            "Review stale assumptions and contradictions",
            "Run guardrail before risky changes",
        ],
        "incident_mode": [
            "Ingest incident summary and timeline",
            "Link incident to affected decisions",
            "Record unresolved assumptions and risks",
        ],
        "before_refactor": [
            "Query historical rationale",
            "Run guardrail checks",
            "Escalate reviewer if confidence low",
        ],
    }


def release_check(project_root: Path) -> dict[str, Any]:
    src = project_root / "src" / "decisiongraph"
    tests = project_root / "tests"
    checks = [
        {"name": "src_exists", "ok": src.exists(), "value": str(src)},
        {"name": "tests_exists", "ok": tests.exists(), "value": str(tests)},
        {"name": "data_store_readable", "ok": resolve_data_path().exists(), "value": str(resolve_data_path())},
        {"name": "schema_version", "ok": schema_info()["schema_version"] >= 2, "value": schema_info()["schema_version"]},
    ]
    ok = all(item["ok"] for item in checks)
    return {"ok": ok, "checks": checks}


def security_audit() -> dict[str, Any]:
    token = api_token()
    gh = github_token()
    groq_key = groq_api_key()
    groq_model_list = groq_models()
    cors = cors_origins()
    return {
        "env": environment_name(),
        "api_token_configured": bool(token),
        "require_token_in_production": require_token_in_production(),
        "rate_limit_per_minute": rate_limit_per_minute(),
        "github_token_configured": bool(gh),
        "groq_api_key_configured": bool(groq_key),
        "groq_models": groq_model_list,
        "github_base_url": github_base_url(),
        "cors_origins": cors,
        "api_mode": "protected" if token else "open",
    }


def schema_info() -> dict[str, Any]:
    store = DecisionStore(resolve_data_path())
    payload = store._read()  # local ops introspection
    return {
        "schema_version": int(payload.get("schema_version", 1)),
        "decisions": len(payload.get("decisions", [])),
        "evidence": len(payload.get("evidence", [])),
        "metrics": len(payload.get("metrics", [])),
    }
