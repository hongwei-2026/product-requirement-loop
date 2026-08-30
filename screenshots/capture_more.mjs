import { chromium } from 'playwright';
import { join } from 'path';

const out = 'D:/量潮科技/课题申请-product-requirement-loop/screenshots';
const pages = [
  ['11-journal-asset.png', 'https://github.com/quanttide/quanttide/blob/main/README.md'],
  ['12-requirement-json.png', 'https://github.com/quanttide/quanttide-profile-of-product-development/blob/main/qtcloud-product/requirement.json'],
  ['13-product-cloud-capture.png', 'https://github.com/quanttide/quanttide-profile-of-product-development/blob/main/qtcloud-product/requirement.md'],
  ['14-loops-from-journal.png', 'https://github.com/quanttide/quanttide-profile-of-agent-engineering/blob/main/default/loops/README.md'],
];

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
for (const [name, url] of pages) {
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(2500);
  if (name.includes('journal')) {
    await page.evaluate(() => {
      const el = [...document.querySelectorAll('*')].find(e => e.textContent?.includes('quanttide-journal'));
      el?.scrollIntoView({ block: 'center' });
    });
    await page.waitForTimeout(800);
  }
  if (name.includes('capture')) {
    await page.evaluate(() => {
      const el = [...document.querySelectorAll('h3')].find(e => e.textContent?.includes('捕捉用户故事'));
      el?.scrollIntoView({ block: 'start' });
    });
    await page.waitForTimeout(800);
  }
  if (name.includes('from-journal')) {
    await page.evaluate(() => {
      const el = [...document.querySelectorAll('p, li')].find(e => e.textContent?.includes('实践日志'));
      el?.scrollIntoView({ block: 'start' });
    });
    await page.waitForTimeout(800);
  }
  await page.screenshot({ path: join(out, name) });
  console.log('ok', name);
  await page.close();
}
await browser.close();
