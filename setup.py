"""Bundle the runtime projection of the catalog and selected application assets."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

ROOT = Path(__file__).resolve().parent
CATALOG = "data/processed/rules/project_added_rules.json"
WORDING = "data/specs/ester_warning_wording_map.json"
ASSETS = (
    "assets/fonts/DejaVu-LICENSE.txt",
    "assets/fonts/DejaVuSans.ttf",
    "assets/icons/njit-auditor.ico",
)
CATALOG_FIELDS = (
    "id",
    "title",
    "question",
    "section",
    "phase",
    "input_required",
    "severity",
    "checkability",
    "rule_definition",
    "remediation",
    "rule_type",
    "implementation_status",
)
# The runtime checks these markers for rule classification. Editorial notes
# and source references are checkout provenance, outside the runtime catalog.
CATALOG_MARKERS = (
    "experimental",
    "opt-in",
    "disabled by default",
    "infrastructure-only",
    "reporting-only",
)
WORDING_FIELDS = (
    "question",
    "remediation",
    "issue_type_questions",
    "apply_question_to_issue_types",
)


def write_runtime_json(destination: Path) -> None:
    catalog = json.loads((ROOT / CATALOG).read_text(encoding="utf-8"))
    wording = json.loads((ROOT / WORDING).read_text(encoding="utf-8"))
    public_catalog = [
        {key: rule[key] for key in CATALOG_FIELDS if key in rule}
        | {
            "notes": " ".join(
                marker for marker in CATALOG_MARKERS if marker in (rule.get("notes") or "").lower()
            )
        }
        for rule in catalog
    ]
    public_wording = {
        "rules": {
            rule_id: {key: rule[key] for key in WORDING_FIELDS if key in rule}
            for rule_id, rule in wording["rules"].items()
        }
    }
    for relative, payload in ((CATALOG, public_catalog), (WORDING, public_wording)):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        # Setuptools can hard-link source files into the release tree.
        target.unlink(missing_ok=True)
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


class BuildRuntimeResources(build_py):
    def run(self):
        super().run()
        runtime = Path(self.build_lib) / "njit_auditor" / "_runtime"
        write_runtime_json(runtime)
        for relative in ASSETS:
            target = runtime / relative
            self.mkpath(str(target.parent))
            self.copy_file(relative, str(target))

    def get_outputs(self, include_bytecode=True):
        runtime = Path(self.build_lib) / "njit_auditor" / "_runtime"
        return super().get_outputs(include_bytecode) + [
            str(runtime / relative) for relative in (CATALOG, WORDING, *ASSETS)
        ]


class RuntimeSourceDistribution(sdist):
    def make_release_tree(self, base_dir, files):
        # Refuse to archive unrelated material from a previous staging tree.
        Path(base_dir).mkdir()
        super().make_release_tree(base_dir, files)
        write_runtime_json(Path(base_dir))


# Both the wheel's build and installation staging derive from build_base.
# An existing build/ directory can contain files outside our allowlists.
with TemporaryDirectory(prefix="njit-package-build-") as build_dir:
    setup(
        cmdclass={"build_py": BuildRuntimeResources, "sdist": RuntimeSourceDistribution},
        options={"build": {"build_base": build_dir}},
    )
