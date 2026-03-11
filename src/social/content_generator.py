"""
Generate social media content for a book: template image + text + audio.

Fetches book info from the database, downloads cover from COS, creates
a branded template image, and copies audio from COS — all into src/content/.

Usage:
    python -m src.social.content_generator --book 99915         # single book
    python -m src.social.content_generator --all                # all books with audio
    python -m src.social.content_generator --book 99915 --dry-run
"""
import argparse
import io
import json
import os
import textwrap
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from qcloud_cos import CosConfig, CosS3Client

load_dotenv()

BASE_DIR    = Path(__file__).parent.parent.parent
CONTENT_DIR = BASE_DIR / "src" / "content"
AUDIO_DIR   = CONTENT_DIR / "audio"
IMAGE_DIR   = CONTENT_DIR / "image"
TEXT_DIR    = CONTENT_DIR / "text"

# Template dimensions (vertical 9:16)
WIDTH, HEIGHT = 1080, 1920

# Colors
BG_COLOR = "#FFFFFF"
PRIMARY_COLOR = "#2E3A7D"  # Dark blue (matching app theme)
ACCENT_COLOR = "#4CAF50"   # Green badge
TEXT_COLOR = "#333333"
SUBTITLE_COLOR = "#666666"
BADGE_TEXT = "#FFFFFF"


def _get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def _get_cos():
    config = CosConfig(
        Region=os.getenv("COS_REGION"),
        SecretId=os.getenv("COS_SECRET_ID"),
        SecretKey=os.getenv("COS_SECRET_KEY"),
    )
    return CosS3Client(config), os.getenv("COS_BUCKET")


def _download_cover(cos_client, bucket: str, book_id: int) -> Image.Image | None:
    """Download cover image from COS. Tries jpeg, jpg, png."""
    for ext in ("jpeg", "jpg", "png"):
        key = f"image/{book_id}.{ext}"
        try:
            resp = cos_client.get_object(Bucket=bucket, Key=key)
            data = resp["Body"].get_raw_stream().read()
            return Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            continue
    return None


def _download_audio(cos_client, bucket: str, book_id: int, dest: Path) -> bool:
    """Download chapter 1 audio from COS."""
    key = f"audio/{book_id}/1_chapter_1.mp3"
    try:
        resp = cos_client.get_object(Bucket=bucket, Key=key)
        data = resp["Body"].get_raw_stream().read()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except Exception:
        return False


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a font, fallback to default if not available."""
    font_names = [
        "C:/Windows/Fonts/segoeui.ttf",     # Windows
        "C:/Windows/Fonts/segoeuib.ttf",     # Windows bold
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",   # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux bold
    ]
    if bold:
        font_names = [f for f in font_names if "Bold" in f or "bold" in f or "segoeuib" in f] + font_names

    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _draw_rounded_rect(draw: ImageDraw.Draw, xy, radius, fill):
    """Draw a rounded rectangle."""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def generate_template(
    cover: Image.Image,
    title: str,
    author: str,
    category: str,
    output_path: Path,
) -> Path:
    """
    Generate a branded book template image similar to the Pewaca app.

    Layout (1080x1920):
    - Top gradient/solid background
    - Centered book cover with shadow
    - Title
    - Author
    - Category badge + duration
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # --- Background gradient (top section) ---
    gradient_height = 1100
    for y in range(gradient_height):
        ratio = y / gradient_height
        r = int(46 + (255 - 46) * ratio)   # #2E -> FF
        g = int(58 + (255 - 58) * ratio)   # #3A -> FF
        b = int(125 + (255 - 125) * ratio) # #7D -> FF
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # --- Book cover (centered, with shadow) ---
    cover_max_w, cover_max_h = 600, 800
    cover_resized = cover.copy()
    cover_resized.thumbnail((cover_max_w, cover_max_h), Image.LANCZOS)
    cw, ch = cover_resized.size

    cover_x = (WIDTH - cw) // 2
    cover_y = 160

    # Shadow
    shadow = Image.new("RGBA", (cw + 30, ch + 30), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        [10, 10, cw + 20, ch + 20], radius=12, fill=(0, 0, 0, 80)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(15))
    img.paste(shadow.convert("RGB"), (cover_x - 10, cover_y + 5), shadow.split()[3])

    # Cover with rounded corners mask
    cover_rgba = cover_resized.convert("RGBA")
    mask = Image.new("L", (cw, ch), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, cw, ch], radius=12, fill=255)
    img.paste(cover_resized, (cover_x, cover_y), mask)

    # --- Title ---
    font_title = _load_font(52, bold=True)
    font_author = _load_font(36)
    font_badge = _load_font(28, bold=True)
    font_desc_label = _load_font(30)

    text_y = cover_y + ch + 40

    # Word-wrap title
    wrapped_title = textwrap.fill(title, width=28)
    title_bbox = draw.multiline_textbbox((0, 0), wrapped_title, font=font_title)
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    title_x = (WIDTH - title_w) // 2

    draw.multiline_text(
        (title_x, text_y), wrapped_title,
        fill=PRIMARY_COLOR, font=font_title, align="center"
    )

    # --- Author ---
    author_y = text_y + title_h + 24
    author_bbox = draw.textbbox((0, 0), author, font=font_author)
    author_w = author_bbox[2] - author_bbox[0]
    draw.text(
        ((WIDTH - author_w) // 2, author_y), author,
        fill=SUBTITLE_COLOR, font=font_author
    )

    # --- Category badge + duration ---
    badge_y = author_y + 60
    badge_text = category
    badge_bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    badge_w = badge_bbox[2] - badge_bbox[0] + 40
    badge_h = badge_bbox[3] - badge_bbox[1] + 20
    badge_x = (WIDTH - badge_w) // 2 - 50

    _draw_rounded_rect(
        draw, [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
        radius=badge_h // 2, fill=ACCENT_COLOR
    )
    draw.text(
        (badge_x + 20, badge_y + 8), badge_text,
        fill=BADGE_TEXT, font=font_badge
    )

    # Duration text next to badge
    duration_text = "Audiobook"
    dur_bbox = draw.textbbox((0, 0), duration_text, font=font_desc_label)
    dur_x = badge_x + badge_w + 20
    draw.text((dur_x, badge_y + 8), duration_text, fill=SUBTITLE_COLOR, font=font_desc_label)

    # --- Storify branding at bottom ---
    font_brand = _load_font(32, bold=True)
    brand_text = "STORIFY"
    brand_bbox = draw.textbbox((0, 0), brand_text, font=font_brand)
    brand_w = brand_bbox[2] - brand_bbox[0]
    draw.text(
        ((WIDTH - brand_w) // 2, HEIGHT - 120), brand_text,
        fill=PRIMARY_COLOR, font=font_brand
    )

    font_tagline = _load_font(24)
    tagline = "Dengarkan ringkasan buku favoritmu"
    tag_bbox = draw.textbbox((0, 0), tagline, font=font_tagline)
    tag_w = tag_bbox[2] - tag_bbox[0]
    draw.text(
        ((WIDTH - tag_w) // 2, HEIGHT - 80), tagline,
        fill=SUBTITLE_COLOR, font=font_tagline
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "JPEG", quality=95)
    return output_path


def generate_content(book_id: int, dry_run: bool = False) -> bool:
    """
    Generate all content files for a book:
      - src/content/image/{book_id}.jpeg  (template image)
      - src/content/text/{book_id}.json   (caption text)
      - src/content/audio/{book_id}.mp3   (chapter 1 audio)
    """
    # Check if already complete
    img_path = IMAGE_DIR / f"{book_id}.jpeg"
    txt_path = TEXT_DIR / f"{book_id}.json"
    audio_path = AUDIO_DIR / f"{book_id}.mp3"

    if img_path.exists() and txt_path.exists() and audio_path.exists():
        print(f"  [{book_id}] Already complete, skip")
        return True

    # Fetch from DB
    conn = _get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT fix_title, author, category, description "
            "FROM public.books_list WHERE id = %s",
            (book_id,)
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        print(f"  [{book_id}] Not found in database")
        return False

    title, author, category, description = row
    if not title:
        print(f"  [{book_id}] No title in database")
        return False

    print(f"  [{book_id}] {title} — {author}")

    if dry_run:
        print(f"    (dry run) Would generate image, text, audio")
        return True

    cos_client, bucket = _get_cos()

    # 1. Download cover & generate template image
    if not img_path.exists():
        cover = _download_cover(cos_client, bucket, book_id)
        if not cover:
            print(f"    [WARN] No cover image in COS for {book_id}")
            return False
        generate_template(cover, title, author or "", category or "Book", img_path)
        print(f"    Image: {img_path.name}")

    # 2. Generate text JSON
    if not txt_path.exists():
        caption_data = {
            "title": title,
            "author": author or "",
            "category": category or "",
            "summary": description or title,
        }
        TEXT_DIR.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(
            json.dumps(caption_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"    Text:  {txt_path.name}")

    # 3. Download audio
    if not audio_path.exists():
        if _download_audio(cos_client, bucket, book_id, audio_path):
            print(f"    Audio: {audio_path.name}")
        else:
            print(f"    [WARN] No audio in COS for {book_id}")
            return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Generate social media content from DB + COS")
    parser.add_argument("--book", type=int, default=None, help="Generate for a single book ID")
    parser.add_argument("--all", action="store_true", help="Generate for all books with audio")
    parser.add_argument("--dry-run", action="store_true", help="Preview without generating")
    args = parser.parse_args()

    if not args.book and not args.all:
        parser.print_help()
        return

    if args.book:
        generate_content(args.book, args.dry_run)
        return

    # --all: get all books that have audio
    conn = _get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM public.books_list "
            "WHERE is_have_audio = 'yes' ORDER BY id"
        )
        book_ids = [r[0] for r in cur.fetchall()]
    finally:
        conn.close()

    print(f"Found {len(book_ids)} books with audio")
    success = 0
    for book_id in book_ids:
        if generate_content(book_id, args.dry_run):
            success += 1
    print(f"\nDone: {success}/{len(book_ids)} generated")


if __name__ == "__main__":
    main()
