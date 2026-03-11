import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.extractor.pdf_to_text import pdf_to_text
from src.models.chapter import Chapter, ChapterSummary
from src.parser.chapter_splitter import split_chapters
from src.summarizer.chapter_summary import summarize_chapter
from src.tts.google_tts import synthesize_all
from src.utils.ocr_config import load_ocr_config, get_ocr_mode

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


def _load_summary(path: Path) -> ChapterSummary:
    """Load a ChapterSummary from a JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return ChapterSummary(**data)


def run_pipeline(pdf_path: str | Path, ocr_config: dict[str, str] | None = None) -> None:
    """Run the full PDF → Chapter → Summary → Audiobook pipeline."""
    pdf_path = Path(pdf_path)
    book_name = pdf_path.stem  # e.g. "290" from "290.pdf"

    # Skip if already fully processed
    done_marker = DATA_DIR / "audio" / book_name / ".done"
    if done_marker.exists():
        print(f"SKIP: {pdf_path.name} already processed (delete {done_marker} to re-process)")
        return

    # Auto-detect completion from existing files (books processed before .done feature)
    chapters_dir  = DATA_DIR / "chapters"  / book_name
    summaries_dir = DATA_DIR / "summaries" / book_name
    audio_dir_    = DATA_DIR / "audio"     / book_name
    n_ch  = len(list(chapters_dir.glob("chapter_*.txt")))   if chapters_dir.exists()  else 0
    n_sum = len(list(summaries_dir.glob("chapter_*.json"))) if summaries_dir.exists() else 0
    n_aud = len(list(audio_dir_.glob("chapter_*.mp3")))     if audio_dir_.exists()    else 0
    if n_ch > 0 and n_ch == n_sum == n_aud:
        done_marker.parent.mkdir(parents=True, exist_ok=True)
        done_marker.write_text("", encoding="utf-8")
        print(f"SKIP: {pdf_path.name} already complete ({n_ch} chapters/summaries/audio). Marked as done.")
        return

    ocr_mode = get_ocr_mode(book_name, ocr_config)
    print(f"[1/5] Extracting text from {pdf_path.name} (OCR mode: {ocr_mode}) ...")
    full_text = pdf_to_text(pdf_path, ocr_mode=ocr_mode)

    print(f"[2/5] Splitting into chapters ...")
    chapters = split_chapters(full_text)
    print(f"       Found {len(chapters)} chapter(s).")

    # Save chapter text files — per-book subfolder
    chapters_dir = DATA_DIR / "chapters" / book_name
    chapters_dir.mkdir(parents=True, exist_ok=True)
    for ch in chapters:
        chapter_file = chapters_dir / f"chapter_{ch.chapter}.txt"
        chapter_file.write_text(ch.content, encoding="utf-8")

    print(f"[3/5] Summarizing chapters ...")
    summaries_dir = DATA_DIR / "summaries" / book_name
    summaries_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[ChapterSummary] = []
    new_count = 0
    skip_count = 0
    for ch in chapters:
        summary_file = summaries_dir / f"chapter_{ch.chapter}.json"
        if summary_file.exists():
            summaries.append(_load_summary(summary_file))
            skip_count += 1
            print(f"       chapter {ch.chapter}: SKIP (already summarized)")
        else:
            summary = summarize_chapter(ch)
            summary_file.write_text(
                json.dumps(summary.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            summaries.append(summary)
            new_count += 1
            print(f"       chapter {ch.chapter}: OK")
            # Small delay between chapters to stay within TPM limits (30k/min)
            time.sleep(3)

    print(f"       Summarized: {new_count} new, {skip_count} skipped (loaded from disk)")

    print(f"[4/5] Generating audio ...")
    audio_dir = DATA_DIR / "audio" / book_name
    language_code = os.getenv("TTS_LANGUAGE_CODE", "id-ID")
    voice_name = os.getenv("TTS_VOICE_NAME", "id-ID-Chirp3-HD-Kore")
    audio_paths = synthesize_all(summaries, audio_dir, language_code=language_code, voice_name=voice_name)

    print(f"[5/5] Done!")
    print(f"       Chapters saved to: {chapters_dir}")
    print(f"       Summaries saved to: {summaries_dir}")
    print(f"       Audio files saved to: {audio_dir}")
    for p in audio_paths:
        print(f"         - {p.name}")

    # Mark as fully processed
    done_marker.write_text("", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Audiobook Agent: PDF → Chapter → Summary → Audiobook"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--input",
        type=str,
        help="Path to a single input PDF file",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Process all PDF files in src/books/",
    )
    parser.add_argument(
        "--books-dir",
        type=str,
        default=None,
        help="Directory containing PDF files (used with --all). Defaults to src/books/",
    )
    parser.add_argument(
        "--excel",
        type=str,
        default=None,
        help="Path to Excel file with OCR classification. Defaults to books_list.xlsx",
    )
    args = parser.parse_args()

    if args.input:
        excel_path = Path(args.excel) if args.excel else None
        ocr_config = load_ocr_config(excel_path)
        run_pipeline(args.input, ocr_config=ocr_config)
    else:
        books_dir = Path(args.books_dir) if args.books_dir else BASE_DIR / "src" / "books"
        pdf_files = sorted(books_dir.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in {books_dir}")
            return

        ocr_config = load_ocr_config(Path(args.excel) if args.excel else None)
        if ocr_config:
            from src.utils.ocr_config import OCR_FULL, OCR_NONE
            full_count = sum(1 for v in ocr_config.values() if v == OCR_FULL)
            none_count = sum(1 for v in ocr_config.values() if v == OCR_NONE)
            print(f"OCR config loaded: {full_count} full-OCR, {none_count} no-OCR")

        print(f"Found {len(pdf_files)} PDF file(s) to process.\n")
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n{'='*60}")
            print(f"[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
            print(f"{'='*60}")
            try:
                run_pipeline(pdf_file, ocr_config=ocr_config)
            except Exception as e:
                print(f"ERROR processing {pdf_file.name}: {e}")
                print("Skipping to next book...\n")
                continue


if __name__ == "__main__":
    main()
