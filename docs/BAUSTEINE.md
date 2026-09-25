# Bausteine des Linux-Baukasten

_Automatisch erzeugt aus dem Katalog (Version 0.1.0) mit `python tools/gen_docs.py` - bitte nicht von Hand ändern._

Die Größenangaben sind grobe Schätzungen (± 30 %). Jedes Paket wurde gegen das Debian-Archiv (13 "trixie") geprüft: `python tools/check_packages.py`.

## Vorlagen

| Vorlage | Desktop | Beschreibung |
|---|---|---|
| **Wegwerf-System (Tails-artig)** (`tails-like`) | Xfce | Startet von USB, speichert nichts; Stick abziehen = alles weg. Mit Firewall, Härtung und Privatsphäre-Werkzeugen. |
| **Sicherheits-Werkzeugkasten (Kali-artig)** (`kali-like`) | Xfce | Netzwerk-, Web-, WLAN-, Passwort- und Forensik-Werkzeuge auf einem Live-Stick, optional installierbar. |
| **Alltags-System (Ubuntu/Mint-artig)** (`daily`) | Cinnamon | Browser, Büro, Multimedia, Drucken, Flatpak, Installer - ein freundliches Komplettsystem. |
| **Rettungssystem (SystemRescue-artig)** (`rescue`) | LXQt | Datenträger retten, Windows reparieren, Hardware prüfen - lädt komplett ins RAM. |
| **Entwickler-Arbeitsplatz** (`developer`) | KDE Plasma | Compiler, Python, Node, Java, Go/Rust, Container, Flatpak - installierbar. |
| **Gaming-Live-System** (`gaming`) | Xfce | Freie Spiele, Wine, Lutris, GameMode und Vulkan auf einem Stick. |
| **Minimaler Server (Live, Konsole)** (`server`) | Kein Desktop (nur Konsole) | Kein Desktop: SSH nur mit Schlüssel, Firewall, Fail2ban, Überwachung - klein und schnell. |
| **Leichtes System für alte Rechner** (`minimal-desktop`) | LXQt | LXQt, Firefox, komprimierter RAM - läuft auch mit 2 GB Arbeitsspeicher. |

## Desktops

| Desktop | ca. Größe | Beschreibung |
|---|---|---|
| **Kein Desktop (nur Konsole)** (`none`) | +0.0 GB | Klein und schnell: Server, Rettungssystem, Basteln im Terminal. |
| **Xfce** (`xfce`) | +0.6 GB | Leicht, schnell, klassisch - guter Standard für USB-Sticks und ältere Rechner. |
| **GNOME** (`gnome`) | +1.5 GB | Modern und aufgeräumt, wie bei Fedora oder Ubuntu. Größer und braucht mehr RAM. |
| **KDE Plasma** (`kde`) | +1.6 GB | Sehr anpassbar, Windows-ähnliche Bedienung. Groß, aber komfortabel. |
| **LXQt** (`lxqt`) | +0.5 GB | Sehr leicht und schlank - für alte oder schwache Hardware. |
| **MATE** (`mate`) | +0.9 GB | Klassischer Desktop im Stil von GNOME 2 - vertraut und stabil. |
| **Cinnamon** (`cinnamon`) | +1.0 GB | Der Desktop von Linux Mint: vertraut, komfortabel, mittelschwer. |
| **i3 (Tiling)** (`i3`) | +0.3 GB | Tastaturgesteuerte Kachel-Oberfläche für Fortgeschrittene, extrem schlank. |

## Live-System (Verhalten des USB-Sticks)

| Baustein | Was er macht | ca. Größe | Hinweise |
|---|---|---|---|
| **Amnesic: Stick abziehen = alles löschen und ausschalten** (`amnesic-full`) | Wie bei Tails: Ziehst du den Stick, geht der Bildschirm aus, alle Programme werden beendet, Daten im RAM gelöscht, freier Speicher überschrieben und der Rechner ausgeschaltet. | 5 MB | nicht mit: `amnesic-fast`, `persistence`, `persistence-encrypted`, `toram`; Nur beim Start vom USB-Stick/UEFI wirksam (Wächter beobachtet das Live-Medium). |
| **Amnesic (schnell): Stick abziehen = sofort ausschalten** (`amnesic-fast`) | Wie oben, aber ohne Löschen des Speichers: Bildschirm aus, alles beenden, sofort aus (schnellste Variante). | 5 MB | nicht mit: `amnesic-full`, `persistence`, `persistence-encrypted`, `toram` |
| **Persistenz: Daten und Einstellungen auf dem Stick behalten** (`persistence`) | Der Stick kann eine Datenpartition nutzen, sodass Dateien, Passwörter und Programme einen Neustart überleben (Einrichtung: siehe /usr/share/doc/baukasten/PERSISTENZ.txt im System). | 1 MB | nicht mit: `amnesic-full`, `amnesic-fast` |
| **Verschlüsselte Persistenz (LUKS)** (`persistence-encrypted`) | Die Datenpartition wird verschlüsselt; beim Start fragt das System nach dem Passwort. | 3 MB | nicht mit: `amnesic-full`, `amnesic-fast`; benötigt: `persistence` |
| **Komplett ins RAM laden (danach Stick abziehen möglich)** (`toram`) | Das ganze System wird beim Start in den Arbeitsspeicher kopiert: schneller, und der Stick kann danach entfernt werden. Braucht RAM mindestens so groß wie die ISO. | 0 MB | nicht mit: `amnesic-full`, `amnesic-fast` |
| **Gehärteter Kernel-Start** (`hardened-boot`) | Zusätzliche Kernel-Parameter: Speicher wird bei Belegung/Freigabe genullt, zufällige Speicheranordnung, keine Auslagerungsdatei, kein Auto-Einhängen von Datenträgern. | 0 MB |  |

## Installer (auf die Festplatte installieren)

| Baustein | Was er macht | ca. Größe | Hinweise |
|---|---|---|---|
| **Grafischer Installer (Calamares)** (`installer-calamares`) | Ein Symbol "System installieren" auf dem Desktop: Das Live-System lässt sich mit ein paar Klicks fest auf die Festplatte installieren. | 150 MB | braucht Desktop; nicht mit: `installer-debian` |
| **Installer im Bootmenü (Debian-Installer)** (`installer-debian`) | Im Startmenü erscheinen "Install" und "Graphical install" (der klassische Debian-Installer, auch ohne Desktop). | 80 MB | nicht mit: `installer-calamares` |

## Sicherheit und Privatsphäre

| Baustein | Was er macht | ca. Größe | Hinweise |
|---|---|---|---|
| **Firewall (ufw) aktiv** (`firewall-ufw`) | Eingehende Verbindungen werden standardmäßig blockiert, ausgehende erlaubt. | 3 MB |  |
| **Kernel-Härtung (sysctl)** (`sysctl-hardening`) | Schaltet unsichere Netzwerk- und Kernel-Funktionen ab (Weiterleitungen, ICMP-Umleitungen, ptrace, unprivilegiertes BPF ...). | 0 MB |  |
| **Zufällige MAC-Adresse (WLAN/LAN)** (`mac-randomization`) | Der Rechner meldet sich im Netz mit wechselnden Hardware-Adressen an - schwerer wiederzuerkennen. | 1 MB |  |
| **AppArmor (Programme einsperren)** (`apparmor`) | Mandatory-Access-Control mit vorbereiteten Profilen. | 12 MB |  |
| **Tor und Tor Browser** (`tor-browser`) | Tor-Dienst, torsocks und der Tor-Browser-Starter (lädt den Browser beim ersten Start). | 25 MB | braucht Desktop; contrib/non-free; Anonymität hängt vom gesamten Verhalten ab - das ist kein Tails-Ersatz. |
| **Privatsphäre-Werkzeuge** (`privacy-tools`) | KeePassXC (Passwörter), MAT2 (Metadaten entfernen), BleachBit (aufräumen), secure-delete, GnuPG. | 90 MB | braucht Desktop |
| **Verschlüsselungs-Werkzeuge** (`crypto-tools`) | cryptsetup (LUKS), gocryptfs und Kommandozeilen-Hilfen. | 8 MB |  |
| **VPN-Werkzeuge** (`vpn-tools`) | WireGuard, OpenVPN und Netzwerk-Manager-Plugin. | 12 MB |  |
| **Virenscanner (ClamAV)** (`antivirus`) | ClamAV mit grafischer Oberfläche (ClamTk). | 60 MB | braucht Desktop |

## Pentest und Analyse (Kali-Stil)

| Baustein | Was er macht | ca. Größe | Hinweise |
|---|---|---|---|
| **Netzwerk-Scanner und -Analyse** (`pentest-network`) | nmap, masscan, hping3, tcpdump, Wireshark, netcat, socat, traceroute, whois, dnsutils ... | 140 MB |  |
| **Web-Sicherheitstests** (`pentest-web`) | nikto, sqlmap, gobuster, dirb, whatweb, wfuzz und curl-Helfer. | 90 MB | contrib/non-free |
| **WLAN-Analyse** (`pentest-wireless`) | aircrack-ng, reaver, bully, pixiewps, macchanger, wifite. | 60 MB | Nur an eigenen Netzen bzw. mit Erlaubnis einsetzen. |
| **Passwort-Audit** (`pentest-passwords`) | John the Ripper, hashcat, hydra, medusa, crunch, cewl. | 70 MB |  |
| **Forensik und Datenrettung** (`pentest-forensics`) | Sleuth Kit, binwalk, foremost, scalpel, testdisk/photorec, exiftool, yara. | 80 MB |  |
| **Reverse Engineering** (`pentest-reverse`) | gdb, edb-debugger, checksec, strace, ltrace, nasm, binutils. | 120 MB |  |

## Alltag und Büro

| Baustein | Was er macht | ca. Größe | Hinweise |
|---|---|---|---|
| **Firefox (ESR)** (`browser-firefox`) | Der Standard-Webbrowser. | 230 MB | braucht Desktop |
| **Chromium** (`browser-chromium`) | Alternativer Webbrowser. | 280 MB | braucht Desktop |
| **LibreOffice (Büro)** (`office`) | Textverarbeitung, Tabellen, Präsentationen. | 520 MB | braucht Desktop |
| **Thunderbird (E-Mail)** (`mail`) | E-Mail-Programm. | 230 MB | braucht Desktop |
| **Multimedia und Codecs** (`multimedia`) | VLC, ffmpeg und GStreamer-Erweiterungen für fast alle Formate. | 380 MB | braucht Desktop |
| **Grafik und Bildbearbeitung** (`graphics`) | GIMP, Inkscape und Krita. | 700 MB | braucht Desktop |
| **Drucken und Scannen** (`printing`) | CUPS, Drucker-Einrichtung, SANE. | 110 MB | braucht Desktop |
| **Bluetooth** (`bluetooth`) | Bluetooth-Dienst und Verwaltung. | 15 MB | braucht Desktop |

## Entwicklung

| Baustein | Was er macht | ca. Größe | Hinweise |
|---|---|---|---|
| **Grundausstattung für Entwickler** (`dev-base`) | build-essential, git, cmake, gdb, vim, neovim, tmux, jq, ripgrep, htop. | 330 MB |  |
| **Python** (`dev-python`) | Python 3 mit pip, venv und pipx. | 90 MB |  |
| **Node.js (Web-Entwicklung)** (`dev-web`) | Node.js und npm. | 200 MB |  |
| **Java** (`dev-java`) | OpenJDK und Maven. | 400 MB |  |
| **Go und Rust** (`dev-go-rust`) | Go-Compiler, Rust-Compiler und Cargo. | 650 MB |  |
| **Container (Podman und Docker)** (`containers`) | Podman, Docker (docker.io) und Compose. | 350 MB |  |
| **Geany (einfache Entwicklungsumgebung)** (`editor-geany`) | Schlanker grafischer Editor. | 40 MB | braucht Desktop |

## Spiele

| Baustein | Was er macht | ca. Größe | Hinweise |
|---|---|---|---|
| **Freie Spiele** (`games-foss`) | SuperTuxKart, 0 A.D., OpenTTD, RetroArch. | 1800 MB | braucht Desktop |
| **Gaming-Werkzeuge** (`gaming-tools`) | GameMode, MangoHud, Vulkan-Werkzeuge, Wine, Lutris. | 900 MB | braucht Desktop; contrib/non-free |

## Rettung und Wartung (SystemRescue-Stil)

| Baustein | Was er macht | ca. Größe | Hinweise |
|---|---|---|---|
| **Datenträger-Rettung** (`rescue-disk`) | GParted, TestDisk, ddrescue, partclone, Clonezilla, gängige Dateisysteme. | 200 MB |  |
| **Windows reparieren** (`rescue-windows`) | chntpw (Passwort zurücksetzen), wimtools, NTFS-Werkzeuge, os-prober. | 15 MB | Nur an eigenen Rechnern bzw. mit Erlaubnis verwenden. |
| **Hardware-Diagnose** (`hardware-diagnose`) | memtester, stress-ng, lm-sensors, hwinfo, inxi, dmidecode, lshw. | 40 MB |  |

## Netzwerk und Server

| Baustein | Was er macht | ca. Größe | Hinweise |
|---|---|---|---|
| **SSH-Server (nur Schlüssel-Login)** (`ssh-server`) | Fernzugriff per SSH; Passwort-Login ist abgeschaltet (Schlüssel nötig). | 6 MB |  |
| **Fail2ban (Schutz vor Passwort-Raten)** (`fail2ban`) | Sperrt Rechner, die den SSH-Zugang zu erraten versuchen. | 20 MB |  |
| **Samba (Windows-Freigaben)** (`samba`) | Dateien im Netzwerk teilen, kompatibel mit Windows. | 90 MB |  |
| **Webserver (nginx)** (`web-server`) | nginx als Webserver. | 8 MB |  |
| **Netzwerk-Erkennung (Avahi/mDNS)** (`avahi`) | Geräte im lokalen Netz per Namen finden (name.local). | 5 MB |  |
| **Überwachungs-Werkzeuge** (`monitoring`) | htop, iotop, iftop, nload, ncdu, sysstat. | 15 MB |  |

## Komfort und Hardware

| Baustein | Was er macht | ca. Größe | Hinweise |
|---|---|---|---|
| **Flatpak und Flathub (zusätzliche Programme)** (`flatpak`) | Zehntausende Programme aus dem Flathub-Store nachinstallierbar (Zugriff auf neuere Versionen). | 25 MB |  |
| **Firmware für WLAN, Grafik, Bluetooth (non-free)** (`firmware-nonfree`) | Treiberdateien, ohne die viele WLAN-Karten, Grafikchips und Laptops nicht laufen. | 420 MB | contrib/non-free |
| **Komprimierter Arbeitsspeicher (zram)** (`zram`) | Macht Rechner mit wenig RAM flüssiger. | 1 MB |  |
| **Laptop-Werkzeuge** (`laptop-tools`) | TLP (Akku-Laufzeit), powertop, brightnessctl. | 8 MB |  |
| **Zusätzliche Schriften** (`fonts`) | Noto, Liberation, Fira Code, Emoji. | 250 MB | braucht Desktop |
| **Timeshift (System-Sicherungspunkte)** (`timeshift`) | Wiederherstellungspunkte, falls ein Update etwas kaputt macht. | 15 MB | braucht Desktop |
