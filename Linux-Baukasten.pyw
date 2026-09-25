"""Startet den Linux-Baukasten (Doppelklick, ohne Konsolenfenster). Optionen: --selftest (ohne Fenster prüfen)."""
import sys

from baukasten import cli

if __name__ == "__main__":
    sys.exit(cli.main(sys.argv[1:]))
