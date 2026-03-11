"""
Rename and upload EPUB files from gutenberg_books/epub/ to Tencent COS.

Rename rule: remove underscore from filename
  999_1.epub  -> 9991.epub
  999_10.epub -> 99910.epub

COS destination: pdf/{renamed}.epub

Usage:
    python upload_epub_cos.py              # upload all
    python upload_epub_cos.py --dry-run    # preview only
"""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosServiceError, CosClientError

load_dotenv()

BASE_DIR   = Path(__file__).parent
EPUB_DIR   = BASE_DIR / "gutenberg_books" / "epub"
COS_PREFIX = "pdf"

SECRET_ID  = os.getenv("COS_SECRET_ID")
SECRET_KEY = os.getenv("COS_SECRET_KEY")
REGION     = os.getenv("COS_REGION")
BUCKET     = os.getenv("COS_BUCKET")


def renamed(filename: str) -> str:
    """999_1.epub -> 9991.epub"""
    return filename.replace("_", "")


def get_client() -> CosS3Client:
    config = CosConfig(Region=REGION, SecretId=SECRET_ID, SecretKey=SECRET_KEY)
    return CosS3Client(config)


def upload_file(client: CosS3Client, local_path: Path, key: str, dry_run: bool) -> bool:
    if dry_run:
        print(f"  [dry] {key}")
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
        print(f"  [ERROR] {key}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    args = parser.parse_args()

    if not all([SECRET_ID, SECRET_KEY, REGION, BUCKET]):
        print("ERROR: Missing COS credentials in .env")
        return

    epub_files = sorted(EPUB_DIR.glob("*.epub"))
    if not epub_files:
        print(f"No .epub files found in {EPUB_DIR}")
        return

    print(f"Found {len(epub_files)} EPUB files")
    print(f"Target: COS {BUCKET}/{COS_PREFIX}/\n")

    client = None if args.dry_run else get_client()

    ok = fail = 0
    for local_path in epub_files:
        cos_filename = renamed(local_path.name)
        key = f"{COS_PREFIX}/{cos_filename}"
        print(f"  {local_path.name} -> {key}")
        if upload_file(client, local_path, key, args.dry_run):
            ok += 1
        else:
            fail += 1

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Done.")
    print(f"  Uploaded : {ok}")
    if fail:
        print(f"  Failed   : {fail}")


if __name__ == "__main__":
    main()
