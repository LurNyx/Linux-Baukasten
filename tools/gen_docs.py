#!/usr/bin/env python3
"""Erzeugt aus dem Katalog: docs/BAUSTEINE.md (alle Vorlagen, Desktops, Bausteine) und recipes/*.baukasten.json (Beispiel-Rezepte).

  python tools/gen_docs.py          schreibt die Dateien
  python tools/gen_docs.py --check  prüft nur, ob sie noch zum Katalog passen (für die Tests)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baukasten import APP_NAME, VERSION, catalog  # noqa: E402


def bausteine_md() -> str:
    L = [f"# Bausteine des {APP_NAME}", "",
         f"_Automatisch erzeugt aus dem Katalog (Version {VERSION}) mit `python tools/gen_docs.py` - bitte nicht von Hand ändern._", "",
         "Die Größenangaben sind grobe Schätzungen (± 30 %). Jedes Paket wurde gegen das Debian-Archiv (13 \"trixie\") geprüft: `python tools/check_packages.py`.", "",
         "## Vorlagen", "", "| Vorlage | Desktop | Beschreibung |", "|---|---|---|"]
    for p in catalog.PRESETS_LIST:
        L.append(f"| **{p.title}** (`{p.id}`) | {catalog.DESKTOPS[p.desktop]['title']} | {p.desc} |")
    L += ["", "## Desktops", "", "| Desktop | ca. Größe | Beschreibung |", "|---|---|---|"]
    for did, d in catalog.DESKTOPS.items():
        L.append(f"| **{d['title']}** (`{did}`) | +{d['size_mb'] / 1024:.1f} GB | {d['desc']} |")
    for cid, ctitle in catalog.CATEGORIES:
        L += ["", f"## {ctitle}", "", "| Baustein | Was er macht | ca. Größe | Hinweise |", "|---|---|---|---|"]
        for f in catalog.FEATURES_LIST:
            if f.category != cid:
                continue
            hints = []
            if f.needs_desktop:
                hints.append("braucht Desktop")
            if f.needs_non_free:
                hints.append("contrib/non-free")
            if f.conflicts:
                hints.append("nicht mit: " + ", ".join(f"`{c}`" for c in f.conflicts))
            if f.requires:
                hints.append("benötigt: " + ", ".join(f"`{c}`" for c in f.requires))
            if f.note:
                hints.append(f.note)
            L.append(f"| **{f.title}** (`{f.id}`) | {f.desc} | {f.size_mb} MB | {'; '.join(hints)} |")
    return "\n".join(L) + "\n"


def expected_files() -> dict:
    files = {ROOT / "docs" / "BAUSTEINE.md": bausteine_md()}
    for p in catalog.PRESETS_LIST:
        files[ROOT / "recipes" / f"{p.id}.baukasten.json"] = catalog.recipe_from_preset(p.id, name=p.id).to_json()
    return files


def main() -> int:
    check = "--check" in sys.argv
    stale = []
    for path, text in expected_files().items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != text:
            stale.append(path.relative_to(ROOT).as_posix())
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(text.encode("utf-8"))
    if check:
        print("ALLES AKTUELL" if not stale else "VERALTET: " + ", ".join(stale))
        return 1 if stale else 0
    print(f"{len(expected_files())} Dateien geschrieben ({len(stale)} geändert)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
