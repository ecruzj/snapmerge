from __future__ import annotations
from pathlib import Path
from typing import Callable, Iterable

from snapmerge.services.eml_to_pdf import eml_to_pdf
from snapmerge.services.file_names import get_original_file_name
from .config import Settings
from .logging_setup import get_logger
from .types_job_types import JobSettings
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
    status_cb: Callable[[str], None] | None = None,
    merge_start_cb: Callable[[int], None] | None = None,
    merge_progress_cb: Callable[[int, int], None] | None = None,
    log_file: Path | None = None,
) -> dict:
    """Run the end-to-end job from a folder (modo clásico)."""
    logger = get_logger(logfile=log_file)
    job: JobSettings = settings.as_job(input_dir, output_pdf)

    allowed = (
        (settings.get("allowed_pdfs") or [])
        + (settings.get("allowed_images") or [])
        + (settings.get("allowed_docs") or [])
        + (settings.get("allowed_emails") or [])
    )

    files = list(discover_files(job.input_dir, job.include_subfolders))
    files = filter_and_sort(files, allowed, job.sort_by, job.sort_desc)

    return _run_core_from_files(
        files,
        job,
        settings,
        logger,
        progress_cb=progress_cb,
        status_cb=status_cb,
        merge_start_cb=merge_start_cb,
        merge_progress_cb=merge_progress_cb,
    )

def _run_core_from_files(
    files: list[Path],
    job: JobSettings,
    settings: Settings,
    logger,
    progress_cb: Callable | None = None,
    status_cb: Callable[[str], None] | None = None,
    merge_start_cb: Callable[[int], None] | None = None,
    merge_progress_cb: Callable[[int, int], None] | None = None,
) -> dict:
    """Processes a list of already discovered and sorted files.

    This function contains ALL the logic for:
    - converting images/docx to PDF
    - accumulating PDFs to merge
    - invoking merge_pdfs
    - building the final report
    """

    allowed_pdfs = settings.get("allowed_pdfs") or []
    allowed_images = settings.get("allowed_images") or []
    allowed_docs = settings.get("allowed_docs") or []
    allowed_emails = settings.get("allowed_emails") or []

    to_merge: list[Path] = []
    skipped: list[Path] = []
    converted: list[Path] = []

    total = len(files)
    done = 0

    if status_cb:
        status_cb(f"Discovered {total} file(s) to process.")

    with TempDir() as tmp:
        for idx, f in enumerate(files, start=1):
            if status_cb:
                original_name = get_original_file_name(f.name)
                status_cb(f"Processing ({idx}/{total}): {original_name}")

            ext = f.suffix.lower()
            try:
                if ext in allowed_pdfs:
                    to_merge.append(f)

                elif ext in allowed_images:
                    outp = tmp.path / (f.stem + ".pdf")
                    image_to_pdf(f, outp, job.image_margin_pts, job.max_image_dim_px)
                    converted.append(outp)
                    to_merge.append(outp)

                elif ext in allowed_docs:
                    outp = tmp.path / (f.stem + ".pdf")
                    if status_cb:
                        status_cb(f"Converting Word → PDF: {original_name}")
                    ok = docx_to_pdf(f, outp)
                    if ok and outp.exists():
                        converted.append(outp)
                        to_merge.append(outp)
                        if status_cb:
                            status_cb(f"Converted: {outp.name}")
                    else:
                        if status_cb:
                            status_cb(f"Can't Convert {original_name} to PDF")
                        logger.warning("Word not available or output missing. Skipping %s", f)
                        skipped.append(f)
                
                elif ext in allowed_emails:
                    outp = tmp.path / (f.stem + ".eml")
                    if status_cb:
                        status_cb(f"Converting Email → EML: {original_name}")
                    eml_to_pdf(f, outp)
                    converted.append(outp)
                    to_merge.append(outp)
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

        if status_cb:
            status_cb("Finalizing (writing PDF…)")
        if merge_start_cb:
            merge_start_cb(len(to_merge))

        merge_pdfs(
            to_merge,
            job.output_pdf,
            status_cb=status_cb,
            progress_cb=merge_progress_cb,
        )

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

def run_manual_merge(
    files: Iterable[Path],
    output_pdf: Path,
    settings: Settings,
    progress_cb: Callable | None = None,
    status_cb: Callable[[str], None] | None = None,
    merge_start_cb: Callable[[int], None] | None = None,
    merge_progress_cb: Callable[[int, int], None] | None = None,
    log_file: Path | None = None,
) -> dict:
    """
    Perform the merge using an explicit file list (already defined order),
    ideal for SnapMerge's new UI.
    """
    logger = get_logger(logfile=log_file)

    # convert to a list of Paths (in case strings are involved)
    file_list = [Path(f) for f in files]

    # The input_dir here is for informational purposes only (for reporting/logs).
    # You can use Path.cwd() or the parent of the first file.
    base_dir = file_list[0].parent if file_list else Path.cwd()
    job: JobSettings = settings.as_job(base_dir, output_pdf)

    return _run_core_from_files(
        file_list,
        job,
        settings,
        logger,
        progress_cb=progress_cb,
        status_cb=status_cb,
        merge_start_cb=merge_start_cb,
        merge_progress_cb=merge_progress_cb,
    )