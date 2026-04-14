# Changelog

All notable changes to This Day in Conspiracies. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version scheme: `MAJOR.MINOR.PATCH.MICRO` (4-digit).

## [Unreleased]

### Added
- Git repo initialized; public on GitHub at `stevenallstead-ux/thisdayinconspiracies`.
- CI workflow (`.github/workflows/deploy.yml`) — Python + Node test runners, build artifact staging. Cloudflare Pages deploy step is wired but gated off until CF secrets are added.
- Node test infrastructure — `package.json`, `vitest`, `@playwright/test`, pinned `fuse.js@^7.0.0` vendored into `js/vendor/fuse.min.mjs` (no CDN).
- Directory scaffolding: `data/`, `js/vendor/`, `scripts/`, `tests/{python,js,e2e}/`.
