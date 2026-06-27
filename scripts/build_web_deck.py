"""Bundle data/cards.json into web/cards.js as `window.CARDS`.

Run after changing the deck so the web app stays in sync:
    python scripts/build_web_deck.py
"""
import json
from pathlib import Path

root = Path(__file__).parent.parent
cards = json.loads((root / "data" / "cards.json").read_text(encoding="utf-8"))

out = root / "web" / "cards.js"
out.parent.mkdir(parents=True, exist_ok=True)
payload = json.dumps(cards, ensure_ascii=False, indent=2)
out.write_text(f"window.CARDS = {payload};\n", encoding="utf-8")

print(f"Wrote {len(cards)} cards to {out.relative_to(root)}")
