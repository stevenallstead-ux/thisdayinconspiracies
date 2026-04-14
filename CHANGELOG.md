# Changelog

All notable changes to This Day in Conspiracies. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version scheme: `MAJOR.MINOR.PATCH.MICRO` (4-digit).

## [Unreleased]

### Added (WITHHELD Easter egg)
- 10 curated "withheld" decoy entities in `data/withheld_entities.json` (MJ-12 Documents, Operation Northwoods Original Plan, JFK Tape Reel 7, Gulf of Tonkin True Cable, Roswell Debris Inventory, CIA Acoustic Kitty Prototype, Bilderberg 2026 Attendee List, Epstein Flight Logs Vol 2, Recipe for Coca-Cola, Bigfoot's Dental Records). They surface in autocomplete with a distinct WITHHELD tag (red background) but never enter the entity registry or the edges graph.
- New `withheld:` URL namespace alongside `event:` and `entity:`. Share URL like `?from=withheld:mj-12-documents&to=event:1947-the-roswell-incident`.
- FOIA-styled mock document Easter egg (`.withheld-document`): rotated CLASSIFIED stamp, black SUBJECT bar, file-number metadata, FILE WITHHELD UNDER EXEMPTION (b)(1) text, DECLASSIFICATION DENIED stamp, italic Operator-voice quote selected deterministically from a 5-line bible.
- Both-endpoints-withheld variant copy: BOTH FILES WITHHELD.
- 4 new E2E tests, 4 new Python tests. Totals: **59 Python + 32 JS unit + 15 E2E = 106 green** (was 98).

### Added (Connect-the-Files Expansion — K-shortest paths + corpus)
- **K-shortest paths in `js/graph.js`** — new `shortestPaths(from, to, opts)` API enumerates every simple path within ε of optimal cost (defaults: tolerance 0.15, maxPaths 8). Cost-bounded DFS, sub-millisecond at corpus scale. `pickPath(paths, seed)` selects deterministically. `shortestPath` becomes a thin wrapper for backward compatibility.
- **Corpus expansion: +35 events, +153 entities** (`scripts/expand_corpus_phase1.py`) targeting 5 under-represented domains: deep history pre-1900 (Knights Templar through Harding), music industry deaths (Buddy Holly through Avicii), finance/banking (Jekyll Island through FTX), tech industry secrecy (Apple founding through CrowdStrike outage), medical/pharmaceutical (Tuskegee through COVID origin), plus the foundational 1947 NSA / CIA Act. Graph: 138 events / 480 entities / 288 edges, 138/138 connected.
- **TRACE A DIFFERENT PATH re-roll button** in chain footer — when alternates exist, shows the count and advances `?seed=N` on click. URL stays the canonical pointer to a specific chain — same URL → same chain across visitors.
- 11 new tests: 8 K-shortest unit cases + 3 alt-path E2E specs. **Totals: 55 Python + 32 JS unit + 11 E2E = 98 green** (was 84).

### Added (Phase C — Connect-Any-Two homepage)
- `js/graph.js` — Dijkstra + binary min-heap on the prebuilt edges graph. Tie-break: cost → hops → lex-min path. Self-loop returns length-0. NaN/Infinity throws a named error. `addVirtualNode`/`removeVirtualNode` for Stage 4 entity-level Connect.
- `js/shared.js` — extracted helpers (`escapeHtml`, `pad`, `formatFullDate`, `renderEventCard` with optional Related Files footer per Issue 2B).
- `js/today.js` + `today/index.html` — daily-entry page moved from `/`. Back-link to Connect homepage.
- `js/connect.js` + rewritten `index.html` — Connect-Any-Two homepage. Loads data + edges + autocomplete + Fuse index in parallel. Loading/searching UI states. Smooth-scroll to chain. Share URLs `?from=event:X&to=entity:Y` (OV-14 namespace). Fuse version assertion (OV-3) with `Fuse.createIndex` fallback. Virtual super-source/super-sink for entity endpoints (Stage 4 ready).
- CSS for Connect tool, autocomplete dropdown (FILE/PERSON/ENTITY tags), chain VIA dividers, end-of-chain row, error states, Related Files footer, mobile fallback at ≤520px (inputs stack, CTA full-width, header link static).
- Root `script.js` deleted — replaced by `js/today.js`.

### Added (Phase C — `generate_entry.py` hardenings)
- **OV-2** Wikipedia extract sanitization (`sanitize_for_prompt`) — strips control chars, markdown links, and known prompt-injection phrases before LLM call.
- **OV-1** Collision-safe ID assignment (`assign_id`) — suffixes `-2`/`-3` and logs to `id_collisions.log`.
- **OV-5** Honest liveness signal — `last_ingest_at` bumped on every successful append.
- **Stage 1 task 9 + OV-7** Entity auto-tag (`auto_tag_entities` + `apply_entity_tags`) — extra LLM call tags new entries; proposed entities land quarantined and promote when ≥2 events mention them.

### Tests
- 19 new pytest cases in `tests/python/test_generate_entry.py` (LLM mocked via `pytest-mock`).
- 6 Playwright E2E specs (8 tests): happy path chain, no-path, archive-unavailable, stale URL, self-loop, /today/ regression + back-link.
- GHA workflow runs Playwright + chromium in CI; uploads `playwright-report/` on failure.
- Totals: 55 Python + 21 JS unit + 8 E2E = **84 green**.

### Added (Phase A + B — earlier this branch)
- Git repo initialized; public on GitHub at `stevenallstead-ux/thisdayinconspiracies`.
- CI workflow (`.github/workflows/deploy.yml`) — Python + Node test runners, build artifact staging. Cloudflare Pages deploy step is wired but gated off until CF secrets are added.
- Node test infrastructure — `package.json`, `vitest`, `@playwright/test`, pinned `fuse.js@7.3.0` vendored into `js/vendor/fuse.min.mjs` (no CDN).
- Directory scaffolding: `data/`, `js/vendor/`, `scripts/`, `tests/{python,js,e2e}/`.
- Hand-rolled ASCII-only slugify (`scripts/_slug.py`) with 23 golden tests.
- ID migration: stable `${year}-${slug(title)}` IDs on all 103 seed entries. Collision-safe (suffix `-2`/`-3` + `id_collisions.log`). Plus top-level `last_ingest_at` for the honest liveness signal.
- Entity graph: 327 hand-curated entities (`data/entities.json`) across person/org/place/program/event/topic. Every seed event tagged with 3-7 entities (avg 5.4). All 103 events connected.
- Build pipeline:
  - `scripts/derive_edges.py` — hub-penalty weighted edges, top-3 rarest UNION cap, `<0.05` prune, quarantine skip + ≥2-occurrence promotion. 213 edges.
  - `scripts/build_autocomplete.py` + `scripts/_build_fuse_index.mjs` — 430 autocomplete items + pre-built Fuse index with `fuse_version` assertion.
- Tests: 36 Python (slugify + derive_edges) + 2 JS sanity — all green.
