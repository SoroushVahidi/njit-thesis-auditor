"""Shared exception type for the online-only URL fetch route."""


class FetchError(Exception):
    """User-facing error raised when a URL download fails or is blocked."""
