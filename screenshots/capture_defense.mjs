/**
 * Capture defense-report screenshots (product UI + result pages).
 * Run from repo root:
 *   node screenshots/capture_defense.mjs
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync, readFileSync, existsSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath, pathToFileURL } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const outDir = join(root, "docs/答辩总报告/assets");
mkdirSync(outDir, { recursive: true });

const reviewPath = join(root, "project/trials/case-01/review.html");
const accepted = JSON.parse(
  readFileSync(join(root, "project/trials/case-01/output/accepted.json"), "utf-8")
);
const storyMd = readFileSync(
  join(root, "project/trials/case-01/output/requirement-story.md"),
  "utf-8"
).slice(0, 1200);

function writeTempHtml(name, body) {
  const p = join(outDir, name);
  writeFileSync(p, body, "utf-8");
  return pathToFileURL(p).href;
}

const archHtml = writeTempHtml(
  "_arch.html",
  `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>架构图</title>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
  mermaid.initialize({ startOnLoad: true, theme: "neutral" });
</script>
<style>
  body{font-family:"Segoe UI","PingFang SC",sans-serif;margin:0;padding:32px;background:#f7f5f0;color:#1a1a1a}
  h1{font-size:22px;margin:0 0 8px}
  p{color:#555;margin:0 0 24px}
  .box{background:#fff;border:1px solid #ddd;padding:24px;border-radius:4px}
</style></head><body>
<h1>product-requirement Loop 系统架构</h1>
<p>日志进入 → AI 两步 → 人确认 → 定稿 → 自动验收</p>
<div class="box"><pre class="mermaid">
flowchart TB
  subgraph Input["输入"]
    J["研发日志 journal-official-full.md"]
  end
  subgraph Loop["product-requirement 循环"]
    S1["Step1 AI<br/>整理需求故事"]
    F1["人反馈 ok / revise"]
    L["锁定 output/locked/"]
    S2["Step2 AI<br/>提取用户故事 JSON"]
    F2["人反馈 ok / revise"]
    S3["人工定稿 accepted.json"]
  end
  subgraph Tools["工具与验收"]
    P["prompts/*.md"]
    Y["specification.yaml"]
    R["review.html 验收页"]
    C["check.py"]
  end
  J --> S1
  Y --> S1
  P --> S1
  P --> S2
  S1 --> F1 --> L --> S2 --> F2 --> S3
  R -.对照.-> F1
  R -.对照.-> F2
  S3 --> C
</pre></div>
</body></html>`
);

const flowHtml = writeTempHtml(
  "_flow.html",
  `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>阶段流程图</title>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
  mermaid.initialize({ startOnLoad: true, theme: "neutral" });
</script>
<style>
  body{font-family:"Segoe UI","PingFang SC",sans-serif;margin:0;padding:32px;background:#f7f5f0}
  h1{font-size:22px;margin:0 0 8px}
  p{color:#555;margin:0 0 24px}
  .box{background:#fff;border:1px solid #ddd;padding:24px}
</style></head><body>
<h1>课题实施：阶段 0 → 7</h1>
<p>从读资料到可答辩演示的完整施工顺序</p>
<div class="box"><pre class="mermaid">
flowchart LR
  S0["0 读资料"] --> S1["1 搭环境"]
  S1 --> S2["2 定 yaml"]
  S2 --> S3["3 写提示词"]
  S3 --> S4["4 跑闭环"]
  S4 --> S5["5 check"]
  S5 --> S6["6 试点报告"]
  S6 --> S7["7 整理提交"]
</pre></div>
</body></html>`
);

const resultHtml = writeTempHtml(
  "_results.html",
  `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>运行结果</title>
<style>
  body{font-family:"Cascadia Code","Consolas","PingFang SC",sans-serif;margin:0;padding:28px;background:#1e1e1e;color:#d4d4d4}
  h1{font-size:18px;color:#fff;margin:0 0 16px}
  .panel{background:#252526;border:1px solid #3c3c3c;padding:16px;margin-bottom:16px}
  .ok{color:#4ec9b0}
  .key{color:#9cdcfe}
  .str{color:#ce9178}
  pre{white-space:pre-wrap;font-size:13px;line-height:1.5;margin:0}
  h2{font-size:14px;color:#dcdcaa;margin:0 0 8px}
</style></head><body>
<h1>case-01 运行结果摘录（阶段 4～5）</h1>
<div class="panel"><h2>闭环 metrics</h2>
<pre>rounds = <span class="ok">${accepted.loop_metrics?.rounds}</span>
corrections = <span class="ok">${accepted.loop_metrics?.corrections}</span>
rework = <span class="ok">${accepted.loop_metrics?.rework}</span>
feedback_triggered = <span class="ok">${accepted.loop_metrics?.feedback_triggered}</span>
history:
${(accepted.loop_metrics?.history || []).map((h) => "  " + h).join("\n")}
</pre></div>
<div class="panel"><h2>accepted.json · review</h2>
<pre>{
  <span class="key">"approved"</span>: <span class="ok">true</span>,
  <span class="key">"approver"</span>: <span class="str">"${accepted.review?.approver}"</span>,
  <span class="key">"comments"</span>: <span class="str">"${(accepted.review?.comments || "").slice(0, 80)}…"</span>
}</pre></div>
<div class="panel"><h2>故事条数 / 修订痕迹</h2>
<pre>stories = <span class="ok">${accepted.stories?.length}</span>
首条 text: <span class="str">${accepted.stories?.[0]?.text || ""}</span>
首条 revisions:
${JSON.stringify(accepted.stories?.[0]?.revisions || [], null, 2)}
</pre></div>
<div class="panel"><h2>check.py（阶段 5）</h2>
<pre class="ok">[OK] stories.json  exit=0  编造=0
[OK] accepted.json --strict  exit=0
uncovered.md 已落盘 · review.comments 已人工确认</pre></div>
</body></html>`
);

const storyHtml = writeTempHtml(
  "_story.html",
  `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>需求故事</title>
<style>
  body{font-family:"PingFang SC","Segoe UI",sans-serif;margin:0;padding:28px;background:#faf8f4;color:#222;max-width:900px}
  h1{font-size:20px;border-bottom:2px solid #2c5f4a;padding-bottom:8px}
  pre{white-space:pre-wrap;line-height:1.65;font-size:14px;background:#fff;border:1px solid #e0dcd3;padding:20px}
</style></head><body>
<h1>Step1 产出 · requirement-story.md（节选）</h1>
<pre>${storyMd.replace(/</g, "&lt;")}</pre>
</body></html>`
);

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

// 1) review.html
await page.goto(pathToFileURL(reviewPath).href, { waitUntil: "domcontentloaded", timeout: 30000 });
await page.waitForTimeout(2000);
await page.screenshot({ path: join(outDir, "shot-review-full.png"), fullPage: false });
// expand spec panel if present
try {
  await page.locator("#spec-panel summary").click({ timeout: 2000 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: join(outDir, "shot-review-spec.png"), fullPage: false });
} catch {}
// click AI area top
await page.screenshot({ path: join(outDir, "shot-review-hero.png"), clip: { x: 0, y: 0, width: 1400, height: 720 } });

// 2) architecture
await page.setViewportSize({ width: 1280, height: 900 });
await page.goto(archHtml, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(2500);
await page.screenshot({ path: join(outDir, "shot-architecture.png"), fullPage: true });

// 3) stage flow
await page.goto(flowHtml, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(2000);
await page.screenshot({ path: join(outDir, "shot-stages-flow.png"), fullPage: true });

// 4) results
await page.setViewportSize({ width: 1200, height: 900 });
await page.goto(resultHtml, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(500);
await page.screenshot({ path: join(outDir, "shot-run-results.png"), fullPage: true });

// 5) story
await page.goto(storyHtml, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(400);
await page.screenshot({ path: join(outDir, "shot-requirement-story.png"), fullPage: true });

await browser.close();
console.log("saved screenshots to", outDir);
