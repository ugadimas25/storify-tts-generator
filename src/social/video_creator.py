"""
Combine a static image + audio file into a video suitable for
Instagram Reels and TikTok (vertical 1080x1920, H.264/AAC).

Uses ffmpeg subprocess — no Python video libraries needed.
"""
import subprocess
from pathlib import Path


def create_video(
    image_path: Path,
    audio_path: Path,
    output_path: Path,
    resolution: str = "1080x1920",
) -> Path:
    """
    Create an MP4 video from a static image and an audio file.

    The video duration matches the audio length.
    Output: H.264 video + AAC audio, vertical format (9:16).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", f"scale='if(gt(iw/ih,9/16),1080,trunc(oh*a/2)*2)':'if(gt(iw/ih,9/16),trunc(ow/a/2)*2,1920)',pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr[-500:]}")

    return output_path
