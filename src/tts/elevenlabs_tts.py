import os
import random
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

from src.models.chapter import ChapterSummary

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

# Comma-separated voice IDs to randomly pick from, e.g. "kSzQ9oZF2iytkgNNztpH,eESTQeTcGUli0jYysKtx"
# Maps to: Kanna, Senandika
_VOICE_IDS_RAW = os.getenv("ELEVENLABS_VOICE_IDS", "")
ELEVENLABS_VOICE_IDS: list[str] = [
    v.strip() for v in _VOICE_IDS_RAW.split(",") if v.strip()
]

# Fallback single voice ID (Kanna)
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "kSzQ9oZF2iytkgNNztpH")


def _pick_voice_id() -> str:
    """Randomly pick a voice ID from ELEVENLABS_VOICE_IDS, or use the single fallback."""
    if ELEVENLABS_VOICE_IDS:
        return random.choice(ELEVENLABS_VOICE_IDS)
    return ELEVENLABS_VOICE_ID


def synthesize_speech_elevenlabs(
    summary: ChapterSummary,
    output_dir: str | Path,
    model_id: str = ELEVENLABS_MODEL_ID,
) -> Path:
    """Convert a chapter summary to an MP3 audio file using ElevenLabs TTS."""
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY is not set in environment variables.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    voice_id = _pick_voice_id()

    print(f"       Chapter {summary.chapter} → ElevenLabs voice: {voice_id}")

    audio_stream = client.text_to_speech.convert(
        voice_id=voice_id,
        text=summary.summary,
        model_id=model_id,
        output_format="mp3_44100_128",
    )

    output_path = output_dir / f"chapter_{summary.chapter}.mp3"
    with open(output_path, "wb") as f:
        for chunk in audio_stream:
            f.write(chunk)

    return output_path
