"""Scan Gutenberg texts for heading patterns."""
import re
from pathlib import Path

books_dir = Path('gutenberg_books/plain_text')
patterns = [
    (r'(?m)^\s*(CHAPTER\s+[IVXLCDM\d]+)', 'CHAPTER'),
    (r'(?m)^\s*(BOOK\s+[IVXLCDM\d]+)', 'BOOK'),
    (r'(?m)^\s*(PART\s+[IVXLCDM\d]+)', 'PART'),
    (r'(?m)^\s*(LETTER\s+\d+)', 'LETTER'),
    (r'(?m)^\s*(ACT\s+[IVXLCDM\d]+)', 'ACT'),
    (r'(?m)^\s*(VOLUME\s+[IVXLCDM\d]+)', 'VOLUME'),
    (r'(?m)^\s*(CANTO\s+[IVXLCDM\d]+)', 'CANTO'),
    (r'(?m)^\s*(SECTION\s+[IVXLCDM\d]+)', 'SECTION'),
    (r'(?m)^\s*(STAVE\s+[IVXLCDM\d]+)', 'STAVE'),
    (r'(?m)^\s*(SCENE\s+[IVXLCDM\d]+)', 'SCENE'),
]

for f in sorted(books_dir.glob('*.txt')):
    if f.name == 'index.txt':
        continue
    text = f.read_text(encoding='utf-8', errors='replace')
    found = []
    for pat, label in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            found.append(f"{label}({len(matches)})")
    if found:
        print(f"{f.name:<18} {', '.join(found)}")
    else:
        print(f"{f.name:<18} -- no headings found --")
