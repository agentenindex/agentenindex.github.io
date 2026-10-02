#!/usr/bin/env python3
import re,sys,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
page=ROOT/"wissen/a2a/index.html"
html=page.read_text(encoding="utf-8")
errors=[]

required=[
  '<title>A2A-Protokoll erklärt:',
  'name="description"',
  'rel="canonical" href="https://agentenindex.de/wissen/a2a/"',
  '"@type":"Article"',
  '"@type":"FAQPage"',
  '"datePublished"',
  '"dateModified"',
  '"citation"',
  '"isBasedOn"',
  'id="agent-card"',
  'id="ablauf"',
  'id="mcp"',
  'id="sicherheit"',
  'id="checkliste"',
  'id="quellen"',
  '/fit/',
  'https://a2a-protocol.org/latest/topics/key-concepts/',
  'https://a2a-protocol.org/dev/topics/agent-discovery/',
  'https://a2a-protocol.org/dev/topics/enterprise-ready/',
  'https://a2a-protocol.org/dev/topics/a2a-and-mcp/',
  'https://www.linuxfoundation.org/'
]
for marker in required:
    if marker not in html:
        errors.append(f"missing marker: {marker}")

if html.count("<h1") != 1:
    errors.append("page must contain exactly one H1")
if html.count('class="faq-item"') < 8:
    errors.append("page must contain at least 8 visible FAQ items")
if html.count('class="a2a-sources') != 1:
    errors.append("page must contain one primary-source block")
if html.count('rel="noopener noreferrer"') < 6:
    errors.append("page must link at least six external primary sources safely")

article_match=re.search(r'<article>(.*?)</article>',html,re.S)
if not article_match:
    errors.append("article body missing")
else:
    body=re.sub(r'<script.*?</script>',' ',article_match.group(1),flags=re.S)
    body=re.sub(r'<[^>]+>',' ',body)
    body=re.sub(r'&[a-zA-Z#0-9]+;',' ',body)
    words=len(re.findall(r'\b[\wÄÖÜäöüß-]+\b',body))
    if words < 1700:
        errors.append(f"authority page too short: {words} words (<1700)")

description=re.search(r'<meta name="description" content="([^"]+)"',html)
if not description or not (120 <= len(description.group(1)) <= 180):
    errors.append("meta description should be 120-180 characters and complete")

for phrase in ("A2A und MCP lösen unterschiedliche Probleme","A2A ist kein Sicherheitszertifikat","A2A unterstützt","A2A Client","A2A Server"):
    if phrase not in html:
        errors.append(f"missing conceptual guard: {phrase}")

if errors:
    print("A2A_GUIDE_VALIDATION_FAILED")
    for e in errors: print("-",e)
    sys.exit(1)

print(json.dumps({
 "status":"A2A_GUIDE_VALID",
 "visible_faqs":html.count('class="faq-item"'),
 "primary_source_links":html.count('rel="noopener noreferrer"'),
 "schema":["Article","FAQPage","BreadcrumbList"]
},ensure_ascii=False))
