from pathlib import Path
import re, json, io
from PIL import Image, ImageDraw
import cairosvg

ROOT=Path('.')
icon_svg=Path('assets/agentenindex-symbol-v2.svg').read_bytes()
logo_svg=Path('assets/agentenindex-logo.svg').read_bytes()

def render(svg, width, height=None):
    return cairosvg.svg2png(bytestring=svg, output_width=width, output_height=height)

def save_png(path, svg, size):
    Path(path).write_bytes(render(svg,size,size))

# Square icon assets used everywhere, including browser/search surfaces.
for size,path in [
    (16,'favicon-16x16.png'),
    (32,'favicon-32x32.png'),
    (48,'favicon-48x48.png'),
    (180,'apple-touch-icon.png'),
    (192,'favicon-192x192.png'),
    (512,'favicon-512x512.png'),
    (48,'assets/favicon.png'),
    (512,'assets/agentenindex-symbol.png'),
    (1024,'assets/agentenindex-profile-1024.png'),
    (512,'brand/AgentenIndex-Symbol-512.png'),
    (1024,'brand/AgentenIndex-Profile-GitHub-HuggingFace-1024.png'),
]:
    save_png(path,icon_svg,size)

# ICO with multiple embedded sizes.
ico_base=Image.open(io.BytesIO(render(icon_svg,256,256))).convert('RGBA')
ico_base.save('favicon.ico',format='ICO',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])

# Stable SVG favicon URLs.
Path('favicon.svg').write_bytes(icon_svg)
Path('assets/favicon.svg').write_bytes(icon_svg)

# PNG version of horizontal brand for external reuse.
Path('assets/agentenindex-logo.png').write_bytes(render(logo_svg,1800))

# New social preview.
logo=Image.open(io.BytesIO(render(logo_svg,980))).convert('RGBA')
canvas=Image.new('RGB',(1200,630),'#F7F9FC')
draw=ImageDraw.Draw(canvas,'RGBA')
draw.ellipse((860,-120,1280,300),fill=(52,126,255,20))
draw.ellipse((-150,400,280,820),fill=(12,181,148,18))
x=(1200-logo.width)//2
y=(630-logo.height)//2-5
canvas.paste(logo,(x,y),logo)
canvas.save('assets/agentenindex-og-1200x630.jpg',quality=94,optimize=True)

# Modern brand markup in header + footer.
brand_pat=re.compile(
    r'<a class="brand" href="/">\s*<img[^>]*class="brandlogo"[^>]*/>\s*'
    r'<span class="brand-wordmark">.*?</span>\s*</a>',
    re.I|re.S
)
brand_new='<a class="brand" href="/"><img alt="AgentenIndex" class="brand-full-logo" height="40" src="/assets/agentenindex-logo.svg" width="162"/></a>'

html_count=0
brand_count=0
for p in ROOT.rglob('*.html'):
    if '.git' in p.parts:
        continue
    s=p.read_text(encoding='utf-8')
    old=s
    s,n=brand_pat.subn(brand_new,s)
    brand_count+=n

    # About-page brand showcase should show the full new wordmark.
    s=re.sub(
        r'<img alt="AgentenIndex Logo"[^>]*src="/assets/agentenindex-profile-1024\.png"[^>]*/>',
        '<img alt="AgentenIndex Logo" class="brand-showcase-logo" height="420" src="/assets/agentenindex-logo.svg" width="1700"/>',
        s
    )

    # Prefer SVG favicon while retaining robust PNG/ICO fallbacks.
    favicon_block=(
        '<link rel="icon" type="image/svg+xml" href="/favicon.svg"/>'
        '<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48x48.png"/>'
        '<link rel="shortcut icon" href="/favicon.ico"/>'
        '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png"/>'
    )
    s=re.sub(
        r'<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48x48\.png"/>'
        r'<link rel="shortcut icon" href="/favicon\.ico"/>'
        r'<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon\.png"/>',
        favicon_block,s
    )
    s=re.sub(r'/assets/styles\.css\?v=[^"\']+','/assets/styles.css?v=8.1.0',s)

    if s!=old:
        p.write_text(s,encoding='utf-8')
        html_count+=1

# Manifest.
manifest={
  "name":"AgentenIndex",
  "short_name":"AgentenIndex",
  "description":"KI-Agenten verstehen, finden und vergleichen.",
  "start_url":"/",
  "display":"standalone",
  "background_color":"#f7f9fc",
  "theme_color":"#f7f9fc",
  "icons":[
    {"src":"/favicon.svg","sizes":"any","type":"image/svg+xml","purpose":"any"},
    {"src":"/favicon-192x192.png","sizes":"192x192","type":"image/png","purpose":"any"},
    {"src":"/favicon-512x512.png","sizes":"512x512","type":"image/png","purpose":"any"}
  ]
}
Path('site.webmanifest').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# CSS: brand asset replaces assembled icon+text everywhere.
cssp=Path('assets/styles.css')
css=cssp.read_text(encoding='utf-8')
block=r'''
/* AgentenIndex v8.1 brand refresh */
.brand{display:inline-flex;align-items:center;line-height:1;text-decoration:none}
.brand-full-logo{display:block;width:162px;height:auto;max-height:40px;object-fit:contain}
.footer .brand-full-logo{width:176px;max-height:44px}
.brand-showcase{grid-template-columns:minmax(300px,440px) 1fr}
.brand-showcase-logo{width:100%;height:auto;max-width:440px;object-fit:contain}
@media(max-width:700px){
  .brand-full-logo{width:146px;max-height:36px}
  .footer .brand-full-logo{width:164px}
  .brand-showcase{grid-template-columns:1fr}
  .brand-showcase-logo{max-width:390px;margin:0 auto}
}
'''
if 'AgentenIndex v8.1 brand refresh' not in css:
    css += '\n'+block
cssp.write_text(css,encoding='utf-8')

# Validate.
assert Path('favicon.svg').exists()
assert Path('favicon.ico').stat().st_size>1000
assert Path('assets/agentenindex-logo.png').stat().st_size>1000
assert Path('assets/agentenindex-og-1200x630.jpg').stat().st_size>1000
assert brand_count >= 280, brand_count
for fn in ['index.html','agenten/index.html','agenten/claude-code/index.html','wissen/index.html','ueber/index.html']:
    s=Path(fn).read_text(encoding='utf-8')
    assert '/assets/agentenindex-logo.svg' in s,fn
    assert '/favicon.svg' in s,fn
    assert '/assets/styles.css?v=8.1.0' in s,fn
assert 'agentenindex-logo.svg' in Path('ueber/index.html').read_text(encoding='utf-8')
print('BRAND_ROLLOUT_READY', 'html_files',html_count,'brand_replacements',brand_count)
