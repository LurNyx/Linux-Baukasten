# Teststand

_Stand: Version 0.1.0 (Alpha), 25.09.2026. Alle Zahlen stammen aus echten Läufen, nicht aus Schätzungen._

## 1. Automatische Tests (bei jedem Push, Windows + Linux)

`python tests/run_all.py`

- Rezept-Modell: Speichern/Laden, Ablehnung bösartiger Eingaben (Namen, Pakete, Kernel-Parameter, Pfade, Wartezeit)
- Katalog: eindeutige IDs, gegenseitige Konflikte, Abhängigkeiten, alle Vorlagen gültig, Skripte beginnen mit `#!/bin/sh` + `set -e`
- **Debian-Archiv:** jeder Paketname des Katalogs existiert in Debian 13 „trixie“ und im richtigen Bereich (`tools/check_packages.py`).
  Das hat schon Fehler gefunden und behoben (`kismet`, `radare2`, `task-english-desktop` fehlen dort; `nikto`/`lutris` liegen in non-free/contrib)
- Generator: vollständiges live-build-Projekt für jede Vorlage, nur LF-Zeilenenden, `sh -n` über alle erzeugten Skripte
- Bau-Befehle (Linux/WSL/Docker), Streaming der Ausgabe, Abbruch
- Oberfläche mit echtem Tk und als gebaute EXE (`Linux-Baukasten.exe --selftest`)

## 2. Echter ISO-Bau (GitHub Actions, Docker, Debian 13, live-build 20250505)

Der Workflow [„ISO bauen (echter Test)“](../.github/workflows/build-iso.yml) baut eine Vorlage komplett und prüft danach das Bootmenü in der fertigen ISO.
**Alle Vorlagen bauen erfolgreich durch** (die fertigen Größen entsprechen echten ISO-Dateien):

| Vorlage | Desktop | ISO-Größe |
|---|---|---|
| server | keiner | 0,74 GB |
| tails-like (Wegwerf-System) | Xfce schlank | 2,0 GB |
| kali-like | Xfce schlank | 2,1 GB |
| daily | Cinnamon schlank | 2,5 GB |
| minimal-desktop | LXQt schlank | 2,5 GB |
| rescue | LXQt schlank | 2,7 GB |
| developer | KDE Plasma schlank | 3,3 GB |
| gaming | Xfce schlank | 4,3 GB |

Jeder Desktop allein (ohne Bausteine): Xfce 1,0 GB · i3 1,1 GB · MATE 1,1 GB · Cinnamon 1,2 GB · GNOME 1,4 GB · KDE 1,9 GB · LXQt 2,0 GB (schlank);
GNOME 3,0 GB · KDE 3,0 GB (komplett). Ein erster Durchlauf mit Debians kompletten Desktop-Paketen (`task-*-desktop`) machte selbst den „leichten“ LXQt-Desktop
3,4 GB groß – deshalb gibt es die „schlanken“ Varianten. Die Größen-Schätzung im Programm ist darauf kalibriert (Genauigkeit ± 30 %).

**Bootmenü in der fertigen ISO** (im CI geprüft): Wartezeit (`set timeout=10` in GRUB, `timeout 100` in isolinux), erster Menüeintrag enthält alle Parameter des Rezepts.

## 3. Start einer selbst gebauten ISO (Hyper-V-VM, UEFI, Secure Boot aus)

Geprüft mit der Vorlage **tails-like** (plus serielle Konsole), geschrieben mit dem Roh-Schreiber aus [Kali Amnesic Stick](https://github.com/LurNyx/kali-amnesic-stick):

- Das Bootmenü startet **von selbst** nach 10 s (Login-Prompt nach 53 s; ohne diese Einstellung wartete es unbegrenzt auf Enter – im VM-Test aufgefallen und behoben)
- Debian GNU/Linux 13 (trixie), Rechnername `baukasten`, deutsche Oberfläche, 1218 Pakete, Desktop (lightdm) und Firewall (ufw) aktiv, MAC-Zufall-Datei vorhanden
- Kernel-Zeile enthält `amnesic`, `noswap`, `init_on_free=1` u. a.
- Der Wächter `amnesic-watch` läuft im Modus „full“ und überwacht `/run/live/medium`
- **Platte aus der laufenden VM entfernt („Stick abziehen“) → VM nach ca. 8 s aus** (`sysrq: Emergency Sync / Remount R/O / Power Off`)
- Fund: das Kommando `sysctl` fehlte im schlanken System → Baustein „Kernel-Härtung“ installiert jetzt `procps`

## 4. Noch nicht geprüft

- Start auf **echter Hardware** und mit Secure Boot
- Start der **anderen Vorlagen** (gebaut ja, gebootet nur tails-like)
- Installer (Calamares / Debian-Installer): gebaut, aber nicht ausgeführt
- Persistenz, verschlüsselte Persistenz, toram
- Der „ISO bauen“-Knopf mit WSL/Docker unter Windows (die Bau-Befehle sind getestet, ein echter Lauf unter Windows noch nicht)
