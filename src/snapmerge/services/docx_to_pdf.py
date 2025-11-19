from __future__ import annotations
from pathlib import Path
import sys, tempfile, importlib

class DocxConversionError(RuntimeError):
    pass

def _patch_win32com_genpy_to_temp():
    """
    En binarios PyInstaller, win32com.gencache falla si no puede escribir
    en su carpeta por defecto. Redirigimos gen_py a %TEMP%.
    """
    import win32com, sys as _sys  # type: ignore
    gen_dir = Path(tempfile.gettempdir()) / "pywin32_gen_py"
    gen_dir.mkdir(parents=True, exist_ok=True)
    # win32com usa este atributo interno si existe:
    win32com.__gen_path__ = str(gen_dir)
    # Asegura el paquete importable
    _sys.modules["win32com.gen_py"] = importlib.import_module("win32com.gen_py")


def _export_to_pdf_with_word(inp: Path, out_pdf: Path) -> None:
    try:
        import pythoncom, win32com.client  # type: ignore
        from pythoncom import com_error
    except Exception as e:
        raise DocxConversionError(f"pywin32/Word COM no disponible: {e}")

    _patch_win32com_genpy_to_temp()  # <-- clave para ejecutable congelado

    co_init = False
    try:
        pythoncom.CoInitialize()
        co_init = True

        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone

        # Rutas simples
        inp_str = str(inp)
        out_pdf.parent.mkdir(parents=True, exist_ok=True)

        # Abrimos sin diálogos de conversión (para .doc antiguos)
        doc = word.Documents.Open(inp_str, ReadOnly=True, ConfirmConversions=False)
        try:
            # ExportAsFixedFormat es más estable que SaveAs para .doc
            wdExportFormatPDF = 17
            wdExportOptimizeForPrint = 0
            wdExportAllDocument = 0
            wdExportDocumentContent = 0
            wdExportCreateHeadingBookmarks = 1

            doc.ExportAsFixedFormat(
                OutputFileName=str(out_pdf),
                ExportFormat=wdExportFormatPDF,
                OpenAfterExport=False,
                OptimizeFor=wdExportOptimizeForPrint,
                Range=wdExportAllDocument,
                From=1, To=1,
                Item=wdExportDocumentContent,
                IncludeDocProps=True,
                KeepIRM=True,
                CreateBookmarks=wdExportCreateHeadingBookmarks,
                DocStructureTags=True,
                BitmapMissingFonts=True,
                UseISO19005_1=False,
            )
        finally:
            doc.Close(0)
            word.Quit()

        if not out_pdf.exists():
            raise DocxConversionError("Word no generó el PDF (sin excepción).")
    finally:
        if co_init:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


def docx_to_pdf(inp: Path, out_pdf: Path) -> bool:
    """
    Convierte .doc o .docx a PDF con Word/COM.
    En EXE evita docx2pdf y usa COM directo con cache en %TEMP%.
    """
    if sys.platform != "win32":
        return False

    ext = inp.suffix.lower()
    if ext not in {".doc", ".docx"}:
        return False

    try:
        # Si es .doc, primero migrarlo a .docx con tu método (opcional)
        if ext == ".doc":
            from .doc_migrate import doc_to_docx_via_word
            from tempfile import TemporaryDirectory
            with TemporaryDirectory(prefix="snapmerge_mig_") as td:
                tmp_docx = Path(td) / (inp.stem + ".docx")
                ok = doc_to_docx_via_word(inp, tmp_docx)
                if not ok or not tmp_docx.exists():
                    raise DocxConversionError("Migración .doc → .docx falló.")
                _export_to_pdf_with_word(tmp_docx, out_pdf)
        else:
            _export_to_pdf_with_word(inp, out_pdf)

        return out_pdf.exists()
    except Exception:
        return False
