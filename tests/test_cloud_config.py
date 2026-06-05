"""Offline unit tests for demos/_cloud_config.py."""

from __future__ import annotations

import pytest
from cursor_sdk import CloudAgentOptions, CloudRepository

from demos._cloud_config import (
    assert_no_cursor_prefixed_env_vars,
    build_cloud_options,
    build_env_vars,
    resolve_cloud_repo_url,
    resolve_cloud_starting_ref,
)


def test_build_env_vars_selects_pipefy_and_demo_keys() -> None:
    environ = {
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID": "cid",
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET": "secret",
        "DEMO_ORG_ID": "42",
        "DEMO_PIPE_ID": "99",
        "DEMO_PHASE_NAME": "Done",
        "UNRELATED": "ignored",
    }

    assert build_env_vars(environ) == {
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID": "cid",
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET": "secret",
        "DEMO_ORG_ID": "42",
        "DEMO_PIPE_ID": "99",
        "DEMO_PHASE_NAME": "Done",
    }


def test_build_env_vars_includes_nvidia_when_set() -> None:
    environ = {
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID": "cid",
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET": "secret",
        "NVIDIA_API_KEY": "nv-key",
    }

    assert build_env_vars(environ)["NVIDIA_API_KEY"] == "nv-key"


def test_build_env_vars_omits_empty_or_whitespace_only_values() -> None:
    environ = {
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID": "cid",
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET": "secret",
        "DEMO_ORG_ID": "   ",
        "NVIDIA_API_KEY": "",
    }

    assert build_env_vars(environ) == {
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID": "cid",
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET": "secret",
    }


def test_build_env_vars_ignores_cursor_api_key_in_full_environ() -> None:
    environ = {
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID": "cid",
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET": "secret",
        "CURSOR_API_KEY": "local-only",
    }

    result = build_env_vars(environ)
    assert "CURSOR_API_KEY" not in result
    assert result == {
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID": "cid",
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET": "secret",
    }


def test_build_cloud_options_builds_expected_cloud_agent_options() -> None:
    env_vars = {
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID": "cid",
        "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET": "secret",
    }

    options = build_cloud_options(
        repo_url="https://github.com/org/repo",
        starting_ref="main",
        env_vars=env_vars,
        skip_reviewer_request=True,
    )

    assert isinstance(options, CloudAgentOptions)
    assert options.skip_reviewer_request is True
    assert options.auto_create_pr is False
    assert options.env_vars == env_vars
    assert len(options.repos) == 1
    repo = options.repos[0]
    assert isinstance(repo, CloudRepository)
    assert repo.url == "https://github.com/org/repo"
    assert repo.starting_ref == "main"


def test_build_cloud_options_auto_create_pr() -> None:
    options = build_cloud_options(
        repo_url="https://github.com/org/repo",
        starting_ref="main",
        env_vars={},
        skip_reviewer_request=False,
        auto_create_pr=True,
    )
    assert options.auto_create_pr is True


def test_build_cloud_options_rejects_cursor_prefixed_env_vars() -> None:
    with pytest.raises(ValueError, match=r"CURSOR_"):
        build_cloud_options(
            repo_url="https://github.com/org/repo",
            starting_ref="main",
            env_vars={"CURSOR_API_KEY": "leak"},
            skip_reviewer_request=False,
        )


def test_assert_no_cursor_prefixed_env_vars_rejects_leak() -> None:
    with pytest.raises(ValueError, match=r"CURSOR_"):
        assert_no_cursor_prefixed_env_vars({"CURSOR_FOO": "x"})


def test_resolve_cloud_repo_url_requires_explicit_value() -> None:
    with pytest.raises(ValueError, match="CLOUD_REPO_URL"):
        resolve_cloud_repo_url({})


def test_resolve_cloud_repo_url_returns_trimmed_value() -> None:
    url = resolve_cloud_repo_url({"CLOUD_REPO_URL": "  https://github.com/org/repo  "})
    assert url == "https://github.com/org/repo"


def test_resolve_cloud_starting_ref_defaults_to_main() -> None:
    assert resolve_cloud_starting_ref({}) == "main"


def test_resolve_cloud_starting_ref_honors_override() -> None:
    assert resolve_cloud_starting_ref({"CLOUD_STARTING_REF": "feature/x"}) == "feature/x"
