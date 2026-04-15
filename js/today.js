// js/today.js — logic for /today/index.html (the dossier daily-entry page).

import {
  pad,
  formatFullDate,
  loadData,
  renderFileCard,
  renderTimelineItem,
  renderEmptyState,
  MONTHS,
  MONTHS_SHORT,
} from './shared.js';

function getToday() {
  return new Date();
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

async function init() {
  const today = getToday();
  const todayKey = `${pad(today.getMonth() + 1)}-${pad(today.getDate())}`;
  const monthKey = pad(today.getMonth() + 1);
  const monthName = MONTHS[today.getMonth()];
  const monthShort = MONTHS_SHORT[today.getMonth()];

  // Header chrome
  setText('ref-date', `${monthShort}${pad(today.getDate())}`);
  setText('stamp-date', `${pad(today.getMonth() + 1)} · ${pad(today.getDate())} · ${today.getFullYear()}`);
  setText('year', today.getFullYear());
  setText('footer-end', `${pad(today.getMonth() + 1)}${pad(today.getDate())} / END OF TRANSMISSION`);
  setText('banner-issue', `Issue ${pad(today.getMonth() + 1)}${pad(today.getDate())}`);
  setText('banner-issue', `Issue ${pad(today.getMonth() + 1)}${pad(today.getDate())}`);

  // big-date with stylized slash
  const bigDateEl = document.getElementById('banner-big-date');
  if (bigDateEl) {
    bigDateEl.innerHTML = `${pad(today.getMonth() + 1)}<span class="slash">/</span>${pad(today.getDate())}`;
  }
  setText('banner-file-date', `${['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][today.getDay()]} · ${monthName} ${today.getDate()} · ${today.getFullYear()}`);
  setText('month-subhead', `${monthName} · Volume IV`);

  let data;
  try {
    data = await loadData();
  } catch (err) {
    document.getElementById('today-events').innerHTML = renderEmptyState();
    setText('banner-ingest', '— · —');
    return;
  }

  // Last ingest timestamp
  if (data.last_ingest_at) {
    const d = new Date(data.last_ingest_at);
    const hh = String(d.getUTCHours()).padStart(2, '0');
    const mm = String(d.getUTCMinutes()).padStart(2, '0');
    const totalToday = data.events.filter((e) => e.date === todayKey).length;
    setText('banner-ingest', `${hh}:${mm}Z · ${totalToday} ${totalToday === 1 ? 'entry' : 'entries'}`);
  }

  // Today's events: highest-year first; first one is featured.
  const todayEvents = data.events
    .filter((e) => e.date === todayKey)
    .sort((a, b) => b.year - a.year);

  const monthEvents = data.events
    .filter((e) => e.date.startsWith(monthKey))
    .sort((a, b) => a.date.localeCompare(b.date) || a.year - b.year);

  // Today section
  const todayContainer = document.getElementById('today-events');
  if (todayEvents.length) {
    todayContainer.innerHTML = todayEvents.map((evt, i) =>
      renderFileCard({ evt, featured: i === 0, today })
    ).join('');
    setText('today-count', `${pad(todayEvents.length)} · ${pad(todayEvents.length)} FILES OPENED`);
  } else {
    todayContainer.innerHTML = renderEmptyState();
    setText('today-count', '00 · 00 FILES OPENED');
  }

  // Month timeline
  const monthContainer = document.getElementById('month-events');
  if (monthEvents.length) {
    monthContainer.innerHTML = monthEvents.map((evt) =>
      renderTimelineItem(evt, evt.date === todayKey)
    ).join('');
  } else {
    document.getElementById('month-section').style.display = 'none';
  }

  // Stagger redaction reveal on hover within a card.
  document.querySelectorAll('.file-card').forEach((card) => {
    card.addEventListener('mouseenter', () => {
      card.querySelectorAll('.redact').forEach((r, i) => {
        setTimeout(() => r.classList.add('peek'), i * 120);
      });
    });
    card.addEventListener('mouseleave', () => {
      card.querySelectorAll('.redact').forEach((r) => r.classList.remove('peek'));
    });
  });

  // Subtle stamp parallax on pointer-fine devices.
  const stamp = document.querySelector('.stamp');
  if (stamp && window.matchMedia('(pointer:fine)').matches &&
      !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.addEventListener('mousemove', (e) => {
      const x = (e.clientX / window.innerWidth - 0.5) * 6;
      const y = (e.clientY / window.innerHeight - 0.5) * 6;
      stamp.style.transform = `rotate(-7deg) translate(${x}px, ${y}px)`;
    });
  }
}

init();
