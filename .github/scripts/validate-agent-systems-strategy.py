#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
errors=[]

def text(path):
    p=ROOT/path
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding="utf-8")

article=text("wissen/artificial-symbiotic-intelligence/index.html")
freigabe=text("freigabe/index.html")
home=text("index.html")
wissen=text("wissen/index.html")
methodik=text("methodik/index.html")
sitemap=text("sitemap.xml")
llms=text("llms.txt")

for marker in [
    '<link rel="canonical" href="https://agentenindex.de/wissen/artificial-symbiotic-intelligence/"/>',
    '"@type":"Article"',
    '"@type":"FAQPage"',
    'https://institute.deepmind.com/essays/artificial-symbiotic-intelligence/',
    'https://institute.deepmind.com/essays/cheaters-and-whistleblowers-in-the-agent-swarm/',
    'id="decomposable-agency"',
    'id="institutionen"',
    'id="quelle"',
    '/freigabe/',
    '/wissen/multi-agent-systeme/',
]:
    if marker not in article:
        errors.append(f"ASI article missing marker: {marker}")

for marker in [
    '<link rel="canonical" href="https://agentenindex.de/freigabe/"/>',
    '"@type":"FAQPage"',
    'unknown ≠ false',
    'id="dimensionen"',
    'id="ablauf"',
    'id="kein-score"',
    '/wissen/artificial-symbiotic-intelligence/',
]:
    if marker not in freigabe:
        errors.append(f"Freigabe page missing marker: {marker}")

for url in [
    "https://agentenindex.de/wissen/artificial-symbiotic-intelligence/",
    "https://agentenindex.de/freigabe/",
]:
    if url not in sitemap:
        errors.append(f"Sitemap missing {url}")
    if url not in llms:
        errors.append(f"llms.txt missing {url}")

for marker in [
    '/wissen/artificial-symbiotic-intelligence/',
    '/freigabe/',
    '/methodik/#systemebene',
]:
    if marker not in home:
        errors.append(f"Homepage missing systems strategy link {marker}")

if '/wissen/artificial-symbiotic-intelligence/' not in wissen:
    errors.append("Wissen hub missing ASI article")
if 'id="systemebene"' not in methodik or '/freigabe/' not in methodik:
    errors.append("Methodik missing system layer / Freigabe link")

schema=json.loads(text("data/agent-system-schema.json") or "{}")
relations=json.loads(text("data/agent-system-relations.json") or "{}")
taxonomy=json.loads(text("data/agent-deep-taxonomy.json") or "{}")
required_entities={"agent","agent_framework","agent_component","agent_system","agent_institution","human_role","organization"}
if not required_entities.issubset(set((schema.get("entity_types") or {}).keys())):
    errors.append("System schema missing required entity types")
required_relations={"uses_component","delegates_to","hands_off_to","requires_approval_from","governed_by"}
if not required_relations.issubset(set((schema.get("relation_types") or {}).keys())):
    errors.append("System schema missing required relation types")
required_signals={"model_change","tool_permission_change","memory_change","delegation_change","human_approval_change","rollback_change"}
if not required_signals.issubset(set(schema.get("watch_change_categories") or [])):
    errors.append("System schema missing required watch categories")
if "not that no relations exist" not in relations.get("principle","").lower():
    errors.append("System relations file must preserve unknown semantics")
for path in ["orchestration.delegation","orchestration.handoffs","memory.shared_across_agents","governance.rollback","governance.delegation_controls"]:
    if path not in (taxonomy.get("paths") or {}):
        errors.append(f"Deep taxonomy missing {path}")
if not (taxonomy.get("system_profile") or {}).get("fields"):
    errors.append("Deep taxonomy missing system_profile")

if errors:
    print("AGENT_SYSTEMS_STRATEGY_VALIDATION_FAILED")
    for e in errors:
        print("-",e)
    sys.exit(1)

print(json.dumps({
    "status":"AGENT_SYSTEMS_STRATEGY_VALID",
    "article":"wissen/artificial-symbiotic-intelligence/",
    "freigabe":"freigabe/",
    "entity_types":len(schema.get("entity_types") or {}),
    "relation_types":len(schema.get("relation_types") or {}),
    "watch_categories":len(schema.get("watch_change_categories") or []),
    "curated_relations":len(relations.get("relations") or []),
},ensure_ascii=False))
