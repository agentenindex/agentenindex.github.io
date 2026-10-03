# AgentenIndex Data

Maschinenlesbarer Startbestand der verifizierten Agentenprofile. Angaben sind mit Prüfdatum und Primärquellen verknüpft.

## Datenebenen

- agents.json ist die kompakte öffentliche Datenbasis für AgentenProfile und AgentenFinder.
- _agentengraph/ ist die interne versionierte Evidenz- und Historienebene. Sie speichert stabile Entitäten, Quellen, Assertions, Ereignisse und Snapshots.
- Der AgentenGraph behauptet in v1 keine feldgenaue Evidenz, wenn bestehende Quellen nur auf Profilebene zugeordnet sind.


## Agentensysteme v1.1

- data/agent-system-schema.json definiert Entitätstypen, Beziehungen, Freigabe-Dimensionen und manuelle Systemsignale für AgentenWache.
- data/agent-system-relations.json ist der kuratierte Eingang für explizit belegte Beziehungen zwischen Agenten, Frameworks, Komponenten, Systemen, Institutionen, Menschen und Organisationen.
- Fehlende Beziehungen bedeuten unbekannt, nicht „existiert nicht“. Plattformmerkmale werden nicht auf Agenten vererbt und Relationen nicht transitiv abgeleitet.
- Konzeptquellen wie der DeepMind-Institute-Essay dürfen die Taxonomie motivieren, aber niemals einen Produktclaim oder eine Produktrelation belegen.
