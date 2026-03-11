"""
Download top books dari Project Gutenberg ke dua folder sekaligus:
    gutenberg_books/plain_text/   → file .txt
    gutenberg_books/epub/         → file .epub

File dinamai berdasarkan urutan ranking: 999_1, 999_2, 999_3, dst.
  Contoh: buku #1 → 999_1.txt dan 999_1.epub
          buku #2 → 999_2.txt dan 999_2.epub

Arguments:
    --period   : yesterday (default), 7, atau 30
    --limit    : Jumlah buku yang didownload (default: semua 100)
    --output   : Folder utama output (default: gutenberg_books/)
    --delay    : Jeda antar download dalam detik (default: 2)

============================================================================
CONTOH PENGGUNAAN:
============================================================================

  # Download 10 buku teratas kemarin
  python download_gutenberg.py --limit 10

  # Download semua 100 buku teratas kemarin
  python download_gutenberg.py

  # Download 10 buku teratas 7 hari terakhir
  python download_gutenberg.py --period 7 --limit 10

  # Download 10 buku teratas 30 hari terakhir
  python download_gutenberg.py --period 30 --limit 10

  # Download semua 100 buku 30 hari terakhir
  python download_gutenberg.py --period 30

  # Download ke folder utama custom
  python download_gutenberg.py --limit 10 --output my_books

  # Perlambat jeda antar download (default 2 detik)
  python download_gutenberg.py --limit 10 --delay 3

============================================================================
HASIL:
    gutenberg_books/
    ├── plain_text/
    │   ├── 999_1.txt
    │   ├── 999_2.txt
    │   └── ...
    ├── epub/
    │   ├── 999_1.epub
    │   ├── 999_2.epub
    │   └── ...
    └── index.txt         ← daftar semua buku yang didownload
============================================================================
"""
import argparse
import re
import sys
import time
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    print("Installing dependencies (requests, beautifulsoup4)...")
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4", "-q"])
    import requests
    from bs4 import BeautifulSoup

TOP_URL = "https://www.gutenberg.org/browse/scores/top"
DELAY_SECONDS = 2  # Be respectful to Gutenberg servers

FORMAT_CONFIG = {
    "txt": {
        "url": "https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
        "ext": ".txt",
        "label": "Plain Text",
    },
    "epub3": {
        "url": "https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}-images-3.epub",
        "ext": ".epub",
        "label": "EPUB3 (with images)",
    },
}


def fetch_top_books(period: str = "yesterday") -> list[dict]:
    """
    Scrape the top 100 ebooks list from Gutenberg.
    period: 'yesterday', '7', or '30'
    Returns list of {id, title, downloads, url}.
    """
    headers = {"User-Agent": "AudiobookAgent/1.0 (educational project)"}
    resp = requests.get(TOP_URL, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find the right section based on period
    section_map = {
        "yesterday": "Top 100 EBooks yesterday",
        "7": "Top 100 EBooks last 7 days",
        "30": "Top 100 EBooks last 30 days",
    }
    target_heading = section_map.get(period, section_map["yesterday"])

    # Find the heading
    target_h2 = None
    for h2 in soup.find_all("h2"):
        if target_heading in h2.get_text():
            target_h2 = h2
            break

    if not target_h2:
        print(f"Could not find section: {target_heading}")
        return []

    # The book list is in the <ol> following the h2
    ol = target_h2.find_next("ol")
    if not ol:
        print("Could not find book list")
        return []

    books = []
    for li in ol.find_all("li"):
        link = li.find("a", href=re.compile(r"/ebooks/\d+"))
        if not link:
            continue

        href = link["href"]
        book_id = re.search(r"/ebooks/(\d+)", href).group(1)
        full_text = li.get_text(strip=True)

        # Extract title and download count
        # Format: "Title by Author (12345)"
        title_match = re.match(r"(.+?)\s*\((\d[\d,]*)\)\s*$", full_text)
        if title_match:
            title = title_match.group(1).strip()
            downloads = title_match.group(2).replace(",", "")
        else:
            title = full_text
            downloads = "0"

        books.append({
            "id": book_id,
            "title": title,
            "downloads": int(downloads),
            "url": f"https://www.gutenberg.org{href}",
        })

    return books


def sanitize_filename(name: str, max_len: int = 80) -> str:
    """Make a string safe for use as a filename."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    if len(name) > max_len:
        name = name[:max_len].strip()
    return name


def download_book(book_id: str, out_path: Path, fmt: str = "txt") -> Path | None:
    """Download a single book in the specified format to out_path. Returns path or None."""
    config = FORMAT_CONFIG[fmt]
    url = config["url"].format(book_id=book_id)
    headers = {"User-Agent": "AudiobookAgent/1.0 (educational project)"}

    try:
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()

        if len(resp.content) < 100:
            print(f"      WARNING: Very short content ({len(resp.content)} bytes), skipping")
            return None

        if fmt == "txt":
            resp.encoding = resp.apparent_encoding or "utf-8"
            out_path.write_text(resp.text, encoding="utf-8")
        else:
            out_path.write_bytes(resp.content)

        return out_path

    except requests.RequestException as e:
        print(f"      ERROR ({fmt}): {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Download top books from Project Gutenberg")
    parser.add_argument(
        "--period", choices=["yesterday", "7", "30"], default="yesterday",
        help="Time period for top books (default: yesterday)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max number of books to download (default: all 100)"
    )
    parser.add_argument(
        "--output", type=str, default="gutenberg_books",
        help="Base output directory (default: gutenberg_books/)"
    )
    parser.add_argument(
        "--delay", type=float, default=DELAY_SECONDS,
        help=f"Delay between downloads in seconds (default: {DELAY_SECONDS})"
    )
    args = parser.parse_args()

    print(f"Fetching top books (period: {args.period})...")
    books = fetch_top_books(args.period)

    if not books:
        print("No books found.")
        return

    if args.limit:
        books = books[:args.limit]

    base_dir    = Path(args.output)
    txt_dir     = base_dir / "plain_text"
    epub_dir    = base_dir / "epub"
    txt_dir.mkdir(parents=True, exist_ok=True)
    epub_dir.mkdir(parents=True, exist_ok=True)

    # Save index file
    index_file = base_dir / "index.txt"
    with open(index_file, "w", encoding="utf-8") as f:
        f.write(f"Top {len(books)} Project Gutenberg Books\n")
        f.write(f"Period: {args.period}\n")
        f.write("=" * 60 + "\n\n")
        for i, book in enumerate(books, 1):
            f.write(f"{i:>3}. [999_{i}] {book['title']} (id: {book['id']}, {book['downloads']:,} downloads)\n")

    print(f"Found {len(books)} books.")
    print(f"  plain_text → {txt_dir}/")
    print(f"  epub       → {epub_dir}/\n")

    txt_ok = txt_skip = txt_fail = 0
    epub_ok = epub_skip = epub_fail = 0

    for i, book in enumerate(books, 1):
        book_id    = book["id"]
        title_short = book["title"][:55]
        stem       = f"999_{i}"   # e.g. 999_1, 999_2, ...
        txt_path   = txt_dir  / f"{stem}.txt"
        epub_path  = epub_dir / f"{stem}.epub"

        print(f"[{i}/{len(books)}] {stem} (id:{book_id}) - {title_short}")

        # --- Plain text ---
        if txt_path.exists() and txt_path.stat().st_size > 100:
            print(f"      .txt  SKIP (already exists)")
            txt_skip += 1
        else:
            result = download_book(book_id, txt_path, fmt="txt")
            if result:
                print(f"      .txt  OK ({result.stat().st_size / 1024:.1f} KB)")
                txt_ok += 1
            else:
                txt_fail += 1

        # --- EPUB3 ---
        if epub_path.exists() and epub_path.stat().st_size > 100:
            print(f"      .epub SKIP (already exists)")
            epub_skip += 1
        else:
            result = download_book(book_id, epub_path, fmt="epub3")
            if result:
                print(f"      .epub OK ({result.stat().st_size / 1024:.1f} KB)")
                epub_ok += 1
            else:
                epub_fail += 1

        # Rate limit after each book
        if i < len(books):
            time.sleep(args.delay)

    print(f"\n{'='*60}")
    print(f"  plain_text : OK={txt_ok}  Skip={txt_skip}  Fail={txt_fail}")
    print(f"  epub       : OK={epub_ok}  Skip={epub_skip}  Fail={epub_fail}")
    print(f"  Index      : {index_file.resolve()}")
    print(f"  Saved in   : {base_dir.resolve()}")


if __name__ == "__main__":
    main()
