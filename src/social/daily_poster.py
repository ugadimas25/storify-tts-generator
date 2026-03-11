"""
Daily social media posting pipeline.

Reads content from src/content/{audio,image,text}/, combines them into videos,
posts to Instagram Reels and TikTok, and tracks posted items.

Content structure:
    src/content/audio/1.mp3
    src/content/image/1.jpeg
    src/content/text/1.json   ← {"summary": "...", "title": "..."}
    → matched by filename stem (e.g. "1")

    Text file can be .json (reads 'summary' field) or .txt (plain text).

Usage:
    python -m src.social.daily_poster                    # post next item
    python -m src.social.daily_poster --platform ig      # Instagram only
    python -m src.social.daily_poster --platform tiktok  # TikTok only
    python -m src.social.daily_poster --item 5           # post item #5
    python -m src.social.daily_poster --list              # list all content
    python -m src.social.daily_poster --dry-run           # preview only
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from src.social.video_creator import create_video

load_dotenv()

BASE_DIR    = Path(__file__).parent.parent.parent
CONTENT_DIR = BASE_DIR / "src" / "content"
AUDIO_DIR   = CONTENT_DIR / "audio"
IMAGE_DIR   = CONTENT_DIR / "image"
TEXT_DIR    = CONTENT_DIR / "text"
VIDEO_DIR   = CONTENT_DIR / "video"
POSTED_FILE = CONTENT_DIR / "posted.json"

HASHTAGS = "#pewaca #audiobook #bacabuku #ringkasanbuku #bukuaudio #buku"


def _load_posted() -> dict:
    if POSTED_FILE.exists():
        return json.loads(POSTED_FILE.read_text(encoding="utf-8"))
    return {}


def _save_posted(posted: dict):
    POSTED_FILE.write_text(json.dumps(posted, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_caption(text_file: Path) -> str:
    """Read caption from .json (uses 'summary' field) or .txt file."""
    if text_file.suffix == ".json":
        d = json.loads(text_file.read_text(encoding="utf-8"))
        return d.get("summary", d.get("title", "")).strip()
    return text_file.read_text(encoding="utf-8").strip()


def _discover_content() -> list[dict]:
    """Find all content sets matched by filename stem."""
    audio_files = {f.stem: f for f in AUDIO_DIR.glob("*.mp3")}
    image_files = {}
    for ext in ("*.jpeg", "*.jpg", "*.png"):
        for f in IMAGE_DIR.glob(ext):
            image_files[f.stem] = f

    # Support both .json and .txt for text
    text_files = {}
    for ext in ("*.json", "*.txt"):
        for f in TEXT_DIR.glob(ext):
            if f.stem not in text_files:  # .json takes priority
                text_files[f.stem] = f

    # Only include items that have all 3 components
    all_stems = sorted(
        audio_files.keys() & image_files.keys() & text_files.keys(),
        key=lambda s: int(s) if s.isdigit() else s,
    )

    items = []
    for stem in all_stems:
        items.append({
            "id": stem,
            "audio": audio_files[stem],
            "image": image_files[stem],
            "text": text_files[stem],
        })
    return items


def _get_next_item(items: list[dict], posted: dict) -> dict | None:
    """Return the first item not yet posted to ALL platforms."""
    for item in items:
        entry = posted.get(item["id"], {})
        if not entry.get("ig") or not entry.get("tiktok"):
            return item
    return None


def _post_item(item: dict, platforms: list[str], dry_run: bool, posted: dict):
    """Create video and post to specified platforms."""
    stem = item["id"]
    caption = _read_caption(item["text"])
    video_path = VIDEO_DIR / f"{stem}.mp4"

    # Create video if not exists or is an empty/corrupt file (0 bytes)
    if not video_path.exists() or video_path.stat().st_size == 0:
        if video_path.exists():
            print(f"  Video corrupt (0 bytes), recreating: {video_path.name}")
            video_path.unlink()
        else:
            print(f"  Creating video: {video_path.name}")
        if not dry_run:
            create_video(item["image"], item["audio"], video_path)
    else:
        print(f"  Video exists: {video_path.name}")

    entry = posted.get(stem, {})

    for platform in platforms:
        if entry.get(platform):
            print(f"  [{platform}] Already posted, skip")
            continue

        print(f"  [{platform}] Posting...", end=" ", flush=True)

        if dry_run:
            print("(dry run)")
            continue

        try:
            if platform == "ig":
                from src.social.instagram_poster import post_reel
                result = post_reel(video_path, caption, HASHTAGS)
            elif platform == "tiktok":
                from src.social.tiktok_poster import post_tiktok
                result = post_tiktok(video_path, caption, HASHTAGS)
            else:
                print(f"Unknown platform: {platform}")
                continue

            entry[platform] = {
                "posted_at": datetime.now().isoformat(),
                **result,
            }
            posted[stem] = entry
            _save_posted(posted)
            print("OK")

        except Exception as e:
            print(f"ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(description="Daily social media poster")
    parser.add_argument("--platform", choices=["ig", "tiktok", "all"], default="all",
                        help="Platform to post to (default: all)")
    parser.add_argument("--item", type=str, default=None,
                        help="Post specific item by ID (filename stem)")
    parser.add_argument("--list", action="store_true", help="List all content and status")
    parser.add_argument("--dry-run", action="store_true", help="Preview without posting")
    args = parser.parse_args()

    items = _discover_content()
    posted = _load_posted()

    if not items:
        print(f"No content found. Put matched files in:")
        print(f"  {AUDIO_DIR}/  (*.mp3)")
        print(f"  {IMAGE_DIR}/  (*.jpeg)")
        print(f"  {TEXT_DIR}/   (*.txt)")
        return

    if args.list:
        print(f"{'ID':>5}  {'Audio':>12}  {'Image':>12}  {'Text':>8}  {'IG':>10}  {'TikTok':>10}")
        print("-" * 65)
        for item in items:
            entry = posted.get(item["id"], {})
            ig_status = "posted" if entry.get("ig") else "-"
            tt_status = "posted" if entry.get("tiktok") else "-"
            print(f"{item['id']:>5}  {item['audio'].name:>12}  {item['image'].name:>12}  "
                  f"{item['text'].name:>8}  {ig_status:>10}  {tt_status:>10}")
        total_ig = sum(1 for i in items if posted.get(i["id"], {}).get("ig"))
        total_tt = sum(1 for i in items if posted.get(i["id"], {}).get("tiktok"))
        print(f"\nTotal: {len(items)} items | IG posted: {total_ig} | TikTok posted: {total_tt}")
        return

    platforms = ["ig", "tiktok"] if args.platform == "all" else [args.platform]

    if args.item:
        item = next((i for i in items if i["id"] == args.item), None)
        if not item:
            print(f"Item '{args.item}' not found or incomplete (needs audio + image + text)")
            return
    else:
        item = _get_next_item(items, posted)
        if not item:
            print("All items have been posted!")
            return

    print(f"Content #{item['id']}:")
    print(f"  Audio: {item['audio'].name}")
    print(f"  Image: {item['image'].name}")
    caption_preview = _read_caption(item["text"])[:80]
    print(f"  Text:  {caption_preview}...")

    _post_item(item, platforms, args.dry_run, posted)


if __name__ == "__main__":
    main()
