from __future__ import annotations
from pathlib import Path
from typing import Callable, Iterable, List, Dict, Any
from .config import Settings
from .logging_setup import get_logger
from .types import JobSettings
from .services.file_discovery import discover_files, filter_and_sort
from .services.image_to_pdf import image_to_pdf
from .services.docx_to_pdf import docx_to_pdf, DocxConversionError
from .services.pdf_merge import merge_pdfs
from .services.temp_utils import TempDir

def run_merge(
    input_dir: Path,
    output_pdf: Path,
    settings: Settings,
    progress_cb: Callable | None = None,
    log_file: Path | None = None,
) -> dict:
    """Run the end-to-end job. Returns a report dict with stats."""
    logger = get_logger(logfile=log_file)
    job: JobSettings = settings.as_job(input_dir, output_pdf)

    allowed = (
        (settings.get("allowed_pdfs") or [])
        + (settings.get("allowed_images") or [])
        + (settings.get("allowed_docs") or [])
    )

    files = list(discover_files(job.input_dir, job.include_subfolders))
    files = filter_and_sort(files, allowed, job.sort_by, job.sort_desc)

    to_merge: list[Path] = []
    skipped: list[Path] = []
    converted: list[Path] = []

    total = len(files)
    done = 0

    with TempDir() as tmp:
        for f in files:
            ext = f.suffix.lower()
            try:
                if ext in (settings.get("allowed_pdfs") or []):
                    to_merge.append(f)
                elif ext in (settings.get("allowed_images") or []):
                    outp = tmp.path / (f.stem + ".pdf")
                    image_to_pdf(f, outp, job.image_margin_pts, job.max_image_dim_px)
                    converted.append(outp)
                    to_merge.append(outp)
                elif ext in (settings.get("allowed_docs") or []):
                    outp = tmp.path / (f.stem + ".pdf")
                    ok = docx_to_pdf(f, outp)
                    if ok:
                        converted.append(outp)
                        to_merge.append(outp)
                    else:
                        logger.warning("No Word/LibreOffice available. Skipping %s", f)
                        skipped.append(f)
                else:
                    skipped.append(f)
            except DocxConversionError as dce:
                logger.error("DOCX conversion error for %s: %s", f, dce)
                skipped.append(f)
            except Exception as exc:
                logger.error("Processing error for %s: %s", f, exc)
                skipped.append(f)
            finally:
                done += 1
                if progress_cb:
                    progress_cb(done, total)

        if not to_merge:
            raise RuntimeError("No eligible files found to merge.")

        merge_pdfs(to_merge, job.output_pdf)


    report = {
        "input": str(job.input_dir),
        "output": str(job.output_pdf),
        "total_found": total,
        "merged_count": len(to_merge),
        "converted_count": len(converted),
        "skipped_count": len(skipped),
        "skipped": [str(p) for p in skipped],
    }
    
    logger.info("Merge complete: %s", report)
    return report