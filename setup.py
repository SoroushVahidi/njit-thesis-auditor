"""Copy only canonical runtime JSON into wheels; keep one source of truth."""

from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

RUNTIME_JSON = (
    "data/processed/rules/project_added_rules.json",
    "data/specs/ester_warning_wording_map.json",
    "data/specs/ester_q_matrix.json",
    "data/specs/ester_q_current_authority_overlay.json",
)


class BuildRuntimeResources(build_py):
    def run(self):
        super().run()
        for relative in RUNTIME_JSON:
            target = Path(self.build_lib) / "njit_auditor" / relative
            self.mkpath(str(target.parent))
            self.copy_file(relative, str(target))

    def get_outputs(self, include_bytecode=True):
        return super().get_outputs(include_bytecode) + [
            str(Path(self.build_lib) / "njit_auditor" / relative)
            for relative in RUNTIME_JSON
        ]


setup(cmdclass={"build_py": BuildRuntimeResources})
