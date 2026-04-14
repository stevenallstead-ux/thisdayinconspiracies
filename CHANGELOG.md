# Changelog

All notable changes to This Day in Conspiracies. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version scheme: `MAJOR.MINOR.PATCH.MICRO` (4-digit).

## [Unreleased]

### Added
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
