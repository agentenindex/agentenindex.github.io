from pathlib import Path
import json,re,xml.etree.ElementTree as ET

ROOT=Path('.')
CSS_MARK='AgentenFinder v1 / AgentenIndex v8.2'

# CSS.
cssp=Path('assets/styles.css')
styles=cssp.read_text(encoding='utf-8')
if CSS_MARK not in styles:
    styles += "\n/* =========================================================\n   AgentenFinder v1 / AgentenIndex v8.2\n   ========================================================= */\n.nav a.nav-finder{\n  color:#1769ff;\n  font-weight:820;\n}\n.nav a.nav-finder[aria-current=\"page\"]{\n  background:#eef5ff;\n  border-radius:10px;\n  padding:8px 10px;\n}\n\n.finder-hero{padding:46px 0 30px}\n.finder-hero-grid{\n  display:grid;\n  grid-template-columns:minmax(0,1.08fr) minmax(360px,.72fr);\n  gap:46px;\n  align-items:center;\n  padding:48px;\n  background:\n    radial-gradient(circle at 88% 14%,rgba(64,130,255,.12),transparent 26%),\n    radial-gradient(circle at 8% 92%,rgba(26,187,150,.08),transparent 24%),\n    #fff;\n  border:1px solid #e3e9f2;\n  border-radius:32px;\n  box-shadow:0 20px 62px rgba(34,61,98,.06);\n}\n.finder-hero h1{\n  margin:12px 0 22px;\n  max-width:820px;\n  font-size:clamp(3.1rem,5.6vw,5.6rem);\n  line-height:.96;\n  letter-spacing:-.065em;\n}\n.finder-lead{\n  max-width:790px;\n  color:#58667e;\n  font-size:1.08rem;\n  line-height:1.65;\n}\n.finder-trust{\n  display:flex;\n  flex-wrap:wrap;\n  gap:8px;\n  margin-top:24px;\n}\n.finder-trust span{\n  padding:7px 10px;\n  border:1px solid #e3e9f2;\n  border-radius:999px;\n  background:rgba(255,255,255,.8);\n  color:#617087;\n  font-size:.7rem;\n}\n.finder-hero-card{\n  display:grid;\n  grid-template-columns:42px 1fr;\n  gap:8px 13px;\n  padding:28px;\n  border:1px solid #e0e8f2;\n  border-radius:24px;\n  background:linear-gradient(145deg,#f8fbff,#f4fbf8);\n  box-shadow:0 13px 38px rgba(34,61,98,.05);\n}\n.finder-step-no{\n  grid-row:span 2;\n  width:34px;\n  height:34px;\n  display:grid;\n  place-items:center;\n  border-radius:11px;\n  background:linear-gradient(135deg,#1769ff,#00a98f);\n  color:#fff;\n  font:800 .64rem ui-monospace,SFMono-Regular,Menlo,monospace;\n}\n.finder-hero-card b{font-size:.88rem;color:#17233e}\n.finder-hero-card p{margin:0 0 15px;color:#68758c;font-size:.76rem}\n\n.finder-tool-section{padding:38px 0 78px}\n.finder-tool-shell{\n  overflow:hidden;\n  border:1px solid #e1e8f1;\n  border-radius:30px;\n  background:#fff;\n  box-shadow:0 22px 68px rgba(34,61,98,.065);\n}\n.finder-form{\n  padding:36px;\n  background:\n    radial-gradient(circle at 94% 5%,rgba(92,143,255,.08),transparent 24%),\n    linear-gradient(180deg,#fff,#fbfdff);\n  border-bottom:1px solid #e5ebf3;\n}\n.finder-form-head{\n  display:flex;\n  align-items:flex-start;\n  justify-content:space-between;\n  gap:24px;\n  margin-bottom:26px;\n}\n.finder-form-head h2,.finder-results-head h2{\n  margin:0;\n  font-size:clamp(2rem,3.4vw,3.2rem);\n  line-height:1;\n  letter-spacing:-.05em;\n}\n.finder-reset{\n  border:1px solid #dfe6ef;\n  border-radius:10px;\n  padding:9px 11px;\n  background:#fff;\n  color:#657188;\n  font:750 .68rem inherit;\n  cursor:pointer;\n}\n.finder-fieldset{\n  margin:0 0 24px;\n  padding:0;\n  border:0;\n}\n.finder-fieldset legend,\n.finder-input-wrap>span{\n  display:block;\n  margin-bottom:10px;\n  color:#34415a;\n  font-size:.74rem;\n  font-weight:820;\n}\n.finder-input-wrap small{\n  color:#8992a2;\n  font-weight:650;\n}\n.finder-choice-grid{\n  display:grid;\n  grid-template-columns:repeat(3,minmax(0,1fr));\n  gap:10px;\n}\n.finder-choice-grid button{\n  min-height:96px;\n  padding:16px;\n  text-align:left;\n  border:1px solid #e2e8f1;\n  border-radius:16px;\n  background:#fff;\n  color:#1c2945;\n  cursor:pointer;\n  transition:.17s ease;\n}\n.finder-choice-grid button:nth-child(1){background:linear-gradient(145deg,#fff,#effaf5)}\n.finder-choice-grid button:nth-child(2){background:linear-gradient(145deg,#fff,#eef5ff)}\n.finder-choice-grid button:nth-child(3){background:linear-gradient(145deg,#fff,#fff5ea)}\n.finder-choice-grid button:nth-child(4){background:linear-gradient(145deg,#fff,#f3f6ff)}\n.finder-choice-grid button:nth-child(5){background:linear-gradient(145deg,#fff,#f7f0ff)}\n.finder-choice-grid button:nth-child(6){background:linear-gradient(145deg,#fff,#fbf5e9)}\n.finder-choice-grid button:hover{transform:translateY(-2px);box-shadow:0 10px 28px rgba(34,61,98,.06)}\n.finder-choice-grid button[aria-pressed=\"true\"]{\n  border-color:#1769ff;\n  box-shadow:0 0 0 3px rgba(23,105,255,.10),0 12px 30px rgba(23,105,255,.08);\n}\n.finder-choice-grid b{display:block;margin-bottom:4px;font-size:.87rem}\n.finder-choice-grid span{display:block;color:#6a758a;font-size:.68rem;line-height:1.4}\n\n.finder-segmented{\n  display:inline-flex;\n  gap:5px;\n  padding:5px;\n  border:1px solid #e1e7f0;\n  border-radius:14px;\n  background:#f7f9fc;\n}\n.finder-segmented button{\n  border:0;\n  border-radius:10px;\n  padding:10px 14px;\n  background:transparent;\n  color:#5c687f;\n  font:780 .73rem inherit;\n  cursor:pointer;\n}\n.finder-segmented button[aria-pressed=\"true\"]{\n  background:#fff;\n  color:#1764dc;\n  box-shadow:0 5px 16px rgba(34,61,98,.08);\n}\n\n.finder-fields-row{\n  display:grid;\n  grid-template-columns:1.4fr .8fr;\n  gap:12px;\n  margin-top:8px;\n}\n.finder-input-wrap input,.finder-input-wrap select{\n  width:100%;\n  min-height:50px;\n  border:1px solid #dfe6ef;\n  border-radius:13px;\n  background:#fff;\n  color:#17223d;\n  padding:0 14px;\n  font:inherit;\n  font-size:.82rem;\n  outline:none;\n  box-shadow:0 7px 20px rgba(34,61,98,.025);\n}\n.finder-input-wrap input:focus,.finder-input-wrap select:focus{\n  border-color:#1769ff;\n  box-shadow:0 0 0 3px rgba(23,105,255,.10);\n}\n.finder-form-actions{\n  display:flex;\n  align-items:center;\n  gap:16px;\n  margin-top:22px;\n}\n.finder-submit{\n  min-height:50px;\n  padding:0 18px;\n  border:0;\n  border-radius:12px;\n  background:linear-gradient(135deg,#1769ff,#0d87ff);\n  color:#fff;\n  font:820 .79rem inherit;\n  cursor:pointer;\n  box-shadow:0 10px 28px rgba(23,105,255,.18);\n}\n.finder-submit:disabled{opacity:.55;cursor:wait}\n#finder-status{color:#758096;font-size:.67rem}\n\n.finder-results-head{\n  display:grid;\n  grid-template-columns:1fr minmax(280px,430px);\n  gap:34px;\n  align-items:end;\n  padding:34px 36px 24px;\n}\n.finder-results-head p{margin:0;color:#68748b;font-size:.78rem}\n.finder-results{\n  display:grid;\n  grid-template-columns:repeat(3,minmax(0,1fr));\n  gap:14px;\n  padding:0 36px 34px;\n}\n.finder-result-card{min-height:470px!important}\n.finder-match{\n  margin:0 0 15px;\n  padding:11px 12px;\n  border:1px solid color-mix(in srgb,var(--ai-accent) 13%,#e7ebf2);\n  border-radius:13px;\n  background:color-mix(in srgb,var(--ai-soft) 68%,#fff);\n}\n.finder-match small{\n  display:block;\n  margin-bottom:3px;\n  color:#7a8598;\n  font-size:.52rem;\n  text-transform:uppercase;\n  letter-spacing:.07em;\n}\n.finder-match b{\n  display:block;\n  color:var(--ai-deep);\n  font-size:.66rem;\n  line-height:1.35;\n}\n.finder-placeholder,.finder-empty{\n  grid-column:1/-1;\n  padding:44px;\n  text-align:center;\n  border:1px dashed #d8e1ed;\n  border-radius:22px;\n  background:#f8fbff;\n}\n.finder-placeholder span{\n  display:grid;\n  place-items:center;\n  width:42px;height:42px;\n  margin:0 auto 12px;\n  border-radius:13px;\n  background:#1769ff;\n  color:#fff;\n  font:800 .68rem ui-monospace,SFMono-Regular,Menlo,monospace;\n}\n.finder-placeholder b,.finder-empty b{display:block;color:#1b2944}\n.finder-placeholder p,.finder-empty p{margin:6px auto 0;max-width:620px;color:#718096;font-size:.78rem}\n.finder-empty a{display:inline-block;margin-top:13px;color:#1769ff;font-weight:820;font-size:.75rem}\n.finder-more-wrap{padding:0 36px 34px;text-align:center}\n\n.finder-explain{\n  background:linear-gradient(180deg,#f4f9ff,#fbfdff);\n  border-block:1px solid #e4ebf4;\n}\n.finder-method-grid{\n  display:grid;\n  grid-template-columns:repeat(4,minmax(0,1fr));\n  gap:12px;\n}\n.finder-method-grid article{\n  padding:24px;\n  border:1px solid #e2e8f1;\n  border-radius:20px;\n  background:#fff;\n  box-shadow:0 8px 26px rgba(34,61,98,.035);\n}\n.finder-method-grid span{\n  display:inline-flex;\n  margin-bottom:18px;\n  color:#1764dc;\n  font:800 .65rem ui-monospace,SFMono-Regular,Menlo,monospace;\n}\n.finder-method-grid h3{margin:0 0 8px;font-size:1rem;letter-spacing:-.025em}\n.finder-method-grid p{margin:0;color:#69758b;font-size:.76rem}\n\n.finder-category-links{\n  display:grid;\n  grid-template-columns:repeat(3,minmax(0,1fr));\n  gap:11px;\n}\n.finder-category-links a{\n  min-height:96px;\n  display:flex;\n  flex-direction:column;\n  justify-content:space-between;\n  padding:20px;\n  border:1px solid #e2e8f1;\n  border-radius:18px;\n  text-decoration:none;\n  background:#fff;\n  box-shadow:0 7px 24px rgba(34,61,98,.03);\n}\n.finder-category-links a:nth-child(1){background:linear-gradient(145deg,#fff,#eefaf5)}\n.finder-category-links a:nth-child(2){background:linear-gradient(145deg,#fff,#eef5ff)}\n.finder-category-links a:nth-child(3){background:linear-gradient(145deg,#fff,#fff5ea)}\n.finder-category-links a:nth-child(4){background:linear-gradient(145deg,#fff,#f3f6ff)}\n.finder-category-links a:nth-child(5){background:linear-gradient(145deg,#fff,#f7f0ff)}\n.finder-category-links a:nth-child(6){background:linear-gradient(145deg,#fff,#fbf5e9)}\n.finder-category-links b{font-size:.92rem}\n.finder-category-links span{color:#1764dc;font-size:.7rem;font-weight:800}\n\n.finder-difference{padding-top:28px}\n.finder-difference-grid{\n  display:grid;\n  grid-template-columns:1fr 1fr;\n  gap:14px;\n}\n.finder-difference-grid article{\n  padding:34px;\n  border:1px solid #e2e8f1;\n  border-radius:24px;\n  background:#fff;\n}\n.finder-difference-grid article:first-child{\n  background:linear-gradient(145deg,#f7fbff,#eff6ff);\n}\n.finder-difference-grid article:last-child{\n  background:linear-gradient(145deg,#f7fffb,#eefaf5);\n}\n.finder-difference-grid h2{margin:0 0 12px;font-size:2rem;letter-spacing:-.045em}\n.finder-difference-grid p{color:#657188}\n.finder-difference-grid a{color:#1764dc;font-weight:820;text-decoration:none}\n\n.finder-answers{\n  background:linear-gradient(180deg,#f8fafc,#f4f7fb);\n  border-top:1px solid #e5eaf2;\n}\n.finder-answer-grid{\n  display:grid;\n  grid-template-columns:repeat(2,minmax(0,1fr));\n  gap:12px;\n}\n.finder-answer-grid article{\n  padding:25px;\n  border:1px solid #e3e9f1;\n  border-radius:20px;\n  background:#fff;\n}\n.finder-answer-grid h3{margin:0 0 8px;font-size:1rem}\n.finder-answer-grid p{margin:0;color:#68748b;font-size:.77rem}\n\n@media(max-width:1120px) and (min-width:901px){\n  .nav a[href=\"/privatpersonen/\"]{display:none}\n}\n@media(max-width:1000px){\n  .finder-hero-grid{grid-template-columns:1fr}\n  .finder-hero-card{max-width:760px}\n  .finder-results{grid-template-columns:repeat(2,minmax(0,1fr))}\n  .finder-method-grid{grid-template-columns:repeat(2,minmax(0,1fr))}\n}\n@media(max-width:900px){\n  .nav.nav-open a[href=\"/privatpersonen/\"]{display:block}\n}\n@media(max-width:700px){\n  .finder-hero{padding:28px 0 20px}\n  .finder-hero-grid{padding:27px 20px;border-radius:24px;gap:28px}\n  .finder-hero h1{font-size:clamp(2.8rem,14vw,4.3rem)}\n  .finder-form{padding:24px 18px}\n  .finder-form-head{display:block}\n  .finder-reset{margin-top:15px}\n  .finder-choice-grid{grid-template-columns:1fr 1fr}\n  .finder-fields-row{grid-template-columns:1fr}\n  .finder-form-actions{align-items:flex-start;flex-direction:column}\n  .finder-submit{width:100%}\n  .finder-results-head{grid-template-columns:1fr;padding:28px 18px 20px}\n  .finder-results{grid-template-columns:1fr;padding:0 18px 28px}\n  .finder-more-wrap{padding:0 18px 28px}\n  .finder-method-grid,.finder-category-links,.finder-difference-grid,.finder-answer-grid{grid-template-columns:1fr}\n}\n@media(max-width:460px){\n  .finder-choice-grid{grid-template-columns:1fr}\n  .finder-segmented{display:grid;grid-template-columns:1fr 1fr;width:100%}\n}\n"
cssp.write_text(styles,encoding='utf-8')

# Sitewide navigation, footer and cache bust.
changed=0
for p in ROOT.rglob('*.html'):
    if '.git' in p.parts or p.as_posix().startswith('design-'):
        continue
    s=p.read_text(encoding='utf-8')
    old=s

    # Add Finder to primary nav after Agenten (finder page already has it).
    if 'class="nav"' in s and 'href="/finder/"' not in s[s.find('<nav'):s.find('</nav>')+6]:
        s=s.replace('<a href="/agenten/">Agenten</a>','<a href="/agenten/">Agenten</a><a class="nav-finder" href="/finder/">Finder</a>',1)

    # Add Finder to footer if missing there.
    footer_pos=s.rfind('<footer class="footer">')
    if footer_pos>=0:
        tail=s[footer_pos:]
        if 'href="/finder/"' not in tail:
            tail=tail.replace('<a href="/agenten/">Agenten</a>','<a href="/agenten/">Agenten</a><a href="/finder/">AgentenFinder</a>',1)
            s=s[:footer_pos]+tail

    # Current editorial/site stand.
    s=s.replace('Stand 30. September 2026','Stand 1. Oktober 2026')
    s=s.replace('<b>30.09.2026</b><p>Prüfstand</p>','<b>01.10.2026</b><p>Prüfstand</p>')

    # Force fresh design.
    s=re.sub(r'/assets/styles\.css\?v=[^"\']+','/assets/styles.css?v=8.2.0',s)

    if s!=old:
        p.write_text(s,encoding='utf-8')
        changed+=1

# Home: Finder becomes the discovery CTA; Agenten-Check already has a dedicated section below.
homep=Path('index.html')
home=homep.read_text(encoding='utf-8')
home=home.replace(
    '<a class="btn secondary" href="https://check.agentenindex.de/">Agenten-Check starten →</a>',
    '<a class="btn secondary" href="/finder/">AgentenFinder starten →</a>',
    1
)
homep.write_text(home,encoding='utf-8')

# Agent index: add an explicit Finder CTA in the hero.
idxp=Path('agenten/index.html')
idx=idxp.read_text(encoding='utf-8')
needle='<div class="v73home-proof"><span>✓ 110 Profile</span><span>✓ 6 Kategorien</span><span>✓ Source-first</span><span>✓ Keine bezahlten Rankings</span></div>'
if needle in idx and 'class="v73agentindex-finder"' not in idx:
    idx=idx.replace(needle,needle+'<div class="v73agentindex-finder"><a class="btn primary" href="/finder/">AgentenFinder starten →</a></div>',1)
idxp.write_text(idx,encoding='utf-8')

# Sitemap: add the canonical Finder URL exactly once.
smp=Path('sitemap.xml')
sm=smp.read_text(encoding='utf-8')
finder_url='https://agentenindex.de/finder/'
if finder_url not in sm:
    insert='  <url><loc>https://agentenindex.de/finder/</loc><lastmod>2026-10-01</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>\n'
    sm=sm.replace('  <url><loc>https://agentenindex.de/agenten/</loc>',insert+'  <url><loc>https://agentenindex.de/agenten/</loc>',1)
smp.write_text(sm,encoding='utf-8')

# llms.txt: concise discovery entries for Finder and method data.
lp=Path('llms.txt')
ll=lp.read_text(encoding='utf-8')
if '- https://agentenindex.de/finder/' not in ll:
    ll=ll.replace(
        '- https://agentenindex.de/agenten/ — Verzeichnis aller 110 Agenten und Plattformen\n',
        '- https://agentenindex.de/agenten/ — Verzeichnis aller 110 Agenten und Plattformen\n'
        '- https://agentenindex.de/finder/ — AgentenFinder: regelbasierte Vorauswahl passender KI-Agenten aus den strukturierten AgentenProfilen\n',
        1
    )
if '/data/finder-methodology.json' not in ll:
    ll=ll.replace(
        '- https://agentenindex.de/data/agents.json — strukturierter Datensatz mit 110 AgentenProfilen, Quellenstatus, Prüfdatum und Changelog\n',
        '- https://agentenindex.de/data/agents.json — strukturierter Datensatz mit 110 AgentenProfilen, Quellenstatus, Prüfdatum und Changelog\n'
        '- https://agentenindex.de/data/finder-methodology.json — maschinenlesbare Regeln und Gewichtung des AgentenFinders\n',
        1
    )
lp.write_text(ll,encoding='utf-8')

# Machine-readable transparent methodology matching assets/finder.js.
method={
  "name":"AgentenFinder",
  "version":"1.0",
  "updated":"2026-10-01",
  "url":"https://agentenindex.de/finder/",
  "source_dataset":"https://agentenindex.de/data/agents.json",
  "agent_count":110,
  "engine":"deterministic_client_side",
  "purpose":"Vorauswahl von KI-Agenten auf Basis dokumentierter AgentenProfil-Felder; keine Qualitätsbewertung und kein bezahltes Ranking.",
  "hard_filters":{
    "category":"filters.category",
    "audience":"filters.audience",
    "provider":"provider"
  },
  "text_scoring":{
    "name_or_provider":7,
    "product_type_or_category":5,
    "use_cases":6,
    "strengths":3,
    "summary":2,
    "access":1
  },
  "tie_breaker":"Bei gleichem Score alphabetisch nach Agentenname.",
  "result_limit_initial":3,
  "privacy":"Auswahl und Freitext werden nicht an einen Empfehlungsdienst gesendet; die Auswertung erfolgt im Browser auf Basis der veröffentlichten AgentenIndex-Daten.",
  "limitations":[
    "Die Vorauswahl ist keine allgemeine Qualitätsbewertung.",
    "Preise, Datenschutz, Verfügbarkeit und konkrete Eignung müssen im AgentenProfil und in den verlinkten Primärquellen geprüft werden.",
    "Nicht strukturierte Merkmale werden nicht als Auswahlkriterium erfunden."
  ]
}
Path('data/finder-methodology.json').write_text(json.dumps(method,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Validation.
assert CSS_MARK in cssp.read_text(encoding='utf-8')
assert Path('finder/index.html').exists()
finder=Path('finder/index.html').read_text(encoding='utf-8')
assert 'index,follow' in finder and 'noindex' not in finder
assert '<link rel="canonical" href="https://agentenindex.de/finder/"/>' in finder
assert 'assets/finder.js?v=1.0.0' in finder
assert finder.count('<h1>')==1
assert 'WebPage' in finder and 'BreadcrumbList' in finder

# XML validity and uniqueness.
ET.parse('sitemap.xml')
sm=Path('sitemap.xml').read_text(encoding='utf-8')
assert sm.count(finder_url)==1

# Every production page with nav should expose Finder and v8.2 styles.
nav_pages=0
for p in ROOT.rglob('*.html'):
    if '.git' in p.parts or p.as_posix().startswith('design-'):
        continue
    s=p.read_text(encoding='utf-8')
    if 'class="nav"' in s:
        nav_pages+=1
        nav=s[s.find('<nav'):s.find('</nav>')+6]
        assert 'href="/finder/"' in nav,p
    if '/assets/styles.css?' in s:
        assert '/assets/styles.css?v=8.2.0' in s,p

assert '/finder/' in Path('llms.txt').read_text(encoding='utf-8')
assert '/data/finder-methodology.json' in Path('llms.txt').read_text(encoding='utf-8')
assert 'href="/finder/"' in Path('index.html').read_text(encoding='utf-8')
assert 'v73agentindex-finder' in Path('agenten/index.html').read_text(encoding='utf-8')
print('FINDER_ROLLOUT_READY', 'html_changed',changed,'nav_pages',nav_pages)
