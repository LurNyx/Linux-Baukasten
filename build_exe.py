#!/usr/bin/env python3
"""Baut Linux-Baukasten.exe (Windows, ein einziges Programm, ohne Konsolenfenster). Aufruf:  python build_exe.py

Braucht PyInstaller (pip install pyinstaller). Ergebnis: dist/Linux-Baukasten.exe
Die EXE ist nicht signiert - Windows SmartScreen kann deshalb beim ersten Start warnen ("Weitere Informationen" -> "Trotzdem ausführen").
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    subprocess.check_call([sys.executable, str(ROOT / "tools" / "make_icon.py")])
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
           "--name", "Linux-Baukasten", "--icon", str(ROOT / "assets" / "icon.ico"),
           "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"), "--specpath", str(ROOT / "build"),
           "--paths", str(ROOT), str(ROOT / "Linux-Baukasten.pyw")]
    subprocess.check_call(cmd, cwd=ROOT)
    exe = ROOT / "dist" / "Linux-Baukasten.exe"
    print(f"\nFertig: {exe} ({exe.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
