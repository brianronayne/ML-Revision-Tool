import json
from datetime import datetime, timedelta
from pathlib import Path

PROGRESS_PATH = Path(__file__).parent.parent / "data" / "progress.json"

BUCKET_INTERVALS = {0: 0, 1: 1.0, 2: 4.0}  # days; 0 = same session
NEW_CARDS_PER_DAY = 20  # max brand-new cards introduced per calendar day


def load_progress() -> dict:
    if PROGRESS_PATH.exists():
        return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    return {}


def save_progress(progress: dict) -> None:
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_PATH.write_text(json.dumps(progress, indent=2), encoding="utf-8")


def filter_by_tag(cards: list[dict], tag: str | None) -> list[dict]:
    if not tag:
        return cards
    return [c for c in cards if tag in c.get("tags", [])]


def new_cards_seen_today(progress: dict, now: datetime | None = None) -> int:
    """Count cards whose first review happened on today's calendar date.

    Counted across the whole deck (not tag-filtered) so the daily new-card
    budget is shared, matching Anki's behaviour.
    """
    today = (now or datetime.now()).date()
    count = 0
    for state in progress.values():
        first_seen = state.get("first_seen")
        if first_seen and datetime.fromisoformat(first_seen).date() == today:
            count += 1
    return count


def get_due_cards(
    cards: list[dict],
    progress: dict,
    tag: str | None = None,
    new_limit: int = NEW_CARDS_PER_DAY,
) -> list[dict]:
    """Return scheduled reviews that are due, plus up to `new_limit` unseen
    cards (minus any new cards already introduced today)."""
    now = datetime.now()
    remaining_new = max(0, new_limit - new_cards_seen_today(progress, now))

    cards = filter_by_tag(cards, tag)
    scheduled = []
    new_cards = []
    for card in cards:
        state = progress.get(card["id"])
        if state is None:
            new_cards.append(card)
        elif datetime.fromisoformat(state["next_due"]) <= now:
            scheduled.append(card)

    return scheduled + new_cards[:remaining_new]


def update_progress(progress: dict, card_id: str, rating: int) -> None:
    """rating: 1=Again, 2=Hard, 3=Good"""
    now = datetime.now()
    state = progress.get(card_id, {"bucket": 0, "interval_days": 0.0, "total_reviews": 0})

    # Record the first time this card is ever reviewed (drives the daily limit).
    if "first_seen" not in state:
        state["first_seen"] = now.isoformat()

    if rating == 1:  # Again
        state["bucket"] = 0
        state["interval_days"] = 0.0
        # next_due set to far past so caller can re-queue within session
        state["next_due"] = (now - timedelta(seconds=1)).isoformat()
    elif rating == 2:  # Hard
        state["bucket"] = 1
        state["interval_days"] = BUCKET_INTERVALS[1]
        state["next_due"] = (now + timedelta(days=BUCKET_INTERVALS[1])).isoformat()
    else:  # Good
        prev_bucket = state.get("bucket", 0)
        new_bucket = min(prev_bucket + 1, 2)
        prev_interval = state.get("interval_days", 0.0)
        if new_bucket == 2:
            new_interval = max(prev_interval * 2.0, BUCKET_INTERVALS[2])
        else:
            new_interval = BUCKET_INTERVALS[new_bucket]
        state["bucket"] = new_bucket
        state["interval_days"] = new_interval
        state["next_due"] = (now + timedelta(days=new_interval)).isoformat()

    state["total_reviews"] = state.get("total_reviews", 0) + 1
    progress[card_id] = state


def all_tags(cards: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for card in cards:
        for tag in card.get("tags", []):
            counts[tag] = counts.get(tag, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def get_stats(cards: list[dict], progress: dict, tag: str | None = None) -> dict:
    counts = {"new": 0, "due": 0, "bucket_0": 0, "bucket_1": 0, "bucket_2": 0}
    now = datetime.now()
    cards = filter_by_tag(cards, tag)
    for card in cards:
        state = progress.get(card["id"])
        if state is None:
            counts["new"] += 1
        else:
            bucket = state["bucket"]
            counts[f"bucket_{bucket}"] += 1
            if datetime.fromisoformat(state["next_due"]) <= now:
                counts["due"] += 1
    return counts
