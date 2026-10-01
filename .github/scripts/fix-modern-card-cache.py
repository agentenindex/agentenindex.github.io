from pathlib import Path
import re

changed=0
links=0
imgs=0

for p in Path('.').rglob('*.html'):
    if '.git' in p.parts:
        continue
    s=p.read_text(encoding='utf-8')
    old=s

    # Force browsers/CDNs to fetch the stylesheet containing the new card system.
    s=re.sub(r'/assets/styles\.css\?v=[^"\']+', '/assets/styles.css?v=7.5.0', s)
    if '/assets/styles.css"' in s:
        s=s.replace('/assets/styles.css"', '/assets/styles.css?v=7.5.0"')

    # Intrinsic dimensions prevent provider logos from exploding even before CSS is painted.
    s=re.sub(
        r'(<span class="ai-card-logo"[^>]*>\s*<img\b)(?![^>]*\bwidth=)([^>]*)(/>)',
        r'\1 width="38" height="38"\2\3',
        s,
        flags=re.I
    )
    s=re.sub(
        r'(<div class="v7p-orbit-core">\s*<img\b)(?![^>]*\bwidth=)([^>]*)(/>)',
        r'\1 width="48" height="48"\2\3',
        s,
        flags=re.I
    )

    if s!=old:
        p.write_text(s,encoding='utf-8')
        changed+=1

# Validate all production pages use one fresh stylesheet URL.
versions=set()
for p in Path('.').rglob('*.html'):
    if '.git' in p.parts or p.as_posix().startswith('design-'):
        continue
    s=p.read_text(encoding='utf-8')
    for m in re.finditer(r'/assets/styles\.css\?v=([^"\']+)',s):
        versions.add(m.group(1))
        links+=1
    imgs += s.count('class="ai-card-logo"')

assert versions=={'7.5.0'},versions
assert links>=140,links
assert imgs>=110,imgs

# Check the exact pages from the screenshot/use cases.
for fn in ['index.html','agenten/index.html','agenten/coding/index.html']:
    s=Path(fn).read_text(encoding='utf-8')
    assert '/assets/styles.css?v=7.5.0' in s,fn
    assert 'ai-agent-card' in s,fn
    assert 'width="38" height="38"' in s,fn

print('CACHE_FIX_OK', 'files',changed,'stylesheet_links',links,'agent_card_logos',imgs)
