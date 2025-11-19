from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtUiTools import loadUiType
from PySide6.QtGui import QIcon
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QMessageBox,
)

# RUN THIS FILE AS MODULE TO LAUNCH THE QT APP:
#   python -m snapmerge.app_qt

# ---------------------------------------------------------------------------
# UI loading (no more .ui -> .py generation)
# ---------------------------------------------------------------------------

UI_PATH = Path(__file__).resolve().parent / "ui" / "snap_merge_app.ui"
_loadui_result = loadUiType(str(UI_PATH))

if isinstance(_loadui_result, tuple):
    Ui_SnapMergeWindow, QtBaseClass = _loadui_result
else:
    # Fallback: some environments return only the UI class
    Ui_SnapMergeWindow = _loadui_result
    QtBaseClass = QMainWindow

# ---------------------------------------------------------------------------
# Version / build info
# ---------------------------------------------------------------------------

# Soporta ejecución tanto como módulo (`python -m snapmerge.app_qt`)
try:
    from .app_version.build_info import FULL_VERSION, APP_VERSION, BUILD_NUMBER, GIT_SHA
except Exception:
    # fallback if you run without a previous build step
    from .app_version.version import APP_VERSION
    FULL_VERSION, BUILD_NUMBER, GIT_SHA = f"{APP_VERSION}+dev", 0, "nogit"

from snapmerge.config import Settings
from snapmerge.pipeline import run_merge

# -------------------- Worker running in a QThread --------------------


class MergeWorker(QObject):
    """Runs the merge pipeline off the UI thread."""
    progress = Signal(int, int)        # done, total
    status = Signal(str)               # status/log line
    finished = Signal(dict)            # report dict
    failed = Signal(str)               # error message
    merge_started = Signal(int)        # total files to join
    merge_progress = Signal(int, int)  # done, total

    def __init__(
        self,
        input_dir: Path,
        output_pdf: Path,
        settings: Settings,
        should_cancel: Callable[[], bool],
    ) -> None:
        super().__init__()
        self.input_dir = input_dir
        self.output_pdf = output_pdf
        self.settings = settings
        self.should_cancel = should_cancel

    @Slot()
    def run(self) -> None:
        """Entrypoint for the worker thread."""

        def progress_cb(done: int, total: int) -> None:
            # Cooperative cancel
            if self.should_cancel():
                raise RuntimeError("Cancelled by user")
            # Emit progress to UI
            self.progress.emit(done, total)
            # If we reached 100% of discovered files, signal finalization phase
            if total > 0 and done >= total:
                self.status.emit("Finalizing (writing PDF…)")

        def merge_start_cb(total: int) -> None:
            # UI reseteará la barra a 0 aquí
            self.merge_started.emit(total)

        def merge_progress_cb(done: int, total: int) -> None:
            self.merge_progress.emit(done, total)

        try:
            report = run_merge(
                input_dir=self.input_dir,
                output_pdf=self.output_pdf,
                settings=self.settings,
                progress_cb=progress_cb,          # Fase 1
                status_cb=self.status.emit,
                merge_start_cb=merge_start_cb,    # Fase 2 (merge begins)
                merge_progress_cb=merge_progress_cb,  # Fase 2 progress
                log_file=None,
            )
            self.finished.emit(report)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# -------------------- Main Window --------------------


class SnapMergeApp(QtBaseClass):
    def __init__(self):
        super().__init__()
        self.ui = Ui_SnapMergeWindow()
        self.ui.setupUi(self)

        # App Title
        self.setWindowTitle(
            f"SnapMerge - Merge Files into PDF - v{APP_VERSION}"
        )

        # App icon
        app_icon = QIcon(str(Path(__file__).resolve().parent / "ui" / "icon.ico"))
        self.setWindowIcon(app_icon)

        # Settings
        self.settings = Settings.from_file(
            Path(__file__).resolve().parents[1] / "config.yaml"
        )

        # Hook up signals (estos nombres deben existir en tu .ui)
        self.ui.add_files_btn.clicked.connect(self.on_add_files)
        self.ui.add_folder_btn.clicked.connect(self.on_add_folder)
        self.ui.remove_btn.clicked.connect(self.on_remove_selected)
        self.ui.clear_btn.clicked.connect(self.on_clear_all)
        self.ui.move_up_btn.clicked.connect(lambda: self.move_row(-1))
        self.ui.move_down_btn.clicked.connect(lambda: self.move_row(1))
        self.ui.sort_name_btn.clicked.connect(self.sort_by_name)
        self.ui.sort_type_btn.clicked.connect(self.sort_by_type)

        self.ui.browse_output_btn.clicked.connect(self.select_output_file)
        self.ui.run_btn.clicked.connect(self.on_run)
        self.ui.cancel_btn.clicked.connect(self.on_cancel)

        # Defaults
        self._cancelled = False
        self._thread: Optional[QThread] = None
        self._worker: Optional[MergeWorker] = None
        self._start_time: Optional[datetime] = None

        # Initial UI state
        self.ui.log_text.setReadOnly(True)
        self.ui.input_line.setReadOnly(True)
        self.ui.output_line.setReadOnly(True)
        self.ui.log_text.append("Ready to merge!")
        self.ui.progress_bar.setValue(0)

    # ------------- UI Helpers -------------

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select input folder")
        if folder:
            self.ui.input_line.setText(folder)

    def select_output_file(self):
        file, _ = QFileDialog.getSaveFileName(
            self, "Save output PDF", "", "PDF Files (*.pdf)"
        )
        if file:
            # Ensure .pdf extension
            out = Path(file)
            if out.suffix.lower() != ".pdf":
                out = out.with_suffix(".pdf")
            self.ui.output_line.setText(str(out))

    def _validate_paths(self) -> tuple[Optional[Path], Optional[Path]]:
        """Validate input/output fields; return tuple if OK, otherwise None/None."""
        input_text = (self.ui.input_line.text() or "").strip()
        output_text = (self.ui.output_line.text() or "").strip()

        if not input_text:
            QMessageBox.warning(self, "SnapMerge", "Please choose an input folder.")
            return None, None
        if not output_text:
            QMessageBox.warning(self, "SnapMerge", "Please choose an output PDF path.")
            return None, None

        input_dir = Path(input_text).expanduser()
        output_pdf = Path(output_text).expanduser()

        if not input_dir.exists() or not input_dir.is_dir():
            QMessageBox.warning(self, "SnapMerge", "Input folder is invalid.")
            return None, None

        if output_pdf.suffix.lower() != ".pdf":
            output_pdf = output_pdf.with_suffix(".pdf")
            self.ui.output_line.setText(str(output_pdf))

        # Ensure parent folder exists
        try:
            output_pdf.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "SnapMerge", f"Cannot create output folder:\n{e}")
            return None, None

        return input_dir, output_pdf

    def _lock_ui(self, running: bool):
        self.ui.run_btn.setEnabled(not running)
        self.ui.cancel_btn.setEnabled(running)
        self.ui.browse_input_btn.setEnabled(not running)
        self.ui.browse_output_btn.setEnabled(not running)
        self.ui.sort_by_combo.setEnabled(not running)
        self.ui.sort_desc_chk.setEnabled(not running)
        self.ui.include_sub_chk.setEnabled(not running)

    # ------------- Run / Cancel -------------
    def on_run(self):
        # Validate
        input_dir, output_pdf = self._validate_paths()
        if not input_dir or not output_pdf:
            return

        # Persist user options to runtime settings (no file write)
        self.settings._data["include_subfolders"] = self.ui.include_sub_chk.isChecked()
        self.settings._data["sort_by"] = self.ui.sort_by_combo.currentText()
        self.settings._data["sort_desc"] = self.ui.sort_desc_chk.isChecked()

        # Prepare UI and timing
        self._cancelled = False
        self._start_time = datetime.now()
        self.ui.progress_bar.setValue(0)
        self.ui.log_text.clear()
        self.ui.log_text.append("Starting…")
        self.ui.log_text.append(f"Input:  {input_dir}")
        self.ui.log_text.append(f"Output: {output_pdf}")
        self.ui.log_text.append(
            f"Start time: {self._start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self._lock_ui(True)

        # Thread + Worker
        self._thread = QThread(self)
        self._worker = MergeWorker(
            input_dir=input_dir,
            output_pdf=output_pdf,
            settings=self.settings,
            should_cancel=lambda: self._cancelled,
        )
        self._worker.moveToThread(self._thread)

        # Wire signals
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.on_progress)
        self._worker.status.connect(self.on_status)
        self._worker.merge_started.connect(self.on_merge_started)      # Fase 2
        self._worker.merge_progress.connect(self.on_merge_progress)    # Fase 2
        self._worker.finished.connect(self.on_finished)
        self._worker.failed.connect(self.on_failed)

        # Cleanup when done
        self._worker.finished.connect(
            lambda _report: self._thread.quit() if self._thread else None
        )
        self._worker.failed.connect(
            lambda _msg: self._thread.quit() if self._thread else None
        )
        self._thread.finished.connect(self._cleanup_thread)

        # Go!
        self._thread.start()

    def on_cancel(self):
        if self._worker is None:
            return
        self._cancelled = True
        self.ui.log_text.append("Cancellation requested…")

    def _cleanup_thread(self):
        """Ensure worker/thread objects are cleaned and UI re-enabled."""
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        if self._thread:
            self._thread.deleteLater()
            self._thread = None

        self._cancelled = False
        self._lock_ui(False)
        self.ui.progress_bar.setValue(0)
        self.ui.log_text.append("Ready to merge again!")

    # ------------- Slots from Worker -------------

    @Slot(int, int)
    def on_progress(self, done: int, total: int):
        if total <= 0:
            return
        pct = int(done * 100 / total)
        self.ui.progress_bar.setValue(pct)
        self.ui.log_text.append(f"Progress: {done}/{total} ({pct}%)")

    @Slot(str)
    def on_status(self, message: str):
        self.ui.log_text.append(message)

    @Slot(dict)
    def on_finished(self, report: dict):
        end_time = datetime.now()
        self.ui.log_text.append(
            f"End time:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        if self._start_time:
            duration = end_time - self._start_time
            self.ui.log_text.append(f"Duration:   {duration}")
        self.ui.log_text.append("Transaction completed successfully.")
        self.ui.log_text.append(f"Output file: {report.get('output')}")

        QMessageBox.information(
            self,
            "SnapMerge",
            "The transaction has finished successfully.\n\n"
            f"Output:\n{report.get('output')}\n\n"
            f"Start: {self._start_time.strftime('%Y-%m-%d %H:%M:%S') if self._start_time else '-'}\n"
            f"End:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}",
        )

    @Slot(str)
    def on_failed(self, message: str):
        self.ui.log_text.append("Error: " + message)
        QMessageBox.critical(self, "SnapMerge", message)

    @Slot(int)
    def on_merge_started(self, total: int) -> None:
        self.ui.progress_bar.setValue(0)
        self.ui.log_text.append(
            f"Starting merge phase… {total} file(s) to append."
        )

    @Slot(int, int)
    def on_merge_progress(self, done: int, total: int) -> None:
        if total <= 0:
            return
        pct = int(done * 100 / total)
        self.ui.progress_bar.setValue(pct)
        if done == 1 or done == total or done % 10 == 0:
            self.ui.log_text.append(f"Merge progress: {done}/{total} ({pct}%)")
            
            
        # ----------------- NUEVOS SLOTS PARA LA NUEVA UI -----------------

    def on_add_files(self):
        """Seleccionar uno o varios archivos y agregarlos a files_table (TODO)."""
        self.ui.log_text.append("on_add_files() not implemented yet.")

    def on_add_folder(self):
        """Seleccionar carpeta y agregar sus archivos a files_table (TODO)."""
        self.ui.log_text.append("on_add_folder() not implemented yet.")

    def on_remove_selected(self):
        """Eliminar filas seleccionadas de files_table."""
        table = self.ui.files_table
        rows = sorted({idx.row() for idx in table.selectedIndexes()}, reverse=True)
        for row in rows:
            table.removeRow(row)
        self.ui.log_text.append(f"Removed {len(rows)} row(s).")

    def on_clear_all(self):
        """Limpiar toda la lista de archivos."""
        self.ui.files_table.setRowCount(0)
        self.ui.log_text.append("Cleared file list.")

    def move_row(self, direction: int):
        """Mover fila actual hacia arriba (-1) o abajo (+1)."""
        table = self.ui.files_table
        current_row = table.currentRow()
        if current_row < 0:
            return

        target_row = current_row + direction
        if target_row < 0 or target_row >= table.rowCount():
            return

        for col in range(table.columnCount()):
            item_current = table.takeItem(current_row, col)
            item_target = table.takeItem(target_row, col)
            table.setItem(current_row, col, item_target)
            table.setItem(target_row, col, item_current)

        table.selectRow(target_row)

    def sort_by_name(self):
        """Ordenar por la columna Name."""
        # Name es la columna 1 (# = 0, Name = 1)
        self.ui.files_table.sortItems(1)
        self.ui.log_text.append("Sorted by name.")

    def sort_by_type(self):
        """Ordenar por la columna Type."""
        # Type es la columna 2
        self.ui.files_table.sortItems(2)
        self.ui.log_text.append("Sorted by type.")


# -------------------- Entry --------------------
def main():
    import sys
    import traceback

    def excepthook(exc_type, exc_value, exc_tb):
        with open("error.log", "a", encoding="utf-8") as f:
            f.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))

    sys.excepthook = excepthook

    app = QApplication([])
    win = SnapMergeApp()
    win.show()
    app.exec()

if __name__ == "__main__":
    main()