// Shared rendering + formatting helpers used by today.js and connect.js.
// No module-level side effects; import-safe.

export const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
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

// Render an event card. Pass `neighbors` (array of {id, title, shared_entity_names})
// to render a Related Files footer; omit for chain results.
export function renderEventCard({ evt, neighbors }) {
  const theories = (evt.theories || [])
    .map((t) => `<li>${escapeHtml(t)}</li>`)
    .join('');

  const footer = Array.isArray(neighbors) && neighbors.length
    ? `
      <div class="related-files">
        <span class="related-files-label">Related Files</span>
        <ul>${neighbors.map((n) => `
          <li>
            <span class="related-files-title">${escapeHtml(n.title)}</span>
            ${n.shared_entity_names && n.shared_entity_names.length
              ? `<span class="related-files-via">via ${escapeHtml(n.shared_entity_names.join(', '))}</span>`
              : ''}
          </li>`).join('')}</ul>
      </div>`
    : '';

  return `
    <article class="event-card">
      <div class="event-meta">
        <span class="year">${escapeHtml(String(evt.year))}</span>
        <span class="category">${escapeHtml(evt.category)}</span>
      </div>
      <h3 class="event-title">${escapeHtml(evt.title)}</h3>
      <p class="event-summary">${escapeHtml(evt.summary)}</p>
      ${theories ? `
        <div class="theories">
          <span class="theories-label">Circulating Theories</span>
          <ul>${theories}</ul>
        </div>
      ` : ''}
      ${footer}
    </article>
  `;
}

export function renderMonthEvent(evt) {
  const [, day] = evt.date.split('-');
  return `
    <div class="month-event">
      <span class="month-event-date">${escapeHtml(pad(Number(day)))} · ${escapeHtml(String(evt.year))}</span>
      <span class="month-event-title">${escapeHtml(evt.title)}</span>
      <span class="month-event-category">${escapeHtml(evt.category)}</span>
    </div>
  `;
}

export function renderEmptyState() {
  return `
    <div class="empty-state">
      <p>No declassified files logged for this date.</p>
      <p style="margin-top: 0.75rem;">The archive is silent &mdash; or the records have been <span class="redact">████████████</span>.</p>
    </div>
  `;
}

// Absolute paths so the same module works from `/` and `/today/` without
// relative-path gymnastics. Cloudflare Pages + local `python -m http.server`
// both resolve `/data/data.json` correctly.
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
