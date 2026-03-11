"""
Convert EPUB files to PDF using Calibre's ebook-convert, then upload to Tencent COS.

Source   : gutenberg_books/epub/999_1.epub
Rename   : remove underscore -> 9991.epub -> 9991.pdf
Convert  : ebook-convert 999_1.epub 9991.pdf
COS dest : pdf/9991.pdf

Usage:
    python convert_epub_upload_cos.py              # convert + upload all
    python convert_epub_upload_cos.py --dry-run    # preview only
    python convert_epub_upload_cos.py --convert-only  # convert without uploading
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosServiceError, CosClientError

load_dotenv()

BASE_DIR       = Path(__file__).parent
EPUB_DIR       = BASE_DIR / "gutenberg_books" / "epub"
PDF_OUT_DIR    = BASE_DIR / "gutenberg_books" / "pdf"
COS_PREFIX     = "pdf"

CALIBRE_EXE    = Path("C:/Program Files/Calibre2/ebook-convert.exe")

SECRET_ID  = os.getenv("COS_SECRET_ID")
SECRET_KEY = os.getenv("COS_SECRET_KEY")
REGION     = os.getenv("COS_REGION")
BUCKET     = os.getenv("COS_BUCKET")


def renamed_stem(filename: str) -> str:
    """999_1.epub -> 9991"""
    stem = Path(filename).stem          # 999_1
    return stem.replace("_", "")       # 9991


def get_client() -> CosS3Client:
    config = CosConfig(Region=REGION, SecretId=SECRET_ID, SecretKey=SECRET_KEY)
    return CosS3Client(config)


def convert_epub_to_pdf(epub_path: Path, pdf_path: Path) -> bool:
    """Convert a single EPUB to PDF using Calibre. Returns True on success."""
    try:
        result = subprocess.run(
            [str(CALIBRE_EXE), str(epub_path), str(pdf_path),
             "--pdf-page-numbers"],
            capture_output=True, text=True, timeout=600,
            encoding="utf-8", errors="replace"
        )
        if result.returncode != 0:
            print(f"    [CONVERT ERROR] {epub_path.name}: {result.stderr.strip()[:200]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"    [TIMEOUT] {epub_path.name}")
        return False
    except Exception as e:
        print(f"    [ERROR] {epub_path.name}: {e}")
        return False


def upload_file(client: CosS3Client, local_path: Path, key: str, dry_run: bool) -> bool:
    if dry_run:
        print(f"    [dry-upload] {key}")
        return True
    try:
        client.upload_file(
            Bucket=BUCKET,
            LocalFilePath=str(local_path),
            Key=key,
            PartSize=10,
            MAXThread=5,
        )
        return True
    except (CosServiceError, CosClientError) as e:
        print(f"    [UPLOAD ERROR] {key}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",      action="store_true", help="Preview without converting or uploading")
    parser.add_argument("--convert-only", action="store_true", help="Convert to PDF but skip COS upload")
    args = parser.parse_args()

    if not CALIBRE_EXE.exists():
        print(f"ERROR: Calibre not found at {CALIBRE_EXE}")
        print("Install from: https://calibre-ebook.com/download_windows")
        sys.exit(1)

    if not args.dry_run and not args.convert_only:
        if not all([SECRET_ID, SECRET_KEY, REGION, BUCKET]):
            print("ERROR: Missing COS credentials in .env")
            sys.exit(1)

    PDF_OUT_DIR.mkdir(parents=True, exist_ok=True)

    epub_files = sorted(EPUB_DIR.glob("*.epub"))
    if not epub_files:
        print(f"No .epub files found in {EPUB_DIR}")
        sys.exit(0)

    print(f"Found {len(epub_files)} EPUB files")
    print(f"Output folder : {PDF_OUT_DIR}")
    if not args.convert_only and not args.dry_run:
        print(f"COS target    : {BUCKET}/{COS_PREFIX}/\n")

    client = None
    if not args.dry_run and not args.convert_only:
        client = get_client()

    ok = fail = skip = 0

    for epub_path in epub_files:
        stem    = renamed_stem(epub_path.name)   # 9991
        pdf_name = f"{stem}.pdf"
        pdf_path = PDF_OUT_DIR / pdf_name
        cos_key  = f"{COS_PREFIX}/{pdf_name}"

        print(f"[{epub_path.name}] -> {pdf_name}")

        # --- Convert ---
        if args.dry_run:
            print(f"    [dry-convert] {epub_path.name} -> {pdf_path.name}")
        elif pdf_path.exists():
            print(f"    [skip-convert] PDF already exists")
            skip += 1
        else:
            print(f"    Converting...", end=" ", flush=True)
            success = convert_epub_to_pdf(epub_path, pdf_path)
            if not success:
                fail += 1
                continue
            print("done")

        # --- Upload ---
        if not args.convert_only:
            if not args.dry_run and not pdf_path.exists():
                print(f"    [skip-upload] PDF not found, skipping")
                continue
            print(f"    Uploading -> {cos_key} ...", end=" ", flush=True)
            if upload_file(client, pdf_path, cos_key, args.dry_run):
                print("done")
                ok += 1
            else:
                fail += 1

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Finished.")
    print(f"  Converted/uploaded : {ok + skip}")
    print(f"  Skipped (existing) : {skip}")
    if fail:
        print(f"  Failed             : {fail}")


if __name__ == "__main__":
    main()
