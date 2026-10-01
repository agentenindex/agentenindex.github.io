from pathlib import Path
import re

# 1) Give the full horizontal logo enough intrinsic canvas on the right.
logo=Path('assets/agentenindex-logo.svg')
s=logo.read_text(encoding='utf-8')
s=s.replace('viewBox="0 0 1700 420"','viewBox="0 0 2050 420"')
logo.write_text(s,encoding='utf-8')

# 2) Append final fixes after all older rules so they always win.
cssp=Path('assets/styles.css')
css=cssp.read_text(encoding='utf-8')
fix=r'''
/* AgentenIndex v8.1.1 visual fixes */
.brand-full-logo{
  width:200px;
  height:auto;
  max-height:42px;
  object-fit:contain;
  object-position:left center;
  overflow:visible;
}
.footer .brand-full-logo{
  width:215px;
  max-height:44px;
}
.v73home-copy h1{
  line-height:.98;
  padding-bottom:.08em;
  overflow:visible;
}
.v73home-copy h1 span{
  display:block;
  padding-bottom:.08em;
  overflow:visible;
}
@media(max-width:700px){
  .brand-full-logo{width:172px;max-height:38px}
  .footer .brand-full-logo{width:188px;max-height:40px}
  .v73home-copy h1{line-height:1}
}
'''
if 'AgentenIndex v8.1.1 visual fixes' not in css:
    css += '\n'+fix
cssp.write_text(css,encoding='utf-8')

# 3) Cache-bust sitewide.
changed=0
for p in Path('.').rglob('*.html'):
    if '.git' in p.parts:
        continue
    t=p.read_text(encoding='utf-8')
    n=re.sub(r'/assets/styles\.css\?v=[^"\']+','/assets/styles.css?v=8.1.1',t)
    if n!=t:
        p.write_text(n,encoding='utf-8')
        changed+=1

# Validation.
assert 'viewBox="0 0 2050 420"' in logo.read_text(encoding='utf-8')
assert 'line-height:.98' in cssp.read_text(encoding='utf-8')
assert 'width:200px' in cssp.read_text(encoding='utf-8')
versions=set()
for p in Path('.').rglob('*.html'):
    if '.git' in p.parts or p.as_posix().startswith('design-'):
        continue
    t=p.read_text(encoding='utf-8')
    for m in re.finditer(r'/assets/styles\.css\?v=([^"\']+)',t):
        versions.add(m.group(1))
assert versions=={'8.1.1'},versions
print('VISUAL_FIX_READY',changed)
