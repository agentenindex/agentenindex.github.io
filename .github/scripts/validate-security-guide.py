#!/usr/bin/env python3
import re,sys,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
page=ROOT/"wissen/ki-agenten-sicherheit/index.html"
html=page.read_text(encoding="utf-8")
errors=[]

required=[
  '<title>KI-Agenten Sicherheit:',
  'name="description"',
  'rel="canonical" href="https://agentenindex.de/wissen/ki-agenten-sicherheit/"',
  '"@type":"Article"',
  '"@type":"FAQPage"',
  '"datePublished"',
  '"dateModified"',
  '"citation"',
  '"isBasedOn"',
  'id="checkliste"',
  'id="prompt-injection"',
  'id="mcp-a2a"',
  'id="quellen"',
  '/fit/',
  'https://www.nist.gov/',
  'https://cheatsheetseries.owasp.org/',
  'https://learn.microsoft.com/',
  'https://developers.openai.com/'
]
for marker in required:
    if marker not in html:
        errors.append(f"missing marker: {marker}")

if html.count("<h1") != 1:
    errors.append("page must contain exactly one H1")
if html.count('class="faq-item"') < 8:
    errors.append("page must contain at least 8 visible FAQ items")
if html.count('class="security-sources') != 1:
    errors.append("page must contain one primary-source block")
if html.count('rel="noopener noreferrer"') < 5:
    errors.append("page must link at least five external primary sources safely")

article_match=re.search(r'<article>(.*?)</article>',html,re.S)
if not article_match:
    errors.append("article body missing")
else:
    text=re.sub(r'<script.*?</script>',' ',article_match.group(1),flags=re.S)
    text=re.sub(r'<[^>]+>',' ',text)
    text=re.sub(r'&[a-zA-Z#0-9]+;',' ',text)
    words=len(re.findall(r'\b[\wÄÖÜäöüß-]+\b',text))
    if words < 1800:
        errors.append(f"authority page too short: {words} words (<1800)")

description=re.search(r'<meta name="description" content="([^"]+)"',html)
if not description or not (120 <= len(description.group(1)) <= 180):
    errors.append("meta description should be 120-180 characters and complete")

for bad in ("Umgang mit se\"", "Lorem ipsum"):
    if bad in html:
        errors.append(f"truncated/placeholder content found: {bad}")

if errors:
    print("SECURITY_GUIDE_VALIDATION_FAILED")
    for e in errors: print("-",e)
    sys.exit(1)

print(json.dumps({
 "status":"SECURITY_GUIDE_VALID",
 "visible_faqs":html.count('class="faq-item"'),
 "primary_source_links":html.count('rel="noopener noreferrer"'),
 "schema":["Article","FAQPage","BreadcrumbList"]
},ensure_ascii=False))
