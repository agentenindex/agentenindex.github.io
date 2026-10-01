#!/usr/bin/env python3
from pathlib import Path
from collections import Counter, defaultdict
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"_agentengraph"
DATA=json.loads((ROOT/"data"/"agents.json").read_text(encoding="utf-8"))
DEEP_PATH=ROOT/"data"/"agent-deep-evidence.json"
DEEP=json.loads(DEEP_PATH.read_text(encoding="utf-8")) if DEEP_PATH.exists() else {"schema_version":"1.0","agents":[]}
TAXONOMY_PATH=ROOT/"data"/"agent-deep-taxonomy.json"
TAXONOMY=json.loads(TAXONOMY_PATH.read_text(encoding="utf-8")) if TAXONOMY_PATH.exists() else {"paths":{},"deprecated_aliases":{}}

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
source_by_url={s["url"]:s for s in sources["sources"]}
canonical_deep_paths=set((TAXONOMY.get("paths") or {}).keys())
deprecated_deep_paths=set((TAXONOMY.get("deprecated_aliases") or {}).keys())

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

# Curated deep evidence must be explicit, deduplicated and resolve to known agents/sources.
deep_keys=set()
deep_claims=[]
for entry in DEEP.get("agents",[]):
    aid=entry.get("agent_id")
    if aid not in agent_ids:
        errors.append(f"Deep evidence references unknown agent {aid}")
    for claim in entry.get("claims",[]):
        path=claim.get("path")
        value=claim.get("value")
        key=(aid,path,json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")))
        if key in deep_keys:
            errors.append(f"Duplicate deep claim {aid} {path} {value!r}")
        deep_keys.add(key)
        deep_claims.append((aid,claim))
        if not path:
            errors.append(f"{aid}: deep claim missing path")
        elif path in deprecated_deep_paths:
            errors.append(f"{aid} {path}: deprecated deep path")
        elif canonical_deep_paths and path not in canonical_deep_paths:
            errors.append(f"{aid} {path}: path missing from canonical deep taxonomy")
        if claim.get("confidence") not in {"high","medium","low"}:
            errors.append(f"{aid} {path}: invalid confidence {claim.get('confidence')}")
        if not claim.get("verified_at"):
            errors.append(f"{aid} {path}: missing verified_at")
        if not claim.get("scope"):
            errors.append(f"{aid} {path}: missing scope")
        evidence=claim.get("evidence") or []
        if not evidence:
            errors.append(f"{aid} {path}: no field-level evidence")
        for ev in evidence:
            if not ev.get("title") or not ev.get("url"):
                errors.append(f"{aid} {path}: evidence item missing title/url")

active=[a for a in assertions["assertions"] if a.get("valid_to") is None]
if not active:
    errors.append("No active assertions")

active_by_value={(a["agent_id"],a["path"],json.dumps(a["value"],ensure_ascii=False,sort_keys=True,separators=(",",":"))):a for a in active}
for aid,claim in deep_claims:
    path=claim.get("path")
    value=claim.get("value")
    key=(aid,path,json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")))
    ast=active_by_value.get(key)
    if not ast:
        errors.append(f"{aid} {path}: deep claim missing active assertion")
        continue
    ev=ast.get("evidence") or {}
    if ev.get("binding")!="field_level" or ev.get("field_level_verified") is not True:
        errors.append(f"{aid} {path}: deep claim not field-level verified")
    expected=[]
    for item in claim.get("evidence") or []:
        src=source_by_url.get(item.get("url"))
        if not src:
            errors.append(f"{aid} {path}: deep evidence URL missing from source registry {item.get('url')}")
        else:
            expected.append(src["source_id"])
    if sorted(set(expected)) != sorted(ev.get("source_ids") or []):
        errors.append(f"{aid} {path}: field-level source binding differs from curated evidence")
    if ev.get("verified_at") != claim.get("verified_at"):
        errors.append(f"{aid} {path}: verified_at differs from curated evidence")
    if ev.get("confidence") != claim.get("confidence"):
        errors.append(f"{aid} {path}: confidence differs from curated evidence")
    if ev.get("scope") != claim.get("scope"):
        errors.append(f"{aid} {path}: scope differs from curated evidence")

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
expected_snapshot_date=max(x for x in [DATA.get("updated"),DEEP.get("updated")] if x)
if snapshot.get("observed_at") != expected_snapshot_date:
    errors.append("Current snapshot date does not match latest source/deep-evidence dataset date")

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
    "curated_deep_claims":len(deep_claims),
    "snapshot":snapshot.get("observed_at"),
},ensure_ascii=False))
