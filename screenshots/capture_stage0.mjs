import { chromium } from 'playwright';
import { join } from 'path';
import { pathToFileURL } from 'url';

const out = 'D:/量潮科技/课题申请-product-requirement-loop/screenshots/stage0';
const root = 'D:/量潮科技/课题申请-product-requirement-loop';

const pages = [
  ['01-review-page.png', pathToFileURL(join(root, 'project/trials/case-01/review.html')).href],
  ['02-review-keyword.png', pathToFileURL(join(root, 'project/trials/case-01/review.html')).href, 'kw'],
  ['03-review-revise.png', pathToFileURL(join(root, 'project/trials/case-01/review.html')).href, 'revise'],
  ['04-source-md.png', pathToFileURL(join(root, 'project/trials/case-01/input/SOURCE.md')).href],
  ['05-checklist.png', pathToFileURL(join(root, '阶段0快速验收清单.md')).href],
  ['06-preview-html.png', pathToFileURL(join(root, '图文预览.html')).href],
];

import { mkdirSync } from 'fs';
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });

for (const [name, url, mode] of pages) {
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(1500);
  if (mode === 'kw') {
    await page.click('button.kw[data-kw="捕捉用户故事"]');
    await page.waitForTimeout(500);
  }
  if (mode === 'revise') {
    await page.click('button.bad[data-code="编造"]');
    await page.waitForTimeout(500);
  }
  await page.screenshot({ path: join(out, name), fullPage: mode === 'revise' });
  console.log('ok', name);
  await page.close();
}

await browser.close();
