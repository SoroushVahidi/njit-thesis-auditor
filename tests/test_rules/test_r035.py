from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfGraphicBlock,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_figure_table_layout import check_pdf_figure_table_layout


def make_mock_doc(is_landscape=False, caption_type="table", body_x0=178.0, body_x1=470.0):
    width, height = (792.0, 612.0) if is_landscape else (612.0, 792.0)
    page = PdfPage(
        page_number=1,
        original_page_index=0,
        original_page_number=1,
        manuscript_page_index=0,
        manuscript_page_number=1,
        width=width,
        height=height,
        is_visually_landscape=is_landscape,
        text_blocks=[],
        graphic_blocks=[]
    )
    
    # Add caption
    if caption_type == "table":
        cap_text = "Table 1.1 Experimental Results of the Mantel Test."
        cap_bbox = BBox(x0=108.0, y0=100.0, x1=540.0, y1=115.0)
        span = PdfTextSpan(text=cap_text, bbox=cap_bbox)
        line = PdfTextLine(spans=[span], bbox=cap_bbox, text=cap_text)
        block = PdfTextBlock(lines=[line], bbox=cap_bbox, text=cap_text)
        page.text_blocks.append(block)
        
        # Add body block (below caption, allow_multiline=True)
        body_bbox = BBox(x0=body_x0, y0=125.0, x1=body_x1, y1=250.0)
        b_text1 = "First line of experimental results under the table."
        b_text2 = "Second line of experimental results under the table."
        bbox_l1 = BBox(x0=body_x0, y0=125.0, x1=body_x1, y1=180.0)
        bbox_l2 = BBox(x0=body_x0, y0=180.0, x1=body_x1, y1=250.0)
        span1 = PdfTextSpan(text=b_text1, bbox=bbox_l1)
        line1 = PdfTextLine(spans=[span1], bbox=bbox_l1, text=b_text1)
        span2 = PdfTextSpan(text=b_text2, bbox=bbox_l2)
        line2 = PdfTextLine(spans=[span2], bbox=bbox_l2, text=b_text2)
        b_block = PdfTextBlock(lines=[line1, line2], bbox=body_bbox, text=b_text1 + " " + b_text2)
        page.text_blocks.append(b_block)
    else:
        # Figure caption (below body)
        cap_text = "Figure 1.1 Experimental Results of the Mantel Test."
        cap_bbox = BBox(x0=108.0, y0=300.0, x1=540.0, y1=315.0)
        span = PdfTextSpan(text=cap_text, bbox=cap_bbox)
        line = PdfTextLine(spans=[span], bbox=cap_bbox, text=cap_text)
        block = PdfTextBlock(lines=[line], bbox=cap_bbox, text=cap_text)
        page.text_blocks.append(block)
        
        # Add graphic block (above caption)
        body_bbox = BBox(x0=body_x0, y0=125.0, x1=body_x1, y1=250.0)
        graphic = PdfGraphicBlock(bbox=body_bbox, kind="image")
        page.graphic_blocks.append(graphic)
        
    doc = PdfDocument(path="mock.pdf", pages=[page])
    return doc

def test_r035_portrait_centered_table():
    """Portrait table centered: delta = 0, should pass"""
    doc = make_mock_doc(is_landscape=False, caption_type="table", body_x0=274.0, body_x1=374.0)
    findings = check_pdf_figure_table_layout(doc)
    assert not any("table_body_not_centered" in f.details.get("issue_type", "") for f in findings)

def test_r035_portrait_table_just_within_tolerance():
    """Portrait table just within 18pt tolerance: delta = 17.9, should pass"""
    doc = make_mock_doc(is_landscape=False, caption_type="table", body_x0=291.9, body_x1=391.9)
    findings = check_pdf_figure_table_layout(doc)
    assert not any("table_body_not_centered" in f.details.get("issue_type", "") for f in findings)

def test_r035_portrait_table_just_beyond_tolerance():
    """Portrait table just beyond 18pt tolerance: delta = 18.1, should find violation"""
    doc = make_mock_doc(is_landscape=False, caption_type="table", body_x0=292.1, body_x1=392.1)
    findings = check_pdf_figure_table_layout(doc)
    assert any("table_body_not_centered" in f.details.get("issue_type", "") for f in findings)

def test_r035_landscape_table_just_within_tolerance():
    """Landscape table just within 50pt tolerance: delta = 49.9, should pass"""
    doc = make_mock_doc(is_landscape=True, caption_type="table", body_x0=413.9, body_x1=513.9)
    findings = check_pdf_figure_table_layout(doc)
    assert not any("table_body_not_centered" in f.details.get("issue_type", "") for f in findings)

def test_r035_landscape_table_just_beyond_tolerance():
    """Landscape table just beyond 50pt tolerance: delta = 50.1, should find violation"""
    doc = make_mock_doc(is_landscape=True, caption_type="table", body_x0=414.1, body_x1=514.1)
    findings = check_pdf_figure_table_layout(doc)
    assert any("table_body_not_centered" in f.details.get("issue_type", "") for f in findings)

def test_r035_portrait_centered_figure():
    """Portrait figure centered: delta = 0, should pass"""
    doc = make_mock_doc(is_landscape=False, caption_type="figure", body_x0=274.0, body_x1=374.0)
    findings = check_pdf_figure_table_layout(doc)
    assert not any("figure_body_not_centered" in f.details.get("issue_type", "") for f in findings)

def test_r035_portrait_figure_just_within_tolerance():
    """Portrait figure just within 18pt tolerance: delta = 17.9, should pass"""
    doc = make_mock_doc(is_landscape=False, caption_type="figure", body_x0=291.9, body_x1=391.9)
    findings = check_pdf_figure_table_layout(doc)
    assert not any("figure_body_not_centered" in f.details.get("issue_type", "") for f in findings)

def test_r035_portrait_figure_just_beyond_tolerance():
    """Portrait figure just beyond 18pt tolerance: delta = 18.1, should find violation"""
    doc = make_mock_doc(is_landscape=False, caption_type="figure", body_x0=292.1, body_x1=392.1)
    findings = check_pdf_figure_table_layout(doc)
    assert any("figure_body_not_centered" in f.details.get("issue_type", "") for f in findings)

def test_r035_landscape_figure_just_within_tolerance():
    """Landscape figure just within 50pt tolerance: delta = 49.9, should pass"""
    doc = make_mock_doc(is_landscape=True, caption_type="figure", body_x0=413.9, body_x1=513.9)
    findings = check_pdf_figure_table_layout(doc)
    assert not any("figure_body_not_centered" in f.details.get("issue_type", "") for f in findings)

def test_r035_landscape_figure_just_beyond_tolerance():
    """Landscape figure just beyond 50pt tolerance: delta = 50.1, should find violation"""
    doc = make_mock_doc(is_landscape=True, caption_type="figure", body_x0=414.1, body_x1=514.1)
    findings = check_pdf_figure_table_layout(doc)
    assert any("figure_body_not_centered" in f.details.get("issue_type", "") for f in findings)


def test_r035_figure_text_fallback_not_used_for_centering():
    """When no qualifying graphic block exists above a figure caption, any
    text fragments found there (axis labels, callouts extracted as separate
    blocks) must not be treated as the figure's visual body for centering
    purposes -- their bbox is not a reliable proxy for where the actual
    image sits, and can be badly off-center even when the real image is
    fine (e.g. an axis-label block flush against the left margin)."""
    page = PdfPage(
        page_number=1,
        original_page_index=0,
        original_page_number=1,
        manuscript_page_index=0,
        manuscript_page_number=1,
        width=612.0,
        height=792.0,
        is_visually_landscape=False,
        text_blocks=[],
        graphic_blocks=[],
    )
    cap_text = "Figure 1.1 Experimental Results of the Mantel Test."
    cap_bbox = BBox(x0=108.0, y0=300.0, x1=540.0, y1=315.0)
    cap_span = PdfTextSpan(text=cap_text, bbox=cap_bbox)
    cap_line = PdfTextLine(spans=[cap_span], bbox=cap_bbox, text=cap_text)
    cap_block = PdfTextBlock(lines=[cap_line], bbox=cap_bbox, text=cap_text)
    page.text_blocks.append(cap_block)

    # Two small, badly off-center single-line text fragments above the
    # caption -- no graphic block is present at all, mimicking axis-label
    # text extracted separately from an actual embedded image.
    for text, y0, y1 in [
        ("Concentration (mg/L) axis label", 200.0, 212.0),
        ("Time (hours) secondary axis note", 213.0, 225.0),
    ]:
        frag_bbox = BBox(x0=50.0, y0=y0, x1=140.0, y1=y1)
        span = PdfTextSpan(text=text, bbox=frag_bbox)
        line = PdfTextLine(spans=[span], bbox=frag_bbox, text=text)
        block = PdfTextBlock(lines=[line], bbox=frag_bbox, text=text)
        page.text_blocks.append(block)

    doc = PdfDocument(path="mock.pdf", pages=[page])
    findings = check_pdf_figure_table_layout(doc)
    assert not any(
        f.details.get("issue_type") == "figure_body_not_centered" for f in findings
    )
