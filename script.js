const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

function pad(n) { return String(n).padStart(2, '0'); }

function formatFullDate(d) {
  return `${MONTHS[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderEventCard(evt) {
  const theories = (evt.theories || []).map(t =>
    `<li>${escapeHtml(t)}</li>`
  ).join('');

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
    </article>
  `;
}

function renderMonthEvent(evt) {
  const [, day] = evt.date.split('-');
  return `
    <div class="month-event">
      <span class="month-event-date">${escapeHtml(pad(Number(day)))} · ${escapeHtml(String(evt.year))}</span>
      <span class="month-event-title">${escapeHtml(evt.title)}</span>
      <span class="month-event-category">${escapeHtml(evt.category)}</span>
    </div>
  `;
}

function renderEmptyState() {
  return `
    <div class="empty-state">
      <p>No declassified files logged for this date.</p>
      <p style="margin-top: 0.75rem;">The archive is silent &mdash; or the records have been <span class="redact">████████████</span>.</p>
    </div>
  `;
}

async function loadData() {
  const res = await fetch('data/data.json');
  if (!res.ok) throw new Error('Failed to load archive.');
  return res.json();
}

function getToday() {
  return new Date();
}

async function init() {
  const today = getToday();
  const todayKey = `${pad(today.getMonth() + 1)}-${pad(today.getDate())}`;
  const monthKey = pad(today.getMonth() + 1);

  document.getElementById('current-date').textContent = formatFullDate(today).toUpperCase();
  document.getElementById('year').textContent = today.getFullYear();

  let data;
  try {
    data = await loadData();
  } catch (err) {
    document.getElementById('today-events').innerHTML = renderEmptyState();
    return;
  }

  const todayEvents = data.events
    .filter(e => e.date === todayKey)
    .sort((a, b) => b.year - a.year);

  const monthEvents = data.events
    .filter(e => e.date.startsWith(monthKey) && e.date !== todayKey)
    .sort((a, b) => a.date.localeCompare(b.date));

  const todayContainer = document.getElementById('today-events');
  todayContainer.innerHTML = todayEvents.length
    ? todayEvents.map(renderEventCard).join('')
    : renderEmptyState();

  const monthContainer = document.getElementById('month-events');
  const monthSection = document.getElementById('month-section');
  if (monthEvents.length) {
    monthContainer.innerHTML = monthEvents.map(renderMonthEvent).join('');
  } else {
    monthSection.style.display = 'none';
  }
}

init();
