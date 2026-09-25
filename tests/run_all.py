#!/usr/bin/env python3
"""Führt alle Tests aus (test_extra.py nutzt Internet und ein Fenster, wenn vorhanden). Aufruf:  python tests/run_all.py"""
import os
import subprocess
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
env = dict(os.environ, PYTHONIOENCODING="utf-8")
failed = []
for name in ("test_core.py", "test_extra.py"):
    r = subprocess.run([sys.executable, str(here / name)], capture_output=True, text=True, encoding="utf-8", env=env)
    summary = next((ln for ln in reversed(r.stdout.splitlines()) if "Tests bestanden" in ln), "(keine Zusammenfassung)")
    print(f"{name:<18} {summary.strip()}")
    if r.returncode != 0:
        failed.append(name)
        print(r.stdout[-3000:], r.stderr[-1500:])
print("\nALLES OK" if not failed else "\nFEHLGESCHLAGEN: " + ", ".join(failed))
sys.exit(1 if failed else 0)
