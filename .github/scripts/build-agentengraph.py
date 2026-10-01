#!/usr/bin/env python3
"""
Build AgentenGraph v1 from data/agents.json plus curated field-level deep evidence.

AgentenGraph is the internal, versioned evidence/history layer behind AgentenIndex.
It intentionally does NOT invent field-level evidence. Existing AgentenProfile
claims start with evidence.binding = "profile_source_set". Curated claims in
data/agent-deep-evidence.json are imported with evidence.binding = "field_level"
and retain their exact source, scope, confidence, and verification metadata.

Historical behavior:
- active assertions are carried forward while unchanged;
- removed/changed values are closed with valid_to;
- new values create new assertions;
- field changes generate append-only events;
- a dated snapshot establishes the state observed on each dataset date.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data" / "agents.json"
DEEP_INPUT = ROOT / "data" / "agent-deep-evidence.json"
OUT = ROOT / "_agentengraph"
SNAP = OUT / "snapshots"

GRAPH_VERSION = "1.0"
SCHEMA_VERSION = "1.0"

SINGLE_FIELDS = {
    "identity.name",
    "identity.provider",
    "classification.category",
    "classification.category_name",
    "classification.product_type",
    "description.summary",
    "access.description",
    "profile.depth",
    "profile.version",
    "verification.source_status",
    "verification.review_status",
}
MULTI_FIELDS = {
    "audience",
    "use_case",
    "editorial.strength",
    "editorial.check",
}

PLANNED_DOMAINS = [
    "capabilities",
    "autonomy",
    "models",
    "tools",
    "protocols.mcp",
    "protocols.a2a",
    "api",
    "integrations",
    "memory",
    "deployment",
    "hosting",
    "privacy.data_usage",
    "privacy.training",
    "privacy.residency",
    "security",
    "governance.sso",
    "governance.audit_logs",
    "pricing",
    "regions",
    "certifications",
]

def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")

def load(path: Path, default):
    if not path.exists():
        return deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8"))

def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "unknown"

def digest(*parts: str, length: int = 16) -> str:
    raw = "|".join(parts).encode("utf-8")
    return sha256(raw).hexdigest()[:length]

def canonical(value):
    if isinstance(value, str):
        return value.strip()
    return value

def value_hash(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()[:16]

def source_id(url: str) -> str:
    return "SRC-" + digest(url, length=14).upper()

def provider_id(name: str) -> str:
    return "PROV-" + slugify(name).upper()[:50]

def assertion_id(agent_id: str, path: str, value, first_seen: str) -> str:
    return "AST-" + digest(agent_id, path, json.dumps(value, ensure_ascii=False, sort_keys=True), first_seen, length=18).upper()

def event_id(*parts: str) -> str:
    return "EVT-" + digest(*parts, length=18).upper()

def claim_nature(path: str) -> str:
    if path.startswith("identity."):
        return "identity"
    if path.startswith("classification.") or path == "audience":
        return "editorial_classification"
    if path == "description.summary":
        return "editorial_summary"
    if path == "access.description":
        return "documented_access_note"
    if path == "use_case":
        return "editorial_use_case"
    if path == "editorial.strength":
        return "editorial_assessment"
    if path == "editorial.check":
        return "editorial_caution"
    if path.startswith("profile.") or path.startswith("verification."):
        return "verification_metadata"
    return "structured_statement"

def deep_claim_index(doc: dict):
    by_agent: dict[str, list[dict]] = defaultdict(list)
    by_key: dict[tuple[str, str, str], dict] = {}
    for entry in doc.get("agents", []):
        aid = entry.get("agent_id")
        for claim in entry.get("claims", []):
            path = claim.get("path")
            value = canonical(claim.get("value"))
            if not aid or not path or value in (None, "", []):
                continue
            rec = deepcopy(claim)
            rec["agent_id"] = aid
            rec["value"] = value
            by_agent[aid].append(rec)
            by_key[(aid, path, value_hash(value))] = rec
    return by_agent, by_key

def agent_claims(agent: dict, deep_claims: list[dict] | None = None) -> list[tuple[str, object]]:
    claims = [
        ("identity.name", agent.get("name")),
        ("identity.provider", agent.get("provider")),
        ("classification.category", agent.get("category")),
        ("classification.category_name", agent.get("category_name")),
        ("classification.product_type", agent.get("type")),
        ("description.summary", agent.get("summary")),
        ("access.description", agent.get("access")),
        ("profile.depth", agent.get("profile_depth")),
        ("profile.version", agent.get("profile_version")),
        ("verification.source_status", agent.get("source_status")),
        ("verification.review_status", agent.get("verification_status")),
    ]
    for value in (agent.get("filters") or {}).get("audience", []):
        claims.append(("audience", value))
    for value in agent.get("uses", []):
        claims.append(("use_case", value))
    for value in agent.get("strengths", []):
        claims.append(("editorial.strength", value))
    for value in agent.get("checks", []):
        claims.append(("editorial.check", value))
    for claim in deep_claims or []:
        claims.append((claim.get("path"), claim.get("value")))
    return [(p, canonical(v)) for p, v in claims if p and v not in (None, "", [])]

def snapshot_claim_map(agent: dict, deep_claims: list[dict] | None = None) -> dict[str, list]:
    out: dict[str, list] = defaultdict(list)
    for path, value in agent_claims(agent, deep_claims):
        out[path].append(value)
    return {k: sorted(v, key=lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True)) for k, v in sorted(out.items())}

def field_level_evidence(claim: dict) -> dict:
    items = []
    source_ids = []
    for ev in claim.get("evidence", []):
        url = ev.get("url")
        if not url:
            continue
        sid = source_id(url)
        source_ids.append(sid)
        item = {"source_id": sid}
        if ev.get("note"):
            item["note"] = ev["note"]
        items.append(item)
    payload = {
        "binding": "field_level",
        "source_ids": sorted(set(source_ids)),
        "field_level_verified": True,
        "verified_at": claim.get("verified_at"),
        "confidence": claim.get("confidence", "high"),
        "scope": claim.get("scope", "documented"),
        "note": claim.get("note", "Feldgenaue Zuordnung aus kuratierter Deep-Evidence-Datei."),
        "evidence_items": items,
    }
    return payload

def main():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    agents = data["agents"]
    deep = load(DEEP_INPUT, {"schema_version":"1.0","updated":data.get("updated"),"agents":[]})
    deep_by_agent, deep_by_key = deep_claim_index(deep)
    known_agent_ids = {a["profile_id"] for a in agents}
    unknown_deep_agents = sorted(set(deep_by_agent) - known_agent_ids)
    if unknown_deep_agents:
        raise SystemExit(f"Deep evidence references unknown agents: {unknown_deep_agents}")
    dates = [x for x in [data.get("updated"), deep.get("updated"), max((a.get("last_verified", "") for a in agents), default="")] if x]
    as_of = max(dates) if dates else ""
    if not as_of:
        raise SystemExit("No dataset date available")

    OUT.mkdir(parents=True, exist_ok=True)
    SNAP.mkdir(parents=True, exist_ok=True)

    old_assertions = load(OUT / "assertions.json", {"assertions": []}).get("assertions", [])
    old_events = load(OUT / "events.json", {"events": []}).get("events", [])
    old_sources = load(OUT / "sources.json", {"sources": []}).get("sources", [])
    prior_snapshot = load(SNAP / "current.json", None)

    providers = {}
    agent_entities = []
    for a in agents:
        aid = a["profile_id"]
        pid = provider_id(a["provider"])
        providers.setdefault(pid, {
            "provider_id": pid,
            "name": a["provider"],
            "slug": slugify(a["provider"]),
            "agent_ids": [],
        })
        providers[pid]["agent_ids"].append(aid)
        agent_entities.append({
            "agent_id": aid,
            "profile_id": aid,
            "slug": a["slug"],
            "name": a["name"],
            "provider_id": pid,
            "provider": a["provider"],
            "profile_url": f"https://agentenindex.de/agenten/{a['slug']}/",
            "last_verified": a.get("last_verified"),
            "profile_version": a.get("profile_version"),
            "active": True,
        })
    for p in providers.values():
        p["agent_ids"] = sorted(p["agent_ids"])

    prior_sources = {s["source_id"]: s for s in old_sources}
    seen_source_agents: dict[str, set[str]] = defaultdict(set)
    source_records = deepcopy(prior_sources)
    agent_source_ids: dict[str, list[str]] = {}

    for a in agents:
        aid = a["profile_id"]
        ids = []
        for title, url in a.get("sources", []):
            sid = source_id(url)
            ids.append(sid)
            seen_source_agents[sid].add(aid)
            if sid not in source_records:
                source_records[sid] = {
                    "source_id": sid,
                    "url": url,
                    "title": title,
                    "first_seen": as_of,
                    "last_seen": as_of,
                    "active": True,
                    "agent_ids": [],
                    "provenance": "AgentenProfil source list",
                }
            else:
                source_records[sid]["url"] = url
                source_records[sid]["title"] = title
                source_records[sid]["last_seen"] = as_of
                source_records[sid]["active"] = True
        agent_source_ids[aid] = sorted(set(ids))

        # Field-level evidence sources also live in the shared source registry,
        # but they do not broaden the source set used by unrelated profile-level claims.
        for claim in deep_by_agent.get(aid, []):
            for ev in claim.get("evidence", []):
                title = ev.get("title")
                url = ev.get("url")
                if not title or not url:
                    continue
                sid = source_id(url)
                seen_source_agents[sid].add(aid)
                if sid not in source_records:
                    source_records[sid] = {
                        "source_id": sid,
                        "url": url,
                        "title": title,
                        "first_seen": as_of,
                        "last_seen": as_of,
                        "active": True,
                        "agent_ids": [],
                        "provenance": "AgentenGraph field-level evidence",
                    }
                else:
                    source_records[sid]["url"] = url
                    source_records[sid]["title"] = title
                    source_records[sid]["last_seen"] = as_of
                    source_records[sid]["active"] = True

    for sid, rec in source_records.items():
        current_agents = seen_source_agents.get(sid, set())
        if current_agents:
            rec["agent_ids"] = sorted(current_agents)
            rec["active"] = True
            rec["last_seen"] = as_of
        elif rec.get("active"):
            rec["active"] = False

    assertions = deepcopy(old_assertions)
    active_by_key = {}
    for i, ast in enumerate(assertions):
        if ast.get("valid_to") is None:
            key = (ast["agent_id"], ast["path"], ast["value_hash"])
            active_by_key[key] = i

    current_keys = set()
    for a in agents:
        aid = a["profile_id"]
        for path, value in agent_claims(a, deep_by_agent.get(aid, [])):
            vh = value_hash(value)
            key = (aid, path, vh)
            current_keys.add(key)
            deep_claim = deep_by_key.get(key)
            evidence_default = {
                "binding": "profile_source_set",
                "source_ids": agent_source_ids[aid],
                "field_level_verified": False,
                "note": "Bestehende AgentenProfile verknüpfen Quellen derzeit auf Profilebene. Eine exakte Feld-zu-Quelle-Zuordnung wird nicht behauptet.",
            }
            evidence = field_level_evidence(deep_claim) if deep_claim else evidence_default
            verified_at = deep_claim.get("verified_at") if deep_claim else a.get("last_verified")
            origin = "data/agent-deep-evidence.json" if deep_claim else "data/agents.json"
            review_status = (deep_claim or {}).get("review_status") or a.get("verification_status")
            if key in active_by_key:
                ast = assertions[active_by_key[key]]
                ast["last_seen"] = as_of
                ast["last_verified"] = verified_at
                ast["profile_version"] = a.get("profile_version")
                if deep_claim:
                    ast["evidence"] = evidence
                    ast["origin"] = origin
                elif (ast.get("evidence") or {}).get("binding") != "field_level":
                    ast["evidence"] = evidence_default
                    ast["origin"] = origin
                ast["review_status"] = review_status
            else:
                assertions.append({
                    "assertion_id": assertion_id(aid, path, value, as_of),
                    "agent_id": aid,
                    "path": path,
                    "value": value,
                    "value_hash": vh,
                    "claim_nature": claim_nature(path),
                    "review_status": review_status,
                    "evidence": evidence,
                    "first_seen": as_of,
                    "last_seen": as_of,
                    "valid_from": as_of,
                    "valid_to": None,
                    "last_verified": verified_at,
                    "profile_version": a.get("profile_version"),
                    "origin": origin,
                })

    closed_now = []
    for ast in assertions:
        if ast.get("valid_to") is not None:
            continue
        key = (ast["agent_id"], ast["path"], ast["value_hash"])
        if key not in current_keys:
            ast["valid_to"] = as_of
            closed_now.append(ast)

    current_snapshot = {
        "graph_version": GRAPH_VERSION,
        "observed_at": as_of,
        "source_dataset": "data/agents.json",
        "source_schema_version": data.get("schema_version"),
        "agents": [{
            "agent_id": a["profile_id"],
            "slug": a["slug"],
            "last_verified": a.get("last_verified"),
            "source_ids": agent_source_ids[a["profile_id"]],
            "claims": snapshot_claim_map(a, deep_by_agent.get(a["profile_id"], [])),
        } for a in agents],
    }

    event_map = {e["event_id"]: e for e in old_events}

    for a in agents:
        aid = a["profile_id"]
        for ch in a.get("changelog", []):
            eid = event_id("profile_changelog", aid, ch.get("date",""), ch.get("type",""), ch.get("change",""))
            event_map.setdefault(eid, {
                "event_id": eid,
                "agent_id": aid,
                "date": ch.get("date"),
                "event_type": ch.get("type"),
                "scope": "profile",
                "description": ch.get("change"),
                "origin": "profile_changelog",
            })

    if prior_snapshot:
        old_map = {a["agent_id"]: a for a in prior_snapshot.get("agents", [])}
        new_map = {a["agent_id"]: a for a in current_snapshot["agents"]}
        for aid in sorted(set(old_map) | set(new_map)):
            old = old_map.get(aid)
            new = new_map.get(aid)
            if old is None:
                eid = event_id("agent_added", aid, as_of)
                event_map.setdefault(eid, {
                    "event_id": eid, "agent_id": aid, "date": as_of,
                    "event_type": "agent_added", "scope": "entity",
                    "description": "Agent erstmals im AgentenGraph beobachtet.",
                    "origin": "graph_diff",
                })
                continue
            if new is None:
                eid = event_id("agent_removed", aid, as_of)
                event_map.setdefault(eid, {
                    "event_id": eid, "agent_id": aid, "date": as_of,
                    "event_type": "agent_removed", "scope": "entity",
                    "description": "Agent ist im aktuellen Quelldatensatz nicht mehr enthalten.",
                    "origin": "graph_diff",
                })
                continue
            old_claims = old.get("claims", {})
            new_claims = new.get("claims", {})
            for path in sorted(set(old_claims) | set(new_claims)):
                before = old_claims.get(path, [])
                after = new_claims.get(path, [])
                if before == after:
                    continue
                eid = event_id("field_change", aid, path, json.dumps(before,ensure_ascii=False,sort_keys=True), json.dumps(after,ensure_ascii=False,sort_keys=True), as_of)
                event_map.setdefault(eid, {
                    "event_id": eid,
                    "agent_id": aid,
                    "date": as_of,
                    "event_type": "field_change",
                    "scope": "field",
                    "path": path,
                    "before": before,
                    "after": after,
                    "description": f"Strukturierter Wert für {path} hat sich geändert.",
                    "origin": "graph_diff",
                })
            if sorted(old.get("source_ids", [])) != sorted(new.get("source_ids", [])):
                before = sorted(old.get("source_ids", []))
                after = sorted(new.get("source_ids", []))
                eid = event_id("source_set_change", aid, json.dumps(before), json.dumps(after), as_of)
                event_map.setdefault(eid, {
                    "event_id": eid,
                    "agent_id": aid,
                    "date": as_of,
                    "event_type": "source_set_change",
                    "scope": "evidence",
                    "before": before,
                    "after": after,
                    "description": "Das Quellen-Set des AgentenProfils hat sich geändert.",
                    "origin": "graph_diff",
                })

    active_assertions = [a for a in assertions if a.get("valid_to") is None]
    by_path = Counter(a["path"] for a in active_assertions)
    field_level = sum(1 for a in active_assertions if (a.get("evidence") or {}).get("binding") == "field_level")
    profile_level = sum(1 for a in active_assertions if (a.get("evidence") or {}).get("binding") == "profile_source_set")
    agents_with_field_evidence = len({a["agent_id"] for a in active_assertions if (a.get("evidence") or {}).get("binding") == "field_level"})

    coverage = {
        "graph_version": GRAPH_VERSION,
        "as_of": as_of,
        "agents": len(agent_entities),
        "providers": len(providers),
        "active_assertions": len(active_assertions),
        "historical_assertions": len(assertions) - len(active_assertions),
        "field_level_evidence_assertions": field_level,
        "profile_level_evidence_assertions": profile_level,
        "agents_with_field_level_evidence": agents_with_field_evidence,
        "active_assertions_by_path": dict(sorted(by_path.items())),
        "planned_enrichment_domains": PLANNED_DOMAINS,
        "important_limitation": "v1 imports existing AgentenProfil structure. Existing source lists are profile-level; exact field-level source bindings must be enriched explicitly and are never inferred automatically.",
    }

    manifest = {
        "name": "AgentenGraph",
        "graph_version": GRAPH_VERSION,
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of,
        "purpose": "Interne, versionierte Evidenz- und Historienbasis für AgentenIndex.",
        "source_dataset": "data/agents.json",
        "source_schema_version": data.get("schema_version"),
        "counts": {
            "agents": len(agent_entities),
            "providers": len(providers),
            "sources": len(source_records),
            "active_sources": sum(1 for s in source_records.values() if s.get("active")),
            "assertions_total": len(assertions),
            "assertions_active": len(active_assertions),
            "events": len(event_map),
        },
        "principles": [
            "Keine unbekannten Merkmale ergänzen.",
            "Feldgenaue Evidenz nur behaupten, wenn sie explizit zugeordnet wurde.",
            "Historische Werte nicht überschreiben, sondern schließen und versionieren.",
            "Redaktionelle Einordnung von dokumentierten Produkteigenschaften trennen.",
            "Stabile IDs für Agenten, Anbieter, Quellen, Aussagen und Ereignisse verwenden.",
        ],
        "storage_note": "_agentengraph/ beginnt mit Unterstrich und ist als interner Datenkern gedacht, nicht als öffentliche API. Das GitHub-Repository selbst ist öffentlich.",
    }

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://agentenindex.de/internal/agentengraph/v1/schema",
        "title": "AgentenGraph v1 Assertion",
        "type": "object",
        "required": ["assertion_id","agent_id","path","value","value_hash","claim_nature","evidence","first_seen","last_seen","valid_from","origin"],
        "properties": {
            "assertion_id": {"type":"string","pattern":"^AST-"},
            "agent_id": {"type":"string","pattern":"^AI-[0-9]{4}$"},
            "path": {"type":"string"},
            "value": {},
            "value_hash": {"type":"string"},
            "claim_nature": {"type":"string"},
            "review_status": {"type":["string","null"]},
            "evidence": {
                "type":"object",
                "required":["binding","source_ids","field_level_verified"],
                "properties":{
                    "binding":{"enum":["profile_source_set","field_level"]},
                    "source_ids":{"type":"array","items":{"type":"string","pattern":"^SRC-"}},
                    "field_level_verified":{"type":"boolean"},
                    "note":{"type":"string"},
                    "verified_at":{"type":["string","null"],"format":"date"},
                    "confidence":{"enum":["high","medium","low"]},
                    "scope":{"type":["string","array"]},
                    "evidence_items":{"type":"array","items":{"type":"object","required":["source_id"],"properties":{"source_id":{"type":"string","pattern":"^SRC-"},"note":{"type":"string"}}}}
                }
            },
            "first_seen":{"type":"string","format":"date"},
            "last_seen":{"type":"string","format":"date"},
            "valid_from":{"type":"string","format":"date"},
            "valid_to":{"type":["string","null"],"format":"date"},
            "last_verified":{"type":["string","null"],"format":"date"},
            "profile_version":{"type":["string","null"]},
            "origin":{"type":"string"}
        }
    }

    readme = f"""# AgentenGraph v{GRAPH_VERSION}

AgentenGraph ist der interne, versionierte Datenkern von AgentenIndex.

## Warum er existiert

'data/agents.json' bleibt die kompakte, veröffentlichte Produkt- und Finder-Datenbasis.
AgentenGraph ergänzt diese Daten sowie `data/agent-deep-evidence.json` um stabile Entitäten, Aussagen (assertions),
Quellen, Historie und Änderungsereignisse.

Der wichtigste Unterschied: Ein Wert wird künftig nicht einfach überschrieben.
Wenn sich ein strukturiertes Feld ändert, wird die alte Assertion geschlossen und
eine neue Assertion mit neuem Gültigkeitsbeginn erzeugt. Zusätzlich entsteht ein
field_change-Event.

## Evidenz in v1

Die bestehenden AgentenProfile besitzen Quellenlisten auf Profilebene. Deshalb
werden Profil-Assertions nicht künstlich als feldgenau verifiziert. Kuratierte Deep-Evidence-Claims werden dagegen explizit feldgenau gebunden.
Sie starten mit:

- evidence.binding = "profile_source_set"
- field_level_verified = false

Wenn später eine konkrete Quelle einem konkreten Feld zugeordnet wird, kann die
Assertion auf binding = "field_level" gesetzt werden. Der Builder bewahrt diese
manuelle Zuordnung bei späteren Builds.

## Dateien

- manifest.json — Version, Prinzipien und Zähler
- entities.json — Agenten und Anbieter
- sources.json — deduplizierte Quellen mit stabilen IDs
- assertions.json — aktuelle und historische strukturierte Aussagen
- events.json — Profil-Changelog plus automatisch erkannte Feldänderungen
- coverage.json — Abdeckung und Evidenz-Reife
- schema.json — Schema für Assertions
- snapshots/YYYY-MM-DD.json — beobachteter Datenzustand
- snapshots/current.json — letzter Datenzustand

## Build

    python .github/scripts/build-agentengraph.py

Quelle: data/agents.json (Schema {data.get('schema_version')})

## Wichtig

Der Ordner beginnt mit _ und ist nicht als öffentliche AgentenIndex-API gedacht.
Das GitHub-Repository selbst ist öffentlich; AgentenGraph ist daher interne
Infrastruktur, aber kein vertraulicher Datenspeicher.
"""

    dump(OUT / "manifest.json", manifest)
    dump(OUT / "entities.json", {"graph_version":GRAPH_VERSION,"as_of":as_of,"agents":sorted(agent_entities,key=lambda x:x["agent_id"]),"providers":sorted(providers.values(),key=lambda x:x["provider_id"])})
    dump(OUT / "sources.json", {"graph_version":GRAPH_VERSION,"as_of":as_of,"sources":sorted(source_records.values(),key=lambda x:x["source_id"])})
    dump(OUT / "assertions.json", {"graph_version":GRAPH_VERSION,"as_of":as_of,"assertions":sorted(assertions,key=lambda x:(x["agent_id"],x["path"],x["valid_from"],x["assertion_id"]))})
    dump(OUT / "events.json", {"graph_version":GRAPH_VERSION,"as_of":as_of,"events":sorted(event_map.values(),key=lambda x:(x.get("date") or "",x["agent_id"],x["event_id"]))})
    dump(OUT / "coverage.json", coverage)
    dump(OUT / "schema.json", schema)
    dump(SNAP / f"{as_of}.json", current_snapshot)
    dump(SNAP / "current.json", current_snapshot)
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    print(json.dumps({
        "status":"AGENTENGRAPH_BUILT",
        "as_of":as_of,
        "agents":len(agent_entities),
        "providers":len(providers),
        "sources":len(source_records),
        "assertions_active":len(active_assertions),
        "assertions_historical":len(assertions)-len(active_assertions),
        "events":len(event_map),
        "field_level_evidence":field_level,
        "closed_now":len(closed_now),
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
