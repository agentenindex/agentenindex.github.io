#!/usr/bin/env python3
"""Live checks for AgentenIndex after GitHub Pages deployment."""
import subprocess, tempfile, json, sys, re

BASE="https://agentenindex.de"
errors=[]
warnings=[]
results={}

def curl(url, *, follow=False, ua=None):
    with tempfile.NamedTemporaryFile() as body, tempfile.NamedTemporaryFile() as headers:
        cmd=[
            "curl","-sS","--max-time","25",
            "-o",body.name,"-D",headers.name,
            "-w","%{http_code}\t%{url_effective}\t%{redirect_url}",
        ]
        if follow:
            cmd.append("-L")
        if ua:
            cmd += ["-A",ua]
        cmd.append(url)
        p=subprocess.run(cmd,capture_output=True,text=True)
        body.seek(0); raw_body=body.read().decode("utf-8","replace")
        headers.seek(0); raw_headers=headers.read().decode("utf-8","replace")
        if p.returncode != 0:
            return {"ok":False,"error":p.stderr.strip(),"code":"000","effective":"","redirect":"","body":raw_body,"headers":raw_headers}
        parts=p.stdout.strip().split("\t")
        while len(parts)<3: parts.append("")
        return {"ok":True,"code":parts[0],"effective":parts[1],"redirect":parts[2],"body":raw_body,"headers":raw_headers}

# Canonical HTTPS endpoint.
home=curl(BASE+"/",follow=True)
results["https_apex"]={k:home[k] for k in ("ok","code","effective")}
if not home["ok"] or home["code"]!="200":
    errors.append(f"HTTPS apex failed: {home.get('error') or home}")
elif home["effective"].rstrip("/") != BASE:
    errors.append(f"HTTPS apex final URL is not canonical: {home['effective']}")
if '<link rel="canonical" href="https://agentenindex.de/"' not in home["body"] and '<link href="https://agentenindex.de/" rel="canonical"' not in home["body"]:
    errors.append("live homepage canonical tag missing or unexpected")

# HTTP must redirect to canonical HTTPS.
http=curl("http://agentenindex.de/",follow=False)
results["http_redirect"]={k:http[k] for k in ("ok","code","redirect")}
if not http["ok"] or http["code"] not in ("301","302","307","308"):
    errors.append(f"HTTP apex does not redirect: {http.get('error') or http}")
elif not http["redirect"].startswith("https://agentenindex.de/"):
    errors.append(f"HTTP apex redirects to unexpected target: {http['redirect']}")

# Key public trust resources.
resources={
    "robots":"/robots.txt",
    "sitemap":"/sitemap.xml",
    "news_sitemap":"/news-sitemap.xml",
    "llms":"/llms.txt",
    "security":"/.well-known/security.txt",
    "indexnow_key":"/e90779b71f2941be8fbdad1a3138950e.txt",
}
for key,path in resources.items():
    r=curl(BASE+path,follow=True)
    results[key]={k:r[k] for k in ("ok","code","effective")}
    if not r["ok"] or r["code"]!="200":
        errors.append(f"{path} not reachable with 200: {r.get('error') or r}")
        continue
    if key=="robots":
        for token in ("OAI-SearchBot","Claude-SearchBot","PerplexityBot","bingbot"):
            if token not in r["body"]:
                errors.append(f"live robots.txt missing {token}")
    if key=="security":
        if "Canonical: https://agentenindex.de/.well-known/security.txt" not in r["body"]:
            errors.append("live security.txt canonical missing")
        if "Contact: mailto:agenten@magenta.de" not in r["body"]:
            errors.append("live security.txt contact missing")
        if not re.search(r"(?mi)^content-type:\s*text/plain(?:;|\s|$)",r["headers"]):
            warnings.append("security.txt is not served with an explicit text/plain Content-Type")
    if key=="indexnow_key":
        if r["body"].strip()!="e90779b71f2941be8fbdad1a3138950e":
            errors.append("live IndexNow key content mismatch")

# AI/search fetchers should receive the public page normally.
for agent in ("OAI-SearchBot","Claude-SearchBot","PerplexityBot","bingbot","Googlebot"):
    r=curl(BASE+"/",follow=True,ua=agent)
    results[f"ua:{agent}"]={k:r[k] for k in ("ok","code","effective")}
    if not r["ok"] or r["code"]!="200":
        errors.append(f"{agent} cannot fetch homepage: {r.get('error') or r}")

# www is recommended by GitHub for apex custom domains. If configured, it must canonicalize.
www=curl("https://www.agentenindex.de/",follow=True)
results["www"]={k:www[k] for k in ("ok","code","effective")}
if not www["ok"]:
    warnings.append("www.agentenindex.de is not currently reachable; add a DNS CNAME to agentenindex.github.io if you want GitHub's automatic www→apex redirect")
elif www["code"]!="200":
    errors.append(f"www endpoint returns {www['code']}")
elif www["effective"].rstrip("/") != BASE:
    errors.append(f"www does not redirect to canonical apex; final URL: {www['effective']}")

# HSTS is a useful HTTPS trust signal; GitHub Pages normally sets it.
if home["ok"] and not re.search(r"(?mi)^strict-transport-security:",home["headers"]):
    warnings.append("Strict-Transport-Security header not observed on homepage")

print(json.dumps({"status":"LIVE_DOMAIN_VALID" if not errors else "LIVE_DOMAIN_FAILED","results":results,"warnings":warnings,"errors":errors},ensure_ascii=False))
for w in warnings:
    print("WARNING:",w)
if errors:
    for e in errors:
        print("ERROR:",e)
    sys.exit(1)
