from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Any
from PySide6.QtCore import QObject, Signal, Slot

class DocPagesWorker(QObject):
    """Worker that reads Word document pages in a QThread."""

    status = Signal(str)
    progress = Signal(int, int)          # done, total
    finished = Signal(dict)             # {Path_str: pages_int}
    error = Signal(str, str)           # message, traceback

    def __init__(self, paths: List[Path], parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        # ormalizing the paths
        self._paths = [p.resolve() for p in paths]

    @Slot()
    def run(self) -> None:
        """It runs within the QThread."""
        import traceback

        result: Dict[str, int] = {}

        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore
        except Exception as exc:
            self.error.emit("pywin32 not available", repr(exc))
            return

        # same patch you use in docx_to_pdf
        try:
            from snapmerge.services.docx_to_pdf import _patch_win32com_genpy_to_temp
            try:
                _patch_win32com_genpy_to_temp()
            except Exception:
                pass
        except Exception:
            pass

        word = None
        co_init = False
        try:
            pythoncom.CoInitialize()
            co_init = True

            total = len(self._paths)
            if total == 0:
                self.finished.emit(result)
                return

            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0  # wdAlertsNone

            for idx, doc_path in enumerate(self._paths, start=1):
                self.progress.emit(idx, total)
                self.status.emit(f"Reading pages: {doc_path.name}")

                try:
                    doc = word.Documents.Open(
                        str(doc_path),
                        ReadOnly=True,
                        ConfirmConversions=False,
                    )
                except Exception:
                    continue

                pages = None
                try:
                    # 1) Built-in property
                    try:
                        props = doc.BuiltInDocumentProperties
                        pages = int(props("Number of Pages"))
                    except Exception:
                        pages = None

                    # 2) Fallback: ComputeStatistics
                    if pages is None:
                        try:
                            wdStatisticPages = 2  # pages
                            pages = int(doc.ComputeStatistics(wdStatisticPages))
                        except Exception:
                            pages = None

                    if pages is not None and pages > 0:
                        result[str(doc_path)] = pages

                finally:
                    try:
                        doc.Close(False)
                    except Exception:
                        pass

        except Exception as exc:
            tb = traceback.format_exc()
            self.error.emit(str(exc), tb)
            return

        finally:
            try:
                if word is not None:
                    word.Quit()
            except Exception:
                pass

            if co_init:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

        self.finished.emit(result)