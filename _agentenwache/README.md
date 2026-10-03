# AgentenWache v1

AgentenWache ist die interne Quellenüberwachung von AgentenIndex.

## Zweck

AgentenGraph speichert strukturierte Zustände und Historie. AgentenWache beobachtet die im AgentenGraph registrierten Primärquellen und meldet Änderungen zur redaktionellen Prüfung.

**Wichtig:** Eine erkannte Webseitenänderung wird niemals automatisch zu einem Produktfakt in AgentenIndex. Erst nach Prüfung der offiziellen Quelle darf `data/agents.json` geändert werden. Danach übernimmt AgentenGraph die versionierte Produktänderung.

## Ablauf

1. Aktive Quellen aus `_agentengraph/sources.json` laden.
2. Pro Host schonend und mit identifizierbarem User-Agent abrufen.
3. Sichtbaren Hauptinhalt normalisieren; Navigation, Footer, Skripte und ähnliche Seitenelemente möglichst ausblenden.
4. HTTP-Status, Redirect-Ziel, ETag/Last-Modified, Text-Hash und SimHash speichern.
5. Beim ersten Lauf nur eine Baseline anlegen.
6. Bei späteren Abweichungen ein Event und einen Eintrag in der Review-Queue erzeugen.
7. Redaktionell prüfen. Nur belegte Produktänderungen fließen in `data/agents.json`.

## Dateien

- `source-states.json` — letzter beobachteter Zustand jeder Quelle
- `review-queue.json` — offene und abgeschlossene Prüffälle
- `events.json` — append-only Monitoring-Ereignisse
- `last-run.json` — Zusammenfassung des letzten Laufs

## Schweregrade

- **high** — Quelle nicht mehr erreichbar, Statuswechsel zu Fehler, sehr große Inhaltsänderung oder Domain-Redirect
- **medium** — deutliche Inhaltsänderung oder Redirect innerhalb derselben Domain
- **low** — kleine Inhaltsänderung oder Wiederherstellung der Erreichbarkeit

Der Schweregrad beschreibt nur die technische Auffälligkeit, nicht die fachliche Bedeutung.

## Review

Ein Review-Eintrag kann nach menschlicher Prüfung z. B. mit folgendem Hilfsskript abgeschlossen werden:

```bash
python .github/scripts/review-agentenwache.py \
  --id REV-... \
  --status reviewed_no_product_change \
  --note "Nur Layout/Navigation geändert; keine relevante Produkteigenschaft."
```

Mögliche Status: `reviewed_no_product_change`, `applied_to_agents`, `dismissed_noise`, `acknowledged`.


## Systemsignale ab v1.1

AgentenWache bleibt ein Detektor für Quellenänderungen. Bei der menschlichen Review kann eine Änderung jetzt zusätzlich als strukturiertes Systemsignal klassifiziert werden, zum Beispiel:

- model_change
- tool_permission_change
- memory_change
- delegation_change
- protocol_change
- human_approval_change
- hosting_change
- audit_change
- identity_change
- rollback_change
- operational_limit_change

Die Klassifikation ist bewusst **manuell**. Ein geänderter Webseiteninhalt beweist noch keinen Modellwechsel oder eine neue Delegationsfähigkeit. Erst die redaktionelle Prüfung darf ein Systemsignal setzen; ein Produktfakt entsteht weiterhin ausschließlich über belegte Datenänderungen im AgentenGraph.

Beispiel:

```bash
python .github/scripts/review-agentenwache.py \
  --id REV-... \
  --status applied_to_agents \
  --system-signal delegation_change \
  --note "Offizielle Dokumentation belegt neue Agent-zu-Agent-Delegation; Deep Evidence aktualisiert."
```

## Frequenz

Der GitHub-Workflow läuft einmal täglich und zusätzlich, wenn sich das AgentenGraph-Quellenregister ändert. Der Abruf erfolgt pro Host seriell mit kurzer Pause, damit Anbieter nicht unnötig belastet werden.

## Grenzen

Dynamische Webseiten können technische Änderungen erzeugen, obwohl sich kein Produktmerkmal geändert hat. Umgekehrt kann eine relevante Änderung klein sein. Deshalb bleibt AgentenWache ein **Detektor für Prüfbedarf**, kein automatischer Faktenextraktor.
