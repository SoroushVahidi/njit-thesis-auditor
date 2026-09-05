import pytest
from pathlib import Path
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_lot_lof_entry_type import check_pdf_lot_lof_entry_type

@pytest.fixture
def mock_pdf_document():
    class MockPdf:
        def __init__(self):
            self.pages = []
    return MockPdf()

def test_r055_valid_table_prefix(mock_pdf_document):
    """Test valid Table 1.1 entry should not generate finding"""
    findings = check_pdf_lot_lof_entry_type(mock_pdf_document)
    assert not any("lot_entry_is_figure" in f.details["issue_type"] for f in findings)
    assert not any("lof_entry_is_table" in f.details["issue_type"] for f in findings)

def test_r055_numeric_only_lot_entry(mock_pdf_document):
    """Test numeric-only LoT entry should generate missing Table prefix finding"""
    findings = check_pdf_lot_lof_entry_type(mock_pdf_document)
    assert any("lot_entry_is_figure" in f.details["issue_type"] for f in findings)
    assert "missing Table prefix" in str(f.details["issue_type"])

def test_r055_cross_type_lot(mock_pdf_document):
    """Test Figure 1.1 in List of Tables should generate wrong-type violation"""
    findings = check_pdf_lot_lof_entry_type(mock_pdf_document)
    assert any("lot_entry_is_figure" in f.details["issue_type"] for f in findings)

def test_r055_cross_type_lof(mock_pdf_document):
    """Test Table 1.1 in List of Figures should generate wrong-type violation"""
    findings = check_pdf_lot_lof_entry_type(mock_pdf_document)
    assert any("lof_entry_is_table" in f.details["issue_type"] for f in findings)
