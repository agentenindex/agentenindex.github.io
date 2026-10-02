#!/usr/bin/env python3
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
errors=[]
method=json.loads((ROOT/"data/fit-methodology.json").read_text(encoding="utf-8"))
tax=json.loads((ROOT/"data/agent-deep-taxonomy.json").read_text(encoding="utf-8"))
agents=json.loads((ROOT/"data/agents.json").read_text(encoding="utf-8"))
deep=json.loads((ROOT/"data/agent-deep-evidence.json").read_text(encoding="utf-8"))
html=(ROOT/"fit/index.html").read_text(encoding="utf-8")
js=(ROOT/"assets/fit.js").read_text(encoding="utf-8")
reqs=method.get("requirements",[])
ids=[r.get("id") for r in reqs]; paths=[r.get("path") for r in reqs]
if len(reqs)<10: errors.append("AgentenFit exposes too few requirements")
if len(ids)!=len(set(ids)): errors.append("Duplicate AgentenFit requirement IDs")
if len(paths)!=len(set(paths)): errors.append("Duplicate AgentenFit requirement paths")
canonical=set(tax.get("completeness_profile",{}).get("fields",[]))
for p in paths:
    if p not in canonical: errors.append(f"Fit path not in 25-field completeness profile: {p}")
html_paths=re.findall(r'data-fit-path="([^"]+)"',html)
if set(html_paths)!=set(paths): errors.append("Fit page requirement paths differ from methodology")
if len(html_paths)!=len(paths): errors.append("Fit page contains duplicate/missing requirement controls")
for marker in ["data-agentenfit","/data/agents.json","/data/agent-deep-evidence.json"]:
    target=html if marker=="data-agentenfit" else js
    if marker not in target: errors.append(f"Missing AgentenFit marker: {marker}")
for marker in ["c.value===false","state:'unknown'","lifecycle_status==='discontinued'","x.contradicted-y.contradicted","y.confirmed-x.confirmed"]:
    if marker not in js: errors.append(f"Missing AgentenFit state/ranking guard: {marker}")
if "unknown" not in method.get("state_model",{}): errors.append("Methodology lacks unknown state")
if agents.get("count")!=len(agents.get("agents",[])): errors.append("agents.json count mismatch")
deep_ids={a.get("agent_id") for a in deep.get("agents",[])}
active=[a for a in agents.get("agents",[]) if a.get("lifecycle_status")!="discontinued"]
if not active: errors.append("No active agents available")
if not deep_ids: errors.append("No deep-evidence agents available")
if errors:
    print("AGENTENFIT_VALIDATION_FAILED")
    for e in errors: print("-",e)
    sys.exit(1)
print(json.dumps({
    "status":"AGENTENFIT_VALID",
    "active_agents":len(active),
    "deep_agents":len(deep_ids),
    "requirements":len(reqs),
    "unknown_policy":"missing claim remains unknown; false requires explicit curated false claim"
},ensure_ascii=False))
