"""Der Katalog: Basissysteme, Desktops, Bausteine ("Features") und fertige Vorlagen.

Alles hier ist Daten. Jeder Baustein sagt, welche Debian-Pakete er braucht, welche Kernel-Parameter, welche Dateien und
Startskripte er ins fertige System bringt und was er nicht verknüpfen darf (Konflikte).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from . import assets
from .model import Recipe, RecipeError, check_fields

# --------------------------------------------------------------------------------------------------
# Basissysteme (heute: Debian per live-build; weitere folgen)
# --------------------------------------------------------------------------------------------------
BASES = {
    # Nur die stabile Ausgabe: alle Paketnamen sind dafür gegen das Debian-Archiv geprüft (tools/check_packages.py).
    # "forky" (Testing) folgt, sobald der Katalog dafür geprüft ist (dort fehlen derzeit u. a. wine und network-manager-gnome).
    "debian": {"title": "Debian", "suites": {"trixie": "Debian 13 \"trixie\" (stabil)"}},
}
# Arbeitsspeicher/Platz, den ein Bau grob braucht
BUILD_NEEDS = "mind. 15 GB freier Platz, 4 GB RAM, stabile Internetverbindung (Pakete werden geladen), 20-60 Minuten"

# --------------------------------------------------------------------------------------------------
# Desktops
# --------------------------------------------------------------------------------------------------
# "schlank" = nur der Desktop selbst mit Terminal, Dateimanager, Netzwerk und Ton. "komplett" = Debians Standard-Desktop-Paket
# (task-*-desktop): bringt zusätzlich Büro-Programme, Browser, Spiele, Sprachpakete u. a. mit - dadurch wird die ISO gut 2 GB größer
# (per echtem Bau gemessen: schon ein "leichter" Desktop wird so 3,4 GB groß).
_AUDIO = ("pipewire-audio", "pavucontrol")
DESKTOPS = {
    "none": {"title": "Kein Desktop (nur Konsole)", "desc": "Klein und schnell: Server, Rettungssystem, Basteln im Terminal.",
             "packages": (), "size_mb": 0},
    "xfce-lean": {"title": "Xfce (schlank)", "desc": "Leicht, schnell, klassisch - der beste Standard für USB-Sticks und ältere Rechner. "
                  "Nur der Desktop, Programme wählst du bei den Bausteinen.",
                  "packages": ("xorg", "lightdm", "lightdm-gtk-greeter", "xfce4", "xfce4-terminal", "thunar", "mousepad",
                               "xfce4-pulseaudio-plugin", "network-manager-gnome", "gvfs", "xdg-user-dirs", "desktop-base") + _AUDIO,
                  "size_mb": 400},
    "lxqt-lean": {"title": "LXQt (schlank)", "desc": "Sehr leicht - für alte oder schwache Hardware (ab ca. 1 GB RAM).",
                  "packages": ("xorg", "sddm", "lxqt-core", "qterminal", "featherpad", "pcmanfm-qt", "lximage-qt", "nm-tray",
                               "gvfs", "xdg-user-dirs", "desktop-base") + _AUDIO, "size_mb": 1400},
    "mate-lean": {"title": "MATE (schlank)", "desc": "Klassischer Desktop im Stil von GNOME 2 - vertraut und stabil.",
                  "packages": ("xorg", "lightdm", "lightdm-gtk-greeter", "mate-desktop-environment-core", "mate-terminal", "pluma",
                               "network-manager-gnome", "gvfs", "xdg-user-dirs", "desktop-base") + _AUDIO, "size_mb": 500},
    "cinnamon-lean": {"title": "Cinnamon (schlank)", "desc": "Der Desktop von Linux Mint: vertraut und komfortabel.",
                      "packages": ("xorg", "lightdm", "lightdm-gtk-greeter", "cinnamon-core", "gnome-terminal", "nemo",
                                   "network-manager-gnome", "gvfs", "xdg-user-dirs", "desktop-base") + _AUDIO, "size_mb": 600},
    "gnome-lean": {"title": "GNOME (schlank)", "desc": "Modern und aufgeräumt, wie bei Fedora oder Ubuntu. Braucht mehr RAM (ab ca. 3 GB).",
                   "packages": ("gnome-core", "gdm3", "network-manager-gnome", "xdg-user-dirs", "desktop-base"), "size_mb": 800},
    "kde-lean": {"title": "KDE Plasma (schlank)", "desc": "Sehr anpassbar, Windows-ähnliche Bedienung. Groß, aber komfortabel (ab ca. 3 GB RAM).",
                 "packages": ("xorg", "sddm", "kde-plasma-desktop", "plasma-nm", "konsole", "dolphin", "kate", "xdg-user-dirs",
                              "desktop-base") + _AUDIO, "size_mb": 1300},
    "i3": {"title": "i3 (Tiling)", "desc": "Tastaturgesteuerte Kachel-Oberfläche für Fortgeschrittene, extrem schlank.",
           "packages": ("xorg", "lightdm", "i3", "i3status", "dmenu", "rxvt-unicode", "network-manager-gnome") + _AUDIO, "size_mb": 500},
    "xfce": {"title": "Xfce (komplett)", "desc": "Xfce mit Debians Standard-Ausstattung: Büro-Programme, Browser, Sprachpakete u. a. sind schon dabei.",
             "packages": ("live-task-xfce", "task-xfce-desktop"), "size_mb": 2100},
    "lxqt": {"title": "LXQt (komplett)", "desc": "LXQt mit Debians Standard-Ausstattung (Büro, Browser ...) - deutlich größer als die schlanke Variante.",
             "packages": ("live-task-lxqt", "task-lxqt-desktop"), "size_mb": 1900},
    "mate": {"title": "MATE (komplett)", "desc": "MATE mit Debians Standard-Ausstattung (Büro, Browser ...).",
             "packages": ("live-task-mate", "task-mate-desktop"), "size_mb": 2100},
    "cinnamon": {"title": "Cinnamon (komplett)", "desc": "Cinnamon mit Debians Standard-Ausstattung (Büro, Browser ...).",
                 "packages": ("live-task-cinnamon", "task-cinnamon-desktop"), "size_mb": 2200},
    "gnome": {"title": "GNOME (komplett)", "desc": "GNOME mit Debians Standard-Ausstattung (Büro, Browser ...). Groß und braucht mehr RAM.",
              "packages": ("live-task-gnome", "task-gnome-desktop"), "size_mb": 2400},
    "kde": {"title": "KDE Plasma (komplett)", "desc": "KDE mit Debians Standard-Ausstattung (Büro, Browser ...). Sehr groß.",
            "packages": ("live-task-kde", "task-kde-desktop"), "size_mb": 2400},
}

# Für Englisch gibt es kein task-english-desktop (per Archiv-Prüfung festgestellt)
LANG_WITHOUT_DESKTOP_TASK = {"english"}
# Sprach-Aufgabenpakete (Debian tasks): Locale-Sprache -> task-Name
LANG_TASKS = {"de": "german", "en": "english", "fr": "french", "es": "spanish", "it": "italian", "pt": "portuguese",
              "nl": "dutch", "pl": "polish", "ru": "russian", "tr": "turkish"}

# --------------------------------------------------------------------------------------------------
# Bausteine
# --------------------------------------------------------------------------------------------------
CATEGORIES = [
    ("live", "Live-System (Verhalten des USB-Sticks)"),
    ("installer", "Installer (auf die Festplatte installieren)"),
    ("security", "Sicherheit und Privatsphäre"),
    ("pentest", "Pentest und Analyse (Kali-Stil)"),
    ("daily", "Alltag und Büro"),
    ("dev", "Entwicklung"),
    ("games", "Spiele"),
    ("rescue", "Rettung und Wartung (SystemRescue-Stil)"),
    ("server", "Netzwerk und Server"),
    ("comfort", "Komfort und Hardware"),
]


@dataclass(frozen=True)
class Feature:
    id: str
    category: str
    title: str
    desc: str
    packages: tuple = ()
    boot_params: tuple = ()
    files: tuple = ()          # ((Pfad im System, Inhalt, ausführbar), ...)
    hooks: tuple = ()          # ((Name, Shell-Skript), ...) - laufen beim Bau im System (chroot)
    lb_options: tuple = ()     # zusätzliche Argumente für "lb config"
    conflicts: tuple = ()
    requires: tuple = ()
    needs_desktop: bool = False
    needs_non_free: bool = False       # braucht die Paketbereiche contrib/non-free/non-free-firmware
    size_mb: int = 0
    desktop_extras: tuple = ()         # ((desktop_id, (Pakete...)), ...)
    note: str = ""


def F(id, category, title, desc, **kw):
    for k in ("packages", "boot_params", "conflicts", "requires", "lb_options"):
        if k in kw:
            kw[k] = tuple(kw[k])
    return Feature(id, category, title, desc, **kw)


SYSCTL_HARDENING = """# Linux-Baukasten: Kernel-Härtung
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
kernel.unprivileged_bpf_disabled = 1
net.core.bpf_jit_harden = 2
kernel.yama.ptrace_scope = 1
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
fs.protected_fifos = 2
fs.protected_regular = 2
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
"""

NM_MAC_RANDOM = """# Linux-Baukasten: zufällige MAC-Adresse (schwerer nachzuverfolgen)
[device]
wifi.scan-rand-mac-address=yes

[connection]
wifi.cloned-mac-address=random
ethernet.cloned-mac-address=random
"""

SSHD_KEYS_ONLY = """# Linux-Baukasten: SSH nur mit Schlüssel (kein Passwort, kein Root-Login)
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
"""

FAIL2BAN_SSH = """[sshd]
enabled = true
"""

PERSISTENCE_DOC = """PERSISTENZ (Daten behalten)
==========================
Dieses System startet mit der Option "persistence". Damit es Daten speichert, braucht der Stick eine weitere Partition:
  1. Freien Platz auf dem USB-Stick als Partition anlegen (z. B. mit GParted), Dateisystem ext4.
  2. Die Partition mit dem Namen (Label)  persistence  versehen.
  3. Sie einbinden und darin eine Datei  persistence.conf  mit dem Inhalt  / union  anlegen.
Beim nächsten Start werden Änderungen dort gespeichert. Mit dem Baustein "Verschlüsselte Persistenz" wird die
Partition mit LUKS verschlüsselt (Passwort beim Start).
"""


def _sh(*lines: str) -> str:
    return "#!/bin/sh\nset -e\n" + "\n".join(lines) + "\n"


_amnesic_files = (("/usr/local/sbin/amnesic-watch", assets.AMNESIC_WATCH, True),
                  ("/etc/systemd/system/amnesic-watch.service", assets.AMNESIC_UNIT, False))
_amnesic_hook = (("0500-amnesic", _sh("chmod 0755 /usr/local/sbin/amnesic-watch", "systemctl enable amnesic-watch.service")),)

FEATURES_LIST = [
    # ---------------------------------------------------------------- Live-System
    F("amnesic-full", "live", "Amnesic: Stick abziehen = alles löschen und ausschalten",
      "Wie bei Tails: Ziehst du den Stick, geht der Bildschirm aus, alle Programme werden beendet, Daten im RAM gelöscht, "
      "freier Speicher überschrieben und der Rechner ausgeschaltet.",
      packages=("python3",), boot_params=("amnesic", "noswap", "noautomount", "nopersistence", "init_on_free=1"),
      files=_amnesic_files, hooks=_amnesic_hook, conflicts=("amnesic-fast", "persistence", "persistence-encrypted", "toram"),
      size_mb=5, note="Nur beim Start vom USB-Stick/UEFI wirksam (Wächter beobachtet das Live-Medium)."),
    F("amnesic-fast", "live", "Amnesic (schnell): Stick abziehen = sofort ausschalten",
      "Wie oben, aber ohne Löschen des Speichers: Bildschirm aus, alles beenden, sofort aus (schnellste Variante).",
      packages=("python3",), boot_params=("amnesic=fast", "noswap", "noautomount", "nopersistence"),
      files=_amnesic_files, hooks=_amnesic_hook, conflicts=("amnesic-full", "persistence", "persistence-encrypted", "toram"),
      size_mb=5),
    F("persistence", "live", "Persistenz: Daten und Einstellungen auf dem Stick behalten",
      "Der Stick kann eine Datenpartition nutzen, sodass Dateien, Passwörter und Programme einen Neustart überleben "
      "(Einrichtung: siehe /usr/share/doc/baukasten/PERSISTENZ.txt im System).",
      boot_params=("persistence",), files=(("/usr/share/doc/baukasten/PERSISTENZ.txt", PERSISTENCE_DOC, False),),
      conflicts=("amnesic-full", "amnesic-fast"), size_mb=1),
    F("persistence-encrypted", "live", "Verschlüsselte Persistenz (LUKS)",
      "Die Datenpartition wird verschlüsselt; beim Start fragt das System nach dem Passwort.",
      packages=("cryptsetup",), boot_params=("persistence-encryption=luks",), requires=("persistence",), size_mb=3),
    F("toram", "live", "Komplett ins RAM laden (danach Stick abziehen möglich)",
      "Das ganze System wird beim Start in den Arbeitsspeicher kopiert: schneller, und der Stick kann danach entfernt werden. "
      "Braucht RAM mindestens so groß wie die ISO.",
      boot_params=("toram",), conflicts=("amnesic-full", "amnesic-fast"), size_mb=0),
    F("hardened-boot", "live", "Gehärteter Kernel-Start",
      "Zusätzliche Kernel-Parameter: Speicher wird bei Belegung/Freigabe genullt, zufällige Speicheranordnung, "
      "keine Auslagerungsdatei, kein Auto-Einhängen von Datenträgern.",
      boot_params=("init_on_alloc=1", "init_on_free=1", "slab_nomerge", "page_alloc.shuffle=1", "randomize_kstack_offset=on",
                   "vsyscall=none", "debugfs=off", "noswap", "noautomount"), size_mb=0),
    # ---------------------------------------------------------------- Installer
    F("installer-calamares", "installer", "Grafischer Installer (Calamares)",
      "Ein Symbol \"System installieren\" auf dem Desktop: Das Live-System lässt sich mit ein paar Klicks fest auf die "
      "Festplatte installieren.", packages=("calamares", "calamares-settings-debian"),
      conflicts=("installer-debian",), needs_desktop=True, size_mb=150),
    F("installer-debian", "installer", "Installer im Bootmenü (Debian-Installer)",
      "Im Startmenü erscheinen \"Install\" und \"Graphical install\" (der klassische Debian-Installer, auch ohne Desktop).",
      lb_options=("--debian-installer", "live", "--debian-installer-gui", "true"), conflicts=("installer-calamares",), size_mb=80),
    # ---------------------------------------------------------------- Sicherheit und Privatsphäre
    F("firewall-ufw", "security", "Firewall (ufw) aktiv",
      "Eingehende Verbindungen werden standardmäßig blockiert, ausgehende erlaubt.", packages=("ufw",),
      hooks=(("0510-ufw", _sh("sed -i 's/^ENABLED=.*/ENABLED=yes/' /etc/ufw/ufw.conf", "systemctl enable ufw.service")),), size_mb=3),
    F("sysctl-hardening", "security", "Kernel-Härtung (sysctl)",
      "Schaltet unsichere Netzwerk- und Kernel-Funktionen ab (Weiterleitungen, ICMP-Umleitungen, ptrace, unprivilegiertes BPF ...).",
      packages=("procps",),          # das Kommando "sysctl" fehlte im schlanken System (echter VM-Test)
      files=(("/etc/sysctl.d/99-baukasten-hardening.conf", SYSCTL_HARDENING, False),), size_mb=1),
    F("mac-randomization", "security", "Zufällige MAC-Adresse (WLAN/LAN)",
      "Der Rechner meldet sich im Netz mit wechselnden Hardware-Adressen an - schwerer wiederzuerkennen.",
      packages=("network-manager",), files=(("/etc/NetworkManager/conf.d/00-baukasten-mac-random.conf", NM_MAC_RANDOM, False),),
      size_mb=1),
    F("apparmor", "security", "AppArmor (Programme einsperren)", "Mandatory-Access-Control mit vorbereiteten Profilen.",
      packages=("apparmor", "apparmor-utils", "apparmor-profiles", "apparmor-profiles-extra"),
      boot_params=("apparmor=1", "security=apparmor"), size_mb=12),
    F("tor-browser", "security", "Tor und Tor Browser", "Tor-Dienst, torsocks und der Tor-Browser-Starter (lädt den Browser beim ersten Start).",
      packages=("tor", "torsocks", "torbrowser-launcher"), needs_desktop=True, needs_non_free=True, size_mb=25,
      note="Anonymität hängt vom gesamten Verhalten ab - das ist kein Tails-Ersatz."),
    F("privacy-tools", "security", "Privatsphäre-Werkzeuge",
      "KeePassXC (Passwörter), MAT2 (Metadaten entfernen), BleachBit (aufräumen), secure-delete, GnuPG.",
      packages=("keepassxc", "mat2", "bleachbit", "secure-delete", "gnupg"), needs_desktop=True, size_mb=90),
    F("crypto-tools", "security", "Verschlüsselungs-Werkzeuge", "cryptsetup (LUKS), gocryptfs und Kommandozeilen-Hilfen.",
      packages=("cryptsetup", "gocryptfs", "ecryptfs-utils"), size_mb=8),
    F("vpn-tools", "security", "VPN-Werkzeuge", "WireGuard, OpenVPN und Netzwerk-Manager-Plugin.",
      packages=("wireguard-tools", "openvpn", "network-manager-openvpn"), size_mb=12),
    F("antivirus", "security", "Virenscanner (ClamAV)", "ClamAV mit grafischer Oberfläche (ClamTk).", packages=("clamav", "clamtk"),
      needs_desktop=True, size_mb=60),
    # ---------------------------------------------------------------- Pentest und Analyse
    F("pentest-network", "pentest", "Netzwerk-Scanner und -Analyse",
      "nmap, masscan, hping3, tcpdump, Wireshark, netcat, socat, traceroute, whois, dnsutils ...",
      packages=("nmap", "masscan", "hping3", "tcpdump", "wireshark", "tshark", "netcat-openbsd", "socat", "traceroute", "mtr-tiny",
                "whois", "dnsutils", "ettercap-text-only", "arp-scan", "iperf3"), size_mb=140),
    F("pentest-web", "pentest", "Web-Sicherheitstests", "nikto, sqlmap, gobuster, dirb, whatweb, wfuzz und curl-Helfer.",
      packages=("nikto", "sqlmap", "gobuster", "dirb", "whatweb", "wfuzz", "curl", "wget"), needs_non_free=True, size_mb=90),
    F("pentest-wireless", "pentest", "WLAN-Analyse", "aircrack-ng, reaver, bully, pixiewps, macchanger, wifite.",
      packages=("aircrack-ng", "reaver", "bully", "pixiewps", "macchanger", "wifite", "pciutils", "iw", "wireless-tools"), size_mb=60,
      note="Nur an eigenen Netzen bzw. mit Erlaubnis einsetzen."),
    F("pentest-passwords", "pentest", "Passwort-Audit", "John the Ripper, hashcat, hydra, medusa, crunch, cewl.",
      packages=("john", "hashcat", "hydra", "medusa", "crunch", "cewl"), size_mb=70),
    F("pentest-forensics", "pentest", "Forensik und Datenrettung",
      "Sleuth Kit, binwalk, foremost, scalpel, testdisk/photorec, exiftool, yara.",
      packages=("sleuthkit", "binwalk", "foremost", "scalpel", "testdisk", "libimage-exiftool-perl", "yara", "gddrescue"),
      size_mb=80),
    F("pentest-reverse", "pentest", "Reverse Engineering", "gdb, edb-debugger, checksec, strace, ltrace, nasm, binutils.",
      packages=("gdb", "gdb-multiarch", "edb-debugger", "checksec", "strace", "ltrace", "nasm", "binutils"), size_mb=120),
    # ---------------------------------------------------------------- Alltag und Büro
    F("browser-firefox", "daily", "Firefox (ESR)", "Der Standard-Webbrowser.", packages=("firefox-esr",), needs_desktop=True, size_mb=230),
    F("browser-chromium", "daily", "Chromium", "Alternativer Webbrowser.", packages=("chromium",), needs_desktop=True, size_mb=280),
    F("office", "daily", "LibreOffice (Büro)", "Textverarbeitung, Tabellen, Präsentationen.",
      packages=("libreoffice-writer", "libreoffice-calc", "libreoffice-impress"), needs_desktop=True, size_mb=520),
    F("mail", "daily", "Thunderbird (E-Mail)", "E-Mail-Programm.", packages=("thunderbird",), needs_desktop=True, size_mb=230),
    F("multimedia", "daily", "Multimedia und Codecs", "VLC, ffmpeg und GStreamer-Erweiterungen für fast alle Formate.",
      packages=("vlc", "ffmpeg", "gstreamer1.0-libav", "gstreamer1.0-plugins-good", "gstreamer1.0-plugins-bad",
                "gstreamer1.0-plugins-ugly"), needs_desktop=True, size_mb=380),
    F("graphics", "daily", "Grafik und Bildbearbeitung", "GIMP, Inkscape und Krita.", packages=("gimp", "inkscape", "krita"),
      needs_desktop=True, size_mb=700),
    F("printing", "daily", "Drucken und Scannen", "CUPS, Drucker-Einrichtung, SANE.",
      packages=("cups", "system-config-printer", "sane-utils", "simple-scan"), needs_desktop=True, size_mb=110),
    F("bluetooth", "daily", "Bluetooth", "Bluetooth-Dienst und Verwaltung.", packages=("bluez", "blueman"), needs_desktop=True, size_mb=15),
    # ---------------------------------------------------------------- Entwicklung
    F("dev-base", "dev", "Grundausstattung für Entwickler", "build-essential, git, cmake, gdb, vim, neovim, tmux, jq, ripgrep, htop.",
      packages=("build-essential", "git", "cmake", "pkg-config", "gdb", "vim", "neovim", "tmux", "jq", "ripgrep", "htop", "curl", "wget"),
      size_mb=330),
    F("dev-python", "dev", "Python", "Python 3 mit pip, venv und pipx.", packages=("python3", "python3-pip", "python3-venv", "python3-dev", "pipx"),
      size_mb=90),
    F("dev-web", "dev", "Node.js (Web-Entwicklung)", "Node.js und npm.", packages=("nodejs", "npm"), size_mb=200),
    F("dev-java", "dev", "Java", "OpenJDK und Maven.", packages=("default-jdk", "maven"), size_mb=400),
    F("dev-go-rust", "dev", "Go und Rust", "Go-Compiler, Rust-Compiler und Cargo.", packages=("golang", "rustc", "cargo"), size_mb=650),
    F("containers", "dev", "Container (Podman und Docker)", "Podman, Docker (docker.io) und Compose.",
      packages=("podman", "docker.io", "docker-compose"), size_mb=350),
    F("editor-geany", "dev", "Geany (einfache Entwicklungsumgebung)", "Schlanker grafischer Editor.", packages=("geany", "geany-plugins"),
      needs_desktop=True, size_mb=40),
    # ---------------------------------------------------------------- Spiele
    F("games-foss", "games", "Freie Spiele", "SuperTuxKart, 0 A.D., OpenTTD, RetroArch.",
      packages=("supertuxkart", "0ad", "openttd", "retroarch"), needs_desktop=True, size_mb=1800),
    F("gaming-tools", "games", "Gaming-Werkzeuge", "GameMode, MangoHud, Vulkan-Werkzeuge, Wine, Lutris.",
      packages=("gamemode", "mangohud", "vulkan-tools", "mesa-vulkan-drivers", "wine", "lutris"), needs_desktop=True,
      needs_non_free=True, size_mb=900),
    # ---------------------------------------------------------------- Rettung und Wartung
    F("rescue-disk", "rescue", "Datenträger-Rettung", "GParted, TestDisk, ddrescue, partclone, Clonezilla, gängige Dateisysteme.",
      packages=("gparted", "testdisk", "gddrescue", "partclone", "clonezilla", "ntfs-3g", "dosfstools", "exfatprogs", "btrfs-progs",
                "xfsprogs", "e2fsprogs", "lvm2", "mdadm", "cryptsetup", "hdparm", "nvme-cli", "smartmontools"), size_mb=200),
    F("rescue-windows", "rescue", "Windows reparieren", "chntpw (Passwort zurücksetzen), wimtools, NTFS-Werkzeuge, os-prober.",
      packages=("chntpw", "wimtools", "ntfs-3g", "os-prober"), size_mb=15,
      note="Nur an eigenen Rechnern bzw. mit Erlaubnis verwenden."),
    F("hardware-diagnose", "rescue", "Hardware-Diagnose", "memtester, stress-ng, lm-sensors, hwinfo, inxi, dmidecode, lshw.",
      packages=("memtester", "stress-ng", "lm-sensors", "hwinfo", "inxi", "dmidecode", "lshw", "smartmontools"), size_mb=40),
    # ---------------------------------------------------------------- Netzwerk und Server
    F("ssh-server", "server", "SSH-Server (nur Schlüssel-Login)", "Fernzugriff per SSH; Passwort-Login ist abgeschaltet (Schlüssel nötig).",
      packages=("openssh-server",), files=(("/etc/ssh/sshd_config.d/10-baukasten.conf", SSHD_KEYS_ONLY, False),),
      hooks=(("0520-ssh", _sh("systemctl enable ssh.service")),), size_mb=6),
    F("fail2ban", "server", "Fail2ban (Schutz vor Passwort-Raten)", "Sperrt Rechner, die den SSH-Zugang zu erraten versuchen.",
      packages=("fail2ban",), files=(("/etc/fail2ban/jail.d/10-baukasten.conf", FAIL2BAN_SSH, False),), size_mb=20),
    F("samba", "server", "Samba (Windows-Freigaben)", "Dateien im Netzwerk teilen, kompatibel mit Windows.",
      packages=("samba", "cifs-utils"), size_mb=90),
    F("web-server", "server", "Webserver (nginx)", "nginx als Webserver.", packages=("nginx",), size_mb=8),
    F("avahi", "server", "Netzwerk-Erkennung (Avahi/mDNS)", "Geräte im lokalen Netz per Namen finden (name.local).",
      packages=("avahi-daemon", "libnss-mdns"), size_mb=5),
    F("monitoring", "server", "Überwachungs-Werkzeuge", "htop, iotop, iftop, nload, ncdu, sysstat.",
      packages=("htop", "iotop", "iftop", "nload", "ncdu", "sysstat"), size_mb=15),
    # ---------------------------------------------------------------- Komfort und Hardware
    F("flatpak", "comfort", "Flatpak und Flathub (zusätzliche Programme)",
      "Zehntausende Programme aus dem Flathub-Store nachinstallierbar (Zugriff auf neuere Versionen).",
      packages=("flatpak",),
      hooks=(("0530-flathub", _sh("flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo || "
                                  "echo 'Hinweis: Flathub konnte nicht eingerichtet werden (Netzwerk?) - später nachholbar.'")),),
      desktop_extras=(("gnome", ("gnome-software-plugin-flatpak",)), ("gnome-lean", ("gnome-software-plugin-flatpak",)),
                       ("kde", ("plasma-discover-backend-flatpak",)), ("kde-lean", ("plasma-discover-backend-flatpak",))), size_mb=25),
    F("firmware-nonfree", "comfort", "Firmware für WLAN, Grafik, Bluetooth (non-free)",
      "Treiberdateien, ohne die viele WLAN-Karten, Grafikchips und Laptops nicht laufen.",
      packages=("firmware-linux", "firmware-iwlwifi", "firmware-realtek", "firmware-atheros", "firmware-misc-nonfree",
                "firmware-amd-graphics", "firmware-intel-graphics", "amd64-microcode", "intel-microcode"), needs_non_free=True,
      size_mb=420),
    F("zram", "comfort", "Komprimierter Arbeitsspeicher (zram)", "Macht Rechner mit wenig RAM flüssiger.", packages=("zram-tools",),
      size_mb=1),
    F("laptop-tools", "comfort", "Laptop-Werkzeuge", "TLP (Akku-Laufzeit), powertop, brightnessctl.", packages=("tlp", "powertop", "brightnessctl"),
      size_mb=8),
    F("fonts", "comfort", "Zusätzliche Schriften", "Noto, Liberation, Fira Code, Emoji.",
      packages=("fonts-noto", "fonts-liberation", "fonts-firacode", "fonts-noto-color-emoji"), needs_desktop=True, size_mb=250),
    F("timeshift", "comfort", "Timeshift (System-Sicherungspunkte)", "Wiederherstellungspunkte, falls ein Update etwas kaputt macht.",
      packages=("timeshift",), needs_desktop=True, size_mb=15),
]

def _symmetric_conflicts(features: list) -> list:
    """Konflikte gelten immer in beide Richtungen (es reicht, sie an einer Stelle einzutragen)."""
    conflicts = {f.id: set(f.conflicts) for f in features}
    for f in features:
        for c in f.conflicts:
            conflicts[c].add(f.id)
    order = [f.id for f in features]
    return [replace(f, conflicts=tuple(sorted(conflicts[f.id], key=order.index))) for f in features]


FEATURES_LIST = _symmetric_conflicts(FEATURES_LIST)
FEATURES = {f.id: f for f in FEATURES_LIST}


# --------------------------------------------------------------------------------------------------
# Vorlagen ("wie Tails", "wie Kali" ...)
# --------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Preset:
    id: str
    title: str
    desc: str
    desktop: str
    features: tuple
    extra: dict = field(default_factory=dict)


PRESETS_LIST = [
    Preset("tails-like", "Wegwerf-System (Tails-artig)",
           "Startet von USB, speichert nichts; Stick abziehen = alles weg. Mit Firewall, Härtung und Privatsphäre-Werkzeugen.",
           "xfce-lean", ("amnesic-full", "hardened-boot", "mac-randomization", "firewall-ufw", "sysctl-hardening", "privacy-tools",
                    "crypto-tools", "browser-firefox", "tor-browser", "fonts")),
    Preset("kali-like", "Sicherheits-Werkzeugkasten (Kali-artig)",
           "Netzwerk-, Web-, WLAN-, Passwort- und Forensik-Werkzeuge auf einem Live-Stick, optional installierbar.",
           "xfce-lean", ("pentest-network", "pentest-web", "pentest-wireless", "pentest-passwords", "pentest-forensics", "pentest-reverse",
                    "dev-python", "persistence", "installer-calamares", "firmware-nonfree", "browser-firefox")),
    Preset("daily", "Alltags-System (Ubuntu/Mint-artig)",
           "Browser, Büro, Multimedia, Drucken, Flatpak, Installer - ein freundliches Komplettsystem.",
           "cinnamon-lean", ("browser-firefox", "mail", "office", "multimedia", "graphics", "printing", "bluetooth", "flatpak",
                        "installer-calamares", "firmware-nonfree", "fonts", "timeshift", "firewall-ufw")),
    Preset("rescue", "Rettungssystem (SystemRescue-artig)",
           "Datenträger retten, Windows reparieren, Hardware prüfen - lädt komplett ins RAM.",
           "lxqt-lean", ("rescue-disk", "rescue-windows", "hardware-diagnose", "pentest-forensics", "toram", "ssh-server", "zram",
                    "firmware-nonfree", "browser-firefox")),
    Preset("developer", "Entwickler-Arbeitsplatz",
           "Compiler, Python, Node, Java, Go/Rust, Container, Flatpak - installierbar.",
           "kde-lean", ("dev-base", "dev-python", "dev-web", "dev-java", "dev-go-rust", "containers", "editor-geany", "flatpak",
                   "browser-firefox", "installer-calamares", "firmware-nonfree", "fonts")),
    Preset("gaming", "Gaming-Live-System",
           "Freie Spiele, Wine, Lutris, GameMode und Vulkan auf einem Stick.",
           "xfce-lean", ("games-foss", "gaming-tools", "multimedia", "firmware-nonfree", "flatpak", "browser-firefox")),
    Preset("server", "Minimaler Server (Live, Konsole)",
           "Kein Desktop: SSH nur mit Schlüssel, Firewall, Fail2ban, Überwachung - klein und schnell.",
           "none", ("ssh-server", "firewall-ufw", "fail2ban", "sysctl-hardening", "monitoring", "installer-debian", "avahi")),
    Preset("minimal-desktop", "Leichtes System für alte Rechner",
           "LXQt, Firefox, komprimierter RAM - läuft auch mit 2 GB Arbeitsspeicher.",
           "lxqt-lean", ("browser-firefox", "zram", "firmware-nonfree", "printing", "installer-calamares")),
]
PRESETS = {p.id: p for p in PRESETS_LIST}


def recipe_from_preset(preset_id: str, name: str | None = None) -> Recipe:
    p = PRESETS[preset_id]
    r = Recipe(name=name or p.id, desktop=p.desktop, features=list(p.features), **p.extra)
    return r


# --------------------------------------------------------------------------------------------------
# Auflösen und Prüfen
# --------------------------------------------------------------------------------------------------
def all_package_names() -> set:
    """Jedes Paket, das der Katalog irgendwo verwendet (für die Prüfung gegen das Debian-Archiv)."""
    names = set()
    for d in DESKTOPS.values():
        names.update(d["packages"])
    for f in FEATURES_LIST:
        names.update(f.packages)
        for _, pk in f.desktop_extras:
            names.update(pk)
    for code in LANG_TASKS.values():
        names.add(f"task-{code}")
        if code not in LANG_WITHOUT_DESKTOP_TASK:
            names.add(f"task-{code}-desktop")
    names.update({"live-boot", "live-config", "sudo", "network-manager", "locales", "python3"})
    return names


def resolve_features(ids) -> list:
    """Fügt benötigte Bausteine hinzu (requires), behält die Reihenfolge des Katalogs."""
    want, todo = set(), list(ids)
    while todo:
        i = todo.pop()
        if i not in FEATURES:
            raise RecipeError(f"Unbekannter Baustein: {i}")
        if i in want:
            continue
        want.add(i)
        todo.extend(FEATURES[i].requires)
    return [f.id for f in FEATURES_LIST if f.id in want]


def validate(r: Recipe) -> list:
    """Vollständige Prüfung: Felder, Basis, Desktop, Bausteine, Konflikte. -> Liste von Fehlertexten (leer = ok)."""
    errors = check_fields(r)
    if r.base not in BASES:
        errors.append(f"Unbekanntes Basissystem: {r.base}")
    elif r.suite not in BASES[r.base]["suites"]:
        errors.append(f"Unbekannte Ausgabe {r.suite!r} für {r.base}.")
    if r.desktop not in DESKTOPS:
        errors.append(f"Unbekannter Desktop: {r.desktop}")
    unknown = [i for i in r.features if i not in FEATURES]
    for i in unknown:
        errors.append(f"Unbekannter Baustein: {i}")
    if unknown:
        return errors
    ids = resolve_features(r.features)
    for i in ids:
        f = FEATURES[i]
        for c in f.conflicts:
            if c in ids and i < c:
                errors.append(f"'{f.title}' passt nicht zusammen mit '{FEATURES[c].title}'.")
        if f.needs_desktop and r.desktop == "none":
            errors.append(f"'{f.title}' braucht einen Desktop (bei \"Kein Desktop\" nicht sinnvoll).")
    return errors


def package_list(r: Recipe) -> list:
    """Alle Pakete des Systems (ohne Doppelte, feste Reihenfolge)."""
    pk = []

    def add(names):
        for n in names:
            if n not in pk:
                pk.append(n)

    add(("live-boot", "live-config", "sudo", "network-manager", "locales"))
    add(DESKTOPS[r.desktop]["packages"])
    lang = r.locale.split("_")[0]
    if lang in LANG_TASKS:
        add((f"task-{LANG_TASKS[lang]}",))
        if r.desktop != "none" and LANG_TASKS[lang] not in LANG_WITHOUT_DESKTOP_TASK:
            add((f"task-{LANG_TASKS[lang]}-desktop",))
    for i in resolve_features(r.features):
        f = FEATURES[i]
        add(f.packages)
        for d, extra in f.desktop_extras:
            if d == r.desktop:
                add(extra)
    add(r.extra_packages)
    return pk


def boot_params(r: Recipe) -> list:
    """Kernel-Parameter des Live-Systems (Standard + Bausteine + eigene)."""
    params = ["boot=live", "components", "quiet", "splash", f"locales={r.locale}", f"keyboard-layouts={r.keyboard}",
              f"timezone={r.timezone}", f"hostname={r.hostname}", f"username={r.username}"]
    for i in resolve_features(r.features):
        for p in FEATURES[i].boot_params:
            if p not in params:
                params.append(p)
    for p in r.extra_boot_params:
        if p not in params:
            params.append(p)
    return params


def needs_non_free(r: Recipe) -> bool:
    return any(FEATURES[i].needs_non_free for i in resolve_features(r.features))


def estimate_size_mb(r: Recipe) -> int:
    """Grobe Schätzung der ISO-Größe (nur zur Orientierung, +/- 30 %)."""
    total = 600 + DESKTOPS[r.desktop]["size_mb"]
    for i in resolve_features(r.features):
        total += FEATURES[i].size_mb
    return total + 8 * len(r.extra_packages)
