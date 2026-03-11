"""
Pipeline untuk buku Gutenberg (plain text → chapter → summary → audiobook).
Berbeda dari pipeline PDF — input langsung dari file .txt, tanpa OCR.

Usage:
    # Proses satu file
    python -m src.pipeline.gutenberg_pipeline --input gutenberg_books/plain_text/999_1.txt

    # Proses semua file (hanya buku yang berhasil di-split, skip 26 buku tanpa heading)
    python -m src.pipeline.gutenberg_pipeline --all

    # Proses semua file termasuk buku tanpa chapter heading
    python -m src.pipeline.gutenberg_pipeline --all --include-unsplit

    # Custom folder input
    python -m src.pipeline.gutenberg_pipeline --all --books-dir gutenberg_books/plain_text

    # Limit jumlah buku
    python -m src.pipeline.gutenberg_pipeline --all --limit 10
"""
import argparse
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv

from src.models.chapter import Chapter, ChapterSummary
from src.parser.chapter_splitter import split_chapters
from src.summarizer.chapter_summary import summarize_chapter
from src.tts.google_tts import synthesize_all
from src.utils.text_cleaner import clean_text

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_BOOKS_DIR = BASE_DIR / "gutenberg_books" / "plain_text"


def _strip_gutenberg_boilerplate(text: str) -> str:
    """Remove Project Gutenberg header and footer boilerplate."""
    # Find start marker
    start_markers = [
        r"\*\*\*\s*START OF (?:THE |THIS )?PROJECT GUTENBERG EBOOK",
        r"\*\*\*\s*START OF THIS EBOOK",
    ]
    for pattern in start_markers:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Skip past the marker line
            newline = text.find("\n", match.end())
            if newline != -1:
                text = text[newline + 1:]
            break

    # Find end marker
    end_markers = [
        r"\*\*\*\s*END OF (?:THE |THIS )?PROJECT GUTENBERG EBOOK",
        r"\*\*\*\s*END OF THIS EBOOK",
    ]
    for pattern in end_markers:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            text = text[:match.start()]
            break

    return text.strip()


def _load_summary(path: Path) -> ChapterSummary:
    """Load a ChapterSummary from a JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return ChapterSummary(**data)


def _extract_book_name(file_path: Path) -> str:
    """Get book name from file stem, e.g. '999_1' → '9991'."""
    return file_path.stem.replace("_", "")


def run_gutenberg_pipeline(txt_path: str | Path, include_unsplit: bool = False) -> None:
    """Run the full Text → Chapter → Summary → Audiobook pipeline for a Gutenberg text."""
    txt_path = Path(txt_path)
    book_name = _extract_book_name(txt_path)

    # Skip if already fully processed
    done_marker = DATA_DIR / "audio" / book_name / ".done"
    if done_marker.exists():
        print(f"SKIP: {txt_path.name} already processed (delete {done_marker} to re-process)")
        return

    # Auto-detect completion from existing files (books processed before .done feature)
    chapters_dir_  = DATA_DIR / "chapters"  / book_name
    summaries_dir_ = DATA_DIR / "summaries" / book_name
    audio_dir__    = DATA_DIR / "audio"     / book_name
    n_ch  = len(list(chapters_dir_.glob("chapter_*.txt")))    if chapters_dir_.exists()  else 0
    n_sum = len(list(summaries_dir_.glob("chapter_*.json")))  if summaries_dir_.exists() else 0
    n_aud = len(list(audio_dir__.glob("chapter_*.mp3")))      if audio_dir__.exists()    else 0
    if n_ch > 0 and n_ch == n_sum == n_aud:
        done_marker.parent.mkdir(parents=True, exist_ok=True)
        done_marker.write_text("", encoding="utf-8")
        print(f"SKIP: {txt_path.name} already complete ({n_ch} chapters/summaries/audio). Marked as done.")
        return

    print(f"[1/4] Reading text from {txt_path.name} ...")
    if not txt_path.exists():
        raise FileNotFoundError(f"Text file not found: {txt_path}")

    raw_text = txt_path.read_text(encoding="utf-8", errors="replace")
    text = _strip_gutenberg_boilerplate(raw_text)
    text = clean_text(text)

    if len(text.strip()) < 100:
        raise ValueError(f"Text too short after cleaning ({len(text)} chars)")

    print(f"       Text length: {len(text):,} chars")

    print(f"[2/4] Splitting into chapters ...")
    chapters = split_chapters(text)
    print(f"       Found {len(chapters)} chapter(s).")

    # Skip books that couldn't be split into proper chapters
    if len(chapters) == 1 and chapters[0].title == "Full Text" and not include_unsplit:
        raise ValueError(
            "No chapter headings detected — skipping unsplit book. "
            "Use --include-unsplit to process anyway."
        )

    # Save chapter text files
    chapters_dir = DATA_DIR / "chapters" / book_name
    chapters_dir.mkdir(parents=True, exist_ok=True)
    for ch in chapters:
        chapter_file = chapters_dir / f"chapter_{ch.chapter}.txt"
        chapter_file.write_text(ch.content, encoding="utf-8")

    print(f"[3/4] Summarizing chapters ...")
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

    print(f"[4/4] Generating audio ...")
    audio_dir = DATA_DIR / "audio" / book_name
    language_code = os.getenv("TTS_LANGUAGE_CODE", "id-ID")
    voice_name = os.getenv("TTS_VOICE_NAME", "id-ID-Chirp3-HD-Kore")
    audio_paths = synthesize_all(summaries, audio_dir, language_code=language_code, voice_name=voice_name)

    print(f"Done!")
    print(f"       Chapters saved to: {chapters_dir}")
    print(f"       Summaries saved to: {summaries_dir}")
    print(f"       Audio files saved to: {audio_dir}")
    for p in audio_paths:
        print(f"         - {p.name}")

    # Mark as fully processed
    done_marker.write_text("", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gutenberg Pipeline: Text → Chapter → Summary → Audiobook"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--input", type=str,
        help="Path to a single input .txt file",
    )
    group.add_argument(
        "--all", action="store_true",
        help="Process all .txt files in books directory",
    )
    parser.add_argument(
        "--books-dir", type=str, default=None,
        help=f"Directory containing .txt files (default: gutenberg_books/plain_text/)",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max number of books to process",
    )
    parser.add_argument(
        "--include-unsplit", action="store_true",
        help="Also process books with no detected chapter headings (treated as one chapter)",
    )
    args = parser.parse_args()

    include_unsplit = args.include_unsplit

    if args.input:
        run_gutenberg_pipeline(args.input, include_unsplit=include_unsplit)
    else:
        books_dir = Path(args.books_dir) if args.books_dir else DEFAULT_BOOKS_DIR
        txt_files = sorted(books_dir.glob("*.txt"))
        # Exclude index.txt
        txt_files = [f for f in txt_files if f.name != "index.txt"]

        if not txt_files:
            print(f"No .txt files found in {books_dir}")
            return

        if args.limit:
            txt_files = txt_files[:args.limit]

        print(f"Found {len(txt_files)} text file(s) to process.\n")
        for i, txt_file in enumerate(txt_files, 1):
            print(f"\n{'='*60}")
            print(f"[{i}/{len(txt_files)}] Processing: {txt_file.name}")
            print(f"{'='*60}")
            try:
                run_gutenberg_pipeline(txt_file, include_unsplit=include_unsplit)
            except Exception as e:
                print(f"ERROR processing {txt_file.name}: {e}")
                print("Skipping to next book...\n")
                continue


if __name__ == "__main__":
    main()
