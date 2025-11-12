from __future__ import annotations
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from .config import Settings
from .pipeline import run_merge
from .logging_setup import get_logger
from .ui.widgets import LogConsole

class SnapMergeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SnapMerge non-Qt")
        self.geometry("760x540")
        self.resizable(True, True)

        self.settings = Settings.from_file(Path(__file__).resolve().parents[2] / "config.yaml")
        self.logger = get_logger()

        self.input_dir = tk.StringVar()
        self.output_pdf = tk.StringVar(value=str(Path.home() / "Desktop" / "merged.pdf"))
        self.include_sub = tk.BooleanVar(value=self.settings.get("include_subfolders", True))
        self.sort_by = tk.StringVar(value=str(self.settings.get("sort_by", "name")))
        self.sort_desc = tk.BooleanVar(value=bool(self.settings.get("sort_desc", False)))

        self._cancel_flag = False

        self._build_ui()

    def _build_ui(self) -> None:
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        # Input folder
        row1 = ttk.Frame(frm)
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="Input folder:").pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.input_dir, width=70).pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        ttk.Button(row1, text="Browse...", command=self._choose_folder).pack(side=tk.LEFT)

        # Output PDF
        row2 = ttk.Frame(frm)
        row2.pack(fill=tk.X, pady=5)
        ttk.Label(row2, text="Output PDF:").pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.output_pdf, width=70).pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        ttk.Button(row2, text="Save as...", command=self._choose_output).pack(side=tk.LEFT)

        # Options
        row3 = ttk.Frame(frm)
        row3.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(row3, text="Include subfolders", variable=self.include_sub).pack(side=tk.LEFT)
        ttk.Label(row3, text="Sort by:").pack(side=tk.LEFT, padx=(12, 4))
        cmb = ttk.Combobox(row3, textvariable=self.sort_by, values=["name", "created", "modified"], width=12)
        cmb.state(["readonly"])
        cmb.pack(side=tk.LEFT)
        ttk.Checkbutton(row3, text="Descending", variable=self.sort_desc).pack(side=tk.LEFT, padx=8)

        # Progress
        row4 = ttk.Frame(frm)
        row4.pack(fill=tk.X, pady=5)
        self.pbar = ttk.Progressbar(row4, length=300, mode="determinate")
        self.pbar.pack(side=tk.LEFT)
        ttk.Button(row4, text="Generate PDF", command=self._on_generate).pack(side=tk.LEFT, padx=8)
        ttk.Button(row4, text="Cancel", command=self._on_cancel).pack(side=tk.LEFT)

        # Log console
        self.console = LogConsole(frm, height=16)
        self.console.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.console.append("Ready.")

    def _choose_folder(self) -> None:
        d = filedialog.askdirectory()
        if d:
            self.input_dir.set(d)

    def _choose_output(self) -> None:
        f = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if f:
            self.output_pdf.set(f)

    def _on_cancel(self) -> None:
        self._cancel_flag = True

    def _on_generate(self) -> None:
        in_dir = Path(self.input_dir.get()).expanduser()
        out_pdf = Path(self.output_pdf.get()).expanduser()
        
        if not in_dir.exists() or not in_dir.is_dir():
            messagebox.showerror("Error", "Please select a valid input folder.")
            return

        self.console.append(f"Starting… Folder: {in_dir}")
        self._cancel_flag = False

        # Start worker thread to avoid blocking UI
        th = threading.Thread(target=self._worker, args=(in_dir, out_pdf), daemon=True)
        th.start()

    def _progress(self, done: int, total: int) -> None:
        if total <= 0:
            return
        pct = int(done * 100 / total)
        self.pbar["value"] = pct
        self.console.append(f"Progress: {done}/{total} ({pct}%)")
        self.update_idletasks()

    def _worker(self, in_dir: Path, out_pdf: Path) -> None:
        try:
            report = run_merge(
            input_dir=in_dir,
            output_pdf=out_pdf,
            settings=self.settings,
            progress_cb=self._progress,
            )
            self.console.append("Done! Output: " + str(report["output"]))
            messagebox.showinfo("SnapMerge", "Merge complete!\n\nOutput: " + str(out_pdf))
        except Exception as exc:
            self.console.append("Error: " + str(exc))
            messagebox.showerror("SnapMerge", str(exc))

def main():
    app = SnapMergeApp()
    app.mainloop()

if __name__ == "__main__":
    main()