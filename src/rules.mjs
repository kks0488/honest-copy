/** Finite wording heuristics, not factual verification or legal classification. */
export const categories = {
  medical: { label: 'Health / medical', short: 'Medical claim', weight: 28 },
  guarantee: { label: 'Absolute guarantee', short: 'Guarantee', weight: 22 },
  superlative: { label: 'Unverifiable superlative', short: 'Superlative', weight: 18 },
  evidence: { label: 'Missing evidence', short: 'Evidence', weight: 16 },
};
const rule = (id, category, pattern, replacement, explanation) => ({id, category, pattern, replacement, explanation});
export const rules = [
  rule('medical-en', 'medical', /\b(?:cures?|treats?|heals?)\s+(?:acne|eczema|diabetes|cancer|arthritis|disease)(?:\s+in\s+\d+\s+days?)?\b/giu, 'is designed for everyday care', 'This wording promises to treat a health condition. Describe the product’s everyday use instead; treatment claims need appropriate authorization and support.'),
  rule('medical-ko', 'medical', /(?:여드름|아토피|당뇨|암|질병)(?:을|를)?\s*(?:완치|치료)(?:합니다|해요|한다|하는|해|된다)?/gu, '일상적인 관리에 사용합니다', 'This phrase promises treatment of a health condition. Describe everyday use rather than claiming a medical effect.'),
  rule('guarantee-en', 'guarantee', /\b(?:100\s*%\s*(?:guaranteed(?:\s+results)?|effective|safe)|guaranteed\s+results|always\s+works|zero\s+side\s+effects|risk[ -]free)\b/giu, 'results may vary', 'An absolute promise leaves no room for different experiences. Set a realistic expectation instead.'),
  rule('guarantee-ko', 'guarantee', /(?:효과\s*)?100\s*%\s*(?:보장|안전|효과)(?:합니다|해요)?|부작용\s*(?:제로|없음|없는)|무조건\s*(?:효과|보장)/gu, '개인에 따라 차이가 있을 수 있습니다', 'A universal guarantee may overpromise. Make room for differences between people and situations.'),
  rule('superlative-en', 'superlative', /(?:\b(?:No\.?\s*1|number\s+one|#1)(?:\s+in\s+(?:Korea|the\s+world))?\b|\b(?:the\s+)?(?:world['’]s\s+best|best\s+in\s+the\s+world|best\s+ever)\b)/giu, 'made with care', 'A ranking needs a clear source, category and date. Without those, describe a concrete feature rather than claiming first place.'),
  rule('superlative-ko', 'superlative', /(?:국내|대한민국|세계)\s*(?:1\s*위|최고)|업계\s*(?:최초|최고)|넘버\s*원/gu, '세심하게 만든 제품', 'A first-place or best-in-category claim needs a defined comparison and current evidence. Describe a feature you can support.'),
  rule('evidence-en', 'evidence', /\b(?:clinically\s+proven|scientifically\s+proven|doctor[ -]recommended|dermatologist[ -]approved|research[ -]backed)\b/giu, 'thoughtfully developed', 'This wording suggests expert or research support. Check the actual evidence and its scope, or remove the implied endorsement. This tool does not verify studies.'),
  rule('evidence-ko', 'evidence', /임상(?:시험)?(?:으로)?\s*(?:입증|검증)(?:된|한|했습니다)?|의사\s*추천|과학적으로\s*입증(?:된)?|피부과\s*(?:인증|추천)/gu, '일상적인 사용을 고려한', 'This phrase implies research or expert support. Verify the specific evidence or use wording without an implied endorsement.'),
];
export const samples = {
  en: 'Our everyday face serum cures acne in 3 days.\n100% guaranteed results. No.1 in Korea.\nClinically proven care for your daily routine.',
  ko: '이 세럼은 여드름을 치료합니다.\n효과 100% 보장. 국내 1위.\n임상으로 입증된 데일리 케어 제품입니다.',
};
export function analyze(text) {
  if (typeof text !== 'string') throw new TypeError('Copy must be text');
  const candidates = [];
  for (const r of rules) {
    for (const m of text.matchAll(new RegExp(r.pattern.source, r.pattern.flags))) {
      const start = m.index;
      candidates.push({ id: `${r.id}:${start}`, ruleId: r.id, start, end: start + m[0].length,
        phrase: m[0], category: r.category, ...categories[r.category], explanation: r.explanation,
        replacement: /^[A-Z]/.test(m[0]) ? r.replacement[0].toUpperCase() + r.replacement.slice(1) : r.replacement });
    }
  }
  candidates.sort((a,b) => a.start-b.start || b.weight-a.weight || b.end-a.end);
  const findings = [];
  for (const f of candidates) if (!findings.length || f.start >= findings.at(-1).end) findings.push(f);
  return { findings, score: Math.min(100, findings.reduce((sum, f) => sum + f.weight, 0)) };
}
export function applyFinding(text, finding, replacement = finding.replacement) {
  if (text.slice(finding.start, finding.end) !== finding.phrase) throw new Error('Draft changed; check again');
  return text.slice(0, finding.start) + replacement + text.slice(finding.end);
}
export function applyAll(text) {
  return analyze(text).findings.reverse().reduce((draft, f) => applyFinding(draft, f), text);
}
