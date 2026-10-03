#!/usr/bin/env python3
"""Validate the public AgentenGraph sections in all AgentenProfiles."""
from pathlib import Path
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
DATA=json.loads((ROOT/"data"/"agents.json").read_text(encoding="utf-8"))
GRAPH=json.loads((ROOT/"_agentengraph"/"manifest.json").read_text(encoding="utf-8"))
ASSERTIONS=json.loads((ROOT/"_agentengraph"/"assertions.json").read_text(encoding="utf-8"))["assertions"]

errors=[]
baseline=GRAPH["as_of"]
active_by_agent={}
for a in ASSERTIONS:
    if a.get("valid_to") is None:
        active_by_agent.setdefault(a["agent_id"],0)
        active_by_agent[a["agent_id"]]+=1

for agent in DATA["agents"]:
    p=ROOT/"agenten"/agent["slug"]/"index.html"
    if not p.exists():
        errors.append(f"Missing profile {p}")
        continue
    s=p.read_text(encoding="utf-8")
    # Every real AgentenProfil uses the same two-column profile hero.
    if s.count("<h1") != 1:
        errors.append(f"{agent['slug']}: page must contain exactly one h1")
    for marker in (
        'class="v7p-hero"',
        'class="container v7p-hero-grid"',
        'class="v7p-hero-copy"',
        'class="v7p-passport-card"',
        'class="v7p-passport-top"',
        'class="v7p-quickfacts"',
        'class="v7p-evidence-strip"',
        'id="passport"',
    ):
        if marker not in s:
            errors.append(f"{agent['slug']}: profile layout missing {marker}")
    if f'class="v7p-passport-id">{agent["profile_id"]}<' not in s:
        errors.append(f"{agent['slug']}: hero passport id mismatch")
    if '/assets/styles.css?v=' not in s:
        errors.append(f"{agent['slug']}: versioned stylesheet link missing")

    if s.count('class="agentengraph-history"') != 1:
        errors.append(f"{agent['slug']}: graph section count != 1")
    if s.count('href="#agentengraph"') != 1:
        errors.append(f"{agent['slug']}: graph TOC link count != 1")
    if f'Strukturierte Historie von {agent["name"]}' not in s:
        errors.append(f"{agent['slug']}: graph title mismatch")
    if 'Baseline seit 1. Oktober 2026' not in s:
        errors.append(f"{agent['slug']}: baseline label missing")
    expected=f'{agent["profile_id"]} · {active_by_agent.get(agent["profile_id"],0)} aktive Aussagen'
    if expected not in s:
        errors.append(f"{agent['slug']}: assertion count mismatch expected {expected}")
    # Editorial changelog and graph history must stay separate.
    gi=s.find('class="agentengraph-history"')
    ci=s.find('class="changelog" id="changelog"')
    if gi < 0 or ci < 0 or gi > ci:
        errors.append(f"{agent['slug']}: graph history not before editorial changelog")
    # No graph section may claim exact field evidence unless graph data contains it.
    exact=sum(1 for a in ASSERTIONS if a["agent_id"]==agent["profile_id"] and a.get("valid_to") is None and (a.get("evidence") or {}).get("binding")=="field_level")
    if exact == 0 and 'Quellenbindung: Profilebene' not in s:
        errors.append(f"{agent['slug']}: missing profile-level evidence disclaimer")

if errors:
    print("AGENTENGRAPH_PROFILE_VALIDATION_FAILED")
    for e in errors[:100]:
        print("-",e)
    sys.exit(1)

print(json.dumps({
    "status":"AGENTENGRAPH_PROFILES_VALID",
    "profiles":len(DATA["agents"]),
    "baseline":baseline,
    "layout":"v7p two-column hero + passport card",
},ensure_ascii=False))
