import os
import random
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import texttospeech

from src.models.chapter import ChapterSummary

load_dotenv()

# Chirp 3: HD voice name format: {language_code}-Chirp3-HD-{VoiceName}
DEFAULT_LANGUAGE_CODE = os.getenv("TTS_LANGUAGE_CODE", "id-ID")
DEFAULT_VOICE_NAME = os.getenv("TTS_VOICE_NAME", "id-ID-Chirp3-HD-Kore")
RANDOM_VOICE = os.getenv("TTS_RANDOM_VOICE", "true").lower() == "true"

# Full list of available Chirp 3: HD voices
AVAILABLE_VOICES = [
    "Achernar", "Achird", "Algenib", "Algieba", "Alnilam",
    "Aoede", "Autonoe", "Callirrhoe", "Charon", "Despina",
    "Enceladus", "Erinome", "Fenrir", "Gacrux", "Iapetus",
    "Kore", "Laomedeia", "Leda", "Orus", "Puck",
    "Pulcherrima", "Rasalgethi", "Sadachbia", "Sadaltager",
    "Schedar", "Sulafat", "Umbriel", "Vindemiatrix",
    "Zephyr", "Zubenelgenubi",
]


def get_voice_name(language_code: str, voice_name: str | None = None) -> str:
    """Return voice name, picking randomly if TTS_RANDOM_VOICE=true."""
    if RANDOM_VOICE:
        chosen = random.choice(AVAILABLE_VOICES)
        return f"{language_code}-Chirp3-HD-{chosen}"
    return voice_name or DEFAULT_VOICE_NAME


def synthesize_speech(
    summary: ChapterSummary,
    output_dir: str | Path,
    language_code: str = DEFAULT_LANGUAGE_CODE,
    voice_name: str = DEFAULT_VOICE_NAME,
) -> Path:
    """Convert a chapter summary to an MP3 audio file using Google Cloud TTS."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = texttospeech.TextToSpeechClient()

    # Pick a random voice per chapter if enabled
    resolved_voice = get_voice_name(language_code, voice_name)
    print(f"       Chapter {summary.chapter} → voice: {resolved_voice}")

    ssml = f"<speak>{summary.summary}<break time='1s'/></speak>"

    synthesis_input = texttospeech.SynthesisInput(ssml=ssml)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=resolved_voice,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )

    output_path = output_dir / f"chapter_{summary.chapter}.mp3"
    with open(output_path, "wb") as f:
        f.write(response.audio_content)

    return output_path


def synthesize_all(
    summaries: list[ChapterSummary],
    output_dir: str | Path,
    language_code: str = "id-ID",
    voice_name: str = "id-ID-Wavenet-D",
) -> list[Path]:
    """Generate audio for all chapter summaries."""
    from tqdm import tqdm

    audio_paths: list[Path] = []
    for summary in tqdm(summaries, desc="Generating audio"):
        path = synthesize_speech(summary, output_dir, language_code, voice_name)
        audio_paths.append(path)
    return audio_paths
