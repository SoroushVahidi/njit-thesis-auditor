#!/usr/bin/env bash
# Reproducible native Linux developer validation; use synthetic PDFs only.
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"
venv_dir="${OFFLINE_VALIDATION_VENV:-${TMPDIR:-/tmp}/njit-offline-validation-$(id -u)}"
python3.12 -m venv "$venv_dir"
"$venv_dir/bin/python" -m pip install -c packaging/offline-build-constraints.txt -e '.[dev]' pyinstaller
"$venv_dir/bin/ruff" check .
"$venv_dir/bin/mypy" src
"$venv_dir/bin/python" -m pytest -q tests/test_offline_desktop.py tests/test_web_app.py \
    tests/test_highlight_pdf_student_routes.py tests/test_student_pdf_report.py
"$venv_dir/bin/pyinstaller" --noconfirm --clean packaging/offline_desktop.spec
"$venv_dir/bin/python" scripts/inspect_offline_bundle.py 'dist/NJIT Thesis Auditor'
if command -v strace >/dev/null; then
    "$venv_dir/bin/python" scripts/smoke_offline_linux.py 'dist/NJIT Thesis Auditor' \
        --trace "${OFFLINE_TRACE_PREFIX:-${TMPDIR:-/tmp}/njit-offline-bind-connect-$(id -u)}"
else
    "$venv_dir/bin/python" scripts/smoke_offline_linux.py 'dist/NJIT Thesis Auditor'
fi
