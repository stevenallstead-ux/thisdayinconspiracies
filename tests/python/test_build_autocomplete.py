"""Tests for scripts/build_autocomplete.py — withheld decoy merge.

The build script reads three sources (data.json, entities.json,
withheld_entities.json) and produces dist/autocomplete.json. Withheld
items must appear with kind="withheld" and tag="WITHHELD" so connect.js
can short-circuit chain rendering when one is selected.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DIST = ROOT / "dist" / "autocomplete.json"
WITHHELD_SRC = ROOT / "data" / "withheld_entities.json"


def test_dist_autocomplete_exists():
    assert DIST.exists(), "Run `python scripts/build_autocomplete.py` first"


def test_withheld_items_present_with_correct_shape():
    items = json.loads(DIST.read_text(encoding="utf-8"))
    withheld = [i for i in items if i.get("kind") == "withheld"]
    assert len(withheld) >= 10, f"Expected >=10 withheld items, got {len(withheld)}"
    for w in withheld:
        assert w["tag"] == "WITHHELD", f"Item {w['id']} has wrong tag: {w.get('tag')}"
        assert w["kind"] == "withheld"
        assert isinstance(w.get("label"), str) and w["label"]
        assert isinstance(w.get("aliases", []), list)


def test_every_withheld_source_id_appears_in_autocomplete():
    src = json.loads(WITHHELD_SRC.read_text(encoding="utf-8"))
    items = json.loads(DIST.read_text(encoding="utf-8"))
    by_id = {i["id"]: i for i in items if i.get("kind") == "withheld"}
    for w in src:
        assert w["id"] in by_id, f"Source decoy {w['id']} missing from autocomplete"


def test_withheld_ids_dont_collide_with_entity_or_event_ids():
    """Decoy ids must be unique across the autocomplete set so URL
    namespace parsing in connect.js can route correctly."""
    items = json.loads(DIST.read_text(encoding="utf-8"))
    by_kind = {"event": set(), "entity": set(), "withheld": set()}
    for i in items:
        kind = i.get("kind")
        if kind in by_kind:
            by_kind[kind].add(i["id"])
    overlap_event = by_kind["withheld"] & by_kind["event"]
    overlap_entity = by_kind["withheld"] & by_kind["entity"]
    assert not overlap_event, f"withheld ids collide with event ids: {overlap_event}"
    assert not overlap_entity, f"withheld ids collide with entity ids: {overlap_entity}"
