import test from 'node:test';
import assert from 'node:assert/strict';
import { analyze, applyFinding, applyAll, samples } from '../src/rules.mjs';
for (const [lang, sample] of Object.entries(samples)) {
  test(`${lang}: exact spans and all four categories`, () => {
    const { findings, score } = analyze(sample);
    assert.equal(findings.length,4);
    assert.equal(new Set(findings.map(f=>f.category)).size,4);
    assert.equal(score,84);
    for (const f of findings) assert.equal(sample.slice(f.start,f.end),f.phrase);
  });
  test(`${lang}: applying all lowers score without adding known patterns`, () => {
    const revised = applyAll(sample);
    assert.equal(analyze(revised).score,0);
    assert.ok(revised.length>0);
    assert.notEqual(revised,sample);
  });
}
test('repeated matches replace only the selected occurrence', () => {
  const text = 'cures acne. cures acne.';
  const f = analyze(text).findings[1];
  assert.equal(applyFinding(text,f),'cures acne. Is designed for everyday care.');
  assert.equal(analyze(applyAll(text)).findings.length,0);
});
test('Unicode offsets and HTML remain plain input', () => {
  const text = '🧴 <script>alert(1)</script> 국내 1위';
  const f = analyze(text).findings[0];
  assert.equal(text.slice(f.start,f.end),'국내 1위');
  assert.ok(applyFinding(text,f).includes('<script>'));
});
test('benign text and boundaries do not match accidentally', () => {
  assert.equal(analyze('A soft cotton towel. Made for everyday use.').score,0);
  assert.equal(analyze('My best friend assures acne care is personal.').score,0);
  assert.equal(analyze('').findings.length,0);
  assert.throws(()=>analyze(null),TypeError);
});
test('stale spans fail instead of rewriting unrelated words', () => {
  const f = analyze('cures acne').findings[0];
  assert.throws(()=>applyFinding('a different draft', f),/Draft changed/);
});
test('scores cap at 100 and remain deterministic', () => {
  const text = 'cures acne. '.repeat(20);
  assert.equal(analyze(text).score,100);
  assert.deepEqual(analyze(text),analyze(text));
});
