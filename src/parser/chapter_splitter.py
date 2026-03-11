import re

from src.models.chapter import Chapter


# ---------------------------------------------------------------------------
# Roman numeral conversion
# ---------------------------------------------------------------------------
_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def _roman_to_int(s: str) -> int | None:
    """Convert a Roman numeral string to an integer (e.g. 'XIV' → 14)."""
    s = s.upper().strip()
    if not s or not all(c in _ROMAN_VALUES for c in s):
        return None
    total = 0
    prev = 0
    for c in reversed(s):
        val = _ROMAN_VALUES[c]
        total = total - val if val < prev else total + val
        prev = val
    return total


# ---------------------------------------------------------------------------
# Ordinal word → int  (Indonesian + English)
# ---------------------------------------------------------------------------
ORDINAL_WORDS: dict[str, int] = {
    # Indonesian
    "satu": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5,
    "enam": 6, "tujuh": 7, "delapan": 8, "sembilan": 9, "sepuluh": 10,
    "sebelas": 11, "dua belas": 12, "tiga belas": 13, "empat belas": 14,
    "lima belas": 15, "enam belas": 16, "tujuh belas": 17,
    "delapan belas": 18, "sembilan belas": 19, "dua puluh": 20,
    # English cardinal
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
    # English ordinal
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
}

_ORDINAL_PATTERN = "|".join(
    re.escape(k) for k in sorted(ORDINAL_WORDS, key=len, reverse=True)
)

# English ordinals used in reversed patterns like "FIRST ACT", "SECOND BOOK"
_REVERSED_ORDINAL_RE = "|".join(
    re.escape(w) for w in [
        "first", "second", "third", "fourth", "fifth",
        "sixth", "seventh", "eighth", "ninth", "tenth",
        "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth",
        "sixteenth", "seventeenth", "eighteenth", "nineteenth", "twentieth",
    ]
)

# ---------------------------------------------------------------------------
# Heading keywords in priority order (most granular → broadest).
# SECTION is excluded because it almost always matches Gutenberg boilerplate.
# ---------------------------------------------------------------------------
HEADING_KEYWORDS = [
    "CHAPTER", "BAB",       # chapters (novels / Indonesian)
    "LETTER",                # epistolary novels
    "CANTO",                 # poetry
    "STAVE",                 # A Christmas Carol
    "ACT",                   # plays
    "SCENE",                 # plays (sub-unit)
    "BOOK",                  # multi-book works
    "PART",                  # multi-part works
    "VOLUME",                # multi-volume works
]

# Roman-numeral character class  (with word-boundary to avoid partial matches)
_ROMAN_RE = r"[IVXLCDM]+\b"

# Minimum content length to keep a section (filters out TOC entries)
_MIN_CONTENT_LENGTH = 600


def _build_heading_pattern(keyword: str) -> str:
    """Build a regex for one heading keyword.

    Captures:
      1 – full heading text  (e.g. "CHAPTER XIV")
      2 – Arabic digit       (e.g. "14")       *or None*
      3 – Roman numeral      (e.g. "XIV")      *or None*
      4 – Ordinal word       (e.g. "fourteen")  *or None*
      5 – Title rest          (everything after separator on the same line)
    """
    return (
        rf"^\s*"
        rf"({keyword}\s+(?:(\d+)|({_ROMAN_RE})|({_ORDINAL_PATTERN})))"
        rf"\s*[:\.\-—]?\s*(.*)"
    )


def _parse_number(
    digit_str: str | None,
    roman_str: str | None,
    word_str: str | None,
) -> int | None:
    """Convert whichever capture group matched into an int."""
    if digit_str:
        return int(digit_str)
    if roman_str:
        return _roman_to_int(roman_str)
    if word_str:
        return ORDINAL_WORDS.get(word_str.lower().strip())
    return None


def _build_reversed_heading_pattern(keyword: str) -> str:
    """Build a regex for reversed ordinal headings like 'FIRST ACT'."""
    return (
        rf"^\s*"
        rf"(({_REVERSED_ORDINAL_RE})\s+{keyword})"
        rf"\s*[:.\.\-\u2014]?\s*(.*)"
    )


def _find_headings(text: str, keyword: str) -> list[tuple[str, str, int]]:
    """Find all headings of *keyword* type in *text*.

    Returns list of (heading_text, title_rest, start_position).
    Handles both standard (CHAPTER IV) and reversed (FOURTH CHAPTER) patterns.
    """
    results: list[tuple[str, str, int]] = []
    seen_positions: set[int] = set()

    # Pattern 1: KEYWORD + NUMBER/ROMAN/ORDINAL (e.g. "CHAPTER 4", "BOOK IV")
    pattern = _build_heading_pattern(keyword)
    for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
        num = _parse_number(m.group(2), m.group(3), m.group(4))
        if num is None:
            continue
        heading_text = m.group(1).strip()
        title_rest = (m.group(5) or "").strip()
        results.append((heading_text, title_rest, m.start()))
        seen_positions.add(m.start())

    # Pattern 2: ORDINAL + KEYWORD (e.g. "FIRST ACT", "SECOND PART")
    # Only for keywords where reversed ordinals are common in literature.
    if keyword.upper() in {"ACT", "PART"}:
        rev_pattern = _build_reversed_heading_pattern(keyword)
        for m in re.finditer(rev_pattern, text, re.IGNORECASE | re.MULTILINE):
            if m.start() in seen_positions:
                continue
            ordinal_word = m.group(2).lower().strip()
            num = ORDINAL_WORDS.get(ordinal_word)
            if num is None:
                continue
            heading_text = m.group(1).strip()
            title_rest = (m.group(3) or "").strip()
            results.append((heading_text, title_rest, m.start()))

    return results


def _remove_toc_cluster(
    headings: list[tuple[str, str, int]], text_length: int
) -> list[tuple[str, str, int]]:
    """Remove heading matches that belong to a Table-of-Contents cluster.

    TOC entries appear as a dense cluster of headings near the start of the
    text with very little content between them.  Real chapter headings are
    spread throughout the text with substantial content between them.
    """
    if len(headings) < 3:
        return headings

    # Only consider clusters in the first 15% of the text
    if headings[0][2] > text_length * 0.15:
        return headings

    # Walk forward from the start; consecutive small gaps indicate TOC
    toc_end = -1  # index of last heading whose gap-to-next is tiny
    for i in range(len(headings) - 1):
        gap = headings[i + 1][2] - headings[i][2]
        if gap < 500:
            toc_end = i
        else:
            break

    # Need at least 2 consecutive small gaps (3 headings) to call it a TOC
    if toc_end < 1:
        return headings

    # Decide whether heading[toc_end+1] is the last TOC entry or first real one.
    # If its title_rest looks like another heading of the same type
    # (e.g. "Chapter 1\tChapter 2" on one TOC line), it's a TOC entry.
    border = headings[toc_end + 1]
    title_rest = border[1]
    border_is_toc = bool(
        re.match(r'(?i)\S+\s+(?:\d+|[IVXLCDM]+\b)', title_rest.strip())
    ) if title_rest else False

    cluster_end = toc_end + 2 if border_is_toc else toc_end + 1
    remaining = headings[cluster_end:]
    return remaining if remaining else headings


def split_chapters(text: str) -> list[Chapter]:
    """Split full text into chapters using auto-detected heading type.

    Tries each heading keyword in priority order and picks the type that
    produces the most matches.  Chapters are numbered sequentially (1, 2, 3 …)
    regardless of the original heading numbers, so works even when chapter
    numbers restart across books/volumes.
    """
    text_length = len(text)

    # --- pick the heading type with the most matches (after TOC removal) ---
    best_keyword: str | None = None
    best_splits: list[tuple[str, str, int]] = []

    for kw in HEADING_KEYWORDS:
        splits = _find_headings(text, kw)
        splits.sort(key=lambda x: x[2])
        splits = _remove_toc_cluster(splits, text_length)
        if len(splits) > len(best_splits):
            best_splits = splits
            best_keyword = kw

    if not best_splits:
        return [Chapter(chapter=1, title="Full Text", content=text.strip())]

    # --- sort by position ---
    best_splits.sort(key=lambda x: x[2])

    # --- build Chapter list, filtering out near-empty TOC entries ---
    chapters: list[Chapter] = []
    for i, (heading, title, start) in enumerate(best_splits):
        heading_end = (
            text.index("\n", start) + 1 if "\n" in text[start:] else len(text)
        )
        end = best_splits[i + 1][2] if i + 1 < len(best_splits) else len(text)
        content = text[heading_end:end].strip()

        # Skip likely TOC entries (very short content between consecutive headings)
        if len(content) < _MIN_CONTENT_LENGTH and i + 1 < len(best_splits):
            continue

        chapter_num = len(chapters) + 1
        if not title:
            title = heading  # e.g. "BOOK IV", "ACT II"

        chapters.append(Chapter(chapter=chapter_num, title=title, content=content))

    if not chapters:
        return [Chapter(chapter=1, title="Full Text", content=text.strip())]

    return chapters
