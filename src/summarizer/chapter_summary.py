import os
import time

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

from src.models.chapter import Chapter, ChapterSummary

load_dotenv()

# ~20,000 chars ≈ ~5,000 tokens — safe for 30k TPM limit
CHUNK_SIZE = 20_000

SYSTEM_PROMPT = """You are an expert book summarizer.

Rules:
- Max 1500 characters
- Keep the key ideas
- Maintain narrative style
- Indonesian language"""

CHUNK_PROMPT_TEMPLATE = """Summarize the following text excerpt from a book:

{chunk_text}"""

MERGE_PROMPT_TEMPLATE = """You are an expert book summarizer.
Below are partial summaries of different sections of the same chapter.
Merge them into one cohesive final summary.

Rules:
- Max 1500 characters
- Keep the key ideas
- Maintain narrative style
- Indonesian language

Partial summaries:
{partial_summaries}"""


def _call_openai(client: OpenAI, prompt: str, max_retries: int = 6) -> str:
    """Call OpenAI API with automatic retry on rate limit errors."""
    delay = 10  # initial backoff in seconds
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content
        except RateLimitError as e:
            if attempt == max_retries:
                raise
            # Try to extract wait time from error message
            import re as _re
            m = _re.search(r'try again in (\d+\.?\d*)s', str(e))
            wait = float(m.group(1)) + 2 if m else delay
            print(f"       [rate limit] waiting {wait:.1f}s before retry {attempt}/{max_retries} ...")
            time.sleep(wait)
            delay = min(delay * 2, 120)  # exponential backoff, max 2 min


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """Split text into chunks of at most chunk_size characters, splitting at word boundaries."""
    chunks = []
    while len(text) > chunk_size:
        split_at = text.rfind(" ", 0, chunk_size)
        if split_at == -1:
            split_at = chunk_size
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    if text:
        chunks.append(text)
    return chunks


def summarize_chapter(chapter: Chapter) -> ChapterSummary:
    """Summarize a single chapter using OpenAI GPT, chunking if too long."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    chunks = _chunk_text(chapter.content)

    if len(chunks) == 1:
        summary_text = _call_openai(
            client, CHUNK_PROMPT_TEMPLATE.format(chunk_text=chunks[0])
        )
    else:
        partial_summaries = []
        for i, chunk in enumerate(chunks, 1):
            partial = _call_openai(
                client, CHUNK_PROMPT_TEMPLATE.format(chunk_text=chunk)
            )
            partial_summaries.append(f"[Part {i}]\n{partial}")

        summary_text = _call_openai(
            client,
            MERGE_PROMPT_TEMPLATE.format(
                partial_summaries="\n\n".join(partial_summaries)
            ),
        )

    return ChapterSummary(
        chapter=chapter.chapter,
        title=chapter.title,
        summary=summary_text,
    )


def summarize_chapters(chapters: list[Chapter]) -> list[ChapterSummary]:
    """Summarize all chapters sequentially."""
    from tqdm import tqdm

    summaries: list[ChapterSummary] = []
    for chapter in tqdm(chapters, desc="Summarizing chapters"):
        summary = summarize_chapter(chapter)
        summaries.append(summary)
    return summaries
