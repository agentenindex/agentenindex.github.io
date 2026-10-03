#!/usr/bin/env python3
"""Render the public AgentenGraph history section into all AgentenProfile."""
from __future__ import annotations

from pathlib import Path
import html
import json
import re
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
DATA = json.loads((ROOT / "data" / "agents.json").read_text(encoding="utf-8"))
GRAPH = ROOT / "_agentengraph"

ASSERTIONS = json.loads((GRAPH / "assertions.json").read_text(encoding="utf-8"))["assertions"]
EVENTS = json.loads((GRAPH / "events.json").read_text(encoding="utf-8"))["events"]
MANIFEST = json.loads((GRAPH / "manifest.json").read_text(encoding="utf-8"))

# The public history baseline is the fixed start of AgentenGraph tracking; it must not drift with each daily snapshot.
BASELINE = "2026-10-01"
SNAPSHOT = MANIFEST["as_of"]

PATH_LABELS = {
    "identity.name": "Produktname",
    "identity.provider": "Anbieter",
    "classification.category": "Kategorie",
    "classification.category_name": "Kategorie",
    "classification.product_type": "Produkttyp",
    "audience": "Zielgruppe",
    "use_case": "Anwendungsfeld",
    "access.description": "Zugang",
    "capabilities": "Fähigkeiten",
    "autonomy": "Autonomie",
    "models": "Modelle",
    "tools": "Tools",
    "protocols.mcp": "MCP",
    "protocols.a2a": "A2A",
    "api": "API",
    "integrations": "Integrationen",
    "memory": "Memory",
    "deployment": "Deployment",
    "hosting": "Hosting",
    "privacy.data_usage": "Datenverwendung",
    "privacy.training": "Training mit Kundendaten",
    "privacy.residency": "Datenresidenz",
    "security": "Security",
    "governance.sso": "SSO",
    "governance.audit_logs": "Audit Logs",
    "pricing": "Preise",
    "regions": "Regionen",
    "certifications": "Zertifizierungen",
}

PRODUCT_HISTORY_PREFIXES = (
    "identity.", "classification.", "access.", "capabilities", "autonomy", "models",
    "tools", "protocols.", "api", "integrations", "memory", "deployment", "hosting",
    "privacy.", "security", "governance.", "pricing", "regions", "certifications",
)
PRODUCT_HISTORY_EXACT = {"audience", "use_case"}

def esc(value) -> str:
    return html.escape(str(value), quote=True)

def de_date(value: str | None) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return value
    months = ["Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"]
    return f"{dt.day}. {months[dt.month-1]} {dt.year}"

def active_assertions(agent_id: str):
    return [a for a in ASSERTIONS if a["agent_id"] == agent_id and a.get("valid_to") is None]

def values_by_path(agent_id: str):
    out = {}
    for a in active_assertions(agent_id):
        out.setdefault(a["path"], []).append(a["value"])
    return out

def evidence_stats(agent_id: str):
    active = active_assertions(agent_id)
    exact = sum(1 for a in active if (a.get("evidence") or {}).get("binding") == "field_level")
    profile = sum(1 for a in active if (a.get("evidence") or {}).get("binding") == "profile_source_set")
    return len(active), exact, profile

def is_public_product_event(e: dict) -> bool:
    if e.get("origin") != "graph_diff":
        return False
    if e.get("event_type") == "source_set_change":
        return True
    if e.get("event_type") in {"agent_added","agent_removed"}:
        return True
    if e.get("event_type") != "field_change":
        return False
    path = e.get("path","")
    return path in PRODUCT_HISTORY_EXACT or any(path.startswith(p) for p in PRODUCT_HISTORY_PREFIXES)

def format_value(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(x) for x in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)

def render_events(agent_id: str) -> str:
    events = [e for e in EVENTS if e.get("agent_id") == agent_id and is_public_product_event(e)]
    events.sort(key=lambda e: (e.get("date") or "", e.get("event_id","")), reverse=True)
    if not events:
        return f'''<div class="ag-empty">
<span class="ag-empty-dot" aria-hidden="true"></span>
<div><b>Noch keine strukturierte Produktänderung seit der Baseline erfasst.</b><p>AgentenIndex verfolgt Änderungen für dieses Profil ab {esc(de_date(BASELINE))}. Frühere Zustände werden nur ergänzt, wenn sie durch belastbare Quellen belegt werden können.</p></div>
</div>'''

    rows = []
    for e in events[:12]:
        date = esc(de_date(e.get("date")))
        et = e.get("event_type")
        if et == "source_set_change":
            rows.append(f'''<div class="ag-event">
<div class="ag-event-date"><time datetime="{esc(e.get("date",""))}">{date}</time><span>Quellen</span></div>
<div><b>Quellen-Set geändert</b><p>Die dem AgentenProfil zugeordneten Primärquellen wurden strukturell verändert. Die konkrete fachliche Bedeutung wird weiterhin redaktionell geprüft.</p></div>
</div>''')
        elif et == "agent_added":
            rows.append(f'''<div class="ag-event">
<div class="ag-event-date"><time datetime="{esc(e.get("date",""))}">{date}</time><span>Entität</span></div>
<div><b>Agent in AgentenGraph aufgenommen</b><p>Der Agent wurde erstmals als strukturierte Entität erfasst.</p></div>
</div>''')
        elif et == "agent_removed":
            rows.append(f'''<div class="ag-event">
<div class="ag-event-date"><time datetime="{esc(e.get("date",""))}">{date}</time><span>Entität</span></div>
<div><b>Agent nicht mehr im aktuellen Datensatz</b><p>Der Agent ist im aktuellen AgentenIndex-Datensatz nicht mehr enthalten. Frühere Zustände bleiben historisch erhalten.</p></div>
</div>''')
        else:
            path = e.get("path","")
            label = PATH_LABELS.get(path, path)
            before = esc(format_value(e.get("before", [])))
            after = esc(format_value(e.get("after", [])))
            rows.append(f'''<div class="ag-event">
<div class="ag-event-date"><time datetime="{esc(e.get("date",""))}">{date}</time><span>{esc(label)}</span></div>
<div><b>Strukturierte Änderung erfasst</b><p><span class="ag-before">Vorher: {before or "—"}</span><span class="ag-after">Jetzt: {after or "—"}</span></p></div>
</div>''')
    return '<div class="ag-events">' + "".join(rows) + '</div>'

def render_section(agent: dict) -> str:
    aid = agent["profile_id"]
    vals = values_by_path(aid)
    total, exact, profile_level = evidence_stats(aid)
    audiences = vals.get("audience", [])
    uses = vals.get("use_case", [])
    category = (vals.get("classification.category_name") or [agent.get("category_name") or "—"])[0]
    product_type = (vals.get("classification.product_type") or [agent.get("type") or "—"])[0]
    access = (vals.get("access.description") or [agent.get("access") or "—"])[0]
    provider = (vals.get("identity.provider") or [agent.get("provider") or "—"])[0]

    if exact:
        evidence_badge = f"{exact} feldgenau belegt"
        evidence_detail = f"{exact} von {total} aktiven Aussagen besitzen bereits eine explizite Feld-zu-Quelle-Zuordnung. Die übrigen Aussagen verwenden weiterhin das Quellen-Set des Profils."
        evidence_class = "exact"
    else:
        evidence_badge = "Quellenbindung: Profilebene"
        evidence_detail = "Die bestehenden Primärquellen sind diesem AgentenProfil zugeordnet. Eine einzelne Quelle wird erst dann einem konkreten Feld zugeschrieben, wenn diese Zuordnung ausdrücklich geprüft wurde."
        evidence_class = "profile"

    chips = "".join(f'<span>{esc(x)}</span>' for x in uses[:4])
    audiences_text = ", ".join(audiences) if audiences else agent.get("audience_short","—")

    return f'''<section class="agentengraph-history" id="agentengraph" aria-labelledby="agentengraph-title">
<div class="ag-head">
<div><p class="kicker">AgentenGraph · Produktverlauf</p><h2 id="agentengraph-title">Strukturierte Historie von {esc(agent["name"])}</h2></div>
<span class="ag-baseline">Baseline seit {esc(de_date(BASELINE))}</span>
</div>
<p class="ag-intro">AgentenGraph speichert strukturierte Zustände dieses Agenten über die Zeit. Neue Werte ersetzen ältere Zustände nicht stillschweigend: Änderungen werden versioniert und als Ereignis erfasst. Frühere Zustände vor der Baseline werden nicht rückwirkend behauptet.</p>
<div class="ag-baseline-card">
<div class="ag-baseline-mark"><span>01</span><b>Baseline erfasst</b><small>{esc(de_date(BASELINE))}</small></div>
<div><b>Ab diesem Datum beobachtet AgentenIndex strukturierte Änderungen dieses Agenten.</b><p>Der heutige Stand ist der Ausgangspunkt. Historische Aussagen vor diesem Datum erscheinen nur, wenn sie durch belastbare Quellen belegt werden können.</p></div>
</div>
<div class="ag-current">
<div class="ag-current-head"><div><small>Aktueller strukturierter Stand</small><b>{esc(aid)} · {total} aktive Aussagen</b></div><span class="ag-evidence-badge {evidence_class}">{esc(evidence_badge)}</span></div>
<div class="ag-facts">
<div><small>Anbieter</small><b>{esc(provider)}</b></div>
<div><small>Kategorie</small><b>{esc(category)}</b></div>
<div><small>Produkttyp</small><b>{esc(product_type)}</b></div>
<div><small>Zielgruppe</small><b>{esc(audiences_text)}</b></div>
<div class="ag-fact-wide"><small>Zugang</small><b>{esc(access)}</b></div>
<div><small>Letzte Profilprüfung</small><b>{esc(de_date(agent.get("last_verified")))}</b></div>
</div>
{f'<div class="ag-usecases"><small>Strukturierte Anwendungsfelder</small><div>{chips}</div></div>' if chips else ''}
<div class="ag-evidence-note"><b>Evidenzstatus</b><p>{esc(evidence_detail)}</p><a href="/methodik/#agentengraph">Methodik zur Datenhistorie →</a></div>
</div>
<div class="ag-history-head"><div><small>Dokumentierte Änderungen seit Baseline</small><b>Produktbezogene AgentenGraph-Ereignisse</b></div></div>
{render_events(aid)}
</section>'''

def render_profile(agent: dict) -> bool:
    path = ROOT / "agenten" / agent["slug"] / "index.html"
    if not path.exists():
        raise FileNotFoundError(path)
    s = path.read_text(encoding="utf-8")
    old = s
    section = render_section(agent)

    # Replace existing rendered section or insert it directly before editorial changelog.
    existing = re.compile(r'<section class="agentengraph-history".*?</section>', re.S)
    if existing.search(s):
        s = existing.sub(section, s, count=1)
    else:
        marker = '<section class="changelog" id="changelog">'
        if marker not in s:
            raise RuntimeError(f"Changelog marker missing: {path}")
        s = s.replace(marker, section + marker, 1)

    # Add TOC entry directly before editorial changelog.
    if '<a href="#agentengraph">AgentenGraph</a>' not in s:
        s = s.replace('<a href="#changelog">Changelog</a>', '<a href="#agentengraph">AgentenGraph</a><a href="#changelog">Changelog</a>', 1)

    # Cache-bust the visual layer.
    s = re.sub(r'/assets/styles\.css\?v=[^"\']+', '/assets/styles.css?v=9.3.0', s)

    if s != old:
        path.write_text(s, encoding="utf-8")
        return True
    return False

changed = 0
for agent in DATA["agents"]:
    changed += int(render_profile(agent))

# Validate all 110 expected pages now contain the public graph section exactly once.
for agent in DATA["agents"]:
    path = ROOT / "agenten" / agent["slug"] / "index.html"
    s = path.read_text(encoding="utf-8")
    assert s.count('class="agentengraph-history"') == 1, path
    assert s.count('href="#agentengraph"') == 1, path
    assert f'Strukturierte Historie von {agent["name"]}' in s, path
    assert 'Baseline seit 1. Oktober 2026' in s, path
    assert '/assets/styles.css?v=9.3.0' in s, path

print(json.dumps({
    "status":"AGENTENGRAPH_PROFILES_RENDERED",
    "profiles":len(DATA["agents"]),
    "changed":changed,
    "baseline":BASELINE,
}, ensure_ascii=False))
