"""Lightweight LaTeX source loader for recursive input/include trees."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

INCLUDE_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")


@dataclass(frozen=True)
class TeXSourceFile:
    """A loaded TeX source file."""

    path: Path
    text: str
    lines: list[str]


@dataclass(frozen=True)
class LoadedTexProject:
    """A loaded TeX project rooted at one main file."""

    main_path: Path
    files: list[TeXSourceFile]
    combined_text: str


def _strip_comment(line: str) -> str:
    escaped = "__PERCENT__"
    return line.replace(r"\%", escaped).split("%", 1)[0].replace(escaped, r"\%")


def _resolve_tex_path(parent: Path, raw_ref: str) -> Path:
    ref = raw_ref.strip()
    candidate = (parent / ref).resolve()
    if candidate.suffix:
        return candidate
    return candidate.with_suffix(".tex")


def load_tex_project(main_tex_path: str | Path) -> LoadedTexProject:
    """Load main TeX plus recursively referenced input/include files."""

    main_path = Path(main_tex_path).resolve()
    if not main_path.exists():
        msg = f"TeX file not found: {main_path}"
        raise FileNotFoundError(msg)

    loaded: list[TeXSourceFile] = []
    visited: set[Path] = set()

    def _load(path: Path) -> None:
        if path in visited or not path.exists():
            return
        visited.add(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        loaded.append(TeXSourceFile(path=path, text=text, lines=lines))

        for line in lines:
            clean_line = _strip_comment(line)
            for match in INCLUDE_RE.finditer(clean_line):
                child_path = _resolve_tex_path(path.parent, match.group(1))
                _load(child_path)

    _load(main_path)
    combined_text = "\n".join(file.text for file in loaded)
    return LoadedTexProject(main_path=main_path, files=loaded, combined_text=combined_text)
