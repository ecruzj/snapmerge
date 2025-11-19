# SnapMerge

Select a folder and merge all eligible files into a single PDF:
- **PDF** files are appended as-is.
- **Images** (PNG/JPG/BMP/TIFF/WEBP) are converted to one-page PDFs with margins.
- **Word** (.docx) files are converted to PDF (requires Microsoft Word via `docx2pdf` or LibreOffice headless).

Excel files are **not** supported in v1.

## Install
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt # or: pip install -e .[dev]

## Run the App
```bash
python -m snapmerge.app_qt