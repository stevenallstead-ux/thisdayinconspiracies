// js/connect.js — Connect-Any-Two homepage client.
//
// Loads the prebuilt data layer (data.json, entities.json, dist/edges.json,
// dist/autocomplete.json, dist/autocomplete-index.json + vendored fuse.js),
// wires up two autocomplete inputs, handles the chain render, and covers
// every design-locked error state.
//
// Share URLs: /?from=event:1963-jfk-assassinated-in-dallas&to=entity:cia
//   Both `event:` and `entity:` prefixes are mandatory.

import Fuse from './vendor/fuse.min.mjs';

import {
  escapeHtml,
  loadData,
  loadJSON,
  renderEventCard,
} from './shared.js';

const TODAY_PATH = '/today/';
const HOME_PATH = '/';

// ── Elements ────────────────────────────────────────────────────────
const fromInput = document.getElementById('from-input');
const toInput = document.getElementById('to-input');
const fromDropdown = document.getElementById('from-dropdown');
const toDropdown = document.getElementById('to-dropdown');
const findButton = document.getElementById('find-button');
const resultRegion = document.getElementById('result-region');
const archiveUpdated = document.getElementById('archive-updated');

// ── State ───────────────────────────────────────────────────────────
const state = {
  data: null,
  entities: null,
  entityById: new Map(),
  eventById: new Map(),
  adjacency: null,
  graph: null,
  autocomplete: null, // array of items
  fuse: null,
  selectedFrom: null, // { id, kind }
  selectedTo: null,   // { id, kind }
  loading: true,
  searching: false,
  // K-shortest paths state (Phase 1 expansion).
  // currentPaths holds the latest enumerated alternatives so the
  // re-roll button can pick a different one without re-running Dijkstra.
  currentPaths: [],
  seed: 0,
};

function setLoadingUi(loading) {
  state.loading = loading;
  fromInput.disabled = loading;
  toInput.disabled = loading;
  findButton.disabled = loading || state.searching;
  if (loading) {
    fromInput.placeholder = 'LOADING ARCHIVE...';
    toInput.placeholder = 'LOADING ARCHIVE...';
    findButton.querySelector('.cta-label').textContent = 'INITIALIZING...';
  } else {
    fromInput.placeholder = 'JFK ASSASSINATION';
    toInput.placeholder = 'MKULTRA';
    findButton.querySelector('.cta-label').textContent = 'FIND THE CONNECTION';
  }
}

function setSearchingUi(searching) {
  state.searching = searching;
  findButton.disabled = searching || state.loading;
  findButton.querySelector('.cta-label').textContent = searching
    ? 'SEARCHING...'
    : 'FIND THE CONNECTION';
}

// ── Rendering helpers ───────────────────────────────────────────────
function renderError(title, body, { includeTodayLink = false, includeHomeLink = false } = {}) {
  const extra = includeTodayLink
    ? `<p class="error-link"><a href="${TODAY_PATH}">Today's File &rarr;</a></p>`
    : includeHomeLink
      ? `<p class="error-link"><a href="${HOME_PATH}">Return to archive home</a></p>`
      : '';
  resultRegion.innerHTML = `
    <div class="empty-state error-state">
      <p class="error-title">${escapeHtml(title)}</p>
      ${body ? `<p class="error-body">${escapeHtml(body)}</p>` : ''}
      ${extra}
    </div>
  `;
}

function renderInitialPlaceholder() {
  resultRegion.innerHTML = `
    <div class="empty-state">
      <p>TYPE TWO SUBJECTS.</p>
      <p>WE WILL ASSEMBLE THE FILE.</p>
    </div>
  `;
}

function renderViaDivider(entityIds) {
  const names = entityIds
    .map((id) => state.entityById.get(id)?.name || id)
    .filter(Boolean)
    .slice(0, 2); // at most 2 names to keep the divider readable
  const text = names.length ? `VIA ${names.join(' + ').toUpperCase()}` : 'VIA [REDACTED]';
  return `<div class="chain-divider section-heading-chain">— ${escapeHtml(text)} —</div>`;
}

function renderEndOfChainRow() {
  const altCount = Math.max(0, state.currentPaths.length - 1);
  const altButton = altCount > 0
    ? `<a href="#" class="alt-path-button" id="alt-path-button">TRACE A DIFFERENT PATH (${altCount} ${altCount === 1 ? 'alternative' : 'alternatives'}) &rarr;</a>`
    : '';
  return `
    <div class="chain-footer-row">
      <a href="#" class="trace-another" id="trace-another">TRACE ANOTHER &rarr;</a>
      ${altButton}
      <span class="declassify-hint" aria-hidden="true">[DECLASSIFY THIS THREAD]</span>
    </div>
  `;
}

function renderChain(pathResult) {
  const { events, edges } = pathResult;
  const parts = [];

  for (let i = 0; i < events.length; i++) {
    const evt = state.eventById.get(events[i]);
    if (!evt) {
      parts.push(`<p class="chain-note">Missing event data for id: ${escapeHtml(events[i])}</p>`);
      continue;
    }
    parts.push(renderEventCard({ evt }));

    if (i < edges.length) {
      parts.push(renderViaDivider(edges[i].via_entity_ids || []));
    }
  }

  parts.push(renderEndOfChainRow());
  resultRegion.innerHTML = parts.join('');

  const traceAnother = document.getElementById('trace-another');
  if (traceAnother) {
    traceAnother.addEventListener('click', (e) => {
      e.preventDefault();
      resetSearch();
      fromInput.focus();
    });
  }

  const altPathButton = document.getElementById('alt-path-button');
  if (altPathButton) {
    altPathButton.addEventListener('click', (e) => {
      e.preventDefault();
      if (state.currentPaths.length <= 1) return;
      state.seed = (state.seed + 1) % state.currentPaths.length;
      const next = state.currentPaths[state.seed];
      renderChain({ events: next.events, edges: next.edges });
      // Update share URL with the new seed (omit seed=0 to keep URLs clean).
      if (state.selectedFrom && state.selectedTo) {
        updateShareUrl(state.selectedFrom, state.selectedTo);
      }
    });
  }

  resultRegion.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderSelfLoopChain(evtId) {
  const evt = state.eventById.get(evtId);
  if (!evt) {
    renderError(
      'ARCHIVE ENTRY NOT FOUND: ' + evtId,
      '',
      { includeHomeLink: true },
    );
    return;
  }
  resultRegion.innerHTML = `
    <div class="chain-note self-loop-note">THE FILE REFERS TO ITSELF.</div>
    ${renderEventCard({ evt })}
    ${renderEndOfChainRow()}
  `;
  resultRegion.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function resetSearch() {
  state.selectedFrom = null;
  state.selectedTo = null;
  state.currentPaths = [];
  state.seed = 0;
  fromInput.value = '';
  toInput.value = '';
  closeDropdown(fromDropdown);
  closeDropdown(toDropdown);
  history.replaceState({}, '', HOME_PATH);
  renderInitialPlaceholder();
}

// ── Autocomplete ────────────────────────────────────────────────────
function openDropdown(el) {
  el.classList.add('open');
  el.setAttribute('aria-hidden', 'false');
}

function closeDropdown(el) {
  el.classList.remove('open');
  el.setAttribute('aria-hidden', 'true');
  el.innerHTML = '';
}

function renderDropdownRow(item) {
  const meta = item.kind === 'event'
    ? `<span class="ac-meta">${escapeHtml(String(item.year))} &middot; ${escapeHtml(item.category)}</span>`
    : '';
  const tagClass = item.kind === 'event'
    ? 'ac-tag-file'
    : item.kind === 'withheld'
      ? 'ac-tag-withheld'
      : 'ac-tag-entity';
  return `
    <div class="ac-row" role="option" data-id="${escapeHtml(item.id)}" data-kind="${escapeHtml(item.kind)}">
      <div class="ac-row-main">
        <span class="ac-label">${escapeHtml(item.label)}</span>
        ${meta}
      </div>
      <span class="ac-tag ${tagClass}">${escapeHtml(item.tag)}</span>
    </div>
  `;
}

function renderDropdownEmpty(el) {
  el.innerHTML = `<div class="ac-row ac-empty">NO MATCHES IN ARCHIVE.</div>`;
  openDropdown(el);
}

function updateDropdown(query, dropdownEl) {
  if (!state.fuse || !query || query.length < 1) {
    closeDropdown(dropdownEl);
    return;
  }
  const results = state.fuse.search(query, { limit: 8 });
  if (!results.length) {
    renderDropdownEmpty(dropdownEl);
    return;
  }
  dropdownEl.innerHTML = results.map((r) => renderDropdownRow(r.item)).join('');
  openDropdown(dropdownEl);
}

function attachInputHandlers(input, dropdown, onSelect) {
  input.addEventListener('input', (e) => {
    if (state.loading) return;
    updateDropdown(e.target.value, dropdown);
  });

  input.addEventListener('focus', (e) => {
    if (state.loading) return;
    if (e.target.value.length >= 1) {
      updateDropdown(e.target.value, dropdown);
    }
  });

  input.addEventListener('blur', () => {
    // Delay so click events on dropdown rows register first.
    setTimeout(() => closeDropdown(dropdown), 150);
  });

  dropdown.addEventListener('mousedown', (e) => {
    const row = e.target.closest('.ac-row[data-id]');
    if (!row) return;
    const id = row.dataset.id;
    const kind = row.dataset.kind;
    const item = state.autocomplete.find((i) => i.id === id && i.kind === kind);
    if (!item) return;
    input.value = item.label;
    onSelect({ id: item.id, kind: item.kind });
    closeDropdown(dropdown);
  });
}

// ── WITHHELD Easter egg ─────────────────────────────────────────────
// Pick one Operator quote based on a deterministic hash of the two ids,
// so the same URL renders the same flavor text every visit (consistent
// with seed determinism elsewhere).
const OPERATOR_QUOTES = [
  'We pulled both files. They are not in the same room. They are not in the same building. They are not in the same archive.',
  'The cabinet was empty when we opened it. It has always been empty.',
  'This file was destroyed in the 1971 server room fire that did not occur.',
  'The chain of custody breaks here. It has always broken here.',
  'There is a folder. There is a label on the folder. The folder contains the label.',
];

function pickOperatorQuote(seedString) {
  let h = 0;
  for (let i = 0; i < seedString.length; i++) {
    h = ((h << 5) - h + seedString.charCodeAt(i)) | 0;
  }
  const idx = ((h % OPERATOR_QUOTES.length) + OPERATOR_QUOTES.length) % OPERATOR_QUOTES.length;
  return OPERATOR_QUOTES[idx];
}

function withheldLabel(sel) {
  if (sel.kind === 'withheld') {
    const item = state.autocomplete.find((i) => i.id === sel.id && i.kind === 'withheld');
    return item ? item.label : sel.id;
  }
  if (sel.kind === 'event') {
    const ev = state.eventById.get(sel.id);
    return ev ? ev.title : sel.id;
  }
  if (sel.kind === 'entity') {
    const ent = state.entityById.get(sel.id);
    return ent ? ent.name : sel.id;
  }
  return sel.id;
}

function renderWithheldDocument(fromSel, toSel) {
  const fromLabel = withheldLabel(fromSel);
  const toLabel = withheldLabel(toSel);
  const bothWithheld = fromSel.kind === 'withheld' && toSel.kind === 'withheld';
  const fileNo = (Math.abs((fromSel.id + toSel.id).split('').reduce(
    (h, c) => ((h << 5) - h + c.charCodeAt(0)) | 0, 0,
  )) % 900000 + 100000).toString();
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, ' ');
  const exemption = bothWithheld
    ? '<strong>BOTH FILES WITHHELD.</strong> The requested cross-reference does not exist in any classification. Both subjects fall under exemption (b)(1) of the Freedom of Information Act, 5 U.S.C. § 552.'
    : '<strong>FILE WITHHELD UNDER EXEMPTION (b)(1).</strong> No corroborating record exists in the archive linking these subjects. Either no link was ever recorded — or the link itself was redacted before this archive was assembled.';
  const quote = pickOperatorQuote(fromSel.id + '|' + toSel.id);

  resultRegion.innerHTML = `
    <div class="withheld-document">
      <span class="classified-stamp-large">CLASSIFIED</span>
      <div class="subject-bar">
        <span class="subject-line">SUBJECT: ${escapeHtml(fromLabel)}</span>
        <span class="subject-line">&rarr; ${escapeHtml(toLabel)}</span>
      </div>
      <div class="file-meta">
        <span>FILED: ${escapeHtml(today.toUpperCase())}</span>
        <span>FILE NO: ${escapeHtml(fileNo)}</span>
        <span>STATUS: WITHHELD</span>
      </div>
      <p class="exemption-text">${exemption}</p>
      <p class="exemption-text">DECLASSIFICATION REQUEST: <strong>DENIED</strong>.</p>
      <span class="denial-stamp">DECLASSIFICATION DENIED</span>
      <p class="operator-quote">&mdash; ${escapeHtml(quote)}</p>
    </div>
    ${renderEndOfChainRow()}
  `;

  // Re-attach the TRACE ANOTHER button (re-roll button is hidden because
  // currentPaths is empty — no paths to alternate through).
  const traceAnother = document.getElementById('trace-another');
  if (traceAnother) {
    traceAnother.addEventListener('click', (e) => {
      e.preventDefault();
      resetSearch();
      fromInput.focus();
    });
  }

  resultRegion.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Search + chain ──────────────────────────────────────────────────
function eventIdsForEntity(entityId) {
  return state.data.events
    .filter((ev) => (ev.entities || []).includes(entityId))
    .map((ev) => ev.id);
}

function enrichViaWithEntityNames(edges) {
  // already resolved by renderViaDivider at draw time. placeholder.
  return edges;
}

function findAndRenderChain(fromSel, toSel) {
  if (!fromSel || !toSel) {
    return;
  }

  // WITHHELD Easter egg: if either endpoint is a decoy, short-circuit
  // the graph entirely and render the FOIA mock document. currentPaths
  // is cleared so the re-roll button doesn't appear.
  if (fromSel.kind === 'withheld' || toSel.kind === 'withheld') {
    state.currentPaths = [];
    state.seed = 0;
    renderWithheldDocument(fromSel, toSel);
    updateShareUrl(fromSel, toSel);
    return;
  }

  // Same endpoint (same kind + same id) → THE FILE REFERS TO ITSELF.
  if (fromSel.id === toSel.id && fromSel.kind === toSel.kind) {
    if (fromSel.kind === 'event') {
      renderSelfLoopChain(fromSel.id);
    } else {
      // Entity-to-same-entity: pick an arbitrary event tagged with it, or show note.
      const events = eventIdsForEntity(fromSel.id);
      if (events.length) {
        renderSelfLoopChain(events[0]);
      } else {
        renderError('THE FILE REFERS TO ITSELF.', '', { includeHomeLink: false });
      }
    }
    return;
  }

  setSearchingUi(true);

  // Entity endpoint: add a virtual super-node connected to every event
  // tagged with that entity. Run Dijkstra. Strip virtual node from result.
  const VIRTUAL_PREFIX = '__virtual__:';
  const virtualFromId = fromSel.kind === 'entity' ? VIRTUAL_PREFIX + fromSel.id + ':from' : null;
  const virtualToId = toSel.kind === 'entity' ? VIRTUAL_PREFIX + toSel.id + ':to' : null;

  try {
    if (virtualFromId) {
      const targets = eventIdsForEntity(fromSel.id);
      if (!targets.length) {
        renderError(
          'NO KNOWN CONNECTION.',
          `No events tagged with "${state.entityById.get(fromSel.id)?.name || fromSel.id}".`,
        );
        return;
      }
      state.graph.addVirtualNode(virtualFromId, targets);
    }
    if (virtualToId) {
      const targets = eventIdsForEntity(toSel.id);
      if (!targets.length) {
        renderError(
          'NO KNOWN CONNECTION.',
          `No events tagged with "${state.entityById.get(toSel.id)?.name || toSel.id}".`,
        );
        return;
      }
      state.graph.addVirtualNode(virtualToId, targets);
    }

    const startId = virtualFromId || fromSel.id;
    const endId = virtualToId || toSel.id;

    if (!state.graph.has(startId)) {
      renderError('ARCHIVE ENTRY NOT FOUND: ' + fromSel.id, '', { includeHomeLink: true });
      return;
    }
    if (!state.graph.has(endId)) {
      renderError('ARCHIVE ENTRY NOT FOUND: ' + toSel.id, '', { includeHomeLink: true });
      return;
    }

    const multi = state.graph.shortestPaths(startId, endId);
    if (!multi || multi.paths.length === 0) {
      renderError('NO KNOWN CONNECTION.', 'THE FILE ENDS HERE.');
      return;
    }

    // Strip virtual nodes from each enumerated path.
    const stripped = multi.paths.map((path) => ({
      events: path.events.filter((id) => !id.startsWith(VIRTUAL_PREFIX)),
      edges: path.edges.filter(
        (e) => !e.from.startsWith(VIRTUAL_PREFIX) && !e.to.startsWith(VIRTUAL_PREFIX),
      ),
      cost: path.cost,
    })).filter((p) => p.events.length > 0);

    if (stripped.length === 0) {
      renderError('NO KNOWN CONNECTION.', 'THE FILE ENDS HERE.');
      return;
    }

    state.currentPaths = stripped;
    // Seed already set from URL on boot; clamp to valid range.
    if (state.seed < 0 || state.seed >= stripped.length) {
      state.seed = ((state.seed % stripped.length) + stripped.length) % stripped.length;
    }
    const chosen = stripped[state.seed];

    renderChain({ events: chosen.events, edges: enrichViaWithEntityNames(chosen.edges) });
    updateShareUrl(fromSel, toSel);
  } finally {
    if (virtualFromId) state.graph.removeVirtualNode(virtualFromId);
    if (virtualToId) state.graph.removeVirtualNode(virtualToId);
    setSearchingUi(false);
  }
}

function updateShareUrl(fromSel, toSel) {
  const qs = new URLSearchParams({
    from: `${fromSel.kind}:${fromSel.id}`,
    to: `${toSel.kind}:${toSel.id}`,
  });
  // Omit seed=0 to keep the default URL clean (backward compatible).
  if (state.seed > 0) qs.set('seed', String(state.seed));
  history.replaceState({}, '', `?${qs.toString()}`);
}

// ── URL share hook ──────────────────────────────────────────────────
function parseNamespacedId(raw) {
  if (!raw || typeof raw !== 'string') return null;
  const m = raw.match(/^(event|entity|withheld):(.+)$/);
  if (!m) return null;
  return { kind: m[1], id: m[2] };
}

function applyShareUrl() {
  const params = new URLSearchParams(window.location.search);
  const fromRaw = params.get('from');
  const toRaw = params.get('to');
  // Seed param is read for ALL nav (even no from/to) so reset paths
  // back to default behave correctly.
  const seedRaw = params.get('seed');
  if (seedRaw !== null) {
    const parsed = parseInt(seedRaw, 10);
    state.seed = Number.isFinite(parsed) ? parsed : 0;
  }
  if (!fromRaw && !toRaw) return;

  const from = parseNamespacedId(fromRaw);
  const to = parseNamespacedId(toRaw);

  if (!from || !to) {
    renderError(
      'ARCHIVE ENTRY NOT FOUND: ' + (fromRaw || toRaw || '?'),
      'Share URL is malformed — expected ?from=event:X&to=entity:Y',
      { includeHomeLink: true },
    );
    return;
  }

  // Validate IDs exist.
  const fromItem = state.autocomplete.find((i) => i.id === from.id && i.kind === from.kind);
  const toItem = state.autocomplete.find((i) => i.id === to.id && i.kind === to.kind);
  if (!fromItem) {
    renderError('ARCHIVE ENTRY NOT FOUND: ' + from.id, '', { includeHomeLink: true });
    return;
  }
  if (!toItem) {
    renderError('ARCHIVE ENTRY NOT FOUND: ' + to.id, '', { includeHomeLink: true });
    return;
  }

  state.selectedFrom = from;
  state.selectedTo = to;
  fromInput.value = fromItem.label;
  toInput.value = toItem.label;
  findAndRenderChain(from, to);
}

// ── Boot ────────────────────────────────────────────────────────────
async function boot() {
  try {
    const [data, entities, adjacency, autocomplete, indexPayload] = await Promise.all([
      loadData('/data/data.json'),
      loadJSON('/data/entities.json'),
      loadJSON('/dist/edges.json'),
      loadJSON('/dist/autocomplete.json'),
      loadJSON('/dist/autocomplete-index.json'),
    ]);

    state.data = data;
    state.entities = entities;
    state.adjacency = adjacency;
    state.autocomplete = autocomplete;

    entities.forEach((e) => state.entityById.set(e.id, e));
    data.events.forEach((ev) => state.eventById.set(ev.id, ev));

    // Version-assert the Fuse index. Mismatch → rebuild from raw.
    let fuseIndex = null;
    if (indexPayload && indexPayload.fuse_version === Fuse.version) {
      try {
        fuseIndex = Fuse.parseIndex(indexPayload.index);
      } catch (err) {
        console.warn('[connect] Fuse.parseIndex failed, rebuilding:', err);
      }
    } else {
      console.warn(
        `[connect] Fuse version mismatch (build=${indexPayload?.fuse_version}, runtime=${Fuse.version}). Rebuilding index.`,
      );
    }

    const keys = (indexPayload && indexPayload.keys) || [
      { name: 'label', weight: 0.7 },
      { name: 'aliases', weight: 0.25 },
      { name: 'id', weight: 0.05 },
    ];

    state.fuse = new Fuse(autocomplete, {
      keys,
      threshold: 0.4,
      includeScore: false,
    }, fuseIndex);

    const { createGraph } = await import('./graph.js');
    state.graph = createGraph(adjacency);

    // Honest liveness signal from data.json last_ingest_at (OV-5).
    if (archiveUpdated && data.last_ingest_at) {
      archiveUpdated.textContent = `ARCHIVE LAST UPDATED ${formatUpdateTimestamp(data.last_ingest_at)}`;
    }

    setLoadingUi(false);
    renderInitialPlaceholder();

    attachInputHandlers(fromInput, fromDropdown, (sel) => {
      state.selectedFrom = sel;
    });
    attachInputHandlers(toInput, toDropdown, (sel) => {
      state.selectedTo = sel;
    });

    findButton.addEventListener('click', () => {
      if (state.loading || state.searching) return;
      // Fallback: if input has text but no explicit selection, use the top
      // Fuse match so Enter-without-dropdown-click still works.
      if (!state.selectedFrom && fromInput.value.trim()) {
        const top = state.fuse.search(fromInput.value.trim(), { limit: 1 })[0];
        if (top) state.selectedFrom = { id: top.item.id, kind: top.item.kind };
      }
      if (!state.selectedTo && toInput.value.trim()) {
        const top = state.fuse.search(toInput.value.trim(), { limit: 1 })[0];
        if (top) state.selectedTo = { id: top.item.id, kind: top.item.kind };
      }
      if (!state.selectedFrom) {
        fromInput.focus();
        return;
      }
      if (!state.selectedTo) {
        toInput.focus();
        return;
      }
      // Fresh user click → start at optimal path. Re-rolls advance seed.
      state.seed = 0;
      findAndRenderChain(state.selectedFrom, state.selectedTo);
    });

    // Enter in inputs submits too.
    [fromInput, toInput].forEach((input) => {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !state.loading && !state.searching) {
          e.preventDefault();
          findButton.click();
        }
      });
    });

    applyShareUrl();
  } catch (err) {
    console.error('[connect] archive load failed:', err);
    setLoadingUi(false);
    findButton.disabled = true;
    renderError('ARCHIVE TEMPORARILY UNAVAILABLE.', '', { includeTodayLink: true });
  }
}

function formatUpdateTimestamp(iso) {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  const h = String(d.getUTCHours()).padStart(2, '0');
  const min = String(d.getUTCMinutes()).padStart(2, '0');
  return `${y}-${m}-${day} ${h}:${min} UTC`;
}

boot();
