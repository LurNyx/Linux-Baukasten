"""Feste Bausteine, die in erzeugte Systeme kopiert werden (Waechter des Projekts kali-amnesic-stick, MIT-Lizenz)."""

# Waechter: beobachtet das Live-Medium (/run/live/medium); verschwindet der Stick, wird die Sitzung beendet, RAM geloescht, ausgeschaltet.
# Modus aus der Kernel-Zeile: "amnesic" = voll (Bildschirm aus, alles beenden, Daten loeschen, RAM ueberschreiben, aus),
# "amnesic=fast" = nur beenden und sofort ausschalten.
AMNESIC_WATCH = r'''#!/usr/bin/env python3
"""amnesic-watch - Boot-Stick abgezogen => Live-System sofort beenden, alles loeschen, ausschalten (Tails-Prinzip)."""
import ctypes
import mmap
import os
import signal
import sys
import time

SYSRQ = "/proc/sysrq-trigger"
LOG = "/run/amnesic-watch.log"
MEDIUM_MOUNTS = ("/run/live/medium", "/lib/live/mount/medium")
USER_TMP_DIRS = ("/dev/shm", "/run/user", "/tmp", "/var/tmp")


def log(msg):
    line = "amnesic-watch: %s\n" % msg
    for path, mode, prefix in (("/dev/kmsg", "w", "<3>"), (LOG, "a", "")):       # <3> = sichtbar auf der Konsole
        try:
            with open(path, mode) as f:
                f.write(prefix + line)
        except OSError:
            pass


def medium_devnum(mountinfo, mounts=MEDIUM_MOUNTS):
    """major:minor des Geraets unter dem Live-Medium-Mountpoint (virtuelle 0:x-Geraete werden uebersprungen)."""
    found = None
    for line in mountinfo.splitlines():
        parts = line.split()
        if len(parts) > 4 and parts[4] in mounts and not parts[2].startswith("0:"):
            found = parts[2]
    return found


def disk_sysfs_path(majmin, root="/sys/dev/block"):
    """sysfs-Verzeichnis des GANZEN Datentraegers (bei einer Partition: das Elterngeraet)."""
    dev = os.path.realpath(os.path.join(root, majmin))
    if not os.path.isdir(dev):
        return None
    if os.path.exists(os.path.join(dev, "partition")):
        dev = os.path.dirname(dev)
    return dev


def lock_memory():
    """Alle Seiten dieses Prozesses im RAM festnageln: nach dem Abziehen darf nichts mehr vom Stick nachgeladen werden."""
    try:
        return ctypes.CDLL(None, use_errno=True).mlockall(1) == 0   # MCL_CURRENT
    except Exception:
        return False


def wait_for_removal(path, interval=0.1, exists=os.path.exists, sleep=time.sleep):
    while exists(path):
        sleep(interval)


def screen_off():
    """Bildschirm sofort dunkel (Hintergrundbeleuchtung aus): man sieht sofort, dass die Sitzung weg ist."""
    base = "/sys/class/backlight"
    try:
        names = os.listdir(base)
    except OSError:
        return 0
    n = 0
    for name in names:
        try:
            with open(os.path.join(base, name, "brightness"), "w") as f:
                f.write("0")
            n += 1
        except OSError:
            pass
    return n


def kill_all(keep=()):
    """SIGKILL an alle Prozesse ausser init (1), uns selbst und Kernel-Threads: Desktop, Browser, Terminals sind sofort weg."""
    me = os.getpid()
    killed = 0
    try:
        names = os.listdir("/proc")
    except OSError:
        return 0
    for name in names:
        if not name.isdigit():
            continue
        pid = int(name)
        if pid in (1, 2, me) or pid in keep:
            continue
        try:
            with open("/proc/%d/stat" % pid) as f:
                ppid = int(f.read().rsplit(")", 1)[1].split()[1])
            if ppid == 2:                                   # Kernel-Thread
                continue
            os.kill(pid, signal.SIGKILL)
            killed += 1
        except (OSError, ValueError, IndexError):
            pass
    return killed


def overlay_upperdirs(mountinfo):
    """upperdir-Pfade der overlayfs-Einhaengung von '/' = die RAM-Schicht des Live-Systems (alle Nutzerdaten)."""
    out = []
    for line in mountinfo.splitlines():
        head, sep, tail = line.partition(" - ")
        if not sep:
            continue
        h, t = head.split(), tail.split()
        if len(h) > 4 and h[4] == "/" and len(t) >= 3 and t[0] == "overlay":
            for opt in t[2].split(","):
                if opt.startswith("upperdir="):
                    out.append(opt[len("upperdir="):])
    return out


def rm_contents(path):
    """Alles unterhalb von path loeschen (der Ordner selbst bleibt). Fehler werden ignoriert. -> Anzahl."""
    try:
        names = os.listdir(path)
    except OSError:
        return 0
    n = 0
    for name in names:
        p = os.path.join(path, name)
        try:
            if os.path.isdir(p) and not os.path.islink(p):
                n += rm_contents(p)
                os.rmdir(p)
            else:
                os.unlink(p)
            n += 1
        except OSError:
            pass
    return n


def wipe_user_data():
    """Loescht alle Nutzerdaten im RAM: die overlay-Schicht (alles, was du im Live-System veraendert hast) + tmpfs-Ordner."""
    try:
        with open("/proc/self/mountinfo") as f:
            info = f.read()
    except OSError:
        info = ""
    n = 0
    for d in overlay_upperdirs(info):
        n += rm_contents(d)
    for d in USER_TMP_DIRS:
        n += rm_contents(d)
    return n


def wipe_memory(reserve=None):
    """Belegt den freien Arbeitsspeicher und ueberschreibt ihn (0xFF, dann 0x00)."""
    chunk, block = 64 << 20, 1 << 20

    def avail():
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
        return 0

    try:
        with open("/proc/self/oom_score_adj", "w") as f:
            f.write("-1000")
    except OSError:
        pass
    keep = reserve if reserve is not None else 96 << 20
    zero, maps = bytes(block), []
    try:
        while avail() > keep + chunk:
            m = mmap.mmap(-1, chunk)
            for _ in range(chunk // block):
                m.write(zero)
            maps.append(m)
    except (MemoryError, OSError):
        pass
    for pattern in (b"\xff", b"\x00"):
        buf = pattern * block
        for m in maps:
            m.seek(0)
            for _ in range(chunk // block):
                m.write(buf)
    return len(maps) * chunk


def power_off(fd, sleep=time.sleep):
    """sysrq: s = sync, u = alles read-only, o = ausschalten (b = Neustart, falls o nicht wirkt)."""
    for key in (b"s", b"u", b"o"):
        try:
            os.write(fd, key)
        except OSError:
            pass
        sleep(0.1)
    sleep(3)
    try:
        os.write(fd, b"b")
    except OSError:
        pass


def removal_sequence(mode, fd, steps=None):
    """Was beim Abziehen passiert. full: Bildschirm aus, alles beenden, Daten loeschen, RAM ueberschreiben, ausschalten.
    fast: Bildschirm aus, alles beenden, sofort ausschalten."""
    s = dict(log=log, screen_off=screen_off, kill_all=kill_all, wipe_user_data=wipe_user_data,
             wipe_memory=wipe_memory, power_off=power_off)
    s.update(steps or {})

    def safe(name):
        # Ein fehlgeschlagener Schritt darf NIE das Ausschalten verhindern.
        try:
            s[name]()
        except Exception as e:
            try:
                s["log"]("Schritt %s fehlgeschlagen: %r" % (name, e))
            except Exception:
                pass

    try:
        safe_log = s["log"]
        safe_log("Boot-Stick entfernt - beende Sitzung (Modus %s)" % mode)
    except Exception:
        pass
    try:
        safe("screen_off")
        safe("kill_all")
        if mode == "full":
            safe("wipe_user_data")
            safe("wipe_memory")
    finally:
        s["power_off"](fd)


def main():
    try:
        with open("/proc/cmdline") as f:
            tokens = f.read().split()
    except OSError:
        tokens = []
    mode = "fast" if "amnesic=fast" in tokens else "full"
    try:
        with open("/proc/sys/kernel/sysrq", "w") as f:
            f.write("1")
    except OSError:
        pass
    with open("/proc/self/mountinfo") as f:
        devnum = medium_devnum(f.read())
    disk = disk_sysfs_path(devnum) if devnum else None
    if not disk:
        log("Kein Boot-Stick gefunden (Live-Medium nicht erkannt) - Ueberwachung INAKTIV")
        return 1
    fd = os.open(SYSRQ, os.O_WRONLY)
    locked = lock_memory()
    log("ueberwache %s (Geraet %s, Modus: %s, mlock=%s) - Stick abziehen beendet die Sitzung"
        % (disk, devnum, mode, locked))
    wait_for_removal(disk)
    removal_sequence(mode, fd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

# Der Dienst startet nur, wenn "amnesic" oder "amnesic=fast" in der Kernel-Zeile steht (sonst ist er unwirksam).
AMNESIC_UNIT = """[Unit]
Description=Amnesic: bei Entfernen des Boot-Sticks sofort beenden und alles loeschen
ConditionKernelCommandLine=|amnesic
ConditionKernelCommandLine=|amnesic=fast
DefaultDependencies=no
After=local-fs.target
Before=sysinit.target shutdown.target
Conflicts=shutdown.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/sbin/amnesic-watch
OOMScoreAdjust=-1000
LimitMEMLOCK=infinity

[Install]
WantedBy=sysinit.target
"""
