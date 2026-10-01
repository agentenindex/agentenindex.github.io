import puppeteer from 'puppeteer-core';

const browser=await puppeteer.launch({
  headless:true,
  executablePath:'/usr/bin/google-chrome',
  args:['--no-sandbox','--disable-dev-shm-usage']
});
const paths=['/','/agenten/','/agenten/claude-code/','/ueber/'];
for (const vp of [{n:'desktop',w:1440,h:1000},{n:'mobile',w:390,h:844}]){
  for (const path of paths){
    const page=await browser.newPage();
    await page.setViewport({width:vp.w,height:vp.h,deviceScaleFactor:1});
    const errors=[];
    page.on('pageerror',e=>errors.push(String(e)));
    const res=await page.goto('http://127.0.0.1:8080'+path,{waitUntil:'networkidle0',timeout:30000});
    const audit=await page.evaluate(()=>{
      const logos=[...document.querySelectorAll('.brand-full-logo')].map(x=>({
        complete:x.complete,naturalWidth:x.naturalWidth,
        width:x.getBoundingClientRect().width,height:x.getBoundingClientRect().height,
        src:x.getAttribute('src')
      }));
      const favicon=[...document.querySelectorAll('link[rel~="icon"]')].map(x=>x.getAttribute('href'));
      return {
        overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
        logos,
        favicon,
        stylesheet:[...document.querySelectorAll('link[rel="stylesheet"]')].map(x=>x.getAttribute('href'))
      };
    });
    const ok=res && res.status()<400 && audit.overflow<=2 &&
      audit.logos.length>=2 &&
      audit.logos.every(x=>x.complete&&x.naturalWidth>0&&x.width>100&&x.width<220) &&
      audit.favicon.includes('/favicon.svg') &&
      audit.stylesheet.some(x=>x.includes('styles.css?v=8.1.0')) &&
      errors.length===0;
    console.log(JSON.stringify({viewport:vp.n,path,status:res?.status(),ok,audit,errors}));
    if(!ok) process.exitCode=1;
    await page.close();
  }
}
await browser.close();
