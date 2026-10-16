import assert from 'node:assert/strict';
import { mkdir, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const browser = await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const context = await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1,permissions:['clipboard-read','clipboard-write']});
const page = await context.newPage();
const errors=[];page.on('pageerror',e=>errors.push(e.message));
const origin=process.env.APP_URL || 'http://127.0.0.1:5173';
async function sample(lang) {await page.locator(`#sample-${lang}`).click();await page.locator('#check').click();}
try {
  await mkdir('media',{recursive:true});
  await page.goto(origin);
  assert.equal(await page.locator('#check').isDisabled(),true);
  await page.screenshot({path:'media/start.png',fullPage:true});
  for (const lang of ['en','ko']) {
    await sample(lang);
    assert.equal(await page.locator('.finding').count(),4);
    assert.equal(await page.locator('mark').count(),4);
    assert.equal(await page.locator('#score-display strong').innerText(),'84');
    await page.screenshot({path:`media/${lang==='en'?'english':'korean'}-review.png`,fullPage:true});
    await page.getByRole('button',{name:/Apply suggestion 1:/}).click();
    assert.equal(await page.locator('#score-display strong').innerText(),'56');
    assert.ok((await page.locator('.compare').innerText()).includes('84 before'));
    await page.getByRole('button',{name:'Undo last change'}).click();
    assert.equal(await page.locator('#score-display strong').innerText(),'84');
    assert.equal(await page.locator('#revised-section').isHidden(),true);
    await page.getByRole('button',{name:'Apply all suggestions',exact:true}).click();
    assert.equal(await page.locator('#score-display strong').innerText(),'0');
    assert.equal(await page.locator('.finding').count(),0);
    assert.ok((await page.locator('#findings').innerText()).includes('No listed patterns found'));
    await page.getByRole('button',{name:'Copy revised text'}).click();
    assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),await page.locator('#revised-copy').innerText());
    await page.screenshot({path:`media/${lang==='en'?'english':'korean'}-revised.png`,fullPage:true});
  }
  await page.locator('#copy-input').fill('A simple cotton towel.');
  assert.equal(await page.locator('.finding').count(),0);
  assert.equal(await page.locator('#score-display strong').innerText(),'—');
  await page.locator('#check').click();
  assert.equal(await page.locator('#score-display strong').innerText(),'0');
  await page.locator('#copy-input').fill(' ');
  assert.equal(await page.locator('#check').isDisabled(),true);
  await page.locator('#copy-input').fill('a'.repeat(5001));
  assert.equal(await page.locator('#check').isDisabled(),true);
  assert.match(await page.locator('#input-error').innerText(),/under 5,000/);
  await page.locator('#copy-input').fill('<img src=x onerror="window.injected=true"> cures acne');
  await page.locator('#check').click();
  assert.equal(await page.locator('#annotated img').count(),0);
  assert.equal(await page.evaluate(()=>window.injected),undefined);
  await page.setViewportSize({width:390,height:844});
  await sample('ko');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
  await page.screenshot({path:'media/mobile-review.png',fullPage:true});
  await page.getByRole('button',{name:'Apply all suggestions',exact:true}).click();
  assert.equal(await page.locator('#score-display strong').innerText(),'0');
  // Real local API contract, without a provider key.
  if (!process.env.SKIP_API_CHECK) {
    const mode=await context.request.get(origin+'/api/rewrite');assert.equal(mode.status(),200);
    assert.equal((await mode.json()).mode,'template');
    const response=await context.request.post(origin+'/api/rewrite',{data:{text:'cures acne',findingId:'medical-en:0'}});
    assert.equal((await response.json()).mode,'template');
  }
  // Mocked browser transport exercises UI integration; this is not a real live API call.
  let scenario='live';
  await page.route('**/api/rewrite',async route=>{
    if(route.request().method()==='GET')return route.fulfill({json:{mode:'live'}});
    if(scenario==='stale')await new Promise(resolve=>setTimeout(resolve,350));
    if(scenario==='error')return route.fulfill({status:503,json:{error:'Unavailable'}});
    return route.fulfill({json:{mode:'live',replacement:'is intended for everyday care',notice:'Mocked AI wording for browser verification.'}});
  });
  await page.setViewportSize({width:1920,height:1080});
  await page.reload();await sample('en');
  await page.getByRole('button',{name:'Try AI wording'}).first().click();
  await page.getByText('Mocked AI wording for browser verification.',{exact:true}).first().waitFor();
  await page.getByRole('button',{name:/Apply suggestion 1:/}).click();
  assert.match(await page.locator('#revised-copy').innerText(),/is intended for everyday care/);
  scenario='error';await sample('en');
  await page.getByRole('button',{name:'Try AI wording'}).first().click();
  await page.getByText('AI wording unavailable. Using the local template instead.',{exact:true}).first().waitFor();
  scenario='stale';await sample('en');
  await page.getByRole('button',{name:'Try AI wording'}).first().click();
  await page.locator('#copy-input').fill('A completely new draft.');
  await page.waitForTimeout(550);
  assert.equal(await page.locator('.finding').count(),0);
  assert.equal(await page.locator('#revised-section').isHidden(),true);
  await page.unroute('**/api/rewrite');
  const mapPage=await context.newPage();
  await mapPage.goto('file://'+resolve('devpost/app-map.html'));
  assert.match(await mapPage.title(),/App Map/);
  assert.equal(await mapPage.locator('script').count(),0);
  for(const anchor of ['renderHighlights','renderRevised','changeDraft'])assert.ok((await readFile('src/main.ts','utf8')).includes(anchor));
  await mapPage.close();
  assert.deepEqual(errors,[]);
  console.log('PASS: EN/KO check→single rewrite→undo→apply all→copy; empty/benign/oversize/stale-edit/XSS/mobile; API demo + mocked live/failure/stale integration; no runtime errors.');
} finally {await context.close();await browser.close();}
