"""
Post a Reel (video + caption) to Instagram using the instagrapi library.

Requires:
    pip install instagrapi

Env vars:
    IG_USERNAME   — Instagram username
    IG_PASSWORD   — Instagram password
"""
import os
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, RecaptchaChallengeForm, SelectContactPointRecoveryForm


def _challenge_code_handler(username: str, choice: int) -> str:
    """Prompt user to enter the challenge code sent via email/SMS."""
    print(f"\n[Instagram Challenge] A verification code was sent to your email/phone for @{username}")
    return input("Enter the 6-digit verification code: ").strip()


def _login(username: str, password: str, session_path: Path) -> Client:
    """Login to Instagram, reusing session if available."""
    cl = Client()
    cl.challenge_code_handler = _challenge_code_handler

    # Delete stale session and retry fresh on any error
    def _fresh_login():
        if session_path.exists():
            session_path.unlink()
        cl2 = Client()
        cl2.challenge_code_handler = _challenge_code_handler
        try:
            cl2.login(username, password)
        except ChallengeRequired:
            cl2.challenge_resolve(cl2.last_json)
        cl2.dump_settings(session_path)
        return cl2

    # Try reusing saved session first
    if session_path.exists():
        cl.load_settings(session_path)
        try:
            cl.login(username, password)
            cl.account_info()
            return cl
        except ChallengeRequired:
            # Challenge triggered — resolve it
            try:
                cl.challenge_resolve(cl.last_json)
                cl.dump_settings(session_path)
                return cl
            except Exception:
                pass
        except Exception:
            pass

    return _fresh_login()


def post_reel(
    video_path: Path,
    caption: str,
    hashtags: str = "",
    session_dir: Path | None = None,
) -> dict:
    """
    Upload a video as an Instagram Reel.

    Returns dict with media_id and media_code on success.
    """
    username = os.getenv("IG_USERNAME")
    password = os.getenv("IG_PASSWORD")
    if not username or not password:
        raise ValueError("IG_USERNAME and IG_PASSWORD must be set in .env")

    if session_dir is None:
        session_dir = Path(__file__).parent.parent.parent / ".ig_session"
    session_dir.mkdir(exist_ok=True)
    session_path = session_dir / f"{username}.json"

    full_caption = f"{caption}\n\n{hashtags}".strip() if hashtags else caption

    cl = _login(username, password, session_path)

    media = cl.clip_upload(
        path=str(video_path),
        caption=full_caption,
    )

    return {
        "platform": "instagram",
        "media_id": media.id,
        "media_code": media.code,
        "url": f"https://www.instagram.com/reel/{media.code}/",
    }
