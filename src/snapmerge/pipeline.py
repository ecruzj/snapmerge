from __future__ import annotations
from pathlib import Path
from typing import Callable, Iterable, List, Dict, Any
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
    """Procesa una lista de archivos ya descubiertos y ordenados.

    Esta función contiene TODA la lógica de:
    - convertir imágenes/docx a PDF
    - acumular PDFs a mergear
    - invocar merge_pdfs
    - construir el reporte final
    """

    allowed_pdfs = settings.get("allowed_pdfs") or []
    allowed_images = settings.get("allowed_images") or []
    allowed_docs = settings.get("allowed_docs") or []

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
                status_cb(f"Processing ({idx}/{total}): {f.name}")

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
                        status_cb(f"Converting Word → PDF: {f.name}")
                    ok = docx_to_pdf(f, outp)
                    if ok and outp.exists():
                        converted.append(outp)
                        to_merge.append(outp)
                        if status_cb:
                            status_cb(f"Converted: {outp.name}")
                    else:
                        if status_cb:
                            status_cb(f"Can't Convert {f.name} to PDF")
                        logger.warning("Word not available or output missing. Skipping %s", f)
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
    Ejecuta el merge usando una lista explícita de archivos (orden YA definido),
    ideal para el nuevo UI de SnapMerge.
    """
    logger = get_logger(logfile=log_file)

    # Convertimos a lista de Paths (por si vienen strings)
    file_list = [Path(f) for f in files]

    # El input_dir aquí es solo informativo (para el reporte/logs).
    # Puedes usar Path.cwd() o el padre del primer archivo.
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
