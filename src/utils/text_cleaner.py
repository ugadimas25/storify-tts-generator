import re


def clean_text(text: str) -> str:
    """Remove excessive whitespace and normalize line breaks."""
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_headers_footers(text: str) -> str:
    """Remove common header/footer patterns like page numbers."""
    text = re.sub(r"(?m)^\s*\d+\s*$", "", text)
    text = re.sub(r"(?m)^.*halaman\s+\d+.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?m)^.*page\s+\d+.*$", "", text, flags=re.IGNORECASE)
    return text
