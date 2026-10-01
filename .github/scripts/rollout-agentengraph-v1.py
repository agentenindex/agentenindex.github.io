from pathlib import Path

ROOT=Path('.')

p=ROOT/'methodik/index.html'
s=p.read_text(encoding='utf-8')
s=s.replace('Version 1.1 · 28.09.2026','Version 1.2 · 01.10.2026')
s=s.replace('Stand: 30. September 2026 · Source-first Referenz','Stand: 1. Oktober 2026 · Source-first Referenz')

marker='<h2 id="vergleich">7. Vergleichen ohne künstlichen Gesamtsieger</h2>'
section='''<h2 id="agentengraph">7. Strukturierte Zustände und Historie</h2>
<p>AgentenIndex führt Produktinformationen nicht nur als Fließtext. Parallel zu den sichtbaren AgentenProfilen wird eine versionierte interne Datenstruktur aufgebaut, die Agenten, Anbieter, Quellen, strukturierte Aussagen und Änderungen mit stabilen IDs verbindet. Dieses System nennen wir intern <strong>AgentenGraph</strong>.</p>
<p>Der Zweck ist nicht, aus öffentlich dokumentierten Herstellerangaben künstlich proprietäre Fakten zu machen. Der Mehrwert entsteht aus konsistenter Normalisierung, Zeitbezug und nachvollziehbarer Historie: Ein strukturierter Wert soll bei einer Änderung nicht einfach überschrieben werden. Stattdessen wird der frühere Zustand geschlossen, ein neuer Zustand angelegt und die Änderung als Ereignis gespeichert.</p>
<div class="soft-card">
<h3>Wichtig: Feldgenaue Evidenz wird nicht vorgetäuscht</h3>
<p>Die bestehenden AgentenProfile verknüpfen Primärquellen bislang überwiegend auf Profilebene. Beim Aufbau des AgentenGraph werden diese Quellen deshalb nicht automatisch einzelnen Feldern zugeschrieben. Eine Aussage gilt erst dann als feldgenau belegt, wenn eine konkrete Quelle ausdrücklich diesem Merkmal zugeordnet wurde. Diese Zuordnung wird schrittweise ausgebaut.</p>
</div>
<p>Damit entsteht ab dem 1. Oktober 2026 eine belastbare Baseline für spätere Änderungsvergleiche. Künftige Erweiterungen sollen unter anderem Fähigkeiten, Autonomie, Modelle, Tools, MCP/A2A, APIs, Integrationen, Hosting, Datenschutz, Datenverwendung, Enterprise Controls, Preise, Regionen und Zertifizierungen strukturiert erfassen.</p>
'''
if marker in s and 'id="agentengraph"' not in s:
    s=s.replace(marker,section+marker,1)

s=s.replace('<h2 id="vergleich">7. Vergleichen ohne künstlichen Gesamtsieger</h2>','<h2 id="vergleich">8. Vergleichen ohne künstlichen Gesamtsieger</h2>')
s=s.replace('<h2 id="unabhaengigkeit">8. Keine bezahlten Rankings</h2>','<h2 id="unabhaengigkeit">9. Keine bezahlten Rankings</h2>')
s=s.replace('<h2 id="grenzen">9. Was AgentenIndex ausdrücklich nicht behauptet</h2>','<h2 id="grenzen">10. Was AgentenIndex ausdrücklich nicht behauptet</h2>')
s=s.replace('<h2 id="korrekturen">10. Änderungen, Korrekturen und neue Informationen</h2>','<h2 id="korrekturen">11. Änderungen, Korrekturen und neue Informationen</h2>')
s=s.replace('<h2 id="maschinenlesbar">11. Maschinenlesbarkeit, SEO und generative Suche</h2>','<h2 id="maschinenlesbar">12. Maschinenlesbarkeit, SEO und generative Suche</h2>')

toc='<a href="#aktualitaet">Aktualität</a>'
if toc in s and '<a href="#agentengraph">Datenhistorie</a>' not in s:
    s=s.replace(toc,toc+'\n<a href="#agentengraph">Datenhistorie</a>',1)

p.write_text(s,encoding='utf-8')

d=ROOT/'data/README.md'
text=d.read_text(encoding='utf-8').rstrip()
extra='''

## Datenebenen

- agents.json ist die kompakte öffentliche Datenbasis für AgentenProfile und AgentenFinder.
- _agentengraph/ ist die interne versionierte Evidenz- und Historienebene. Sie speichert stabile Entitäten, Quellen, Assertions, Ereignisse und Snapshots.
- Der AgentenGraph behauptet in v1 keine feldgenaue Evidenz, wenn bestehende Quellen nur auf Profilebene zugeordnet sind.
'''
if '## Datenebenen' not in text:
    text += extra
d.write_text(text+'\n',encoding='utf-8')

assert 'Version 1.2 · 01.10.2026' in p.read_text(encoding='utf-8')
assert 'id="agentengraph"' in p.read_text(encoding='utf-8')
assert '<a href="#agentengraph">Datenhistorie</a>' in p.read_text(encoding='utf-8')
assert '## Datenebenen' in d.read_text(encoding='utf-8')
print('AGENTENGRAPH_METHODIK_READY')
