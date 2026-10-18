"""Generate local synthetic thesis and hostile PDF surfaces; never use real data."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

import fitz
import pikepdf


def make_extended_thesis(path: Path) -> Path:
    """Text-only, multi-page fixture with structural and substantive fake content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        page.insert_text((145, 110), "SYNTHETIC NOVAFERN STUDY", fontname="tibo", fontsize=14)
        page.insert_text((205, 170), "Mira Example", fontname="tiro", fontsize=12)
        page.insert_text((220, 220), "ABSTRACT", fontname="tibo", fontsize=14)
        page.insert_text(
            (108, 270), "Fabricated fern data illustrate a wholly invented study.", fontname="tiro"
        )
        page.insert_text(
            (144, 294), "Synthetic samples confirm no empirical finding.", fontname="tiro"
        )
        page.insert_text((300, 736), "i", fontname="tiro", fontsize=12)

        page = doc.new_page(width=612, height=792)
        page.insert_text((195, 100), "TABLE OF CONTENTS", fontname="tibo", fontsize=14)
        page.insert_text((108, 155), "CHAPTER 1 Synthetic Methods ........ 1", fontname="tiro")
        page.insert_text((108, 180), "CHAPTER 2 Imaginary Findings ....... 2", fontname="tiro")
        page.insert_text((108, 205), "APPENDIX A Fabricated Inputs ....... 3", fontname="tiro")
        page.insert_text((195, 285), "LIST OF TABLES", fontname="tibo", fontsize=14)
        page.insert_text((108, 322), "Table 1.1 Fictional samples ........ 1", fontname="tiro")
        page.insert_text((195, 390), "LIST OF FIGURES", fontname="tibo", fontsize=14)
        page.insert_text((108, 427), "Figure 1.1 Invented trend .......... 1", fontname="tiro")
        page.insert_text((300, 736), "ii", fontname="tiro", fontsize=12)

        page = doc.new_page(width=612, height=792)
        page.insert_text((245, 100), "CHAPTER 1", fontname="tibo", fontsize=14)
        page.insert_text((215, 132), "SYNTHETIC METHODS", fontname="tibo", fontsize=13)
        page.insert_text((108, 190), "A fictional observer counted paper ferns in an empty room.")
        page.insert_text((144, 215), "No human subject or real measurement entered this example.")
        page.insert_text((108, 245), "Table 1.1: Fictional samples.", fontname="tiit", fontsize=11)
        page.insert_text((108, 270), "Sample A       12       14", fontname="cour", fontsize=10)
        page.insert_text((108, 288), "Sample B       17       19", fontname="cour", fontsize=10)
        page.insert_text((108, 330), "Figure 1.1: Invented trend.", fontname="tiit", fontsize=11)
        page.insert_text((55, 370), "Deliberate left-margin violation in fake content.")
        page.insert_text((300, 736), "1", fontname="tiro", fontsize=12)

        page = doc.new_page(width=612, height=792)
        page.insert_text((245, 100), "CHAPTER 2", fontname="tibo", fontsize=14)
        page.insert_text((220, 132), "IMAGINARY FINDINGS", fontname="tibo", fontsize=13)
        page.insert_text((108, 190), "The invented outcomes have no relation to a real study.")
        page.insert_text((144, 215), "All quantities and names on these pages are fabricated.")
        page.insert_text((240, 305), "REFERENCES", fontname="tibo", fontsize=14)
        page.insert_text((108, 345), "Example, M. (2026). A paper fern catalog. Fiction Press.")
        page.insert_text((300, 736), "2", fontname="tiro", fontsize=12)

        page = doc.new_page(width=612, height=792)
        page.insert_text((245, 100), "APPENDIX A", fontname="tibo", fontsize=14)
        page.insert_text((108, 170), "Invented inputs are listed solely for testing.")
        page.insert_text((300, 736), "3", fontname="tiro", fontsize=12)
        doc.set_metadata({"title": "SYNTHETIC extended thesis fixture", "author": "Mira Example"})
        doc.save(path, garbage=4, deflate=True)
    return path


def make_adversarial_fixtures(directory: Path) -> dict[str, Path]:
    """Plant artificial secrets in supported and deliberately unsupported surfaces."""
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / "synthetic_base.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        page.insert_text((108, 100), "ABSTRACT", fontname="hebo", fontsize=14)
        page.insert_text((108, 160), "VISIBLE_SECRET_CEDAR_521 is invented.")
        page.insert_text((300, 736), "i")
        doc.set_metadata({"title": "SYNTHETIC adversarial base", "author": "META_SECRET_CEDAR_521"})
        doc.save(base, garbage=4, deflate=True)
    files: dict[str, Path] = {"visible_metadata": base}

    def save_variant(name: str, modify: Callable[[fitz.Document], object]) -> None:
        output = directory / f"synthetic_{name}.pdf"
        with fitz.open(base) as doc:
            modify(doc)
            doc.save(output, garbage=4, deflate=True)
        files[name] = output

    save_variant(
        "annotation_appearance",
        lambda doc: doc[0].add_freetext_annot(
            fitz.Rect(50, 220, 280, 260), "ANNOT_SECRET_CEDAR_521"
        ),
    )
    save_variant(
        "xmp",
        lambda doc: doc.set_xml_metadata(
            '<x:xmpmeta xmlns:x="adobe:ns:meta/">XMP_SECRET_CEDAR_521</x:xmpmeta>'
        ),
    )
    save_variant(
        "attachment",
        lambda doc: doc.embfile_add("secret.txt", b"ATTACH_SECRET_CEDAR_521"),
    )
    save_variant("optional_layer", lambda doc: doc.add_ocg("LAYER_SECRET_CEDAR_521"))

    def vector_code(doc: fitz.Document) -> None:
        # A binary barcode in vector rectangles, recoverable from path geometry.
        bits = "".join(f"{byte:08b}" for byte in b"VECTOR_SECRET_CEDAR_521")
        for index, bit in enumerate(bits):
            if bit == "1":
                x = 50 + 3 * index
                doc[0].draw_rect(fitz.Rect(x, 300, x + 2, 302), color=(0, 0, 0), fill=(0, 0, 0))

    save_variant("vector", vector_code)
    save_variant("rotated_page", lambda doc: doc[0].set_rotation(90))
    save_variant("cropped_page", lambda doc: doc[0].set_cropbox(fitz.Rect(10, 10, 600, 780)))

    def embedded_math(doc: fitz.Document) -> None:
        fontfile = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        if fontfile.is_file():
            doc[0].insert_font(fontname="SyntheticMath", fontfile=str(fontfile))
            doc[0].insert_text((108, 250), "∑ α × β = 42", fontname="SyntheticMath", fontsize=12)
        else:
            doc[0].insert_text((108, 250), "∑ α × β = 42", fontname="symb", fontsize=12)

    save_variant("embedded_unicode_math", embedded_math)

    def subset_font(doc: fitz.Document) -> None:
        embedded_math(doc)
        doc.subset_fonts()

    save_variant("subset_font", subset_font)

    def mixed_font(doc: fitz.Document) -> None:
        doc[0].insert_text((108, 250), "Mixed", fontname="tiro", fontsize=12)
        doc[0].insert_text((140, 250), "Font Secret", fontname="tibo", fontsize=12)

    save_variant("mixed_font_line", mixed_font)

    def rotated_text_matrix(doc: fitz.Document) -> None:
        xref = doc[0].get_contents()[0]
        stream = doc.xref_stream(xref) or b""
        doc.update_stream(
            xref,
            stream + b"\nBT /helv 12 Tf 0 1 -1 0 200 200 Tm (ROTATED_SECRET_CEDAR_521) Tj ET\n",
        )

    save_variant("rotated_text_matrix", rotated_text_matrix)

    def hidden_ocr(doc: fitz.Document) -> None:
        xref = doc[0].get_contents()[0]
        stream = doc.xref_stream(xref) or b""
        doc.update_stream(
            xref,
            stream + b"\nBT /helv 12 Tf 3 Tr 1 0 0 1 100 500 Tm (OCR_SECRET_CEDAR_521) Tj ET\n",
        )

    save_variant("hidden_ocr", hidden_ocr)

    def pixel_image(doc: fitz.Document) -> None:
        with fitz.open() as donor:
            page = donor.new_page(width=200, height=40)
            page.insert_text((5, 25), "PIXEL_SECRET_521", fontsize=12)
            pix = page.get_pixmap(alpha=False)
            doc[0].insert_image(fitz.Rect(50, 300, 250, 340), pixmap=pix)

    save_variant("pixel_image", pixel_image)

    scan = directory / "synthetic_scan.pdf"
    with fitz.open() as doc, fitz.open() as donor:
        donor_page = donor.new_page(width=612, height=792)
        donor_page.insert_text((108, 120), "SCAN_SECRET_CEDAR_521", fontsize=20)
        pix = donor_page.get_pixmap(alpha=False)
        page = doc.new_page(width=612, height=792)
        page.insert_image(page.rect, pixmap=pix)
        doc.set_metadata({"title": "SYNTHETIC scan only"})
        doc.save(scan, garbage=4, deflate=True)
    files["scan"] = scan

    def form_xobject(doc: fitz.Document) -> None:
        with fitz.open() as donor:
            page = donor.new_page(width=200, height=40)
            page.insert_text((5, 25), "FORM_SECRET_CEDAR_521", fontsize=12)
            doc[0].show_pdf_page(fitz.Rect(50, 300, 250, 340), donor, 0)

    save_variant("form_xobject", form_xobject)

    multi_column = directory / "synthetic_multi_column.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        page.insert_text((108, 100), "CHAPTER 1", fontname="hebo", fontsize=14)
        page.insert_text((108, 160), "Invented left column sentence.")
        page.insert_text((330, 160), "Fabricated right column sentence.")
        page.insert_text((108, 185), "A second fictional left entry.")
        page.insert_text((330, 185), "A second fictional right entry.")
        page.insert_text((300, 736), "1")
        doc.set_metadata({"title": "SYNTHETIC multi column layout"})
        doc.save(multi_column, garbage=4, deflate=True)
    files["multi_column"] = multi_column

    def add_pike(name: str, edit: Callable[[pikepdf.Pdf], object]) -> None:
        output = directory / f"synthetic_{name}.pdf"
        with pikepdf.Pdf.open(base) as pdf:
            edit(pdf)
            pdf.save(output)
        files[name] = output

    add_pike(
        "javascript_action",
        lambda pdf: pdf.Root.__setitem__(
            "/OpenAction",
            pikepdf.Dictionary(
                S=pikepdf.Name("/JavaScript"), JS=pikepdf.String("JS_SECRET_CEDAR_521")
            ),
        ),
    )
    add_pike(
        "tag_alt_text",
        lambda pdf: pdf.Root.__setitem__(
            "/StructTreeRoot",
            pdf.make_indirect(
                pikepdf.Dictionary(
                    Type=pikepdf.Name("/StructTreeRoot"),
                    K=pikepdf.Array(
                        [pikepdf.Dictionary(Alt=pikepdf.String("ALT_SECRET_CEDAR_521"))]
                    ),
                )
            ),
        ),
    )

    def add_thumbnail(pdf: pikepdf.Pdf) -> None:
        thumbnail = pikepdf.Stream(pdf, bytes([255]))
        thumbnail.Type = pikepdf.Name("/XObject")
        thumbnail.Subtype = pikepdf.Name("/Image")
        thumbnail.Width = 1
        thumbnail.Height = 1
        thumbnail.ColorSpace = pikepdf.Name("/DeviceGray")
        thumbnail.BitsPerComponent = 8
        thumbnail.Alt = pikepdf.String("THUMB_SECRET_CEDAR_521")
        pdf.pages[0].Thumb = thumbnail

    add_pike("thumbnail", add_thumbnail)
    add_pike(
        "acroform",
        lambda pdf: pdf.Root.__setitem__(
            "/AcroForm",
            pdf.make_indirect(
                pikepdf.Dictionary(
                    Fields=pikepdf.Array(
                        [pikepdf.Dictionary(T=pikepdf.String("FORM_FIELD_SECRET_CEDAR_521"))]
                    )
                )
            ),
        ),
    )

    incremental = directory / "synthetic_incremental.pdf"
    incremental.write_bytes(base.read_bytes())
    with fitz.open(incremental) as doc:
        doc.set_metadata({"title": "SYNTHETIC incremental", "author": "REV_SECRET_CEDAR_521"})
        doc.saveIncr()
    files["incremental"] = incremental

    residual = directory / "synthetic_residual_object.pdf"
    residual.write_bytes(base.read_bytes() + b"\n999 0 obj\n(RESIDUAL_SECRET_CEDAR_521)\nendobj\n")
    files["residual_object"] = residual
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(make_extended_thesis(args.directory / "synthetic_extended_thesis.pdf"))
    print(len(make_adversarial_fixtures(args.directory / "adversarial")), "adversarial PDFs")


if __name__ == "__main__":
    main()
