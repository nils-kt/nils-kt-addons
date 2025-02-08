## [2.0.2] - 08.02.2025

### Added
- **Persistente Speicherung:**  
  Versanddaten werden nun in der Datei `/data/trackings.json` gespeichert, sodass alle Tracking-Daten auch nach einem Neustart erhalten bleiben.
- **Fortschrittsanzeige:**  
  Die DHL-API liefert nun auch Fortschrittswerte. Diese werden in den Feldern `progress` und `maxProgress` gespeichert.
- **Progressbar in der Karte:**  
  In der benutzerdefinierten Karte wird unter jedem Eintrag, sofern Fortschrittsdaten vorliegen, eine kleine visuelle Progressbar angezeigt, die den aktuellen Fortschritt (als Prozentsatz) darstellt.
- **Paketname:**  
  Beim Hinzufügen einer Sendung kann nun optional ein Paketname eingegeben werden. Wird ein Paketname angegeben, erscheint dieser zusammen mit der Trackingnummer (in Klammern) in der Anzeige.
- **Vue.js Dashboard:**  
  Das Frontend basiert jetzt auf Vue.js und aktualisiert die Daten automatisch in dem in der Konfiguration festgelegten Intervall.

### Changed
- **Layout & Styling:**  
  Das Layout der benutzerdefinierten Karte wurde verbessert – es werden nun gestreifte Einträge mit abgerundeten Ecken verwendet, um die Übersichtlichkeit zu erhöhen.
- **Update-Intervall:**  
  Das in der Konfiguration definierte Update-Intervall wird sowohl im Hintergrundthread als auch im Vue.js-Frontend zur Aktualisierung der Daten angewendet.

### Fixed
- **Template-Konflikte:**  
  Durch die Verwendung von `{% raw %}` im Vue.js-Teil des Templates wurden Konflikte zwischen Jinja2- und Vue.js-Syntax behoben.
- **Fehlerbehandlung:**  
  Verbesserte Fehlerausgaben und stabile Handhabung von API-Antworten, sodass auch bei fehlenden Daten oder API-Fehlern eine aussagekräftige Rückmeldung erfolgt.
