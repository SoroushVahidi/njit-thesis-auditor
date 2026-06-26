#!/usr/bin/env bash
# web_demo_smoke.sh — Local smoke check for the NJIT Thesis Auditor web demo fixtures.
#
# WHAT THIS SCRIPT DOES:
#   1. Prints the committed synthetic fixture paths and their suggested manual upload order.
#   2. Runs the automated pytest smoke suite (tests/test_web_demo_fixtures.py) in quiet mode.
#
# WHAT THIS SCRIPT DOES NOT DO:
#   - Does NOT start a long-running web server.
#   - Does NOT make any external network requests.
#   - Does NOT upload files to any remote service.
#   - Does NOT require any credentials or API keys.
#
# USAGE:
#   ./scripts/web_demo_smoke.sh
#
# PREREQUISITES:
#   - A Python virtualenv must be active with the package installed:
#       python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
#
# PRIVACY NOTE:
#   All fixtures in tests/fixtures/web_demo/ contain only synthetic placeholder text.
#   Do NOT add real dissertation files to that directory.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FIXTURES_DIR="$REPO_DIR/tests/fixtures/web_demo"

echo "======================================================================"
echo "  NJIT Thesis Auditor — Web Demo Smoke Check"
echo "======================================================================"
echo ""
echo "Fixture directory: $FIXTURES_DIR"
echo ""
echo "Committed synthetic fixtures (suggested manual upload order):"
echo ""
echo "  1. $FIXTURES_DIR/clean_minimal.pdf"
echo "       Upload type : PDF (web UI)"
echo "       Expected    : Audit completes; residual P011/P013/P027 outputs (minimal demo, not zero findings)"
echo ""
echo "  2. $FIXTURES_DIR/issues_pdf.pdf"
echo "       Upload type : PDF (web UI)"
echo "       Expected    : P011 margin warnings and P013 findings appear"
echo ""
echo "  3. $FIXTURES_DIR/clean_minimal.tex"
echo "       Upload type : TeX (command-line tool only)"
echo "       Expected    : Rejected by the web upload form (PDF-only); source audit"
echo "                     completes via the CLI 'tex' command with zero or very few findings"
echo ""
echo "  4. $FIXTURES_DIR/issues_tex.tex"
echo "       Upload type : TeX (command-line tool only)"
echo "       Expected    : Rejected by the web upload form (PDF-only); CLI source audit"
echo "                     produces P001/P002/P004/P005/P007 findings"
echo ""
echo "  5. $FIXTURES_DIR/demo_project.zip"
echo "       Upload type : ZIP (command-line tool only)"
echo "       Expected    : Rejected by the web upload form (PDF-only); CLI extracts the"
echo "                     ZIP, detects main.tex, and produces a source report"
echo ""
echo "To run the web UI manually for the PDF uploads above:"
echo "  ./scripts/run_web_gui.sh 127.0.0.1"
echo "  Then open http://localhost:8000 in a browser."
echo ""
echo "======================================================================"
echo "  Running automated pytest smoke suite ..."
echo "======================================================================"
echo ""

cd "$REPO_DIR"
python -m pytest tests/test_web_demo_fixtures.py -q

echo ""
echo "======================================================================"
echo "  Smoke check complete."
echo "======================================================================"
