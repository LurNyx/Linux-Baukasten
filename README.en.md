# Linux-Baukasten ("Linux building kit") – English guide

**Build your own Linux with a few clicks.** A small program with a GUI (a single **EXE** for Windows, or plain Python everywhere) where you pick a base system,
a desktop and any number of **building blocks** – and get a bootable **ISO**: a **live system for a USB stick**, with an **installer**, a **rescue system**, a
**disposable (Tails-like) system** and more. The interface is in German.

> ⚠️ **Alpha (0.1).** The catalog and the project generator are tested and every package name is verified against the real Debian archive. End-to-end ISO
> builds are being proven with real CI runs – see [Test status](#test-status-honest). German main README: [README.md](README.md).

## What you can build

Eight presets (disposable Tails-like system with pull-the-stick-to-wipe, Kali-like security toolbox, Ubuntu/Mint-like everyday system, SystemRescue-like rescue system,
developer workstation, gaming live system, minimal console server, lightweight system for old PCs) – each just a starting point. Combine **7 desktops** (Xfce, GNOME,
KDE Plasma, LXQt, MATE, Cinnamon, i3) or none with **55 building blocks** in 10 categories: live behaviour (**amnesic**, **persistence**, encrypted persistence, **toram**),
**installer** (Calamares or Debian-Installer), security (firewall, AppArmor, kernel hardening, MAC randomisation, Tor, VPN), pentest, office, development, games, rescue,
server and comfort (Flatpak/Flathub, firmware, zram ...). Full list: [docs/BAUSTEINE.md](docs/BAUSTEINE.md) (German). Extra Debian packages and kernel parameters can be added by hand.

## How to use it

1. **Download** `Linux-Baukasten.exe` from the [Releases](https://github.com/LurNyx/Linux-Baukasten/releases/latest) page (Windows; SmartScreen may warn because the file is unsigned:
   *More info → Run anyway*), or run `python Linux-Baukasten.pyw` with Python 3 (no extra packages).
2. Pick a **preset** (tab 1), a **desktop** (tab 2), tick **building blocks** (tab 3), add extras (tab 4). Conflicts are resolved for you; the ISO size is estimated.
3. Tab 5 **"Bauen"**: **"Projekt exportieren"** writes a live-build project you can build anywhere with `sudo ./build.sh`, or **"ISO bauen"** builds directly using **WSL**, **Docker** or **Linux**.
4. Write the ISO to a USB stick (e.g. [Rufus](https://rufus.ie) or [balenaEtcher](https://etcher.balena.io)) and boot from it.

Headless: `python Linux-Baukasten.pyw --list`, `--export rescue --out ./my-rescue`, `--export my.baukasten.json`, then `sudo ./my-rescue/build.sh`.
A build needs **15 GB free disk**, **4 GB RAM**, internet and **20–60 minutes**; best on **Debian 12/13**, **WSL with Debian**, or **Docker** (`debian:trixie`).

## How it works

`Recipe (JSON) → catalog (blocks: packages, kernel parameters, files, hooks) → generator → live-build project → ISO`. Each block is a handful of data; the generator writes
`auto/config`, the package list, hooks and `includes.chroot`. The result is an ordinary live-build project you can edit by hand. The **amnesic** block ships the watcher from the sister project
[Kali Amnesic Stick](https://github.com/LurNyx/kali-amnesic-stick).

## Test status (honest)

**Automated** (`python tests/run_all.py`, runs on every push on Windows and Linux): recipe validation against hostile input, catalog consistency, the generator for every preset
including a shell syntax check of all generated scripts, build commands and cancellation, the GUI (real Tk), generated docs. **All package names** are checked against the Debian 13
archive (`python tools/check_packages.py`) – this already caught real mistakes (`kismet`, `radare2` and `task-english-desktop` don't exist there; `nikto`/`lutris` live in non-free/contrib).

**Real ISO build:** the workflow [“ISO bauen (echter Test)”](.github/workflows/build-iso.yml) builds an ISO in Docker (Debian 13); see [Actions](https://github.com/LurNyx/Linux-Baukasten/actions) and [docs/TESTSTAND.md](docs/TESTSTAND.md).

**Not verified:** booting built ISOs on real hardware (including Secure Boot), the installer (Calamares), persistence, the amnesic watcher inside a self-built system, and the "ISO bauen" button with WSL/Docker on Windows.
Reports are very welcome (issues).

## Roadmap
More bases (Ubuntu, Arch/archiso, Fedora; Debian "forky"), writing the USB stick straight from the program (technique from *Kali Amnesic Stick*), more blocks, custom blocks from files, English UI.

## Notes
Default live login is `user` / `live` – change it after boot. Tools with abuse potential (pentest, Wi-Fi, Windows password reset): use only on systems you own or have permission for.
Tor and the disposable system are **not** a replacement for Tails. "Debian" and "Kali" are trademarks of their owners; this project is not affiliated with either.
[MIT license](LICENSE), use at your own risk.

**Related project:** [Kali Amnesic Stick](https://github.com/LurNyx/kali-amnesic-stick) – Kali Linux as a live stick that wipes everything and powers off when you pull it.
