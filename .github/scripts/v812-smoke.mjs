import puppeteer from 'puppeteer-core';

const browser=await puppeteer.launch({
  headless:true,
  executablePath:'/usr/bin/google-chrome',
  args:['--no-sandbox','--disable-dev-shm-usage']
});

const viewports=[
  {name:'desktop',width:1440,height:1000},
  {name:'compact',width:1024,height:900},
  {name:'mobile',width:390,height:844}
];

for (const vp of viewports){
  const page=await browser.newPage();
  await page.setViewport({width:vp.width,height:vp.height,deviceScaleFactor:1});
  const errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  const res=await page.goto('http://127.0.0.1:8080/',{waitUntil:'networkidle0',timeout:30000});
  const audit=await page.evaluate(()=>{
    const header=document.querySelector('.header');
    const brand=document.querySelector('.brand');
    const symbol=document.querySelector('.brand-symbol-v2');
    const wordmark=document.querySelector('.brand-wordmark-v2');
    const nav=document.querySelector('.nav');
    const r=e=>e?e.getBoundingClientRect():null;
    const hr=r(header), br=r(brand), sr=r(symbol), wr=r(wordmark), nr=r(nav);
    const overlap=br&&nr ? Math.max(0,br.right-nr.left) : 0;
    return {
      overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
      stylesheet:[...document.querySelectorAll('link[rel="stylesheet"]')].map(x=>x.getAttribute('href')),
      header:hr?{w:hr.width,h:hr.height}:null,
      brand:br?{w:br.width,h:br.height}:null,
      symbol:sr?{w:sr.width,h:sr.height}:null,
      wordmark:wr?{w:wr.width,h:wr.height,text:wordmark.textContent}:null,
      nav:nr?{display:getComputedStyle(nav).display,left:nr.left,right:nr.right}:null,
      overlap
    };
  });

  const navHidden = audit.nav?.display==='none';
  const ok=res && res.status()<400 &&
    audit.overflow<=2 &&
    audit.stylesheet.some(x=>x?.includes('styles.css?v=8.1.2')) &&
    audit.brand && audit.brand.w>130 && audit.brand.w<260 &&
    audit.wordmark?.text==='AgentenIndex' &&
    audit.symbol?.w<=42 &&
    (navHidden || audit.overlap<=0.5) &&
    errors.length===0;

  console.log(JSON.stringify({viewport:vp.name,status:res?.status(),ok,audit,errors}));
  if(!ok) process.exitCode=1;
  await page.close();
}
await browser.close();
