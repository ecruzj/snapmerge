from pathlib import Path
import sys

class DocxConversionError(RuntimeError):
    pass

def _convert_with_word_com(inp: Path, out_pdf: Path) -> None:
    """
    Convierte .doc y .docx a PDF usando Microsoft Word (COM).
    Usa ExportAsFixedFormat porque es más fiable con .doc (97–2003).
    """
    try:
        import pythoncom
        import win32com.client
        from pythoncom import com_error
    except Exception as e:
        raise DocxConversionError(
            "Se requiere Windows con Microsoft Word y pywin32 instalados: " + str(e)
        )

    co_init = False
    try:
        pythoncom.CoInitialize()
        co_init = True

        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        # 0 = wdAlertsNone (evita prompts invisibles)
        word.DisplayAlerts = 0

        # Abrimos sin confirmar conversiones para .doc antiguos
        doc = word.Documents.Open(
            str(inp),
            ReadOnly=True,
            ConfirmConversions=False,
        )

        try:
            out_pdf.parent.mkdir(parents=True, exist_ok=True)

            # Constantes (valores de Word)
            wdExportFormatPDF = 17
            wdExportOptimizeForPrint = 0
            wdExportAllDocument = 0
            wdExportDocumentContent = 0
            wdExportCreateHeadingBookmarks = 1

            # Exportación fiable a PDF (mejor que SaveAs para .doc)
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

            # Verifica que **realmente** se haya creado el PDF
            if not out_pdf.exists():
                # Como fallback, intenta SaveAs2 (algunas builds lo requieren)
                try:
                    wdFormatPDF = 17
                    doc.SaveAs2(str(out_pdf), FileFormat=wdFormatPDF)
                except Exception:
                    pass

            if not out_pdf.exists():
                raise DocxConversionError(
                    f"Word no generó el PDF para '{inp.name}' (sin excepción COM)."
                )

        finally:
            # 0 = DoNotSaveChanges
            doc.Close(0)
            word.Quit()

    # except com_error as e:
    #     # Mensaje COM con detalle (HRESULT + descripción)
    #     desc = ""
    #     try:
    #         desc = e.excepinfo[2] if e.excepinfo and e.excepinfo[2] else ""
    #     except Exception:
    #         pass
    #     raise DocxConversionError(
    #         f"Error COM Word 0x{e.hresult & 0xFFFFFFFF:08X}: {desc or e}"
    #     )
    except Exception as exc:
        raise DocxConversionError(f"Fallo al convertir '{inp.name}': {exc}")
    finally:
        if co_init:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


def docx_to_pdf(inp: Path, out_pdf: Path) -> bool:
    if sys.platform != "win32":
        return False
    if inp.suffix.lower() not in {".docx", ".doc"}:
        return False
    _convert_with_word_com(inp, out_pdf)
    return True
