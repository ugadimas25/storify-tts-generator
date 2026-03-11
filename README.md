# AI Audiobook Agent

Pipeline otomatis untuk mengubah **buku PDF** menjadi **audiobook** berbasis ringkasan tiap bab.

## Pipeline

```
PDF → Text Extraction → Chapter Splitting → LLM Summary → Google TTS → Audio (MP3)
```

## Tech Stack

- **Python 3.10+**
- **pdfminer.six** — PDF text extraction
- **Anthropic Claude** — LLM summarization
- **Google Cloud Text-to-Speech** — audio generation
- **Pydantic** — data models

## Setup

1. Clone dan masuk ke direktori project:

```bash
cd ai-audiobook-agent
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Buat file `.env` dari template:

```bash
cp .env.example .env
```

4. Isi environment variables di `.env`:

```
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_APPLICATION_CREDENTIALS=path_to_service_account.json
```

## Usage

Letakkan file PDF di folder `data/input_pdf/`, lalu jalankan:

```bash
python -m src.pipeline.audiobook_pipeline --input data/input_pdf/book.pdf
```

## Output

```
data/
├── chapters/
│   ├── chapter_1.txt
│   └── chapter_2.txt
├── summaries/
│   ├── chapter_1.json
│   └── chapter_2.json
└── audio/
    ├── chapter_1.mp3
    └── chapter_2.mp3
```

## Project Structure

```
ai-audiobook-agent/
├── src/
│   ├── extractor/
│   │   └── pdf_to_text.py       # PDF text extraction
│   ├── parser/
│   │   └── chapter_splitter.py   # Split text into chapters
│   ├── summarizer/
│   │   └── chapter_summary.py    # LLM summarization (Claude)
│   ├── tts/
│   │   └── google_tts.py         # Google Cloud TTS
│   ├── pipeline/
│   │   └── audiobook_pipeline.py # Main pipeline orchestrator
│   ├── models/
│   │   └── chapter.py            # Pydantic data models
│   └── utils/
│       └── text_cleaner.py       # Text cleaning utilities
├── data/
│   ├── input_pdf/
│   ├── chapters/
│   ├── summaries/
│   └── audio/
├── requirements.txt
├── .env.example
└── README.md
```
