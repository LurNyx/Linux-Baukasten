#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Weitere Tests: Oberfläche (mit echtem Tk, falls ein Bildschirm da ist), erzeugte Dokumentation, Debian-Paketnamen (mit Internet).
Aufruf:  python tests/test_extra.py
"""
import subprocess
import sys
import tempfile
import traceback
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from baukasten import catalog, cli  # noqa: E402

results = []


def test(fn):
    try:
        fn()
        results.append(True)
        print(f"  ok    {fn.__name__}")
    except Exception:
        results.append(False)
        print(f"  FAIL  {fn.__name__}\n{traceback.format_exc()}")
    return fn


@test
def test_generated_docs_and_example_recipes_match_the_catalog():
    import gen_docs
    stale = [p.relative_to(ROOT).as_posix() for p, text in gen_docs.expected_files().items()
             if not p.exists() or p.read_text(encoding="utf-8") != text]
    assert not stale, f"veraltet, bitte 'python tools/gen_docs.py' ausführen: {stale}"
    for pid in catalog.PRESETS:
        from baukasten.model import Recipe
        r = Recipe.from_json((ROOT / "recipes" / f"{pid}.baukasten.json").read_text(encoding="utf-8"))
        assert catalog.validate(r) == []


@test
def test_command_line_export_list_and_selftest_without_window():
    with tempfile.TemporaryDirectory() as td:
        assert cli.main(["--export", "rescue", "--out", td]) == 0
        assert (Path(td) / "auto" / "config").is_file() and (Path(td) / "build.sh").is_file()
        assert cli.main(["--export", str(ROOT / "recipes" / "server.baukasten.json"), "--out", td + "/s"]) == 0
        assert cli.main(["--export", "gibt-es-nicht.json", "--out", td + "/x"]) == 1
    assert cli.main(["--list"]) == 0 and cli.main(["--version"]) == 0


@test
def test_gui_selftest_runs_with_real_tk():
    from baukasten import gui
    try:
        import tkinter
        tkinter.Tcl()
    except Exception:
        print("        (übersprungen: kein Tk)")
        return
    try:
        rc = gui.selftest()
    except tkinter.TclError as e:                   # kein Bildschirm (z. B. Server ohne DISPLAY)
        print(f"        (übersprungen: kein Bildschirm: {e})")
        return
    assert rc == 0


@test
def test_package_names_exist_in_debian_archive_if_online():
    import check_packages
    try:
        missing, area_problems = check_packages.check("trixie")
    except (urllib.error.URLError, OSError) as e:
        print(f"        (übersprungen: kein Internet: {e})")
        return
    assert not missing, f"Pakete fehlen im Debian-Archiv: {missing}"
    assert not area_problems, area_problems


if __name__ == "__main__":
    print(f"\n{sum(results)}/{len(results)} Tests bestanden")
    sys.exit(0 if all(results) else 1)
