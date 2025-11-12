from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from pathlib import Path
import threading

# Importa la clase generada automáticamente
from .ui.snap_merge_app import Ui_SnapMergeWindow
from .config import Settings
from .pipeline import run_merge


class SnapMergeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_SnapMergeWindow()
        self.ui.setupUi(self)
        self.settings = Settings.from_file(Path(__file__).resolve().parents[1] / "config.yaml")

        # Conectar botones del UI con funciones
        self.ui.browse_input_btn.clicked.connect(self.select_input_folder)
        self.ui.browse_output_btn.clicked.connect(self.select_output_file)
        self.ui.run_btn.clicked.connect(self.run_merge)
        self.ui.cancel_btn.clicked.connect(self.cancel_merge)

        self._cancel_flag = False
        self.ui.log_text.append("Ready.")

    # --------------------- Handlers ---------------------
    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select input folder")
        if folder:
            self.ui.input_line.setText(folder)

    def select_output_file(self):
        file, _ = QFileDialog.getSaveFileName(self, "Save output PDF", "", "PDF Files (*.pdf)")
        if file:
            self.ui.output_line.setText(file)

    def cancel_merge(self):
        self._cancel_flag = True
        self.ui.log_text.append("Cancellation requested...")

    def run_merge(self):
        input_dir = Path(self.ui.input_line.text()).expanduser()
        output_pdf = Path(self.ui.output_line.text()).expanduser()

        if not input_dir.exists():
            QMessageBox.critical(self, "SnapMerge", "Invalid input folder.")
            return

        self._cancel_flag = False
        self.ui.progress_bar.setValue(0)
        self.ui.log_text.clear()
        self.ui.log_text.append(f"Starting merge for folder: {input_dir}")

        def progress_cb(done, total):
            if self._cancel_flag:
                raise RuntimeError("Cancelled by user")
            pct = int(done * 100 / total)
            self.ui.progress_bar.setValue(pct)
            self.ui.log_text.append(f"Progress: {done}/{total} ({pct}%)")

        def worker():
            try:
                report = run_merge(input_dir, output_pdf, self.settings, progress_cb=progress_cb)
                self.ui.log_text.append("Done! Output: " + str(report["output"]))
                QMessageBox.information(self, "SnapMerge", f"Merge complete!\\n\\nOutput: {output_pdf}")
            except Exception as e:
                self.ui.log_text.append("Error: " + str(e))
                QMessageBox.critical(self, "SnapMerge", str(e))

        threading.Thread(target=worker, daemon=True).start()


def main():
    app = QApplication([])
    window = SnapMergeApp()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
