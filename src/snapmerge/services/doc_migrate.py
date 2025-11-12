from __future__ import annotations
from pathlib import Path
import sys

class DocMigrationError(RuntimeError):
    pass

def doc_to_docx_via_word(inp: Path, out_docx: Path) -> bool:
    """
    Attempts to convert a .doc (or .docx) file to a .docx file using Microsoft Word/COM
    (SaveAs2 with FileFormat=12). Returns True if the .docx file was created.
    """
    if sys.platform != "win32":
        return False

    try:
        import pythoncom
        import win32com.client
        from pythoncom import com_error
    except Exception as e:
        raise DocMigrationError("Windows + pywin32 + Microsoft Word required: " + str(e))

    co_init = False
    try:
        pythoncom.CoInitialize()
        co_init = True

        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone

        # Open without confirming conversions (for .doc 97-2003)
        doc = word.Documents.Open(str(inp), ReadOnly=True, ConfirmConversions=False)
        try:
            out_docx.parent.mkdir(parents=True, exist_ok=True)
            wdFormatXMLDocument = 12  # .docx
            # SaveAs2 is the MS supported way for new extensions
            doc.SaveAs2(str(out_docx), FileFormat=wdFormatXMLDocument)
        finally:
            doc.Close(0)  # wdDoNotSaveChanges
            word.Quit()

        return out_docx.exists()
    except Exception as exc:
        raise DocMigrationError(f"Failed to migrate '{inp.name}' to .docx: {exc}")

    finally:
        if co_init:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

def doc_to_docx_text_only(inp: Path, out_docx: Path) -> bool:
    """
    Plan B: Open the .doc file with Word/COM, extract ONLY the plain text, 
        and create a new .docx file with python-docx. 
    Useful for checking access/permissions. (You'll lose formatting, images, tables, etc.)
    """
    if sys.platform != "win32":
        return False

    try:
        import pythoncom
        import win32com.client
        from docx import Document
    except Exception as e:
        raise DocMigrationError("Missing dependency for plan B (pywin32/python-docx): " + str(e))

    co_init = False
    try:
        pythoncom.CoInitialize()
        co_init = True

        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0

        doc = word.Documents.Open(str(inp), ReadOnly=True, ConfirmConversions=False)
        try:
            # Full text of the document
            text = doc.Content.Text or ""
        finally:
            doc.Close(0)
            word.Quit()

        # Create a new .docx with python-docx
        out_docx.parent.mkdir(parents=True, exist_ok=True)
        d = Document()
        for line in text.splitlines():
            d.add_paragraph(line)
        d.save(str(out_docx))

        return out_docx.exists()

    except Exception as exc:
        raise DocMigrationError(f"Plan B failed for'{inp.name}': {exc}")

    finally:
        if co_init:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

if __name__ == "__main__":
    # Quick use by CLI: python -m snapmerge.services.doc_migrate "C:\path\in.doc" "C:\out\in.docx"
    # python -m snapmerge.services.doc_migrate "C:\tmp\OFFICE-OLD.doc" "C:\tmp\OFFICE-OLD_out.docx"

    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("inp")
    p.add_argument("out_docx")
    p.add_argument("--text-only", action="store_true", help="Usar Plan B (solo texto)")
    args = p.parse_args()

    ok = False
    if args.text_only:
        print("Using Plan B (text only)...")
        ok = doc_to_docx_text_only(Path(args.inp), Path(args.out_docx))
    else:
        print("Using Plan A (full)...")
        ok = doc_to_docx_via_word(Path(args.inp), Path(args.out_docx))

    print("OK" if ok else "FAILED")