import './style.css';
import { analyze, applyFinding, applyAll, categories, samples } from './rules.mjs';
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
let history: string[] = [];
let revision = 0;
let liveMode = false;
let pendingId: string | null = null;
const aiResults = new Map<string,{replacement:string;notice:string;mode:string}>();
function invalidateAI() {revision++;pendingId=null;aiResults.clear();}
const startState = el('findings').firstElementChild!.cloneNode(true);
let toastTimer: ReturnType<typeof setTimeout>;

function text(tag: string, value: string, className = '') {
  const node = document.createElement(tag); node.textContent = value; node.className = className; return node;
}
function notify(message: string) { el('toast').textContent = message; clearTimeout(toastTimer); toastTimer = setTimeout(() => {el('toast').textContent='';}, 4500); }
function inputChanged() {
  invalidateAI();
  el('char-count').textContent = `${input.value.length.toLocaleString()} / 5,000`;
  el<HTMLButtonElement>('check').disabled = !input.value.trim() || input.value.length > 5000;
  el('input-error').textContent = input.value.length > 5000 ? 'Keep your draft under 5,000 characters.' : '';
  if (checked) {checked = false; baseline = ''; current = ''; history = []; render();}
}
input.addEventListener('input', inputChanged);
for (const lang of ['en','ko'] as const) el(`sample-${lang}`).addEventListener('click', () => {input.value = samples[lang]; inputChanged(); input.focus();});
el('check').addEventListener('click', () => {
  if (!input.value.trim() || input.value.length > 5000) return;
  invalidateAI(); baseline = input.value; current = baseline; history = []; checked = true; render(); notify('Copy checked. Review the highlighted phrases.');
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
  el('revised-section').hidden = !checked || current === baseline;
  if (!checked) {el('findings').replaceChildren(startState.cloneNode(true)); return;}
  renderRevised();
  renderHighlights(findings);
  el('legend').replaceChildren(...Object.entries(categories).map(([key,cat]) => text('span',cat.short,`legend-item ${key}`)));
  let allActions = document.getElementById('all-actions');
  allActions?.remove();
  if (findings.length) {
    allActions = text('div','','all-actions'); allActions.id='all-actions';
    const applyAllButton = text('button','Apply all suggestions','secondary') as HTMLButtonElement;
    applyAllButton.addEventListener('click',()=>changeDraft(applyAll(current)));
    allActions.append(applyAllButton,text('p','Review the revised draft before publishing.')); el('review-section').append(allActions);
  }
  const list = el('findings'); list.replaceChildren();
  if (!findings.length) {
    const empty = text('div','','empty-state success'); empty.append(text('span','✓','empty-icon'),text('h3','No listed patterns found.'),text('p','That’s a more measured draft by these rules. Unflagged claims may still need evidence or review.'));list.append(empty);
  }
  for (const [i,f] of findings.entries()) {
    const card = text('article','',`finding ${f.category}`);
    const head = text('div','','finding-top');head.append(text('span',String(i+1).padStart(2,'0'),'finding-number'),text('span',f.label,'category-label'));
    const aiResult = aiResults.get(f.id);
    card.append(head,text('h3',`“${f.phrase}”`),text('p',f.explanation),text('span','TRY A MORE MEASURED PHRASE','suggestion-label'),text('div',aiResult?.replacement || f.replacement,'suggestion'));
    const actions = text('div','','finding-actions');
    const apply = text('button','Apply suggestion ↗','secondary') as HTMLButtonElement;
    apply.setAttribute('aria-label',`Apply suggestion ${i+1}: ${f.phrase}`);
    apply.addEventListener('click',()=>changeDraft(applyFinding(current,f,aiResult?.replacement || f.replacement)));
    const aiButton = text('button',pendingId===f.id?'Finding words…':'Try AI wording','quiet') as HTMLButtonElement;
    aiButton.disabled=!liveMode || pendingId!==null;
    aiButton.title=liveMode?'Send this draft to the configured AI provider for an optional suggestion':'AI is unavailable in this demo. Local suggestions always work.';
    aiButton.addEventListener('click',()=>requestAI(f));
    actions.append(apply,aiButton); card.append(actions);
    if (liveMode || aiResult) card.append(text('p',aiResult?.notice || 'Optional: AI wording sends this draft to the configured provider when you click.','ai-note'));
    list.append(card);
  }
}

function changeDraft(next: string) {
  if (next === current) return;
  invalidateAI(); history.push(current); current = next; render();
  notify('Suggestion applied. Review your revised draft.');
}
function renderRevised() {
  const section = el('revised-section'); section.replaceChildren();
  if (current === baseline) return;
  const heading = text('div','','section-heading'); heading.append(text('h3','Your revised draft'),text('span','03 / CLEARER WORDS'));
  const compare = text('div','','compare');
  compare.append(text('span','Rule-risk score:'),text('span',`${analyze(baseline).score} before →`),text('b',`${analyze(current).score} after`));
  const revised = text('div',current,'revised-box'); revised.id='revised-copy';
  const actions = text('div','','revision-actions');
  const copy = text('button','Copy revised text','primary') as HTMLButtonElement;
  copy.addEventListener('click',async()=>{
    try {await navigator.clipboard.writeText(current);notify('Revised text copied. Give it one final read before publishing.');}
    catch {notify('Clipboard unavailable. Select and copy the revised draft above.');}
  });
  const undo = text('button','Undo last change','secondary') as HTMLButtonElement;
  undo.disabled=!history.length; undo.addEventListener('click',()=>{invalidateAI();current=history.pop()!;render();notify('Last change undone.');});
  actions.append(copy,undo); section.append(heading,revised,compare,actions);
}

async function requestAI(finding: Finding) {
  const atRevision=revision;pendingId=finding.id;render();
  let result:{replacement:string;mode:string;notice:string};
  try {
    const response=await fetch('/api/rewrite',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:current,findingId:finding.id}),signal:AbortSignal.timeout(30000)});
    if(!response.ok) throw new Error('Unavailable');
    const data=await response.json();
    if(typeof data.replacement!=='string' || !data.replacement.trim() || data.replacement.length>240 || analyze(data.replacement).findings.length || !['template','live'].includes(data.mode)) throw new Error('Invalid response');
    result={replacement:data.replacement,mode:data.mode,notice:typeof data.notice==='string'?data.notice:'Review this suggestion before applying.'};
  } catch {result={replacement:finding.replacement,mode:'template',notice:'AI wording unavailable. Using the local template instead.'};}
  if(revision!==atRevision) return;
  pendingId=null;aiResults.set(finding.id,result);render();notify(result.notice);
}
fetch('/api/rewrite',{signal:AbortSignal.timeout(5000)}).then(r=>r.ok?r.json():null).then(data=>{
  liveMode=data?.mode==='live';
  el('mode-label').textContent=liveMode?'AI wording available · rules first':'Demo mode · local templates';
  if(checked)render();
}).catch(()=>{/* Static hosting retains working local templates. */});
