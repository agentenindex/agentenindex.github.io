#!/usr/bin/env python3
import re,sys,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
page=ROOT/"wissen/memory/index.html"
html=page.read_text(encoding="utf-8")
errors=[]

required=[
  '<title>Memory bei KI-Agenten:',
  'name="description"',
  'rel="canonical" href="https://agentenindex.de/wissen/memory/"',
  '"@type":"Article"',
  '"@type":"FAQPage"',
  '"datePublished"',
  '"dateModified"',
  '"citation"',
  '"isBasedOn"',
  'id="arten"',
  'id="session-vs-longterm"',
  'id="rag"',
  'id="poisoning"',
  'id="datenschutz"',
  'id="checkliste"',
  'id="quellen"',
  'https://openai.github.io/openai-agents-python/sessions/',
  'https://openai.github.io/openai-agents-python/sandbox/memory/',
  'https://learn.microsoft.com/en-us/agent-framework/agents/conversations/',
  'https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html'
]
for marker in required:
    if marker not in html:
        errors.append(f"missing marker: {marker}")

if html.count("<h1") != 1:
    errors.append("page must contain exactly one H1")
if html.count('class="faq-item"') < 8:
    errors.append("page must contain at least 8 visible FAQ items")
if html.count('class="memory-sources') != 1:
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
    if words < 1800:
        errors.append(f"authority page too short: {words} words (<1800)")

description=re.search(r'<meta name="description" content="([^"]+)"',html)
if not description or not (120 <= len(description.group(1)) <= 180):
    errors.append("meta description should be 120-180 characters and complete")

for phrase in ("Session Memory","Langzeit-Memory","Memory Poisoning","RAG","unknown"):
    if phrase not in html:
        errors.append(f"missing conceptual guard: {phrase}")

if errors:
    print("MEMORY_GUIDE_VALIDATION_FAILED")
    for e in errors: print("-",e)
    sys.exit(1)

print(json.dumps({
 "status":"MEMORY_GUIDE_VALID",
 "visible_faqs":html.count('class="faq-item"'),
 "primary_source_links":html.count('rel="noopener noreferrer"'),
 "schema":["Article","FAQPage","BreadcrumbList"]
},ensure_ascii=False))
