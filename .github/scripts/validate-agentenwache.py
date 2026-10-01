#!/usr/bin/env python3
"""Validate AgentenWache state and review queue integrity."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
GRAPH=json.loads((ROOT/"_agentengraph"/"sources.json").read_text(encoding="utf-8"))
WATCH=ROOT/"_agentenwache"

def load(name):
    return json.loads((WATCH/name).read_text(encoding="utf-8"))

states_doc=load("source-states.json")
queue_doc=load("review-queue.json")
events_doc=load("events.json")
summary=load("last-run.json")

active_sources={s["source_id"]:s for s in GRAPH["sources"] if s.get("active")}
states={s["source_id"]:s for s in states_doc.get("states",[])}
errors=[]

if len(states_doc.get("states",[])) != len(states):
    errors.append("Duplicate source state IDs")
if set(active_sources)-set(states):
    errors.append(f"Missing states for active sources: {sorted(set(active_sources)-set(states))[:20]}")
if summary.get("active_sources") != len(active_sources):
    errors.append(f"Summary active_sources {summary.get('active_sources')} != {len(active_sources)}")

valid_queue_status={"open","reviewed_no_product_change","applied_to_agents","dismissed_noise","acknowledged"}
review_ids=set()
for item in queue_doc.get("items",[]):
    rid=item.get("review_id")
    if not rid or rid in review_ids:
        errors.append(f"Invalid/duplicate review id {rid}")
    review_ids.add(rid)
    if item.get("source_id") not in active_sources:
        errors.append(f"{rid}: unknown/inactive source {item.get('source_id')}")
    if item.get("status") not in valid_queue_status:
        errors.append(f"{rid}: invalid status {item.get('status')}")
    source=active_sources.get(item.get("source_id"))
    if source and sorted(item.get("agent_ids",[])) != sorted(source.get("agent_ids",[])):
        errors.append(f"{rid}: agent mapping differs from AgentenGraph source registry")
    if item.get("change_type") not in {"content_change","status_change","redirect_change","availability_change","availability_restored","source_unavailable"}:
        errors.append(f"{rid}: invalid change type {item.get('change_type')}")
    if item.get("severity") not in {"low","medium","high"}:
        errors.append(f"{rid}: invalid severity {item.get('severity')}")
    if "auto" in str(item.get("editorial_action","")).lower() and "not" not in str(item.get("editorial_action","")).lower():
        errors.append(f"{rid}: editorial action looks like auto-publication")

event_ids=set()
for event in events_doc.get("events",[]):
    eid=event.get("event_id")
    if not eid or eid in event_ids:
        errors.append(f"Invalid/duplicate event id {eid}")
    event_ids.add(eid)
    if event.get("source_id") not in active_sources:
        errors.append(f"{eid}: unknown/inactive source {event.get('source_id')}")
    if event.get("status") != "needs_review":
        errors.append(f"{eid}: monitor event must remain review-only")
    if event.get("policy") != "Never auto-publish as product fact.":
        errors.append(f"{eid}: safety policy missing")

successful=0
blocked_or_failed=0
for sid,src in active_sources.items():
    state=states.get(sid)
    if not state:
        continue
    if state.get("active") is not True:
        errors.append(f"{sid}: active graph source not marked active in watch state")
    if state.get("ok"):
        successful+=1
        ct=(state.get("content_type") or "").lower()
        if ("text" in ct or "html" in ct or "json" in ct or "xml" in ct or not ct) and not state.get("text_hash"):
            errors.append(f"{sid}: successful textual state has no text_hash")
    else:
        blocked_or_failed+=1

if summary.get("open_review_items") != sum(1 for i in queue_doc.get("items",[]) if i.get("status")=="open"):
    errors.append("Open review item count mismatch")

if errors:
    print("AGENTENWACHE_VALIDATION_FAILED")
    for e in errors[:100]:
        print("-",e)
    sys.exit(1)

print(json.dumps({
    "status":"AGENTENWACHE_VALID",
    "active_sources":len(active_sources),
    "successful_states":successful,
    "blocked_or_failed_states":blocked_or_failed,
    "events":len(events_doc.get("events",[])),
    "open_review_items":summary.get("open_review_items",0),
},ensure_ascii=False))
