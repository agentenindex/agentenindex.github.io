import puppeteer from 'puppeteer-core';

const browser=await puppeteer.launch({
  headless:true,
  executablePath:'/usr/bin/google-chrome',
  args:['--no-sandbox','--disable-dev-shm-usage']
});

for (const vp of [{name:'desktop',width:1440,height:1100},{name:'mobile',width:390,height:844}]){
  const page=await browser.newPage();
  await page.setViewport({width:vp.width,height:vp.height,deviceScaleFactor:1});
  const errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  const res=await page.goto('http://127.0.0.1:8080/',{waitUntil:'networkidle0',timeout:30000});
  const audit=await page.evaluate(()=>{
    const logo=document.querySelector('.brand-full-logo');
    const h1=document.querySelector('.v73home-copy h1');
    const span=h1?.querySelector('span');
    const lr=logo?.getBoundingClientRect();
    const sr=span?.getBoundingClientRect();
    const hr=h1?.getBoundingClientRect();
    const cs=h1?getComputedStyle(h1):null;
    const ss=span?getComputedStyle(span):null;
    return {
      overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
      stylesheet:[...document.querySelectorAll('link[rel="stylesheet"]')].map(x=>x.getAttribute('href')),
      logo:{w:lr?.width,h:lr?.height,naturalWidth:logo?.naturalWidth,naturalHeight:logo?.naturalHeight,complete:logo?.complete},
      hero:{lineHeight:cs?.lineHeight,paddingBottom:cs?.paddingBottom,spanPaddingBottom:ss?.paddingBottom,h:hr?.height,spanH:sr?.height}
    };
  });
  const ok=res && res.status()<400 &&
    audit.overflow<=2 &&
    audit.stylesheet.some(x=>x?.includes('styles.css?v=8.1.1')) &&
    audit.logo.complete && audit.logo.naturalWidth>0 &&
    audit.logo.w>160 && audit.logo.w<230 &&
    parseFloat(audit.hero.lineHeight)>70 &&
    parseFloat(audit.hero.paddingBottom)>0 &&
    parseFloat(audit.hero.spanPaddingBottom)>0 &&
    errors.length===0;
  console.log(JSON.stringify({viewport:vp.name,status:res?.status(),ok,audit,errors}));
  if(!ok) process.exitCode=1;
  await page.close();
}
await browser.close();
