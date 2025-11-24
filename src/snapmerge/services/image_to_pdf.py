from __future__ import annotations
from pathlib import Path
from PIL import Image

# --- Page size---
PAGE_DPI = 300                # PDF resolution
PAGE_WIDTH_IN = 8.5           # Letter
PAGE_HEIGHT_IN = 11.0

PAGE_WIDTH_PX = int(PAGE_WIDTH_IN * PAGE_DPI)
PAGE_HEIGHT_PX = int(PAGE_HEIGHT_IN * PAGE_DPI)

def _downscale(img: Image.Image, max_dim: int) -> Image.Image:
    """Downscale image if its longest side exceeds max_dim (in pixels)."""
    w, h = img.size
    if max(w, h) <= max_dim:
        return img

    ratio = max_dim / float(max(w, h))
    new_size = (int(w * ratio), int(h * ratio))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def image_to_pdf(
    image_path: Path,
    out_pdf: Path,
    margin_pts: int = 24,
    max_dim: int = 4000,
) -> None:
    """
    Convert an image to a single-page, fixed-size (Letter) PDF,
    maintaining the image aspect ratio and including margins.
    - margin_pts: margin in points (1 pt = 1 px at 300 dpi).
    - max_dim: maximum size of the longest side of the image in pixels
    BEFORE placing it on the page (to avoid 10k px images).
    """
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        img = _downscale(img, max_dim)

        page_w, page_h = PAGE_WIDTH_PX, PAGE_HEIGHT_PX
        margin = max(int(margin_pts), 0)

        # Available area within the margins
        inner_w = page_w - 2 * margin
        inner_h = page_h - 2 * margin
        if inner_w <= 0 or inner_h <= 0:
            # Excessive margin, no usable space: we remove margin
            inner_w, inner_h = page_w, page_h
            margin = 0

        img_w, img_h = img.size

        # scale actor so that the image fits within the usable area.
        # We do not upscale (min(..., 1.0)).
        scale = min(inner_w / img_w, inner_h / img_h, 1.0)
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)

        if scale < 1.0:
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            img_w, img_h = img.size  # update size

        # We created the white "sheet" in Letter size
        canvas = Image.new("RGB", (page_w, page_h), (255, 255, 255))

        # We centered the image within the useful rectangle
        offset_x = margin + (inner_w - img_w) // 2
        offset_y = margin + (inner_h - img_h) // 2
        canvas.paste(img, (int(offset_x), int(offset_y)))

        # save as pdf with specified resolution
        canvas.save(out_pdf, "PDF", resolution=PAGE_DPI)