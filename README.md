# ML Revision Tool

A flashcard app for revising technical concepts, with a built-in
spaced-repetition scheduler. The deck of **234 cards** spans five subjects —
Machine Learning, Data Science, Programming, SQL & Databases, and MLOps &
Systems (see [Source material](#source-material)). It runs two ways:

- **Web app** — a dark, modern single-page UI you can deploy anywhere (see [Web app](#web-app)).
- **Terminal CLI** — a Rich-powered command-line reviewer (see [Usage](#usage)).

Both share the same deck and the same 3-bucket spaced-repetition rules. Filter by
subject and topic. No account needed (optional cloud login for cross-device sync).

## Setup

Requires Python 3.10+.

```bash
pip install -r requirements.txt
```

The only runtime dependency is [`rich`](https://github.com/Textualize/rich)
(for the coloured terminal UI). `PyMuPDF` is listed for the optional
card-generation script and isn't needed for day-to-day review.

## Web app

A self-contained single-page app lives in [`web/`](web/). It's pure
HTML/CSS/JS — no build step, no backend. The deck is bundled as `web/cards.js`
and your progress is saved in the browser's `localStorage`, so it works offline
and on any static host.

### Run it locally

Just open `web/index.html` in a browser (double-click works — there's no
`fetch`, so `file://` is fine). Optionally serve it:

```bash
python -m http.server -d web 8000   # then visit http://localhost:8000
```

### Features

- Dark, modern UI with a 3-D card-flip reveal and animated progress bar.
- Topic filter and a configurable daily new-card limit (mirrors the CLI).
- Keyboard shortcuts: `Space` / `Enter` to reveal, `1` / `2` / `3` to rate, `Esc` to exit.
- Dashboard showing new / due / learning / known counts.

### Deploy

The `web/` folder is the entire site. Any static host works:

- **Netlify / Vercel** — drag-and-drop the `web/` folder, or point the project at
  this repo with `web` as the publish directory.
- **GitHub Pages** — push the repo and set Pages to serve the `web/` folder
  (e.g. via the *Deploy from a branch* option, or copy `web/`'s contents to `/docs`).

### Keeping the deck in sync

`web/cards.js` is generated from `data/cards.json`. After editing the deck, regenerate it:

```bash
python scripts/build_web_deck.py
```

## Login & cloud sync (optional)

By default, progress is saved per-browser in `localStorage` — no account needed.
You can optionally enable **accounts + cross-device sync** with a free
[Supabase](https://supabase.com) project. The app stays a static site; Supabase
provides auth and storage, so there's still no server to run.

The app degrades gracefully: with no Supabase config it runs exactly as before
(local-only), and the sign-in button stays hidden.

### Setup

1. Create a free project at [supabase.com](https://supabase.com).
2. In the project's **SQL Editor**, run [`supabase/schema.sql`](supabase/schema.sql)
   (creates a `user_progress` table with row-level security).
3. In **Project Settings → API**, copy the **Project URL** and the **anon public** key.
4. Paste them into [`web/config.js`](web/config.js), then commit and redeploy.
5. In **Authentication → URL Configuration**, add your deployed site URL (and
   `http://localhost:8000` for local dev) to the allowed redirect URLs.
6. *(Optional)* enable the **Google** provider under **Authentication → Providers**
   to light up the "Continue with Google" button.

The `anon` key is meant to be public — row-level security ensures each user can
only read and write their own progress row.

### How sync works

- Sign in with a magic link (passwordless email) or Google.
- On sign-in, your local progress is **merged** with the cloud copy (per card, the
  more-advanced review wins; earliest `first_seen` is preserved) — so nothing you
  studied while logged out is lost.
- Subsequent reviews are pushed to the cloud automatically (debounced).

## Usage

Run from the project root:

```bash
python src/main.py review        # review everything due (default command)
python src/main.py stats         # show deck progress
python src/main.py subjects      # list subjects and card counts
python src/main.py tags          # list topics and card counts
```

### Reviewing

```bash
python src/main.py review
```

Each card shows the **question**, waits for you to press `Enter`, then reveals
the **answer**. Rate how well you knew it:

| Key | Rating | Effect |
|----|--------|--------|
| `1` | **Again** | Reset to learning; re-shown later in the same session |
| `2` | **Hard**  | Due again in 1 day |
| `3` | **Good**  | Promoted; interval grows (1 day → 4 days → doubling) |

### Focusing on a subject or topic

Filter any review or stats view by `--subject` and/or `--tag`:

```bash
python src/main.py review --subject "Data Science"
python src/main.py review --subject "SQL & Databases" --tag joins
python src/main.py stats  --subject Programming
python src/main.py tags   --subject "MLOps & Systems"   # topics within a subject
```

Subjects: `Machine Learning`, `Data Science`, `Programming`, `SQL & Databases`,
`MLOps & Systems`. Run `python src/main.py subjects` for counts, and
`python src/main.py tags --subject "<name>"` to see that subject's topics.

### Daily new-card limit

To avoid being buried on day one, at most **20 brand-new cards** are introduced
per calendar day (scheduled reviews are always shown in full). Adjust it:

```bash
python src/main.py review --new-limit 40   # bigger session today
python src/main.py review --new-limit 0    # reviews only, no new cards
```

The budget is shared across all topics for the day.

## How scheduling works

A simple 3-bucket spaced-repetition system:

| Bucket | Meaning | Interval until next review |
|--------|---------|----------------------------|
| 0 | Learning | Same session |
| 1 | Hard     | 1 day |
| 2 | Known    | 4 days, then doubles each `Good` (4 → 8 → 16 …) |

A card is **due** when its `next_due` timestamp has passed.

## Data model

```
data/cards.json      # the deck (committed)
data/progress.json   # your personal progress (gitignored)
```

**Card:**

```json
{
  "id": "uuid4",
  "subject": "Machine Learning",
  "source": "REF-8C1B",
  "question": "What is multi-head attention and why is it used?",
  "answer": "...",
  "tags": ["transformers", "llm"]
}
```

**Progress entry** (keyed by card `id`):

```json
{
  "bucket": 1,
  "interval_days": 1.0,
  "next_due": "2026-06-28T10:00:00",
  "total_reviews": 3,
  "first_seen": "2026-06-27T10:00:00"
}
```

## Project layout

```
src/
  main.py            # CLI entry point (review / stats / tags / subjects)
  srs.py             # scheduling: due cards, progress, stats, subjects, tags
  display.py         # Rich-based terminal rendering
web/
  index.html         # single-page web app
  styles.css         # dark, modern theme
  srs.js             # scheduler (port of src/srs.py) + progress merge
  app.js             # views, session loop, keyboard shortcuts
  cards.js           # deck bundle (generated from data/cards.json)
  config.js          # Supabase keys (empty = local-only mode)
  auth.js            # optional login & cloud sync
supabase/
  schema.sql         # user_progress table + row-level security
data/                # deck + progress
scripts/
  build_web_deck.py  # regenerate web/cards.js from data/cards.json
  mask_sources.py    # replace source titles with opaque codes
```

## Source material

Each card's `source` is an opaque code rather than a title, so the underlying
references aren't exposed publicly. There are two kinds:

- **`REF-…`** — the Machine Learning cards, drawn from three reference works
  (`REF-2BE2`, `REF-F9BD`, `REF-8C1B`). The code→title mapping is kept privately
  in `source_map.private.json` (gitignored), not part of this repository.
- **`GEN-…`** — the Data Science, Programming, SQL, and MLOps cards, authored
  from general domain knowledge of well-established fundamentals.
