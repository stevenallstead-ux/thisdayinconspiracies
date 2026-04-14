// js/today.js — logic for /today/index.html (the daily-entry archive page).
// Moved from the original script.js when the homepage flipped to Connect-Any-Two.

import {
  pad,
  formatFullDate,
  loadData,
  renderEventCard,
  renderMonthEvent,
  renderEmptyState,
} from './shared.js';

function getToday() {
  return new Date();
}

async function init() {
  const today = getToday();
  const todayKey = `${pad(today.getMonth() + 1)}-${pad(today.getDate())}`;
  const monthKey = pad(today.getMonth() + 1);

  document.getElementById('current-date').textContent = formatFullDate(today).toUpperCase();
  const yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = today.getFullYear();

  let data;
  try {
    data = await loadData();
  } catch (err) {
    document.getElementById('today-events').innerHTML = renderEmptyState();
    return;
  }

  const todayEvents = data.events
    .filter((e) => e.date === todayKey)
    .sort((a, b) => b.year - a.year);

  const monthEvents = data.events
    .filter((e) => e.date.startsWith(monthKey) && e.date !== todayKey)
    .sort((a, b) => a.date.localeCompare(b.date));

  const todayContainer = document.getElementById('today-events');
  todayContainer.innerHTML = todayEvents.length
    ? todayEvents.map((evt) => renderEventCard({ evt })).join('')
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
