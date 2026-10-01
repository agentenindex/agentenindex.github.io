from pathlib import Path
import json, re, html

ROOT=Path('.')
data=json.loads(Path('data/agents.json').read_text(encoding='utf-8'))
agents={a['slug']:a for a in data['agents']}

MONTHS={1:'Jan.',2:'Feb.',3:'März',4:'Apr.',5:'Mai',6:'Juni',7:'Juli',8:'Aug.',9:'Sept.',10:'Okt.',11:'Nov.',12:'Dez.'}
FOCUS={
 'recherche':'Recherche & Analyse',
 'coding':'Code & Tools',
 'automatisierung':'Automatisierung',
 'unternehmen':'Enterprise & Prozesse',
 'service-sales':'Service & Sales',
 'recht':'Legal & Professional'
}
TONES=['mint','blue','peach','lilac','sky','gold']

def esc(x):
    return html.escape(str(x or ''), quote=True)

def de_date(s):
    try:
        y,m,d=map(int,s.split('-'))
        return f'{d:02d}. {MONTHS[m]} {y}'
    except Exception:
        return s or '—'

def tone_for(slug):
    return TONES[sum(ord(c) for c in slug)%len(TONES)]

def capability_list(a):
    vals=list(a.get('uses') or [])
    if len(vals)<3:
        vals += [x for x in (a.get('strengths') or []) if x not in vals]
    return vals[:3]

def card_inner(a):
    uses=capability_list(a)
    source_count=int(a.get('source_count') or 0)
    source_label=f'{source_count} Primärquelle' if source_count==1 else f'{source_count} Primärquellen'
    category=a.get('category_name') or a.get('category') or ''
    focus=FOCUS.get(a.get('category'), category)
    audience=a.get('audience_short') or '—'
    chips=''.join(f'<span>{esc(x)}</span>' for x in uses)
    return (
      f'<span class="ai-card-logo" aria-hidden="true"><img src="{esc(a["provider_logo"])}" alt="" loading="lazy" decoding="async"/></span>'
      f'<div class="ai-card-top"><span class="ai-card-verified">✓ geprüft</span><span class="ai-card-category">{esc(category)}</span></div>'
      f'<div class="ai-card-heading"><h3>{esc(a["name"])}</h3><small>{esc(a["provider"])}</small></div>'
      f'<p class="ai-card-summary">{esc(a.get("summary",""))}</p>'
      f'<div class="ai-card-chips">{chips}</div>'
      f'<div class="ai-card-meta">'
        f'<div><small>Fokus</small><b>{esc(focus)}</b></div>'
        f'<div><small>Zielgruppe</small><b>{esc(audience)}</b></div>'
        f'<div><small>Quellen</small><b>{esc(source_label)}</b></div>'
      f'</div>'
      f'<div class="ai-card-bottom"><span>Geprüft {esc(de_date(a.get("last_verified","")))} · Profil {esc(a.get("profile_version","2.0"))}</span><b>AgentenProfil öffnen →</b></div>'
    )

def enhance_opening(tag,a):
    cm=re.search(r'class="([^"]*)"',tag)
    if cm:
        classes=cm.group(1).split()
        if 'ai-agent-card' not in classes:
            classes.append('ai-agent-card')
        tag=tag[:cm.start(1)]+' '.join(classes)+tag[cm.end(1):]
    else:
        tag=tag[:-1]+' class="ai-agent-card">'
    if 'data-tone=' not in tag:
        tag=tag[:-1]+f' data-tone="{tone_for(a["slug"])}">'
    if 'data-category=' not in tag:
        tag=tag[:-1]+f' data-category="{esc(a.get("category",""))}">'
    return tag

def replace_cards(text, accepted_classes):
    total=0
    for slug,a in agents.items():
        href=f'/agenten/{slug}/'
        if href not in text:
            continue
        # Card anchors have no nested anchors.
        pat=re.compile(rf'(<a\b[^>]*href="{re.escape(href)}"[^>]*>)(.*?)(</a>)',re.I|re.S)
        def repl(m):
            nonlocal total
            tag=m.group(1)
            cm=re.search(r'class="([^"]*)"',tag,re.I)
            if not cm:
                return m.group(0)
            classes=set(cm.group(1).split())
            if not classes.intersection(accepted_classes):
                return m.group(0)
            total+=1
            return enhance_opening(tag,a)+card_inner(a)+m.group(3)
        text=pat.sub(repl,text)
    return text,total

MODERN_CSS=r'''
/* AgentenIndex modern AgentenProfil cards v1 */
.ai-agent-card{
  --ai-accent:#1769ff;--ai-soft:#eef5ff;--ai-blob:rgba(23,105,255,.14);--ai-deep:#124fb9;
  position:relative!important;overflow:hidden!important;isolation:isolate;
  min-height:430px!important;padding:24px!important;
  display:flex!important;flex-direction:column!important;
  background:
    radial-gradient(circle at 92% 22%,var(--ai-blob),transparent 27%),
    linear-gradient(145deg,#fff 0%,#fff 64%,var(--ai-soft) 150%)!important;
  border:1px solid color-mix(in srgb,var(--ai-accent) 17%,#e6eaf1)!important;
  border-radius:24px!important;text-decoration:none!important;color:#0b1739!important;
  box-shadow:0 9px 30px rgba(30,55,90,.055)!important;
  transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease!important;
}
.ai-agent-card::after{
  content:"";position:absolute;right:-28px;top:70px;width:155px;height:92px;z-index:-1;
  border-radius:58% 42% 65% 35%;transform:rotate(-24deg);
  background:linear-gradient(135deg,var(--ai-blob),transparent);opacity:.7;
}
.ai-agent-card:hover{transform:translateY(-4px)!important;box-shadow:0 22px 55px rgba(30,55,90,.11)!important;border-color:color-mix(in srgb,var(--ai-accent) 34%,#dfe5ee)!important}
.ai-agent-card[data-tone="mint"]{--ai-accent:#078e75;--ai-soft:#ecfaf5;--ai-blob:rgba(29,183,145,.17);--ai-deep:#066d5b}
.ai-agent-card[data-tone="blue"]{--ai-accent:#1769ff;--ai-soft:#eef5ff;--ai-blob:rgba(57,119,255,.16);--ai-deep:#124fb9}
.ai-agent-card[data-tone="peach"]{--ai-accent:#c56b19;--ai-soft:#fff4e9;--ai-blob:rgba(235,150,73,.18);--ai-deep:#8b4710}
.ai-agent-card[data-tone="lilac"]{--ai-accent:#7041d8;--ai-soft:#f5efff;--ai-blob:rgba(134,88,229,.16);--ai-deep:#5327b7}
.ai-agent-card[data-tone="sky"]{--ai-accent:#087ca8;--ai-soft:#edf9fc;--ai-blob:rgba(51,174,215,.17);--ai-deep:#075d7c}
.ai-agent-card[data-tone="gold"]{--ai-accent:#9a762d;--ai-soft:#fbf5e8;--ai-blob:rgba(200,162,82,.17);--ai-deep:#74551c}
.ai-card-top{display:flex;justify-content:space-between;align-items:center;gap:12px;min-height:30px;padding-right:74px}
.ai-card-verified{display:inline-flex;align-items:center;width:max-content;padding:6px 10px;border-radius:999px;background:#e9f8ef;color:#20703d;font-size:.64rem;font-weight:850;letter-spacing:.01em}
.ai-card-category{color:var(--ai-deep);font-size:.61rem;font-weight:850;letter-spacing:.12em;text-transform:uppercase}
.ai-card-logo{position:absolute;right:22px;top:58px;width:60px;height:60px;border-radius:18px;background:rgba(255,255,255,.92);border:1px solid rgba(223,229,237,.95);display:grid;place-items:center;box-shadow:0 10px 28px rgba(35,57,88,.08);z-index:2}
.ai-card-logo img{width:38px;height:38px;object-fit:contain;display:block}
.ai-card-heading{margin-top:24px;padding-right:78px}
.ai-agent-card .ai-card-heading h3{margin:0 0 5px!important;padding:0!important;color:#0a1737!important;font-size:1.65rem!important;line-height:1.04!important;letter-spacing:-.045em!important}
.ai-card-heading small{display:block;color:#8b6a2e!important;font-size:.65rem!important;letter-spacing:.13em!important;text-transform:uppercase;font-weight:850!important}
.ai-card-summary{margin:10px 0 16px!important;min-height:3.9em;color:#4f5e77!important;font-size:.82rem!important;line-height:1.52!important;padding-right:8px}
.ai-card-chips{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:17px}
.ai-card-chips span{display:inline-flex;align-items:center;min-height:30px;padding:7px 10px;border-radius:11px;border:1px solid color-mix(in srgb,var(--ai-accent) 11%,#e9edf4);font-size:.61rem;font-weight:720;color:var(--ai-deep);background:color-mix(in srgb,var(--ai-soft) 78%,#fff)}
.ai-card-chips span:nth-child(2){background:#eef6ff;color:#145bb7;border-color:#deebfb}
.ai-card-chips span:nth-child(3){background:#f5efff;color:#6632bd;border-color:#eadfff}
.ai-card-meta{display:grid!important;grid-template-columns:1.18fr 1.18fr .72fr!important;gap:8px!important;margin-top:auto!important}
.ai-card-meta>div{min-width:0;background:rgba(248,249,251,.84)!important;border:1px solid rgba(230,234,240,.85);border-radius:13px!important;padding:11px 12px!important}
.ai-card-meta small{display:block!important;color:#7c8799!important;font-size:.54rem!important;line-height:1.25;text-transform:uppercase;letter-spacing:.07em;margin-bottom:4px!important}
.ai-card-meta b{display:block!important;color:#17223d!important;font-size:.7rem!important;line-height:1.28!important;overflow-wrap:anywhere}
.ai-card-bottom{margin-top:17px;padding-top:14px;border-top:1px solid rgba(221,227,236,.95);display:grid;grid-template-columns:1fr auto;align-items:center;gap:12px}
.ai-card-bottom span{color:#788398;font-size:.58rem;line-height:1.35}
.ai-card-bottom b{color:var(--ai-deep);font-size:.72rem;font-weight:850;white-space:nowrap}
.modern-agent-grid{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:16px!important}
.v73agents{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:16px!important}
.v73agents .ai-agent-card{min-height:430px!important}
@media(max-width:1100px){
  .modern-agent-grid,.v73agents{grid-template-columns:repeat(2,minmax(0,1fr))!important}
}
@media(max-width:700px){
  .modern-agent-grid,.v73agents{grid-template-columns:1fr!important}
  .ai-agent-card{min-height:0!important;padding:20px!important}
  .ai-card-logo{width:52px;height:52px;right:18px;top:54px;border-radius:16px}
  .ai-card-logo img{width:32px;height:32px}
  .ai-card-heading{padding-right:68px}
  .ai-card-summary{min-height:0}
  .ai-card-meta{grid-template-columns:1fr 1fr!important}
  .ai-card-meta>div:last-child{grid-column:1/-1}
  .ai-card-bottom{grid-template-columns:1fr}
  .ai-card-bottom b{white-space:normal}
}
'''

# ---------- OPTION B: refine preview first ----------
preview=Path('design-next/index.html')
if preview.exists():
    s=preview.read_text(encoding='utf-8')
    # Replace its six agent cards with the exact production component.
    s,_=replace_cards(s,{'agent'})
    # Ensure preview-specific cards use the production class system.
    # Remove older preview logo elements/classes by relying on replacement.
    # Make the card grid 3 columns and append modern component CSS.
    s=s.replace('.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}', '.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}')
    if 'AgentenIndex modern AgentenProfil cards v1' not in s:
        s=s.replace('</style>',MODERN_CSS+'\n</style>')
    preview.write_text(s,encoding='utf-8')

# Validation for Option B.
ps=preview.read_text(encoding='utf-8')
assert ps.count('ai-agent-card') >= 6
assert ps.count('ai-card-logo') >= 6
assert ps.count('ai-card-chips') >= 6
assert ps.count('ai-card-meta') >= 6
print('OPTION_B_OK preview_cards=',ps.count('ai-agent-card'))

# ---------- OPTION A: roll same component across production ----------
changed_files=0
card_count=0
for p in ROOT.rglob('*.html'):
    if '.git' in p.parts or p.as_posix().startswith('design-'):
        continue
    s=p.read_text(encoding='utf-8')
    original=s
    s,n=replace_cards(s,{'agent-list-card','v73agent','v73-related-card'})
    card_count+=n

    if 'agent-list-card' in s:
        s=s.replace('<div class="grid2" id="agent-grid">','<div class="grid2 modern-agent-grid" id="agent-grid">')
        s=s.replace('<div class="grid2"><a class="card agent-list-card','<div class="grid2 modern-agent-grid"><a class="card agent-list-card')
    if s!=original:
        p.write_text(s,encoding='utf-8')
        changed_files+=1

cssp=Path('assets/styles.css')
css=cssp.read_text(encoding='utf-8')
if 'AgentenIndex modern AgentenProfil cards v1' not in css:
    cssp.write_text(css+'\n'+MODERN_CSS+'\n',encoding='utf-8')

# Production validation.
idx=Path('agenten/index.html').read_text(encoding='utf-8')
home=Path('index.html').read_text(encoding='utf-8')
assert idx.count('ai-agent-card')==110, idx.count('ai-agent-card')
assert idx.count('ai-card-logo')==110
assert 'modern-agent-grid' in idx
assert home.count('ai-agent-card')>=6
assert home.count('ai-card-chips')>=6

# Every category page with agent-list-card must use modern grid.
for p in Path('agenten').glob('*/index.html'):
    s=p.read_text(encoding='utf-8')
    if 'agent-list-card' in s:
        assert 'modern-agent-grid' in s,p

print('OPTION_A_OK changed_files=',changed_files,'cards=',card_count,'index_cards=',idx.count('ai-agent-card'),'home_cards=',home.count('ai-agent-card'))
