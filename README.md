# Bundesliga (OpenLigaDB) für Home Assistant

Spieltage, Ergebnisse und Live-Status für 1. und 2. Bundesliga, 3. Liga und DFB-Pokal. Die Daten kommen kostenlos und ohne API-Schlüssel von [OpenLigaDB](https://www.openligadb.de/).

## Installation über HACS

1. HACS → Benutzerdefinierte Repositories → `https://github.com/fumagallis4ever/ha-bundesliga`, Typ „Integration“
2. „Bundesliga (OpenLigaDB)“ installieren und Home Assistant neu starten
3. Einstellungen → Geräte & Dienste → Integration hinzufügen → „Bundesliga“ und die gewünschten Ligen auswählen

## Entities

- `sensor.bundesliga_<liga>`: aktueller Spieltag, Spiele mit Anstoß, Status und Ergebnis als Attribut `spiele`
- `binary_sensor.bundesliga_live`: an, wenn ein Spiel in Kürze beginnt oder läuft

Abfrage alle 10 Minuten, während Spielen jede Minute.

## Dashboard-Karte

Die Integration bringt eine eigene Karte mit. Nach der Installation erscheint sie unter **Karte hinzufügen → Bundesliga**, eine Ressource muss nicht eingetragen werden. Einstellbar im visuellen Editor:

- Titel und Ligen
- Anzeige: nur heutige Spiele oder ganzer Spieltag
- Nur anzeigen, wenn ein Spiel läuft oder bald beginnt
- Vereinslogos ein/aus

```yaml
type: custom:bundesliga-card
entities:
  - sensor.bundesliga_bl1
  - sensor.bundesliga_bl2
anzeige: heute
nur_live: false
logos: true
```

Die frühere Markdown-Variante liegt weiterhin unter `examples/karte_bundesliga.yaml`.
