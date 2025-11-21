from __future__ import annotations

"""Background worker for running the SnapMerge pipeline in a QThread.

This module isolates the long‑running merge job so the Qt UI can stay
responsive.  It does **not** know anything about widgets; it only talks
in terms of paths, settings and Qt signals.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtCore import QObject, Signal, Slot

from ..config import Settings
from ..pipeline import run_merge

class MergeCancelledError(Exception):
    """Raised when the user requests cancellation of the merge job."""
    pass

@dataclass(slots=True)
class MergeJob:
    """Small data container with everything the worker needs.

    - ``input_dir``  : Folder that already contains the *ordered* files
                       to be merged (usually a staging/temp directory
                       prepared by the UI).
    - ``output_pdf`` : Final PDF path selected by the user.
    - ``settings``   : Settings instance (usually loaded from config.yaml).
    - ``log_file``   : Optional path where the pipeline will write a log.
    """

    input_dir: Path
    output_pdf: Path
    settings: Settings
    log_file: Optional[Path] = None


class MergeWorker(QObject):
    """QObject that runs ``run_merge`` in a background thread.

    You create it in the main window, move it to a ``QThread`` and
    connect its signals to update the progress bar, log widget, etc.
    """

    # High‑level status text (shown in the log area)
    status = Signal(str)

    # File discovery / conversion progress: done, total
    progress = Signal(int, int)

    # Called once just before starting the final PDF merge.
    merge_start = Signal(int)  # total files to merge

    # Merge progress: done, total
    merge_progress = Signal(int, int)

    # Emitted when the job finishes successfully
    finished = Signal(dict)

    # Emitted on error: human message, full traceback as string
    error = Signal(str, str)
    
    # Emitted when the job is cancelled by the user
    cancelled = Signal()

    def __init__(self, job: MergeJob, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._job = job
        self._cancel_requested = False

    # --------------------------- internal callbacks -----------------------

    def _progress_cb(self, done: int, total: int) -> None:
        self._check_cancel()
        self.progress.emit(done, total)

    def _status_cb(self, message: str) -> None:
        self._check_cancel()
        self.status.emit(message)

    def _merge_start_cb(self, total: int) -> None:
        self._check_cancel()
        self.merge_start.emit(total)

    def _merge_progress_cb(self, done: int, total: int) -> None:
        self._check_cancel()
        self.merge_progress.emit(done, total)
        
    # --------------------------- cancellation API -------------------------
    def request_cancel(self):
        self._cancel_requested = True
        
    def _check_cancel(self) -> None:
        """Raise if cancellation was requested.

        This is called from the callbacks that run inside `run_merge`,
        so raising here aborts the pipeline cleanly and bubbles back to
        `MergeWorker.run`.
        """
        if self._cancel_requested:
            raise MergeCancelledError("Merge cancelled by user.")

    # ------------------------------- API ----------------------------------

    @Slot()
    def run(self) -> None:
        """Entry‑point that will be invoked from the QThread.

        Any exception is caught and converted into an ``error`` signal,
        so the GUI thread can decide how to show it (message box, log, etc.).
        """
        import traceback

        try:
            report: Dict[str, Any] = run_merge(
                input_dir=self._job.input_dir,
                output_pdf=self._job.output_pdf,
                settings=self._job.settings,
                progress_cb=self._progress_cb,
                status_cb=self._status_cb,
                merge_start_cb=self._merge_start_cb,
                merge_progress_cb=self._merge_progress_cb,
                log_file=self._job.log_file,
            )
        except MergeCancelledError:
            # "Normal" cancellation is not a user or system error
            self.status.emit("Merge cancelled by user.")
            self.cancelled.emit()
        except Exception as exc:  # noqa: BLE001 – we really want to catch *everything*
            tb = traceback.format_exc()
            # First emit a human message, then the traceback for logging
            self.error.emit(str(exc), tb)
        else:
            self.finished.emit(report)
