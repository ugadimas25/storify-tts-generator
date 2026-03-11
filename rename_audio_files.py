"""
Rename audio files from chapter_N.mp3 -> N_chapter_N.mp3
Example: data/audio/2/chapter_1.mp3 -> data/audio/2/1_chapter_1.mp3

Usage:
    python rename_audio_files.py           # dry run (preview only)
    python rename_audio_files.py --apply   # actually rename
"""
import argparse
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
AUDIO_DIR = BASE_DIR / "data" / "audio"

CHAPTER_RE = re.compile(r'^chapter_(\d+)\.mp3$', re.IGNORECASE)


def main(apply: bool):
    files = list(AUDIO_DIR.rglob("*.mp3"))
    renames = []

    for path in sorted(files):
        m = CHAPTER_RE.match(path.name)
        if not m:
            print(f"  [skip] {path.relative_to(BASE_DIR)}  (name doesn't match pattern)")
            continue
        n = m.group(1)
        new_name = f"{n}_{path.name}"
        new_path = path.parent / new_name
        if new_path.exists():
            print(f"  [skip] target already exists: {new_path.relative_to(BASE_DIR)}")
            continue
        renames.append((path, new_path))

    print(f"\n{'DRY RUN — ' if not apply else ''}Renaming {len(renames)} files:\n")
    for old, new in renames:
        print(f"  {old.relative_to(BASE_DIR)}")
        print(f"    -> {new.name}")
        if apply:
            old.rename(new)

    if not apply:
        print(f"\nRun with --apply to actually rename {len(renames)} files.")
    else:
        print(f"\nDone. Renamed {len(renames)} files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually rename files (default: dry run)")
    args = parser.parse_args()
    main(apply=args.apply)
