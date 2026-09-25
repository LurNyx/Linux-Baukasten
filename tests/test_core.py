#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests für Rezept, Katalog, Generator und Bau-Befehle - ohne Internet, ohne Linux, ohne GUI.
Aufruf:  python tests/test_core.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baukasten import backends, catalog, generator  # noqa: E402
from baukasten.model import PKG_RE, Recipe, RecipeError, split_words  # noqa: E402

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


def find_sh():
    for cand in (shutil.which("bash"), shutil.which("sh"), r"C:\Program Files\Git\usr\bin\sh.exe", r"C:\Program Files\Git\bin\bash.exe"):
        if cand and os.path.exists(cand):
            return cand
    return None


# ----------------------------------------------------------------------------- Rezept
@test
def test_recipe_json_roundtrip_and_errors():
    r = Recipe(name="Test-1", desktop="kde", features=["flatpak", "firewall-ufw"], extra_packages=["htop"], extra_boot_params=["nomodeset"])
    r2 = Recipe.from_json(r.to_json())
    assert r2 == r and r2.copy() == r
    assert Recipe.from_json('{"name":"X","unbekannt":1}').name == "X", "unbekannte Felder werden ignoriert"
    for bad in ("kein json", "[1,2]", '{"schema": 99}', '{"features": "abc"}', '{"features": [1]}'):
        try:
            Recipe.from_json(bad)
        except RecipeError:
            pass
        else:
            raise AssertionError(f"hätte abgelehnt werden müssen: {bad}")
    assert split_words("a b, c;\nd a") == ["a", "b", "c", "d"]


@test
def test_field_validation_rejects_dangerous_input():
    ok = Recipe(name="Mein-Linux")
    assert catalog.validate(ok) == []
    bad_fields = {"name": ["", "a b", "x;rm -rf", "$(id)", "a" * 41, "-x"], "hostname": ["Groß", "a_b", "-a", ""],
                  "username": ["Root", "1abc", "a b"], "locale": ["de_DE", "de_DE.utf8", "x; y"], "keyboard": ["", "DE", "de us"],
                  "timezone": ["Berlin", "../etc", "Europe/Ber lin"]}
    for field, values in bad_fields.items():
        for v in values:
            r = Recipe()
            setattr(r, field, v)
            assert catalog.validate(r), (field, v)
    r = Recipe(extra_packages=["ok-paket", "Bad Paket", "x;y"], extra_boot_params=["good=1", "bad param", "$(x)"])
    errs = catalog.validate(r)
    assert sum("Paketname" in e for e in errs) == 2 and sum("Kernel-Parameter" in e for e in errs) == 2, errs
    assert PKG_RE.match("libstdc++6") and PKG_RE.match("g++") and not PKG_RE.match("a")


# ----------------------------------------------------------------------------- Katalog
@test
def test_catalog_is_consistent():
    ids = [f.id for f in catalog.FEATURES_LIST]
    assert len(ids) == len(set(ids)), "doppelte Baustein-IDs"
    cats = {c for c, _ in catalog.CATEGORIES}
    for f in catalog.FEATURES_LIST:
        assert f.category in cats, f.id
        assert f.title and f.desc and f.size_mb >= 0, f.id
        for other in f.requires + f.conflicts:
            assert other in catalog.FEATURES, (f.id, other)
        for c in f.conflicts:
            assert f.id in catalog.FEATURES[c].conflicts, f"Konflikt {f.id} <-> {c} ist nicht gegenseitig"
        assert not set(f.requires) & set(f.conflicts)
        for p in f.packages:
            assert PKG_RE.match(p), (f.id, p)
        for bp in f.boot_params:
            assert " " not in bp, (f.id, bp)
        for path, content, executable in f.files:
            assert path.startswith("/") and ".." not in path and content.endswith("\n"), (f.id, path)
        for name, script in f.hooks:
            assert script.startswith("#!/bin/sh\nset -e\n"), (f.id, name)
    for d in catalog.DESKTOPS.values():
        assert d["title"] and d["desc"] and d["size_mb"] >= 0
    assert set(catalog.LANG_WITHOUT_DESKTOP_TASK) <= set(catalog.LANG_TASKS.values())


@test
def test_presets_are_valid_and_meaningful():
    assert len(catalog.PRESETS_LIST) >= 6
    for p in catalog.PRESETS_LIST:
        r = catalog.recipe_from_preset(p.id)
        assert catalog.validate(r) == [], (p.id, catalog.validate(r))
        assert p.desktop in catalog.DESKTOPS and p.title and p.desc
        assert len(set(r.features)) == len(r.features)
    tails = catalog.recipe_from_preset("tails-like")
    assert "amnesic" in catalog.boot_params(tails) and "persistence" not in catalog.boot_params(tails)
    server = catalog.recipe_from_preset("server")
    assert server.desktop == "none" and not any(catalog.FEATURES[i].needs_desktop for i in catalog.resolve_features(server.features))


@test
def test_resolve_conflicts_and_desktop_rules():
    assert "persistence" in catalog.resolve_features(["persistence-encrypted"])           # requires wird ergänzt
    assert catalog.resolve_features(["flatpak", "firewall-ufw"]) == ["firewall-ufw", "flatpak"]
    try:
        catalog.resolve_features(["gibt-es-nicht"])
    except RecipeError:
        pass
    else:
        raise AssertionError
    r = Recipe(features=["amnesic-full", "persistence"])
    assert any("passt nicht zusammen" in e for e in catalog.validate(r))
    r = Recipe(features=["amnesic-full", "toram"])
    assert any("passt nicht zusammen" in e for e in catalog.validate(r)), "toram entfernt das Live-Medium - Wächter wäre wirkungslos"
    r = Recipe(features=["installer-calamares", "installer-debian"])
    assert any("passt nicht zusammen" in e for e in catalog.validate(r))
    r = Recipe(desktop="none", features=["browser-firefox"])
    assert any("braucht einen Desktop" in e for e in catalog.validate(r))
    assert catalog.validate(Recipe(features=["nix"])) != []
    assert catalog.validate(Recipe(desktop="windows")) != []
    assert catalog.validate(Recipe(suite="jessie")) != []


@test
def test_package_list_and_boot_params():
    r = Recipe(desktop="gnome", features=["flatpak", "pentest-network"], extra_packages=["htop", "nmap"], locale="de_DE.UTF-8")
    pk = catalog.package_list(r)
    assert len(pk) == len(set(pk)), "keine doppelten Pakete"
    for must in ("live-boot", "live-config", "live-task-gnome", "task-gnome-desktop", "task-german", "task-german-desktop",
                 "flatpak", "gnome-software-plugin-flatpak", "nmap", "htop"):
        assert must in pk, must
    assert "plasma-discover-backend-flatpak" not in pk
    en = catalog.package_list(Recipe(locale="en_US.UTF-8"))
    assert "task-english" in en and "task-english-desktop" not in en
    assert "task-german" not in catalog.package_list(Recipe(locale="xx_XX.UTF-8")), "unbekannte Sprache: keine Sprachpakete"
    none = catalog.package_list(Recipe(desktop="none"))
    assert "task-german-desktop" not in none
    bp = catalog.boot_params(Recipe(features=["persistence-encrypted", "hardened-boot", "toram"], extra_boot_params=["nomodeset", "toram"]))
    assert bp.count("toram") == 1 and "persistence" in bp and "persistence-encryption=luks" in bp and "nomodeset" in bp
    assert "locales=de_DE.UTF-8" in bp and "keyboard-layouts=de" in bp and "timezone=Europe/Berlin" in bp
    assert catalog.needs_non_free(Recipe(features=["firmware-nonfree"])) and not catalog.needs_non_free(Recipe(features=["flatpak"]))
    assert catalog.estimate_size_mb(Recipe(desktop="none")) < catalog.estimate_size_mb(Recipe(desktop="kde", features=["office"]))


# ----------------------------------------------------------------------------- Generator
@test
def test_generator_writes_complete_live_build_project_for_every_preset():
    sh = find_sh()
    for p in catalog.PRESETS_LIST:
        with tempfile.TemporaryDirectory() as td:
            r = catalog.recipe_from_preset(p.id, name=p.id)
            files = generator.generate(r, td)
            td = Path(td)
            for must in ("auto/config", "auto/build", "auto/clean", "build.sh", "wsl-build.sh", "LIESMICH.txt", "REZEPT.json",
                         "config/package-lists/baukasten.list.chroot", "config/includes.chroot/usr/share/doc/baukasten/REZEPT.json"):
                assert must in files and (td / must).is_file(), (p.id, must)
            assert Recipe.from_json((td / "REZEPT.json").read_text(encoding="utf-8")) == r
            cfg = (td / "auto/config").read_text(encoding="utf-8")
            assert cfg.startswith("#!/bin/sh\n") and "lb config noauto" in cfg and '"${@}"' in cfg and "--distribution trixie" in cfg
            assert "--binary-images iso-hybrid" in cfg and "--bootappend-live" in cfg
            pkgs = [ln for ln in (td / "config/package-lists/baukasten.list.chroot").read_text(encoding="utf-8").splitlines()
                    if ln and not ln.startswith("#")]
            assert pkgs == catalog.package_list(r)
            for f in td.rglob("*"):
                if f.is_file():
                    data = f.read_bytes()
                    assert b"\r" not in data, f"CRLF in {f}"
                    data.decode("utf-8")
            for f in catalog.resolve_features(r.features):
                for path, content, _ in catalog.FEATURES[f].files:
                    assert (td / ("config/includes.chroot" + path)).read_text(encoding="utf-8") == content
                for name, _ in catalog.FEATURES[f].hooks:
                    assert (td / f"config/hooks/live/{name}.hook.chroot").is_file()
            if sh:                                                    # Shell-Syntax aller erzeugten Skripte
                scripts = [td / "auto/config", td / "auto/build", td / "auto/clean", td / "build.sh", td / "wsl-build.sh"]
                scripts += list((td / "config/hooks/live").glob("*.hook.chroot")) if (td / "config/hooks/live").exists() else []
                for s in [x for x in scripts if x]:
                    rc = subprocess.run([sh, "-n", str(s)], capture_output=True, text=True)
                    assert rc.returncode == 0, (p.id, s.name, rc.stderr)


@test
def test_generator_option_details():
    r = Recipe(name="Mein Test", features=[])
    try:
        generator.generate(r, tempfile.mkdtemp())
    except RecipeError:
        pass
    else:
        raise AssertionError("ungültiger Name muss abgelehnt werden")
    r = Recipe(name="Mein-Test", desktop="none", features=["installer-debian"])
    cfg = generator.auto_config(r)
    assert "--debian-installer live --debian-installer-gui true" in cfg
    assert "--archive-areas main" in cfg and "contrib" not in cfg
    assert "contrib non-free non-free-firmware" in generator.auto_config(Recipe(features=["firmware-nonfree"]))
    assert generator.iso_volume_label("Mein-Test.1") == "MEIN_TEST_1" and len(generator.iso_volume_label("x" * 50)) == 32
    files = generator.project_files(Recipe(features=["amnesic-full"]))
    assert files["config/includes.chroot/usr/local/sbin/amnesic-watch"][1] is True
    assert "ConditionKernelCommandLine=|amnesic" in files["config/includes.chroot/etc/systemd/system/amnesic-watch.service"][0]
    assert "amnesic-watch" in files["config/hooks/live/0500-amnesic.hook.chroot"][0]


@test
def test_boot_menu_timeout_files():
    r = Recipe(boot_timeout=7)
    files = generator.project_files(r)
    grub = files["config/includes.binary/boot/grub/config.cfg"][0]
    iso = files["config/includes.binary/isolinux/isolinux.cfg"][0]
    assert grub.startswith("set default=0\nset timeout=7\n") and "source /boot/grub/theme.cfg" in grub and "terminal_output gfxterm" in grub
    assert iso == "include menu.cfg\ndefault vesamenu.c32\nprompt 0\ntimeout 70\n", "isolinux zählt in Zehntelsekunden"
    assert not [k for k in generator.project_files(Recipe(boot_timeout=0)) if "includes.binary" in k], "0 = Standardverhalten unverändert"
    for bad in (-1, 301, "5", 2.5, True, None):
        assert catalog.validate(Recipe(boot_timeout=bad)), bad
    assert catalog.validate(Recipe(boot_timeout=0)) == [] and catalog.validate(Recipe(boot_timeout=300)) == []
    assert Recipe.from_json('{"name": "X"}').boot_timeout == 10, "alte Rezepte ohne das Feld bekommen den Standard"


@test
def test_amnesic_watcher_asset_is_valid_python_and_matches_source_project_behaviour():
    import ast
    from baukasten import assets
    ast.parse(assets.AMNESIC_WATCH)
    ns = {}
    exec(compile(assets.AMNESIC_WATCH.split('if __name__ == "__main__":')[0], "amnesic-watch", "exec"), ns)
    mi = "30 28 8:1 / /run/live/medium ro,noatime shared:6 - iso9660 /dev/sda1 ro\n31 28 0:27 / /run tmpfs rw - tmpfs tmpfs rw\n"
    assert ns["medium_devnum"](mi) == "8:1"
    assert "amnesic=fast" in assets.AMNESIC_WATCH and "sysrq" in assets.AMNESIC_WATCH


# ----------------------------------------------------------------------------- Bau-Befehle
@test
def test_build_commands_and_streaming():
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td)
        cmd, cwd = backends.build_command("linux", proj)
        assert cmd[-2:] == ["sh", "./build.sh"] or cmd[-1] == "./build.sh", cmd
        assert cwd == proj
        cmd, cwd = backends.build_command("wsl", proj, distro="Debian")
        assert cmd == ["wsl.exe", "-d", "Debian", "-u", "root", "--", "sh", "./wsl-build.sh"] and cwd == proj
        cmd, cwd = backends.build_command("docker", proj)
        assert cmd[:4] == ["docker", "run", "--rm", "--privileged"] and f"{proj}:/work" in cmd and cwd is None
        assert backends.build_command("export", proj) is None
        for bad in (Path(td) / "a'b", Path(td) / 'a"b', Path(td) / "a$b", Path(td) / "a`b"):
            try:
                backends.build_command("linux", bad)
            except ValueError:
                pass
            else:
                raise AssertionError(bad)
    lines = []
    code = backends.run_streaming([sys.executable, "-c", "print('eins'); print('zwei', flush=True)"], lines.append)
    assert code == 0 and lines == ["eins", "zwei"], lines
    lines = []
    assert backends.run_streaming([sys.executable, "-c", "import sys; print('x'); sys.exit(3)"], lines.append) == 3
    cancel = threading.Event()
    threading.Timer(0.5, cancel.set).start()
    import time
    t0 = time.time()
    code = backends.run_streaming([sys.executable, "-c", "import time; time.sleep(30)"], lambda s: None, cancel)
    assert code == -1 and time.time() - t0 < 10, "Abbruch muss den Bau beenden"
    ids = [b.id for b in backends.detect_backends()]
    assert ids == ["linux", "wsl", "docker", "export"] and backends.detect_backends()[-1].available


if __name__ == "__main__":
    print(f"\n{sum(results)}/{len(results)} Tests bestanden")
    sys.exit(0 if all(results) else 1)
