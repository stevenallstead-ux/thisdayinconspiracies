// js/connect.js — Connect-Any-Two homepage client.
//
// Two view modes:
//  1. Empty state — connect-form (FROM + TO + CTA). Default for `/`.
//  2. Query state — query-bar + assembly + evidence-wall (cork board with
//     pin-cards and red string between thumbtacks). Triggered by URL params
//     ?from=event:X&to=entity:Y or by clicking FIND THE CONNECTION.
//
// Preserves: K-shortest paths re-roll, WITHHELD Easter egg short-circuit,
// self-loop / no-path / archive-unavailable error states.

import Fuse from './vendor/fuse.min.mjs';

import {
  escapeHtml,
  loadData,
  loadJSON,
  renderPinCard,
  MONTHS_SHORT,
  pad,
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

const formSection = document.getElementById('connect-form-section');
const queryBar = document.getElementById('query-bar');
const queryFromValue = document.getElementById('query-from-value');
const queryFromSub = document.getElementById('query-from-sub');
const queryToValue = document.getElementById('query-to-value');
const queryToSub = document.getElementById('query-to-sub');
const queryStatus = document.getElementById('query-status');
const traceAnotherTop = document.getElementById('trace-another-top');
const tapeStatus = document.getElementById('tape-status');
const mastheadStamp = document.getElementById('masthead-stamp');
const stampMeta = document.getElementById('stamp-meta');

// ── State ───────────────────────────────────────────────────────────
const state = {
  data: null,
  entities: null,
  entityById: new Map(),
  eventById: new Map(),
  adjacency: null,
  graph: null,
  autocomplete: null,
  fuse: null,
  selectedFrom: null,
  selectedTo: null,
  loading: true,
  searching: false,
  currentPaths: [],
  seed: 0,
  // Last successfully drawn chain — needed for resize redraws.
  lastDrawn: null,
};

// ── Header chrome ───────────────────────────────────────────────────
function setHeaderChrome() {
  const today = new Date();
  const refDate = `${pad(today.getMonth() + 1)}${pad(today.getDate())}`;
  const refLineDate = document.getElementById('ref-date');
  if (refLineDate) refLineDate.textContent = `${refDate}-00${(today.getDate() * 13 % 1000).toString().padStart(3, '0')}`;
  const yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = today.getFullYear();
  const footerEnd = document.getElementById('footer-end');
  if (footerEnd) footerEnd.textContent = `${refDate} / END OF TRANSMISSION`;
}

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

// ── View toggle ─────────────────────────────────────────────────────
function showEmptyState() {
  formSection.hidden = false;
  queryBar.hidden = true;
  mastheadStamp.hidden = true;
  if (tapeStatus) tapeStatus.textContent = 'Transmission Active · Awaiting Query';
  resultRegion.innerHTML = '';
}

function showQueryState(fromSel, toSel, hopCount) {
  formSection.hidden = true;
  queryBar.hidden = false;
  mastheadStamp.hidden = false;

  const fromLabel = labelFor(fromSel);
  const toLabel = labelFor(toSel);
  queryFromValue.innerHTML = renderQueryLabel(fromLabel);
  queryToValue.innerHTML = renderQueryLabel(toLabel);
  queryFromSub.innerHTML = renderQuerySub(fromSel);
  queryToSub.innerHTML = renderQuerySub(toSel);

  if (typeof hopCount === 'number' && hopCount >= 0) {
    queryStatus.textContent = `Chain Complete · ${hopCount} HOP${hopCount === 1 ? '' : 'S'}`;
    if (tapeStatus) tapeStatus.textContent = `Transmission Active · Chain Resolved · ${hopCount} HOP${hopCount === 1 ? '' : 'S'}`;
    if (stampMeta) {
      const today = new Date();
      stampMeta.textContent = `${hopCount} · HOPS · ${pad(today.getMonth() + 1)}·${pad(today.getDate())}·${today.getFullYear()}`;
    }
  } else {
    queryStatus.textContent = 'Query Resolved';
    if (tapeStatus) tapeStatus.textContent = 'Transmission Active · Query Resolved';
    if (stampMeta) stampMeta.textContent = 'FILE WITHHELD';
  }
}

function labelFor(sel) {
  if (!sel) return '';
  if (sel.kind === 'event') {
    const ev = state.eventById.get(sel.id);
    return ev ? ev.title : sel.id;
  }
  if (sel.kind === 'entity') {
    const ent = state.entityById.get(sel.id);
    return ent ? ent.name : sel.id;
  }
  if (sel.kind === 'withheld') {
    const item = state.autocomplete.find((i) => i.id === sel.id && i.kind === 'withheld');
    return item ? item.label : sel.id;
  }
  return sel.id;
}

// Italicize the LAST whole word for visual rhythm (mirrors the reference
// `Suge *Knight*` pattern). Skip if too short.
function renderQueryLabel(text) {
  const safe = escapeHtml(text);
  const words = safe.split(/\s+/);
  if (words.length < 2) return safe;
  const last = words.pop();
  return `${words.join(' ')} <em>${last}</em>`;
}

function renderQuerySub(sel) {
  if (!sel) return '';
  if (sel.kind === 'event') {
    const ev = state.eventById.get(sel.id);
    if (!ev) return 'EVENT';
    return `EVENT &middot; ${escapeHtml(String(ev.year))} &middot; <span class="type-chip">${escapeHtml(ev.category || 'UNEXPLAINED')}</span>`;
  }
  if (sel.kind === 'entity') {
    const ent = state.entityById.get(sel.id);
    const type = (ent && ent.type) ? ent.type.toUpperCase() : 'ENTITY';
    return `ENTITY &middot; ${escapeHtml(type)} &middot; <span class="type-chip entity">PERSON OF INTEREST</span>`;
  }
  if (sel.kind === 'withheld') {
    return `<span class="type-chip" style="background:var(--redact);">WITHHELD</span>`;
  }
  return '';
}

// ── Error rendering ─────────────────────────────────────────────────
function renderError(title, body, { includeTodayLink = false, includeHomeLink = false } = {}) {
  const extra = includeTodayLink
    ? `<p class="error-link"><a href="${TODAY_PATH}">Today's File &rarr;</a></p>`
    : includeHomeLink
      ? `<p class="error-link"><a href="${HOME_PATH}">Return to archive home</a></p>`
      : '';
  resultRegion.innerHTML = `
    <div class="error-state">
      <p class="error-title">${title}</p>
      ${body ? `<p class="error-body">${escapeHtml(body)}</p>` : ''}
      ${extra}
    </div>
  `;
  // Always show form again on error so user can retry.
  formSection.hidden = false;
  queryBar.hidden = true;
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
    ? `<span class="ac-meta">${escapeHtml(String(item.year || ''))} &middot; ${escapeHtml(item.category || '')}</span>`
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
    if (e.target.value.length >= 1) updateDropdown(e.target.value, dropdown);
  });
  input.addEventListener('blur', () => {
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

function renderWithheldDocument(fromSel, toSel) {
  const fromLabel = labelFor(fromSel);
  const toLabel = labelFor(toSel);
  const bothWithheld = fromSel.kind === 'withheld' && toSel.kind === 'withheld';
  const fileNo = (Math.abs((fromSel.id + toSel.id).split('').reduce(
    (h, c) => ((h << 5) - h + c.charCodeAt(0)) | 0, 0,
  )) % 900000 + 100000).toString();
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, ' ');
  const exemption = bothWithheld
    ? '<strong>BOTH FILES WITHHELD.</strong> The requested cross-reference does not exist in any classification. Both subjects fall under exemption (b)(1) of the Freedom of Information Act, 5 U.S.C. § 552.'
    : '<strong>FILE WITHHELD UNDER EXEMPTION (b)(1).</strong> No corroborating record exists in the archive linking these subjects. Either no link was ever recorded — or the link itself was redacted before this archive was assembled.';
  const quote = pickOperatorQuote(fromSel.id + '|' + toSel.id);

  showQueryState(fromSel, toSel, null);
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
    ${renderChainFooter()}
  `;
  attachFooterHandlers();
  scrollToResult();
}

// ── Chain rendering ─────────────────────────────────────────────────
const ROTATIONS = [-2.5, 1.8, -1.4, 2.2, -2.0, 1.2, -1.7, 2.6, -2.2, 1.5];

function renderChainFooter() {
  const altCount = Math.max(0, state.currentPaths.length - 1);
  const altButton = altCount > 0
    ? `<a href="#" class="alt-path-button" id="alt-path-button">TRACE A DIFFERENT PATH (${altCount} ${altCount === 1 ? 'alternative' : 'alternatives'}) &rarr;</a>`
    : '';
  return `
    <div class="chain-footer">
      <a href="#" class="trace-another" id="trace-another">TRACE ANOTHER &rarr;</a>
      ${altButton}
      <span class="declassify-hint" aria-hidden="true">[DECLASSIFY THIS THREAD]</span>
    </div>
  `;
}

function attachFooterHandlers() {
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
      if (state.selectedFrom && state.selectedTo) {
        updateShareUrl(state.selectedFrom, state.selectedTo);
      }
    });
  }
}

function renderAssemblyHead(hopCount) {
  const hopWord = hopCount === 1 ? 'hop' : 'hops';
  const numWord = ['Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten'][hopCount] || String(hopCount);
  return `
    <div class="assembly-head">
      <h2>${escapeHtml(numWord)} ${escapeHtml(hopWord)}. <em>One</em> thread.</h2>
      <div class="legend">
        <span class="line">STRING &middot; NAMED EDGE</span>
        <span class="hops">DASH &middot; FILE BOUNDARY</span>
      </div>
    </div>
  `;
}

function buildBridgeEntities(edges) {
  // Set of entity ids that appear in any edge's via_entity_ids — these get
  // .bridge styling on the chips inside pin-cards.
  const set = new Set();
  edges.forEach((e) => (e.via_entity_ids || []).forEach((id) => set.add(id)));
  return set;
}

function renderChain(pathResult) {
  const { events, edges } = pathResult;
  const hopCount = Math.max(0, events.length - 1);
  showQueryState(state.selectedFrom, state.selectedTo, hopCount);

  const bridge = buildBridgeEntities(edges);

  // Build ambient cork decorations (pinholes + coffee rings, deterministic per-chain).
  const decor = renderCorkDecor(events.length);

  const cards = events.map((evtId, i) => {
    const evt = state.eventById.get(evtId);
    if (!evt) return `<article class="pin-card"><p>Missing: ${escapeHtml(evtId)}</p></article>`;
    const termTape = i === 0 ? 'origin' : (i === events.length - 1 ? 'terminus' : null);
    const rot = ROTATIONS[i % ROTATIONS.length] + 'deg';
    const delay = 0.10 + i * 0.40;
    return renderPinCard({
      evt,
      nodeIndex: i + 1,
      termTape,
      rotation: rot,
      bridgeEntities: bridge,
      delay,
    });
  }).join('');

  // VIA labels for SVG string overlay.
  const viaLabels = edges.map((e) => {
    const names = (e.via_entity_ids || [])
      .map((id) => state.entityById.get(id)?.name || id)
      .filter(Boolean)
      .slice(0, 2);
    const text = names.length ? names.join(' + ') : '[REDACTED]';
    const rot = (Math.random() * 7 - 3.5).toFixed(1);
    return { label: text.toUpperCase(), rot };
  });

  resultRegion.innerHTML = `
    ${renderAssemblyHead(hopCount)}
    <div class="evidence-wall" aria-label="Evidence wall">
      <svg class="string-layer" xmlns="http://www.w3.org/2000/svg" id="string-layer">
        <defs>
          <filter id="stringShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="1.2" />
            <feOffset dx="1" dy="3" result="off" />
            <feComponentTransfer><feFuncA type="linear" slope="0.55"/></feComponentTransfer>
            <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>
      </svg>
      <div id="via-tag-layer"></div>
      ${decor}
      <div class="evidence-grid">
        ${cards}
      </div>
    </div>
    ${renderChainFooter()}
  `;

  attachFooterHandlers();
  state.lastDrawn = { viaLabels };

  // Wait for fonts to settle before measuring thumbtack positions.
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => requestAnimationFrame(() => drawStrings(viaLabels)));
  } else {
    requestAnimationFrame(() => drawStrings(viaLabels));
  }

  scrollToResult();
}

function renderCorkDecor(eventCount) {
  // Deterministic positions seeded from event count so re-rolls stay stable.
  return `
    <span class="pinhole" style="top: 64px; left: 12%;"></span>
    <span class="pinhole" style="top: 26%; right: 7%;"></span>
    <span class="pinhole" style="top: 48%; left: 4%;"></span>
    <span class="pinhole" style="top: 62%; right: 12%;"></span>
    <span class="pinhole" style="top: 78%; left: 15%;"></span>
    <span class="pinhole" style="top: 88%; right: 6%;"></span>
    <span class="coffee-ring" style="top: 38%; right: 16%; --rot: -12deg;"></span>
    <span class="coffee-ring" style="top: 72%; left: 8%; --rot: 8deg; width: 80px; height: 80px;"></span>
  `;
}

// ── SVG string routing ──────────────────────────────────────────────
function drawStrings(viaLabels) {
  const wall = resultRegion.querySelector('.evidence-wall');
  const svg = resultRegion.querySelector('.string-layer');
  const tagLayer = resultRegion.querySelector('#via-tag-layer');
  if (!wall || !svg || !tagLayer) return;

  const cards = Array.from(resultRegion.querySelectorAll('.pin-card'));
  if (cards.length < 2) return;

  // Set SVG width/height attributes (NOT CSS) — without these, SVGs with
  // only width:100% CSS collapse to ~300x150 intrinsic and the strings
  // render in the wrong coordinate space.
  const w = wall.clientWidth;
  const h = wall.clientHeight;
  svg.setAttribute('width', String(w));
  svg.setAttribute('height', String(h));
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);

  // Wipe old paths + tags but preserve <defs>.
  Array.from(svg.querySelectorAll('path.string')).forEach((p) => p.remove());
  tagLayer.innerHTML = '';

  const wallRect = wall.getBoundingClientRect();

  function tackCenter(card, which) {
    const tack = card.querySelector(which === 'top' ? '.thumbtack:not(.bottom)' : '.thumbtack.bottom');
    if (!tack) return null;
    const r = tack.getBoundingClientRect();
    return {
      x: r.left + r.width / 2 - wallRect.left,
      y: r.top + r.height / 2 - wallRect.top,
    };
  }

  for (let i = 0; i < cards.length - 1; i++) {
    const exit = tackCenter(cards[i], 'bottom');
    const enter = tackCenter(cards[i + 1], 'top');
    if (!exit || !enter) continue;

    // Bezier control points: drop the string into a slack curve below the
    // midpoint. Slack scales with horizontal distance so adjacent-column
    // hops droop more, opposite-column hops hang naturally between.
    const dx = enter.x - exit.x;
    const dy = enter.y - exit.y;
    const slack = Math.max(60, Math.abs(dy) * 0.35 + Math.abs(dx) * 0.18);
    const c1x = exit.x + dx * 0.25;
    const c1y = exit.y + slack;
    const c2x = exit.x + dx * 0.75;
    const c2y = enter.y + slack;
    const d = `M ${exit.x} ${exit.y} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${enter.x} ${enter.y}`;

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('class', 'string');
    path.setAttribute('d', d);
    svg.appendChild(path);

    const length = path.getTotalLength();
    path.style.strokeDasharray = String(length);
    path.style.strokeDashoffset = String(length);
    path.style.animationDelay = `${0.4 + i * 0.35}s`;
    requestAnimationFrame(() => path.classList.add('animated'));

    // VIA tag at the deepest sag point of this Bezier.
    const labelData = viaLabels[i];
    if (labelData) {
      let maxY = -Infinity;
      let maxPt = null;
      for (let t = 0.30; t <= 0.70; t += 0.05) {
        const pt = path.getPointAtLength(length * t);
        if (pt.y > maxY) { maxY = pt.y; maxPt = pt; }
      }
      if (maxPt) {
        const tag = document.createElement('div');
        tag.className = 'via-tag';
        tag.style.left = `${maxPt.x}px`;
        tag.style.top = `${maxPt.y + 6}px`;
        tag.style.setProperty('--rot', `${labelData.rot}deg`);
        tag.style.animationDelay = `${1.4 + i * 0.35}s`;
        tag.innerHTML = `<span class="via-label">VIA</span>${escapeHtml(labelData.label)}`;
        tagLayer.appendChild(tag);
      }
    }
  }
}

let resizeTimer = null;
window.addEventListener('resize', () => {
  if (!state.lastDrawn) return;
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => drawStrings(state.lastDrawn.viaLabels), 120);
});

// ── Self-loop ───────────────────────────────────────────────────────
function renderSelfLoopChain(evtId) {
  const evt = state.eventById.get(evtId);
  if (!evt) {
    renderError('ARCHIVE ENTRY NOT FOUND: ' + evtId, '', { includeHomeLink: true });
    return;
  }
  showQueryState(state.selectedFrom, state.selectedTo, 0);
  resultRegion.innerHTML = `
    ${renderAssemblyHead(0)}
    <div class="self-loop-note" style="font-family:'EB Garamond',serif;font-style:italic;font-size:18px;color:var(--ink-soft);text-align:center;padding:24px;border-top:1px dashed var(--rule);border-bottom:1px dashed var(--rule);margin:24px 0;">
      THE FILE REFERS TO ITSELF.
    </div>
    <div class="evidence-wall" aria-label="Evidence wall">
      <div class="evidence-grid">
        ${renderPinCard({ evt, nodeIndex: 1, termTape: null, rotation: '-1.2deg', bridgeEntities: new Set(), delay: 0.1 })}
      </div>
    </div>
    ${renderChainFooter()}
  `;
  attachFooterHandlers();
  scrollToResult();
}

function scrollToResult() {
  const target = document.getElementById('chain') || resultRegion;
  if (target && target.scrollIntoView) {
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

function resetSearch() {
  state.selectedFrom = null;
  state.selectedTo = null;
  state.currentPaths = [];
  state.seed = 0;
  state.lastDrawn = null;
  fromInput.value = '';
  toInput.value = '';
  closeDropdown(fromDropdown);
  closeDropdown(toDropdown);
  history.replaceState({}, '', HOME_PATH);
  showEmptyState();
}

// ── Search + chain ──────────────────────────────────────────────────
function eventIdsForEntity(entityId) {
  return state.data.events
    .filter((ev) => (ev.entities || []).includes(entityId))
    .map((ev) => ev.id);
}

function findAndRenderChain(fromSel, toSel) {
  if (!fromSel || !toSel) return;

  // WITHHELD short-circuit.
  if (fromSel.kind === 'withheld' || toSel.kind === 'withheld') {
    state.currentPaths = [];
    state.seed = 0;
    renderWithheldDocument(fromSel, toSel);
    updateShareUrl(fromSel, toSel);
    return;
  }

  // Self-loop.
  if (fromSel.id === toSel.id && fromSel.kind === toSel.kind) {
    if (fromSel.kind === 'event') {
      renderSelfLoopChain(fromSel.id);
    } else {
      const events = eventIdsForEntity(fromSel.id);
      if (events.length) renderSelfLoopChain(events[0]);
      else renderError('THE FILE REFERS TO ITSELF.', '', { includeHomeLink: false });
    }
    return;
  }

  setSearchingUi(true);

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
    if (state.seed < 0 || state.seed >= stripped.length) {
      state.seed = ((state.seed % stripped.length) + stripped.length) % stripped.length;
    }
    const chosen = stripped[state.seed];

    renderChain({ events: chosen.events, edges: chosen.edges });
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
  setHeaderChrome();

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

    let fuseIndex = null;
    if (indexPayload && indexPayload.fuse_version === Fuse.version) {
      try { fuseIndex = Fuse.parseIndex(indexPayload.index); }
      catch (err) { console.warn('[connect] Fuse.parseIndex failed, rebuilding:', err); }
    } else {
      console.warn(`[connect] Fuse version mismatch (build=${indexPayload?.fuse_version}, runtime=${Fuse.version}). Rebuilding.`);
    }

    const keys = (indexPayload && indexPayload.keys) || [
      { name: 'label', weight: 0.7 },
      { name: 'aliases', weight: 0.25 },
      { name: 'id', weight: 0.05 },
    ];

    state.fuse = new Fuse(autocomplete, { keys, threshold: 0.4, includeScore: false }, fuseIndex);

    const { createGraph } = await import('./graph.js');
    state.graph = createGraph(adjacency);

    if (archiveUpdated && data.last_ingest_at) {
      archiveUpdated.textContent = `ARCHIVE LAST UPDATED ${formatUpdateTimestamp(data.last_ingest_at)}`;
    }

    setLoadingUi(false);
    showEmptyState();

    attachInputHandlers(fromInput, fromDropdown, (sel) => { state.selectedFrom = sel; });
    attachInputHandlers(toInput, toDropdown, (sel) => { state.selectedTo = sel; });

    findButton.addEventListener('click', () => {
      if (state.loading || state.searching) return;
      if (!state.selectedFrom && fromInput.value.trim()) {
        const top = state.fuse.search(fromInput.value.trim(), { limit: 1 })[0];
        if (top) state.selectedFrom = { id: top.item.id, kind: top.item.kind };
      }
      if (!state.selectedTo && toInput.value.trim()) {
        const top = state.fuse.search(toInput.value.trim(), { limit: 1 })[0];
        if (top) state.selectedTo = { id: top.item.id, kind: top.item.kind };
      }
      if (!state.selectedFrom) { fromInput.focus(); return; }
      if (!state.selectedTo) { toInput.focus(); return; }
      state.seed = 0;
      findAndRenderChain(state.selectedFrom, state.selectedTo);
    });

    [fromInput, toInput].forEach((input) => {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !state.loading && !state.searching) {
          e.preventDefault();
          findButton.click();
        }
      });
    });

    if (traceAnotherTop) {
      traceAnotherTop.addEventListener('click', (e) => {
        e.preventDefault();
        resetSearch();
        fromInput.focus();
      });
    }

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
