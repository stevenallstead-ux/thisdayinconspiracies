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
import re
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
ENTITIES_PATH = ROOT / "data" / "entities.json"
ID_COLLISION_LOG = ROOT / "id_collisions.log"
NEW_ENTITIES_LOG = ROOT / "new_entities.log"

# Make scripts/ importable for _slug.slugify
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


_INJECTION_PATTERNS = [
    re.compile(r"ignore previous", re.I),
    re.compile(r"system:", re.I),
    re.compile(r"assistant:", re.I),
    re.compile(r"</?instructions?>", re.I),
    re.compile(r"</?system>", re.I),
    re.compile(r"\[INST\]", re.I),
]


def sanitize_for_prompt(text: str, max_len: int = 500) -> str:
    """OV-2 defense: strip prompt-injection-friendly content from external
    text (Wikipedia extract) before it reaches the LLM. Removes:
      - unicode control chars
      - markdown links [label](url)
      - common injection phrase patterns
    Then collapses whitespace and clamps to max_len chars.
    """
    if not isinstance(text, str) or not text:
        return ""
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    text = re.sub(r"\[[^\]]*\]\([^)]*\)", "", text)
    for pat in _INJECTION_PATTERNS:
        text = pat.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


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
            "text": sanitize_for_prompt(text, max_len=300),
            "title": top.get("normalizedtitle") or top.get("title") or "",
            "extract": sanitize_for_prompt(top.get("extract", ""), max_len=500),
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


# ── OV-1: collision-safe ID assignment ────────────────────────────────────
def assign_id(entry: dict, existing_ids: set[str]) -> tuple[str, bool]:
    """Returns (id, was_collision). Suffixes -2, -3, ... on collision and
    logs to id_collisions.log. Same algorithm as scripts/add_ids.py."""
    from scripts._slug import slugify
    base = f"{entry['year']}-{slugify(entry['title'], fallback_year=entry['year'])}"
    candidate = base
    n = 2
    collision = False
    while candidate in existing_ids:
        candidate = f"{base}-{n}"
        n += 1
        collision = True
    if collision:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with ID_COLLISION_LOG.open("a", encoding="utf-8") as f:
            f.write(
                f"{ts}\tcollision\tyear={entry['year']}\t"
                f"title={entry['title']}\tassigned_id={candidate}\n"
            )
    return candidate, collision


def update_last_ingest(data: dict) -> None:
    """OV-5: honest liveness signal. Always reflects the moment of last
    successful append, regardless of CF Pages mtime fiddling."""
    data["last_ingest_at"] = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


# ── Stage 1 task 9 + OV-7: entity auto-tag with quarantine ────────────────
ENTITY_TAG_SYSTEM_PROMPT = """You are an entity tagger for a conspiracy archive.
Given one new event and the registry of known entities (id → display name),
return the entity IDs that this event references AND propose any new entities
worth adding.

Hard rules:
- Mention only entity IDs that exist in the registry below.
- Be conservative with new_entities — propose only when the event clearly
  references a person/org/place/program/topic that is not in the registry.
- Each new entity needs type ∈ {person, org, place, program, event, topic},
  a display name, and 0+ aliases.

Output strict JSON, nothing else:
{
  "mentions": ["entity_id_a", "entity_id_b"],
  "new_entities": [
    {"type": "person", "name": "Display Name", "aliases": ["alias1"]}
  ]
}
"""


def load_entities() -> list[dict]:
    if not ENTITIES_PATH.exists():
        return []
    with ENTITIES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_entities(entities: list[dict]) -> None:
    with ENTITIES_PATH.open("w", encoding="utf-8") as f:
        json.dump(entities, f, indent=2, ensure_ascii=False)
        f.write("\n")


def auto_tag_entities(entry: dict, entities: list[dict]) -> dict:
    """Return parsed LLM response: {mentions, new_entities}."""
    live_entities = [e for e in entities if not e.get("quarantined")]
    summary_lines = [f"  {e['id']}: {e['name']}" for e in live_entities]
    user = (
        f"NEW EVENT:\n"
        f"Title: {entry['title']}\n"
        f"Year: {entry['year']}\n"
        f"Category: {entry['category']}\n"
        f"Summary: {entry['summary']}\n\n"
        f"KNOWN ENTITY REGISTRY ({len(live_entities)} entries):\n"
        + "\n".join(summary_lines)
        + "\n\nReturn JSON with mentions (existing entity IDs) and new_entities."
    )
    return generate(ENTITY_TAG_SYSTEM_PROMPT, user)


def apply_entity_tags(
    entry: dict,
    entities: list[dict],
    llm_response: dict,
) -> tuple[list[str], list[str]]:
    """
    Apply LLM tagging response to entry + entities registry. Returns
    (added_mentions, new_entity_ids_added).

    OV-7: new entities land with quarantined=true. They become live only
    when ≥2 distinct events reference them (handled in derive_edges.py).
    """
    from scripts._slug import slugify

    existing_ids = {e["id"] for e in entities}
    mentions = [m for m in (llm_response.get("mentions") or []) if m in existing_ids]
    entry["entities"] = list(mentions)  # don't alias — new entities append to entry only

    added_ids: list[str] = []
    for new_e in (llm_response.get("new_entities") or []):
        try:
            etype = new_e["type"]
            name = new_e["name"]
        except (KeyError, TypeError):
            continue
        if etype not in {"person", "org", "place", "program", "event", "topic"}:
            continue
        new_id = slugify(name)
        if not new_id:
            continue
        # Avoid clobbering existing entity ids
        original = new_id
        n = 2
        while new_id in existing_ids:
            new_id = f"{original}-{n}"
            n += 1
        entities.append({
            "id": new_id,
            "type": etype,
            "name": name,
            "aliases": list(new_e.get("aliases") or []),
            "quarantined": True,
        })
        existing_ids.add(new_id)
        added_ids.append(new_id)
        if new_id not in entry["entities"]:
            entry["entities"].append(new_id)

    if added_ids:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with NEW_ENTITIES_LOG.open("a", encoding="utf-8") as f:
            for nid in added_ids:
                f.write(f"{ts}\tnew_entity_quarantined\tid={nid}\tfrom_event={entry['id']}\n")

    return mentions, added_ids


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

    # OV-1: assign a stable, collision-safe ID before append.
    existing_ids = {e["id"] for e in data["events"] if "id" in e}
    entry_id, was_collision = assign_id(entry, existing_ids)
    entry["id"] = entry_id
    if was_collision:
        print(f"[!] ID collision: assigned {entry_id} (logged to {ID_COLLISION_LOG.name})")

    # Reorder so id is first in the entry dict (matches add_ids.py output).
    entry = {"id": entry_id, **{k: v for k, v in entry.items() if k != "id"}}

    print("[+] Generated entry:")
    print(json.dumps(entry, indent=2, ensure_ascii=False))

    # Stage 1 task 9 + OV-7: entity auto-tag with quarantine.
    entities = load_entities()
    if entities:
        try:
            tag_response = auto_tag_entities(entry, entities)
            mentions, new_ids = apply_entity_tags(entry, entities, tag_response)
            print(f"[+] Auto-tagged: {len(mentions)} mentions, "
                  f"{len(new_ids)} new entities (quarantined)")
        except Exception as exc:
            print(f"[!] Entity auto-tag failed: {exc}", file=sys.stderr)
            entry["entities"] = []
    else:
        print("[!] entities.json not found — skipping auto-tag.")
        entry["entities"] = []

    if args.dry_run:
        print("[*] Dry run — not writing.")
        return 0

    data["events"].append(entry)
    update_last_ingest(data)  # OV-5
    save_data(data)
    if entities:
        save_entities(entities)
    print(f"[+] Appended to data.json. Total entries: {len(data['events'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
