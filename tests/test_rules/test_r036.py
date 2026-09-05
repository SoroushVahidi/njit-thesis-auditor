import pytest
from pathlib import Path
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_body_spacing import check_pdf_body_spacing

@pytest.fixture
def mock_pdf():
    class MockPdf:
        def __init__(self):
            self.pages = []
    return MockPdf()

def test_r036_chapter_boundary_accepted(mock_pdf):
    """Test chapter boundary should not trigger spacing violation"""
    findings = check_pdf_body_spacing(mock_pdf)
    assert not any("spacing_violation" in f.details.get("issue_type", "") for f in findings)

def test_r036_appendix_boundary_accepted(mock_pdf):
    """Test appendix boundary should not trigger spacing violation"""
    findings = check_pdf_body_spacing(mock_pdf)
    assert not any("spacing_violation" in f.details.get("issue_type", "") for f in findings)

def test_r036_arbitrary_all_caps_not_exempted(mock_pdf):
    """Test arbitrary ALL-CAPS text should still be checked"""
    findings = check_pdf_body_spacing(mock_pdf)
    # Should detect genuine spacing issues
    assert any("spacing_violation" in f.details.get("issue_type", "") for f in findings)
