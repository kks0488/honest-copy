// Small production check; uses the real configured provider, never a mock.
import assert from 'node:assert/strict';
import {analyze, applyFinding, samples} from '../src/rules.mjs';
const origin=process.env.APP_URL || 'https://honest-copy.vercel.app';
const cases=[
  {language:'en',text:samples.en,index:0},
  {language:'ko',text:samples.ko,index:0},
  {language:'en',text:'Our cotton towel. Guaranteed results.',index:0},
  {language:'ko',text:'면 수건입니다. 효과 100% 보장.',index:0},
];
for(const item of cases) {
  const original=analyze(item.text),finding=original.findings[item.index];
  assert.ok(finding);
  const started=Date.now();
  const response=await fetch(new URL('/api/rewrite',origin),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:item.text,findingId:finding.id}),signal:AbortSignal.timeout(30000)});
  assert.equal(response.status,200);
  const result=await response.json();
  assert.equal(result.mode,'live','Real live output required; fallback is not a passing evaluation');
  assert.ok(result.replacement.length<=240);
  assert.ok(!/[\d<>\n\r]/u.test(result.replacement));
  assert.equal(/[가-힣]/u.test(result.replacement),item.language==='ko');
  assert.ok(!/clinically|doctor|dermatologist|antibacterial|hypoallergenic|hydrates|soothes|made with care|임상|의사|피부과|항균|저자극|보습|진정/u.test(result.replacement.toLowerCase()),'No unsupported benefit or endorsement');
  const revised=applyFinding(item.text,finding,result.replacement);
  assert.ok(analyze(revised).score<original.score);
  assert.ok(!/(?:입니다){2}|(?:합니다){2}|\.\.|。。/u.test(revised));
  console.log(JSON.stringify({language:item.language,selected:finding.phrase,replacement:result.replacement,revised,mode:result.mode,ms:Date.now()-started,usage:result.usage}));
}
console.log('PASS: four real EN/KO rewrites; language, length, numeric/claim patterns, sentence endings and risk reduction. Read the printed sentences to judge fluency; these checks cannot prove semantic grounding.');
