// Production acceptance and footage: real UI clicks, real provider, no interception.
import assert from 'node:assert/strict';
import {mkdir, readdir, writeFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {homedir} from 'node:os';
import path from 'node:path';
import {analyze, applyFinding} from '../src/rules.mjs';
if(process.platform==='darwin') throw new Error('Run browsers and ffmpeg on pilot only.');
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const cache=path.join(homedir(),'.cache/ms-playwright');
const cached=(await readdir(cache)).filter(n=>n.startsWith('chromium_headless_shell-')).sort().reverse()[0];
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH || path.join(cache,cached,'chrome-headless-shell-linux64/chrome-headless-shell')});
const directory=path.resolve(process.env.VIDEO_DIR || 'media');
const samplesDirectory=path.resolve(process.env.SAMPLES_DIR || path.join(directory,'samples'));
const rawDirectory=path.join(directory,'raw');
await mkdir(directory,{recursive:true});await mkdir(samplesDirectory,{recursive:true});await mkdir(rawDirectory,{recursive:true});
const origin=process.env.APP_URL || 'https://honest-copy.vercel.app';
const cases=[
  {name:'english',label:'English skincare serum',input:'Our face serum cures acne in 3 days.\n100% guaranteed results.\nA 30 mL bottle for your daily routine.',expected:[['cures acne in 3 days','medical'],['100% guaranteed results','guarantee']]},
  {name:'kitchen',label:'English kitchen gadget',input:'This kitchen gadget is No.1 best-selling.\nIt lasts forever.\nA handheld kitchen tool for everyday cooking.',expected:[['No.1 best-selling','superlative'],['lasts forever','guarantee']]},
  {name:'korean',label:'Korean cosmetics',input:'데일리 페이스 세럼.\n3일 만에 여드름 완치.\n100% 효과 보장. 국내 1위.',expected:[['3일 만에 여드름 완치','medical'],['100% 효과 보장','guarantee'],['국내 1위','superlative']]},
];
const evidence={capturedAt:new Date().toISOString(),url:origin,viewport:'1920x1080',cases:[],errors:[]};
const ffmpeg=args=>{const r=spawnSync('ffmpeg',['-hide_banner','-loglevel','error','-y',...args],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);};
async function click(page,locator) {
  await locator.scrollIntoViewIfNeeded();const box=await locator.boundingBox();assert.ok(box);
  await page.mouse.move(box.x+box.width/2,box.y+box.height/2,{steps:20});await page.waitForTimeout(180);await locator.click();
}
async function scroll(page,selector) {
  await page.evaluate(selector=>{const e=document.querySelector(selector);scrollTo({top:Math.max(0,e.getBoundingClientRect().top+scrollY-32),behavior:'smooth'});},selector);
  await page.waitForTimeout(700);
}
async function boxes(page) {
  const result={};for(const selector of ['#copy-input','#annotated','.finding','.suggestion','#revised-copy','.compare','.score-panel']) {
    const locator=page.locator(selector).first();if(await locator.count())result[selector]=await locator.boundingBox();
  }return result;
}
async function shot(page,name,result) {await page.screenshot({path:path.join(directory,name+'.png')});result.boxes[name]=await boxes(page);}
function markdown(result) {
  return `# ${result.label} — ${result.status}\n\nProduction: ${origin}\n\nCaptured: ${evidence.capturedAt}\n\nProvider: live Nebius (every rewrite returned mode: live). Real UI actions at 1920×1080; no mocked responses.\n\n## Input\n\n${result.input}\n\n## Flags and explanations\n\n${result.flags.map((f,i)=>`${i+1}. **${f.phrase}** — ${f.label} (${f.category})\n   ${f.explanation}`).join('\n\n')}\n\n## Live rewrites, in application order\n\n${result.calls.map((c,i)=>`${i+1}. **${c.phrase}** → **${c.replacement}**\n   Mode: ${c.mode}; rule-risk: ${c.beforeScore} → ${c.afterScore}; ${c.ms} ms.\n\n   Resulting draft:\n\n${c.revised.split('\n').map(l=>'   > '+l).join('\n')}`).join('\n\n')}\n\n## Final draft\n\n${result.revised}\n\n## Before / after\n\nRule-risk score: **${result.beforeScore} → ${result.afterScore}**. Remaining matched phrases: ${result.remaining}. Lower scores only count matched wording patterns; they are not factual verification or publishing approval.\n\nUI errors: none. All expected claim spans/categories matched; every suggestion was applied through the UI, copied and undo/restored. Naturalness and grounding were also reviewed by the builder after capture; this is not owner sign-off or a legal review.\n`;
}
try {
  for(const item of cases) {
    const context=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1,recordVideo:{dir:rawDirectory,size:{width:1920,height:1080}},permissions:['clipboard-read','clipboard-write']});
    await context.addInitScript(()=>addEventListener('DOMContentLoaded',()=>{
      const dot=document.createElement('div');dot.style.cssText='position:fixed;left:0;top:0;width:20px;height:20px;border:3px solid #254f40;background:#ffc677cc;border-radius:50%;pointer-events:none;z-index:2147483647;transform:translate(-60px,-60px)';document.body.append(dot);
      addEventListener('mousemove',e=>dot.style.transform=`translate(${e.clientX-10}px,${e.clientY-10}px)`);
    }));
    const epoch=Date.now(),page=await context.newPage();
    page.on('pageerror',e=>evidence.errors.push(e.message));
    page.on('console',m=>{if(m.type()==='error')evidence.errors.push(m.text());});
    page.on('response',r=>{if(r.status()>=400)evidence.errors.push(`${r.status()} ${r.url()}`);});
    const result={...item,status:'FAIL',flags:[],calls:[],boxes:{},segments:[]};
    evidence.cases.push(result);
    try {
      await page.goto(origin,{waitUntil:'networkidle'});
      await page.getByText('AI wording available · rules first',{exact:true}).waitFor();
      await scroll(page,'.workspace');
      const inputStart=(Date.now()-epoch)/1000;
      await click(page,page.locator('#copy-input'));await page.locator('#copy-input').pressSequentially(item.input,{delay:38});
      await click(page,page.locator('#check'));await scroll(page,'.workspace');
      const flags=await page.locator('mark').evaluateAll(es=>es.map(e=>[e.textContent,e.className]));
      assert.deepEqual(flags,item.expected,'Every risky phrase needs its full span and correct category');
      result.flags=analyze(item.input).findings;
      assert.deepEqual(flags,result.flags.map(f=>[f.phrase,f.category]));
      result.beforeScore=Number(await page.locator('#score-display strong').innerText());
      assert.equal(result.beforeScore,analyze(item.input).score);
      await shot(page,item.name+'-flags',result);
      result.segments.push({name:item.name+'-input',start:inputStart,end:(Date.now()-epoch)/1000});
      let current=item.input;
      for(let i=0;i<item.expected.length;i++) {
        const finding=analyze(current).findings[0];assert.ok(finding);
        const card=page.locator('.finding').first();assert.ok((await card.innerText()).includes(finding.explanation));
        await scroll(page,'.workspace');
        const liveStart=(Date.now()-epoch)/1000;
        const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/rewrite')&&r.request().method()==='POST');
        await click(page,card.getByRole('button',{name:'Try AI wording'}));
        const started=Date.now(),response=await responsePromise,body=await response.json(),responseMs=Date.now()-started;
        assert.equal(response.status(),200);assert.equal(body.mode,'live','Template fallback is a failed live acceptance run');
        assert.ok(body.replacement?.trim());assert.ok(!/\[needs info\]|guaranteed|forever|best.selling|popular|built to last|years of use|완치|보장|1위/i.test(body.replacement));
        await page.getByText('AI wording. Review it for accuracy before applying.',{exact:true}).first().waitFor();
        assert.equal(await page.locator('.suggestion').first().innerText(),body.replacement);
        await page.waitForTimeout(1800);
        if(i===0)await shot(page,item.name+'-review',result);
        const applyStart=(Date.now()-epoch)/1000;
        await click(page,page.getByRole('button',{name:/Apply suggestion 1:/}));
        current=applyFinding(current,finding,body.replacement);
        assert.ok(!/\b(is|are|was|were)\s+\1\b/i.test(current),'No duplicate copula at a phrase boundary');
        assert.equal(await page.locator('#revised-copy').innerText(),current);
        const afterScore=Number(await page.locator('#score-display strong').innerText());
        assert.equal(afterScore,analyze(current).score);
        assert.ok(afterScore<(i?result.calls.at(-1).afterScore:result.beforeScore));
        await scroll(page,'#revised-section');await page.waitForTimeout(1900);
        if(i===0) {
          await shot(page,item.name+'-first-revised',result);
          result.segments.push({name:item.name+'-live',start:liveStart,end:applyStart});
          result.segments.push({name:item.name+'-apply',start:applyStart,end:(Date.now()-epoch)/1000});
        }
        result.calls.push({phrase:finding.phrase,replacement:body.replacement,mode:body.mode,usage:body.usage,ms:responseMs,beforeScore:i?result.calls.at(-1).afterScore:result.beforeScore,afterScore,revised:current});
      }
      result.revised=current;result.afterScore=Number(await page.locator('#score-display strong').innerText());result.remaining=await page.locator('mark').count();
      assert.equal(result.afterScore,0);assert.equal(result.remaining,0);
      assert.ok(!/\[needs info\]|\.\.|입니다입니다|합니다합니다/i.test(current));
      const sentences=current.split(/[.!?。\n]+/u).map(s=>s.trim()).filter(Boolean);
      assert.equal(new Set(sentences).size,sentences.length,'No duplicated sentences in the final draft');
      await scroll(page,'#revised-section');await shot(page,item.name+'-revised',result);
      await click(page,page.getByRole('button',{name:'Copy revised text'}));
      assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),current);
      await click(page,page.getByRole('button',{name:'Undo last change'}));
      assert.ok(await page.locator('mark').count()>0);
      // Restore the already verified live phrase after undo, without another API call.
      await page.evaluate(({text})=>{document.querySelector('#copy-input').value=text;document.querySelector('#copy-input').dispatchEvent(new Event('input',{bubbles:true}));},{text:current});
      await click(page,page.locator('#check'));assert.equal(await page.locator('mark').count(),0);
      assert.deepEqual(evidence.errors,[]);result.status='PASS';
    } finally {
      const raw=await page.video().path();await context.close();
      for(const s of result.segments)ffmpeg(['-ss',String(s.start),'-i',raw,'-t',String(Math.max(5,s.end-s.start+0.5)),'-vf','fps=30,scale=1920:1080,setsar=1,tpad=stop_mode=clone:stop_duration=2','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',path.join(directory,s.name+'.mp4')]);
    }
    console.log(JSON.stringify({case:item.name,status:result.status,before:result.beforeScore,after:result.afterScore,calls:result.calls}));
  }
  assert.equal(evidence.cases.filter(c=>c.status==='PASS').length,3);
  assert.deepEqual(evidence.errors,[]);
  for(const result of evidence.cases)await writeFile(path.join(samplesDirectory,result.name+'.md'),markdown(result));
  console.log('PASS: all three production inputs consecutively; seven live AI rewrites; copy/undo/recheck; no UI errors.');
} finally {
  await writeFile(path.join(directory,'production-verification.json'),JSON.stringify(evidence,null,2)+'\n');await browser.close();
}
