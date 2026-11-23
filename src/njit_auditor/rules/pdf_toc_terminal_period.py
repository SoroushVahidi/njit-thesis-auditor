"""Conservative TOC entry terminal-period absence check (P054).

Partial heuristic PDF coverage for Q049/Q050/Q051:
  - Q049: TOC L1 entries (chapter headings) are all-caps with no terminal period.
  - Q050: TOC L2 entries use title case with no terminal period.
  - Q051: TOC L3 entries use sentence case with no terminal period.

Table of Contents pages only. LoT and LoF are excluded (handled by P053 and P040).
Does not duplicate P024 (TOC case/punctuation), P039 (hierarchy), P042 (appendix format),
P053 (LoT no terminal period), or P040 (LoF must have terminal punctuation).

P040 checks that LoF entries DO have terminal punctuation.
P053 checks that LoT entries do NOT have a terminal period.
P054 checks that TOC entries do NOT have a terminal period (symmetric to P053 for TOC pages).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from functools import cache, partial

import fitz

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextSpan, format_bbox_detail
from njit_auditor.rules.pdf_toc_alignment import (
    LEADER_GAP_JITTER_EM,
    LEADER_GRID_MAX_SPREAD_PT,
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
    is_isolated_terminal_grid_leader_dot,
)
from njit_auditor.toc_entry_geometry import Glyph, row_glyphs

MIN_ENTRY_TEXT_LEN = 10

_LEADER_STRIP_RE = re.compile(r"\s*(?:(?:\.\s*){2,}|[-–—_]{2,})$")
_DOT_LEADER_CHARS = ".…·"
_SEPARATED_DOT_LEADER_RE = re.compile(r"\s+[.…·][.…·\s]*$")
_ATTACHED_DOT_LEADER_RE = re.compile(r"[.…·]+$")
_MIXED_DOT_SUFFIX_RE = re.compile(r"(?<=[^\s.…·])\.(?=\s*[.…·][.…·\s]*$)")
_TERMINAL_PERIOD_RE = re.compile(r"\.\s*$")
# Allow measurement noise at the same precision as exported boxes. Peer
# dispersion, rather than the page-wide spread ceiling, defines each column.
_POSITION_EPSILON_PT = 0.1
# Two coherent peers make attachment ambiguous even before there are enough
# rows to confirm a page-wide grid. A warning then needs positive run evidence.
_MIN_PLAUSIBLE_PEER_ROWS = 2

_TraceChar = tuple[int, int, tuple[float, float], tuple[float, float, float, float]]
_SourceRuns = list[tuple[_TraceChar, ...]]


def _dot_leader_weight(text: str) -> int:
    """Return visible dot weight for a candidate dot-leader fragment."""

    return sum(3 if char == "…" else 1 for char in text if char in _DOT_LEADER_CHARS)


def _strip_trailing_leaders(text: str) -> str:
    """Strip visual leaders while preserving isolated title punctuation."""

    stripped = text.rstrip()
    while True:
        legacy_stripped = _LEADER_STRIP_RE.sub("", stripped).strip()
        if legacy_stripped != stripped:
            stripped = legacy_stripped
            continue

        separated = _SEPARATED_DOT_LEADER_RE.search(stripped)
        if separated is not None and _dot_leader_weight(separated.group()) >= 2:
            stripped = stripped[: separated.start()].rstrip()
            continue

        attached = _ATTACHED_DOT_LEADER_RE.search(stripped)
        if attached is not None and _dot_leader_weight(attached.group()) >= 2:
            stripped = stripped[: attached.start()].rstrip()
            continue

        break

    return stripped.strip()


def _without_folio(text: str, folio: str | None) -> str:
    text = text.rstrip()
    if folio and text.endswith(folio):
        return text[:-len(folio)].rstrip()
    return text


def _extract_toc_entry_text(entry: TocEntryLine) -> str | None:
    """Return entry text stripped of page number and leaders."""
    text = _strip_trailing_leaders(_without_folio(entry.cleaned_text, entry.page_number_token))
    return text if len(text) >= MIN_ENTRY_TEXT_LEN else None


def _title_glyph_indices(glyphs: list[Glyph], folio: str | None) -> list[int]:
    visible = [i for i, glyph in enumerate(glyphs) if not glyph.char.isspace()]
    if folio and "".join(glyphs[i].char for i in visible[-len(folio):]) == folio:
        return visible[:-len(folio)]
    return visible


def _detached_dots(page: PdfPage) -> dict[float, list[Glyph]]:
    dots: dict[float, list[Glyph]] = {}
    for block in page.text_blocks:
        for line in block.lines:
            if line.baseline_y is not None and re.fullmatch(r"[.…·\s]+", line.text):
                dots.setdefault(line.baseline_y, []).extend(row_glyphs(line))
    return dots


def _with_detached_followers(
    entry: TocEntryLine, leaders: list[Glyph], baseline: float | None,
    detached: dict[float, list[Glyph]],
) -> list[Glyph]:
    # The shared entry parser can omit standalone later dots. Use them only
    # as corroboration for a mixed row, on the measured leader baseline and
    # strictly between the last reconstructed dot and the folio.
    if not leaders or baseline is None or entry.page_number_line is None:
        return leaders
    last_x = leaders[-1].x1
    if last_x is None:
        return leaders
    folio_glyphs = [g for g in row_glyphs(entry.page_number_line) if not g.char.isspace()]
    folio = entry.page_number_token
    if not folio or "".join(g.char for g in folio_glyphs[-len(folio):]) != folio:
        return leaders
    folio_x = folio_glyphs[-len(folio)].x0
    if folio_x is None:
        return leaders
    return leaders + [
        dot for y, glyphs in detached.items() if abs(y - baseline) <= _POSITION_EPSILON_PT
        for dot in glyphs
        if dot.char in _DOT_LEADER_CHARS and dot.x0 is not None and dot.x1 is not None
        and last_x <= dot.x0 < dot.x1 <= folio_x
    ]


def _peer_leader_glyphs(
    entry: TocEntryLine, detached: dict[float, list[Glyph]]
) -> list[Glyph]:
    row = entry.page_number_line or entry.line
    glyphs = row_glyphs(row)
    visible = _title_glyph_indices(glyphs, entry.page_number_token)
    start = len(visible)
    while start and glyphs[visible[start - 1]].char in _DOT_LEADER_CHARS:
        start -= 1
    if start == 0 or len(visible) - start < 2:
        return []
    preceding = glyphs[visible[start - 1]]
    first = glyphs[visible[start]]
    # Only count the first dot as grid evidence when it is separated from the
    # peer title. A genuine period in a peer title cannot establish the grid.
    if (
        first.x0 is None
        or preceding.x1 is None
        or not first.size
        or first.x0 - preceding.x1 <= LEADER_GAP_JITTER_EM * first.size
    ):
        start += 1
    leaders = [glyphs[i] for i in visible[start:]]
    spans = sorted(row.spans, key=lambda span: span.bbox.x0)
    last = _span_at_glyph(spans, visible[-1])
    baseline = last[0].baseline_y if last is not None else None
    return _with_detached_followers(entry, leaders, baseline, detached)


def _nearest_peer_dot(
    glyphs: list[Glyph], char: str, x: float, *, right_edge: bool = False
) -> float | None:
    positions = (glyph.x1 if right_edge else glyph.x0 for glyph in glyphs if glyph.char == char)
    return min(
        (pos for pos in positions if pos is not None and abs(pos - x) <= LEADER_GRID_MAX_SPREAD_PT),
        key=lambda pos: abs(pos - x),
        default=None,
    )


def _matches_measured_column(x: float, positions: list[float]) -> bool:
    if len(positions) < _MIN_PLAUSIBLE_PEER_ROWS:
        return False
    left, right = min(positions), max(positions)
    return (
        right - left <= LEADER_GRID_MAX_SPREAD_PT
        and left - _POSITION_EPSILON_PT <= x <= right + _POSITION_EPSILON_PT
    )


def _coherent_peer_columns(
    candidate_x: float, leader_x: float, pairs: list[tuple[float, float]]
) -> bool:
    # A nearby row from another layout can disagree with an otherwise coherent
    # grid. Test bounded windows of paired observations, keeping the same
    # contributing rows in both columns.
    if len(pairs) < _MIN_PLAUSIBLE_PEER_ROWS:
        return False
    for left in {x for x, _ in pairs if x <= candidate_x + _POSITION_EPSILON_PT}:
        column = [(x, y) for x, y in pairs if 0 <= x - left <= LEADER_GRID_MAX_SPREAD_PT]
        for start in {y for _, y in column if y <= leader_x + _POSITION_EPSILON_PT}:
            window = [(x, y) for x, y in column if 0 <= y - start <= LEADER_GRID_MAX_SPREAD_PT]
            if (
                _matches_measured_column(candidate_x, [x for x, _ in window])
                and _matches_measured_column(leader_x, [y for _, y in window])
            ):
                return True
    return False


def _has_peer_leader_evidence(
    entry: TocEntryLine, peers: list[TocEntryLine], period: Glyph, leaders: list[Glyph],
    detached: dict[float, list[Glyph]],
) -> bool:
    candidate_x = period.x0 if period.x0 is not None else period.x1
    if candidate_x is None:
        return False
    peer_rows: list[tuple[float, list[Glyph]]] = []
    for peer in peers:
        if peer is entry or peer.page_number_token is None:
            continue
        glyphs = _peer_leader_glyphs(peer, detached)
        first_x = _nearest_peer_dot(
            glyphs, period.char, candidate_x, right_edge=period.x0 is None
        )
        if first_x is not None:
            peer_rows.append((first_x, glyphs))
    if len(peer_rows) < _MIN_PLAUSIBLE_PEER_ROWS:
        return False
    # The immediate dot can be displaced. A later dot can still corroborate
    # the candidate's column, provided the same peers support both positions.
    for leader in leaders:
        if leader.x0 is None:
            continue
        pairs: list[tuple[float, float]] = []
        for first_x, glyphs in peer_rows:
            next_x = _nearest_peer_dot(glyphs, leader.char, leader.x0)
            if next_x is not None and first_x < next_x:
                pairs.append((first_x, next_x))
        if _coherent_peer_columns(candidate_x, leader.x0, pairs):
            return True
    return False


def _visible_source_runs(page: fitz.Page) -> _SourceRuns:
    return [
        run["chars"] for run in page.get_texttrace()
        if run["dir"] == (1.0, 0.0) and run["type"] in (0, 1) and run["opacity"] > 0
    ]


def _read_source_runs(path: str, page_index: int) -> _SourceRuns:
    # Read only when peer geometry conflicts with title attachment. A layout
    # built in memory or a PDF that cannot be reopened has no run evidence.
    try:
        with fitz.open(path) as pdf:
            if not 0 <= page_index < len(pdf):
                return []
            page = pdf[page_index]
            if page.first_widget is not None:
                return []
            if not page.annot_xrefs():
                return _visible_source_runs(page)
            # get_texttrace includes annotation appearances. Isolate the
            # underlying page in memory before using it as authorship evidence.
            with fitz.open() as clean:
                clean.insert_pdf(
                    pdf, from_page=page_index, to_page=page_index, links=False, annots=False
                )
                return _visible_source_runs(clean[0])
    except (OSError, RuntimeError, ValueError, IndexError):
        return []


def _dot_in_source_runs(
    runs: _SourceRuns, dot: Glyph, baseline: float
) -> tuple[int, int] | None:
    use_left = dot.x0 is not None
    edge = dot.x0 if use_left else dot.x1
    if edge is None:
        return None
    found = None
    for run_index, run in enumerate(runs):
        for offset, (codepoint, _, (x, y), box) in enumerate(run):
            if (
                codepoint == ord(dot.char)
                and abs(y - baseline) <= _POSITION_EPSILON_PT
                and abs((x if use_left else box[2]) - edge) <= _POSITION_EPSILON_PT
            ):
                if found is not None:
                    return None
                found = run_index, offset
    return found


def _source_run_ends_with_period(
    runs: _SourceRuns,
    preceding: Glyph,
    period: Glyph,
    leader: Glyph,
    period_baseline: float,
    leader_baseline: float,
) -> bool:
    title_match = _dot_in_source_runs(runs, period, period_baseline)
    leader_match = _dot_in_source_runs(runs, leader, leader_baseline)
    if title_match is None or leader_match is None or title_match[0] == leader_match[0]:
        return False
    run_index, offset = title_match
    run = runs[run_index]
    return (
        offset > 0
        and run[offset - 1][0] == ord(preceding.char)
        and (
            preceding.x1 is None
            or abs(run[offset - 1][3][2] - preceding.x1) <= _POSITION_EPSILON_PT
        )
        and all(0 <= char[0] <= 0x10FFFF and chr(char[0]).isspace() for char in run[offset + 1:])
    )


def _span_at_glyph(spans: list[PdfTextSpan], offset: int) -> tuple[PdfTextSpan, int] | None:
    for span in spans:
        if offset < len(span.text):
            return span, offset
        offset -= len(span.text)
    return None


def _mixed_dot_period_bbox(
    entry: TocEntryLine,
    peers: list[TocEntryLine],
    title: str,
    match: re.Match[str],
    source_runs: Callable[[], _SourceRuns] | None,
    detached: dict[float, list[Glyph]],
) -> tuple[BBox, float] | None:
    """Locate the attached period and the first leader on the final title row."""
    if match.end() < MIN_ENTRY_TEXT_LEN:
        return None

    # The folio row normally holds the last visual title line. An auxiliary
    # folio fragment can hold only dots and a number, so use the title line
    # in that case.
    row = entry.page_number_line
    folio = entry.page_number_token
    if row is None or not any(c.isalpha() for c in _without_folio(row.text, folio)):
        row = entry.line
    glyphs = row_glyphs(row)
    visible = _title_glyph_indices(glyphs, folio)
    suffix = "".join(title[match.start() - 1:].split())
    tail = visible[-len(suffix):]
    if "".join(glyphs[i].char for i in tail) != suffix:
        return None

    preceding, period, leader = (glyphs[i] for i in tail[:3])
    if period.x1 is None or leader.x0 is None or not period.size:
        return None
    jitter = LEADER_GAP_JITTER_EM * period.size
    if leader.x0 - period.x1 <= jitter:
        return None

    spans = sorted(row.spans, key=lambda span: span.bbox.x0)
    period_location = _span_at_glyph(spans, tail[1])
    if period_location is None:
        return None
    span, offset = period_location
    if preceding.x1 is not None and period.x0 is not None:
        if abs(period.x0 - preceding.x1) > jitter:
            return None
    elif offset == 0 or span.text[offset - 1] != preceding.char:
        return None
    leader_location = _span_at_glyph(spans, tail[2])
    leader_baseline = leader_location[0].baseline_y if leader_location is not None else None
    last_location = _span_at_glyph(spans, tail[-1])
    last_baseline = last_location[0].baseline_y if last_location is not None else None
    leaders = _with_detached_followers(
        entry, [glyphs[i] for i in tail[2:]], last_baseline, detached
    )
    if _has_peer_leader_evidence(entry, peers, period, leaders, detached):
        # Only a matched title run ending in the period resolves conflicting
        # grid evidence. The first leader has its own baseline even when the
        # layout parser groups both spans into the same visual row.
        if source_runs is None or span.baseline_y is None or leader_baseline is None:
            return None
        if not _source_run_ends_with_period(
            source_runs(), preceding, period, leader, span.baseline_y, leader_baseline
        ):
            return None
    # A span ending at an unmeasured period still gives a title-only box.
    bbox = BBox(
        x0=period.x0 if period.x0 is not None else span.bbox.x0,
        y0=span.bbox.y0,
        x1=period.x1,
        y1=span.bbox.y1,
    )
    return bbox, leader.x0


def _single_spaced_dot_is_ambiguous(entry_text: str) -> bool:
    """Avoid treating an isolated, space-separated leader as title punctuation.

    A lone dot can be the last cell of a leader grid. Without a repeated dot
    pattern or a page-wide aligned grid, extracted whitespace alone cannot
    establish whether the dot belongs to the title.
    """
    return re.search(r"\s+\.$", entry_text) is not None


def _check_toc_terminal_period_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
    page_entry_offset: int,
    source_runs: Callable[[], _SourceRuns] | None = None,
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    detached = _detached_dots(context.page)
    for idx, entry in enumerate(entries):
        if entry.page_number_token is None:
            continue
        bbox = entry.line.bbox
        leader_start = None
        title = _without_folio(entry.cleaned_text, entry.page_number_token)
        match = _MIXED_DOT_SUFFIX_RE.search(title)
        if match is not None:
            period = _mixed_dot_period_bbox(entry, entries, title, match, source_runs, detached)
            if period is None:
                continue
            bbox, leader_start = period
        else:
            entry_text = _extract_toc_entry_text(entry)
            if entry_text is None or not _TERMINAL_PERIOD_RE.search(entry_text):
                continue
            if is_isolated_terminal_grid_leader_dot(entry, entries):
                continue
            if _single_spaced_dot_is_ambiguous(entry_text):
                continue
        details = {
            "issue_type": "toc_entry_has_terminal_period",
            "page": str(context.page.page_number),
            "section_type": "table_of_contents",
            "entry_index": str(page_entry_offset + idx),
            "terminal_punctuation": ".",
            "page_number_token_present": "true",
            "bbox": format_bbox_detail(bbox),
            "triage_tier": "medium",
            "source_q_rule_id": "Q050",
        }
        if leader_start is not None:
            details["highlight_right_limit"] = str(leader_start)
        findings.append(
            AuditFinding(
                rule_id="P054",
                severity=Severity.WARNING,
                page=context.page.page_number,
                message=(
                    "Table of Contents entry ends with a terminal period. "
                    "NJIT guidelines require that TOC entries "
                    "at all levels do not end with a terminal period."
                ),
                details=details,
            )
        )
    return findings


def check_pdf_toc_terminal_period(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P054 warnings for TOC entries with a terminal period."""
    findings: list[AuditFinding] = []
    entry_offset = 0
    for context in detect_toc_like_pages(pdf_document):
        if context.page_type != "table_of_contents":
            continue
        entries = extract_toc_entry_lines(context)
        if len(entries) < 2:
            continue
        page_index = context.page.original_page_index
        if page_index is None:
            page_index = context.page.page_number - 1
        source_runs = cache(partial(_read_source_runs, pdf_document.path, page_index))
        page_findings = _check_toc_terminal_period_page(context, entries, entry_offset, source_runs)
        findings.extend(page_findings)
        entry_offset += len(entries)
    return findings
