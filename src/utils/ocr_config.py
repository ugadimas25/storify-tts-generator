"""
Read OCR classification from books_list.xlsx.

Column 'OCR' = 'V'        → full OCR (entire PDF is scanned)
Column 'just cover' = 'V' → cover-only image, text is extractable (no OCR needed)
Both empty                 → pure text PDF (no OCR needed)
"""
from pathlib import Path

EXCEL_PATH = Path(__file__).resolve().parent.parent.parent / "books_list.xlsx"

# OCR modes
OCR_FULL = "full"          # Force OCR on all pages
OCR_NONE = "none"          # No OCR, pdfminer only
OCR_AUTO = "auto"          # Current behavior: pdfminer + fallback


def load_ocr_config(excel_path: Path | None = None) -> dict[str, str]:
    """
    Load OCR classification from the Excel file.
    Returns dict mapping book_id (str) → ocr_mode (str).
    """
    import openpyxl

    path = excel_path or EXCEL_PATH
    if not path.exists():
        return {}

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    config: dict[str, str] = {}

    for row in ws.iter_rows(min_row=2, values_only=True):
        book_id = str(row[2]) if row[2] is not None else None  # Column C: Book ID
        if not book_id:
            continue

        ocr_val = str(row[5]).strip().upper() if row[5] else ""        # Column F: OCR
        cover_val = str(row[6]).strip().upper() if row[6] else ""      # Column G: just cover

        if ocr_val == "V":
            config[book_id] = OCR_FULL
        elif cover_val == "V":
            config[book_id] = OCR_NONE   # cover is image but content is text
        else:
            config[book_id] = OCR_NONE   # pure text PDF

    wb.close()
    return config


def get_ocr_mode(book_id: str, config: dict[str, str] | None = None) -> str:
    """Get OCR mode for a specific book. Loads config if not provided."""
    if config is None:
        config = load_ocr_config()
    return config.get(book_id, OCR_AUTO)
