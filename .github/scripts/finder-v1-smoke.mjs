import puppeteer from 'puppeteer-core';

const browser=await puppeteer.launch({
  headless:true,
  executablePath:'/usr/bin/google-chrome',
  args:['--no-sandbox','--disable-dev-shm-usage']
});

async function baseAudit(path,vp){
  const page=await browser.newPage();
  await page.setViewport({width:vp.width,height:vp.height,deviceScaleFactor:1});
  const errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('console',m=>{if(m.type()==='error') errors.push(m.text())});
  const res=await page.goto('http://127.0.0.1:8080'+path,{waitUntil:'networkidle0',timeout:30000});
  const audit=await page.evaluate(()=>{
    const nav=document.querySelector('.nav');
    const brand=document.querySelector('.brand');
    const nr=nav?.getBoundingClientRect(), br=brand?.getBoundingClientRect();
    const navDisplay=nav?getComputedStyle(nav).display:null;
    return {
      title:document.title,
      overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
      styles:[...document.querySelectorAll('link[rel="stylesheet"]')].map(x=>x.getAttribute('href')),
      finderLinks:[...document.querySelectorAll('a[href="/finder/"]')].length,
      navDisplay,
      navOverlap:(navDisplay!=='none'&&nr&&br)?Math.max(0,br.right-nr.left):0,
      h1:document.querySelectorAll('h1').length
    };
  });
  const ok=res && res.status()<400 && audit.overflow<=2 &&
    audit.styles.some(x=>x?.includes('styles.css?v=8.2.0')) &&
    audit.finderLinks>=1 && audit.navOverlap<=1 && errors.length===0;
  console.log(JSON.stringify({kind:'base',viewport:vp.name,path,status:res?.status(),ok,audit,errors}));
  await page.close();
  return ok;
}

let failed=false;
for(const vp of [
  {name:'desktop',width:1440,height:1000},
  {name:'compact',width:1024,height:900},
  {name:'mobile',width:390,height:844}
]){
  for(const path of ['/','/agenten/','/agenten/claude-code/','/finder/']){
    if(!(await baseAudit(path,vp))) failed=true;
  }
}

// Functional AgentenFinder test.
{
  const page=await browser.newPage();
  await page.setViewport({width:1440,height:1200,deviceScaleFactor:1});
  const errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('console',m=>{if(m.type()==='error') errors.push(m.text())});
  const res=await page.goto('http://127.0.0.1:8080/finder/',{waitUntil:'networkidle0',timeout:30000});
  await page.waitForSelector('#finder-submit:not([disabled])',{timeout:10000});

  const structured=await page.evaluate(()=>{
    const blocks=[...document.querySelectorAll('script[type="application/ld+json"]')];
    return blocks.map(x=>JSON.parse(x.textContent));
  });

  await page.click('[data-finder-category][data-value="coding"]');
  await page.click('[data-finder-audience][data-value="unternehmen"]');
  await page.type('#finder-query','Bugfixes');
  await page.click('#finder-submit');
  await page.waitForSelector('.finder-result-card',{timeout:10000});

  const result=await page.evaluate(()=>({
    cards:document.querySelectorAll('.finder-result-card').length,
    names:[...document.querySelectorAll('.finder-result-card h3')].map(x=>x.textContent.trim()),
    reasons:[...document.querySelectorAll('.finder-match b')].map(x=>x.textContent.trim()),
    status:document.querySelector('#finder-status')?.textContent.trim(),
    overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth
  }));

  const ok=res && res.status()<400 && structured.length>=1 &&
    result.cards>=1 && result.cards<=3 &&
    result.names.includes('Devin') &&
    result.reasons.every(Boolean) &&
    result.overflow<=2 && errors.length===0;
  console.log(JSON.stringify({kind:'finder-function',ok,result,structuredBlocks:structured.length,errors}));
  if(!ok) failed=true;
  await page.close();
}

// Machine-readable resources.
for(const path of ['/data/agents.json','/data/finder-methodology.json','/sitemap.xml','/llms.txt']){
  const page=await browser.newPage();
  const res=await page.goto('http://127.0.0.1:8080'+path,{waitUntil:'domcontentloaded',timeout:20000});
  const ok=res && res.status()<400;
  console.log(JSON.stringify({kind:'resource',path,status:res?.status(),ok}));
  if(!ok) failed=true;
  await page.close();
}

await browser.close();
if(failed) process.exit(1);
