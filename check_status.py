"""
Cek status processing semua buku (PDF phase1, PDF phase2, Gutenberg).
Tampilkan: DONE / PARTIAL (ada summary tapi belum audio) / PENDING
"""
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

print(f"{'Book':<20} {'Source':<12} {'Status':<10} {'Chapters':>8} {'Summaries':>10} {'Audio':>6}")
print("-" * 72)

rows = []

def check_book(book_name: str, source: str):
    done_marker  = DATA_DIR / "audio"     / book_name / ".done"
    chapters_dir = DATA_DIR / "chapters"  / book_name
    summaries_dir= DATA_DIR / "summaries" / book_name
    audio_dir    = DATA_DIR / "audio"     / book_name

    n_chapters  = len(list(chapters_dir.glob("chapter_*.txt")))   if chapters_dir.exists()  else 0
    n_summaries = len(list(summaries_dir.glob("chapter_*.json")))  if summaries_dir.exists() else 0
    n_audio     = len(list(audio_dir.glob("chapter_*.mp3")))       if audio_dir.exists()     else 0

    if done_marker.exists():
        status = "DONE"
    elif n_chapters > 0 and n_audio == n_chapters and n_summaries == n_chapters:
        status = "DONE*"   # fully complete but no .done marker (processed before this feature)
    elif n_summaries > 0 or n_audio > 0:
        status = "PARTIAL"
    else:
        status = "PENDING"

    rows.append((book_name, source, status, n_chapters, n_summaries, n_audio))


# --- PDF phase1 ---
books1 = BASE_DIR / "src" / "books"
if books1.exists():
    for pdf in sorted(books1.glob("*.pdf")):
        check_book(pdf.stem, "PDF-phase1")

# --- PDF phase2 ---
books2 = BASE_DIR / "src" / "books_phase2"
if books2.exists():
    for pdf in sorted(books2.glob("*.pdf")):
        check_book(pdf.stem, "PDF-phase2")

# --- Gutenberg ---
gutenberg = BASE_DIR / "gutenberg_books" / "plain_text"
if gutenberg.exists():
    for txt in sorted(gutenberg.glob("*.txt")):
        if txt.name == "index.txt":
            continue
        book_name = txt.stem.replace("_", "")
        check_book(book_name, "Gutenberg")

# Print rows
for book_name, source, status, n_ch, n_sum, n_aud in rows:
    print(f"{book_name:<20} {source:<12} {status:<10} {n_ch:>8} {n_sum:>10} {n_aud:>6}")

# Summary
total     = len(rows)
done      = sum(1 for r in rows if r[2] in ("DONE", "DONE*"))
partial   = sum(1 for r in rows if r[2] == "PARTIAL")
pending   = sum(1 for r in rows if r[2] == "PENDING")

print("-" * 72)
print(f"Total: {total}  |  DONE: {done}  |  PARTIAL: {partial}  |  PENDING: {pending}")
print(f"  (* DONE* = chapters/summaries/audio complete, no .done marker)")
