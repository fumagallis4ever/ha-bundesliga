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

Mögliche Werte für `status` je Spiel: `geplant`, `live`, `halbzeit`, `beendet`, `abgesagt` und `offen` (Spiel vorbei, aber noch kein Ergebnis bekannt).

## Optional: Live-Stände über API-Football

OpenLigaDB wird von Freiwilligen gepflegt – gerade bei der 2. Liga fehlen Ergebnisse manchmal stundenlang. Mit einem kostenlosen Schlüssel von [API-Football](https://dashboard.api-football.com/register) ergänzt die Integration Live-Stände, Spielminute, Halbzeit und fehlende Endergebnisse:

1. Kostenlos registrieren und den API-Schlüssel aus dem Dashboard kopieren
2. Einstellungen → Geräte & Dienste → Bundesliga → **Konfigurieren** → Schlüssel eintragen

OpenLigaDB bleibt die Hauptquelle (Spielplan, Logos, Spieltag). API-Football wird nur abgefragt, solange ein Spiel läuft oder ein Ergebnis fehlt, höchstens alle 6 Minuten pro Liga. Das reicht im Gratis-Tarif (100 Abrufe/Tag) für einen normalen Spieltag. Bei knappem Kontingent pausiert die Integration bis zum nächsten Tag; die übrigen Abrufe stehen im Attribut `api_football_abrufe_uebrig` von `binary_sensor.bundesliga_live`.

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
