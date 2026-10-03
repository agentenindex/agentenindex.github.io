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
SYSTEM_SCHEMA_PATH=ROOT/"data"/"agent-system-schema.json"
SYSTEM_RELATIONS_PATH=ROOT/"data"/"agent-system-relations.json"
SYSTEM_SCHEMA_SOURCE=json.loads(SYSTEM_SCHEMA_PATH.read_text(encoding="utf-8")) if SYSTEM_SCHEMA_PATH.exists() else {"entity_types":{},"relation_types":{}}
SYSTEM_RELATIONS_SOURCE=json.loads(SYSTEM_RELATIONS_PATH.read_text(encoding="utf-8")) if SYSTEM_RELATIONS_PATH.exists() else {"entities":[],"relations":[]}

def load(name):
    return json.loads((OUT/name).read_text(encoding="utf-8"))

manifest=load("manifest.json")
entities=load("entities.json")
sources=load("sources.json")
assertions=load("assertions.json")
events=load("events.json")
coverage=load("coverage.json")
deep_coverage=load("deep-coverage.json")
research_priority=load("research-priority.json")
system_schema=load("system-schema.json")
relations=load("relations.json")
snapshot=json.loads((OUT/"snapshots"/"current.json").read_text(encoding="utf-8"))

errors=[]

agent_ids={a["profile_id"] for a in DATA["agents"]}
lifecycle_by_agent={a["profile_id"]:a.get("lifecycle_status","active") for a in DATA["agents"]}
valid_lifecycle_statuses={"active","discontinued"}
for aid,status in lifecycle_by_agent.items():
    if status not in valid_lifecycle_statuses:
        errors.append(f"{aid}: invalid lifecycle status {status!r}")
entity_ids={a["agent_id"] for a in entities["agents"]}
provider_names={a["provider"] for a in DATA["agents"]}
source_ids={s["source_id"] for s in sources["sources"]}
source_by_url={s["url"]:s for s in sources["sources"]}
canonical_deep_paths=set((TAXONOMY.get("paths") or {}).keys())
deprecated_deep_paths=set((TAXONOMY.get("deprecated_aliases") or {}).keys())
allowed_evidence_types=set((TAXONOMY.get("evidence_model") or {}).get("evidence_types") or [])

if DATA["count"] != len(DATA.get("agents", [])):
    errors.append(f"Source count field differs from agents array: {DATA['count']} vs {len(DATA.get('agents', []))}")
if len(agent_ids) != DATA["count"]:
    errors.append("Source profile IDs are not unique")
if entity_ids != agent_ids:
    errors.append("Entity agent IDs do not match source dataset")
if len(entities["providers"]) != len(provider_names):
    errors.append("Provider entity count does not match unique source providers")
if len(snapshot["agents"]) != DATA["count"]:
    errors.append("Snapshot agent count mismatch")


# Agent-system layer: exact source copy plus explicit, evidence-bound relations only.
if system_schema != SYSTEM_SCHEMA_SOURCE:
    errors.append("Generated system-schema.json differs from data/agent-system-schema.json")
if relations.get("schema_version") != SYSTEM_RELATIONS_SOURCE.get("schema_version"):
    errors.append("System relation schema version mismatch")

# Manually curated source entries must survive generation exactly. Generated output may
# additionally contain deterministic projections from field-level-verified deep evidence.
generated_entities=relations.get("entities") or []
generated_relations=relations.get("relations") or []
for entity in SYSTEM_RELATIONS_SOURCE.get("entities",[]):
    if entity not in generated_entities:
        errors.append(f"Curated system entity missing from generated graph: {entity.get('entity_id')}")
for relation in SYSTEM_RELATIONS_SOURCE.get("relations",[]):
    if relation not in generated_relations:
        errors.append(f"Curated system relation missing from generated graph: {relation.get('relation_id')}")

valid_entity_types=set((system_schema.get("entity_types") or {}).keys())
relation_types=system_schema.get("relation_types") or {}
valid_relation_states=set(system_schema.get("relation_state_model") or [])
allowed_system_evidence=set((system_schema.get("evidence_requirements") or {}).get("evidence_types") or [])
system_entities=relations.get("entities") or []
system_relations=relations.get("relations") or []
system_entity_ids=set()
for entity in system_entities:
    eid=entity.get("entity_id")
    if not eid or eid in system_entity_ids:
        errors.append(f"Invalid/duplicate system entity id {eid}")
        continue
    system_entity_ids.add(eid)
    if entity.get("entity_type") not in valid_entity_types:
        errors.append(f"{eid}: invalid system entity type {entity.get('entity_type')}")
    if entity.get("entity_type")=="agent_component" and entity.get("component_type") not in set(system_schema.get("component_types") or []):
        errors.append(f"{eid}: invalid component_type {entity.get('component_type')}")

# Verify the protocol relation projection is a lossless view of explicit deep claims.
protocol_projection={
    "protocols.mcp.client":("COMP-PROTOCOL-MCP","mcp","client"),
    "protocols.mcp.server":("COMP-PROTOCOL-MCP","mcp","server"),
    "protocols.a2a.client":("COMP-PROTOCOL-A2A","a2a","client"),
    "protocols.a2a.server":("COMP-PROTOCOL-A2A","a2a","server"),
}
expected_projection=set()
for entry in DEEP.get("agents",[]):
    aid=entry.get("agent_id")
    for claim in entry.get("claims",[]):
        path=claim.get("path")
        if path in protocol_projection and claim.get("value") is True:
            expected_projection.add((aid,path,claim.get("scope","documented")))
generated_projection=set()
for rel in system_relations:
    if rel.get("origin")=="deep_evidence_projection":
        generated_projection.add((rel.get("subject_id"),rel.get("source_path"),rel.get("scope","documented")))
        spec=protocol_projection.get(rel.get("source_path"))
        if not spec:
            errors.append(f"{rel.get('relation_id')}: projection uses unsupported source_path {rel.get('source_path')}")
        else:
            component_id,protocol,role=spec
            if rel.get("object_id")!=component_id or rel.get("protocol")!=protocol or rel.get("role")!=role:
                errors.append(f"{rel.get('relation_id')}: protocol projection metadata mismatch")
if generated_projection != expected_projection:
    errors.append(f"Protocol projection mismatch: generated={len(generated_projection)} expected={len(expected_projection)}")
for required_component in ("COMP-PROTOCOL-MCP","COMP-PROTOCOL-A2A"):
    if required_component not in system_entity_ids:
        errors.append(f"Missing protocol component entity {required_component}")

known_relation_refs=agent_ids | system_entity_ids
relation_ids=set()
for rel in system_relations:
    rid=rel.get("relation_id")
    if not rid or rid in relation_ids:
        errors.append(f"Invalid/duplicate relation id {rid}")
        continue
    relation_ids.add(rid)
    predicate=rel.get("predicate")
    if predicate not in relation_types:
        errors.append(f"{rid}: unknown relation predicate {predicate}")
    if rel.get("subject_id") not in known_relation_refs:
        errors.append(f"{rid}: unknown subject {rel.get('subject_id')}")
    if rel.get("object_id") not in known_relation_refs:
        errors.append(f"{rid}: unknown object {rel.get('object_id')}")
    if rel.get("state") not in valid_relation_states:
        errors.append(f"{rid}: invalid relation state {rel.get('state')}")
    if not rel.get("verified_at"):
        errors.append(f"{rid}: missing verified_at")
    evidence=rel.get("evidence") or []
    if not evidence:
        errors.append(f"{rid}: relation has no explicit evidence")
    for ev in evidence:
        if not ev.get("title") or not ev.get("url"):
            errors.append(f"{rid}: relation evidence missing title/url")
        if allowed_system_evidence and ev.get("evidence_type") not in allowed_system_evidence:
            errors.append(f"{rid}: invalid relation evidence_type {ev.get('evidence_type')}")

# Deep completeness report must preserve unknown semantics.
expected_completeness_fields=list((TAXONOMY.get("completeness_profile") or {}).get("fields") or [])
if deep_coverage.get("fields") != expected_completeness_fields:
    errors.append("Deep completeness fields do not match taxonomy")
if set((deep_coverage.get("agents") or {}).keys()) != agent_ids:
    errors.append("Deep completeness agent set mismatch")
allowed_states={"documented_true_or_value","documented_false","unknown"}
for aid, report in (deep_coverage.get("agents") or {}).items():
    states=report.get("states") or {}
    if set(states.keys()) != set(expected_completeness_fields):
        errors.append(f"{aid}: deep completeness state fields mismatch")
    bad={state for state in states.values() if state not in allowed_states}
    if bad:
        errors.append(f"{aid}: invalid deep completeness states {sorted(bad)}")
    if report.get("unknown_fields") != sum(1 for state in states.values() if state=="unknown"):
        errors.append(f"{aid}: unknown field count mismatch")

# Research priority report must stay aligned with deep coverage.
rp_agents=research_priority.get("agents") or []
if {item.get("agent_id") for item in rp_agents} != agent_ids:
    errors.append("Research priority agent set mismatch")
target=research_priority.get("target") or {}
if target.get("core_fields") != len(expected_completeness_fields):
    errors.append("Research priority core field count mismatch")
if target.get("minimum_core_coverage_pct") != 40:
    errors.append("Research priority minimum coverage target must be 40")
valid_priorities={"P0_raise_existing_to_40pct","P1_start_zero_coverage","P2_maintain_or_deepen","P3_discontinued"}
deep_agent_ids={entry.get("agent_id") for entry in DEEP.get("agents",[])}
for item in rp_agents:
    aid=item.get("agent_id")
    if item.get("priority") not in valid_priorities:
        errors.append(f"{aid}: invalid research priority {item.get('priority')}")
    report=(deep_coverage.get("agents") or {}).get(aid) or {}
    lifecycle_status=lifecycle_by_agent.get(aid,"active")
    if item.get("lifecycle_status") != lifecycle_status:
        errors.append(f"{aid}: research priority lifecycle status mismatch")
    if item.get("documented_fields") != report.get("documented_fields"):
        errors.append(f"{aid}: research priority documented count mismatch")
    if item.get("unknown_fields") != report.get("unknown_fields"):
        errors.append(f"{aid}: research priority unknown count mismatch")
    if lifecycle_status=="discontinued":
        if item.get("priority")!="P3_discontinued":
            errors.append(f"{aid}: discontinued agent not marked P3")
    else:
        if aid in deep_agent_ids and report.get("coverage_pct",0) < 40 and item.get("priority")!="P0_raise_existing_to_40pct":
            errors.append(f"{aid}: below-target deep agent not marked P0")
        if aid not in deep_agent_ids and item.get("priority")!="P1_start_zero_coverage":
            errors.append(f"{aid}: zero-coverage active agent not marked P1")

    score=item.get("priority_score")
    if not isinstance(score,(int,float)) or isinstance(score,bool) or not (0 <= score <= 100):
        errors.append(f"{aid}: invalid priority score {score!r}")

    source_hints=item.get("available_primary_sources") or []
    hint_urls=[]
    for hint in source_hints:
        if not isinstance(hint,dict) or not hint.get("title") or not hint.get("url") or hint.get("origin") not in {"profile_source","field_level_evidence"}:
            errors.append(f"{aid}: malformed research source hint {hint!r}")
            continue
        hint_urls.append(hint["url"])
        if hint["url"] not in source_by_url:
            errors.append(f"{aid}: research source hint not present in source registry {hint['url']}")
    if len(hint_urls) != len(set(hint_urls)):
        errors.append(f"{aid}: duplicate research source hint URL")

    expected_fields_needed=0 if lifecycle_status=="discontinued" else max(0,target.get("minimum_documented_fields",0)-report.get("documented_fields",0))
    if item.get("fields_needed_for_40pct") != expected_fields_needed:
        errors.append(f"{aid}: fields_needed_for_40pct mismatch")

    tier_base={"P0_raise_existing_to_40pct":80.0,"P1_start_zero_coverage":60.0,"P2_maintain_or_deepen":20.0,"P3_discontinued":0.0}
    if lifecycle_status=="discontinued":
        gap_component=0.0
        unknown_component=0.0
        source_component=0.0
        expected_score=0.0
    else:
        gap_component=round((expected_fields_needed/max(1,target.get("minimum_documented_fields",1)))*10.0,2)
        unknown_component=round((report.get("unknown_fields",0)/max(1,len(expected_completeness_fields)))*5.0,2)
        source_component=float(min(5,len(source_hints)))
        expected_score=round(min(100.0,tier_base.get(item.get("priority"),0)+gap_component+unknown_component+source_component),2)
    if score != expected_score:
        errors.append(f"{aid}: priority score {score!r} != reproducible score {expected_score}")

    recommended=item.get("recommended_unknown_paths") or []
    if lifecycle_status=="discontinued" and recommended:
        errors.append(f"{aid}: discontinued agent must not have active research recommendations")
    if lifecycle_status=="discontinued" and (item.get("research_hints") or []):
        errors.append(f"{aid}: discontinued agent must not have active research hints")
    states=report.get("states") or {}
    if any(states.get(path)!="unknown" for path in recommended):
        errors.append(f"{aid}: recommended research path is not unknown")
    for hint in item.get("research_hints") or []:
        path=hint.get("path") if isinstance(hint,dict) else None
        if path not in recommended:
            errors.append(f"{aid}: research hint path {path!r} not in recommended_unknown_paths")
        if not isinstance(hint,dict) or not hint.get("suggested_query"):
            errors.append(f"{aid}: malformed research field hint {hint!r}")

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
            evidence_type=ev.get("evidence_type")
            if not evidence_type:
                errors.append(f"{aid} {path}: evidence item missing evidence_type")
            elif allowed_evidence_types and evidence_type not in allowed_evidence_types:
                errors.append(f"{aid} {path}: invalid evidence_type {evidence_type}")
            for optional_key in ("source_section","product_version"):
                if optional_key in ev and (not isinstance(ev.get(optional_key),str) or not ev.get(optional_key).strip()):
                    errors.append(f"{aid} {path}: invalid {optional_key}")

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
    "system_entities":len(system_entities),
    "system_relations":len(system_relations),
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
    "system_entities":len(system_entities),
    "system_relations":len(system_relations),
    "snapshot":snapshot.get("observed_at"),
},ensure_ascii=False))
