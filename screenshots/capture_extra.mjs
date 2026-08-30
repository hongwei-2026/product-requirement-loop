import { chromium } from 'playwright';
import { join } from 'path';

const out = 'D:/量潮科技/课题申请-product-requirement-loop/screenshots';
const pages = [
  ['08-implementation-py.png', 'https://github.com/quanttide/quanttide-profile-of-agent-engineering/blob/main/default/loops/devops-code/implementation.py'],
  ['09-loops-trials-section.png', 'https://github.com/quanttide/quanttide-profile-of-agent-engineering/blob/main/default/loops/README.md'],
  ['10-product-cloud-stories.png', 'https://github.com/quanttide/quanttide-profile-of-product-development/blob/main/qtcloud-product/requirement.md'],
];

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
for (const [name, url] of pages) {
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(2000);
  if (name.includes('trials')) {
    await page.evaluate(() => {
      const el = [...document.querySelectorAll('h2, h3, strong, b')].find(e => e.textContent?.includes('验证') || e.textContent?.includes('trials'));
      el?.scrollIntoView({ block: 'start' });
    });
    await page.waitForTimeout(800);
  }
  if (name.includes('stories')) {
    await page.evaluate(() => {
      const el = [...document.querySelectorAll('h3, h2')].find(e => e.textContent?.includes('捕捉用户故事'));
      el?.scrollIntoView({ block: 'start' });
    });
    await page.waitForTimeout(800);
  }
  await page.screenshot({ path: join(out, name) });
  console.log('ok', name);
  await page.close();
}
await browser.close();
