import './style.css';
import { analyze, categories, samples } from './rules.mjs';
type Finding = ReturnType<typeof analyze>['findings'][number];
const app = document.querySelector<HTMLDivElement>('#app')!;
app.innerHTML = `
  <header class="topbar"><a class="brand" href="/" aria-label="Honest Copy home"><span class="brand-mark" aria-hidden="true">h<span>c</span></span>Honest Copy<span class="edition">THE SELLER’S SECOND LOOK</span></a><span class="mode"><i></i><span id="mode-label">Demo mode · local templates</span></span></header>
  <main>
    <section class="intro"><div><p class="eyebrow">GOOD PRODUCTS. HONEST WORDS.</p><h1>A little less hype.<br>A lot more <em>trust.</em></h1><p class="lead">Give your product copy a second look.<br>Spot claims worth rethinking, and find a clearer way to say it.</p></div><aside class="intro-note"><span class="note-star" aria-hidden="true">✳</span><p>For the small shop.<br>The late-night listing.<br>The words you want to get right.</p><span>ENGLISH + 한국어</span></aside></section>
    <div class="workspace">
      <section class="paper input-panel" aria-labelledby="draft-heading"><div class="panel-top"><div><span class="step">01 / YOUR WORDS</span><h2 id="draft-heading">Start with your draft</h2></div><span class="local-note">No account. No saved drafts.</span></div>
        <div class="sample-row"><span>Try a fictional listing</span><button class="chip" id="sample-en">English sample ↗</button><button class="chip" id="sample-ko">Korean sample ↗</button></div>
        <label class="sr-only" for="copy-input">Product copy</label><textarea id="copy-input" placeholder="Paste your product title or description here…" maxlength="6000" spellcheck="false"></textarea>
        <div class="editor-meta"><span>English or Korean. Your words stay in this tab.*</span><span id="char-count">0 / 5,000</span></div>
        <div class="check-row"><button class="primary" id="check" disabled>Check my copy <span aria-hidden="true">→</span></button><span class="check-note">A clearer draft starts<br>with a closer look.</span></div>
        <p class="error" id="input-error" role="alert"></p>
        <section id="review-section" hidden><div class="section-heading"><h3>Your copy, annotated</h3><span>Color shows the type of claim</span></div><div class="annotated" id="annotated"></div><div class="legend" id="legend"></div></section>
        <section id="revised-section" hidden></section>
      </section>
      <aside class="review-column" aria-label="Copy review"><section class="score-panel"><div class="score-top"><span class="step">02 / THE SECOND LOOK</span><span class="tiny-pill">RULES FIRST</span></div><div id="score-display" class="score-display"><strong>—</strong><div><h2>Room for clearer words</h2><p>Your rule-risk score appears here.</p></div></div><div class="score-track"><span id="score-fill"></span></div><p class="score-caption">0–100 rule-risk indicator · lower is better<br>A wording check, never an approval score.</p></section>
        <div class="findings-heading"><h2>Things to rethink <span id="issue-count">0</span></h2><span id="findings-hint">A second pair of eyes</span></div>
        <div id="findings" aria-live="polite"><div class="empty-state"><span class="empty-icon" aria-hidden="true">⌁</span><h3>Let’s look at the words.</h3><p>Paste a draft or pick a sample. We’ll look for medical promises, guarantees, rankings and claims that need evidence.</p><div class="empty-tags"><span>Explainable checks</span><span>No AI key needed</span></div></div></div>
      </aside>
    </div>
    <footer><span><b>Honest words go further.</b> Built for thoughtful sellers.</span><p>*Checks and templates run locally. Optional AI wording shares the selected draft with your configured provider only when requested.<br>Patterns can miss claims and context. Review suggestions and evidence before publishing; this is not legal advice.</p><a href="https://github.com/kks0488/honest-copy" target="_blank" rel="noreferrer">How it works ↗</a></footer>
  </main><div id="toast" role="status" aria-live="polite"></div>`;
const el = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const input = el<HTMLTextAreaElement>('copy-input');
let baseline = '', current = '', checked = false;
function text(tag: string, value: string, className = '') {
  const node = document.createElement(tag); node.textContent = value; node.className = className; return node;
}
function notify(message: string) { el('toast').textContent = message; }
function inputChanged() {
  el('char-count').textContent = `${input.value.length.toLocaleString()} / 5,000`;
  el<HTMLButtonElement>('check').disabled = !input.value.trim() || input.value.length > 5000;
  el('input-error').textContent = input.value.length > 5000 ? 'Keep your draft under 5,000 characters.' : '';
  if (checked) {checked = false; baseline = ''; current = ''; render();}
}
input.addEventListener('input', inputChanged);
for (const lang of ['en','ko'] as const) el(`sample-${lang}`).addEventListener('click', () => {input.value = samples[lang]; inputChanged(); input.focus();});
el('check').addEventListener('click', () => {
  if (!input.value.trim() || input.value.length > 5000) return;
  baseline = input.value; current = baseline; checked = true; render(); notify('Copy checked. Review the highlighted phrases.');
});
function renderHighlights(findings: Finding[]) {
  const box = el('annotated'); box.replaceChildren(); let offset = 0;
  for (const [i,f] of findings.entries()) {
    box.append(document.createTextNode(current.slice(offset,f.start)));
    const mark = text('mark',f.phrase,f.category); mark.title = `${i+1}. ${f.label}`;
    box.append(mark); offset = f.end;
  }
  box.append(document.createTextNode(current.slice(offset)));
}
function render() {
  const {findings,score} = analyze(current);
  el('review-section').hidden = !checked;
  el('issue-count').textContent = checked ? String(findings.length) : '0';
  el('findings-hint').textContent = checked ? `${findings.length} phrase${findings.length===1?'':'s'} to review` : 'A second pair of eyes';
  el('score-display').replaceChildren();
  const scoreInfo = text('div','');
  scoreInfo.append(text('h2',!checked?'Room for clearer words':score===0?'A more measured draft':score>=60?'Some claims need care':'A few words to revisit'),text('p',checked?'Known pattern matches · review each one':'Your rule-risk score appears here.'));
  el('score-display').append(text('strong',checked?String(score):'—'),scoreInfo);
  el('score-fill').style.width = `${checked?score:0}%`;
  if (!checked) return;
  renderHighlights(findings);
  el('legend').replaceChildren(...Object.entries(categories).map(([key,cat]) => text('span',cat.short,`legend-item ${key}`)));
  const list = el('findings'); list.replaceChildren();
  if (!findings.length) {
    const empty = text('div','','empty-state success'); empty.append(text('span','✓','empty-icon'),text('h3','No listed patterns found.'),text('p','That’s a more measured draft by these rules. Unflagged claims may still need evidence or review.'));list.append(empty);
  }
  for (const [i,f] of findings.entries()) {
    const card = text('article','',`finding ${f.category}`);
    const head = text('div','','finding-top');head.append(text('span',String(i+1).padStart(2,'0'),'finding-number'),text('span',f.label,'category-label'));
    card.append(head,text('h3',`“${f.phrase}”`),text('p',f.explanation),text('span','TRY A MORE MEASURED PHRASE','suggestion-label'),text('div',f.replacement,'suggestion'));
    list.append(card);
  }
}
