from pathlib import Path
import json,re

data=json.loads(Path('data/agents.json').read_text(encoding='utf-8'))
agents={a['slug']:a for a in data['agents']}

for slug,a in agents.items():
    p=Path('agenten')/slug/'index.html'
    if not p.exists():
        continue
    s=p.read_text(encoding='utf-8')
    img=f'<img src="{a["provider_logo"]}" alt="" aria-hidden="true" loading="eager" decoding="async"/>'
    s=re.sub(r'<div class="v7p-orbit-core">.*?</div>',f'<div class="v7p-orbit-core">{img}</div>',s,count=1,flags=re.S)
    p.write_text(s,encoding='utf-8')

target_classes=('agent-list-card','v73agent','v73-related-card')
for p in Path('.').rglob('*.html'):
    if '.git' in p.parts:
        continue
    s=p.read_text(encoding='utf-8')
    original=s
    for slug,a in agents.items():
        href=f'/agenten/{slug}/'
        if href not in s:
            continue
        pattern=re.compile(rf'<a\b[^>]*href="{re.escape(href)}"[^>]*>',re.I)
        def repl(m):
            tag=m.group(0)
            cm=re.search(r'class="([^"]*)"',tag,re.I)
            if not cm or not any(c in cm.group(1).split() for c in target_classes):
                return tag
            after=s[m.end():m.end()+180]
            if 'agent-provider-mark' in after:
                return tag
            logo=(f'<span class="agent-provider-mark" aria-hidden="true">'
                  f'<img src="{a["provider_logo"]}" alt="" loading="lazy" decoding="async"/>'
                  f'</span>')
            return tag+logo
        s=pattern.sub(repl,s)
    if s!=original:
        p.write_text(s,encoding='utf-8')

preview=Path('design-next/index.html')
if preview.exists():
    s=preview.read_text(encoding='utf-8')
    for slug in ['chatgpt-deep-research','claude-code','gemini-deep-research','devin','salesforce-agentforce','intercom-fin']:
        a=agents[slug]
        href=f'/agenten/{slug}/'
        pat=re.compile(rf'(<a class="agent" href="{re.escape(href)}">)(?!\s*<span class="preview-provider-logo")')
        logo=f'<span class="preview-provider-logo" aria-hidden="true"><img src="{a["provider_logo"]}" alt=""/></span>'
        s=pat.sub(r'\1'+logo,s)
    if '.preview-provider-logo{' not in s:
        s=s.replace('</style>','''
.preview-provider-logo{position:absolute;right:22px;top:54px;width:54px;height:54px;border:1px solid #e4eaf3;border-radius:16px;background:rgba(255,255,255,.92);display:grid;place-items:center;box-shadow:0 8px 24px rgba(34,62,98,.07)}
.preview-provider-logo img{width:32px;height:32px;object-fit:contain}
.agent{position:relative}
.agent .agent-title{padding-right:66px}
</style>''')
    preview.write_text(s,encoding='utf-8')

css_path=Path('assets/styles.css')
css=css_path.read_text(encoding='utf-8')
block='''

/* AgentenIndex provider logos — local, reusable brand layer */
.agent-list-card,
.v73agent,
.v73-related-card{position:relative}
.agent-provider-mark{
  width:46px;height:46px;border-radius:14px;
  display:grid;place-items:center;
  background:rgba(255,255,255,.94);
  border:1px solid #e4e7e0;
  box-shadow:0 8px 24px rgba(24,31,26,.07);
}
.agent-provider-mark img{
  width:28px;height:28px;object-fit:contain;display:block;
}
.agent-list-card .agent-provider-mark{
  position:absolute;right:18px;top:18px;
}
.agent-list-card{
  padding-right:82px!important;
}
.v73agent .agent-provider-mark{
  position:absolute;right:20px;top:58px;
}
.v73agent h3{
  padding-right:58px;
}
.v73-related-card .agent-provider-mark{
  position:absolute;right:16px;top:16px;
}
.v7p-orbit-core{
  background:#fff!important;
  border:1px solid rgba(221,226,218,.9);
  box-shadow:0 0 0 10px rgba(205,164,75,.08),0 18px 45px rgba(20,24,21,.14)!important;
}
.v7p-orbit-core img{
  width:48px;height:48px;object-fit:contain;display:block;
}
@media(max-width:620px){
  .agent-list-card .agent-provider-mark{width:40px;height:40px;right:14px;top:14px}
  .agent-list-card .agent-provider-mark img{width:24px;height:24px}
  .agent-list-card{padding-right:68px!important}
  .v73agent .agent-provider-mark{width:40px;height:40px;right:16px;top:54px}
  .v73agent .agent-provider-mark img{width:24px;height:24px}
}
'''
if 'AgentenIndex provider logos — local, reusable brand layer' not in css:
    css_path.write_text(css+block,encoding='utf-8')

for slug,a in agents.items():
    p=Path('agenten')/slug/'index.html'
    assert p.exists(),slug
    s=p.read_text(encoding='utf-8')
    assert a['provider_logo'] in s,(slug,a['provider_logo'])
    logo_path=Path(a['provider_logo'].lstrip('/'))
    assert logo_path.exists(),logo_path

idx=Path('agenten/index.html').read_text(encoding='utf-8')
assert idx.count('agent-provider-mark') >= 100, idx.count('agent-provider-mark')
print('Profiles with provider logos:',len(agents))
print('Agent index card logos:',idx.count('agent-provider-mark'))
