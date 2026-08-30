import { createRequire } from 'module';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { writeFileSync } from 'fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(join(__dirname, '../screenshots/package.json'));
const { chromium } = require('playwright');

const root = join(__dirname, '..');
const { pathToFileURL } = await import('url');
const reviewUrl = pathToFileURL(join(root, 'project/trials/case-01/review.html')).href;
const reportPath = join(root, 'stage0-ux-self-test-report.md');

const results = [];

function record(id, name, feature, ok, detail) {
  results.push({ id, name, feature, ok, detail });
  console.log(`[${ok ? 'PASS' : 'FAIL'}] ${id} ${name} — ${detail}`);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

try {
  await page.goto(reviewUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(2000);

  const sourceText = await page.locator('#source-text').innerText();
  record(
    'UX01',
    '左边加载出日志',
    '人打开页不看到空白',
    !sourceText.includes('加载中') && sourceText.includes('捕捉用户故事'),
    sourceText.slice(0, 40).replace(/\n/g, ' ') + '…'
  );

  await page.click('button.kw[data-kw="捕捉用户故事"]');
  await page.waitForTimeout(400);
  const markCount = await page.locator('mark').count();
  record(
    'UX02',
    '点关键词会高亮',
    '不熟文件也能定位',
    markCount > 0,
    `高亮 ${markCount} 处`
  );

  await page.click('button.ok');
  let cmd = await page.inputValue('#cmd');
  record('UX03', '点通过出 ok', '锁定本步指令', cmd === 'ok', `cmd=${cmd}`);

  await page.click('button.bad[data-code="编造"]');
  const builderVisible = await page.locator('#builder').isVisible();
  record(
    'UX04',
    '点编造出现句式区',
    '不会写原因有引导',
    builderVisible,
    'builder 显示'
  );

  await page.click('button.primary');
  cmd = await page.inputValue('#cmd');
  const statusEmpty = (await page.locator('#status').innerText()).includes('请写');
  record(
    'UX05',
    '没填原因不能生成',
    '打叉必须留痕',
    !cmd || cmd === 'ok' || statusEmpty,
    '空原因时未生成 revise 或已提示'
  );

  await page.click('button.template-chip');
  await page.waitForTimeout(200);
  const reason = await page.inputValue('#reason');
  record(
    'UX06',
    '点现成句式会填入',
    '降低写原因门槛',
    reason.length > 5,
    reason.slice(0, 30) + (reason.length > 30 ? '…' : '')
  );

  await page.click('button.primary');
  cmd = await page.inputValue('#cmd');
  record(
    'UX07',
    '填好原因能生成 revise',
    '反馈点可交给 Loop',
    cmd.startsWith('revise:编造:'),
    cmd.slice(0, 50) + (cmd.length > 50 ? '…' : '')
  );

  const storyCount = await page.locator('.story').count();
  record(
    'UX08',
    '右边有示例故事',
    '左右对照可读',
    storyCount >= 3,
    `${storyCount} 条示例`
  );
} catch (e) {
  record('UX00', '浏览器自测', '整体', false, String(e.message));
}

await browser.close();

const failed = results.filter((r) => !r.ok).length;
const lines = [
  '# 阶段 0 人机体验自测报告（Playwright）',
  '',
  `**结果：** ${failed === 0 ? '全部通过' : `${failed} 项未通过`}`,
  '',
  '> 这层测的是：**真人打开 review.html 点按钮时，页面会不会按设计反应。**',
  '> 不替代你亲自验收，但比「只检查 html 里有这段代码」更接近真实体验。',
  '',
  '| ID | 检查项 | 对应体验 | 结果 | 说明 |',
  '|----|--------|----------|------|------|',
];
for (const r of results) {
  lines.push(`| ${r.id} | ${r.name} | ${r.feature} | ${r.ok ? '✓' : '✗'} | ${r.detail} |`);
}
lines.push('', '由 `node scripts/verify_stage0_ux.mjs` 生成。');
writeFileSync(reportPath, lines.join('\n'), 'utf-8');
console.log(`\n合计: ${results.length} 项, 失败 ${failed}`);
console.log(`已写入: ${reportPath}`);
process.exit(failed ? 1 : 0);
