#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
WEBSITE_ID="4fb73149-d914-4ff4-acef-04b982c3b8d7"
APP=ROOT/"assets/app.js"
PRIVACY=ROOT/"datenschutz/index.html"

errors=[]
app=APP.read_text(encoding="utf-8")
privacy=PRIVACY.read_text(encoding="utf-8")

for marker in [
    "https://cloud.umami.is/script.js",
    WEBSITE_ID,
    "data-website-id",
    "dataset.domains",
    "dataset.excludeSearch='true'",
    "dataset.excludeHash='true'",
    "dataset.doNotTrack='true'",
    "agentenindex.de,www.agentenindex.de",
]:
    if marker not in app:
        errors.append(f"app.js missing analytics marker: {marker}")

for marker in [
    "Umami Analytics",
    "ohne Tracking-Cookies",
    "URL-Suchparameter",
    "Do-Not-Track",
    "Art. 6 Abs. 1 lit. f DSGVO",
    "https://docs.umami.is/docs/faq",
    "https://umami.is/umami-dpa.pdf",
    "Stand: 3. Oktober 2026",
]:
    if marker not in privacy:
        errors.append(f"privacy page missing marker: {marker}")

# The shared app.js is the single site-wide analytics integration point.
# Every public HTML page should load it; otherwise pageview coverage would silently be incomplete.
html_pages=[p for p in ROOT.rglob("*.html") if ".git" not in p.parts and "_site" not in p.parts]
excluded_exact={"google76153e357fd68b75.html"}
excluded_prefixes=("design-next/","design-hell/","design-modern/")
tracked_pages=[]
for p in html_pages:
    rel=str(p.relative_to(ROOT))
    if rel in excluded_exact or rel.startswith(excluded_prefixes):
        continue
    tracked_pages.append(p)

missing=[]
for p in tracked_pages:
    text=p.read_text(encoding="utf-8")
    if "/assets/app.js" not in text:
        missing.append(str(p.relative_to(ROOT)))

if missing:
    errors.append(f"{len(missing)} HTML pages do not load /assets/app.js: {', '.join(missing[:25])}")

# Avoid accidental duplicate direct Umami snippets in HTML pages.
duplicates=[]
for p in html_pages:
    text=p.read_text(encoding="utf-8")
    if WEBSITE_ID in text or "cloud.umami.is/script.js" in text:
        duplicates.append(str(p.relative_to(ROOT)))
if duplicates:
    errors.append(f"Direct Umami snippet found in HTML; keep integration centralized in app.js: {', '.join(duplicates[:25])}")

if errors:
    print("ANALYTICS_VALIDATION_FAILED")
    for e in errors:
        print("-",e)
    sys.exit(1)

print({
    "status":"ANALYTICS_VALID",
    "html_pages":len(html_pages),
    "tracked_pages":len(tracked_pages),
    "excluded_nonproduction_pages":len(html_pages)-len(tracked_pages),
    "integration":"assets/app.js",
    "cookies":False,
    "exclude_search":True,
    "exclude_hash":True,
    "respect_dnt":True,
})
