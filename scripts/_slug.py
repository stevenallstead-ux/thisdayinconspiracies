"""
Hand-rolled slugify. ASCII-only, stable across Python versions, vendored
so ID generation never drifts with third-party library upgrades.

Used by:
- scripts/add_ids.py (one-shot ID migration for seeded entries)
- generate_entry.py (assigns ID to each new daily entry at ingest)

Golden tests live in tests/python/test_slugify.py. Re-running slugify on
any pinned golden MUST produce the same output. If a change here breaks
a golden test, either the golden is wrong or the ID scheme is about to
break every share URL — treat the test as a tripwire.
"""
from __future__ import annotations

import re
import unicodedata


def slugify(s: str, *, fallback_year: int | None = None) -> str:
    """
    ASCII-only slug derived from free text.

    Steps:
      1. NFKD-normalize (decomposes accented Latin into base + combining marks).
      2. Strip combining marks (removes the accents, keeps the base letters).
      3. Encode ASCII, dropping anything non-representable (CJK, RTL, emoji).
      4. Lowercase.
      5. Replace any run of non-[a-z0-9] with a single dash.
      6. Strip leading/trailing dashes.
      7. If empty (all-non-ASCII input), fall back to "untitled" or "untitled-{year}".

    Deterministic. Idempotent: slugify(slugify(x)) == slugify(x) for all inputs.
    """
    if not isinstance(s, str):
        raise TypeError(f"slugify expected str, got {type(s).__name__}")

    decomposed = unicodedata.normalize("NFKD", s)
    stripped_marks = "".join(
        ch for ch in decomposed if not unicodedata.combining(ch)
    )
    # Replace non-ASCII punctuation and symbols with space so em-dashes,
    # curly quotes, etc. act as word separators instead of silently
    # disappearing and collapsing adjacent words ("1947–1980" must not
    # become "19471980").
    bridged = "".join(
        " " if ord(ch) > 127 and unicodedata.category(ch)[0] in ("P", "S", "Z")
        else ch
        for ch in stripped_marks
    )
    ascii_only = bridged.encode("ascii", errors="ignore").decode("ascii")
    lowered = ascii_only.lower()
    dashed = re.sub(r"[^a-z0-9]+", "-", lowered)
    trimmed = dashed.strip("-")

    if trimmed:
        return trimmed
    if fallback_year is not None:
        return f"untitled-{fallback_year}"
    return "untitled"
