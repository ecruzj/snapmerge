from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import shutil

from .doc_migrate import doc_to_docx_via_word

class DocxConversionError(RuntimeError):
    pass

def _convert_docx_to_pdf_with_docx2pdf(inp_docx: Path, out_pdf: Path) -> None:
    """
    Convert a .docx to PDF using docx2pdf (Word/COM below).
    """
    try:
        from docx2pdf import convert  # requires Microsoft Word on Windows
    except Exception as e:
        raise DocxConversionError(
            "The 'docx2pdf' dependency is missing or Microsoft Word is not available.: " + str(e)
        )

    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    # docx2pdf supports convert(file_in, file_out) on Windows
    convert(str(inp_docx), str(out_pdf))

    if not out_pdf.exists():
        raise DocxConversionError("docx2pdf did not generate the PDF (without exception).")


def docx_to_pdf(inp: Path, out_pdf: Path) -> bool:
    """
    Convert Word documents to PDF.
    - If it's a .doc file: first migrate to a .docx file with Word/COM (doc_to_docx_via_word),
        then convert that .docx file to a PDF with docx2pdf.
    - If it is .docx: convert directly with docx2pdf.
    Returns True if the PDF was generated.
    """
    if sys.platform != "win32":
        # Requires Windows + Microsoft Word for docx2pdf/COM
        return False

    suffix = inp.suffix.lower()
    if suffix not in {".doc", ".docx"}:
        return False

    tmp_dir: Path | None = None
    tmp_docx: Path | None = None

    try:
        if suffix == ".doc":
            # 1) Migrate .doc -> .docx
            tmp_dir = Path(tempfile.mkdtemp(prefix="snapmerge_docx_tmp_"))
            tmp_docx = tmp_dir / (inp.stem + ".docx")

            ok = doc_to_docx_via_word(inp, tmp_docx)
            if not ok or not tmp_docx.exists():
                raise DocxConversionError(
                    f"Could not migrate {inp.name} to .docx before exporting to PDF."
                )

            # 2) Convert .docx -> .pdf
            _convert_docx_to_pdf_with_docx2pdf(tmp_docx, out_pdf)

        else:
            # .docx directo to PDF
            _convert_docx_to_pdf_with_docx2pdf(inp, out_pdf)

        return out_pdf.exists()

    except Exception as exc:
        return False

    finally:
        # Temporary cleanup if there was migration
        if tmp_dir and tmp_dir.exists():
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass
