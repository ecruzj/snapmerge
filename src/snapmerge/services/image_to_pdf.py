from __future__ import annotations
from pathlib import Path
from PIL import Image

def _downscale(img: Image.Image, max_dim: int) -> Image.Image:
    """Downscale image in-place if larger than max_dim (either axis)."""
    w, h = img.size
    if max(w, h) <= max_dim:
        return img
    
    ratio = max_dim / float(max(w, h))
    new_size = (int(w * ratio), int(h * ratio))
    return img.resize(new_size, Image.Resampling.LANCZOS)

def image_to_pdf(image_path: Path, out_pdf: Path, margin_pts: int = 24, max_dim: int = 4000) -> None:
    """Convert a single image into a single-page PDF with margin and aspect preserved."""
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        img = _downscale(img, max_dim)
        # Save as PDF: Pillow generates a page sized to the image. Margin can be simulated via
        # expanding the canvas (white background) before saving.
        if margin_pts > 0:
            # Pillow uses pixels; assume 72 DPI to interpret points (1pt = 1px at 72dpi)
            margin_px = int(margin_pts) # at 72 dpi approximation
            w, h = img.size
            canvas = Image.new("RGB", (w + 2 * margin_px, h + 2 * margin_px), (255, 255, 255))
            canvas.paste(img, (margin_px, margin_px))
            canvas.save(out_pdf, "PDF", resolution=72.0)
        else:
            img.save(out_pdf, "PDF", resolution=72.0)