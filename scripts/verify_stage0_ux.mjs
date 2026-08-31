import { createRequire } from 'module';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { existsSync, writeFileSync } from 'fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');
const reportPath = join(root, 'docs/自测/stage0-ux-self-test-report.md');
const results = [];

function record(id, name, feature, ok, detail) {
  results.push({ id, name, feature, ok, detail });
  console.log(`[${ok ? 'PASS' : 'FAIL'}] ${id} ${name} — ${detail}`);
}

function writeReport(skipped = false) {
  const failed = results.filter((r) => !r.ok).length;
  const lines = [
    '# 阶段 0 人机体验自测报告（Playwright）',
    '',
    skipped
      ? '**结果：** 已跳过（未安装 Playwright 浏览器）。请先运行：`npx playwright install`（在 screenshots 目录或项目根）。'
      : `**结果：** ${failed === 0 ? '全部通过' : `${failed} 项未通过`}`,
    '',
    '> 这层测的是：**真人打开 review.html 点按钮时，页面会不会按设计反应。**',
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
  return failed;
}

let chromium;
try {
  const require = createRequire(join(__dirname, '../screenshots/package.json'));
  chromium = require('playwright').chromium;
} catch {
  record('UX00', 'Playwright 依赖', '体验层前置', false, 'screenshots/package.json 未安装 playwright');
  writeReport(true);
  process.exit(0);
}

const { pathToFileURL } = await import('url');
const reviewUrl = pathToFileURL(join(root, 'project/trials/case-01/review.html')).href;

let browser;
try {
  browser = await chromium.launch({ headless: true });
} catch (e) {
  record(
    'UX00',
    'Playwright 浏览器',
    '体验层前置',
    false,
    `${e.message} — 请运行 npx playwright install`
  );
  writeReport(true);
  process.exit(0);
}

const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

try {
  await page.goto(reviewUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(2500);

  const sourceText = await page.locator('#source-text').innerText();
  record(
    'UX01',
    '左边加载出完整原文',
    '人打开页不看到空白/摘要',
    !sourceText.includes('加载中') && sourceText.includes('事件风暴') && sourceText.length > 800,
    `${sourceText.length} 字，含事件风暴`
  );

  await page.click('button.kw[data-kw="捕捉用户故事"]');
  await page.waitForTimeout(400);
  const markCount = await page.locator('mark').count();
  record('UX02', '点关键词会高亮', '不熟文件也能定位', markCount > 0, `高亮 ${markCount} 处`);

  await page.click('button.ok');
  let cmd = await page.inputValue('#cmd');
  record('UX03', '点通过出 ok', '锁定本步指令', cmd === 'ok', `cmd=${cmd}`);

  await page.click('button.bad[data-code="编造"]');
  cmd = await page.inputValue('#cmd');
  const badge = await page.locator('#verdict-badge').innerText();
  record(
    'UX04',
    '点编造清空 ok',
    '通过/打叉不同时对',
    cmd !== 'ok' && (badge.includes('待生成') || badge.includes('未确认')),
    `cmd=${cmd || '(空)'}, badge=${badge}`
  );

  const builderVisible = await page.locator('#builder').isVisible();
  record('UX05', '点编造出现句式区', '不会写原因有引导', builderVisible, 'builder 显示');

  await page.click('button.primary');
  cmd = await page.inputValue('#cmd');
  const statusEmpty = (await page.locator('#status').innerText()).includes('打叉');
  record(
    'UX06',
    '没填原因不能生成 revise',
    '打叉必须留痕',
    !cmd.startsWith('revise:'),
    cmd || '空'
  );

  await page.click('button.template-chip');
  await page.waitForTimeout(200);
  const reason = await page.inputValue('#reason');
  record('UX07', '点现成句式会填入', '降低写原因门槛', reason.length > 5, reason.slice(0, 30));

  await page.click('button.primary');
  cmd = await page.inputValue('#cmd');
  record(
    'UX08',
    '填好原因能生成 revise',
    '反馈点可交给 Loop',
    cmd.startsWith('revise:编造:'),
    cmd.slice(0, 60)
  );

  const aiBtn = await page.locator('#btn-ai').count();
  record('UX09', '有 AI 试抓按钮', '右侧可接 Agnes', aiBtn === 1, 'btn-ai 存在');
} catch (e) {
  record('UX00', '浏览器自测', '整体', false, String(e.message));
}

await browser.close();
const failed = writeReport(false);
process.exit(failed ? 1 : 0);
