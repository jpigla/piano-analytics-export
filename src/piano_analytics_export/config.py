"""Config loading, --init template generation, and --api-key handling."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EXAMPLE_CONFIG = {
    "credentials": [
        {
            "beschreibung": "Beispiel-Datensatz",
            "api_key": "DEIN-API-KEY",
        },
        {
            "beschreibung": "Weiterer Datensatz",
            "api_key": "WEITERER-API-KEY",
        },
    ]
}

DEFAULT_CONFIG_PATH = Path("api_keys.json")


def init_config(path: Path) -> None:
    """Write an example api_keys.json to *path*. Abort if the file already exists."""
    if path.exists():
        raise SystemExit(f"Config-Datei existiert bereits: {path}")
    path.write_text(json.dumps(EXAMPLE_CONFIG, indent=2, ensure_ascii=False) + "\n")
    print(f"Config-Vorlage erstellt: {path}")
    print("Bitte API-Keys und Beschreibungen anpassen, dann erneut ausführen.")


def load_config(path: Path) -> list[dict[str, Any]]:
    """Load credentials from a JSON config file."""
    if not path.exists():
        raise SystemExit(
            f"Config-Datei nicht gefunden: {path}\n"
            "Erstelle eine Vorlage mit: piano-analytics-export --init"
        )
    data = json.loads(path.read_text())
    credentials = data.get("credentials", [])
    if not credentials:
        raise SystemExit("Config muss mindestens einen Eintrag unter 'credentials' enthalten")
    return credentials


def build_inline_credentials(api_key: str) -> list[dict[str, Any]]:
    """Build a single-entry credentials list from an inline --api-key value."""
    return [{"beschreibung": "Inline Key", "api_key": api_key}]
