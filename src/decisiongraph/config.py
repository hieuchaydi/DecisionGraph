from __future__ import annotations

import os
from pathlib import Path


DEFAULT_DATA_PATH = Path("data/decisiongraph.json")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    return value in {"1", "true", "yes", "on"}


def resolve_data_path() -> Path:
    raw = os.getenv("DECISIONGRAPH_DATA_PATH", str(DEFAULT_DATA_PATH))
    path = Path(raw).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def api_token() -> str | None:
    token = os.getenv("DECISIONGRAPH_API_TOKEN", "").strip()
    return token or None


def cors_origins() -> list[str]:
    raw = os.getenv("DECISIONGRAPH_CORS_ORIGINS", "").strip()
    if not raw:
        return []
    parts = [part.strip() for part in raw.split(",")]
    return [part for part in parts if part]


def environment_name() -> str:
    return os.getenv("DECISIONGRAPH_ENV", "development").strip() or "development"


def github_token() -> str | None:
    token = os.getenv("DECISIONGRAPH_GITHUB_TOKEN", "").strip()
    return token or None


def github_base_url() -> str:
    # Backward-compatible fallback for older local env naming.
    base = os.getenv("DECISIONGRAPH_GITHUB_BASE_URL", os.getenv("SE_URL", "https://api.github.com")).strip()
    return base or "https://api.github.com"


def groq_api_key() -> str | None:
    token = os.getenv("GROQ_API_KEY", "").strip()
    return token or None


def groq_models() -> list[str]:
    raw = os.getenv("GROQ_MODELS", "").strip()
    if not raw:
        return []
    parts = [part.strip() for part in raw.split(",")]
    return [part for part in parts if part]


def require_token_in_production() -> bool:
    return _env_bool("DECISIONGRAPH_REQUIRE_TOKEN_IN_PRODUCTION", True)


def validate_runtime_configuration() -> None:
    env = environment_name().lower()
    if env == "production" and require_token_in_production() and not api_token():
        raise RuntimeError(
            "DECISIONGRAPH_API_TOKEN is required in production "
            "(set DECISIONGRAPH_REQUIRE_TOKEN_IN_PRODUCTION=false to override)."
        )


def rate_limit_per_minute() -> int:
    raw = os.getenv("DECISIONGRAPH_RATE_LIMIT_PER_MINUTE", "240").strip()
    if not raw:
        return 240
    try:
        value = int(raw)
    except ValueError:
        return 240
    return max(0, value)
