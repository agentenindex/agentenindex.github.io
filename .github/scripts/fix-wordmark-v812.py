from pathlib import Path
import re

brand_new='<a class="brand" href="/" aria-label="AgentenIndex Startseite"><img alt="" aria-hidden="true" class="brand-symbol-v2" height="40" src="/assets/agentenindex-symbol-v2.svg" width="40"/><span class="brand-wordmark-v2"><span class="brand-main-v2">Agenten</span><span class="brand-accent-v2">Index</span></span></a>'

changed=0
replaced=0
for p in Path('.').rglob('*.html'):
    if '.git' in p.parts:
        continue
    s=p.read_text(encoding='utf-8')
    old=s

    # Replace the horizontal SVG logo in all header/footer brand anchors.
    s,n=re.subn(
        r'<a class="brand" href="/">\s*<img[^>]*class="brand-full-logo"[^>]*/>\s*</a>',
        brand_new,
        s,
        flags=re.I|re.S
    )
    replaced += n

    # Also normalize any already partially altered brand anchor.
    s,n2=re.subn(
        r'<a class="brand" href="/"[^>]*>\s*<img[^>]*class="brand-full-logo"[^>]*/>\s*</a>',
        brand_new,
        s,
        flags=re.I|re.S
    )
    replaced += n2

    # About-page showcase: use symbol + browser-rendered wordmark instead of SVG text.
    s=re.sub(
        r'<img alt="AgentenIndex Logo" class="brand-showcase-logo"[^>]*/>',
        '<div class="brand-showcase-logo-v2" aria-label="AgentenIndex"><img alt="" aria-hidden="true" height="96" src="/assets/agentenindex-symbol-v2.svg" width="96"/><span><b>Agenten</b><em>Index</em></span></div>',
        s
    )

    # Cache bust.
    s=re.sub(r'/assets/styles\.css\?v=[^"\']+','/assets/styles.css?v=8.1.2',s)

    if s!=old:
        p.write_text(s,encoding='utf-8')
        changed+=1

cssp=Path('assets/styles.css')
css=cssp.read_text(encoding='utf-8')
block=r'''
/* AgentenIndex v8.1.2 robust browser-rendered wordmark */
.brand{
  display:inline-flex;
  align-items:center;
  gap:10px;
  min-width:max-content;
  white-space:nowrap;
  line-height:1;
  text-decoration:none;
}
.brand-symbol-v2{
  display:block;
  width:40px;
  height:40px;
  flex:0 0 40px;
  object-fit:contain;
}
.brand-wordmark-v2{
  display:inline-flex;
  align-items:baseline;
  gap:0;
  font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  font-size:1.48rem;
  font-weight:850;
  line-height:1;
  letter-spacing:-.045em;
}
.brand-main-v2{
  color:#1769ff;
  background:linear-gradient(90deg,#1769ff,#1288ef);
  -webkit-background-clip:text;
  background-clip:text;
  -webkit-text-fill-color:transparent;
}
.brand-accent-v2{
  color:#f0ad21;
  background:linear-gradient(90deg,#ffd02d,#efa11d);
  -webkit-background-clip:text;
  background-clip:text;
  -webkit-text-fill-color:transparent;
}
.footer .brand{
  gap:11px;
}
.footer .brand-symbol-v2{
  width:42px;
  height:42px;
  flex-basis:42px;
}
.footer .brand-wordmark-v2{
  font-size:1.56rem;
}
.brand-showcase-logo-v2{
  width:100%;
  max-width:440px;
  min-height:190px;
  display:flex;
  align-items:center;
  justify-content:center;
  gap:20px;
  padding:34px;
  border:1px solid #e3e9f2;
  border-radius:26px;
  background:linear-gradient(145deg,#fff,#f6f9ff);
  box-shadow:0 16px 46px rgba(34,61,98,.055);
}
.brand-showcase-logo-v2 img{
  width:96px;
  height:96px;
  object-fit:contain;
}
.brand-showcase-logo-v2 span{
  display:inline-flex;
  align-items:baseline;
  font-size:2.3rem;
  line-height:1;
  font-weight:850;
  letter-spacing:-.05em;
}
.brand-showcase-logo-v2 b{
  color:#1769ff;
}
.brand-showcase-logo-v2 em{
  font-style:normal;
  color:#f0ad21;
}
@media(max-width:1100px){
  .brand-symbol-v2{width:36px;height:36px;flex-basis:36px}
  .brand-wordmark-v2{font-size:1.32rem}
}
@media(max-width:700px){
  .brand{gap:8px}
  .brand-symbol-v2{width:34px;height:34px;flex-basis:34px}
  .brand-wordmark-v2{font-size:1.22rem}
  .footer .brand-symbol-v2{width:38px;height:38px;flex-basis:38px}
  .footer .brand-wordmark-v2{font-size:1.35rem}
  .brand-showcase-logo-v2{max-width:390px;min-height:160px;padding:26px;gap:14px}
  .brand-showcase-logo-v2 img{width:74px;height:74px}
  .brand-showcase-logo-v2 span{font-size:1.8rem}
}
'''
if 'AgentenIndex v8.1.2 robust browser-rendered wordmark' not in css:
    css += '\n'+block
cssp.write_text(css,encoding='utf-8')

# Make the standalone horizontal SVG safe too, even though the live header no longer depends on SVG text metrics.
logo=Path('assets/agentenindex-logo.svg')
if logo.exists():
    t=logo.read_text(encoding='utf-8')
    t=t.replace('viewBox="0 0 2050 420"','viewBox="0 0 2350 420"')
    t=t.replace('x="1240" y="294" fill="url(#wordGold)"','x="1500" y="294" fill="url(#wordGold)"')
    logo.write_text(t,encoding='utf-8')

# Validation.
assert replaced >= 280, replaced
for fn in ['index.html','agenten/index.html','agenten/claude-code/index.html','wissen/index.html','ueber/index.html']:
    s=Path(fn).read_text(encoding='utf-8')
    assert 'brand-symbol-v2' in s, fn
    assert 'brand-wordmark-v2' in s, fn
    assert 'brand-full-logo' not in s, fn
    assert '/assets/styles.css?v=8.1.2' in s, fn

versions=set()
for p in Path('.').rglob('*.html'):
    if '.git' in p.parts or p.as_posix().startswith('design-'):
        continue
    s=p.read_text(encoding='utf-8')
    for m in re.finditer(r'/assets/styles\.css\?v=([^"\']+)',s):
        versions.add(m.group(1))
assert versions=={'8.1.2'}, versions

print('WORDMARK_FIX_READY', 'html_changed',changed,'brand_replacements',replaced)
