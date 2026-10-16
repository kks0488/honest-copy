// Real browser recording only; no synthetic UI or simulated provider success.
import { mkdir, rename } from 'node:fs/promises';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const directory=process.env.VIDEO_DIR || '/tmp/learnai-capture';
await mkdir(directory,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox']});
const context=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1,recordVideo:{dir:directory,size:{width:1920,height:1080}},permissions:['clipboard-read','clipboard-write']});
const page=await context.newPage();
const pause=ms=>page.waitForTimeout(ms);
async function focus(locator) {await locator.scrollIntoViewIfNeeded();await pause(600);}
try {
  await page.goto(process.env.APP_URL || 'http://127.0.0.1:5173');
  await pause(6500);
  await page.locator('#sample-en').click();await pause(4000);
  await page.locator('#check').click();await pause(6500);
  await focus(page.locator('.finding').first());await pause(4500);
  await focus(page.locator('.finding').nth(2));await pause(4500);
  await focus(page.locator('.finding').nth(3));await pause(4500);
  await page.getByRole('button',{name:/Apply suggestion 1:/}).click();
  await focus(page.locator('#revised-section'));await pause(5000);
  await page.getByRole('button',{name:'Undo last change'}).click();await pause(2500);
  await page.getByRole('button',{name:'Apply all suggestions',exact:true}).click();
  await focus(page.locator('#revised-section'));await pause(6500);
  await page.getByRole('button',{name:'Copy revised text'}).click();await pause(3000);
  await page.locator('#sample-ko').click();await pause(2500);
  await page.locator('#check').click();await pause(5000);
  await focus(page.locator('.finding').nth(2));await pause(3500);
  await page.getByRole('button',{name:'Apply all suggestions',exact:true}).click();
  await focus(page.locator('#revised-section'));await pause(5000);
  await page.evaluate(()=>window.scrollTo(0,0));await pause(3500);
} finally {const video=page.video();await context.close();if(video)await rename(await video.path(),directory+'/honest-copy-raw.webm');await browser.close();}
console.log(directory+'/honest-copy-raw.webm');
