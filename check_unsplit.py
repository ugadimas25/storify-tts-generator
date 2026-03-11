"""Check what the unsplit books look like - do they have any structure?"""
import re
from pathlib import Path

no_split = [
    "999_21.txt", "999_24.txt", "999_26.txt", "999_27.txt", "999_30.txt",
    "999_35.txt", "999_40.txt", "999_41.txt", "999_45.txt", "999_49.txt",
    "999_51.txt", "999_57.txt", "999_58.txt", "999_59.txt", "999_63.txt",
    "999_64.txt", "999_66.txt", "999_70.txt", "999_73.txt", "999_75.txt",
    "999_76.txt", "999_78.txt", "999_80.txt", "999_92.txt", "999_93.txt",
    "999_98.txt",
]

# Check for any structure clues
heading_re = re.compile(
    r"^\s{0,4}[A-Z][A-Z\s\.\-:]{5,60}$", re.MULTILINE
)

for fname in no_split:
    p = Path("gutenberg_books/plain_text") / fname
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    size = len(text)

    # Find potential all-caps headings
    caps = heading_re.findall(text)
    # Filter out short/common noise
    caps = [c.strip() for c in caps if len(c.strip()) > 5][:5]

    # Also check index.txt for the book title
    print(f"{fname}: {size:>10,} chars | sample caps: {caps}")
