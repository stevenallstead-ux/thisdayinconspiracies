"""
generate_entry.py — add one new conspiracy/unexplained event to data.json.

Flow:
  1. Pull Wikipedia's "On this day" feed for today (or a date you pass in).
  2. Drop candidates already in data.json.
  3. Ask the LLM to pick the single candidate with the strongest
     conspiracy / unexplained / paranormal / political-coverup angle
     and produce one entry in our schema.
  4. Append the entry to data.json.

Usage:
    python generate_entry.py                    # today
    python generate_entry.py --date 07-04       # specific MM-DD
    python generate_entry.py --dry-run          # print only, don't write

Env vars (via .env or shell):
    OPENAI_API_KEY       — required if provider=openai (default)
    ANTHROPIC_API_KEY    — required if provider=anthropic
    LLM_PROVIDER         — openai | anthropic        (default: openai)
    LLM_MODEL            — e.g. gpt-4o-mini          (default per provider)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
    # Also load ObscuraCast's .env so the same key works in both projects.
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "data.json"

WIKI_ENDPOINT = "https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{mm}/{dd}"
USER_AGENT = "ThisDayInConspiracies/0.1 (https://github.com/yourname/thisday)"

ALLOWED_CATEGORIES = [
    "UFO", "Government", "Political", "Cryptid",
    "Unexplained", "Space", "Celebrity",
]

SYSTEM_PROMPT = """You are a research editor for an archive site called "This Day in Conspiracies."
You select real historical events with genuine, documented conspiracy, coverup, unexplained-phenomena, UFO, cryptid, paranormal, or unsolved-mystery angles.

Hard rules:
- Only use events from the candidate list the user provides. Do not invent events or dates.
- Pick ONE candidate. It must have a real, well-documented alternative narrative or unresolved mystery — not just an ordinary tragedy.
- If NO candidate qualifies, respond with exactly: {"skip": true, "reason": "..."}
- Theories listed must be real circulating theories (mainstream-reported or widely-discussed fringe), not fabrications. Describe them as theories, not facts.
- Write in a measured, archival tone. No hype, no emoji, no editorial flourish.
- Category must be exactly one of: UFO, Government, Political, Cryptid, Unexplained, Space, Celebrity.

Output: strict JSON matching this shape, and nothing else:
{
  "date": "MM-DD",
  "year": 1969,
  "title": "Short headline (≤70 chars)",
  "category": "UFO",
  "summary": "2-4 sentence neutral description of the event.",
  "theories": ["Theory one.", "Theory two.", "Theory three."]
}"""


def load_data() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict) -> None:
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def parse_target_date(arg: str | None) -> tuple[int, int]:
    if arg:
        mm, dd = arg.split("-")
        return int(mm), int(dd)
    now = datetime.now(timezone.utc)
    return now.month, now.day


def fetch_wikipedia_events(month: int, day: int) -> list[dict]:
    url = WIKI_ENDPOINT.format(mm=f"{month:02d}", dd=f"{day:02d}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read())
    raw = payload.get("events", [])
    events = []
    for e in raw:
        year = e.get("year")
        text = e.get("text", "")
        pages = e.get("pages", [])
        top = pages[0] if pages else {}
        events.append({
            "year": year,
            "text": text,
            "title": top.get("normalizedtitle") or top.get("title") or "",
            "extract": top.get("extract", ""),
            "url": (top.get("content_urls", {}).get("desktop") or {}).get("page", ""),
        })
    return events


def filter_new(events: list[dict], data: dict, month: int, day: int) -> list[dict]:
    date_key = f"{month:02d}-{day:02d}"
    existing = {
        (e["date"], e["year"], e["title"].lower())
        for e in data.get("events", [])
    }
    existing_titles = {e["title"].lower() for e in data.get("events", []) if e["date"] == date_key}

    fresh = []
    for e in events:
        if not e["year"] or not e["title"]:
            continue
        key = (date_key, e["year"], e["title"].lower())
        if key in existing:
            continue
        if e["title"].lower() in existing_titles:
            continue
        fresh.append(e)
    return fresh


def build_user_prompt(month: int, day: int, candidates: list[dict]) -> str:
    date_key = f"{month:02d}-{day:02d}"
    lines = [
        f"Target date: {date_key}",
        f"Candidate count: {len(candidates)}",
        "",
        "Candidates (pick one that has a real conspiracy/unexplained/paranormal/coverup angle — or skip):",
        "",
    ]
    for i, c in enumerate(candidates[:25], 1):
        lines.append(f"{i}. [{c['year']}] {c['title']}")
        if c["text"]:
            lines.append(f"   Summary: {c['text']}")
        if c["extract"]:
            excerpt = c["extract"][:500].replace("\n", " ")
            lines.append(f"   Extract: {excerpt}")
        lines.append("")
    return "\n".join(lines)


def call_openai(system: str, user: str, model: str) -> str:
    from openai import OpenAI
    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        temperature=0.4,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content or ""


def call_anthropic(system: str, user: str, model: str) -> str:
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=1500,
        temperature=0.4,
        system=system,
        messages=[{"role": "user", "content": user + "\n\nReturn only strict JSON."}],
    )
    return resp.content[0].text


def generate(system: str, user: str) -> dict:
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    if provider == "anthropic":
        model = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")
        text = call_anthropic(system, user, model)
    else:
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        text = call_openai(system, user, model)

    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def validate_entry(entry: dict, month: int, day: int) -> tuple[bool, str]:
    if entry.get("skip"):
        return False, f"LLM skipped: {entry.get('reason', 'no reason given')}"
    required = {"date", "year", "title", "category", "summary", "theories"}
    missing = required - set(entry.keys())
    if missing:
        return False, f"missing fields: {missing}"
    if entry["date"] != f"{month:02d}-{day:02d}":
        return False, f"wrong date: {entry['date']} != {month:02d}-{day:02d}"
    if entry["category"] not in ALLOWED_CATEGORIES:
        return False, f"bad category: {entry['category']}"
    if not isinstance(entry["theories"], list) or not entry["theories"]:
        return False, "theories must be a non-empty list"
    if not isinstance(entry["year"], int):
        return False, f"year must be an integer, got {type(entry['year']).__name__}"
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="Target date MM-DD. Defaults to today (UTC).")
    ap.add_argument("--dry-run", action="store_true", help="Print entry, do not write.")
    args = ap.parse_args()

    month, day = parse_target_date(args.date)
    date_key = f"{month:02d}-{day:02d}"
    print(f"[*] Target: {date_key}")

    data = load_data()
    events = fetch_wikipedia_events(month, day)
    print(f"[*] Wikipedia returned {len(events)} events.")

    candidates = filter_new(events, data, month, day)
    print(f"[*] {len(candidates)} candidates remain after dedup.")
    if not candidates:
        print("[!] No new candidates. Nothing to do.")
        return 0

    system = SYSTEM_PROMPT
    user = build_user_prompt(month, day, candidates)

    try:
        entry = generate(system, user)
    except Exception as e:
        print(f"[!] LLM error: {e}", file=sys.stderr)
        return 1

    ok, err = validate_entry(entry, month, day)
    if not ok:
        print(f"[!] Rejected: {err}")
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return 2

    print("[+] Generated entry:")
    print(json.dumps(entry, indent=2, ensure_ascii=False))

    if args.dry_run:
        print("[*] Dry run — not writing.")
        return 0

    data["events"].append(entry)
    save_data(data)
    print(f"[+] Appended to data.json. Total entries: {len(data['events'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
