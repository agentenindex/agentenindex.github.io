# AgentenGraph v1.1

AgentenGraph ist der interne, versionierte Datenkern von AgentenIndex.

## Warum er existiert

'data/agents.json' bleibt die kompakte, veröffentlichte Produkt- und Finder-Datenbasis.
AgentenGraph ergänzt diese Daten sowie `data/agent-deep-evidence.json` um stabile Entitäten, Aussagen (assertions),
Quellen, Historie und Änderungsereignisse.

Der wichtigste Unterschied: Ein Wert wird künftig nicht einfach überschrieben.
Wenn sich ein strukturiertes Feld ändert, wird die alte Assertion geschlossen und
eine neue Assertion mit neuem Gültigkeitsbeginn erzeugt. Zusätzlich entsteht ein
field_change-Event.

## Evidenz in v1.1

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
- deep-coverage.json — explizite Kernfeld-Matrix mit documented/false/unknown
- research-priority.json — automatisch priorisierte Recherche-Lücken pro Agent und Feld
- system-schema.json — Entitäts-, Relations-, Freigabe- und Monitoring-Taxonomie für Agentensysteme
- relations.json — explizit kuratierte, evidence-first Systembeziehungen; fehlende Relationen bleiben unbekannt
- schema.json — Schema für Assertions
- snapshots/YYYY-MM-DD.json — beobachteter Datenzustand
- snapshots/current.json — letzter Datenzustand

## Build

    python .github/scripts/build-agentengraph.py

Quelle: data/agents.json (Schema 5.2)

## Wichtig

Der Ordner beginnt mit _ und ist nicht als öffentliche AgentenIndex-API gedacht.
Das GitHub-Repository selbst ist öffentlich; AgentenGraph ist daher interne
Infrastruktur, aber kein vertraulicher Datenspeicher.
