// Real production browser footage. No synthetic UI or simulated provider success.
import assert from 'node:assert/strict';
import {mkdir, readdir, rm} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {homedir} from 'node:os';
import path from 'node:path';
import {samples} from '../src/rules.mjs';
if(process.platform==='darwin') throw new Error('Record on pilot only.');
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const cache=path.join(homedir(),'.cache/ms-playwright');
const cached=(await readdir(cache)).filter(n=>n.startsWith('chromium_headless_shell-')).sort().reverse()[0];
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH || path.join(cache,cached,'chrome-headless-shell-linux64/chrome-headless-shell')});
const directory=path.resolve(process.env.VIDEO_DIR || 'media');
const rawDirectory='/tmp/honest-copy-polish1';
await mkdir(directory,{recursive:true});await mkdir(rawDirectory,{recursive:true});
const context=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1,recordVideo:{dir:rawDirectory,size:{width:1920,height:1080}},permissions:['clipboard-read','clipboard-write']});
await context.addInitScript(()=>addEventListener('DOMContentLoaded',()=>{
  const dot=document.createElement('div');dot.style.cssText='position:fixed;left:0;top:0;width:20px;height:20px;border:3px solid #254f40;background:#ffc677cc;border-radius:50%;pointer-events:none;z-index:2147483647;box-shadow:0 0 0 5px #ffc67733;transform:translate(-60px,-60px)';document.body.append(dot);
  addEventListener('mousemove',e=>{dot.style.transform=`translate(${e.clientX-10}px,${e.clientY-10}px)`;});
}));
const epoch=Date.now(),segments=[],evidence={calls:[],boxes:{},errors:[]};
const page=await context.newPage();page.on('pageerror',e=>evidence.errors.push(e.message));
const pause=ms=>page.waitForTimeout(ms);
async function click(locator) {const box=await locator.boundingBox();assert.ok(box);await page.mouse.move(box.x+box.width/2,box.y+box.height/2,{steps:30});await pause(200);await locator.click();}
async function scroll(selector) {
  await page.evaluate(async selector=>{const start=scrollY,end=Math.max(0,document.querySelector(selector).getBoundingClientRect().top+scrollY-32),epoch=performance.now();await new Promise(resolve=>{function tick(now){const p=Math.min(1,(now-epoch)/900);scrollTo(0,start+(end-start)*(1-Math.pow(1-p,3)));p<1?requestAnimationFrame(tick):resolve();}requestAnimationFrame(tick);});},selector);await pause(400);
}
async function segment(name,seconds,action) {
  const started=Date.now(),start=(started-epoch)/1000;await action();await pause(Math.max(700,seconds*1000-(Date.now()-started)+500));
  const duration=(Date.now()-started)/1000;segments.push({name,start,seconds,duration});console.log(JSON.stringify({segment:name,seconds,realDuration:duration}));
}
async function boxes(name) {
  const result={};for(const selector of ['#annotated','mark','.finding','.suggestion','#revised-copy','.score-panel']) {const locator=page.locator(selector).first();if(await locator.count())result[selector]=await locator.boundingBox();}evidence.boxes[name]=result;
}
const ffmpeg=args=>{const r=spawnSync('ffmpeg',['-hide_banner','-loglevel','error','-y',...args],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);};
try {
  await page.goto(process.env.APP_URL || 'https://honest-copy.vercel.app',{waitUntil:'networkidle'});
  await page.getByText('AI wording available · rules first',{exact:true}).waitFor();
  await page.screenshot({path:path.join(directory,'start.png')});
  await scroll('.workspace');
  for(const [language,key,seconds] of [['english','en',20],['korean','ko',12]]) {
    await page.locator('#copy-input').fill('');
    await segment(language+'-live',seconds,async()=>{
      await click(page.locator('#copy-input'));await page.locator('#copy-input').pressSequentially(samples[key],{delay:32});
      await click(page.locator('#check'));await pause(650);await scroll('.workspace');
      assert.equal(await page.locator('mark').count(),4);
      const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/rewrite')&&r.request().method()==='POST');
      await click(page.getByRole('button',{name:'Try AI wording'}).first());
      const response=await responsePromise,result=await response.json();assert.equal(response.status(),200);assert.equal(result.mode,'live');
      await page.getByText('AI wording. Review it for accuracy before applying.',{exact:true}).first().waitFor();
      evidence.calls.push({language,mode:result.mode,replacement:result.replacement,usage:result.usage});
      await pause(700);
    });
    await page.screenshot({path:path.join(directory,language+'-review.png')});await boxes(language+'-review');
    await segment(language+'-apply',10,async()=>{
      await pause(900);await click(page.getByRole('button',{name:/Apply suggestion 1:/}));await scroll('#review-section');await pause(1200);
      assert.ok(await page.locator('#revised-copy').isVisible());assert.equal(await page.locator('#score-display strong').innerText(),'56');
    });
    await page.screenshot({path:path.join(directory,language+'-revised.png')});await boxes(language+'-revised');await scroll('.workspace');
  }
  assert.deepEqual(evidence.errors,[]);
} finally {
  const raw=await page.video().path();await context.close();await browser.close();
  for(const s of segments) {
    ffmpeg(['-ss',String(s.start),'-i',raw,'-t',String(s.seconds),'-vf',`trim=duration=${s.duration},setpts=${Math.min(1,s.seconds/s.duration)}*(PTS-STARTPTS),fps=30,scale=1920:1080,setsar=1,tpad=stop_mode=clone:stop_duration=1`,'-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',path.join(directory,s.name+'.mp4')]);
  }
  await rm(raw);
}
ffmpeg(['-sseof','-4','-i',path.join(directory,'english-live.mp4'),'-i',path.join(directory,'english-apply.mp4'),'-filter_complex','[0:v]setpts=PTS-STARTPTS[a];[1:v]trim=duration=5,setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0[out]','-map','[out]','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',path.join(directory,'hook-live.mp4')]);
console.log(JSON.stringify(evidence,null,2));
