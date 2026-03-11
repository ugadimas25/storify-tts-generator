"""
Check all PDFs in src/books/ and report chapter detection results.
Usage: python check_books.py
"""
import sys
from pathlib import Path

sys.path.insert(0, ".")

from src.extractor.pdf_to_text import pdf_to_text
from src.parser.chapter_splitter import split_chapters
from src.utils.ocr_config import load_ocr_config, get_ocr_mode

BOOKS_DIR = Path("src/books")
MIN_CONTENT_LEN = 500

STATUS_OK    = "OK"
STATUS_WARN  = "WARN"
STATUS_ERROR = "ERROR"


def check_book(pdf_path: Path, ocr_config: dict[str, str] | None = None) -> dict:
    try:
        book_id = pdf_path.stem
        ocr_mode = get_ocr_mode(book_id, ocr_config)
        text = pdf_to_text(pdf_path, ocr_mode=ocr_mode)
        if not text.strip():
            return {"status": STATUS_ERROR, "chapters": 0, "note": "No text extracted (OCR also failed)"}

        chapters = split_chapters(text)
        chapter_count = len(chapters)

        if chapter_count == 1 and chapters[0].title == "Full Text":
            return {"status": STATUS_WARN, "chapters": 1, "note": "No chapter markers found"}

        short = [c.chapter for c in chapters if len(c.content) < MIN_CONTENT_LEN]
        if short:
            return {
                "status": STATUS_WARN,
                "chapters": chapter_count,
                "note": f"Short chapters: {short}",
            }

        return {"status": STATUS_OK, "chapters": chapter_count, "note": ""}

    except Exception as e:
        return {"status": STATUS_ERROR, "chapters": 0, "note": str(e)[:80]}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Check PDFs for chapter detection")
    parser.add_argument(
        "--books-dir", type=str, default=None,
        help="Directory containing PDF files (default: src/books)"
    )
    parser.add_argument(
        "--excel", type=str, default=None,
        help="Path to Excel file with OCR classification (default: books_list.xlsx)"
    )
    args = parser.parse_args()

    books_dir = Path(args.books_dir) if args.books_dir else BOOKS_DIR
    excel_path = Path(args.excel) if args.excel else None

    pdf_files = sorted(books_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {books_dir}")
        return

    ocr_config = load_ocr_config(excel_path)
    if ocr_config:
        from src.utils.ocr_config import OCR_FULL, OCR_NONE
        full_count = sum(1 for v in ocr_config.values() if v == OCR_FULL)
        none_count = sum(1 for v in ocr_config.values() if v == OCR_NONE)
        print(f"OCR config loaded: {full_count} full-OCR, {none_count} no-OCR")

    print(f"Checking {len(pdf_files)} PDF files...\n")
    print(f"{'File':<15} {'OCR':<8} {'Status':<10} {'Chapters':>8}  Note")
    print("-" * 85)

    summary = {STATUS_OK: [], STATUS_WARN: [], STATUS_ERROR: []}

    for pdf_path in pdf_files:
        result = check_book(pdf_path, ocr_config=ocr_config)
        status = result["status"]
        chapters = result["chapters"]
        note = result["note"]

        ocr_mode = get_ocr_mode(pdf_path.stem, ocr_config)
        marker = {STATUS_OK: "✓", STATUS_WARN: "⚠", STATUS_ERROR: "✗"}.get(status, "?")
        print(f"{pdf_path.name:<15} {ocr_mode:<8} {marker} {status:<6}  {chapters:>8}  {note}")
        summary[status].append(pdf_path.name)

    total = len(pdf_files)
    print("\n" + "=" * 75)
    print(f"  ✓ OK    : {len(summary[STATUS_OK])}/{total} — ready to generate")
    print(f"  ⚠ WARN  : {len(summary[STATUS_WARN])}/{total} — no chapter markers, will generate as 1 chapter")
    print(f"  ✗ ERROR : {len(summary[STATUS_ERROR])}/{total} — failed to process")
    if summary[STATUS_WARN]:
        print(f"\n  WARN files (no chapter markers):")
        for f in summary[STATUS_WARN]:
            print(f"    - {f}")
    if summary[STATUS_ERROR]:
        print(f"\n  ERROR files:")
        for f in summary[STATUS_ERROR]:
            print(f"    - {f}")


if __name__ == "__main__":
    main()
