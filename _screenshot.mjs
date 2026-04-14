import { chromium } from 'playwright';

const url = process.argv[2] || 'http://localhost:8765/';
const out = process.argv[3] || 'site-screenshot.png';

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 1600 } });
const page = await context.newPage();

const errors = [];
page.on('pageerror', e => errors.push('pageerror: ' + e.message));
page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });

await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForSelector('#today-events article, #today-events .empty-state', { timeout: 5000 });

const title = await page.title();
const todayCards = await page.locator('#today-events .event-card').count();
const monthRows = await page.locator('#month-events .month-event').count();
const dateText = await page.locator('#current-date').textContent();

await page.screenshot({ path: out, fullPage: true });
await browser.close();

console.log(JSON.stringify({ title, dateText, todayCards, monthRows, errors }, null, 2));
