"""Debug: print extracted text to identify chapter heading format."""
import sys
sys.path.insert(0, ".")

from src.extractor.pdf_to_text import pdf_to_text

pdf_path = "src/books/290.pdf"
text = pdf_to_text(pdf_path)

print("=== FIRST 3000 CHARS ===")
print(text[:3000])
print("\n=== LINES CONTAINING POSSIBLE CHAPTER MARKERS ===")
keywords = ["bab", "chapter", "bagian", "part", "section", "unit", "pelajaran"]
for i, line in enumerate(text.splitlines()):
    stripped = line.strip()
    if stripped and any(kw in stripped.lower() for kw in keywords):
        print(f"[line {i}] {stripped}")
