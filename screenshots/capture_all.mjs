import { chromium } from 'playwright';
import { join } from 'path';

const out = 'D:/量潮科技/课题申请-product-requirement-loop/screenshots';
const pages = [
  ['01-agent-engineering-repo.png', 'https://github.com/quanttide/quanttide-profile-of-agent-engineering'],
  ['02-loops-readme.png', 'https://github.com/quanttide/quanttide-profile-of-agent-engineering/blob/main/default/loops/README.md'],
  ['03-product-requirement-index.png', 'https://github.com/quanttide/quanttide-profile-of-agent-engineering/blob/main/default/loops/product-requirement/index.md'],
  ['04-devops-code-spec.png', 'https://github.com/quanttide/quanttide-profile-of-agent-engineering/blob/main/default/loops/devops-code/specification.yaml'],
  ['05-product-cloud-requirement.png', 'https://github.com/quanttide/quanttide-profile-of-product-development/blob/main/qtcloud-product/requirement.md'],
  ['06-docs-center.png', 'https://docs.quanttide.com'],
  ['07-docs-intention.png', 'https://docs.quanttide.com'],
  ['08-implementation-py.png', 'https://github.com/quanttide/quanttide-profile-of-agent-engineering/blob/main/default/loops/devops-code/implementation.py'],
  ['09-loops-trials-section.png', 'https://github.com/quanttide/quanttide-profile-of-agent-engineering/blob/main/default/loops/README.md'],
  ['10-product-cloud-stories.png', 'https://github.com/quanttide/quanttide-profile-of-product-development/blob/main/qtcloud-product/requirement.md'],
  ['11-journal-asset.png', 'https://github.com/quanttide/quanttide/blob/main/README.md'],
  ['12-requirement-json.png', 'https://github.com/quanttide/quanttide-profile-of-product-development/blob/main/qtcloud-product/requirement.json'],
  ['13-product-cloud-capture.png', 'https://github.com/quanttide/quanttide-profile-of-product-development/blob/main/qtcloud-product/requirement.md'],
  ['14-loops-from-journal.png', 'https://github.com/quanttide/quanttide-profile-of-agent-engineering/blob/main/default/loops/README.md'],
];

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });

for (const [name, url] of pages) {
  const page = await ctx.newPage();
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(2500);
    if (name.includes('trials')) {
      await page.evaluate(() => {
        const el = [...document.querySelectorAll('h2, h3, strong, b')].find(
          (e) => e.textContent?.includes('验证') || e.textContent?.includes('trials')
        );
        el?.scrollIntoView({ block: 'start' });
      });
    } else if (name.includes('stories') || name.includes('capture') || name === '05-product-cloud-requirement.png') {
      await page.evaluate(() => {
        const el = [...document.querySelectorAll('h3, h2')].find((e) =>
          e.textContent?.includes('捕捉用户故事')
        );
        el?.scrollIntoView({ block: 'start' });
      });
    } else if (name.includes('journal-asset')) {
      await page.evaluate(() => {
        const el = [...document.querySelectorAll('*')].find((e) =>
          e.textContent?.includes('quanttide-journal')
        );
        el?.scrollIntoView({ block: 'center' });
      });
    } else if (name.includes('from-journal')) {
      await page.evaluate(() => {
        const el = [...document.querySelectorAll('p, li')].find((e) =>
          e.textContent?.includes('实践日志')
        );
        el?.scrollIntoView({ block: 'start' });
      });
    }
    await page.waitForTimeout(800);
    await page.screenshot({ path: join(out, name) });
    console.log('ok', name);
  } catch (e) {
    console.error('fail', name, e.message);
  }
  await page.close();
}

await browser.close();
