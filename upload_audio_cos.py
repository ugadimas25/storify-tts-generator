"""
Upload all MP3 files from data/audio/ to Tencent COS bucket.

Local:  data/audio/{book_id}/{N}_chapter_{N}.mp3
COS:    audio/{book_id}/{N}_chapter_{N}.mp3

Usage:
    python upload_audio_cos.py              # upload all files
    python upload_audio_cos.py --dry-run    # preview only (no upload)
    python upload_audio_cos.py --book 290   # upload single book folder
"""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosServiceError, CosClientError

load_dotenv()

BASE_DIR   = Path(__file__).parent
AUDIO_DIR  = BASE_DIR / "data" / "audio"
COS_PREFIX = "audio"   # folder inside the bucket

SECRET_ID  = os.getenv("COS_SECRET_ID")
SECRET_KEY = os.getenv("COS_SECRET_KEY")
REGION     = os.getenv("COS_REGION")
BUCKET     = os.getenv("COS_BUCKET")


def get_client() -> CosS3Client:
    config = CosConfig(Region=REGION, SecretId=SECRET_ID, SecretKey=SECRET_KEY)
    return CosS3Client(config)


def cos_key(local_path: Path) -> str:
    """Convert local path to COS key: audio/{book_id}/{filename}"""
    relative = local_path.relative_to(AUDIO_DIR)
    return f"{COS_PREFIX}/{relative.as_posix()}"


def upload_file(client: CosS3Client, local_path: Path, key: str, dry_run: bool) -> bool:
    if dry_run:
        print(f"  [dry] {key}")
        return True
    try:
        client.upload_file(
            Bucket=BUCKET,
            LocalFilePath=str(local_path),
            Key=key,
            PartSize=10,        # multipart threshold: 10 MB
            MAXThread=5,
        )
        return True
    except (CosServiceError, CosClientError) as e:
        print(f"  [ERROR] {key}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",  action="store_true", help="Preview without uploading")
    parser.add_argument("--book",     type=str, default=None, help="Upload single book folder (e.g. --book 290)")
    args = parser.parse_args()

    if not all([SECRET_ID, SECRET_KEY, REGION, BUCKET]):
        print("ERROR: Missing COS credentials in .env (COS_SECRET_ID, COS_SECRET_KEY, COS_REGION, COS_BUCKET)")
        return

    client = None if args.dry_run else get_client()

    # Collect files to upload
    if args.book:
        search_dir = AUDIO_DIR / args.book
        if not search_dir.exists():
            print(f"ERROR: data/audio/{args.book} not found")
            return
        files = sorted(search_dir.rglob("*.mp3"))
    else:
        files = sorted(AUDIO_DIR.rglob("*.mp3"))

    total   = len(files)
    success = 0
    failed  = 0

    print(f"Bucket  : {BUCKET}")
    print(f"Region  : {REGION}")
    print(f"Prefix  : {COS_PREFIX}/")
    print(f"Files   : {total}")
    print(f"Mode    : {'DRY RUN' if args.dry_run else 'UPLOAD'}\n")

    for i, local_path in enumerate(files, 1):
        key = cos_key(local_path)
        size_kb = local_path.stat().st_size // 1024
        print(f"[{i}/{total}] {key}  ({size_kb} KB)", end=" ... " if not args.dry_run else "\n")
        ok = upload_file(client, local_path, key, args.dry_run)
        if not args.dry_run:
            if ok:
                success += 1
                print("OK")
            else:
                failed += 1

    print(f"\n{'Preview' if args.dry_run else 'Done'}:")
    if not args.dry_run:
        print(f"  Uploaded : {success}")
        print(f"  Failed   : {failed}")
    else:
        print(f"  Would upload {total} files to {BUCKET}/{COS_PREFIX}/")


if __name__ == "__main__":
    main()
