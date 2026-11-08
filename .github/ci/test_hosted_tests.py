"""Exercise fail-closed hosted boundaries without loading application tests."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hosted_tests import check_workspace, inventory


class HostedBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.git("config", "lfs.fetchexclude", "*")
        self.environment = patch.dict(os.environ, {"GIT_LFS_SKIP_SMUDGE": "1"}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        (self.root / "tests").mkdir()
        (self.root / "tests/test_synthetic.py").touch()
        (self.root / "tests/test_local.py").touch()
        (self.root / ".github/ci").mkdir(parents=True)
        self.manifest = {"hosted": ["tests/test_synthetic.py"],
                         "local_only": {"tests/test_local.py": "Private fixture"},
                         "browser": ["tests/test_synthetic.py::test_browser"], "support": []}
        self.write_manifest()

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root)

    def write_manifest(self):
        (self.root / ".github/ci/tests.json").write_text(json.dumps(self.manifest))

    def test_clean_checkout_and_inventory_are_accepted(self):
        check_workspace(self.root)
        self.assertEqual(inventory(self.root), self.manifest)

    def test_new_unclassified_module_cannot_be_collected(self):
        (self.root / "tests/test_new.py").touch()
        with self.assertRaisesRegex(ValueError, "classify every module"):
            inventory(self.root)

    def test_unreviewed_conftest_cannot_execute(self):
        (self.root / "tests/conftest.py").write_text("raise RuntimeError('must not import')")
        with self.assertRaisesRegex(ValueError, "Test support changed"):
            inventory(self.root)

    def test_private_module_cannot_enter_browser_selection(self):
        self.manifest["browser"] = ["tests/test_local.py"]
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "Browser selection"):
            inventory(self.root)

    def test_private_root_is_rejected_without_disclosing_contents(self):
        private = self.root / "data/raw"
        private.mkdir(parents=True)
        (private / "synthetic-secret-name.pdf").write_bytes(b"synthetic secret")
        with self.assertRaisesRegex(ValueError, "Private fixture roots") as error:
            check_workspace(self.root)
        self.assertNotIn("synthetic-secret", str(error.exception))

    def test_private_environment_is_rejected(self):
        os.environ["NJIT_ESTER_AUDIT_SOURCE_MANIFEST"] = "synthetic-secret.json"
        with self.assertRaisesRegex(ValueError, "Private replay environment"):
            check_workspace(self.root)

    def test_remote_and_lfs_fetch_configuration_are_enforced(self):
        self.git("remote", "add", "origin", "https://example.invalid/repo.git")
        with self.assertRaisesRegex(ValueError, "Remove checkout remotes"):
            check_workspace(self.root)
        self.git("remote", "remove", "origin")
        self.git("config", "lfs.fetchexclude", "not-everything")
        with self.assertRaisesRegex(ValueError, "All LFS fetching"):
            check_workspace(self.root)

    def test_pointer_allowed_but_materialized_lfs_is_rejected(self):
        (self.root / ".gitattributes").write_text("*.pdf filter=lfs\n")
        pdf = self.root / "synthetic.pdf"
        pdf.write_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:" + b"0" * 64)
        self.git("-c", "filter.lfs.clean=cat", "-c", "filter.lfs.process=",
                 "-c", "filter.lfs.required=false", "add", ".")
        check_workspace(self.root)
        pdf.write_bytes(b"%PDF synthetic materialized payload")
        with self.assertRaisesRegex(ValueError, "Materialized LFS content"):
            check_workspace(self.root)


if __name__ == "__main__":
    unittest.main()
