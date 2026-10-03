#!/usr/bin/env python3
import json,re,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
page=ROOT/"ueber/index.html"
html=page.read_text(encoding="utf-8")
errors=[]

required=[
  '<title>Über AgentenIndex:',
  'name="description"',
  'rel="canonical" href="https://agentenindex.de/ueber/"',
  '"@type":"AboutPage"',
  '"@type":"Organization"',
  '"@type":"Person"',
  '"accountablePerson":{"@id":"https://agentenindex.de/ueber/#kai-schiller"}',
  '"sameAs":["https://www.linkedin.com/in/kaischiller/"]',
  '"@type":"FAQPage"',
  '"dateModified":"2026-10-03"',
  'id="mission"',
  'id="prinzipien"',
  'id="aufnahme"',
  'id="bausteine"',
  'id="evidenz"',
  'id="auswahl"',
  'id="aktualitaet"',
  'id="unabhaengigkeit"',
  'id="offen"',
  'id="zielgruppen"',
  'id="nicht"',
  'id="faq"',
  'Source-first',
  'Unknown ist nicht false',
  'Keine bezahlten Rankings',
  '/finder/',
  '/fit/',
  '/aktuelles/',
  '/wissen/',
  '/methodik/',
  '/data/agent-deep-evidence.json',
  'https://github.com/agentenindex/agentenindex.github.io',
  'id="kai-schiller"',
  'Kooperation &amp; fachlicher Austausch',
  'https://www.linkedin.com/in/kaischiller/',
  'rel="me noopener noreferrer"'
]
for marker in required:
    if marker not in html:
        errors.append(f"missing marker: {marker}")

if html.count("<h1") != 1:
    errors.append("page must contain exactly one H1")
if html.count('class="faq-item"') < 10:
    errors.append("page must contain at least 10 visible FAQ items")
if '110 dokumentierte Agenten' in html or '110 AgentenProfile' in html:
    errors.append("stale 110-agent corpus count present")
if '111 AgentenProfile' not in html:
    errors.append("current 111-agent corpus count missing")

description=re.search(r'<meta name="description" content="([^"]+)"',html)
if not description or not (120 <= len(description.group(1)) <= 180):
    errors.append("meta description should be 120-180 characters")

article=re.search(r'<article>(.*?)</article>',html,re.S)
if not article:
    errors.append("article body missing")
else:
    body=re.sub(r'<script.*?</script>',' ',article.group(1),flags=re.S)
    body=re.sub(r'<[^>]+>',' ',body)
    body=re.sub(r'&[a-zA-Z#0-9]+;',' ',body)
    words=len(re.findall(r'\b[\wÄÖÜäöüß-]+\b',body))
    if words < 1800:
        errors.append(f"about authority page too short: {words} words (<1800)")

for phrase in ("unknown","Primärquelle","Field-Level","AgentenGraph","AgentenWache","Historie","redaktionell"):
    if phrase.lower() not in html.lower():
        errors.append(f"missing trust concept: {phrase}")

if errors:
    print("ABOUT_PAGE_VALIDATION_FAILED")
    for error in errors:
        print("-",error)
    sys.exit(1)

print(json.dumps({
    "status":"ABOUT_PAGE_VALID",
    "visible_faqs":html.count('class="faq-item"'),
    "schema":["Organization","Person","WebSite","AboutPage","FAQPage","BreadcrumbList"],
    "corpus_count":111
},ensure_ascii=False))
