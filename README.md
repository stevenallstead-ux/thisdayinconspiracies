# This Day in Conspiracies

A static, zero-backend daily archive of unexplained events, UFO sightings, political cover-ups, and cryptid encounters — rotated by calendar date.

## Stack

- Plain HTML / CSS / vanilla JS (no build step, no framework)
- Single `data.json` corpus keyed by `MM-DD`
- Hostable on Cloudflare Pages, Netlify, Vercel, or GitHub Pages (pure static)

## Run locally

The site uses `fetch('data.json')`, which requires serving over HTTP (not `file://`). From this directory:

```bash
python -m http.server 8000
# then open http://localhost:8000
```

Or any equivalent static server.

## Adding new entries

Append to `data.json` &rarr; `events` array. Every entry needs:

```json
{
  "date": "MM-DD",
  "year": 1969,
  "title": "Short headline",
  "category": "UFO | Government | Political | Cryptid | Unexplained | Space | Celebrity",
  "summary": "2–4 sentence description.",
  "theories": ["Theory 1", "Theory 2"]
}
```

- `date` is month-day only (year-agnostic rotation)
- Multiple events can share a date — they will all render as cards
- `category` drives the colored label; keep to the set above for consistent styling

## Daily auto-generation

`generate_entry.py` pulls Wikipedia's "On this day" feed, filters out events already in `data.json`, and asks an LLM to pick the one candidate with the strongest conspiracy/unexplained/paranormal angle and write it up in the site's schema.

### One-time setup

```bash
cd thisdayinconspiracies
pip install -r requirements.txt
cp .env.example .env
# edit .env: add OPENAI_API_KEY=sk-...
```

### Usage

```bash
python generate_entry.py                    # add one entry for today
python generate_entry.py --date 07-04       # backfill a specific MM-DD
python generate_entry.py --dry-run          # preview without writing
```

If no candidate has a genuine conspiracy angle, the script will print a skip reason and exit without writing — safer than forcing a weak entry.

### Cron it

**Linux/macOS:**
```cron
0 6 * * * cd /path/to/thisdayinconspiracies && /usr/bin/python generate_entry.py >> generate.log 2>&1
```

**Windows Task Scheduler** — model on `scripts/register_tasks.ps1` from the ObscuraCast pipeline in the parent directory.

**GitHub Actions (recommended for static deploy):** commit `data.json` back to the repo on schedule, so Cloudflare Pages auto-redeploys.

## Next steps (post-MVP)

1. **Expand the corpus further**: the 103 seeded entries are a floor; `generate_entry.py` will backfill gaps over time
2. **Per-event pages**: generate `/event/{slug}.html` at build time for SEO and shareable URLs
3. **Archive browser**: calendar grid view linking to any date
4. **Comments**: Disqus or utterances (GitHub Issues) for discussion
5. **Ads**: Ezoic / Mediavine once traffic supports it; AdSense interim (see placeholders in `index.html`)
6. **Cross-link to ObscuraCast**: add "Watch the episode" CTA on events with matching video content
