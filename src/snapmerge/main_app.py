from __future__ import annotations
import html
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QIcon
from PySide6.QtUiTools import loadUiType
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTableWidgetItem,
    QAbstractItemView,
    QHeaderView
)

from snapmerge.config import Settings
# from snapmerge.services.docx_to_pdf import _patch_win32com_genpy_to_temp
from snapmerge.thread_worker.doc_pages_worker import DocPagesWorker
from snapmerge.thread_worker.merge_worker import MergeWorker, MergeJob

# ---------------------------------------------------------------------------
# Load .ui file
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
UI_PATH = HERE / "ui" / "snap_merge_app.ui"

if not UI_PATH.exists():
    raise FileNotFoundError(f"UI file not found: {UI_PATH}")

_ui_result = loadUiType(str(UI_PATH))
if isinstance(_ui_result, tuple):
    Ui_SnapMergeWindow, QtBaseClass = _ui_result
else:  # very old / edge Qt versions
    Ui_SnapMergeWindow = _ui_result
    QtBaseClass = QMainWindow

# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class SnapMergeApp(QtBaseClass):
    def __init__(self) -> None:
        super().__init__()
        
        # Log styles
        self.LOG_STYLES = {
            "warning": {"color": "#d97a00", "bold": True},
            "error":   {"color": "#c62828", "bold": True},
            "success": {"color": "#007200", "bold": True},
            "info":    {"color": "#000000", "bold": False},
        }

        # Build UI
        self.ui = Ui_SnapMergeWindow()
        self.ui.setupUi(self)
        
        # Progress bar initial state
        self.ui.merge_progress_bar.setValue(0)
        self.ui.merge_progress_bar.setVisible(False)

        # Enable drag & drop
        self.setAcceptDrops(True)

        # Optional: custom window title + icon
        self.setWindowTitle("SnapMerge - Merge files into PDF")
        icon_path = HERE / "ui" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Convenience alias
        self.table = self.ui.files_table

        # Configure table
        header = self.table.horizontalHeader()
        # Allow the user to always be able to resize columns
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)  # the last column (Path) stretches at the end

        # Set initial column widths
        self.table.setColumnWidth(0, 20)  # #
        self.table.setColumnWidth(1, 200)  # Name
        self.table.setColumnWidth(2, 45)  # Type
        self.table.setColumnWidth(3, 45)  # Size
        self.table.setColumnWidth(4, 45)  # Pages

        # Set row height
        vh = self.table.verticalHeader()
        vh.setDefaultSectionSize(20)
        vh.setMinimumSectionSize(18)

        self.table.setStyleSheet(
            """
            QTableView::item:selected {
                background-color: #cde8ff;  /* blue light */
                color: black;
            }
            """
        )

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.table.setDropIndicatorShown(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        
        # Columns: #, Name, Type, Size, Pages, Path
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["#", "Name", "Type", "Size", "Pages", "Path"])
        self.table.horizontalHeader().setStretchLastSection(True)

        # Wire toolbar buttons
        self.ui.add_files_btn.clicked.connect(self.on_add_files)
        self.ui.add_folder_btn.clicked.connect(self.on_add_folder)
        self.ui.remove_btn.clicked.connect(self.on_remove_selected)
        self.ui.clear_btn.clicked.connect(self.on_clear_all)
        self.ui.move_up_btn.clicked.connect(lambda: self.move_row(-1))
        self.ui.move_down_btn.clicked.connect(lambda: self.move_row(1))
        self.ui.sort_name_btn.clicked.connect(self.sort_by_name)
        self.ui.sort_type_btn.clicked.connect(self.sort_by_type)

        # Bottom area
        self.ui.browse_output_btn.clicked.connect(self.select_output_file)
        self.ui.run_btn.clicked.connect(self.on_merge_clicked)
        self.ui.cancel_btn.clicked.connect(self.on_cancel_clicked)

        # Log widget
        self.ui.log_text.setReadOnly(True)
        self.log("Ready to merge files.")

        # Load settings from YAML (or defaults if file is missing)
        config_path = HERE.parent.parent / "config.yaml"
        self.settings = Settings.from_file(config_path)
        
        # Cache extension groups from settings (all lowercase)
        self.image_exts = {ext.lower() for ext in self.settings.get("allowed_images", [])}
        self.pdf_exts = {ext.lower() for ext in self.settings.get("allowed_pdfs", [])}
        self.doc_exts = {ext.lower() for ext in self.settings.get("allowed_docs", [])}
        
        self.word_page_count_enabled = bool(self.settings.get("word_page_count", True))
        self.max_docs_for_word_batch = int(self.settings.get("max_docs_for_word_batch", 30))
        
        # Cache for Word page counts to avoid reopening the same file
        self._doc_pages_cache: dict[Path, int] = {}
        
        self._merge_thread: QThread | None = None
        self._merge_worker: MergeWorker | None = None
        self._current_staging_dir: Path | None = None
        self._last_output_pdf: Path | None = None
        self._doc_thread: QThread | None = None
        self._doc_worker: DocPagesWorker | None = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------    
    def log(self, message: str, style: str = "info") -> None:
        """Unified logger with style presets (warning, error, success, info)."""
        safe = html.escape(message)  # Avoid breaking HTML due to special characters

        cfg = self.LOG_STYLES.get(style, self.LOG_STYLES["info"])
        color = cfg["color"]
        bold = cfg["bold"]

        if bold:
            html_msg = f'<span style="color:{color};"><b>{safe}</b></span>'
        else:
            html_msg = f'<span style="color:{color};">{safe}</span>'

        self.ui.log_text.append(html_msg)

        
    def _set_ui_enabled(self, enabled: bool) -> None:
        """
        Enable or disable all main controls while a long task is running.
        The log and progress bar stay enabled/visible.
        """
        # Top buttons
        self.ui.add_files_btn.setEnabled(enabled)
        self.ui.add_folder_btn.setEnabled(enabled)
        self.ui.include_subfolders_chk.setEnabled(enabled)
        self.ui.remove_btn.setEnabled(enabled)
        self.ui.clear_btn.setEnabled(enabled)
        self.ui.move_up_btn.setEnabled(enabled)
        self.ui.move_down_btn.setEnabled(enabled)
        self.ui.sort_name_btn.setEnabled(enabled)
        self.ui.sort_type_btn.setEnabled(enabled)
        self.ui.allow_duplicate_files_chk.setEnabled(enabled)

        # Table
        self.table.setEnabled(enabled)

        # Destination / options
        self.ui.browse_output_btn.setEnabled(enabled)
        self.ui.overwrite_chk.setEnabled(enabled)
        self.ui.output_line.setEnabled(enabled) 

        # Merge / Cancel buttons
        self.ui.run_btn.setEnabled(enabled)

    # -------------------- File list handling -------------------------

    def _collect_files_from_folder(self, folder: Path, recursive: bool) -> List[Path]:
        """Return the list of supported files in the folder (and subfolders if recursive=True)."""
        if recursive:
            candidates = folder.rglob("*")
        else:
            candidates = folder.iterdir()

        paths: List[Path] = [
            p for p in candidates if p.is_file() and p.suffix.lower() in self.settings.allowed_exts
        ]
        return paths
    
    def _append_files(self, paths: List[Path]) -> None:
        """
        Append the given file paths to the table, skipping duplicates.

        Now consider two types of duplicates:
        - Same Path
        - Same signature (Name, Type, Size, Pages) even if the Path is different.
        - Same signature (Name, Type, Size) only for .doc/.docx (ignoring Pages).
        """
        if not paths:
            return
        
        # If the user checked "Overwrite if exists", we allow duplicates
        # by signature (Name/Type/Size/Pages). We only continue to block exact duplicates
        # by Path.
        skip_signature_check = self.ui.allow_duplicate_files_chk.isChecked()

        # ------------------------------------------------------------------
        # 1) Build sets from what already exists in the table
        # ------------------------------------------------------------------
        existing_paths: set[Path] = set()
        existing_signatures: set[tuple[str, str, str, str]] = set()
        doc_candidates: list[Path] = []  # for doc page count update later

        for row in range(self.table.rowCount()):
            # actual Path actual
            path_item = self.table.item(row, 5)  # Path column
            if path_item is not None:
                try:
                    rp = Path(path_item.text()).resolve()
                    existing_paths.add(rp)
                except Exception:
                    pass

            # actual signature (Name, Type, Size, Pages)
            name_item = self.table.item(row, 1)
            type_item = self.table.item(row, 2)
            size_item = self.table.item(row, 3)
            pages_item = self.table.item(row, 4)
           
            name_text = (name_item.text() if name_item else "").lower()
            ext_text = (type_item.text() if type_item else "").lower()
            size_text = size_item.text() if size_item else ""
            pages_text = pages_item.text() if pages_item else ""
            
            if ext_text in ("doc", "docx"):
                signature = (name_text, ext_text, size_text) # Create special signature for doc/docx (ignore pages)
            else:
                signature = (name_text, ext_text, size_text, pages_text) # Full signature for others
                
            existing_signatures.add(signature)

        # ------------------------------------------------------------------
        # 2) Process new paths
        # ------------------------------------------------------------------
        added_count = 0
        skipped_count = 0

        for path in paths:
            if not path.is_file():
                continue

            rp = path.resolve()

            # File data that we will use both for signing and for displaying
            ext = path.suffix.lower().lstrip(".")
            
            if "." + ext in self.pdf_exts:
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(str(rp))

                    # Some versions use .is_encrypted, others .encrypted
                    if getattr(reader, "is_encrypted", False):
                        skipped_count += 1
                        self.log(
                            f"Skipped password-protected PDF (cannot be merged): {rp}",
                            "error"
                        )
                        continue
                except Exception as exc:
                    # A PDF that can't even be opened; it's best not to accept it.
                    skipped_count += 1
                    self.log(
                        f"Skipped unreadable PDF (cannot be merged): {rp} ({exc})",
                        "error"
                    )
                    continue

            try:
                size_bytes = path.stat().st_size
            except OSError:
                size_bytes = 0
            size_str = self._format_size(size_bytes)

            pages = self._guess_pages(path)
            pages_text = "" if pages is None else str(pages)

            if "." + ext in self.doc_exts:
                signature = (path.name.lower(), ext.lower(), size_str)
            else:
                # signature (Name, Type, Size, Pages)
                signature = (path.name.lower(), ext.lower(), size_str, pages_text)

            # 2.1 Duplicated by PATH
            if rp in existing_paths:
                skipped_count += 1
                self.log(
                    f"Skipped duplicate file (same path already in the list): {rp}",
                    "warning")
                continue

            # 2.2 Duplicate by Name/Type/Size/Pages (even though the path is different)
            # We only apply this validation if *Overwrite* is not checked.
            if (not skip_signature_check) and (signature in existing_signatures):
                skipped_count += 1
                self.log(
                    "Skipped duplicate file "
                    "(same Name/Type/Size/Pages as another entry): "
                    f"{path.name} [{ext}, {size_str}, pages={pages_text or '0'}]",
                    "warning"
                )
                continue

            # If we get here, it's a new file → we add it
            existing_paths.add(rp)
            existing_signatures.add(signature)
            added_count += 1

            row = self.table.rowCount()
            self.table.insertRow(row)

            # Column 0: index (#)
            idx_item = QTableWidgetItem(str(row + 1))
            idx_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, idx_item)

            # Column 1: Name
            name_item = QTableWidgetItem(path.name)
            self.table.setItem(row, 1, name_item)

            # Column 2: Type (extension)
            type_item = QTableWidgetItem(ext)
            self.table.setItem(row, 2, type_item)

            # Column 3: Size (ya calculado)
            size_item = QTableWidgetItem(size_str)
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, size_item)

            # Column 4: Pages
            pages_item = QTableWidgetItem(pages_text)
            pages_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, pages_item)

            # Collect doc/docx candidates for later page count update
            if "." + ext in self.doc_exts:
                doc_candidates.append(rp)

            # Column 5: Full path
            path_item = QTableWidgetItem(str(rp))
            self.table.setItem(row, 5, path_item)

        # ------------------------------------------------------------------
        # 3) Post-processing: renumber, recalculate pages, doc pages
        # ------------------------------------------------------------------
        self._renumber_rows()
        self._recalculate_total_pages()

        # Resolve doc/docx pages in batch
        if doc_candidates:
            self._update_doc_pages_batch(doc_candidates)

        if added_count:
            self.log(f"Added {added_count} file(s).")
        if skipped_count:
            self.log(f"Skipped {skipped_count} duplicate file(s).", "warning")

    @staticmethod
    def _format_size(num_bytes: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if num_bytes < 1024.0:
                return f"{num_bytes:.0f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.0f} TB"
    
    def _guess_pages(self, path: Path) -> int | None:
        """
        Try to estimate page count for a file.

        - Images: always 1 page
        - PDFs: real page count using PyPDF2
        - Docs: left as None for now (phase 2, if we hook into Word/COM)
        """
        ext = path.suffix.lower()

        # Images: 1 page
        if ext in self.image_exts:
            return 1

        # PDFs: use PyPDF2 to get page count
        if ext in self.pdf_exts:
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(str(path))
                return len(reader.pages)
            except Exception:
                # If anything goes wrong, we just don't show pages
                return None

        # Docs: we never call word counter here
        if ext in self.doc_exts:
            cached = self._doc_pages_cache.get(path.resolve())
            return cached if cached is not None else None

        # Others: unknown
        return None
    
    def _update_doc_pages_batch(self, paths: list[Path]) -> None:
        """
        Launch a background worker to count doc/docx pages.
        The UI doesn't freeze; the counts are populated when the worker finishes.
        """
        if not self.word_page_count_enabled:
            return

        if sys.platform != "win32":
            return

        # Normalize and filter only documents that are NOT cached yet
        to_process: list[Path] = []
        for p in paths:
            p_res = p.resolve()
            if p_res.suffix.lower() in self.doc_exts and p_res not in self._doc_pages_cache:
                to_process.append(p_res)

        if not to_process:
            return

        # (Optional) respect the document limit to avoid abuse
        # if len(to_process) > self.max_docs_for_word_batch:
        #     self.log(
        #         f"Skipping Word page counting for {len(to_process)} document(s) "
        #         f"(limit {self.max_docs_for_word_batch}); you can run it later.",
        #         "warning",
        #     )
        #     return

        self._start_doc_pages_job(to_process)
        
    def _start_doc_pages_job(self, paths: list[Path]) -> None:
        # Avoid launching two page workers in parallel.
        if self._doc_thread is not None and self._doc_thread.isRunning():
            self.log(
                "Word page counting is already running in background.",
                "info",
            )
            return

        self._doc_thread = QThread(self)
        self._doc_worker = DocPagesWorker(paths)
        self._doc_worker.moveToThread(self._doc_thread)

        # Connections
        self._doc_thread.started.connect(self._doc_worker.run)
        self._doc_worker.status.connect(self._on_doc_pages_status)
        self._doc_worker.progress.connect(self._on_doc_pages_progress)
        self._doc_worker.finished.connect(self._on_doc_pages_finished)
        self._doc_worker.error.connect(self._on_doc_pages_error)

        # Cleaning
        self._doc_worker.finished.connect(self._doc_thread.quit)
        self._doc_worker.finished.connect(self._doc_worker.deleteLater)
        self._doc_thread.finished.connect(self._on_doc_thread_finished)
        self._doc_thread.finished.connect(self._doc_thread.deleteLater)

        # Show bar down by reusing the same
        self.ui.merge_progress_bar.setVisible(True)
        self.ui.merge_progress_bar.setValue(0)

        self._doc_thread.start()
        
    def _on_doc_thread_finished(self) -> None:
        self._doc_thread = None
        self._doc_worker = None
        self.ui.merge_progress_bar.setVisible(False)
    
    def _recalculate_total_pages(self) -> None:
        """Recalculate and display the total number of pages from the table."""
        total = 0
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 4)  # Pages column
            if item is None:
                continue
            text = (item.text() or "").strip()
            if not text:
                continue
            try:
                total += int(text)
            except ValueError:
                # If it's something like "?" or non-numeric, skip it
                continue

        # Update label in the UI
        self.ui.total_pages_label.setText(f"Total pages: {total}")

    def _renumber_rows(self) -> None:
        """Refresh the index (#) column after any structural change."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is None:
                item = QTableWidgetItem()
                self.table.setItem(row, 0, item)
            item.setText(str(row + 1))


    # -------------------- Background merge via QThread -----------------
    def _start_merge_job(self, job: MergeJob) -> None:
        """Create QThread + MergeWorker and start the background merge."""
        # Safety: avoid starting if another thread is already running
        if self._merge_thread is not None and self._merge_thread.isRunning():
            self.log("A merge is already running; new request ignored.")
            return

        self._merge_thread = QThread(self)
        self._merge_worker = MergeWorker(job)
        self._merge_worker.moveToThread(self._merge_thread)

        # Wire thread/worker life‑cycle
        self._merge_thread.started.connect(self._merge_worker.run)
        self._merge_worker.finished.connect(self._on_merge_finished)
        self._merge_worker.error.connect(self._on_merge_error)
        
        # Cancellation signals
        self._merge_worker.cancelled.connect(self._on_merge_cancelled)
        self._merge_worker.cancelled.connect(self._merge_thread.quit)
        self._merge_worker.cancelled.connect(self._merge_worker.deleteLater)

        # Progress / status signals
        self._merge_worker.status.connect(self._on_worker_status)
        self._merge_worker.progress.connect(self._on_worker_progress)
        self._merge_worker.merge_start.connect(self._on_worker_merge_start)
        self._merge_worker.merge_progress.connect(self._on_worker_merge_progress)

        # Clean‑up when the job ends (success or error)
        self._merge_worker.finished.connect(self._merge_thread.quit)
        self._merge_worker.error.connect(self._merge_thread.quit)
        self._merge_worker.finished.connect(self._merge_worker.deleteLater)
        self._merge_worker.error.connect(self._merge_worker.deleteLater)
        self._merge_thread.finished.connect(self._on_thread_finished)
        self._merge_thread.finished.connect(self._merge_thread.deleteLater)

        self._merge_thread.start()

    def _cleanup_staging_dir(self) -> None:
        """Delete the temporary staging directory, if any."""
        if self._current_staging_dir is not None:
            try:
                shutil.rmtree(self._current_staging_dir, ignore_errors=True)
            except Exception:
                # Best‑effort clean‑up; don't crash the app on failure
                pass
            finally:
                self._current_staging_dir = None

    # -- slots that receive progress from MergeWorker (GUI thread) -----

    def _on_worker_status(self, message: str) -> None:
        self.log(message)

    def _on_worker_progress(self, done: int, total: int) -> None:
        if total <= 0:
            return
        pct = int(done * 100 / total)
        # Conversion phase → 0–70 %
        bar_pct = int(pct * 0.7)
        self.ui.merge_progress_bar.setValue(bar_pct)

    def _on_worker_merge_start(self, total_files: int) -> None:
        self.log(f"Merge phase started… {total_files} file(s) to append.")

    def _on_worker_merge_progress(self, done: int, total: int) -> None:
        if total <= 0:
            return
        if done == 1 or done == total or done % 10 == 0:
            pct = int(done * 100 / total)
            # Merge phase → 70–100 %
            bar_pct = 70 + int(pct * 0.3)
            self.ui.merge_progress_bar.setValue(bar_pct)
            self.log(f"Merge progress: {done}/{total} ({pct}%)")

    def _on_merge_finished(self, report: dict) -> None:
        """Called when MergeWorker finishes successfully."""
        self.ui.merge_progress_bar.setValue(100)
        self._set_ui_enabled(True)
        self.log("Merge completed successfully.", "success")
        self._cleanup_staging_dir()

        # Prefer the path reported by the pipeline, fallback to the last
        # one selected in the UI if not present.
        output_value = report.get("output") if isinstance(report, dict) else None
        output_path = None
        if output_value:
            try:
                output_path = Path(output_value)
            except TypeError:
                output_path = None
        if output_path is None:
            output_path = self._last_output_pdf

        if output_path is None:
            QMessageBox.information(
                self,
                "SnapMerge",
                "The merge has finished successfully.",
            )
        else:
            QMessageBox.information(
                self,
                "SnapMerge",
                "The merge has finished successfully.\n\n"
                f"Output:\n{output_path}",
            )

    def _on_merge_error(self, message: str, tb: str) -> None:
        """Called when MergeWorker emits an error."""
        self._set_ui_enabled(True)
        self.ui.merge_progress_bar.setVisible(False)
        self._cleanup_staging_dir()

        self.log(f"Error during merge: {message}", "error")
        if tb:
            self.log(tb, "error")

        QMessageBox.critical(
            self,
            "SnapMerge",
            f"An error occurred while merging:\n{message}",
        )
        
    def _on_merge_cancelled(self) -> None:
        """Called when the worker reports that the job was cancelled."""
        self.log("Merge cancelled by user.", "warning")

        self._set_ui_enabled(True)
        self.ui.merge_progress_bar.setVisible(False)

        self._cleanup_staging_dir()

        QMessageBox.information(
            self,
            "SnapMerge",
            "The merge operation was cancelled.",
        )

    def _on_thread_finished(self) -> None:
        """Reset thread/worker references when the QThread stops."""
        self._merge_thread = None
        self._merge_worker = None
        
    # --------------------- Doc Pages Worker Slots ---------------------
    def _on_doc_pages_status(self, message: str) -> None:
        self.log(message)

    def _on_doc_pages_progress(self, done: int, total: int) -> None:
        # Barra compartida mientras NO se esté ejecutando un merge
        self.ui.merge_progress_bar.setMaximum(total)
        self.ui.merge_progress_bar.setValue(done)

    def _on_doc_pages_finished(self, pages_map: dict) -> None:
        # Actualizar cache y tabla
        for path_str, pages in pages_map.items():
            p = Path(path_str)
            self._doc_pages_cache[p] = pages

        for row in range(self.table.rowCount()):
            path_item = self.table.item(row, 5)
            if path_item is None:
                continue
            row_path = Path(path_item.text()).resolve()
            if row_path in self._doc_pages_cache:
                pages = self._doc_pages_cache[row_path]
                pages_item = self.table.item(row, 4)
                if pages_item is None:
                    pages_item = QTableWidgetItem()
                    pages_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, 4, pages_item)
                pages_item.setText(str(pages))

        self._recalculate_total_pages()
        self.log(
            f"Finished reading Word page counts for {len(pages_map)} document(s).",
            "success",
        )

    def _on_doc_pages_error(self, message: str, tb: str) -> None:
        self.log(f"Error reading Word pages: {message}", "error")
        # opcional: escribir el traceback en el log o archivo


    # -------------------- Drag & Drop Events -------------------------
    def dragEnterEvent(self, event):  # type: ignore[override]
        """Trigger when something enters the window with drag."""
        mime = event.mimeData()
        if not mime.hasUrls():
            event.ignore()
            return

        # We accept the drag if at least one item is:
        # - a file with a supported extension, or
        # - a folder (we will process it in dropEvent)
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            p = Path(url.toLocalFile())
            if p.is_dir():
                event.acceptProposedAction()
                return
            if p.is_file() and p.suffix.lower() in self.settings.allowed_exts:
                event.acceptProposedAction()
                return

        event.ignore()

    def dropEvent(self, event):  # type: ignore[override]
        """Trigger when files/folders are dropped into the window."""
        mime = event.mimeData()
        if not mime.hasUrls():
            event.ignore()
            return

        recursive = self.ui.include_subfolders_chk.isChecked()
        all_paths: List[Path] = []
        roots: List[Path] = []  # source folders

        for url in mime.urls():
            if not url.isLocalFile():
                continue
            p = Path(url.toLocalFile())

            if p.is_dir():
                roots.append(p)
                all_paths.extend(self._collect_files_from_folder(p, recursive))

            elif p.is_file() and p.suffix.lower() in self.settings.allowed_exts:
                roots.append(p.parent)
                all_paths.append(p)

        if not all_paths:
            self.log("Dropped items, but none matched supported formats.", "warning")
            event.ignore()
            return

        # Remove duplicate files while maintaining order
        seen_files = set()
        unique_paths: List[Path] = []
        for p in all_paths:
            if p not in seen_files:
                seen_files.add(p)
                unique_paths.append(p)

        # Remove duplicate folders (for logging)
        unique_roots: List[Path] = []
        seen_roots = set()
        for r in roots:
            r_resolved = r.resolve()
            if r_resolved not in seen_roots:
                seen_roots.add(r_resolved)
                unique_roots.append(r_resolved)

        # Logs
        self.log(f"Added {len(unique_paths)} file(s) from drag & drop.")
        
        # Add to table
        self._append_files(unique_paths)

        if len(unique_roots) == 1:
            folder = unique_roots[0]
            self.log(f"Main folder: {folder.name}")
            self.log(f"Path: {folder}")
        elif len(unique_roots) > 1:
            self.log("Folders detected:")
            for r in unique_roots:
                self.log(f" - {r.name}  →  {r}")

        event.acceptProposedAction()

    # -------------------- Slots: toolbar buttons ---------------------

    def on_add_files(self) -> None:
        """Select one or more files and append them to the list."""
        start_dir = str(Path.home())
        filters = (
            "Supported files (*.pdf *.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.docx);;"
            "All files (*.*)"
        )
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select files to merge",
            start_dir,
            filters,
        )
        paths = [Path(f) for f in files]
        if paths:
            self._append_files(paths)

    def on_add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select folder to scan",
            str(Path.home()),
        )
        if not folder:
            return

        folder_path = Path(folder)
        self.log(f"Folder selected: {folder_path}")

        recursive = self.ui.include_subfolders_chk.isChecked()
        paths = self._collect_files_from_folder(folder_path, recursive)

        if not paths:
            self.log("No supported files found in this folder (or subfolders).", "warning")
            QMessageBox.information(
                self,
                "SnapMerge",
                "No supported files were found in the selected folder.",
            )
            return

        self._append_files(sorted(paths))
        scope = " and subfolders" if recursive else ""
        self.log(f"Added {len(paths)} file(s) from folder{scope}: {folder_path.name}")

    def on_remove_selected(self) -> None:
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)
        if rows:
            self._renumber_rows()
            self._recalculate_total_pages()
            self.log(f"Removed {len(rows)} row(s).")

    def on_clear_all(self) -> None:
        self.table.setRowCount(0)
        self._recalculate_total_pages()
        self.log("Cleared file list.")

    def move_row(self, direction: int) -> None:
        """Move currently selected row up (-1) or down (+1)."""
        row = self.table.currentRow()
        if row < 0:
            return

        target = row + direction
        if target < 0 or target >= self.table.rowCount():
            return

        for col in range(self.table.columnCount()):
            src_item = self.table.takeItem(row, col)
            dst_item = self.table.takeItem(target, col)
            self.table.setItem(row, col, dst_item)
            self.table.setItem(target, col, src_item)

        self.table.selectRow(target)
        self._renumber_rows()

    def sort_by_name(self) -> None:
        # Column 1 = Name
        self.table.sortItems(1)
        self._renumber_rows()
        self.log("Sorted by name.")

    def sort_by_type(self) -> None:
        # Column 2 = Type
        self.table.sortItems(2)
        self._renumber_rows()
        self.log("Sorted by type.")

    # -------------------- Bottom area -------------------------------

    def select_output_file(self) -> None:
        suggested = str(Path.home() / "output.pdf")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select destination PDF",
            suggested,
            "PDF files (*.pdf)",
        )
        if not file_path:
            return

        out_path = Path(file_path)
        if out_path.suffix.lower() != ".pdf":
            out_path = out_path.with_suffix(".pdf")

        self.ui.output_line.setText(str(out_path))

    def _collect_paths_from_table(self) -> List[Path]:
        """Return the file paths from the table in the current visible order."""
        paths: List[Path] = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 5)  # Path column
            if item is None:
                continue
            text = (item.text() or "").strip()
            if not text:
                continue
            paths.append(Path(text))
        return paths


    def on_merge_clicked(self) -> None:
        """Called when user clicks the Merge button.

        This validates the inputs, stages the selected files into a
        temporary folder in the same order as the table, and then
        starts a background QThread (MergeWorker) so the UI stays
        responsive while ``run_merge`` is executing.
        """
        if self.table.rowCount() == 0:
            QMessageBox.warning(
                self,
                "SnapMerge",
                "Please add at least one file to merge.",
            )
            return

        output_text = self.ui.output_line.text().strip()
        if not output_text:
            QMessageBox.warning(
                self,
                "SnapMerge",
                "Please choose a destination PDF file.",
            )
            return

        output_path = Path(output_text)
        # Respect the "Overwrite if exists" checkbox
        if output_path.exists() and not self.ui.overwrite_chk.isChecked():
            QMessageBox.warning(
                self,
                "SnapMerge",
                "The destination file already exists.\n"
                "Enable 'Overwrite if exists' if you want to replace it.",
            )
            return

        # Ensure parent directory exists
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self,
                "SnapMerge",
                f"Cannot create destination folder:\n{exc}",
            )
            return

        # Collect paths from the table in the visible order
        paths = self._collect_paths_from_table()
        if not paths:
            QMessageBox.warning(
                self,
                "SnapMerge",
                "No valid file paths were found in the table.",
            )
            return

        # If a merge is already running, don't start a new one.
        if self._merge_thread is not None and self._merge_thread.isRunning():
            QMessageBox.warning(
                self,
                "SnapMerge",
                "A merge operation is already running.",
            )
            return

        self._last_output_pdf = output_path

        self.log("Merge requested.")
        self.log(f"Destination: {output_path}")
        # self.log("Files to merge (in order):")
        # for p in paths:
        #     self.log(f"  - {p}")

        # Disable main UI while merging and show progress bar
        self._set_ui_enabled(False)
        self.ui.merge_progress_bar.setVisible(True)
        self.ui.merge_progress_bar.setValue(0)

        # Stage files into a temporary folder so that the pipeline can
        # work over a single input_dir while preserving the table order.
        try:
            staging_dir = Path(tempfile.mkdtemp(prefix="snapmerge_"))
            staged_count = 0

            for idx, src in enumerate(paths, start=1):
                if not src.exists():
                    self.log(f"Skipping missing file: {src}")
                    continue

                target_name = f"{idx:06d}_{src.name}"
                dst = staging_dir / target_name
                try:
                    shutil.copy2(src, dst)
                except Exception as copy_exc:  # noqa: BLE001
                    self.log(f"Error copying {src} → {dst}: {copy_exc}", "error")
                    continue
                staged_count += 1

            if staged_count == 0:
                shutil.rmtree(staging_dir, ignore_errors=True)
                QMessageBox.warning(
                    self,
                    "SnapMerge",
                    "No files could be staged for merging.\n"
                    "Please check that the source files still exist.",
                )
                self._set_ui_enabled(True)
                self.ui.merge_progress_bar.setVisible(False)
                return

            self.log(f"Staged {staged_count} file(s) for merge.")
            self._current_staging_dir = staging_dir

            job = MergeJob(
                input_dir=staging_dir,
                output_pdf=output_path,
                settings=self.settings,
                log_file=None,
            )
            self._start_merge_job(job)

        except Exception as exc:  # noqa: BLE001
            if 'staging_dir' in locals():
                shutil.rmtree(staging_dir, ignore_errors=True)
            self._set_ui_enabled(True)
            self.ui.merge_progress_bar.setVisible(False)
            self.log(f"Error preparing merge: {exc}")
            QMessageBox.critical(
                self,
                "SnapMerge",
                f"An error occurred while preparing the merge:\n{exc}",
            )

    def on_cancel_clicked(self) -> None:
        """Called when user clicks Cancel."""
        if self._merge_thread is not None and self._merge_thread.isRunning():
            # request confirmation
            reply = QMessageBox.question(
                self,
                "Cancel merge?",
                "Do you really want to cancel the merge process?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            self.log("Cancellation requested...", "warning")

            if self._merge_worker is not None:
                self._merge_worker.request_cancel()
            return

        # there is no running job
        self.log("Cancel clicked (no running job).")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
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
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
