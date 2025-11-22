from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

import re
from email import policy
from email.parser import BytesParser
from html import unescape

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics


@dataclass
class EmlToPdfResult:
    """Result of converting a .eml file into a PDF."""
    input_eml: Path
    output_pdf: Path
    pages: int


# ---------------------------------------------------------------------------
# E-mail parsing helpers
# ---------------------------------------------------------------------------

def _load_email(path: Path):
    with path.open("rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    return msg


def _decode_part(part) -> str:
    """Return decoded text for a MIME part."""
    data = part.get_payload(decode=True) or b""
    charset = part.get_content_charset() or "utf-8"
    return data.decode(charset, errors="replace")


def _html_to_text(html: str) -> str:
    """Very small HTML → plain text converter, enough for email bodies."""
    text = unescape(html)

    # Remove script and style blocks
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", text)

    # <br> y </p> -> saltos de línea
    text = re.sub(r"(?i)<\s*br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n\n", text)

    # Quitar el resto de etiquetas
    text = re.sub(r"(?s)<[^>]+>", "", text)

    # Normalizar saltos de línea
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _extract_best_body(msg) -> str:
    """
    Return text body for the email.

    Preferencias:
      1) text/plain
      2) text/html convertido a texto
    """
    if msg.is_multipart():
        # Primero text/plain
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return _decode_part(part)

        # Luego text/html
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                raw = _decode_part(part)
                return _html_to_text(raw)

        return ""
    else:
        ctype = msg.get_content_type()
        raw = _decode_part(msg)
        if ctype == "text/html":
            return _html_to_text(raw)
        return raw


def _format_header_line(label: str, value: Optional[str]) -> str:
    if not value:
        return ""
    return f"{label}: {value.strip()}"


def _build_header_block(msg) -> str:
    """Build a header section similar to Outlook's print layout."""
    headers: List[str] = []

    headers.append(_format_header_line("From", msg.get("From")))
    headers.append(_format_header_line("Sent", msg.get("Date")))
    headers.append(_format_header_line("To", msg.get("To")))
    cc_line = _format_header_line("Cc", msg.get("Cc"))
    if cc_line:
        headers.append(cc_line)
    headers.append(_format_header_line("Subject", msg.get("Subject")))

    # Eliminar líneas vacías
    headers = [h for h in headers if h]

    if not headers:
        return ""

    block = "\n".join(headers)
    # Regla horizontal tipo Outlook
    block += "\n" + ("-" * 72) + "\n"
    return block


# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------

def _wrap_text_lines(
    text: str,
    max_width: float,
    font_name: str,
    font_size: int,
) -> List[str]:
    """
    Envuelve el texto en múltiples líneas para que cada una quepa en max_width.
    Usa stringWidth de ReportLab para medir la longitud real.
    """
    lines: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r\n")
        if not line:
            lines.append("")
            continue

        current = ""
        for word in line.split(" "):
            candidate = word if not current else current + " " + word
            width = pdfmetrics.stringWidth(candidate, font_name, font_size)
            if width <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

    return lines


def _draw_text_multi_page(
    c: canvas.Canvas,
    text: str,
    *,
    left_margin: float = 1.0 * inch,
    right_margin: float = 1.0 * inch,
    top_margin: float = 10.5 * inch,
    bottom_margin: float = 1.0 * inch,
    font_name: str = "Helvetica",
    font_size: int = 10,
    leading: float = 13,
) -> int:
    """
    Dibuja texto en varias páginas con un layout sencillo tipo Outlook.

    Devuelve el número de páginas usadas.
    """
    page_width, _page_height = letter
    usable_width = page_width - left_margin - right_margin
    y = top_margin

    c.setFont(font_name, font_size)

    lines = _wrap_text_lines(text, usable_width, font_name, font_size)

    pages = 1
    for line in lines:
        if y < bottom_margin:
            c.showPage()
            c.setFont(font_name, font_size)
            y = top_margin
            pages += 1

        if line:
            c.drawString(left_margin, y, line)
        y -= leading

    return pages

def _build_final_text_for_eml(path: Path) -> str:
    """Reutiliza la misma lógica de header + body que eml_to_pdf."""
    msg = _load_email(path)

    header_block = _build_header_block(msg)
    body_text = _extract_best_body(msg)

    # Normalizar saltos
    body_text = (body_text or "").replace("\r\n", "\n").replace("\r", "\n")

    if header_block and body_text:
        final_text = header_block + "\n" + body_text
    elif header_block:
        final_text = header_block
    else:
        final_text = body_text or ""

    return final_text.strip() or "(empty email)"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def eml_to_pdf(input_eml: Path, output_pdf: Path) -> EmlToPdfResult:
    input_eml = input_eml.resolve()
    output_pdf = output_pdf.resolve()

    final_text = _build_final_text_for_eml(input_eml)

    c = canvas.Canvas(str(output_pdf), pagesize=letter)

    # Exactamente el mismo layout
    pages_used = _draw_text_multi_page(c, final_text)
    c.save()

    return EmlToPdfResult(
        input_eml=input_eml,
        output_pdf=output_pdf,
        pages=pages_used,
    )

# def eml_to_pdf(input_eml: Path, output_pdf: Path) -> EmlToPdfResult:
#     """
#     Convert an .eml file into a reasonably Outlook-like PDF.

#     Layout:
#       * Bloque de encabezado (From/Sent/To/Cc/Subject) + línea horizontal
#       * Body del correo en texto, preservando párrafos y quoting básico

#     Attachments NO se renderizan (solo el cuerpo del correo).
#     """
#     input_eml = input_eml.resolve()
#     output_pdf = output_pdf.resolve()

#     msg = _load_email(input_eml)

#     header_block = _build_header_block(msg)
#     body_text = _extract_best_body(msg)

#     # Normalizar saltos
#     body_text = body_text.replace("\r\n", "\n").replace("\r", "\n")

#     if header_block and body_text:
#         final_text = header_block + "\n" + body_text
#     elif header_block:
#         final_text = header_block
#     else:
#         final_text = body_text or "(empty email)"

#     # Crear PDF
#     c = canvas.Canvas(str(output_pdf), pagesize=letter)
#     pages_used = _draw_text_multi_page(c, final_text)
#     c.save()

#     return EmlToPdfResult(
#         input_eml=input_eml,
#         output_pdf=output_pdf,
#         pages=pages_used,
#     )

def estimate_eml_pages(eml_path: Path) -> int | None:
    """
    Estima el número de páginas que tendrá el E-mail en PDF,
    usando el mismo layout que eml_to_pdf, pero sin generar el PDF.
    """
    final_text = _build_final_text_for_eml(eml_path)

    page_width, _ = letter
    left_margin = 1.0 * inch
    right_margin = 1.0 * inch
    top_margin = 10.5 * inch
    bottom_margin = 1.0 * inch
    font_name = "Helvetica"
    font_size = 10
    leading = 13  # espacio entre líneas

    usable_width = page_width - left_margin - right_margin

    # Reutilizamos tu wrap
    lines = _wrap_text_lines(final_text, usable_width, font_name, font_size)

    if not lines:
        return 1

    # Cuántas líneas caben en una página
    available_height = top_margin - bottom_margin
    lines_per_page = max(1, int(available_height / leading))

    pages = (len(lines) + lines_per_page - 1) // lines_per_page
    return max(1, pages)