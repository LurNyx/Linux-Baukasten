"""Einstieg: ohne Argumente öffnet sich die Oberfläche; mit Optionen läuft alles auch ohne Fenster (Skripte, Tests)."""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from . import APP_NAME, VERSION, catalog, generator
from .model import Recipe, RecipeError


def parse_args(argv):
    p = argparse.ArgumentParser(prog="linux-baukasten", description=f"{APP_NAME} {VERSION} - dein eigenes Linux aus Bausteinen.")
    p.add_argument("--selftest", action="store_true", help="Katalog, Generator und Oberfläche kurz prüfen und beenden")
    p.add_argument("--list", action="store_true", help="Vorlagen, Desktops und Bausteine anzeigen und beenden")
    p.add_argument("--export", metavar="REZEPT|VORLAGE", help="Projekt ohne Fenster erzeugen (Rezept-Datei oder Vorlagen-Name)")
    p.add_argument("--out", metavar="ORDNER", help="Zielordner für --export")
    p.add_argument("--version", action="store_true")
    return p.parse_args(argv)


def cmd_list() -> int:
    print("Vorlagen:")
    for p in catalog.PRESETS_LIST:
        print(f"  {p.id:16} {p.title} - {p.desc}")
    print("\nDesktops: " + ", ".join(catalog.DESKTOPS))
    print("\nBausteine:")
    for cid, ctitle in catalog.CATEGORIES:
        print(f"  [{ctitle}]")
        for f in catalog.FEATURES_LIST:
            if f.category == cid:
                print(f"    {f.id:22} {f.title}")
    return 0


def cmd_export(spec: str, out: str | None) -> int:
    path = Path(spec)
    try:
        if spec in catalog.PRESETS:
            recipe = catalog.recipe_from_preset(spec)
        else:
            recipe = Recipe.from_json(path.read_text(encoding="utf-8"))
        target = Path(out) if out else Path.cwd() / recipe.name
        files = generator.generate(recipe, target)
    except (RecipeError, OSError) as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 1
    print(f"Projekt erzeugt: {target} ({len(files)} Dateien). Bauen: sudo ./build.sh (siehe LIESMICH.txt)")
    return 0


def cmd_selftest() -> int:
    problems = []
    for p in catalog.PRESETS_LIST:
        r = catalog.recipe_from_preset(p.id, name=p.id)
        errs = catalog.validate(r)
        if errs:
            problems.append((p.id, errs))
            continue
        with tempfile.TemporaryDirectory() as td:
            files = generator.generate(r, td)
            if "auto/config" not in files or not (Path(td) / "build.sh").is_file():
                problems.append((p.id, ["Projekt unvollständig"]))
    if problems:
        print("SELBSTTEST FEHLGESCHLAGEN:", problems)
        return 1
    print(f"Katalog/Generator OK ({len(catalog.PRESETS_LIST)} Vorlagen, {len(catalog.FEATURES_LIST)} Bausteine)")
    try:
        from . import gui
        return gui.selftest()
    except Exception as e:                                        # z. B. kein Bildschirm (Server)
        print(f"Oberfläche nicht geprüft: {e}")
        return 0


def main(argv=None) -> int:
    if sys.stdout is None or sys.stderr is None:                 # Fenster-EXE ohne Konsole: Ausgaben verwerfen statt abstürzen
        import os
        sink = open(os.devnull, "w", encoding="utf-8")
        sys.stdout = sys.stdout or sink
        sys.stderr = sys.stderr or sink
    args = parse_args(argv)
    if args.version:
        print(f"{APP_NAME} {VERSION}")
        return 0
    if args.list:
        return cmd_list()
    if args.export:
        return cmd_export(args.export, args.out)
    if args.selftest:
        return cmd_selftest()
    from . import gui
    return gui.main()
