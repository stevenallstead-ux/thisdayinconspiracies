# TODOs — This Day in Conspiracies

## Post-Stage-1 Polish

### Accessibility pass for Connect-Any-Two homepage

- **What:** ARIA combobox pattern for the Fuse.js autocomplete (role="combobox", aria-expanded, aria-controls, aria-activedescendant), keyboard navigation (↑↓ to move through suggestions, Enter to select, Escape to close, Tab to move between FROM/TO/button), focus-visible styles for keyboard users, screen reader labels for the red `─── VIA [ENTITY] ───` chain divider rows so non-visual users hear "connected via CIA" instead of decorative dashes.
- **Why:** Stage 1 ships with mobile CSS inline (Pass 6 decision in design review — see plan file) so phone visitors don't bounce, but a11y stays deferred. Keyboard nav is table-stakes for the autocomplete pattern; share-link traffic includes assistive-tech users.
- **Pros:** Passes WCAG AA for the core flow. Opens the share hook to assistive-tech users. Removes the embarrassment of shipping a desktop-only-keyboard autocomplete in 2026.
- **Cons:** ~3-5 hours of focused work. Fuse.js has no built-in ARIA component, so the combobox pattern is hand-rolled against the [WAI ARIA Authoring Practices combobox spec](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/).
- **Context:** Originally bundled with a "mobile layout" TODO under `/plan-ceo-review` HOLD SCOPE (2026-04-14). Mobile portion was pulled into Stage 1 during `/plan-design-review` (2026-04-14, Pass 6) as a single 30-line CSS media query. Remaining a11y work is harder to defer because share-link traffic = unpredictable user mix.
- **Effort:** S (human, ~3-5 hr) → S (CC+gstack, ~30-45 min)
- **Priority:** P2
- **Depends on / blocked by:** Stage 1 ship (homepage rewrite, autocomplete implementation, chain divider markup must exist before being made accessible).

### Entity-split migration format

- **What:** Add `data/entity_aliases_retired.json` with `{old_id: [new_id, ...]}`. Have `scripts/derive_edges.py` rewrite historical entity references on rebuild so splitting an entity (e.g. `mkultra` → `mkultra-phase-1` + `mkultra-subproject-68`) doesn't break old chain share URLs.
- **Why:** Plan locks "IDs never change once written" (design doc line 53). That promise is unenforceable under real historical-disambiguation pressure without a retired-alias pointer map. Flagged during `/plan-eng-review` outside voice (2026-04-14, OV-4).
- **Pros:** Future-proofs URL stability — the thing the share hook depends on.
- **Cons:** Nobody needs it until ~500+ events in; premature at Stage 1 scale.
- **Context:** 103 seed entities hand-tagged as single concepts. As the corpus grows and hand-tagging surfaces historical nuance the seed missed, some entities WILL want splitting. Without this migration format, the first split silently breaks every old share URL that routed through the now-ambiguous entity. Files referenced: `scripts/derive_edges.py`, `data/entities.json`, future `data/entity_aliases_retired.json`.
- **Effort:** S (human, ~2-3 hr) → S (CC+gstack, ~30 min)
- **Priority:** P3
- **Depends on / blocked by:** First real entity-split need (nothing blocks the capture itself; the build waits for a concrete use case).

### data.json file lock (race-condition guard)

- **What:** Add POSIX `fcntl.flock` or atomic `.tmp`+rename in `generate_entry.py:save_data` so two concurrent invocations (cron + manual `--date` backfill) can't silently drop an entry.
- **Why:** Current `save_data` at `generate_entry.py:79-82` does a plain `open("w") + json.dump`. If two processes read data.json simultaneously, each append one entry, and both write back — last writer wins, one entry silently lost. Flagged during `/plan-eng-review` outside voice (2026-04-14, OV-6).
- **Pros:** Eliminates the race-condition bug class. Small code change (~20 lines).
- **Cons:** `fcntl` is POSIX-only (Windows dev needs a different primitive). Atomic rename wants careful encoding handling. Probability of the race is near-zero for a solo builder.
- **Context:** Cron runs once/day; manual backfills are rare. Failure mode is SILENT (no error, just a missing entry). The quiet-failure property is what makes it worth capturing even at low probability.
- **Effort:** XS (human, ~30 min) → XS (CC+gstack, ~10 min)
- **Priority:** P3
- **Depends on / blocked by:** First observed race incident (or nothing, if you just want to ship it defensively).

### ?debug=1 chain introspection

- **What:** Add a `?debug=1` query-string flag to the homepage. When set, after the chain renders, append a debug panel showing: every edge weight on the chosen path, the top-3 alternative paths considered with their total weights, each event's entity list, and the two endpoint IDs. Dev-only, not linked from the UI.
- **Why:** When a user says "my chain is wrong — it went via CIA instead of via NASA," there's currently zero runtime introspection. Reproducing the bug requires rebuilding the graph locally and manually re-running Dijkstra. `?debug=1` turns that into a one-URL copy-paste. Flagged during `/plan-eng-review` outside voice (2026-04-14, OV-11).
- **Pros:** Huge support-burden reduction once chain-share traffic grows. Zero production UX cost (feature-flagged).
- **Cons:** Exposes internal edge weights to anyone finding the query string. Low info-leak risk — all edges are derived from public data.json + entities.json.
- **Context:** Builds on Stage 1's `js/graph.js` Dijkstra implementation. The function already knows the path cost; `?debug=1` just exposes it plus a few alternative-path runs. Files to touch: `js/connect.js`, maybe `js/graph.js` to expose a second API `shortestPathsTopK(aId, bId, k=3)`.
- **Effort:** S (human, ~1 hr) → S (CC+gstack, ~20 min)
- **Priority:** P2 once chain-share traffic exceeds "friends I sent it to," P3 until then.
- **Depends on / blocked by:** Stage 1 ship (homepage + graph.js must exist before the debug overlay can read from them).
