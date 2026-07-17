"""Static (no-import, no-execution) ground-truth extraction for detector rules.

Scans `src/njit_auditor/rules/*.py` source text with `ast` to recover which
`(rule_id, issue_type)` pairs a detector actually constructs via
`AuditFinding(...)`, without importing or running any detector.

Why this exists: `data/processed/rules/project_added_rules.json`'s
`issue_types` field is the usual ground truth for "what does this rule emit",
but it is only populated for a minority of catalog rows (see
docs/RULE_ARCHITECTURE.md). A rule whose catalog entry has no `issue_types`
was previously invisible to the wording-coverage ratchet in
`tests/test_rule_registry_consistency.py` — which is exactly how P014 shipped
a real wording bug ("...issue issue...") undetected.

## What this module resolves (a bounded, static, string-literal-provenance
## analysis — not a general data-flow engine, not detector execution)

Within a single module (never across modules — every rule lives in exactly
one `rules/*.py` file, and cross-module tracing was never needed for any
pattern found in this codebase), it tracks the possible string-literal
value(s) of any expression through:

- a direct string literal, or a ternary (`A if cond else B`) of literals;
- a module-level dict literal, looked up by subscript or `.get()`, either as
  a whole value or unpacked from a tuple value at a fixed position;
- the same lookup pattern reached through one intermediate local variable
  (`config = _MAP.get(key); issue_type, q_id = config`);
- `for key, (a, b) in MODULE_DICT.items(): ...` — a nested tuple-unpack
  directly in a for-loop target over a module-level dict-of-tuples;
- `for a, b in [(lit1, x1), (lit2, x2), ...]: ...` — a tuple-unpack over an
  inline list/tuple-of-tuples literal (no module dict involved);
- an f-string built entirely from literal text and slots that each resolve
  to a finite literal set (e.g. `f"level{level}_sentence_case_issue"` where
  `level` came from the for-loop pattern above) — resolved as the Cartesian
  product of each part's possible values;
- passing any of the above as a positional or keyword argument to another
  function defined in the same module, whose body uses that parameter in
  one of the positions above (a same-module, whole-module fixed-point over
  monotonically-growing literal sets — bounded iteration count, guaranteed
  to terminate since each iteration only ever adds to finite sets);
- a `details=` argument that is a dict literal built directly, assigned to a
  local variable first, wrapped by a helper call that takes a dict literal
  as one of its own arguments, or returned by a same-module helper function
  that builds and returns the dict literal internally.

This is deliberately conservative: whatever pattern this module cannot
resolve, it simply omits from its output — the *catalog* `issue_types` field
remains the fallback ground truth for those cases, exactly as before this
module existed. This scanner can only ever *add* coverage the catalog
missed, never remove or contradict it.

## What this module does NOT resolve (by design, not lack of effort)

- Anything requiring cross-module tracing (not needed by any rule today).
- Truly dynamic issue types (e.g. built from runtime-extracted PDF content) —
  none exist in this codebase; every issue_type is always drawn from a
  closed, developer-authored set of literals.
- The TeX/"source" pipeline (P001–P010): those detectors never set
  `issue_type` in their own `details` at all — it is synthesized downstream,
  by `rule_id` alone, in `report_outputs.derive_source_issue_type()`. See
  `source_pipeline_issue_type_pairs()` below, a second, independent static
  extractor for that one function's literal `if rule_id == ...: return "..."`
  dispatch chain.
- P021's `abstract_word_count_exceeded`: synthesized in
  `polished_comments.build_polished_comment()` itself, based on the
  *presence* of certain detail keys, not a literal the detector ever
  constructs. This is a single, narrow, explicitly-documented exception
  (`KNOWN_NON_DETECTOR_ISSUE_TYPES` below) — not general machinery, because
  there is exactly one such case in the whole codebase and inventing a
  generic mechanism for one occurrence would be more risk than value.

Used by:
- tests/test_rule_registry_consistency.py (the wording-coverage ratchet)
- scripts/atomic_presentation_inventory.py (the diagnostic inventory report)
"""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = _REPO_ROOT / "src/njit_auditor/rules"
REPORT_OUTPUTS_PATH = _REPO_ROOT / "src/njit_auditor/report_outputs.py"

# Legacy modules that predate the P0xx rule numbering, kept only for the
# deprecated `[Legacy] njit-audit audit` CLI command and never invoked by
# audit_runner.py — see docs/RULE_ARCHITECTURE.md. Not part of the active
# default-enabled rule set.
_DEAD_LEGACY_FILES = frozenset({"abstract.py", "page_numbers.py", "title_page.py"})

_MAX_FIXED_POINT_ITERATIONS = 5

# A single, explicitly-documented exception: P021's issue_type is synthesized
# in the wording layer (see module docstring), not declared by its detector.
KNOWN_NON_DETECTOR_ISSUE_TYPES: frozenset[tuple[str, str]] = frozenset(
    {("P021", "abstract_word_count_exceeded")}
)


def _resolve_literal_set(node: ast.AST) -> set[str]:
    """String-only literal resolution: a bare string constant, or a ternary
    of such constants. Used everywhere a value must literally BE the
    issue_type string (never int/float — those are never valid issue types)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if isinstance(node, ast.IfExp):
        return _resolve_literal_set(node.body) | _resolve_literal_set(node.orelse)
    return set()


def _resolve_scalar_literal_repr(node: ast.AST) -> set[str]:
    """Like `_resolve_literal_set` but also stringifies int/float constants —
    used only to fill an f-string slot, where Python would stringify a
    non-str value anyway (e.g. `f"level{2}"` -> `"level2"`)."""
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (str, int, float))
        and not isinstance(node.value, bool)
    ):
        return {str(node.value)}
    if isinstance(node, ast.IfExp):
        return _resolve_scalar_literal_repr(node.body) | _resolve_scalar_literal_repr(node.orelse)
    return set()


def _dict_lookup_source_name(node: ast.AST) -> str | None:
    """If node is `MODULE_DICT[key]` or `MODULE_DICT.get(key)`, return 'MODULE_DICT'."""
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        return node.value.id
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and isinstance(node.func.value, ast.Name)
    ):
        return node.func.value.id
    return None


class _ModuleResolver:
    """Bounded, same-module, fixed-point string-literal-provenance resolver.

    See the module docstring for exactly which patterns this supports. The
    fixed point is over `self.locals: dict[(func_name, var_name), set[str]]`
    — a monotonically growing map, so iterating a small, fixed number of
    times is sufficient and always terminates (no cycles are possible in a
    "sets only ever grow" fixed point over a finite universe of literals).
    """

    def __init__(self, tree: ast.Module):
        self.module_dicts: dict[str, ast.Dict] = {}
        self.module_constants: dict[str, set[str]] = defaultdict(set)
        self.func_defs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.module_dicts[target.id] = node.value
            if isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Dict):
                if isinstance(node.target, ast.Name):
                    self.module_dicts[node.target.id] = node.value
            if isinstance(node, ast.Assign):
                lits = _resolve_literal_set(node.value)
                if lits:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.module_constants[target.id] |= lits
            if isinstance(node, ast.AnnAssign) and node.value is not None:
                lits = _resolve_literal_set(node.value)
                if lits and isinstance(node.target, ast.Name):
                    self.module_constants[node.target.id] |= lits
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.func_defs[node.name] = node

        self.locals: dict[tuple[str, str], set[str]] = defaultdict(set)
        self._dict_lookup_source: dict[tuple[str, str], ast.Dict] = {}
        self._run_fixed_point()

    # -- dict-value helpers ------------------------------------------------

    def _resolve_module_dict_values(
        self, dict_node: ast.Dict, tuple_index: int | None = None
    ) -> set[str]:
        out: set[str] = set()
        for value in dict_node.values:
            if tuple_index is not None and isinstance(value, (ast.Tuple, ast.List)):
                if tuple_index < len(value.elts):
                    out |= _resolve_literal_set(value.elts[tuple_index])
            elif tuple_index is None:
                out |= _resolve_literal_set(value)
        return out

    # -- scalar resolution (the core primitive) -----------------------------

    def _resolve_scalar(self, node: ast.AST, func_name: str) -> set[str]:
        lits = _resolve_literal_set(node)
        if lits:
            return lits
        if isinstance(node, ast.Name):
            return (
                self.locals.get((func_name, node.id), set())
                | self.module_constants.get(node.id, set())
            )
        dict_name = _dict_lookup_source_name(node)
        if dict_name and dict_name in self.module_dicts:
            return self._resolve_module_dict_values(self.module_dicts[dict_name])
        if isinstance(node, ast.JoinedStr):
            return self._resolve_fstring(node, func_name)
        return set()

    def _resolve_fstring(self, node: ast.JoinedStr, func_name: str) -> set[str]:
        """Cartesian product over each f-string part's resolvable value set.
        Any part that fails to resolve makes the whole f-string unresolved
        (empty set) — this only ever adds coverage for f-strings built
        entirely from known finite pieces, never guesses a partial string."""
        part_options: list[set[str]] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                part_options.append({value.value})
                continue
            if isinstance(value, ast.FormattedValue):
                slot_values = _resolve_scalar_literal_repr(value.value)
                if not slot_values and isinstance(value.value, ast.Name):
                    slot_values = self.locals.get(
                        (func_name, value.value.id), set()
                    ) | self.module_constants.get(value.value.id, set())
                if not slot_values:
                    return set()
                part_options.append(slot_values)
                continue
            return set()
        results = {""}
        for options in part_options:
            results = {prefix + suffix for prefix in results for suffix in options}
        return results

    # -- fixed point ---------------------------------------------------------

    def _add(self, key: tuple[str, str], values: set[str]) -> bool:
        if not values:
            return False
        before = len(self.locals[key])
        self.locals[key] |= values
        return len(self.locals[key]) != before

    def _run_fixed_point(self) -> None:
        for _ in range(_MAX_FIXED_POINT_ITERATIONS):
            changed = False
            for func_name, func in self.func_defs.items():
                changed |= self._pass_local_assigns(func_name, func)
            for func_name, func in self.func_defs.items():
                changed |= self._pass_for_loops(func_name, func)
            for func_name, func in self.func_defs.items():
                changed |= self._pass_call_sites(func_name, func)
            if not changed:
                break

    def _iter_assigns(
        self, func: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[tuple[list[ast.expr], ast.expr]]:
        assigns: list[tuple[list[ast.expr], ast.expr]] = []
        for node in ast.walk(func):
            if isinstance(node, ast.Assign):
                assigns.append((node.targets, node.value))
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                assigns.append(([node.target], node.value))
        return assigns

    def _pass_local_assigns(
        self, func_name: str, func: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> bool:
        changed = False
        assigns = self._iter_assigns(func)

        for targets, value in assigns:
            if len(targets) == 1 and isinstance(targets[0], ast.Name):
                name = targets[0].id
                changed |= self._add((func_name, name), self._resolve_scalar(value, func_name))
                dict_name = _dict_lookup_source_name(value)
                if dict_name and dict_name in self.module_dicts:
                    self._dict_lookup_source[(func_name, name)] = self.module_dicts[dict_name]

        for targets, value in assigns:
            if len(targets) != 1 or not isinstance(targets[0], (ast.Tuple, ast.List)):
                continue
            mod_dict = None
            dict_name = _dict_lookup_source_name(value)
            if dict_name and dict_name in self.module_dicts:
                mod_dict = self.module_dicts[dict_name]
            elif isinstance(value, ast.Name):
                mod_dict = self._dict_lookup_source.get((func_name, value.id))
            if mod_dict is None:
                continue
            for idx, elt in enumerate(targets[0].elts):
                if isinstance(elt, ast.Name):
                    changed |= self._add(
                        (func_name, elt.id),
                        self._resolve_module_dict_values(mod_dict, tuple_index=idx),
                    )
        return changed

    def _pass_for_loops(self, func_name: str, func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        changed = False
        for node in ast.walk(func):
            if not isinstance(node, ast.For):
                continue
            it = node.iter
            mod_dict = None
            inline_tuples: list[ast.expr] | None = None
            if (
                isinstance(it, ast.Call)
                and isinstance(it.func, ast.Attribute)
                and it.func.attr == "items"
                and isinstance(it.func.value, ast.Name)
                and it.func.value.id in self.module_dicts
            ):
                mod_dict = self.module_dicts[it.func.value.id]
            elif isinstance(it, (ast.List, ast.Tuple)):
                inline_tuples = it.elts

            target = node.target
            if mod_dict is not None:
                if not (isinstance(target, ast.Tuple) and len(target.elts) == 2):
                    continue
                _key_target, value_target = target.elts
                if isinstance(value_target, ast.Name):
                    changed |= self._add(
                        (func_name, value_target.id), self._resolve_module_dict_values(mod_dict)
                    )
                elif isinstance(value_target, (ast.Tuple, ast.List)):
                    for idx, elt in enumerate(value_target.elts):
                        if isinstance(elt, ast.Name):
                            changed |= self._add(
                                (func_name, elt.id),
                                self._resolve_module_dict_values(mod_dict, tuple_index=idx),
                            )
            elif inline_tuples is not None:
                if isinstance(target, ast.Name):
                    # for x in (lit1, lit2, ...): — single-name target over a
                    # plain literal collection (no unpacking involved).
                    values = set()
                    for entry in inline_tuples:
                        values |= _resolve_scalar_literal_repr(entry)
                    changed |= self._add((func_name, target.id), values)
                    continue
                if not isinstance(target, (ast.Tuple, ast.List)):
                    continue
                for idx, elt in enumerate(target.elts):
                    if not isinstance(elt, ast.Name):
                        continue
                    values = set()
                    for entry in inline_tuples:
                        if isinstance(entry, (ast.Tuple, ast.List)) and idx < len(entry.elts):
                            values |= _resolve_scalar_literal_repr(entry.elts[idx])
                    changed |= self._add((func_name, elt.id), values)
        return changed

    def _pass_call_sites(
        self, caller_name: str, caller_func: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> bool:
        changed = False
        for node in ast.walk(caller_func):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            callee_name = node.func.id
            if callee_name not in self.func_defs:
                continue
            target = self.func_defs[callee_name]
            arg_names = [a.arg for a in target.args.args] + [a.arg for a in target.args.kwonlyargs]
            for i, arg_val in enumerate(node.args):
                if i < len(arg_names):
                    changed |= self._add(
                        (callee_name, arg_names[i]), self._resolve_scalar(arg_val, caller_name)
                    )
            for kw in node.keywords:
                if kw.arg is not None:
                    changed |= self._add(
                        (callee_name, kw.arg), self._resolve_scalar(kw.value, caller_name)
                    )
        return changed

    # -- details=/rule_id= resolution ----------------------------------------

    def _find_issue_type_in_dict_literal(
        self, dict_node: ast.Dict, func_name: str
    ) -> set[str]:
        out: set[str] = set()
        for key, value in zip(dict_node.keys, dict_node.values):
            if isinstance(key, ast.Constant) and key.value == "issue_type":
                out |= self._resolve_scalar(value, func_name)
        return out

    def _find_dict_literal_in_local_var(
        self, var_name: str, func: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> ast.Dict | None:
        for node in ast.walk(func):
            if isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Dict):
                if isinstance(node.target, ast.Name) and node.target.id == var_name:
                    return node.value
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == var_name:
                        return node.value
        return None

    def _find_returned_dict_literal(
        self, func: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> ast.Dict | None:
        for node in ast.walk(func):
            if not isinstance(node, ast.Return) or node.value is None:
                continue
            if isinstance(node.value, ast.Dict):
                return node.value
            if isinstance(node.value, ast.Name):
                dict_lit = self._find_dict_literal_in_local_var(node.value.id, func)
                if dict_lit is not None:
                    return dict_lit
        return None

    def _resolve_details_arg(
        self, details_node: ast.AST, func: ast.FunctionDef | ast.AsyncFunctionDef, func_name: str
    ) -> set[str]:
        if isinstance(details_node, ast.Dict):
            return self._find_issue_type_in_dict_literal(details_node, func_name)
        if isinstance(details_node, ast.Name):
            dict_lit = self._find_dict_literal_in_local_var(details_node.id, func)
            if dict_lit is not None:
                return self._find_issue_type_in_dict_literal(dict_lit, func_name)
            return set()
        if isinstance(details_node, ast.Call):
            out: set[str] = set()
            for arg in list(details_node.args) + [kw.value for kw in details_node.keywords]:
                if isinstance(arg, ast.Dict):
                    out |= self._find_issue_type_in_dict_literal(arg, func_name)
            if out:
                return out
            if isinstance(details_node.func, ast.Name) and details_node.func.id in self.func_defs:
                callee_name = details_node.func.id
                callee_func = self.func_defs[callee_name]
                dict_lit = self._find_returned_dict_literal(callee_func)
                if dict_lit is not None:
                    return self._find_issue_type_in_dict_literal(dict_lit, callee_name)
            return out
        return set()

    def emitted_pairs(self) -> set[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        for func_name, func in self.func_defs.items():
            for call in ast.walk(func):
                if not isinstance(call, ast.Call):
                    continue
                if not (isinstance(call.func, ast.Name) and call.func.id == "AuditFinding"):
                    continue
                rule_ids: set[str] = set()
                details_node: ast.AST | None = None
                for kw in call.keywords:
                    if kw.arg == "rule_id":
                        rule_ids |= self._resolve_scalar(kw.value, func_name)
                    if kw.arg == "details":
                        details_node = kw.value
                if not rule_ids or details_node is None:
                    continue
                for issue_type in self._resolve_details_arg(details_node, func, func_name):
                    for rule_id in rule_ids:
                        pairs.add((rule_id, issue_type))
        return pairs


def detector_emitted_pairs_by_static_scan() -> set[tuple[str, str]]:
    """Statically extract (rule_id, issue_type) pairs from `AuditFinding(...)`
    call sites in src/njit_auditor/rules/*.py (excluding dead legacy modules).
    See the module docstring for exactly which code patterns this resolves.
    """
    pairs: set[tuple[str, str]] = set()
    for path in sorted(RULES_DIR.glob("*.py")):
        if path.name in _DEAD_LEGACY_FILES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        pairs |= _ModuleResolver(tree).emitted_pairs()
    return pairs


def source_pipeline_issue_type_pairs() -> set[tuple[str, str]]:
    """Statically extract the TeX/"source" pipeline's rule_id -> issue_type
    mapping from `report_outputs.derive_source_issue_type()`'s literal
    `if rule_id == "P0xx": return "..."` dispatch chain. P001-P010 never set
    `issue_type` in their own `AuditFinding.details` — it is synthesized here,
    downstream, by rule_id alone (see module docstring).
    """
    source_text = REPORT_OUTPUTS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(REPORT_OUTPUTS_PATH))
    pairs: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == "derive_source_issue_type"):
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.If):
                continue
            test = stmt.test
            if not (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == "rule_id"
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Eq)
            ):
                continue
            comparator = test.comparators[0]
            if not (isinstance(comparator, ast.Constant) and isinstance(comparator.value, str)):
                continue
            rule_id = comparator.value
            for inner in stmt.body:
                if isinstance(inner, ast.Return) and isinstance(inner.value, ast.Constant):
                    if isinstance(inner.value.value, str):
                        pairs.add((rule_id, inner.value.value))
    return pairs


def full_active_issue_type_universe() -> set[tuple[str, str]]:
    """Union of every static ground-truth source this module knows about:
    the comprehensive AST scan, the TeX/source-pipeline dispatch mapping, and
    the one documented non-detector exception (P021). Does not filter by
    rule_type/phase (reporting-only, experimental, evaluation-task) — callers
    that need "active default-enabled only" should cross-reference against
    the rule catalog themselves, same as they already do for the catalog's
    own `issue_types` field.
    """
    return (
        detector_emitted_pairs_by_static_scan()
        | source_pipeline_issue_type_pairs()
        | set(KNOWN_NON_DETECTOR_ISSUE_TYPES)
    )
