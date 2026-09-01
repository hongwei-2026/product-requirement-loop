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
const OUT = join(ROOT, 'docs', 'delivery-guide', 'assets');
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
  await page.waitForTimeout(700);
  await page.screenshot({ path, fullPage: false });
  console.log('ok', name);
}

await page.goto(`${BASE}/login.html`, { waitUntil: 'networkidle', timeout: 60000 });
await shot('01-login.png');

await page.locator('#login-user').fill('demo');
await page.locator('#login-pass').fill('demo1234');
await shot('02-login-filled.png');
await page.locator('#btn-login').click();
await page.waitForURL(url => !String(url).includes('login.html'), { timeout: 30000 });
await page.waitForTimeout(1500);
await shot('03-workbench.png');

async function openNav(id, file) {
  await page.locator(`#${id}`).click();
  await page.waitForTimeout(1000);
  await shot(file);
}

await openNav('nav-journals', '04-journals.png');

const product = page.locator('#jp-filter-product');
if (await product.count()) {
  const opts = await product.locator('option').allTextContents();
  const pick = opts.find(t => /产品|qtcloud-product|product/i.test(t));
  if (pick) {
    await product.selectOption({ label: pick }).catch(async () => {
      const val = await product.locator('option').filter({ hasText: pick }).first().getAttribute('value');
      if (val) await product.selectOption(val);
    });
    await page.waitForTimeout(600);
    await shot('05-journals-filter.png');
  }
}

await openNav('nav-fetch', '06-fetch.png');
await openNav('nav-queue', '07-queue.png');
await openNav('nav-audit', '08-audit.png');

const auditBtn = page.locator('.btn-audit-detail').first();
if (await auditBtn.count()) {
  await auditBtn.click();
  await page.waitForTimeout(900);
  await shot('09-audit-detail.png');
  const close = page.locator('#btn-close-audit-detail');
  if (await close.count()) await close.click().catch(() => {});
  else await page.keyboard.press('Escape').catch(() => {});
  await page.waitForTimeout(400);
}

await openNav('nav-registry', '10-registry.png');
const regDetail = page.locator('.btn-reg-detail').first();
if (await regDetail.count()) {
  await regDetail.click();
  await page.waitForTimeout(1000);
  await shot('11-registry-detail.png');
  const closeR = page.locator('#btn-close-registry-detail');
  if (await closeR.count()) await closeR.click().catch(() => {});
}

await openNav('nav-manual', '12-manual.png');

await page.locator('#nav-journals').click();
await page.waitForTimeout(800);
const previewBtn = page.locator('.btn-preview-j, button:has-text("看全文")').first();
if (await previewBtn.count()) {
  await previewBtn.click();
  await page.waitForTimeout(1000);
  await shot('14-journal-preview.png');
  const closeP = page.locator('#btn-close-jp-preview, #btn-close-preview, button:has-text("关闭")').first();
  if (await closeP.count()) await closeP.click().catch(() => {});
} else {
  const card = page.locator('.j-card').first();
  if (await card.count()) {
    await card.click();
    await page.waitForTimeout(1000);
    await shot('14-journal-preview.png');
  }
}

// Use a try excerpt into workbench if idle
await page.locator('#nav-journals').click();
await page.waitForTimeout(600);
const useBtn = page.locator('.btn-use').first();
if (await useBtn.count()) {
  page.once('dialog', async d => { try { await d.accept(); } catch {} });
  await useBtn.click();
  await page.waitForTimeout(1500);
  await page.locator('#nav-work').click().catch(() => {});
  await page.waitForTimeout(800);
  await shot('15-workbench-with-journal.png');
}

await openNav('nav-work', '13-workbench-back.png');

await browser.close();
console.log('done ->', OUT);
