from pathlib import Path

from dotenv import load_dotenv
from pdfminer.high_level import extract_text

from src.utils.text_cleaner import clean_text, remove_headers_footers

load_dotenv()


def _ocr_pdf(pdf_path: Path) -> str:
    """
    Fallback: render each PDF page to an image and run OCR via Google Cloud Vision API.
    Requires: pip install pymupdf google-cloud-vision
    Uses GOOGLE_APPLICATION_CREDENTIALS from env (already configured).
    """
    try:
        import fitz  # pymupdf
        from google.cloud import vision
    except ImportError as e:
        raise ImportError(
            f"OCR dependencies missing: {e}.\n"
            "Install with: pip install pymupdf google-cloud-vision"
        ) from e

    client = vision.ImageAnnotatorClient()
    doc = fitz.open(str(pdf_path))
    pages_text = []

    for page in doc:
        pix = page.get_pixmap(dpi=300)
        image = vision.Image(content=pix.tobytes("png"))
        response = client.document_text_detection(image=image)

        if response.error.message:
            raise RuntimeError(f"Google Vision API error: {response.error.message}")

        pages_text.append(response.full_text_annotation.text)

    doc.close()
    return "\n".join(pages_text)


def pdf_to_text(pdf_path: str | Path, ocr_mode: str = "auto") -> str:
    """
    Extract text from a PDF file and return cleaned string.

    ocr_mode:
        "full"  — Force OCR on all pages (for fully scanned PDFs).
        "none"  — Use pdfminer only, no OCR fallback.
        "auto"  — Try pdfminer first, fallback to OCR if text < 100 chars.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if ocr_mode == "full":
        # Entire PDF is scanned — go straight to OCR
        raw_text = _ocr_pdf(pdf_path)
    else:
        try:
            raw_text = extract_text(str(pdf_path))
        except Exception:
            # pdfminer can fail on some malformed PDFs
            raw_text = ""

        # Auto-fallback to OCR if extracted text is too short
        if ocr_mode == "auto" and len(raw_text.strip()) < 100:
            raw_text = _ocr_pdf(pdf_path)

    text = remove_headers_footers(raw_text)
    text = clean_text(text)
    return text
