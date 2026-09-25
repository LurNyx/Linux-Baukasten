"""Aus einem Rezept ein vollständiges live-build-Projekt erzeugen (Konfiguration, Paketlisten, Startskripte, Dateien).

Das Ergebnis ist ein Ordner, der auf jedem Debian-System (auch in WSL oder Docker) mit `sudo ./build.sh` eine
startbare ISO-Datei baut. Alle Dateien werden mit Unix-Zeilenenden (LF) geschrieben.
"""
from __future__ import annotations

import re
import shlex
from pathlib import Path

from . import APP_NAME, VERSION
from .catalog import (BASES, BUILD_NEEDS, DESKTOPS, FEATURES, boot_params, estimate_size_mb, needs_non_free, package_list,
                      resolve_features, validate)
from .model import Recipe, RecipeError


def iso_volume_label(name: str) -> str:
    """ISO-Volumenname: Großbuchstaben/Ziffern/Unterstrich, max. 32 Zeichen."""
    label = re.sub(r"[^A-Z0-9_]", "_", name.upper())
    return label[:32] or "LINUX_BAUKASTEN"


def lb_config_lines(r: Recipe) -> list:
    """Argumente für `lb config` (eine Zeile je Option)."""
    areas = "main contrib non-free non-free-firmware" if needs_non_free(r) else "main"
    opts = [
        f"--distribution {r.suite}",
        "--architectures amd64",
        f"--archive-areas {shlex.quote(areas)}",
        "--binary-images iso-hybrid",
        f"--bootappend-live {shlex.quote(' '.join(boot_params(r)))}",
        f"--iso-application {shlex.quote(r.name)}",
        f"--iso-publisher {shlex.quote(APP_NAME + ' ' + VERSION)}",
        f"--iso-volume {shlex.quote(iso_volume_label(r.name))}",
        f"--image-name {shlex.quote(r.name)}",
        "--memtest none",
        "--checksums sha256",
        "--security true",
        "--updates true",
    ]
    for i in resolve_features(r.features):
        f = FEATURES[i]
        if f.lb_options:
            opts.append(" ".join(shlex.quote(x) for x in f.lb_options))
    return opts


def auto_config(r: Recipe) -> str:
    body = " \\\n    ".join(lb_config_lines(r))
    return (f"#!/bin/sh\n# Erzeugt von {APP_NAME} {VERSION}. Rezept: REZEPT.json\nset -e\n\n"
            f"lb config noauto \\\n    {body} \\\n    \"${{@}}\"\n")


# Bootmenü-Wartezeit: live-build (Debian 13) lässt das Menü ohne Zeitlimit stehen (GRUB ohne "timeout", isolinux "timeout 0").
# Darum werden die zwei kleinen Menü-Dateien über includes.binary ersetzt. Inhalt = die Originale aus einer echten
# Debian-13-Live-ISO (live-build 20250505), nur mit Wartezeit. Der CI-Bau prüft das Ergebnis in der gebauten ISO.
GRUB_CONFIG_CFG = """set default=0
set timeout=@SEC@

if [ x$feature_default_font_path = xy ] ; then
    font=unicode
else
    font=$prefix/unicode.pf2
fi

# Copied from the netinst image
if loadfont $font ; then
    set gfxmode=800x600
    set gfxpayload=keep
    insmod efi_gop
    insmod efi_uga
    insmod video_bochs
    insmod video_cirrus
else
    set gfxmode=auto
    insmod all_video
fi

insmod gfxterm
insmod png

source /boot/grub/theme.cfg

terminal_output gfxterm

insmod play
play 960 440 1 0 4 440 1
"""

ISOLINUX_CFG = """include menu.cfg
default vesamenu.c32
prompt 0
timeout @TENTHS@
"""


def boot_timeout_files(r: Recipe) -> dict:
    if not r.boot_timeout:
        return {}
    return {"config/includes.binary/boot/grub/config.cfg": (GRUB_CONFIG_CFG.replace("@SEC@", str(r.boot_timeout)), False),
            "config/includes.binary/isolinux/isolinux.cfg": (ISOLINUX_CFG.replace("@TENTHS@", str(r.boot_timeout * 10)), False)}


AUTO_BUILD = """#!/bin/sh
set -e
lb build noauto "${@}" 2>&1 | tee build.log
"""

AUTO_CLEAN = """#!/bin/sh
set -e
lb clean noauto "${@}"
rm -f config/binary config/bootstrap config/chroot config/common config/source
"""

BUILD_SH = """#!/bin/sh
# {app}: baut die ISO. Braucht Root, {needs}.
# Aufruf:  sudo ./build.sh        (empfohlen: Debian 12/13, WSL mit Debian, oder Docker-Image debian:trixie)
set -e
cd "$(dirname "$0")"
if [ "$(id -u)" -ne 0 ]; then
    echo "Bitte als root starten:  sudo ./build.sh" >&2
    exit 1
fi
if ! command -v lb >/dev/null 2>&1; then
    echo "live-build fehlt - installiere die Bauwerkzeuge (nur auf Debian/Ubuntu-artigen Systemen) ..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y live-build debootstrap squashfs-tools xorriso isolinux syslinux-common grub-pc-bin grub-efi-amd64-bin \\
        mtools dosfstools ca-certificates
fi
chmod +x auto/* config/hooks/live/*.hook.chroot 2>/dev/null || true
lb clean noauto >/dev/null 2>&1 || true
lb config
lb build 2>&1 | tee build.log
echo
echo "Fertig. Die ISO liegt hier:"
ls -lh ./*.iso
"""


WSL_BUILD_SH = """#!/bin/sh
# Baut die ISO in WSL: Ordner unter /mnt/c (NTFS) sind für debootstrap ungeeignet. Darum wird das Projekt ins
# Linux-Dateisystem kopiert, dort gebaut und die ISO zurückkopiert. Aufruf (Windows): wsl -u root -- sh ./wsl-build.sh
set -e
SRC="$(pwd)"
WORK=/root/linux-baukasten-build
rm -rf "$WORK"
mkdir -p "$WORK"
cp -a "$SRC/." "$WORK/"
cd "$WORK"
sh ./build.sh
cp -v ./*.iso "$SRC/"
"""


def readme_txt(r: Recipe) -> str:
    feats = resolve_features(r.features)
    lines = [f"{r.name}  -  erzeugt mit {APP_NAME} {VERSION}", "=" * 60, "",
             f"Basis:    {BASES[r.base]['title']} {r.suite}",
             f"Desktop:  {DESKTOPS[r.desktop]['title']}",
             f"Sprache:  {r.locale}, Tastatur {r.keyboard}, Zeitzone {r.timezone}",
             f"Benutzer: {r.username} (Live-Standardpasswort: live)", "",
             "Bausteine:"] + [f"  - {FEATURES[i].title}" for i in feats] + [
             "", f"Geschätzte Größe der ISO: ca. {estimate_size_mb(r) / 1024:.1f} GB", "",
             "ISO bauen", "---------",
             f"Voraussetzungen: {BUILD_NEEDS}.", "",
             "  Linux (Debian/Ubuntu):   sudo ./build.sh",
             "  Windows (WSL + Debian):  in WSL: sudo ./build.sh   (Projekt vorher ins Linux-Home kopieren, nicht auf C:)",
             "  Docker:                  docker run --rm --privileged -v \"$PWD\":/work debian:trixie sh -c "
             "'cp -a /work /build && cd /build && sh ./build.sh && cp ./*.iso /work/'", "",
             "Danach die ISO auf einen USB-Stick schreiben (z. B. mit Rufus, balenaEtcher oder `dd`) und davon starten.",
             "Ohne Secure-Boot-Freigabe des Boot-Loaders muss Secure Boot ggf. im BIOS ausgeschaltet werden.", ""]
    return "\n".join(lines)


def project_files(r: Recipe) -> dict:
    """Alle Dateien des Projekts: relativer Pfad -> (Inhalt als Text, ausführbar)."""
    errors = validate(r)
    if errors:
        raise RecipeError("\n".join(errors))
    files = {
        "auto/config": (auto_config(r), True),
        "auto/build": (AUTO_BUILD, True),
        "auto/clean": (AUTO_CLEAN, True),
        "build.sh": (BUILD_SH.format(app=APP_NAME, needs=BUILD_NEEDS), True),
        "wsl-build.sh": (WSL_BUILD_SH, True),
        "LIESMICH.txt": (readme_txt(r), False),
        "REZEPT.json": (r.to_json(), False),
        "config/package-lists/baukasten.list.chroot":
            ("# Pakete - erzeugt von " + APP_NAME + "\n" + "\n".join(package_list(r)) + "\n", False),
        "config/includes.chroot/usr/share/doc/baukasten/REZEPT.json": (r.to_json(), False),
    }
    files.update(boot_timeout_files(r))
    for i in resolve_features(r.features):
        f = FEATURES[i]
        for path, content, executable in f.files:
            files["config/includes.chroot" + path] = (content, executable)
        for name, script in f.hooks:
            files[f"config/hooks/live/{name}.hook.chroot"] = (script, True)
    return files


def generate(r: Recipe, out_dir) -> list:
    """Schreibt das Projekt nach out_dir. -> Liste der geschriebenen relativen Pfade."""
    out = Path(out_dir)
    files = project_files(r)
    for rel, (content, executable) in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content.replace("\r\n", "\n").encode("utf-8"))
        if executable:
            try:
                p.chmod(0o755)
            except OSError:
                pass
    return sorted(files)
