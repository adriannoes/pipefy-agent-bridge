"""Shared errors for golden evaluation loading (PRD-2)."""


class GoldenLoadError(ValueError):
    """Raised when ``golden.yaml`` fails structural or filesystem validation."""
