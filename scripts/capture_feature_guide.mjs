/**
 * Capture every major product screen for the feature guide.
 * Requires server at http://127.0.0.1:8765/
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const OUT = join(ROOT, 'docs', '交付', 'assets', 'guide');
const BASE = 'http://127.0.0.1:8765';

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  locale: 'zh-CN',
});
const page = await ctx.newPage();

async function shot(name) {
  const path = join(OUT, name);
  await page.waitForTimeout(600);
  await page.screenshot({ path, fullPage: false });
  console.log('ok', name);
}

// 1) Login
await page.goto(`${BASE}/login.html`, { waitUntil: 'networkidle', timeout: 60000 });
await shot('01-login.png');

await page.getByPlaceholder('例如 demo').fill('demo');
await page.getByPlaceholder('至少 6 位').fill('demo1234');
await shot('02-login-filled.png');
await page.getByRole('button', { name: '登录进入' }).click();
await page.waitForURL(/\/(app\.html)?(\?.*)?$/, { timeout: 30000 }).catch(() => {});
await page.waitForTimeout(1500);
if (!page.url().includes('app.html') && !page.url().match(/8765\/?$/)) {
  await page.goto(`${BASE}/`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
}
await shot('03-workbench.png');

async function openNav(id, file) {
  await page.locator(`#${id}`).click();
  await page.waitForTimeout(900);
  await shot(file);
}

await openNav('nav-journals', '04-journals.png');

// journal filters if present
const usage = page.locator('#jp-filter-usage');
if (await usage.count()) {
  await usage.selectOption({ label: /正式全文|formal/i }).catch(() => {});
  await page.waitForTimeout(500);
  await shot('05-journals-filter.png');
}

await openNav('nav-fetch', '06-fetch.png');
await openNav('nav-queue', '07-queue.png');
await openNav('nav-audit', '08-audit.png');

// open first audit detail if any
const auditBtn = page.locator('.btn-audit-detail').first();
if (await auditBtn.count()) {
  await auditBtn.click();
  await page.waitForTimeout(800);
  await shot('09-audit-detail.png');
  const close = page.locator('#btn-close-audit-detail, .modal.show .btn').filter({ hasText: /关闭|取消/ }).first();
  if (await close.count()) await close.click().catch(() => {});
  await page.waitForTimeout(400);
}

await openNav('nav-registry', '10-registry.png');
const regDetail = page.locator('.btn-reg-detail').first();
if (await regDetail.count()) {
  await regDetail.click();
  await page.waitForTimeout(900);
  await shot('11-registry-detail.png');
  const closeR = page.locator('#btn-close-registry-detail');
  if (await closeR.count()) await closeR.click().catch(() => {});
}

await openNav('nav-manual', '12-manual.png');
await openNav('nav-work', '13-workbench-back.png');

// Try open journal preview from library without force reopen
await page.locator('#nav-journals').click();
await page.waitForTimeout(700);
const card = page.locator('.j-card').first();
if (await card.count()) {
  await card.click();
  await page.waitForTimeout(900);
  await shot('14-journal-preview.png');
  const closeP = page.locator('#btn-close-preview, #btn-close-jp-preview, .modal.show button').filter({ hasText: /关闭/ }).first();
  if (await closeP.count()) await closeP.click().catch(() => {});
}

// Step pipeline strip / action area
await page.locator('#nav-work').click();
await page.waitForTimeout(600);
await shot('15-workbench-actions.png');

await browser.close();
console.log('done ->', OUT);
