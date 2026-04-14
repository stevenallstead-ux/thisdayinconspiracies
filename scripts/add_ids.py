#!/usr/bin/env python3
"""
One-shot ID migration + top-level metadata for data/data.json.

For each entry:
  - If `id` is already present, leave it alone (idempotent).
  - Otherwise compute `id = f"{year}-{slugify(title)}"`.
  - On collision within the current corpus, suffix -2, -3, ... and log
    to id_collisions.log.

For the top-level object:
  - Add `last_ingest_at` (ISO 8601 UTC) if absent.
  - Reshape from `[...]` (bare array) or `{"events": [...]}` into the
    locked schema `{"last_ingest_at": "...", "events": [...]}`.

Usage:
    python scripts/add_ids.py [--dry-run]

This script is one-shot. Re-running it is safe (idempotent) but normal
operation is: run once, commit result, let generate_entry.py take over
for future entries (which writes id + updates last_ingest_at per append).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._slug import slugify  # noqa: E402

DATA_PATH = ROOT / "data" / "data.json"
COLLISION_LOG = ROOT / "id_collisions.log"


def load_data() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    # Normalize to {"events": [...]} shape if caller passed a bare list.
    if isinstance(raw, list):
        return {"events": raw}
    if "events" not in raw:
        raise ValueError(f"{DATA_PATH} missing 'events' key")
    return raw


def save_data(data: dict, dry_run: bool = False) -> None:
    if dry_run:
        print("[dry-run] would write to", DATA_PATH)
        return
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def derive_id(entry: dict, used_ids: set[str]) -> tuple[str, bool]:
    """
    Return (id, was_collision). Uses slugify(title) with year prefix,
    suffixes -2, -3, ... on collision within the corpus.
    """
    year = entry.get("year")
    title = entry.get("title", "")
    if not isinstance(year, int):
        raise ValueError(f"entry missing integer year: {entry}")
    base = f"{year}-{slugify(title, fallback_year=year)}"
    candidate = base
    collision = False
    n = 2
    while candidate in used_ids:
        candidate = f"{base}-{n}"
        n += 1
        collision = True
    return candidate, collision


def log_collision(original_entry: dict, assigned_id: str) -> None:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = (
        f"{ts}\tcollision\tyear={original_entry.get('year')}\t"
        f"title={original_entry.get('title')}\tassigned_id={assigned_id}\n"
    )
    with COLLISION_LOG.open("a", encoding="utf-8") as f:
        f.write(line)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = load_data()
    events = data["events"]

    # First pass: gather existing IDs so new assignments avoid collision.
    used_ids: set[str] = {e["id"] for e in events if "id" in e}

    added = 0
    collisions = 0

    for entry in events:
        if "id" in entry:
            continue
        assigned, was_collision = derive_id(entry, used_ids)
        entry["id"] = assigned
        used_ids.add(assigned)
        added += 1
        if was_collision:
            collisions += 1
            log_collision(entry, assigned)

    # Reorder each entry so `id` appears first for readability.
    for i, entry in enumerate(events):
        events[i] = {"id": entry["id"], **{k: v for k, v in entry.items() if k != "id"}}

    # Top-level metadata.
    if "last_ingest_at" not in data:
        data["last_ingest_at"] = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    # Reorder so last_ingest_at is first in the top-level object.
    data = {
        "last_ingest_at": data["last_ingest_at"],
        "events": events,
        **{k: v for k, v in data.items() if k not in ("last_ingest_at", "events")},
    }

    save_data(data, dry_run=args.dry_run)

    print(f"[+] entries: {len(events)}")
    print(f"[+] ids added: {added}")
    print(f"[+] collisions: {collisions}")
    if collisions:
        print(f"[!] see {COLLISION_LOG.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
