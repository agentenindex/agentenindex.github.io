#!/usr/bin/env python3
from pathlib import Path
from collections import Counter, defaultdict
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"_agentengraph"
DATA=json.loads((ROOT/"data"/"agents.json").read_text(encoding="utf-8"))

def load(name):
    return json.loads((OUT/name).read_text(encoding="utf-8"))

manifest=load("manifest.json")
entities=load("entities.json")
sources=load("sources.json")
assertions=load("assertions.json")
events=load("events.json")
coverage=load("coverage.json")
snapshot=json.loads((OUT/"snapshots"/"current.json").read_text(encoding="utf-8"))

errors=[]

agent_ids={a["profile_id"] for a in DATA["agents"]}
entity_ids={a["agent_id"] for a in entities["agents"]}
provider_names={a["provider"] for a in DATA["agents"]}
source_ids={s["source_id"] for s in sources["sources"]}

if DATA["count"] != 110:
    errors.append(f"Expected 110 source agents, got {DATA['count']}")
if len(agent_ids) != DATA["count"]:
    errors.append("Source profile IDs are not unique")
if entity_ids != agent_ids:
    errors.append("Entity agent IDs do not match source dataset")
if len(entities["providers"]) != len(provider_names):
    errors.append("Provider entity count does not match unique source providers")
if len(snapshot["agents"]) != DATA["count"]:
    errors.append("Snapshot agent count mismatch")

active=[a for a in assertions["assertions"] if a.get("valid_to") is None]
if not active:
    errors.append("No active assertions")

# Every source reference must resolve. Exact field-level evidence must be explicit.
for a in assertions["assertions"]:
    ev=a.get("evidence") or {}
    refs=ev.get("source_ids") or []
    missing=[x for x in refs if x not in source_ids]
    if missing:
        errors.append(f"{a['assertion_id']} references missing sources {missing}")
    if ev.get("binding")=="field_level" and not ev.get("field_level_verified"):
        errors.append(f"{a['assertion_id']} field_level binding without verified flag")
    if ev.get("field_level_verified") and ev.get("binding")!="field_level":
        errors.append(f"{a['assertion_id']} verified field evidence without field_level binding")

# No duplicate active assertion for the exact same value.
active_keys=[(a["agent_id"],a["path"],a["value_hash"]) for a in active]
dups=[k for k,c in Counter(active_keys).items() if c>1]
if dups:
    errors.append(f"Duplicate active assertions: {dups[:10]}")

# Single-valued fields must have exactly one active value per agent.
single={
    "identity.name","identity.provider","classification.category",
    "classification.category_name","classification.product_type",
    "description.summary","access.description","profile.depth",
    "profile.version","verification.source_status","verification.review_status"
}
by_agent_path=defaultdict(list)
for a in active:
    by_agent_path[(a["agent_id"],a["path"])].append(a)
for aid in sorted(agent_ids):
    for path in sorted(single):
        c=len(by_agent_path[(aid,path)])
        if c != 1:
            errors.append(f"{aid} {path}: expected 1 active assertion, got {c}")

# Events and sources must reference valid agents.
for e in events["events"]:
    if e["agent_id"] not in agent_ids:
        errors.append(f"Event {e['event_id']} references unknown agent {e['agent_id']}")
for s in sources["sources"]:
    for aid in s.get("agent_ids",[]):
        if aid not in agent_ids:
            errors.append(f"Source {s['source_id']} references unknown agent {aid}")

# Manifest / coverage consistency.
expected={
    "agents":len(entities["agents"]),
    "providers":len(entities["providers"]),
    "sources":len(sources["sources"]),
    "assertions_total":len(assertions["assertions"]),
    "assertions_active":len(active),
    "events":len(events["events"]),
}
for k,v in expected.items():
    if manifest["counts"].get(k) != v:
        errors.append(f"Manifest count {k}={manifest['counts'].get(k)} expected {v}")

if coverage.get("active_assertions") != len(active):
    errors.append("Coverage active assertion count mismatch")

# v1 must not pretend exact field-level coverage already exists.
field_exact=sum(1 for a in active if (a.get("evidence") or {}).get("binding")=="field_level")
if field_exact != coverage.get("field_level_evidence_assertions"):
    errors.append("Field-level evidence count mismatch")

# Current baseline snapshot must match source dataset date.
if snapshot.get("observed_at") != DATA.get("updated"):
    errors.append("Current snapshot date does not match agents.json updated date")

if errors:
    print("AGENTENGRAPH_VALIDATION_FAILED")
    for e in errors[:100]:
        print("-",e)
    sys.exit(1)

print(json.dumps({
    "status":"AGENTENGRAPH_VALID",
    "agents":len(agent_ids),
    "providers":len(entities["providers"]),
    "sources":len(source_ids),
    "assertions_total":len(assertions["assertions"]),
    "assertions_active":len(active),
    "events":len(events["events"]),
    "field_level_evidence":field_exact,
    "snapshot":snapshot.get("observed_at"),
},ensure_ascii=False))
