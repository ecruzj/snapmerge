from __future__ import annotations

"""
Minimal SnapMerge Qt entrypoint using snap_merge_app.ui.

- Loads the UI via Qt Designer .ui file (no .py generation).
- Wires all toolbar buttons and fields.
- Implements basic list behaviour:
    * Add files
    * Add folder
    * Remove / Clear
    * Move up / Move down
    * Sort by name / type
- "Merge" button is currently a stub that just shows a message box.
  You can later plug your real merge pipeline here.

This file is intentionally self‑contained so you can drop it into
`snapmerge/src/snapmerge/app.py` and run:

    python -m snapmerge.app

or, if you prefer, directly:

    python src/snapmerge/app.py

(as long as you have PySide6 installed and the repo structure intact).
"""

import sys
from pathlib import Path
from typing import List

from PySide6.QtCore import Qt
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

# supported file extensions
SUPPORTED_EXTS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".bmp",
    ".tif", ".tiff", ".webp", ".docx"
}

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

        # Build UI
        self.ui = Ui_SnapMergeWindow()
        self.ui.setupUi(self)
        
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
        header.setStretchLastSection(True)   # the last column (Path) stretches at the end

        # Set initial column widths
        self.table.setColumnWidth(0, 20)   # #
        self.table.setColumnWidth(1, 200)  # Name
        self.table.setColumnWidth(2, 45)   # Type
        self.table.setColumnWidth(3, 45)   # Size
        self.table.setColumnWidth(4, 45)   # Pages
        
        # Set row height        
        vh = self.table.verticalHeader()
        vh.setDefaultSectionSize(20)
        vh.setMinimumSectionSize(18)
        
        self.table.setStyleSheet("""
            QTableView::item:selected {
                background-color: #cde8ff;  /* blue light */
                color: black;
            }""")

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.table.setDropIndicatorShown(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        # Columns: #, Name, Type, Size, Pages, Path
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["#", "Name", "Type", "Size", "Pages", "Path"]
        )
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def log(self, message: str) -> None:
        self.ui.log_text.append(message)

    # -------------------- File list handling -------------------------

    def _collect_files_from_folder(self, folder: Path, recursive: bool) -> List[Path]:
        """Returns the list of supported files in the folder (and subfolders if recursive=True)."""
        if recursive:
            candidates = folder.rglob("*")
        else:
            candidates = folder.iterdir()

        paths: List[Path] = [
            p for p in candidates
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
        ]
        return paths
    
    def _append_files(self, paths: List[Path]) -> None:
        """Append the given file paths to the table, skipping duplicates already present."""
        if not paths:
            return

        # 1) Routes that already exist in the table
        existing = set()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 5)  # columna Path
            if item is not None:
                existing.add(Path(item.text()).resolve())

        added_count = 0
        skipped_count = 0

        for path in paths:
            if not path.is_file():
                continue

            rp = path.resolve()
            if rp in existing:
                skipped_count += 1
                continue  # I was already on the table

            existing.add(rp)   # mark as viewed globally
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
            ext = path.suffix.lower().lstrip(".")
            type_item = QTableWidgetItem(ext)
            self.table.setItem(row, 2, type_item)

            # Column 3: Size
            try:
                size_bytes = path.stat().st_size
            except OSError:
                size_bytes = 0
            size_item = QTableWidgetItem(self._format_size(size_bytes))
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, size_item)

            # Column 4: Pages
            pages_item = QTableWidgetItem("")
            pages_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, pages_item)

            # Column 5: Full path
            path_item = QTableWidgetItem(str(rp))
            self.table.setItem(row, 5, path_item)

        self._renumber_rows()

        if added_count:
            self.log(f"Added {added_count} file(s).")
        if skipped_count:
            self.log(f"Skipped {skipped_count} duplicate file(s).")

    @staticmethod
    def _format_size(num_bytes: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if num_bytes < 1024.0:
                return f"{num_bytes:.0f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.0f} TB"

    def _renumber_rows(self) -> None:
        """Refresh the index (#) column after any structural change."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is None:
                item = QTableWidgetItem()
                self.table.setItem(row, 0, item)
            item.setText(str(row + 1))
            
            
    # -------------------- Drag & Drop Events -------------------------
    def dragEnterEvent(self, event):
        """It triggers when something enters the window with drag."""
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
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                event.acceptProposedAction()
                return

        event.ignore()
    
    def dropEvent(self, event):
        """It is triggered when files/folders are dropped into the window."""
        mime = event.mimeData()
        if not mime.hasUrls():
            event.ignore()
            return

        recursive = self.ui.include_subfolders_chk.isChecked()
        all_paths = []
        roots = []  # folders origen

        for url in mime.urls():
            if not url.isLocalFile():
                continue
            p = Path(url.toLocalFile())

            if p.is_dir():
                roots.append(p)
                all_paths.extend(self._collect_files_from_folder(p, recursive))

            elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                roots.append(p.parent)
                all_paths.append(p)

        if not all_paths:
            self.log("Dropped items, but none matched supported formats.")
            event.ignore()
            return

        # Remove duplicate files while maintaining order
        seen = set()
        unique_paths = []
        for p in all_paths:
            if p not in seen:
                seen.add(p)
                unique_paths.append(p)

        # Remove duplicate folders
        unique_roots = []
        seen = set()
        for r in roots:
            r = r.resolve()
            if r not in seen:
                seen.add(r)
                unique_roots.append(r)

        # Add to table
        self._append_files(unique_paths)

        # Logs
        self.log(f"Added {len(unique_paths)} file(s) from drag & drop.")
        
        if len(unique_roots) == 1:
            folder = unique_roots[0]
            self.log(f"Main folder: {folder.name}")
            self.log(f"Path: {folder}")
        elif len(unique_roots) > 1:
            self.log("Folders detected:")
            for r in unique_roots:
                self.log(f" - {r.name}  →  {r}")

        event.acceptProposedAction()

    # def dropEvent(self, event):
    #     """It is triggered when files/folders are dropped into the window."""
    #     mime = event.mimeData()
    #     if not mime.hasUrls():
    #         event.ignore()
    #         return

    #     recursive = self.ui.include_subfolders_chk.isChecked()
    #     all_paths: List[Path] = []
    #     roots = []   # List of source (parent) folders

    #     for url in mime.urls():
    #         if not url.isLocalFile():
    #             continue
    #         p = Path(url.toLocalFile())
    #         if p.is_dir():
    #             # Just like Add folder, respecting the Subfolders checkbox
    #             roots.append(p)
    #             all_paths.extend(self._collect_files_from_folder(p, recursive))
    #         elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
    #             all_paths.append(p)
    #             roots.append(p.parent)

    #     if not all_paths:
    #         self.log("Dropped items, but none matched supported formats.")
    #         event.ignore()
    #         return

    #     # We remove duplicates while maintaining order
    #     seen = set()
    #     unique_paths: List[Path] = []
    #     for p in all_paths:
    #         if p not in seen:
    #             seen.add(p)
    #             unique_paths.append(p)

    #     self._append_files(unique_paths)
    #     self.log(f"Added {len(unique_paths)} file(s) from drag & drop.")
    #     event.acceptProposedAction()

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
            self.log("No supported files found in this folder (or subfolders).")
            QMessageBox.information(
                self,
                "SnapMerge",
                "No supported files were found in the selected folder.",
            )
            return

        self._append_files(sorted(paths))
        scope = " and subfolders" if recursive else ""
        self.log(f"Added {len(paths)} file(s) from folder{scope}: {folder_path.name}")

    # def on_add_folder(self) -> None:
    #     """Select a folder and append eligible files from it."""
    #     folder = QFileDialog.getExistingDirectory(
    #         self,
    #         "Select folder to scan",
    #         str(Path.home()),
    #     )
    #     if not folder:
    #         return

    #     folder_path = Path(folder)
    #     exts = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".docx"}
        
    #     recursive = self.ui.include_subfolders_chk.isChecked()
        
    #     if recursive:
    #         candites = folder_path.rglob("*")
    #     else:
    #         candites = folder_path.iterdir()

    #     paths: List[Path] = [
    #         p for p in candites
    #         if p.is_file() and p.suffix.lower() in exts
    #     ]
    #     if not paths:
    #         QMessageBox.information(
    #             self,
    #             "SnapMerge",
    #             "No supported files were found in the selected folder.",
    #         )
    #         return

    #     self._append_files(sorted(paths))
    #     scope = "and subfolders" if recursive else ""
    #     self.log(f"Added {len(paths)} file(s) from folder {scope} in: {folder_path.name}")

    def on_remove_selected(self) -> None:
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)
        if rows:
            self._renumber_rows()
            self.log(f"Removed {len(rows)} row(s).")

    def on_clear_all(self) -> None:
        self.table.setRowCount(0)
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

    def on_merge_clicked(self) -> None:
        """Called when user clicks the Merge button.

        For now this is a stub that only validates fields and shows a
        message. You can later plug your real merge pipeline here.
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
        if output_path.exists() and not self.ui.overwrite_chk.isChecked():
            QMessageBox.warning(
                self,
                "SnapMerge",
                "The destination file already exists.\n"
                "Enable 'Overwrite if exists' if you want to replace it.",
            )
            return

        # At this point inputs are valid.
        # Later you can extract the ordered list of paths with:
        #   paths = [Path(self.table.item(r, 5).text()) for r in range(self.table.rowCount())]
        paths = [Path(self.table.item(r, 5).text()) for r in range(self.table.rowCount())]

        self.log("Merge requested.")
        self.log(f"Destination: {output_path}")
        self.log("Files to merge (in order):")
        for p in paths:
            self.log(f"  - {p}")

        QMessageBox.information(
            self,
            "SnapMerge",
            "UI is working correctly.\n\n"
            "This demo build does NOT perform the actual merge yet.\n"
            "You can now wire your existing pipeline.run_merge() here.",
        )

    def on_cancel_clicked(self) -> None:
        # No background job yet; just log for now.
        self.log("Cancel clicked (no running job).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    app = QApplication(sys.argv)
    window = SnapMergeApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
