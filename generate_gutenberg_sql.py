"""
Generate SQL INSERT statements for Gutenberg books into books_list table.
Extracts Title and Author from each file's Gutenberg header.
Uses OpenAI to classify each book into a category.

Usage:
    python generate_gutenberg_sql.py
    python generate_gutenberg_sql.py --output insert_gutenberg.sql
"""
import argparse
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_DIR = Path(__file__).parent
GUTENBERG_DIR = BASE_DIR / "gutenberg_books" / "plain_text"

CATEGORIES = [
    "Business", "Finance", "History", "Psychology", "Religion",
    "Productivity", "Fiction", "Lifestyle", "Leadership", "Communication",
    "Technology", "Self-Improvement", "Education",
]


def extract_meta(text: str) -> tuple[str, str]:
    """Extract Title and Author from Gutenberg header (first 2000 chars)."""
    header = text[:2000]
    title_match  = re.search(r'^Title:\s*(.+)',  header, re.MULTILINE)
    author_match = re.search(r'^Author:\s*(.+)', header, re.MULTILINE)
    title  = title_match.group(1).strip()[:128] if title_match  else ""
    author = author_match.group(1).strip()[:50]  if author_match else ""
    return title, author


def classify_books_batch(books: list[dict]) -> list[str]:
    """Classify a batch of books into categories using a single OpenAI call."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    numbered = "\n".join(
        f"{i+1}. Title: {b['title']} | Author: {b['author']}"
        for i, b in enumerate(books)
    )
    cat_list = ", ".join(CATEGORIES)

    prompt = f"""Classify each book below into EXACTLY one category from this list:
{cat_list}

Books:
{numbered}

Reply with a JSON array of {len(books)} strings, one category per book, in the same order.
Example: ["Fiction", "History", "Religion"]
Only use categories from the list above. No explanation."""

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content.strip()
    # Extract JSON array from response
    m = re.search(r'\[.*\]', raw, re.DOTALL)
    if not m:
        raise ValueError(f"Could not parse categories from response: {raw}")
    categories = json.loads(m.group(0))
    # Validate — fallback mapping for common non-list categories
    _FALLBACK_MAP = {
        "Philosophy": "Education",
        "Biography": "Education",
        "Memoir": "Lifestyle",
        "Autobiography": "Lifestyle",
        "Biography & Memoir": "Education",
        "Science": "Education",
        "Economics": "Finance",
        "Politics": "History",
        "Travel": "Lifestyle",
        "Art": "Lifestyle",
        "Poetry": "Fiction",
        "Drama": "Fiction",
        "Classics": "Fiction",
    }
    for i, cat in enumerate(categories):
        if cat not in CATEGORIES:
            mapped = _FALLBACK_MAP.get(cat, "Fiction")
            print(f"    [warn] Unknown category {cat!r} for book {i+1}, mapping to '{mapped}'")
            categories[i] = mapped
    return categories


def escape_sql(s: str) -> str:
    return s.replace("'", "''")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="insert_gutenberg.sql")
    parser.add_argument("--batch-size", type=int, default=20,
                        help="Books per OpenAI classification call (default: 20)")
    args = parser.parse_args()

    txt_files = sorted(GUTENBERG_DIR.glob("*.txt"))
    txt_files = [f for f in txt_files if f.name != "index.txt"]

    # Extract meta for all books
    books = []
    for txt in txt_files:
        text = txt.read_text(encoding="utf-8", errors="replace")
        title, author = extract_meta(text)
        books.append({
            "file": txt,
            "book_id": int(txt.stem.replace("_", "")),
            "title": title,
            "author": author,
        })

    # Classify in batches
    print(f"Classifying {len(books)} books in batches of {args.batch_size}...")
    categories = []
    for i in range(0, len(books), args.batch_size):
        batch = books[i:i + args.batch_size]
        print(f"  Batch {i // args.batch_size + 1}: books {i+1}-{i+len(batch)}")
        batch_cats = classify_books_batch(batch)
        categories.extend(batch_cats)

    # Build SQL
    lines = [
        "-- Gutenberg books INSERT",
        f"-- Generated from {GUTENBERG_DIR}",
        f"-- Total: {len(books)} files",
        "",
    ]

    skipped = []
    for book, category in zip(books, categories):
        if not book["title"]:
            skipped.append(book["file"].name)
            lines.append(f"-- SKIPPED (no title found): {book['file'].name}")
            continue

        lines.append(
            f"INSERT INTO public.books_list (id, fix_title, author, category) VALUES "
            f"({book['book_id']}, '{escape_sql(book['title'])}', "
            f"'{escape_sql(book['author'])}', '{escape_sql(category)}');"
        )

    output = Path(args.output)
    output.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nSaved: {output}")
    print(f"  Inserted : {len(books) - len(skipped)}")
    print(f"  Skipped  : {len(skipped)}")
    if skipped:
        for s in skipped:
            print(f"    - {s}")


if __name__ == "__main__":
    main()

