#!/usr/bin/env python3
"""Schreibt tools/calibration/desktop-<id>.baukasten.json (jeder Desktop allein, ohne Bausteine) - zum Messen echter ISO-Größen mit dem
Workflow "ISO bauen (echter Test)" (Eingabe: Pfad der Rezept-Datei statt Vorlagen-Name)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baukasten import catalog  # noqa: E402
from baukasten.model import Recipe  # noqa: E402


def main() -> int:
    out = ROOT / "tools" / "calibration"
    out.mkdir(exist_ok=True)
    for did in catalog.DESKTOPS:
        r = Recipe(name=f"desktop-{did}", desktop=did, features=[])
        (out / f"desktop-{did}.baukasten.json").write_bytes(r.to_json().encode("utf-8"))
    print(f"{len(catalog.DESKTOPS)} Rezepte in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
