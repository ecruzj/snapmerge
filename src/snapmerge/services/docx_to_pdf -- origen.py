from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import sys

class DocxConversionError(RuntimeError):
    """Raised when a .docx to .pdf conversion fails."""
    pass

def has_word() -> bool:
    # Heuristic: docx2pdf requires Word on Windows. We'll try to import and run.
    try:
        import docx2pdf # type: ignore
        return True
    except Exception:
        return False

def convert_with_docx2pdf(inp: Path, out_pdf: Path) -> None:
    # Ensure COM is initialized for this worker thread
    try:
        import pythoncom  # type: ignore
        pythoncom.CoInitialize()
        co_init = True
    except Exception:
        co_init = False

    try:
        from docx2pdf import convert  # type: ignore
        # docx2pdf writes to a folder; we convert file→folder and then move result
        tmp_out = out_pdf.parent
        convert(str(inp), str(tmp_out))
        # Resulting file should be same name with .pdf
        candidate = tmp_out / (inp.stem + ".pdf")
        if not candidate.exists():
            raise DocxConversionError("docx2pdf did not produce expected output")
        candidate.replace(out_pdf)
    finally:
        # Important to tear down COM to avoid hanging next runs
        if co_init:
            try:
                import pythoncom  # type: ignore
                pythoncom.CoUninitialize()
            except Exception:
                pass

def convert_with_libreoffice(inp: Path, out_pdf: Path) -> None:
    import shutil, subprocess
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    
    if not soffice:
        raise DocxConversionError("LibreOffice not found in PATH")
    cmd = [soffice, "--headless", "--convert-to", "pdf", str(inp), "--outdir", str(out_pdf.parent)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    if proc.returncode != 0:
        raise DocxConversionError(proc.stderr or "LibreOffice conversion failed")
    candidate = out_pdf.parent / (inp.stem + ".pdf")
    
    if not candidate.exists():
        raise DocxConversionError("LibreOffice did not produce expected output")
    candidate.replace(out_pdf)

def docx_to_pdf(inp: Path, out_pdf: Path) -> bool:
    """
    Return True if converted, False if no tool available.
    Robust in frozen EXE: either prefer LibreOffice, or initialize COM when using Word.
    """
    # Prefer LibreOffice when frozen (EXE) to avoid COM threading quirks
    is_frozen = getattr(sys, "frozen", False)
    try:
        if is_frozen:
            try:
                convert_with_libreoffice(inp, out_pdf)
                return True
            except DocxConversionError:
                # fallback to Word/COM if LibreOffice not present
                if has_word():
                    convert_with_docx2pdf(inp, out_pdf)
                    return True
                return False
        else:
            if has_word():
                convert_with_docx2pdf(inp, out_pdf)
                return True
            try:
                convert_with_libreoffice(inp, out_pdf)
                return True
            except DocxConversionError:
                return False
    except Exception as exc:
        raise DocxConversionError(str(exc))