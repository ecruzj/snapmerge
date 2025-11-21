from __future__ import annotations
import re

def get_original_file_name(filename: str) -> str:
    # Remove a pattern like: 000123_
    return re.sub(r"^\d{6}_", "", filename)