#!/usr/bin/env python3
"""Validate AgentenIndex crawler, canonical, sitemap and trust signals."""
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import re, sys, json

ROOT=Path(__file__).resolve().parents[2]
CANONICAL_HOST="agentenindex.de"
BASE="https://agentenindex.de"
errors=[]

def read(path):
    return (ROOT/path).read_text(encoding="utf-8")

# --- CNAME / domain ---
cname=read(Path("CNAME")).strip()
if cname != CANONICAL_HOST:
    errors.append(f"CNAME must be {CANONICAL_HOST}, got {cname!r}")

# --- robots.txt ---
robots=read(Path("robots.txt"))
required_agents=(
    "OAI-SearchBot","ChatGPT-User","Claude-SearchBot","Claude-User",
    "PerplexityBot","Perplexity-User","Googlebot","bingbot"
)
for agent in required_agents:
    block=re.search(rf"(?mis)^User-agent:\s*{re.escape(agent)}\s*$([\s\S]*?)(?=^User-agent:|^Sitemap:|\Z)", robots)
    if not block:
        errors.append(f"robots.txt missing explicit {agent} group")
    elif not re.search(r"(?mi)^Allow:\s*/\s*$", block.group(1)):
        errors.append(f"robots.txt {agent} group does not Allow: /")
if "User-agent: *" not in robots or not re.search(r"(?mis)^User-agent:\s*\*\s*$([\s\S]*?)^Allow:\s*/\s*$", robots):
    errors.append("robots.txt wildcard allow missing")
if re.search(r"(?mi)^Disallow:\s*/\s*$", robots):
    errors.append("robots.txt contains sitewide Disallow: /")
for sm in (f"{BASE}/sitemap.xml",f"{BASE}/news-sitemap.xml"):
    if f"Sitemap: {sm}" not in robots:
        errors.append(f"robots.txt missing {sm}")

# --- Jekyll publication of .well-known ---
config=ROOT/"_config.yml"
if not config.exists():
    errors.append("_config.yml missing; .well-known would be excluded by Jekyll")
else:
    config_text=config.read_text(encoding="utf-8")
    if ".well-known" not in config_text or "include:" not in config_text:
        errors.append("_config.yml must explicitly include .well-known")

# --- security.txt ---
well=ROOT/".well-known"/"security.txt"
legacy=ROOT/"security.txt"
for p in (well,legacy):
    if not p.exists():
        errors.append(f"missing {p.relative_to(ROOT)}")
if well.exists():
    sec=well.read_text(encoding="utf-8")
    if legacy.exists() and legacy.read_text(encoding="utf-8") != sec:
        errors.append("root security.txt must match .well-known/security.txt")
    for marker in (
        "Contact: mailto:agenten@magenta.de",
        "Contact: https://agentenindex.de/impressum/",
        "Preferred-Languages: de, en",
        "Canonical: https://agentenindex.de/.well-known/security.txt",
    ):
        if marker not in sec:
            errors.append(f"security.txt missing {marker}")
    m=re.search(r"(?m)^Expires:\s*(\S+)\s*$",sec)
    if not m:
        errors.append("security.txt missing Expires")
    else:
        try:
            expiry=datetime.fromisoformat(m.group(1).replace("Z","+00:00"))
            if expiry <= datetime.now(timezone.utc):
                errors.append("security.txt Expires is not in the future")
        except Exception:
            errors.append("security.txt Expires is not valid ISO 8601")

# --- pages / canonical / robots meta ---
excluded_dirs={"design-next","design-modern","design-hell"}
production=[]
for p in ROOT.rglob("index.html"):
    rel=p.relative_to(ROOT)
    if rel.parts and rel.parts[0] in excluded_dirs:
        continue
    production.append(p)

expected_urls={}
for p in production:
    rel=p.relative_to(ROOT)
    if rel.as_posix()=="index.html":
        expected=f"{BASE}/"
    else:
        expected=f"{BASE}/"+"/".join(rel.parts[:-1])+"/"
    expected_urls[expected]=rel.as_posix()
    html=p.read_text(encoding="utf-8")
    cans=re.findall(r'<link\s+[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\'][^>]*>|<link\s+[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']canonical["\'][^>]*>',html,re.I)
    flat=[a or b for a,b in cans]
    if len(flat)!=1:
        errors.append(f"{rel}: expected exactly one canonical, found {len(flat)}")
    elif flat[0]!=expected:
        errors.append(f"{rel}: canonical {flat[0]} != {expected}")
    if "http://agentenindex.de" in html or "http://www.agentenindex.de" in html:
        errors.append(f"{rel}: insecure internal http URL")
    if "https://www.agentenindex.de" in html:
        errors.append(f"{rel}: www internal URL conflicts with canonical host")
    robots_meta=re.findall(r'<meta\s+[^>]*name=["\']robots["\'][^>]*content=["\']([^"\']+)["\'][^>]*>|<meta\s+[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']robots["\'][^>]*>',html,re.I)
    directives=" ".join((a or b) for a,b in robots_meta).lower()
    for bad in ("noindex","nofollow","noarchive","nocache","nosnippet"):
        if bad in directives:
            errors.append(f"{rel}: production page contains robots directive {bad}")

# Design previews must stay out of search.
for d in excluded_dirs:
    p=ROOT/d/"index.html"
    if p.exists():
        html=p.read_text(encoding="utf-8").lower()
        if 'name="robots"' not in html or "noindex" not in html:
            errors.append(f"{d}/index.html must remain noindex")

# --- main sitemap ---
sitemap=ROOT/"sitemap.xml"
try:
    root=ET.parse(sitemap).getroot()
    ns={"sm":"http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs=[el.text.strip() for el in root.findall("sm:url/sm:loc",ns) if el.text]
except Exception as e:
    errors.append(f"sitemap.xml invalid XML: {e}")
    locs=[]

if len(locs)!=len(set(locs)):
    errors.append("sitemap.xml contains duplicate loc entries")
for loc in locs:
    u=urlparse(loc)
    if u.scheme!="https" or u.netloc!=CANONICAL_HOST:
        errors.append(f"sitemap non-canonical URL: {loc}")
    if u.query or u.fragment:
        errors.append(f"sitemap URL has query/fragment: {loc}")

missing_from_sitemap=sorted(set(expected_urls)-set(locs))
extra_in_sitemap=sorted(set(locs)-set(expected_urls))
for loc in missing_from_sitemap:
    errors.append(f"indexable page missing from sitemap: {loc} ({expected_urls[loc]})")
for loc in extra_in_sitemap:
    errors.append(f"sitemap URL has no production index.html: {loc}")

# --- news sitemap ---
try:
    nroot=ET.parse(ROOT/"news-sitemap.xml").getroot()
    nns={"sm":"http://www.sitemaps.org/schemas/sitemap/0.9"}
    nlocs=[el.text.strip() for el in nroot.findall("sm:url/sm:loc",nns) if el.text]
except Exception as e:
    errors.append(f"news-sitemap.xml invalid XML: {e}")
    nlocs=[]
if len(nlocs)!=len(set(nlocs)):
    errors.append("news-sitemap.xml contains duplicate loc entries")
for loc in nlocs:
    if loc not in locs:
        errors.append(f"news sitemap URL missing from main sitemap: {loc}")
    if not loc.startswith(f"{BASE}/aktuelles/"):
        errors.append(f"news sitemap URL outside /aktuelles/: {loc}")

# --- llms / internal host consistency ---
llms=read(Path("llms.txt"))
for marker in (
    f"{BASE}/",
    f"{BASE}/sitemap.xml",
    f"{BASE}/news-sitemap.xml",
    f"{BASE}/.well-known/security.txt",
):
    if marker not in llms:
        errors.append(f"llms.txt missing {marker}")
if "http://agentenindex.de" in llms or "https://www.agentenindex.de" in llms:
    errors.append("llms.txt contains non-canonical internal host")

if errors:
    print("CRAWLER_TRUST_VALIDATION_FAILED")
    for e in errors[:250]:
        print("-",e)
    if len(errors)>250:
        print(f"... {len(errors)-250} more")
    sys.exit(1)

print(json.dumps({
    "status":"CRAWLER_TRUST_VALID",
    "canonical_host":CANONICAL_HOST,
    "production_pages":len(production),
    "sitemap_urls":len(locs),
    "news_urls":len(nlocs),
    "ai_search_agents":list(required_agents[:6]),
    "security_txt":True,
},ensure_ascii=False))
