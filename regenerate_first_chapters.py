"""
Regenerate the first audio file (ascending by filename) of each book
using ElevenLabs TTS, replacing the existing file in data/audio/<book_id>/.
"""

import json
import os
import random
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

from src.models.chapter import ChapterSummary

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
SUMMARIES_DIR = BASE_DIR / "data" / "summaries"
AUDIO_DIR = BASE_DIR / "data" / "audio"

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

_VOICE_IDS_RAW = os.getenv("ELEVENLABS_VOICE_IDS", "")
ELEVENLABS_VOICE_IDS: list[str] = [
    v.strip() for v in _VOICE_IDS_RAW.split(",") if v.strip()
]
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "kSzQ9oZF2iytkgNNztpH")

# Map voice IDs to names for logging
VOICE_NAMES = dict(
    zip(
        [v.strip() for v in os.getenv("ELEVENLABS_VOICE_IDS", "").split(",") if v.strip()],
        [v.strip() for v in os.getenv("ELEVENLABS_VOICE_NAMES", "").split(",") if v.strip()],
    )
)


def pick_voice_id() -> str:
    if ELEVENLABS_VOICE_IDS:
        return random.choice(ELEVENLABS_VOICE_IDS)
    return ELEVENLABS_VOICE_ID


def main() -> None:
    if not ELEVENLABS_API_KEY:
        print("ERROR: ELEVENLABS_API_KEY not set in .env")
        return

    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    # Get all book folders in summaries
    book_dirs = sorted(
        [d for d in SUMMARIES_DIR.iterdir() if d.is_dir()],
        key=lambda p: p.name,
    )

    print(f"Found {len(book_dirs)} book(s) in {SUMMARIES_DIR}\n")

    for i, book_dir in enumerate(book_dirs, 1):
        book_id = book_dir.name

        # Find first summary file (ascending by name)
        summary_files = sorted(book_dir.glob("*.json"), key=lambda p: p.name)
        if not summary_files:
            print(f"[{i}/{len(book_dirs)}] {book_id}: no summary files, skipping")
            continue

        first_file = summary_files[0]

        # Load summary
        data = json.loads(first_file.read_text(encoding="utf-8"))
        summary = ChapterSummary(**data)

        # Output path
        audio_out_dir = AUDIO_DIR / book_id
        audio_out_dir.mkdir(parents=True, exist_ok=True)
        output_path = audio_out_dir / f"chapter_{summary.chapter}.mp3"

        # Pick voice
        voice_id = pick_voice_id()
        voice_label = VOICE_NAMES.get(voice_id, voice_id)

        print(
            f"[{i}/{len(book_dirs)}] Book {book_id} → "
            f"{first_file.name} → voice: {voice_label}"
        )

        # Generate audio
        audio_stream = client.text_to_speech.convert(
            voice_id=voice_id,
            text=summary.summary,
            model_id=ELEVENLABS_MODEL_ID,
            output_format="mp3_44100_128",
        )

        with open(output_path, "wb") as f:
            for chunk in audio_stream:
                f.write(chunk)

        status = "replaced" if output_path.exists() else "created"
        print(f"       ✓ {output_path.name} ({status})")

    print(f"\nDone! Processed {len(book_dirs)} book(s).")


if __name__ == "__main__":
    main()
