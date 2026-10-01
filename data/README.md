# AgentenIndex Data

Maschinenlesbarer Startbestand der verifizierten Agentenprofile. Angaben sind mit Prüfdatum und Primärquellen verknüpft.

## Datenebenen

- agents.json ist die kompakte öffentliche Datenbasis für AgentenProfile und AgentenFinder.
- _agentengraph/ ist die interne versionierte Evidenz- und Historienebene. Sie speichert stabile Entitäten, Quellen, Assertions, Ereignisse und Snapshots.
- Der AgentenGraph behauptet in v1 keine feldgenaue Evidenz, wenn bestehende Quellen nur auf Profilebene zugeordnet sind.

