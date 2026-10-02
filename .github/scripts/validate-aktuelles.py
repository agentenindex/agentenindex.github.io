#!/usr/bin/env python3
import json,re,sys
from pathlib import Path
from datetime import datetime,timedelta,timezone
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
errors=[]
data=json.loads((ROOT/"data/aktuelles.json").read_text(encoding="utf-8"))
agents=json.loads((ROOT/"data/agents.json").read_text(encoding="utf-8"))
items=data.get("items",[])
agent_slugs={a.get("slug") for a in agents.get("agents",[])}
ids=set(); slugs=set()

if not items: errors.append("Aktuelles must contain at least one item")
for item in items:
    rid=item.get("id"); slug=item.get("slug")
    if rid in ids: errors.append(f"duplicate news id: {rid}")
    if slug in slugs: errors.append(f"duplicate news slug: {slug}")
    ids.add(rid); slugs.add(slug)
    if item.get("agent_slug") not in agent_slugs: errors.append(f"{slug}: unknown agent_slug")
    body=item.get("body",[])
    words=len(" ".join(body).split())
    if not 200 <= words <= 400: errors.append(f"{slug}: editorial body must be 200-400 words, got {words}")
    src=item.get("source",{})
    if not src.get("title") or not str(src.get("url","")).startswith("https://"): errors.append(f"{slug}: primary source missing")
    for k in ("headline","description","date_published","date_modified","section","change_type","agent_id","agent_name","provider","summary"):
        if not item.get(k): errors.append(f"{slug}: missing {k}")
    page=ROOT/"aktuelles"/slug/"index.html"
    if not page.exists():
        errors.append(f"{slug}: generated article missing")
        continue
    html=page.read_text(encoding="utf-8")
    url=f"https://agentenindex.de/aktuelles/{slug}/"
    markers=[url,'"@type":"NewsArticle"','"datePublished"','"dateModified"','"author"','"publisher"','"mainEntityOfPage"','"articleSection"','"about"','"citation"',src.get("url",""),f'/agenten/{item.get("agent_slug")}/']
    for marker in markers:
        if marker not in html: errors.append(f"{slug}: article missing marker {marker}")
    if html.count("<h1") != 1: errors.append(f"{slug}: article must contain exactly one h1")

hub=(ROOT/"aktuelles/index.html").read_text(encoding="utf-8")
for slug in slugs:
    if f"/aktuelles/{slug}/" not in hub: errors.append(f"hub missing {slug}")

rss=(ROOT/"aktuelles/feed.xml").read_text(encoding="utf-8")
for slug in slugs:
    if f"https://agentenindex.de/aktuelles/{slug}/" not in rss: errors.append(f"RSS missing {slug}")
try: ET.fromstring(rss)
except Exception as e: errors.append(f"RSS XML invalid: {e}")

sitemap=(ROOT/"sitemap.xml").read_text(encoding="utf-8")
if "https://agentenindex.de/aktuelles/" not in sitemap: errors.append("canonical sitemap missing Aktuelles hub")
for slug in slugs:
    if f"https://agentenindex.de/aktuelles/{slug}/" not in sitemap: errors.append(f"canonical sitemap missing {slug}")

news=(ROOT/"news-sitemap.xml").read_text(encoding="utf-8")
try: ET.fromstring(news)
except Exception as e: errors.append(f"News sitemap XML invalid: {e}")
as_of=datetime.fromisoformat(data["updated"]+"T23:59:59+00:00")
recent=set()
for item in items:
    d=datetime.fromisoformat(item["date_published"]).astimezone(timezone.utc)
    if d >= as_of-timedelta(days=2): recent.add(item["slug"])
for slug in recent:
    if f"https://agentenindex.de/aktuelles/{slug}/" not in news: errors.append(f"News sitemap missing recent {slug}")

robots=(ROOT/"robots.txt").read_text(encoding="utf-8")
if "https://agentenindex.de/news-sitemap.xml" not in robots: errors.append("robots.txt missing News sitemap")

llms=(ROOT/"llms.txt").read_text(encoding="utf-8")
for marker in ("https://agentenindex.de/aktuelles/","https://agentenindex.de/data/aktuelles.json"):
    if marker not in llms: errors.append(f"llms.txt missing {marker}")

if errors:
    print("AKTUELLES_VALIDATION_FAILED")
    for e in errors: print("-",e)
    sys.exit(1)
print(json.dumps({"status":"AKTUELLES_VALID","items":len(items),"recent_news_sitemap_items":len(recent),"editorial_word_range":"200-400","schema":"NewsArticle"},ensure_ascii=False))
