#!/usr/bin/env python3
"""Prüft ALLE Paketnamen des Katalogs gegen das echte Debian-Archiv (Internet nötig).

  python tools/check_packages.py [trixie|forky]

Ergebnis: Pakete, die es in der gewählten Ausgabe nicht gibt, und Bausteine, deren Pakete in contrib/non-free liegen,
obwohl der Baustein `needs_non_free` nicht gesetzt hat (dann würde der Bau am fehlenden Paketbereich scheitern).
Die Paketlisten werden einmal geladen und in tools/.cache zwischengespeichert.
"""
import lzma
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baukasten import catalog  # noqa: E402

MIRROR = "https://deb.debian.org/debian"
AREAS = ("main", "contrib", "non-free", "non-free-firmware")
CACHE = ROOT / "tools" / ".cache"


def load_index(suite: str, area: str, offline_ok: bool = True) -> str:
    CACHE.mkdir(exist_ok=True)
    cached = CACHE / f"{suite}-{area}.txt"
    if cached.exists():
        return cached.read_text(encoding="utf-8", errors="replace")
    url = f"{MIRROR}/dists/{suite}/{area}/binary-amd64/Packages.xz"
    with urllib.request.urlopen(url, timeout=120) as r:
        data = r.read()
    text = lzma.decompress(data).decode("utf-8", errors="replace")
    cached.write_text(text, encoding="utf-8")
    return text


def parse_names(text: str) -> set:
    names = set()
    for line in text.splitlines():
        if line.startswith("Package: "):
            names.add(line[9:].strip())
        elif line.startswith("Provides: "):
            for part in line[10:].split(","):
                names.add(part.strip().split(" ")[0])
    return names


def build_map(suite: str) -> dict:
    """Paketname -> Bereich, in dem es liegt (main hat Vorrang)."""
    where = {}
    for area in reversed(AREAS):
        for n in parse_names(load_index(suite, area)):
            where[n] = area
    return where


def check(suite: str = "trixie") -> tuple:
    where = build_map(suite)
    missing = sorted(n for n in catalog.all_package_names() if n not in where)
    area_problems = []
    for f in catalog.FEATURES_LIST:
        pk = set(f.packages)
        for _, extra in f.desktop_extras:
            pk.update(extra)
        need = {where[n] for n in pk if n in where and where[n] != "main"}
        if need and not f.needs_non_free:
            area_problems.append((f.id, sorted(need)))
    for did, d in catalog.DESKTOPS.items():
        need = {where[n] for n in d["packages"] if n in where and where[n] != "main"}
        if need:
            area_problems.append((f"desktop:{did}", sorted(need)))
    return missing, area_problems


def main() -> int:
    suite = sys.argv[1] if len(sys.argv) > 1 else "trixie"
    missing, area_problems = check(suite)
    print(f"Debian {suite}: {len(catalog.all_package_names())} Paketnamen des Katalogs geprüft")
    for n in missing:
        print(f"  FEHLT im Archiv: {n}")
    for fid, areas in area_problems:
        print(f"  Bereichsproblem: {fid} braucht {areas}, needs_non_free ist aber nicht gesetzt")
    print("ALLES OK" if not missing and not area_problems else "PROBLEME GEFUNDEN")
    return 1 if missing or area_problems else 0


if __name__ == "__main__":
    sys.exit(main())
