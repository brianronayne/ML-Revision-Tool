import argparse
import json
import random
import sys
from pathlib import Path

# Cards contain Unicode math symbols (θ, σ, ∇, …). On Windows, stdout defaults
# to cp1252 when redirected, which crashes on these. Force UTF-8 where possible.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Allow running from repo root or src/
sys.path.insert(0, str(Path(__file__).parent))

import display
import srs

CARDS_PATH = Path(__file__).parent.parent / "data" / "cards.json"


def load_cards() -> list[dict]:
    if not CARDS_PATH.exists():
        display.console.print("[red]No cards found at data/cards.json[/red]")
        sys.exit(1)
    return json.loads(CARDS_PATH.read_text(encoding="utf-8"))


def resolve_tag(cards: list[dict], tag: str | None) -> str | None:
    """Validate a requested tag; exit with a helpful message if unknown."""
    if tag is None:
        return None
    available = srs.all_tags(cards)
    if tag not in available:
        display.show_unknown_tag(tag, available)
        sys.exit(1)
    return tag


def run_review(args: argparse.Namespace) -> None:
    cards = load_cards()
    progress = srs.load_progress()
    tag = resolve_tag(cards, args.tag)

    due = srs.get_due_cards(cards, progress, tag=tag, new_limit=args.new_limit)
    if not due:
        display.show_no_cards()
        return

    random.shuffle(due)
    queue = list(due)
    again_queue: list[dict] = []

    seen = good = hard = again_count = 0

    scope = f" — [magenta]{tag}[/magenta]" if tag else ""
    display.console.rule(f"[bold cyan]Review Session — {len(due)} cards due{scope}[/bold cyan]")

    while queue or again_queue:
        if not queue:
            # second pass: cards marked Again
            queue = again_queue
            again_queue = []
            display.console.rule("[yellow]Re-reviewing 'Again' cards[/yellow]")

        card = queue.pop(0)
        seen += 1
        display.show_question(card, seen, len(due) + len(again_queue) + len(queue) + 1)
        display.prompt_reveal()
        display.show_answer(card)

        rating = display.prompt_rating()
        srs.update_progress(progress, card["id"], rating)

        if rating == 1:
            again_count += 1
            again_queue.append(card)
        elif rating == 2:
            hard += 1
        else:
            good += 1

    srs.save_progress(progress)
    display.show_session_stats(seen, again_count, hard, good)


def run_stats(args: argparse.Namespace) -> None:
    cards = load_cards()
    progress = srs.load_progress()
    tag = resolve_tag(cards, args.tag)
    stats = srs.get_stats(cards, progress, tag=tag)
    display.show_deck_stats(stats)


def run_tags(args: argparse.Namespace) -> None:
    cards = load_cards()
    display.show_tags(srs.all_tags(cards))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ml-revision", description="ML flashcard revision tool")
    sub = parser.add_subparsers(dest="command")

    p_review = sub.add_parser("review", help="review due cards")
    p_review.add_argument("--tag", help="only review cards with this tag")
    p_review.add_argument(
        "--new-limit",
        type=int,
        default=srs.NEW_CARDS_PER_DAY,
        help=f"max new cards to introduce today (default {srs.NEW_CARDS_PER_DAY})",
    )
    p_review.set_defaults(func=run_review)

    p_stats = sub.add_parser("stats", help="show deck statistics")
    p_stats.add_argument("--tag", help="only count cards with this tag")
    p_stats.set_defaults(func=run_stats)

    p_tags = sub.add_parser("tags", help="list all tags and card counts")
    p_tags.set_defaults(func=run_tags)

    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "command", None):
        # default to review with no tag filter
        args = parser.parse_args(["review"])
    args.func(args)
