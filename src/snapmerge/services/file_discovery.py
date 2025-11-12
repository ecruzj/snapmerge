from __future__ import annotations
from pathlib import Path
from typing import Iterable, List
import os

def discover_files(root: Path, include_subfolders: bool) -> Iterable[Path]:
    """Yield all files under root (optionally including subfolders)."""
    if include_subfolders:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                yield Path(dirpath) / fn
    else:
        for p in root.iterdir():
            if p.is_file():
                yield p

def filter_and_sort(
files: Iterable[Path],
allowed_exts: List[str],
sort_by: str = "name",
desc: bool = False,
) -> list[Path]:
    """Filter by extension, then sort by name/created/modified."""
    allowed = {e.lower() for e in allowed_exts}
    pool = [p for p in files if p.suffix.lower() in allowed]

    if sort_by == "name":
        key = lambda p: p.name.lower()
    elif sort_by == "created":
        key = lambda p: p.stat().st_ctime
    elif sort_by == "modified":
        key = lambda p: p.stat().st_mtime
    else:
        key = lambda p: p.name.lower()  

    return sorted(pool, key=key, reverse=desc)