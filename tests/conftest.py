"""Shared pytest fixtures and integration-test guards."""

from __future__ import annotations

import os
import shutil

import pytest

_PIPEFY_CREDENTIAL_ENV_VARS: tuple[str, ...] = (
    "PIPEFY_SERVICE_ACCOUNT_CLIENT_ID",
    "PIPEFY_SERVICE_ACCOUNT_CLIENT_SECRET",
)


def _pipefy_credentials_configured() -> bool:
    return all(os.environ.get(name) for name in _PIPEFY_CREDENTIAL_ENV_VARS)


def _pipefy_cli_available() -> bool:
    return shutil.which("pipefy") is not None


@pytest.fixture(autouse=True)
def _skip_integration_without_pipefy_runtime(request: pytest.FixtureRequest) -> None:
    """Skip @pytest.mark.integration tests when live Pipefy prerequisites are missing."""
    marker = request.node.get_closest_marker("integration")
    if marker is None:
        return
    if not _pipefy_credentials_configured():
        pytest.skip(
            f"Pipefy service account credentials not set ({', '.join(_PIPEFY_CREDENTIAL_ENV_VARS)})"
        )
    if not _pipefy_cli_available():
        pytest.skip("pipefy CLI not on PATH — run: make install-pipefy-tools")
