"""Debug: show which heading keyword the splitter picks for each file."""
from pathlib import Path
from src.parser.chapter_splitter import (
    _find_headings, _remove_toc_cluster, HEADING_KEYWORDS, split_chapters,
)

tests = [
    "999_1.txt",   # BOOK(13) expected
    "999_32.txt",  # ACT(3) - "FIRST ACT" pattern
    "999_50.txt",  # CANTO(100) expected (Dante's Comedy)
    "999_2.txt",   # CHAPTER(24+) expected (Frankenstein)
    "999_10.txt",  # CHAPTER(86+) expected (Middlemarch)
    "999_6.txt",   # SCENE(25) expected (Romeo and Juliet)
    "999_48.txt",  # PART(7) expected
    "999_71.txt",  # BOOK(24) expected (Odyssey)
]

for fname in tests:
    p = Path("gutenberg_books/plain_text") / fname
    if not p.exists():
        print(f"{fname}: NOT FOUND\n")
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    text_length = len(text)

    # Show raw vs filtered match counts per keyword
    print(f"=== {fname} ({text_length:,} chars) ===")
    for kw in HEADING_KEYWORDS:
        hits = _find_headings(text, kw)
        if hits:
            hits_sorted = sorted(hits, key=lambda x: x[2])
            after_toc = _remove_toc_cluster(hits_sorted, text_length)
            removed = len(hits) - len(after_toc)
            label = f"  {kw}: {len(hits)} raw"
            if removed:
                label += f" -> {len(after_toc)} after TOC removal (-{removed})"
            print(label)

    # Show final chapter split
    chapters = split_chapters(text)
    print(f"  RESULT: {len(chapters)} chapters")
    for c in chapters[:5]:
        print(f"    {c.chapter}. {c.title!r} ({len(c.content):,} chars)")
    if len(chapters) > 5:
        print(f"    ... ({len(chapters) - 5} more)")
    print()
