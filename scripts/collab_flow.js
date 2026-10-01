/** Shared rules for /claim and /approve. Used by Actions and local self-test. */

function hasSubmitTarget(text) {
  const s = String(text || '');
  if (/提交到\s*[:：]\s*\S+/.test(s)) return true;
  if (/(?:^|\n)\s*(?:改动|改到|文件)\s*[:：]\s*\S+/.test(s)) return true;
  if (/(?:project|docs|scripts|\.github)\/[A-Za-z0-9._/\-]+/.test(s)) return true;
  return false;
}

function claimAllowed(bodies) {
  if (hasSubmitTarget((bodies || []).filter(Boolean).join('\n'))) {
    return { ok: true, message: '' };
  }
  return {
    ok: false,
    message: [
      '还不能接取。请先在本 Issue 写清要提交到仓库的哪里。',
      '例如单独一行：`提交到：project/web/app.html`',
      '写好后再单独一行发送 `/claim`。',
    ].join('\n'),
  };
}

const PASS = new Set(['approve', 'lgtm', 'ack']);
const FAIL = new Set(['reject', 'changes', 'deny']);

function isSubmittedCommand(body) {
  return String(body || '').split(/\r?\n/).some((line) => /^\/(submitted|done)$/i.test(line.trim()));
}

function parseReviewCommand(body) {
  const lines = String(body || '').split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  for (const line of lines) {
    let m = line.match(/^\/(approve|lgtm|ack|reject|changes|deny)(?![A-Za-z0-9_])/i);
    if (!m && /^(approve|lgtm|ack|reject|changes|deny)$/i.test(line)) {
      m = [line, line];
    }
    if (!m) continue;
    const key = m[1].toLowerCase();
    if (PASS.has(key)) return 'pass';
    if (FAIL.has(key)) return 'fail';
  }
  return null;
}

function tallyReviews(required, author, votes) {
  const authorKey = String(author || '').toLowerCase();
  const need = (required || []).filter((u) => u.toLowerCase() !== authorKey);
  const missing = [];
  const rejected = [];
  const passed = [];
  for (const name of need) {
    const hit = (votes || {})[name.toLowerCase()];
    if (!hit) missing.push(name);
    else if (hit !== 'pass') rejected.push(name);
    else passed.push(name);
  }
  return { need, missing, rejected, passed, ok: missing.length === 0 && rejected.length === 0 && need.length > 0 };
}

module.exports = { hasSubmitTarget, claimAllowed, isSubmittedCommand, parseReviewCommand, tallyReviews };
