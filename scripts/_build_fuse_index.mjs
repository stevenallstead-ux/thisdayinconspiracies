#!/usr/bin/env node
// Build dist/autocomplete-index.json from dist/autocomplete.json.
// Writes fuse_version alongside the serialized index so runtime
// can assert a version match (OV-3 version-lock).
//
// Called by scripts/build_autocomplete.py after it emits autocomplete.json.
import Fuse from 'fuse.js';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const dataPath = resolve(root, 'dist/autocomplete.json');
const outPath = resolve(root, 'dist/autocomplete-index.json');

const items = JSON.parse(readFileSync(dataPath, 'utf8'));

// Keys Fuse indexes + weights. Label is most important; aliases secondary;
// id as fallback so users who paste a share URL fragment can find it.
const keys = [
  { name: 'label', weight: 0.7 },
  { name: 'aliases', weight: 0.25 },
  { name: 'id', weight: 0.05 },
];

const index = Fuse.createIndex(keys, items);
const pkg = JSON.parse(
  readFileSync(resolve(root, 'node_modules/fuse.js/package.json'), 'utf8')
);

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(
  outPath,
  JSON.stringify({ fuse_version: pkg.version, keys, index: index.toJSON() }, null, 2) + '\n'
);

console.log(`[+] Fuse index (fuse.js@${pkg.version}) -> dist/autocomplete-index.json`);
