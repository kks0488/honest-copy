import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const browser = await chromium.launch({ headless:true, executablePath:process.env.CHROMIUM_PATH, args:['--no-sandbox'] });
const context = await browser.newContext({viewport:{width:1920,height:1080}, deviceScaleFactor:1});
const page = await context.newPage();
const errors=[];page.on('pageerror',e=>errors.push(e.message));
try {
  await page.goto(process.env.APP_URL || 'http://127.0.0.1:5173');
  await page.getByRole('button',{name:'English sample'}).click();
  await page.getByRole('button',{name:'Check my copy'}).click();
  assert.equal(await page.locator('.finding').count(),4);
  assert.equal(await page.locator('mark').count(),4);
  assert.equal(await page.locator('#score-display strong').innerText(),'84');
  await mkdir('media',{recursive:true});
  await page.screenshot({path:'media/english-review.png',fullPage:true});
  await page.getByRole('button',{name:'Korean sample'}).click();
  await page.getByRole('button',{name:'Check my copy'}).click();
  assert.equal(await page.locator('.finding').count(),4);
  assert.equal(await page.locator('mark').count(),4);
  assert.deepEqual(errors,[]);
  console.log('PASS: English + Korean browser checks, 4 exact highlights each, score 84, no runtime errors.');
} finally {await context.close();await browser.close();}
