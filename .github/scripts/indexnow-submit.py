#!/usr/bin/env python3
"""Submit meaningful AgentenIndex URL changes to IndexNow."""
from __future__ import annotations
import argparse, json, subprocess, time, urllib.error, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HOST="agentenindex.de"
BASE="https://agentenindex.de"
KEY="e90779b71f2941be8fbdad1a3138950e"
KEY_LOCATION=f"{BASE}/{KEY}.txt"
ENDPOINT="https://api.indexnow.org/indexnow"
ACCEPTED={200,202}
MAX_BATCH=250
MAX_CHANGED_URLS=250
EXCLUDED_TOP={"design-next","design-modern","design-hell"}

def repo_path_to_url(path: str):
    p=Path(path)
    if not path.endswith(".html") or p.name!="index.html":
        return None
    if p.parts and p.parts[0] in EXCLUDED_TOP:
        return None
    if path=="index.html":
        return BASE+"/"
    return BASE+"/"+"/".join(p.parts[:-1])+"/"

def changed_urls(before: str, after: str):
    p=subprocess.run(["git","diff","--name-status",before,after,"--","*.html","**/*.html"],capture_output=True,text=True,check=True)
    urls=[]; urgent=[]
    for line in p.stdout.splitlines():
        parts=line.split("\t")
        if len(parts)<2: continue
        status=parts[0]
        for path in parts[1:]:
            u=repo_path_to_url(path)
            if u:
                urls.append(u)
                if status.startswith(("D","R")): urgent.append(u)
    urls=sorted(set(urls))
    if len(urls)<=MAX_CHANGED_URLS:
        return urls
    hubs={BASE+"/",BASE+"/agenten/",BASE+"/finder/",BASE+"/fit/",BASE+"/aktuelles/",BASE+"/wissen/",BASE+"/methodik/",BASE+"/ueber/",BASE+"/rss/"}
    priority=urgent+[u for u in urls if u in hubs or "/aktuelles/" in u]
    selected=[]; seen=set()
    for u in priority+urls:
        if u not in seen:
            selected.append(u); seen.add(u)
        if len(selected)>=MAX_CHANGED_URLS: break
    print(f"Changed HTML set is large ({len(urls)}); submitting {len(selected)} priority URLs. Full discovery remains covered by sitemap.xml.")
    return selected

def news_urls():
    p=ROOT/"news-sitemap.xml"
    if not p.exists(): return []
    root=ET.parse(p).getroot()
    ns={"sm":"http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [x.text.strip() for x in root.findall("sm:url/sm:loc",ns) if x.text]

def bootstrap_urls():
    hubs=[BASE+"/",BASE+"/agenten/",BASE+"/finder/",BASE+"/fit/",BASE+"/aktuelles/",BASE+"/wissen/",BASE+"/methodik/",BASE+"/ueber/",BASE+"/rss/"]
    return sorted(set(hubs+news_urls()))

def verify_key(attempts=15, delay=10):
    last=""
    for i in range(attempts):
        try:
            req=urllib.request.Request(KEY_LOCATION,headers={"User-Agent":"AgentenIndex-IndexNow/1.0"})
            with urllib.request.urlopen(req,timeout=20) as r:
                body=r.read().decode("utf-8","replace").strip()
                if r.status==200 and body==KEY:
                    print(f"IndexNow key verified live at {KEY_LOCATION}")
                    return
                last=f"HTTP {r.status}, body={body!r}"
        except Exception as e:
            last=str(e)
        if i+1<attempts: time.sleep(delay)
    raise RuntimeError(f"IndexNow key not live after retries: {last}")

def _post(batch):
    payload={"host":HOST,"key":KEY,"keyLocation":KEY_LOCATION,"urlList":batch}
    req=urllib.request.Request(ENDPOINT,data=json.dumps(payload,separators=(",",":")).encode("utf-8"),method="POST",headers={"Content-Type":"application/json; charset=utf-8","User-Agent":"AgentenIndex-IndexNow/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            return r.status,r.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e:
        return e.code,e.read().decode("utf-8","replace")

def submit(urls):
    urls=sorted(set(u for u in urls if u.startswith(BASE+"/")))
    if not urls:
        print("No changed indexable HTML URLs to submit.")
        return
    print(f"Submitting {len(urls)} URL(s) to IndexNow.")
    for start in range(0,len(urls),MAX_BATCH):
        batch=urls[start:start+MAX_BATCH]
        code=0; body=""
        for attempt in range(3):
            code,body=_post(batch)
            print(f"IndexNow batch {start//MAX_BATCH+1}, attempt {attempt+1}: HTTP {code} ({len(batch)} URLs)")
            if code in ACCEPTED: break
            if code==403 and "SiteVerificationNotCompleted" in body and attempt<2:
                print("IndexNow site verification is still pending; retrying in 30 seconds.")
                time.sleep(30); continue
            break
        if body.strip(): print(body[:1000])
        if code in ACCEPTED: continue
        if code==403 and "SiteVerificationNotCompleted" in body:
            print("IndexNow ownership verification is still pending. Leaving this run successful; a later change will retry automatically.")
            return
        raise RuntimeError(f"IndexNow submission failed with HTTP {code}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--before"); ap.add_argument("--after"); ap.add_argument("--bootstrap",action="store_true")
    args=ap.parse_args()
    verify_key()
    if args.bootstrap: urls=bootstrap_urls()
    elif args.before and args.after: urls=changed_urls(args.before,args.after)
    else: ap.error("use --bootstrap or both --before and --after")
    submit(urls)

if __name__=="__main__":
    main()
