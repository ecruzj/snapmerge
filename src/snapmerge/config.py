from __future__ import annotations
import yaml
from pathlib import Path
from .types_job_types import JobSettings


DEFAULTS = {
    "include_subfolders": True,
    "image_margin_pts": 24,
    "sort_by": "name",
    "sort_desc": False,
    "allowed_images": [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"],
    "allowed_docs": [".docx", ".doc", ".odt", ".rtf"],
    "allowed_pdfs": [".pdf"],
    "max_image_dim_px": 4000,
    "workers": 4,
    }

class Settings:
    def __init__(self, data: dict | None = None):
        self._data = {**DEFAULTS, **(data or {})}
        
    @property
    def allowed_exts(self):
        """Return a unified set of all allowed file extensions."""
        return set(
            self._data["allowed_images"]
            + self._data["allowed_docs"]
            + self._data["allowed_pdfs"]
        )

    @classmethod
    def from_file(cls, path: Path) -> "Settings":
        if not path.exists():
            return cls()
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(data)

    def as_job(self, input_dir: Path, output_pdf: Path) -> JobSettings:
        return JobSettings(
        input_dir=input_dir,
        output_pdf=output_pdf,
        include_subfolders=bool(self._data["include_subfolders"]),
        sort_by=self._data["sort_by"],
        sort_desc=bool(self._data["sort_desc"]),
        image_margin_pts=int(self._data["image_margin_pts"]),
        max_image_dim_px=int(self._data["max_image_dim_px"]),
        workers=int(self._data["workers"]),
        )

    def get(self, key: str, default=None):
        return self._data.get(key, default)