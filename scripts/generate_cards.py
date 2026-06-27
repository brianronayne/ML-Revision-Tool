"""
Extract text from PDFs in resource/ and use Claude to generate Q&A flashcards.
Writes results to data/cards.json (appends, deduplicates by question text).

Usage:
    python scripts/generate_cards.py
    python scripts/generate_cards.py --model claude-haiku-4-5-20251001
    python scripts/generate_cards.py --pages-per-chunk 8 --cards-per-chunk 5
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF not installed. Run: pip install PyMuPDF")
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("anthropic not installed. Run: pip install anthropic")
    sys.exit(1)

REPO_ROOT = Path(__file__).parent.parent
RESOURCE_DIR = REPO_ROOT / "resource"
CARDS_PATH = REPO_ROOT / "data" / "cards.json"

GENERATION_PROMPT = """\
You are an expert ML tutor creating flashcards for a student revising machine learning.

From the textbook excerpt below, generate exactly {n} high-quality Q&A flashcard pairs.
Focus on conceptual understanding: definitions, intuitions, trade-offs, and key formulas.
Avoid trivially obvious questions.

Return ONLY a JSON array (no markdown fences) like:
[
  {{"question": "...", "answer": "..."}},
  ...
]

Textbook excerpt:
{text}
"""


def extract_page_texts(pdf_path: Path) -> list[str]:
    doc = fitz.open(str(pdf_path))
    return [page.get_text() for page in doc]


def chunk_pages(pages: list[str], pages_per_chunk: int) -> list[str]:
    chunks = []
    for i in range(0, len(pages), pages_per_chunk):
        chunk = "\n".join(pages[i : i + pages_per_chunk]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def generate_cards_for_chunk(
    client: anthropic.Anthropic,
    chunk: str,
    model: str,
    n: int,
) -> list[dict]:
    prompt = GENERATION_PROMPT.format(n=n, text=chunk[:6000])  # hard cap to stay in token budget
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        pairs = json.loads(raw)
        return [p for p in pairs if "question" in p and "answer" in p]
    except json.JSONDecodeError:
        print(f"  [warn] Could not parse JSON from model response. Skipping chunk.")
        return []


def load_existing_cards() -> list[dict]:
    if CARDS_PATH.exists():
        return json.loads(CARDS_PATH.read_text(encoding="utf-8"))
    return []


def deduplicate(existing: list[dict], new_cards: list[dict]) -> list[dict]:
    existing_questions = {c["question"].lower().strip() for c in existing}
    unique = []
    for card in new_cards:
        q = card["question"].lower().strip()
        if q not in existing_questions:
            existing_questions.add(q)
            unique.append(card)
    return unique


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    parser.add_argument("--pages-per-chunk", type=int, default=6)
    parser.add_argument("--cards-per-chunk", type=int, default=5)
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set. Add it to a .env file or export it.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    pdfs = sorted(RESOURCE_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {RESOURCE_DIR}")
        sys.exit(1)

    existing = load_existing_cards()
    all_new: list[dict] = []

    for pdf_path in pdfs:
        print(f"\nProcessing: {pdf_path.name}")
        pages = extract_page_texts(pdf_path)
        chunks = chunk_pages(pages, args.pages_per_chunk)
        print(f"  {len(pages)} pages → {len(chunks)} chunks")

        for i, chunk in enumerate(chunks, 1):
            print(f"  Chunk {i}/{len(chunks)}...", end=" ", flush=True)
            pairs = generate_cards_for_chunk(client, chunk, args.model, args.cards_per_chunk)
            cards = [
                {
                    "id": str(uuid.uuid4()),
                    "source": pdf_path.name,
                    "question": p["question"],
                    "answer": p["answer"],
                }
                for p in pairs
            ]
            unique = deduplicate(existing + all_new, cards)
            all_new.extend(unique)
            print(f"+{len(unique)} cards")

    if not all_new:
        print("\nNo new cards generated.")
        return

    combined = existing + all_new
    CARDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CARDS_PATH.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone. {len(all_new)} new cards added. Total: {len(combined)}.")


if __name__ == "__main__":
    main()
