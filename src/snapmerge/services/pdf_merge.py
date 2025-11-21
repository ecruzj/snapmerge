from __future__ import annotations
from pathlib import Path
from typing import Callable, Optional
from PyPDF2 import PdfMerger

from snapmerge.services.file_names import get_original_file_name

def merge_pdfs(inputs: list[Path], out_pdf: Path, 
               status_cb: Callable[[str], None] | None = None,
               progress_cb: Callable[[int, int], None] | None = None) -> None:
    """
    Merge PDFs with optional per-file progress callback.
    progress_cb(done, total) is called for each appended PDF.
    """
    merger = PdfMerger()
    try:
        total = len(inputs)
        done = 0
        for p in inputs:
            if status_cb:
                original_name = get_original_file_name(p.name)
                status_cb(f"Merging: {original_name}")
            try:                               
                merger.append(str(p))        
            except Exception as e:
                # Skip problematic file but continue
                if status_cb:
                    status_cb(f"Skipping (unreadable/encrypted): {original_name} — {e}")
            finally:
                done += 1
                if progress_cb:
                    progress_cb(done, total)
                    
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        with out_pdf.open("wb") as fh:
            merger.write(fh)
    finally:
        merger.close()