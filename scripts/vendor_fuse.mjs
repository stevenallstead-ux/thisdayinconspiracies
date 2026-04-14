#!/usr/bin/env node
// Vendor fuse.min.js from node_modules into js/vendor/ so the homepage
// loads a pinned, same-origin copy (no CDN). Version is written into
// dist/autocomplete-index.json by build_autocomplete.py at build time
// so runtime can assert a match.
//
// Run: npm run vendor:fuse
import { copyFileSync, readFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const src = resolve(root, 'node_modules/fuse.js/dist/fuse.min.mjs');
const dstDir = resolve(root, 'js/vendor');
const dst = resolve(dstDir, 'fuse.min.mjs');

mkdirSync(dstDir, { recursive: true });
copyFileSync(src, dst);

const pkg = JSON.parse(
  readFileSync(resolve(root, 'node_modules/fuse.js/package.json'), 'utf8')
);
console.log(`Vendored fuse.js@${pkg.version} → js/vendor/fuse.min.mjs`);
