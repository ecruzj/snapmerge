from __future__ import annotations
from pathlib import Path
import tempfile
import shutil

class TempDir:
    def __init__(self, prefix: str = "snapmerge_"):
        self._path = Path(tempfile.mkdtemp(prefix=prefix))

    @property
    def path(self) -> Path:
        return self._path

    def cleanup(self) -> None:
        if self._path.exists():
            shutil.rmtree(self._path, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.cleanup()