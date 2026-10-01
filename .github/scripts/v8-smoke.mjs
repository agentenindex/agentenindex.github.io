import puppeteer from 'puppeteer-core';

const browser = await puppeteer.launch({
  headless: true,
  executablePath: '/usr/bin/google-chrome',
  args: ['--no-sandbox','--disable-dev-shm-usage']
});

const pages = [
  '/',
  '/agenten/',
  '/agenten/claude-code/',
  '/wissen/',
  '/wissen/was-ist-ein-ki-agent/',
  '/methodik/',
  '/unternehmen/'
];
const viewports = [
  {name:'desktop',width:1440,height:1000},
  {name:'mobile',width:390,height:844}
];

let failed=false;
for (const vp of viewports){
  for (const path of pages){
    const page=await browser.newPage();
    await page.setViewport({width:vp.width,height:vp.height,deviceScaleFactor:1});
    const errors=[];
    page.on('pageerror', e=>errors.push(String(e)));
    page.on('console', msg=>{if(msg.type()==='error') errors.push(msg.text())});

    const res=await page.goto('http://127.0.0.1:8080'+path,{waitUntil:'networkidle0',timeout:30000});
    const audit=await page.evaluate(()=>{
      const doc=document.documentElement;
      const logos=[...document.querySelectorAll('.ai-card-logo img')].map(el=>{
        const r=el.getBoundingClientRect();
        return {w:r.width,h:r.height};
      });
      const style=[...document.querySelectorAll('link[rel="stylesheet"]')].map(x=>x.getAttribute('href'));
      const header=document.querySelector('.site-header');
      const footer=document.querySelector('.footer');
      const passport=document.querySelector('.v7p-passport-card');
      return {
        title:document.title,
        overflow:doc.scrollWidth-doc.clientWidth,
        styles:style,
        logoCount:logos.length,
        maxLogo:logos.reduce((m,x)=>Math.max(m,x.w,x.h),0),
        headerColor:header?getComputedStyle(header).color:null,
        footerBg:footer?getComputedStyle(footer).backgroundColor:null,
        passportColor:passport?getComputedStyle(passport).color:null
      };
    });

    const ok = res && res.status()<400 &&
      audit.styles.some(x=>x && x.includes('styles.css?v=8.0.0')) &&
      audit.overflow <= 2 &&
      audit.maxLogo <= 50 &&
      errors.length===0;

    console.log(JSON.stringify({viewport:vp.name,path,status:res?.status(),ok,audit,errors}));
    if(!ok) failed=true;
    await page.close();
  }
}
await browser.close();
if(failed) process.exit(1);
