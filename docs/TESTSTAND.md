# Teststand

_Stand: Version 0.1.0 (Alpha). Diese Datei wird nach echten Testläufen aktualisiert._

## Geprüft (automatisch bei jedem Push)

- Rezept-Modell: Speichern/Laden, Ablehnung bösartiger Eingaben (Namen, Pakete, Kernel-Parameter, Pfade)
- Katalog: eindeutige IDs, gegenseitige Konflikte, Abhängigkeiten, alle Vorlagen gültig, Skripte beginnen mit `#!/bin/sh` + `set -e`
- Debian-Archiv: **jeder** Paketname des Katalogs existiert in Debian 13 „trixie“ und im richtigen Bereich (`tools/check_packages.py`)
- Generator: vollständiges live-build-Projekt für jede Vorlage, nur LF-Zeilenenden, `sh -n` über alle erzeugten Skripte
- Bau-Befehle (Linux/WSL/Docker), Streaming der Ausgabe, Abbruch
- Oberfläche mit echtem Tk (Vorlagen laden, Konflikte lösen, Fehler anzeigen, Projekt exportieren) und als gebaute EXE (`--selftest`)

## Echter ISO-Bau (Ende-zu-Ende)

Der Workflow „ISO bauen (echter Test)“ baut eine Vorlage in Docker (Debian 13, live-build):

| Vorlage | Ergebnis | Datum |
|---|---|---|
| _(wird nach den ersten Läufen eingetragen)_ | | |

## Noch nicht geprüft

- Start der ISOs auf echter Hardware/in einer VM (auch Secure Boot)
- Installer (Calamares / Debian-Installer), Persistenz, verschlüsselte Persistenz
- Der Amnesic-Wächter in einem selbst gebauten System
- Der „ISO bauen“-Knopf mit WSL/Docker unter Windows
