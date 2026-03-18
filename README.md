# Piano API Export

Python-Paket zum Exportieren von Piano-Analytics-Daten via Restricted API Keys als CSV.

## Installation

### Weg 1: Git-Repo klonen

```sh
git clone https://github.com/jpigla/piano-analytics-export.git
cd piano-analytics-export
pip install .
```

### Weg 2: Direkt von GitHub installieren

```sh
pip install git+https://github.com/jpigla/piano-analytics-export.git
```

### Weg 3: Wheel-Datei

Wheel bauen und verschicken:
```sh
pip install build
python -m build
# dist/piano_analytics_export-1.0.0-py3-none-any.whl verschicken
```

Empfänger installiert mit:
```sh
pip install piano_analytics_export-1.0.0-py3-none-any.whl
```

Danach steht der Befehl `piano-analytics-export` zur Verfügung.

## Schnellstart

### 1. Config erstellen

```sh
piano-analytics-export --init
```

Erzeugt eine `api_keys.json` im aktuellen Verzeichnis mit einer Vorlage:

```json
{
  "credentials": [
    {
      "beschreibung": "Beispiel-Datensatz",
      "api_key": "DEIN-API-KEY"
    }
  ]
}
```

- `beschreibung`: Frei wählbarer Name, wird im Log und als Dateiname verwendet.
- `api_key`: Der Restricted API Key aus Piano Analytics.

### 2. Daten exportieren

```sh
piano-analytics-export --start 2025-01-01 --end 2025-01-31
```

## Ausgabedateien

- **Ein Eintrag** in der Config: Ergebnis wird in `export.csv` geschrieben (oder `--output`).
- **Mehrere Einträge**: Pro Eintrag eine eigene CSV-Datei, benannt nach der Beschreibung (z.B. `Beispiel-Datensatz.csv`, `Weiterer-Datensatz.csv`).

## Verwendung

### Pflichtparameter

- `--start`: Startdatum im ISO-Format (`YYYY-MM-DD`).
- `--end`: Enddatum im ISO-Format (`YYYY-MM-DD`).

### Config-Optionen (gegenseitig exklusiv)

- `--config PFAD`: Pfad zur Credentials-Datei (Standard: `./api_keys.json`).
- `--api-key KEY`: Einzelner API-Key direkt als Flag, ohne Config-Datei.

### Weitere Optionen

- `--init`: Config-Vorlage (`api_keys.json`) im aktuellen Verzeichnis erstellen.
- `--output PFAD`: Ausgabe-CSV (Standard: `export.csv`). Bei mehreren Einträgen wird das Verzeichnis des Pfads verwendet.
- `--dry-run`: Payload anzeigen ohne API-Aufruf.
- `--timeout N`: Request-Timeout in Sekunden (Standard: 120).
- `--max-workers N`: Parallele API-Requests (Standard: 5).
- `--filter LISTE`: Komma-getrennte Beschreibungen zum Filtern.
- `--quiet`: Nur Fehler ausgeben.
- `--verbose`: Erweiterte Ausgabe.

## Beispiele

Daten für Januar 2025 exportieren:
```sh
piano-analytics-export --start 2025-01-01 --end 2025-01-31
```

Schnelle Einzelabfrage ohne Config-Datei:
```sh
piano-analytics-export --start 2025-01-01 --end 2025-01-31 --api-key "ABC123"
```

Nur einen bestimmten Eintrag abfragen:
```sh
piano-analytics-export --start 2025-01-01 --end 2025-01-31 --filter "Mein Datensatz"
```

Payload prüfen ohne API-Aufruf:
```sh
piano-analytics-export --dry-run --start 2025-01-01 --end 2025-01-31
```

Ergebnis in ein bestimmtes Verzeichnis schreiben:
```sh
piano-analytics-export --start 2025-01-01 --end 2025-01-31 --output ergebnisse/export.csv
```

## Rate Limiting

- Bei `429 Too Many Requests` wartet das Tool 10 Sekunden und versucht es erneut. Jede weitere 429-Antwort erhöht die Wartezeit um 10 Sekunden (20s, 30s, ...).
- Jeder Wartevorgang wird im Log als `WAIT`/`RETRY` angezeigt.
- Nach insgesamt 60 Sekunden Wartezeit wird abgebrochen.

## Paginierung

- Die Piano API liefert maximal 10.000 Zeilen pro Request. Bei genau 10.000 Zeilen wird automatisch die nächste Seite abgerufen.
- Maximal 20 Seiten (200.000 Zeilen) werden abgerufen.
- Seitenübergänge erscheinen als `PAGE` im Log, die finale `OK`-Zeile zeigt Gesamtzeilenzahl und Seitenanzahl.

## Parallelisierung

Mehrere API-Keys werden standardmäßig mit bis zu 5 parallelen Threads abgefragt. Anpassbar mit `--max-workers`.
