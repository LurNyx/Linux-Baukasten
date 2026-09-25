#!/usr/bin/env python3
"""Hyper-V-Pruefung einer mit dem Linux-Baukasten GEBAUTEN ISO (Administrator noetig).
Schreibt die ISO mit dem getesteten Roh-Schreiber (Projekt kali-amnesic-stick) auf eine virtuelle Platte, startet sie in einer Gen2-VM
(Secure Boot aus), loggt sich ueber die serielle Konsole ein (user/live), prueft den Waechter und 'zieht' dann die Platte.
Aufruf (als Administrator):  python tools/hyperv/verify_iso.py ISO [--mem MB] [--keep] [--no-enter]

Voraussetzungen: Windows Pro mit Hyper-V, ca. 5 GB freier Platz, ca. 1,5 GB freier RAM und ein Checkout des Projekts
https://github.com/LurNyx/kali-amnesic-stick (Umgebungsvariable KAS_DIR, sonst ein Ordner "KaliAmnesicStick" neben diesem Projekt).
Gedacht fuer die Vorlage "tools/calibration/test-tails-serial.baukasten.json" (serielle Konsole, Waechter "amnesic"). Das Skript
schreibt nur auf seine EIGENE virtuelle Platte (vor dem Schreiben wird geprueft, dass es eine Datei-Platte ist), nie auf echte Sticks.
Ergebnis: verify_iso.log, verify_iso_serial.log, vmshots/*.png (Bildschirmfotos der VM).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

KAS = Path(os.environ.get("KAS_DIR") or Path(__file__).resolve().parents[3] / "KaliAmnesicStick")
if not (KAS / "kas").is_dir():
    raise SystemExit(f"kali-amnesic-stick nicht gefunden ({KAS}). Bitte auschecken und KAS_DIR setzen.")
sys.path.insert(0, str(KAS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ["KAS_ALLOW_VIRTUAL"] = "1"

from kas.disks_windows import WindowsBackend, ps  # noqa: E402

HERE = Path(__file__).resolve().parent
LOG = HERE / "verify_iso.log"
SERIAL = HERE / "verify_iso_serial.log"
VM = "lb-verify-vm"
PIPE = r"\\.\pipe\lb-verify-com1"
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[()][A-Z0-9]|\x1b[=>]|\x1b\][^\x07\x1b]*(\x07|\x1b\\)")
LOG.write_text("", encoding="utf-8")


def log(msg):
    print(msg, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def psx(script, timeout=300):
    return ps("$ErrorActionPreference = 'Stop'; " + script, timeout)


def diskpart(script: str, work: Path) -> str:
    f = work / "dp.txt"
    f.write_text(script, encoding="ascii")
    r = subprocess.run(["diskpart", "/s", str(f)], capture_output=True)
    out = r.stdout.decode("cp850", "replace")
    if r.returncode != 0:
        raise RuntimeError("diskpart fehlgeschlagen: " + out[-400:])
    return out


def vdisk_number(vhd: Path) -> int:
    out = ps("Get-Disk | Where-Object { $_.Location -like '*" + vhd.name + "' } | ForEach-Object { $_.Number }")
    nums = [int(x) for x in out.split() if x.strip().isdigit()]
    assert len(nums) == 1, f"virtuelle Platte nicht eindeutig: {nums}"
    n = nums[0]
    assert ps(f"(Get-Disk -Number {n}).BusType").strip() == "File Backed Virtual", "SICHERHEIT: keine Test-VHDX"
    return n


class Console:
    def __init__(self):
        self.buf, self.lock, self.wlock, self.f, self.eof, self.t_eof = bytearray(), threading.Lock(), threading.Lock(), None, False, None
        self.dump = open(SERIAL, "wb")

    def connect(self, timeout=120):
        end, last = time.time() + timeout, None
        while time.time() < end:
            try:
                self.f = open(PIPE, "r+b", buffering=0)
                threading.Thread(target=self._reader, daemon=True).start()
                return
            except OSError as e:
                last = e
                time.sleep(1)
        raise RuntimeError(f"serielle Konsole nicht erreichbar: {last}")

    def _avail(self):
        import ctypes
        import msvcrt
        from ctypes import wintypes
        avail = wintypes.DWORD(0)
        if not ctypes.windll.kernel32.PeekNamedPipe(wintypes.HANDLE(msvcrt.get_osfhandle(self.f.fileno())), None, 0, None,
                                                    ctypes.byref(avail), None):
            raise OSError("Pipe geschlossen")
        return avail.value

    def _reader(self):
        while True:
            try:
                n = self._avail()
                if n == 0:
                    time.sleep(0.05)
                    continue
                with self.wlock:
                    data = self.f.read(min(n, 4096))
            except (OSError, ValueError):
                break
            if not data:
                break
            with self.lock:
                self.buf += data
            self.dump.write(data)
            self.dump.flush()
        self.eof, self.t_eof = True, time.time()

    def text(self):
        with self.lock:
            raw = bytes(self.buf)
        return ANSI.sub("", raw.decode("utf-8", "replace").replace("\r", ""))

    def send(self, s):
        with self.wlock:
            self.f.write(s.encode())

    def wait_for(self, pattern, timeout, start=0):
        end, rx = time.time() + timeout, re.compile(pattern, re.I)
        while time.time() < end:
            m = rx.search(self.text()[start:])
            if m:
                return m
            if self.eof:
                return None
            time.sleep(0.5)
        return None


def shell(con, cmd, n, timeout=60):
    tag = f"__D{n}__"
    pos = len(con.text())
    con.send(f"{cmd} ; echo {tag}$?\r")
    m = con.wait_for(rf"{tag}(\d+)", timeout, start=pos)
    if not m:
        return "(keine Antwort)", None
    out = con.text()[pos:]
    out = out[:out.index(m.group(0))]
    return "\n".join(out.split("\n")[1:]).strip(), int(m.group(1))


def main() -> int:
    from ctypes import windll
    if not windll.shell32.IsUserAnAdmin():
        log("FEHLER: Administrator-Rechte noetig")
        return 2
    args = sys.argv[1:]
    iso = Path(args[0])
    mem = int(args[args.index("--mem") + 1]) if "--mem" in args else 1536
    keep = "--keep" in args
    work = Path(tempfile.mkdtemp(prefix="lb-verify-"))
    vhdx = work / "lb_verify.vhdx"
    be = WindowsBackend(allow_virtual=True)
    res = {"ok": False}
    vm_created, con, attached = False, None, False
    try:
        assert iso.is_file(), f"ISO fehlt: {iso}"
        psx("Get-Command New-VM | Out-Null")
        free_gb = shutil.disk_usage(work).free / 2**30
        log(f"ISO: {iso.name} ({iso.stat().st_size / 2**30:.2f} GiB), freier Platz {free_gb:.1f} GiB, VM-RAM {mem} MB")
        assert free_gb > iso.stat().st_size / 2**30 * 1.5 + 2, "zu wenig Platz"
        diskpart(f'create vdisk file="{vhdx}" maximum=8192 type=expandable\nselect vdisk file="{vhdx}"\nattach vdisk\n', work)
        attached = True
        n = vdisk_number(vhdx)
        usable, _ = be.list_disks()
        disk = next(d for d in usable if d.id == str(n))
        log(f"== Schreibe die selbst gebaute ISO mit dem Roh-Schreiber (Datentraeger {n}) ...")
        t = time.time()
        be.flash(disk, iso, False)
        log(f"   geschrieben und geprueft in {time.time() - t:.0f} s")
        diskpart(f'select vdisk file="{vhdx}"\ndetach vdisk\n', work)
        attached = False

        psx(f"if (Get-VM -Name {VM} -ErrorAction SilentlyContinue) {{ Stop-VM -Name {VM} -TurnOff -Force -ErrorAction SilentlyContinue; Remove-VM -Name {VM} -Force }}")
        psx(f"New-VM -Name {VM} -Generation 2 -MemoryStartupBytes {mem}MB -NoVHD -Path '{work}' | Out-Null; "
            f"Set-VM -Name {VM} -CheckpointType Disabled -AutomaticStartAction Nothing -AutomaticStopAction TurnOff; "
            f"Set-VMMemory -VMName {VM} -DynamicMemoryEnabled $false -StartupBytes {mem}MB; Set-VMProcessor -VMName {VM} -Count 2; "
            f"Set-VMFirmware -VMName {VM} -EnableSecureBoot Off; "
            f"Add-VMHardDiskDrive -VMName {VM} -ControllerType SCSI -Path '{vhdx}'; "
            f"Set-VMFirmware -VMName {VM} -FirstBootDevice (Get-VMHardDiskDrive -VMName {VM}); "
            f"Set-VMComPort -VMName {VM} -Number 1 -Path '{PIPE}'")
        vm_created = True
        free_mb = int(psx("[int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1024)").strip() or 0)
        log(f"Freier RAM des Rechners: {free_mb} MB")
        psx(f"Start-VM -Name {VM}")
        t_start = time.time()
        log("VM gestartet (Secure Boot aus).")
        con = Console()
        con.connect(120)
        import vmshot
        shots = HERE / "vmshots"
        shots.mkdir(exist_ok=True)
        got_login = False
        import vmkey
        for i in range(24):                                       # bis ~6 Minuten, alle 15 s ein Bildschirmfoto der VM
            if con.wait_for(r"login:", 15):
                got_login = True
                break
            try:
                if i in (1, 2) and "--no-enter" not in sys.argv:  # Bootmenue wartet ohne Zeitlimit -> Enter druecken
                    log(f"Enter ans Bootmenue gesendet: {vmkey.press(VM, 13)}")
                vmshot.shot(VM, shots / f"t{int(time.time() - t_start):04d}.png")
            except Exception as e:
                log(f"(Bildschirmfoto/Taste fehlgeschlagen: {e})")
        if not got_login:
            log("FEHLER: kein Login-Prompt. Konsole (%d Zeichen), letzte Ausgabe:\n" % len(con.text()) + con.text()[-1500:])
            log(f"VM-Status: {psx(f'(Get-VM -Name {VM}).State').strip()}; Bildschirmfotos in {shots}")
            return 1
        log(f"Login-Prompt nach {time.time() - t_start:.0f} s")
        pos = len(con.text())
        con.send("user\r")
        if not con.wait_for(r"passwor[dt]:", 30, start=pos):
            log("FEHLER: kein Passwort-Prompt")
            return 1
        con.send("live\r")
        ready, end = False, time.time() + 120
        while time.time() < end and not ready:
            if con.wait_for(r"user@\S+:\S*\$", 20):
                for _ in range(6):
                    p = len(con.text())
                    con.send("echo READY$((6*7))\r")
                    if con.wait_for(r"READY42", 6, start=p):
                        ready = True
                        break
        if not ready:
            log("FEHLER: Login fehlgeschlagen. Ausgabe:\n" + con.text()[-800:])
            return 1
        log("Eingeloggt (user).")
        checks, seq = {}, 0
        for name, cmd in (("os", "grep -E '^(PRETTY_NAME|VERSION_CODENAME)=' /etc/os-release"),
                          ("cmdline", "cat /proc/cmdline"),
                          ("dienst", "systemctl is-active amnesic-watch"),
                          ("watchlog", "cat /run/amnesic-watch.log"),
                          ("medium", "grep -E ' /run/live/medium ' /proc/self/mountinfo"),
                          ("ufw", "systemctl is-active ufw"),
                          ("sysctl", "sysctl -n kernel.kptr_restrict kernel.dmesg_restrict"),
                          ("mac", "cat /etc/NetworkManager/conf.d/00-baukasten-mac-random.conf | head -3"),
                          ("desktop", "systemctl is-active lightdm"),
                          ("pakete", "dpkg -l | grep -c '^ii'"),
                          ("speicher", "grep -E 'MemTotal|MemAvailable' /proc/meminfo")):
            seq += 1
            out, rc = shell(con, cmd, seq)
            checks[name] = (out, rc)
            log(f"  [{name}] rc={rc}\n" + "\n".join("      " + ln for ln in out.splitlines()[:6]))
        res["cmdline_ok"] = re.search(r"\bamnesic(=fast)?\b", checks["cmdline"][0]) is not None
        res["service_active"] = checks["dienst"][0].strip().endswith("active") and "inactive" not in checks["dienst"][0]
        res["watching"] = "ueberwache" in checks["watchlog"][0]

        mark = len(con.text())
        log("\n>>> Entferne die Platte aus der laufenden VM (= Stick abziehen) ...")
        t0 = time.time()
        psx(f"Remove-VMHardDiskDrive -VMName {VM} -ControllerType SCSI -ControllerNumber 0 -ControllerLocation 0")
        t_removed = time.time()
        state = None
        while time.time() - t_removed < 180:
            state = psx(f"(Get-VM -Name {VM}).State").strip()
            if state == "Off":
                break
            time.sleep(1)
        res.update(state=state, off_after=time.time() - t_removed)
        log(f"VM-Status nach dem Entfernen: {state}; aus nach ca. {res['off_after']:.1f} s")
        tail = con.text()[mark:]
        if tail.strip():
            log("Konsolenausgabe nach dem Entfernen:\n" + "\n".join("      " + ln for ln in tail.strip().splitlines()[-8:]))
        res["ok"] = state == "Off" and res["cmdline_ok"] and res["service_active"] and res["watching"]
    except Exception:
        log("FEHLER:\n" + traceback.format_exc())
    finally:
        try:
            if vm_created:
                psx(f"Stop-VM -Name {VM} -TurnOff -Force -ErrorAction SilentlyContinue; Remove-VM -Name {VM} -Force")
        except Exception as e:
            log(f"(VM entfernen: {e})")
        if attached:
            try:
                diskpart(f'select vdisk file="{vhdx}"\ndetach vdisk\n', work)
            except Exception:
                pass
        if con is not None:
            try:
                con.dump.close()
            except Exception:
                pass
        time.sleep(2)
        if not keep:
            shutil.rmtree(work, ignore_errors=True)
    log("\nERGEBNIS: " + ("BESTANDEN" if res["ok"] else "FEHLGESCHLAGEN") + f" {res}")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
