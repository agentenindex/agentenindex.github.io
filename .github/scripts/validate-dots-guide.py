#!/usr/bin/env python3
import re,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
page=ROOT/"wissen/chatgpt-dots/index.html"
profile=ROOT/"agenten/chatgpt-dots/index.html"
html=page.read_text(encoding="utf-8")
profile_html=profile.read_text(encoding="utf-8")
errors=[]
required=[
 '<title>ChatGPT dots:',
 'name="description"',
 'rel="canonical" href="https://agentenindex.de/wissen/chatgpt-dots/"',
 '"@type":"Article"','"@type":"FAQPage"','"datePublished"','"dateModified"','"citation"','"isBasedOn"',
 'id="definition"','id="unterschied"','id="cloud-computer"','id="apps"','id="proactive-research"','id="scheduled"','id="memory"','id="approvals"','id="sicherheit"','id="enterprise"','id="datenschutz"','id="verfuegbarkeit"','id="vergleich"','id="checkliste"','id="quellen"','id="faq"',
 'https://help.openai.com/en/articles/20001530-getting-started-with-your-dot','https://help.openai.com/en/articles/20001529-dots-privacy-security-and-safety-faqs','https://help.openai.com/en/articles/20001554-manage-dots-in-chatgpt-workspaces',
 '/agenten/chatgpt-dots/','Always-on','Custom Rules','proaktive Recherche','unknown','EWR'
]
for marker in required:
    if marker not in html: errors.append(f"missing marker: {marker}")
if html.count("<h1") != 1: errors.append("page must contain exactly one H1")
if html.count('class="faq-item"') < 10: errors.append("page must contain at least 10 visible FAQ items")
if html.count('class="memory-sources') != 1: errors.append("page must contain one primary-source block")
if html.count('rel="noopener noreferrer"') < 3: errors.append("page must link all three OpenAI primary sources safely")
article_match=re.search(r'<article>(.*?)</article>',html,re.S)
if not article_match:
    errors.append("article body missing")
else:
    body=re.sub(r'<[^>]+>',' ',article_match.group(1))
    body=re.sub(r'&[a-zA-Z#0-9]+;',' ',body)
    words=len(re.findall(r'\b[\wÄÖÜäöüß-]+\b',body))
    if words < 2200: errors.append(f"authority page too short: {words} words (<2200)")
description=re.search(r'<meta name="description" content="([^"]+)"',html)
if not description or not (120 <= len(description.group(1)) <= 180):
    errors.append("meta description should be 120-180 characters and complete")
profile_required=['AI-0111','ChatGPT dots','https://help.openai.com/en/articles/20001530-getting-started-with-your-dot','https://help.openai.com/en/articles/20001529-dots-privacy-security-and-safety-faqs','https://help.openai.com/en/articles/20001554-manage-dots-in-chatgpt-workspaces','class="changelog" id="changelog"','href="#changelog"','/wissen/chatgpt-dots/']
for marker in profile_required:
    if marker not in profile_html: errors.append(f"profile missing marker: {marker}")
if profile_html.count("<h1") != 1: errors.append("profile must contain exactly one H1")
data=json.loads((ROOT/"data/agents.json").read_text(encoding="utf-8"))
agent=next((a for a in data["agents"] if a.get("profile_id")=="AI-0111"),None)
if not agent or agent.get("slug")!="chatgpt-dots": errors.append("AI-0111 missing or slug mismatch")
deep=json.loads((ROOT/"data/agent-deep-evidence.json").read_text(encoding="utf-8"))
entry=next((a for a in deep.get("agents",[]) if a.get("agent_id")=="AI-0111"),None)
if not entry: errors.append("AI-0111 deep evidence missing")
else:
    paths={c.get("path") for c in entry.get("claims",[])}
    for p in ("governance.human_approval","governance.custom_roles","governance.rbac","privacy.training.customer_data","identity.agent_identity","security.encryption.at_rest","security.encryption.in_transit"):
        if p not in paths: errors.append(f"deep evidence missing {p}")
if errors:
    print("DOTS_GUIDE_VALIDATION_FAILED")
    for e in errors: print("-",e)
    sys.exit(1)
print(json.dumps({"status":"DOTS_GUIDE_VALID","faqs":html.count('class="faq-item"'),"agent_id":"AI-0111","sources":3},ensure_ascii=False))
