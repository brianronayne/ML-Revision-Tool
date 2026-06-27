"""Replace book titles in the `source` field with opaque codes.

Published files (data/cards.json, web/cards.js) keep only codes like "REF-A3F9".
The decipher key is written to source_map.private.json, which is gitignored and
never published. Re-running is safe (idempotent): existing codes are preserved.

    python scripts/mask_sources.py
"""
import json
import secrets
from pathlib import Path

ROOT = Path(__file__).parent.parent
CARDS = ROOT / "data" / "cards.json"
MAP_FILE = ROOT / "source_map.private.json"  # code -> real title (gitignored)


def load_map() -> dict[str, str]:
    if MAP_FILE.exists():
        return json.loads(MAP_FILE.read_text(encoding="utf-8"))
    return {}


def new_code(existing: set[str]) -> str:
    while True:
        code = "REF-" + secrets.token_hex(2).upper()  # e.g. REF-A3F9
        if code not in existing:
            return code


def main() -> None:
    cards = json.loads(CARDS.read_text(encoding="utf-8"))

    code_to_title = load_map()                       # decipher key
    title_to_code = {v: k for k, v in code_to_title.items()}
    codes = set(code_to_title)

    masked = 0
    for card in cards:
        src = card["source"]
        if src in code_to_title:
            continue  # already a code — leave as-is
        if src not in title_to_code:
            code = new_code(codes)
            codes.add(code)
            code_to_title[code] = src
            title_to_code[src] = code
        card["source"] = title_to_code[src]
        masked += 1

    CARDS.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    MAP_FILE.write_text(json.dumps(code_to_title, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Masked {masked} card source fields.")
    print(f"Decipher key written to {MAP_FILE.name} (gitignored):")
    for code, title in code_to_title.items():
        print(f"  {code}  ->  {title}")


if __name__ == "__main__":
    main()
