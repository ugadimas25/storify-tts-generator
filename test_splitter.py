"""Test chapter_splitter on ALL Gutenberg books."""
from pathlib import Path
from src.parser.chapter_splitter import split_chapters

books_dir = Path("gutenberg_books/plain_text")
files = sorted(books_dir.glob("*.txt"))

no_split = []  # Books that couldn't be split (only 1 "Full Text" chapter)

for p in files:
    text = p.read_text(encoding="utf-8", errors="replace")
    chapters = split_chapters(text)
    label = f"{p.name:<20s} {len(chapters):>3d} ch"
    if chapters:
        sizes = [len(c.content) for c in chapters]
        label += f"  | min={min(sizes):>5,} max={max(sizes):>6,} avg={sum(sizes)//len(sizes):>6,}"
        label += f"  | {chapters[0].title[:50]}"
    print(label)
    if len(chapters) == 1 and chapters[0].title == "Full Text":
        no_split.append(p.name)

print(f"\n--- {len(no_split)} books with no chapter split ---")
for n in no_split:
    print(f"  {n}")
