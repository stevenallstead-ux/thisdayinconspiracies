// Shared rendering + formatting helpers used by today.js and connect.js.
// No module-level side effects; import-safe.

export const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

export const MONTHS_SHORT = [
  'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
  'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC',
];

export function pad(n) {
  return String(n).padStart(2, '0');
}

export function formatFullDate(d) {
  return `${MONTHS[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
}

export function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Parse `*word word*` → italic accent in oxblood. Used in titles, year
// displays, section heads, person names.
export function parseAccent(text) {
  if (!text) return '';
  const escaped = escapeHtml(text);
  return escaped.replace(/\*([^*]+)\*/g, '<em>$1</em>');
}

// Parse `{{redact:hidden text}}` → black bar that reveals on hover.
// Text underneath stays in DOM so screen readers announce it; the title
// attribute provides sighted-user tooltip equivalence.
export function parseRedactions(text) {
  if (!text) return '';
  const escaped = escapeHtml(text);
  return escaped.replace(/\{\{redact:([^}]+)\}\}/g, (_, content) => {
    const safe = content.replace(/"/g, '&quot;');
    return `<span class="redact" title="${safe}">${content}</span>`;
  });
}

// ── Procedural metadata derivation (no data.json edits needed) ──

// case_no example: "CON-1865-0414-FORD" — derived from year + date + slug head.
export function deriveCaseNo(evt) {
  const date = (evt.date || '').replace('-', '');
  const slugHead = (evt.id || evt.title || '')
    .replace(/^-?\d+-/, '')
    .split('-')
    .slice(0, 1)
    .join('')
    .slice(0, 8)
    .toUpperCase();
  return `CON-${evt.year}-${date}-${slugHead || 'X'}`;
}

// timestamp_location example: "APR 14 · 1865"
export function deriveTimestamp(evt) {
  const [mm, dd] = (evt.date || '').split('-').map((n) => parseInt(n, 10));
  if (!mm || !dd) return String(evt.year || '');
  return `${MONTHS_SHORT[mm - 1]} ${pad(dd)} · ${evt.year}`;
}

export function deriveYearsAgo(evt, today = new Date()) {
  const currentYear = today.getFullYear();
  return Math.max(0, currentYear - (evt.year || currentYear));
}

// Year display markup: italicize last two digits in oxblood. Years before
// 1000 don't get the split treatment — they're rendered whole.
export function renderYearAccent(year) {
  const y = String(year);
  if (y.length !== 4) return escapeHtml(y);
  return `${escapeHtml(y.slice(0, 2))}<em>${escapeHtml(y.slice(2))}</em>`;
}

// Category className helper — lowercase, fallback to 'unexplained'.
export function categoryClass(category) {
  return (category || 'unexplained').toLowerCase().replace(/[^a-z]/g, '');
}

function formatDateShort(dateMmDd) {
  const [mm, dd] = (dateMmDd || '').split('-').map((n) => parseInt(n, 10));
  if (!mm || !dd) return '';
  return `${MONTHS_SHORT[mm - 1]} ${pad(dd)}`;
}

// Display-friendly entity name from a slug id.
function entityDisplay(id) {
  return id.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── File card render (today page) ──
export function renderFileCard({ evt, featured = false, today = new Date() }) {
  const caseNo = deriveCaseNo(evt);
  const stamp = deriveTimestamp(evt);
  const yearsAgo = deriveYearsAgo(evt, today);
  const cat = categoryClass(evt.category);
  const yearMarkup = renderYearAccent(evt.year);

  const theoriesHtml = (evt.theories || [])
    .map((t) => `<li>${parseAccent(t)}</li>`)
    .join('');

  const entitiesHtml = (evt.entities || []).slice(0, 8)
    .map((id) => `<span class="chip">${escapeHtml(entityDisplay(id))}</span>`)
    .join('');

  const dateShort = formatDateShort(evt.date);

  return `
    <article class="file-card${featured ? ' featured' : ''}">
      <div class="file-strip">
        <span class="case-no">CASE № ${escapeHtml(caseNo)}</span>
        <span>${escapeHtml(stamp)}</span>
        <span class="category ${escapeHtml(cat)}">${escapeHtml(evt.category)}</span>
      </div>

      <div class="year-display">
        <div class="year">${yearMarkup}</div>
        <div class="date-abs">${yearsAgo} years ago<br/>${escapeHtml(dateShort)}</div>
      </div>

      <h3>${parseAccent(evt.title)}</h3>

      <p class="summary">${parseRedactions(evt.summary)}</p>

      ${theoriesHtml ? `<div class="theories"><ul>${theoriesHtml}</ul></div>` : ''}

      ${entitiesHtml ? `<div class="entities">${entitiesHtml}</div>` : ''}
    </article>
  `;
}

// ── Pin card (connect page evidence wall) ──
// nodeIndex is 1-based. termTape is 'origin' | 'terminus' | null.
// rotation is the per-card --rot var (e.g. -2.5deg).
// bridgeEntities is a Set of entity ids that should get .bridge styling.
// delay is animation-delay seconds for the staggered reveal.
export function renderPinCard({
  evt,
  nodeIndex,
  termTape = null,
  rotation = '0deg',
  bridgeEntities = new Set(),
  delay = 0,
}) {
  const caseNo = deriveCaseNo(evt);
  const stamp = deriveTimestamp(evt);
  const yearsAgo = deriveYearsAgo(evt);
  const cat = categoryClass(evt.category);
  const yearMarkup = renderYearAccent(evt.year);

  const entitiesHtml = (evt.entities || []).slice(0, 6)
    .map((id) => {
      const display = entityDisplay(id);
      const isBridge = bridgeEntities.has(id);
      return `<span class="chip${isBridge ? ' bridge' : ''}">${escapeHtml(display)}</span>`;
    }).join('');

  const tapeHtml = termTape === 'origin'
    ? '<span class="term-tape">From</span>'
    : termTape === 'terminus'
      ? '<span class="term-tape end">To</span>'
      : '';

  const summaryShort = (evt.summary || '').slice(0, 280);
  const truncated = (evt.summary || '').length > 280 ? '…' : '';

  return `
    <article class="pin-card" style="--rot: ${rotation}; --delay: ${delay}s;">
      <span class="thumbtack" aria-hidden="true"></span>
      <span class="thumbtack bottom" aria-hidden="true"></span>
      <span class="tape tl" aria-hidden="true"></span>
      <span class="tape br" aria-hidden="true"></span>
      ${tapeHtml}

      <span class="node-num">№ ${nodeIndex}</span>

      <div class="file-strip">
        <span class="case-no">${escapeHtml(caseNo)}</span>
        <span class="category ${escapeHtml(cat)}">${escapeHtml(evt.category)}</span>
      </div>

      <div class="year-row">
        <div class="year">${yearMarkup}</div>
        <div class="abs">${yearsAgo} yrs ago<br/>${escapeHtml(stamp)}</div>
      </div>

      <h3>${parseAccent(evt.title)}</h3>

      <p class="summary">${parseRedactions(summaryShort)}${truncated}</p>

      ${entitiesHtml ? `<div class="entities">${entitiesHtml}</div>` : ''}
    </article>
  `;
}

// Backwards-compatible alias — older callers use renderEventCard.
export function renderEventCard({ evt }) {
  return renderFileCard({ evt, featured: false });
}

// Month timeline list item (today page right column).
export function renderTimelineItem(evt, isToday = false) {
  return `
    <li${isToday ? ' class="today"' : ''}>
      <span class="date"><span class="yr">${escapeHtml(String(evt.year))}</span> · ${escapeHtml(formatDateShort(evt.date))}${isToday ? ' — <strong>TODAY</strong>' : ''}</span>
      <span class="t-title">${parseAccent(evt.title)}</span>
    </li>
  `;
}

// Backwards-compat — older callers use renderMonthEvent.
export function renderMonthEvent(evt) {
  return renderTimelineItem(evt, false);
}

export function renderEmptyState() {
  return `
    <div class="file-card">
      <div class="file-strip">
        <span class="case-no">FILE EMPTY</span>
        <span>No record on this date</span>
      </div>
      <h3>The archive is silent on this date.</h3>
      <p class="summary" style="font-style:italic;color:var(--ink-fade);">No declassified records have been logged for today's calendar entry. Either nothing surfaces here yet, or the records have been <span class="redact" title="REDACTED">withheld</span>.</p>
    </div>
  `;
}

// Absolute paths so the same module works from `/` and `/today/` without
// relative-path gymnastics.
export async function loadData(path = '/data/data.json') {
  const res = await fetch(path);
  if (!res.ok) throw new Error('Failed to load archive.');
  return res.json();
}

export async function loadJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return res.json();
}
