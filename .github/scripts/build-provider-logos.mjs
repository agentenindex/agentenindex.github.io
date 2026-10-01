import fs from 'fs';

const mod = await import('simple-icons');
const icons = Object.values(mod).filter(x =>
  x && typeof x === 'object' && typeof x.title === 'string' &&
  typeof x.path === 'string' && typeof x.hex === 'string'
);

const norm = s => String(s || '')
  .normalize('NFKD')
  .replace(/[\u0300-\u036f]/g,'')
  .toLowerCase()
  .replace(/&/g,'and')
  .replace(/\.com/g,'dotcom')
  .replace(/[^a-z0-9]/g,'');

const aliases = {
  'AWS':'Amazon Web Services',
  'Google Cloud':'Google Cloud',
  'monday.com':'monday.com',
  'Mistral AI':'Mistral AI',
  'NiCE Cognigy':'Cognigy',
  'Zendesk / Forethought':'Zendesk',
  'Thomson Reuters':'Thomson Reuters',
  'Relay.app':'Relay',
  'Relevance AI':'Relevance AI',
  'Tray.ai':'Tray.io',
  'Kore.ai':'Kore.ai',
  'xAI':'xAI',
  'You.com':'You.com'
};

const byNorm = new Map();
for (const i of icons) byNorm.set(norm(i.title), i);

const dataPath = 'data/agents.json';
const data = JSON.parse(fs.readFileSync(dataPath,'utf8'));
fs.mkdirSync('assets/provider-logos',{recursive:true});

function providerSlug(name){
  return name.toLowerCase()
    .normalize('NFKD').replace(/[\u0300-\u036f]/g,'')
    .replace(/&/g,'and')
    .replace(/[^a-z0-9]+/g,'-')
    .replace(/^-+|-+$/g,'');
}

function firstOfficialUrl(agent){
  for (const s of (agent.sources || [])){
    let u = null;
    if (Array.isArray(s) && s.length >= 2) u = s[1];
    else if (s && typeof s === 'object') u = s.url;
    if (typeof u === 'string' && /^https?:\/\//.test(u)) return u;
  }
  return null;
}

function initials(name){
  const bits = name.replace(/\/.*$/,'').split(/[^A-Za-z0-9]+/).filter(Boolean);
  if (!bits.length) return 'AI';
  if (bits.length === 1) return bits[0].slice(0,2).toUpperCase();
  return (bits[0][0] + bits[1][0]).toUpperCase();
}

function fallbackSvg(name){
  const label = initials(name);
  const hue = [...name].reduce((n,c)=>n+c.charCodeAt(0),0) % 360;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="${name.replace(/&/g,'&amp;')}"><rect width="128" height="128" rx="30" fill="hsl(${hue} 58% 94%)"/><rect x="1" y="1" width="126" height="126" rx="29" fill="none" stroke="hsl(${hue} 38% 80%)" stroke-width="2"/><text x="64" y="76" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="42" font-weight="800" fill="hsl(${hue} 55% 32%)">${label}</text></svg>`;
}

const providerAgents = new Map();
for (const a of data.agents){
  if (!providerAgents.has(a.provider)) providerAgents.set(a.provider,a);
}

const logoMap = {};
let simpleCount=0, faviconCount=0, fallbackCount=0;

for (const [provider, agent] of providerAgents.entries()){
  const slug = providerSlug(provider);
  const wanted = aliases[provider] || provider;
  const icon = byNorm.get(norm(wanted));

  if (icon){
    const file = `assets/provider-logos/${slug}.svg`;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" role="img" aria-label="${provider.replace(/&/g,'&amp;')}"><path fill="#${icon.hex}" d="${icon.path}"/></svg>`;
    fs.writeFileSync(file,svg);
    logoMap[provider] = {path:'/'+file,type:'brand',source:'simple-icons',title:icon.title};
    simpleCount++;
    continue;
  }

  const sourceUrl = firstOfficialUrl(agent);
  let faviconOk = false;
  if (sourceUrl){
    try{
      const fav = `https://www.google.com/s2/favicons?domain_url=${encodeURIComponent(sourceUrl)}&sz=128`;
      const res = await fetch(fav,{headers:{'User-Agent':'AgentenIndexLogoBuilder/1.0'}});
      if (res.ok){
        const buf = Buffer.from(await res.arrayBuffer());
        if (buf.length > 150){
          const file = `assets/provider-logos/${slug}.png`;
          fs.writeFileSync(file,buf);
          logoMap[provider] = {path:'/'+file,type:'favicon',source:sourceUrl};
          faviconCount++;
          faviconOk = true;
        }
      }
    }catch(e){}
  }
  if (faviconOk) continue;

  const file = `assets/provider-logos/${slug}.svg`;
  fs.writeFileSync(file,fallbackSvg(provider));
  logoMap[provider] = {path:'/'+file,type:'monogram',source:null};
  fallbackCount++;
}

for (const a of data.agents){
  const entry = logoMap[a.provider];
  a.provider_logo = entry.path;
  a.provider_logo_type = entry.type;
}
data.schema_version = '5.2';
data.updated = '2026-10-01';
fs.writeFileSync(dataPath,JSON.stringify(data,null,2)+'\n');

fs.writeFileSync('data/provider-logos.json',JSON.stringify({
  updated:'2026-10-01',
  providers:Object.keys(logoMap).length,
  logos:logoMap
},null,2)+'\n');

console.log(JSON.stringify({
  providers:Object.keys(logoMap).length,
  simple_icons:simpleCount,
  favicons:faviconCount,
  monograms:fallbackCount
}));
