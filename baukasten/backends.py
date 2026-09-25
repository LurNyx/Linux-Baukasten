"""Wo die ISO gebaut wird: direkt unter Linux, in WSL (Windows), in Docker - oder nur exportieren.

Die Befehle werden hier nur zusammengesetzt und mit Ausgabe-Streaming gestartet. Der eigentliche Bau läuft in live-build.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
BAD_PATH_CHARS = set("'\"`$\n\r")


@dataclass
class Backend:
    id: str
    label: str
    available: bool
    hint: str = ""


def safe_for_shell(path) -> bool:
    """Pfade mit Anführungszeichen, `$` oder Zeilenumbrüchen werden in den Bau-Befehlen nicht verwendet."""
    return not (set(str(path)) & BAD_PATH_CHARS)


def wsl_distros() -> list:
    """Installierte WSL-Distributionen (ohne Docker-Desktop-interne), Debian zuerst."""
    exe = shutil.which("wsl")
    if not exe:
        return []
    try:
        r = subprocess.run([exe, "-l", "-q"], capture_output=True, timeout=20, creationflags=NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0:
        return []
    text = r.stdout.decode("utf-16-le", "ignore") if b"\x00" in r.stdout else r.stdout.decode("utf-8", "ignore")
    names = [ln.strip().replace("\x00", "") for ln in text.splitlines()]
    names = [n for n in names if n and not n.lower().startswith("docker-desktop")]
    names.sort(key=lambda n: (0 if n.lower().startswith("debian") else 1 if n.lower().startswith("ubuntu") else 2, n))
    return names


def detect_backends() -> list:
    out = []
    if sys.platform.startswith("linux"):
        ok = shutil.which("apt-get") is not None
        out.append(Backend("linux", "Direkt auf diesem Linux", ok,
                           "" if ok else "Braucht ein Debian/Ubuntu-artiges System (apt-get)."))
    else:
        out.append(Backend("linux", "Direkt auf diesem Linux", False, "Nur unter Linux verfügbar."))
    if os.name == "nt":
        distros = wsl_distros()
        label = "WSL (Windows-Subsystem für Linux)" + (f" – {distros[0]}" if distros else "")
        out.append(Backend("wsl", label, bool(distros),
                           "" if distros else "WSL ist nicht eingerichtet. In einer Eingabeaufforderung (Administrator): "
                                              "wsl --install -d Debian   (danach Neustart)."))
    else:
        out.append(Backend("wsl", "WSL (Windows-Subsystem für Linux)", False, "Nur unter Windows verfügbar."))
    docker = shutil.which("docker")
    out.append(Backend("docker", "Docker", bool(docker),
                       "" if docker else "Docker ist nicht installiert (https://docs.docker.com/get-docker/)."))
    out.append(Backend("export", "Nur Projekt exportieren (selbst bauen)", True, ""))
    return out


def build_command(backend_id: str, project_dir, distro: str | None = None):
    """(Befehlsliste, Arbeitsordner) zum Bauen der ISO im Projektordner - oder None bei 'export'."""
    project = Path(project_dir)
    if not safe_for_shell(project):
        raise ValueError("Der Ordnerpfad enthält Zeichen, die im Bau-Befehl nicht erlaubt sind (' \" ` $). "
                         "Bitte einen anderen Ordner wählen.")
    if backend_id == "linux":
        cmd = ["sh", "./build.sh"] if hasattr(os, "geteuid") and os.geteuid() == 0 else ["sudo", "sh", "./build.sh"]
        return cmd, project
    if backend_id == "wsl":
        # wsl.exe übernimmt den aktuellen Windows-Ordner als Arbeitsordner (-> /mnt/c/...); wsl-build.sh kopiert das Projekt
        # ins Linux-Dateisystem, baut dort und kopiert die ISO zurück. So kommen keine Pfade in die Befehlszeile.
        cmd = ["wsl.exe"] + (["-d", distro] if distro else []) + ["-u", "root", "--", "sh", "./wsl-build.sh"]
        return cmd, project
    if backend_id == "docker":
        script = "set -e; cp -a /work /build; cd /build; sh ./build.sh; cp -v ./*.iso /work/"
        cmd = ["docker", "run", "--rm", "--privileged", "-v", f"{project}:/work", "debian:trixie", "sh", "-c", script]
        return cmd, None
    return None


def run_streaming(cmd, on_line, cancel: threading.Event | None = None, cwd=None) -> int:
    """Startet den Befehl und gibt jede Ausgabezeile an on_line(str). -> Rückgabewert (-1 bei Abbruch)."""
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)

    def watch():
        while proc.poll() is None:
            if cancel is not None and cancel.wait(0.2):
                try:
                    proc.terminate()
                    proc.wait(5)
                except (OSError, subprocess.TimeoutExpired):
                    proc.kill()
                return

    t = threading.Thread(target=watch, daemon=True)
    t.start()
    try:
        for raw in iter(proc.stdout.readline, b""):
            on_line(raw.decode("utf-8", "replace").rstrip("\r\n"))
    finally:
        proc.stdout.close()
    code = proc.wait()
    t.join(1)
    if cancel is not None and cancel.is_set():
        return -1
    return code
