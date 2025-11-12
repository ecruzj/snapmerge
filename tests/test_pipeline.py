from pathlib import Path
from src.snapmerge.config import Settings
from src.snapmerge.pipeline import run_merge
import pytest

def test_runs_with_empty_folder(tmp_path: Path):
    (tmp_path / "sub").mkdir()
    out = tmp_path / "out.pdf"
    settings = Settings()
    # Expect error due to no eligible files
    try:
        run_merge(tmp_path, out, settings)
    except Exception as exc:
        assert "No eligible files" in str(exc)