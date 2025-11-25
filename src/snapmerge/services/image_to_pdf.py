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
    longest = max(w, h)
    if longest <= max_dim:
        return img

    ratio = max_dim / float(longest)
    new_size = (int(w * ratio), int(h * ratio))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def image_to_pdf(
    image_path: Path,
    out_pdf: Path,
    margin_pts: int = 24,
    max_dim: int = 4000,
    max_upscale: float = 3.0,   # limit of how much we can enlarge
) -> None:
    """
    Convert an image to a single-page, fixed-size (Letter) PDF.

    - Maintains aspect ratio.
    - Preserves margins.
    - Reduces the size of very large images (max_dim).
    - Allows upscaling of small images up to max_upscale times,
      but never larger than the usable area of ​​the page.
    """
    with Image.open(image_path) as img:
        img = img.convert("RGB")

        # 1) Reduce absurdly large images first.
        if max_dim > 0:
            img = _downscale(img, max_dim)

        page_w, page_h = PAGE_WIDTH_PX, PAGE_HEIGHT_PX
        margin = max(int(margin_pts), 0)

        # 2) Usable area within the margins
        inner_w = page_w - 2 * margin
        inner_h = page_h - 2 * margin
        if inner_w <= 0 or inner_h <= 0:
            # If the margin got out of hand, we ignore it.
            inner_w, inner_h = page_w, page_h
            margin = 0

        img_w, img_h = img.size

        # 3) Scale factor to fit within the usable rectangle
        scale_to_fit = min(inner_w / img_w, inner_h / img_h)

        # 4) Choose final scale:
        # - if < 1 → downscale
        # - if > 1 → upscale, but limited by max_upscale
        if scale_to_fit < 1.0:
            scale = scale_to_fit
        else:
            scale = min(scale_to_fit, max_upscale)

        # 5) Apply scaling if necessary
        if abs(scale - 1.0) > 1e-3:
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            img_w, img_h = img.size

        # 6) Create a letter-size "sheet" and center the image
        canvas = Image.new("RGB", (page_w, page_h), (255, 255, 255))
        offset_x = margin + (inner_w - img_w) // 2
        offset_y = margin + (inner_h - img_h) // 2
        canvas.paste(img, (int(offset_x), int(offset_y)))

        # 7) Save as PDF
        canvas.save(out_pdf, "PDF", resolution=PAGE_DPI)