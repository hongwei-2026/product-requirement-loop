const assert = require('assert');
const flow = require('./collab_flow');

assert.strictEqual(flow.claimAllowed(['/claim']).ok, false);
assert.strictEqual(
  flow.claimAllowed(['我先看一下', '/claim\n提交到：docs/handbook/index.md']).ok,
  true
);
assert.strictEqual(
  flow.claimAllowed(['改这里 project/web/app.html', '/claim']).ok,
  true
);
assert.strictEqual(flow.isSubmittedCommand('/submitted'), true);
assert.strictEqual(flow.isSubmittedCommand('pipeline started\n/done'), true);
assert.strictEqual(flow.isSubmittedCommand('/已提交'), false);
assert.strictEqual(flow.isSubmittedCommand('/claim'), false);
assert.strictEqual(flow.parseReviewCommand('notes\n/approve'), 'pass');
assert.strictEqual(flow.parseReviewCommand('/reject missing screenshot'), 'fail');
assert.strictEqual(flow.parseReviewCommand('/通过'), null);
assert.strictEqual(flow.parseReviewCommand('看起来可以'), null);

const reviewers = ['hongwei-2026', 'hl019', 'Jerrybao99', 'likexin105'];
const partial = flow.tallyReviews(reviewers, 'hongwei-2026', { hl019: 'pass' });
assert.strictEqual(partial.ok, false);
assert.deepStrictEqual(partial.need.map((n) => n.toLowerCase()), ['hl019', 'jerrybao99', 'likexin105']);
assert.ok(partial.missing.includes('Jerrybao99'));

const full = flow.tallyReviews(reviewers, 'hongwei-2026', {
  hl019: 'pass',
  jerrybao99: 'pass',
  likexin105: 'pass',
  'hongwei-2026': 'pass',
});
assert.strictEqual(full.ok, true);
assert.ok(!full.passed.map((n) => n.toLowerCase()).includes('hongwei-2026'));

const rejected = flow.tallyReviews(reviewers, 'someone', {
  'hongwei-2026': 'pass',
  hl019: 'fail',
  jerrybao99: 'pass',
  likexin105: 'pass',
});
assert.strictEqual(rejected.ok, false);
assert.deepStrictEqual(rejected.rejected, ['hl019']);

console.log('collab_flow self-test ok');
