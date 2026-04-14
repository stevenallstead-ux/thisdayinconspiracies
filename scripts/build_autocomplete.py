#!/usr/bin/env python3
"""
Build dist/autocomplete.json + dist/autocomplete-index.json from
data/data.json + data/entities.json.

Output schema:
  autocomplete.json       — flat array of {id, label, kind, tag}
      kind: "event" | "entity"
      tag:  display label shown on the right side of the dropdown row
            (FILE for events, ENTITY for entity types)
  autocomplete-index.json — {fuse_version, index}
      fuse_version — exact fuse.js version string read from
                     node_modules/fuse.js/package.json at build time;
                     runtime asserts a match (OV-3).
      index        — Fuse.createIndex().toJSON() dump.

Quarantined entities are excluded from both outputs — they should not
appear in autocomplete until promoted.

Run: python scripts/build_autocomplete.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_PATH = ROOT / "data" / "data.json"
ENTITIES_PATH = ROOT / "data" / "entities.json"
WITHHELD_PATH = ROOT / "data" / "withheld_entities.json"
DIST_DIR = ROOT / "dist"
AUTOCOMPLETE_PATH = DIST_DIR / "autocomplete.json"
INDEX_PATH = DIST_DIR / "autocomplete-index.json"
FUSE_INDEX_BUILDER = HERE / "_build_fuse_index.mjs"


def load_json(p: Path) -> object:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    data = load_json(DATA_PATH)
    entities = load_json(ENTITIES_PATH)

    items: list[dict] = []

    for ev in data["events"]:  # type: ignore[index]
        items.append({
            "id": ev["id"],
            "label": ev["title"],
            "kind": "event",
            "year": ev["year"],
            "category": ev["category"],
            "tag": "FILE",
        })

    type_tag = {
        "person": "PERSON",
        "org": "ORG",
        "place": "PLACE",
        "program": "PROGRAM",
        "event": "EVENT",
        "topic": "TOPIC",
    }
    for e in entities:  # type: ignore[union-attr]
        if e.get("quarantined"):
            continue
        items.append({
            "id": e["id"],
            "label": e["name"],
            "kind": "entity",
            "aliases": e.get("aliases", []),
            "tag": type_tag.get(e["type"], "ENTITY"),
        })

    # WITHHELD decoys: surface in autocomplete with a distinct tag, but
    # never enter data/entities.json or dist/edges.json. Picking one
    # triggers the FOIA Easter egg in connect.js.
    if WITHHELD_PATH.exists():
        withheld = load_json(WITHHELD_PATH)
        for w in withheld:  # type: ignore[union-attr]
            items.append({
                "id": w["id"],
                "label": w["name"],
                "kind": "withheld",
                "aliases": w.get("aliases", []),
                "category": w.get("category", "Unexplained"),
                "tag": "WITHHELD",
            })

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    with AUTOCOMPLETE_PATH.open("w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"[+] {len(items)} autocomplete items ({sum(1 for i in items if i['kind']=='event')} events, "
          f"{sum(1 for i in items if i['kind']=='entity')} entities, "
          f"{sum(1 for i in items if i['kind']=='withheld')} withheld) -> {AUTOCOMPLETE_PATH}")

    # Build Fuse index via node. Shell out so we share the exact fuse
    # version that will be loaded at runtime from js/vendor/fuse.min.mjs.
    if not FUSE_INDEX_BUILDER.exists():
        print(f"[!] {FUSE_INDEX_BUILDER} not found; skipping Fuse index build.",
              file=sys.stderr)
        return 1

    try:
        result = subprocess.run(
            ["node", str(FUSE_INDEX_BUILDER)],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        print(result.stdout.strip())
    except FileNotFoundError:
        print("[!] `node` not on PATH. Install Node 20+ and re-run.",
              file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as e:
        print(f"[!] fuse index build failed: {e.stderr}", file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
