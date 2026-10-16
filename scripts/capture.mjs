import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
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
  assert.deepEqual(errors,[]);
  console.log('PASS: EN/KO check→single rewrite→undo→apply all→copy; empty/benign/oversize/stale-edit/XSS/mobile; no runtime errors.');
} finally {await context.close();await browser.close();}
