"""Pure helpers for Cursor Cloud agent configuration (offline-testable)."""

from __future__ import annotations

from collections.abc import Mapping

from cursor_sdk import CloudAgentOptions, CloudRepository

from demos._cursor_harness import CLOUD_SESSION_ENV_KEYS

CURSOR_ENV_PREFIX = "CURSOR_"
DEFAULT_CLOUD_STARTING_REF = "main"


def build_env_vars(environ: Mapping[str, str]) -> dict[str, str]:
    """Select session keys from ``environ`` for cloud ``env_vars`` (never ``CURSOR_*``)."""
    env: dict[str, str] = {}
    for key in CLOUD_SESSION_ENV_KEYS:
        value = environ.get(key, "").strip()
        if value:
            env[key] = value
    return env


def build_cloud_options(
    repo_url: str,
    starting_ref: str,
    env_vars: dict[str, str],
    skip_reviewer_request: bool,
    auto_create_pr: bool = False,
) -> CloudAgentOptions:
    """Build ``CloudAgentOptions`` for ``Agent.create(..., cloud=...)``."""
    assert_no_cursor_prefixed_env_vars(env_vars)

    return CloudAgentOptions(
        repos=[CloudRepository(url=repo_url, starting_ref=starting_ref)],
        env_vars=env_vars,
        skip_reviewer_request=skip_reviewer_request,
        auto_create_pr=auto_create_pr,
    )


def assert_no_cursor_prefixed_env_vars(env_vars: Mapping[str, str]) -> None:
    """Reject ``env_vars`` keys prefixed with ``CURSOR_`` (SDK constraint).

    Raises:
        ValueError: When any key in ``env_vars`` starts with ``CURSOR_``.
    """
    cursor_keys = sorted(key for key in env_vars if key.startswith(CURSOR_ENV_PREFIX))
    if not cursor_keys:
        return
    joined = ", ".join(cursor_keys)
    raise ValueError(
        f"cloud env_vars cannot use keys prefixed with {CURSOR_ENV_PREFIX!r}: "
        f"found {joined}; pass the Cursor API key via Agent.create(api_key=...) instead"
    )


def resolve_cloud_repo_url(environ: Mapping[str, str]) -> str:
    """Return ``CLOUD_REPO_URL`` from ``environ`` (required, no maintainer default).

    Raises:
        ValueError: When ``CLOUD_REPO_URL`` is unset or whitespace-only.
    """
    explicit = environ.get("CLOUD_REPO_URL", "").strip()
    if explicit:
        return explicit
    raise ValueError("CLOUD_REPO_URL is required (set in .env or export before make demo-cloud)")


def resolve_cloud_starting_ref(environ: Mapping[str, str]) -> str:
    """Return ``CLOUD_STARTING_REF`` from ``environ``, defaulting to ``main``."""
    value = environ.get("CLOUD_STARTING_REF", DEFAULT_CLOUD_STARTING_REF).strip()
    return value or DEFAULT_CLOUD_STARTING_REF
