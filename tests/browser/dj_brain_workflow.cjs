// Run with Playwright available on NODE_PATH. All network requests are mocked;
// synthetic songs only, no credentials, real plan mutations or live playback.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '../..');
const web = path.join(root, 'brain/web');
const providers = [
  {name:'claude-cli', label:'Claude (signed-in CLI)', available:true, detail:'signed in'},
  {name:'codex-cli', label:'OpenAI Codex (signed-in CLI)', available:false, detail:'not signed in'},
  {name:'grok-cli', label:'Grok (signed-in CLI)', available:false, detail:'not signed in'},
  {name:'anthropic-api', label:'Claude API key', available:false, detail:'set ANTHROPIC_API_KEY in .env'},
  {name:'openai-api', label:'OpenAI API key', available:false, detail:'set OPENAI_API_KEY in .env'},
  {name:'xai-api', label:'xAI Grok API key', available:true, detail:'key set · model grok-example'},
  {name:'hcompany-api', label:'H Company Holo API key', available:true, detail:'key set · model holo3-1-35b-a3b'},
  {name:'llama-server', label:'llama.cpp llama-server (local)', available:true, detail:'running at http://127.0.0.1:8080'},
];
const tracks = [
  {track_id:'synthetic-a',artist:'North Avenue',title:'After Hours',bpm:94,key:'Am'},
  {track_id:'synthetic-b',artist:'Velvet Room',title:'First Light',bpm:96,key:'C'},
  {track_id:'synthetic-c',artist:'The Low End',title:'Keep It Moving',bpm:95,key:'Am'},
];
const errors = [], posts = [];
let missing = 0, failedAsk = false, refreshes = 0;
const summary = {track_count:3,event_count:8,estimated_seconds:620,profile:{name:'club-set'},backbeat:{matched:1,unverified:1},tracks,segments:[{index:0,from:'After Hours',to:'First Light',technique:'gentle_blend',beats:32,score:.8}]};
const mix = () => ({profile:'dj-showcase',playlist_ready:true,plan_ready:true,plan_stale:false,building:0,running:0,enriching:0,finalized:{count:3,analyzed_count:3-missing,missing_bpm_count:missing,tracks},summary});

(async () => {
  const browser = await chromium.launch({executablePath: process.env.CLAWDJ_TEST_CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless:true});
  try {
    const context = await browser.newContext({viewport:{width:1440,height:1100}});
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      if (request.method() === 'POST') posts.push({path:url.pathname,body:request.postDataJSON()});
      if (url.pathname === '/') return route.fulfill({contentType:'text/html',body:fs.readFileSync(path.join(web,'playlist.html'),'utf8')});
      if (url.pathname.startsWith('/web/')) return route.fulfill({contentType:'text/javascript',body:fs.readFileSync(path.join(web,path.basename(url.pathname)),'utf8')});
      let data = {};
      switch (url.pathname) {
        case '/api/providers': refreshes++; data={providers}; break;
        case '/api/meta': data={track_count:3,analyzed_count:3,selected_analyzed_count:3,selected_count:3,artists:[]}; break;
        case '/api/tracks': data={total:3,tracks}; break;
        case '/api/brain': data={results:{},running:0}; break;
        case '/api/brain/ask': if(failedAsk) return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Synthetic provider failure'})}); break;
        case '/api/mix': data=mix(); break;
        case '/api/directives': data={running:0,preview:{notes:[{track_id:'synthetic-a',artist:'North Avenue',title:'After Hours',old:'',new:'ride_beats=192'}],reorder:null}}; break;
        case '/api/plans': data={plans:[]}; break;
        case '/api/plans/active': data={}; break;
        case '/api/collections': data={collections:[],active:null}; break;
      }
      await route.fulfill({contentType:'application/json',body:JSON.stringify(data)});
    });
    await page.goto('http://clawdj.test/#mix');
    await page.waitForFunction(() => document.querySelector('#builder-readiness').textContent === '3 tracks ready');
    assert.equal(await page.locator('#directives-engine').count(),0);
    assert.equal(await page.locator('#engine option[value="nemoclaw"]').count(),0);
    assert.equal(await page.locator('#engine option').count(),8);
    assert.equal(await page.locator('#engine option[value="codex-cli"]').isDisabled(),true);
    assert.equal(await page.locator('#interpret-directives').isDisabled(),true);
    await page.locator('#order-engine').selectOption('hcompany-api');
    await page.locator('[data-profile="club-set"]').click();
    await page.locator('#mix-brief').fill('Smooth blends; let the verses breathe.');
    await page.locator('#refresh-providers').click();
    await page.waitForFunction(() => !document.querySelector('#refresh-providers').disabled);
    assert.equal(await page.locator('#order-engine').inputValue(),'hcompany-api');
    await page.evaluate(() => pollMix());
    assert.equal(await page.locator('[data-profile="club-set"]').getAttribute('aria-pressed'),'true');
    await page.locator('#build-mix').click();
    assert.deepEqual(posts.find(p => p.path === '/api/mix/build').body,{profile:'club-set',dj_format:'none',mix_brief:'Smooth blends; let the verses breathe.',order_engine:'hcompany-api'});
    await page.evaluate(() => { clearInterval(mixState.pollTimer); mixState.pollTimer=null; });
    await page.locator('#mix-advanced summary').click();
    await page.locator('#interpret-directives').click();
    assert.equal(posts.find(p => p.path === '/api/directives/ask').body.engine,'hcompany-api');
    assert.equal(posts.some(p => p.path === '/api/directives/apply'),false);
    assert.equal(posts.some(p => p.path === '/api/mix/start'),false);
    await page.locator('#order-engine').selectOption('none');
    assert.equal(await page.locator('#interpret-directives').isDisabled(),true);
    missing=1; await page.evaluate(() => pollMix());
    assert.equal(await page.locator('#build-mix').isDisabled(),true);
    missing=0; await page.evaluate(() => pollMix());
    await page.locator('#mix-advanced').evaluate(el => el.open=false);
    await page.locator('#order-engine').selectOption('llama-server');
    await page.locator('.mix-builder').screenshot({path:'/private/tmp/clawdj-builder-desktop.png'});
    await page.setViewportSize({width:390,height:844});
    await page.locator('.mix-builder').screenshot({path:'/private/tmp/clawdj-builder-mobile.png'});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),true);
    await page.locator('#nav-curate').click();
    await page.locator('#engine').selectOption('llama-server');
    await page.locator('#brief').fill('Old-school soul');
    failedAsk=true; await page.locator('#ask').click();
    await page.waitForFunction(() => document.querySelector('#brain-detail').textContent.includes('Synthetic provider failure'));
    assert.equal(await page.locator('#ask').isDisabled(),false);
    for(const p of providers) p.available=false;
    await page.locator('#refresh-brain-providers').click();
    await page.waitForFunction(() => !document.querySelector('#refresh-brain-providers').disabled);
    assert.equal(await page.locator('#ask').isDisabled(),true);
    await page.locator('#nav-mix').click();
    await page.locator('#order-engine').selectOption('none');
    assert.equal(await page.locator('#build-mix').isDisabled(),false);
    assert.equal(await page.locator('#interpret-directives').isDisabled(),true);
    assert(refreshes >= 3);
    assert.deepEqual(errors,[]);
    console.log('PASS: shared provider requests, previews, refresh, preference retention, failures, optimizer-only, analysis gate, desktop/mobile layout');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode=1; });
