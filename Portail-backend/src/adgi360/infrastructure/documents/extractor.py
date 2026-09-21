"""Extraction déterministe des documents envoyés au workflow n8n."""

import csv
import io
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from pypdf import PdfReader
from pptx import Presentation

from adgi360.shared.exceptions import ValidationError


def _tabular(rows: list[list[Any]], filename: str) -> dict:
    rows = [["" if value is None else value for value in row] for row in rows]
    if not rows:
        return {"source_type": "document", "filename": filename, "columns": [], "row_count": 0, "rows": []}
    columns = [str(value or f"colonne_{index + 1}") for index, value in enumerate(rows[0])]
    objects = [dict(zip(columns, row)) for row in rows[1:501]]
    return {"source_type": "document", "filename": filename, "columns": columns, "row_count": max(0, len(rows) - 1), "rows": objects}


def extract_document(content: bytes, filename: str, content_type: str | None = None) -> dict:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv" or content_type == "text/csv":
        text = content.decode("utf-8-sig", errors="replace")
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
        return _tabular(list(csv.reader(io.StringIO(text), dialect)), filename)
    if suffix in {".xlsx", ".xlsm"}:
        book = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = book.active
        return _tabular([list(row) for row in sheet.iter_rows(values_only=True)], filename)
    if suffix == ".pdf" or content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(content))
        text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)
        return {"source_type": "document", "filename": filename, "page_count": len(reader.pages), "text": text[:120_000]}
    if suffix in {".pptx", ".potx"}:
        deck = Presentation(io.BytesIO(content))
        slides = []
        for index, slide in enumerate(deck.slides, start=1):
            texts = [shape.text.strip() for shape in slide.shapes if hasattr(shape, "text") and shape.text.strip()]
            slides.append({"slide": index, "text": "\n".join(texts)})
        return {"source_type": "document", "filename": filename, "slide_count": len(slides), "slides": slides}
    if suffix in {".txt", ".md", ".json"} or (content_type or "").startswith("text/"):
        return {"source_type": "document", "filename": filename, "text": content.decode("utf-8", errors="replace")[:120_000]}
    raise ValidationError(f"Format non pris en charge pour l’analyse : {suffix or content_type}")
