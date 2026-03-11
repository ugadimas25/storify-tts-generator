"""
Upload a video to TikTok using tiktok-uploader (Selenium-based).

Requires:
    pip install tiktok-uploader

Env vars:
    TIKTOK_SESSION_ID — sessionid cookie from browser (get from DevTools)

Notes:
    - tiktok-uploader uses Selenium + browser cookies for auth
    - Get sessionid: login to TikTok in Chrome → DevTools → Application →
      Cookies → tiktok.com → copy "sessionid" value
"""
import os
import tempfile
from pathlib import Path

from tiktok_uploader.upload import upload_video


def _write_cookie_file(session_id: str) -> Path:
    """Write sessionid as a Netscape-format cookie file for tiktok-uploader."""
    cookie_dir = Path(__file__).parent.parent.parent / ".tiktok_session"
    cookie_dir.mkdir(exist_ok=True)
    cookie_file = cookie_dir / "cookies.txt"
    # Netscape cookie format: domain, flag, path, secure, expiry, name, value
    content = (
        "# Netscape HTTP Cookie File\n"
        f".tiktok.com\tTRUE\t/\tTRUE\t9999999999\tsessionid\t{session_id}\n"
    )
    cookie_file.write_text(content, encoding="utf-8")
    return cookie_file


def post_tiktok(
    video_path: Path,
    caption: str,
    hashtags: str = "",
) -> dict:
    """
    Upload a video to TikTok.

    Returns dict with status on success.
    """
    session_id = os.getenv("TIKTOK_SESSION_ID")
    if not session_id:
        raise ValueError("TIKTOK_SESSION_ID must be set in .env")

    full_caption = f"{caption} {hashtags}".strip() if hashtags else caption

    cookie_file = _write_cookie_file(session_id)

    upload_video(
        filename=str(video_path),
        description=full_caption,
        cookies=str(cookie_file),
        headless=False,   # set True after confirming it works
    )

    return {
        "platform": "tiktok",
        "status": "uploaded",
        "caption": full_caption[:50],
    }
