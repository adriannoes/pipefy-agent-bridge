"""Shared errors for golden evaluation loading."""


class GoldenLoadError(ValueError):
    """Raised when ``golden.yaml`` fails structural or filesystem validation."""
