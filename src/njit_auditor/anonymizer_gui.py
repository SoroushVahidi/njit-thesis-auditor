"""Small local file-picker front end for the verified PDF anonymizer."""

from __future__ import annotations

from pathlib import Path

from njit_auditor.practical_pdf_anonymizer import UnsupportedPDF, anonymize


def select_and_anonymize() -> None:
    """Ask for separate source and destination files, then run locally."""
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.withdraw()
    try:
        selected = filedialog.askopenfilename(
            parent=root,
            title="Select a PDF to anonymize locally",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not selected:
            return
        source = Path(selected)
        output = filedialog.asksaveasfilename(
            parent=root,
            title="Save anonymized PDF as",
            initialfile=f"{source.stem}-anonymized.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            confirmoverwrite=False,
        )
        if not output:
            return
        try:
            report = anonymize(
                source, Path(output), authorized=True, verify_auditor=True
            )
        except (UnsupportedPDF, FileExistsError, ValueError, OSError) as exc:
            messagebox.showerror("PDF refused", str(exc), parent=root)
            return
        except Exception:
            messagebox.showerror(
                "Anonymization failed",
                "The PDF could not be processed. No output was published.",
                parent=root,
            )
            return
        messagebox.showinfo(
            "Anonymization complete",
            f"Saved {report['pages']} page(s) to {output}.\n"
            "Review the result before sharing; layout can still identify a source.",
            parent=root,
        )
    finally:
        root.destroy()


def main() -> None:
    try:
        select_and_anonymize()
    except ImportError as exc:
        raise SystemExit("Tkinter is required for the file picker") from exc


if __name__ == "__main__":
    main()
