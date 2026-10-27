"""JSON-only worker state transport preserving tuple geometry and integer keys."""

from __future__ import annotations

from typing import Any

from njit_auditor.pdf_highlight import HighlightBox, PageBoxSpace


def encode(value: Any) -> Any:
    if isinstance(value, PageBoxSpace):
        return {"kind": "page", "items": [value[0], value[1], value.rotation]}
    if isinstance(value, HighlightBox):
        return {"kind": "box", "items": [*value, value.kind]}
    if isinstance(value, tuple):
        return {"kind": "tuple", "items": [encode(item) for item in value]}
    if isinstance(value, dict):
        return {"kind": "map", "items": [[encode(k), encode(v)] for k, v in value.items()]}
    if isinstance(value, list):
        return [encode(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("Unsupported desktop state value")


def decode(value: Any) -> Any:
    if isinstance(value, list):
        return [decode(item) for item in value]
    if not isinstance(value, dict):
        return value
    kind, items = value["kind"], value["items"]
    if kind == "page":
        return PageBoxSpace(items[0], items[1], items[2])
    if kind == "box":
        return HighlightBox(items[0], items[1], items[2], items[3], kind=items[4])
    if kind == "tuple":
        return tuple(decode(item) for item in items)
    if kind == "map":
        return {decode(key): decode(item) for key, item in items}
    raise ValueError("Unsupported desktop state kind")
