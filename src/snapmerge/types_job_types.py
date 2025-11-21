from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SortBy = Literal["name", "created", "modified"]

@dataclass
class JobSettings:
    input_dir: Path
    output_pdf: Path
    include_subfolders: bool
    sort_by: SortBy
    sort_desc: bool
    image_margin_pts: int
    max_image_dim_px: int
    workers: int
    word_page_count: bool