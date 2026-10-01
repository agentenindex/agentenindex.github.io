import puppeteer from 'puppeteer-core';

const browser=await puppeteer.launch({
  headless:true,
  executablePath:'/usr/bin/google-chrome',
  args:['--no-sandbox','--disable-dev-shm-usage']
});

const paths=[
  '/agenten/chatgpt-deep-research/',
  '/agenten/claude-code/',
  '/agenten/zapier-central/',
  '/agenten/harvey-ai/'
];
const viewports=[
  {name:'desktop',width:1440,height:1100},
  {name:'mobile',width:390,height:844}
];

let failed=false;
for(const vp of viewports){
  for(const path of paths){
    const page=await browser.newPage();
    await page.setViewport({width:vp.width,height:vp.height,deviceScaleFactor:1});
    const errors=[];
    page.on('pageerror',e=>errors.push(String(e)));
    page.on('console',m=>{if(m.type()==='error') errors.push(m.text())});
    const res=await page.goto('http://127.0.0.1:8080'+path,{waitUntil:'networkidle0',timeout:30000});
    const audit=await page.evaluate(()=>{
      const graph=document.querySelector('.agentengraph-history');
      const changelog=document.querySelector('.changelog#changelog');
      const toc=[...document.querySelectorAll('.toc a')].map(x=>x.getAttribute('href'));
      const badge=graph?.querySelector('.ag-evidence-badge')?.textContent.trim();
      const baseline=graph?.querySelector('.ag-baseline')?.textContent.trim();
      const current=graph?.querySelector('.ag-current-head b')?.textContent.trim();
      const empty=graph?.querySelector('.ag-empty b')?.textContent.trim();
      const gr=graph?.getBoundingClientRect();
      const cr=changelog?.getBoundingClientRect();
      return {
        overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
        graphCount:document.querySelectorAll('.agentengraph-history').length,
        tocCount:toc.filter(x=>x==='#agentengraph').length,
        badge,baseline,current,empty,
        graphBeforeChangelog:!!(gr&&cr&&gr.top<cr.top),
        stylesheet:[...document.querySelectorAll('link[rel="stylesheet"]')].map(x=>x.getAttribute('href'))
      };
    });
    const ok=res && res.status()<400 &&
      audit.overflow<=2 &&
      audit.graphCount===1 &&
      audit.tocCount===1 &&
      audit.badge==='Quellenbindung: Profilebene' &&
      audit.baseline==='Baseline seit 1. Oktober 2026' &&
      /AI-\d{4} · \d+ aktive Aussagen/.test(audit.current||'') &&
      audit.empty==='Noch keine strukturierte Produktänderung seit der Baseline erfasst.' &&
      audit.graphBeforeChangelog &&
      audit.stylesheet.some(x=>x?.includes('styles.css?v=8.3.0')) &&
      errors.length===0;
    console.log(JSON.stringify({viewport:vp.name,path,status:res?.status(),ok,audit,errors}));
    if(!ok) failed=true;
    await page.close();
  }
}
await browser.close();
if(failed) process.exit(1);
