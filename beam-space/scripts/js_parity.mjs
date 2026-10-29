// Regenerates tests/fixtures/rules_parity.json from the original JavaScript rules.
// Run from the repository root of honest-copy:
//   node beam-space/scripts/js_parity.mjs beam-space/tests/fixtures/parity_phrases.json > beam-space/tests/fixtures/rules_parity.json
// Offsets are converted from UTF-16 units to code points so they compare with Python string indexes.
import { analyze, applyAll } from '../../src/rules.mjs';
import { readFileSync } from 'node:fs';

const phrases = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const cp = (s) => Array.from(s).length;
const out = phrases.map((text) => {
  const { findings, score } = analyze(text);
  return {
    text, score, revised: applyAll(text),
    findings: findings.map((f) => ({
      rule_id: f.ruleId, category: f.category, phrase: f.phrase, replacement: f.replacement,
      start: cp(text.slice(0, f.start)), end: cp(text.slice(0, f.end)),
    })),
  };
});
console.log(JSON.stringify(out, null, 1));
