"""Bildschirmfoto einer Hyper-V-VM (WMI GetVirtualSystemThumbnailImage, RGB565 -> PNG). Administrator noetig."""
import base64
import struct
import subprocess
import zlib
from pathlib import Path

PS = r"""
$ErrorActionPreference = 'Stop'
$ns = 'root\virtualization\v2'
$vm = Get-CimInstance -Namespace $ns -ClassName Msvm_ComputerSystem -Filter "ElementName='@VM@'"
$svc = Get-CimInstance -Namespace $ns -ClassName Msvm_VirtualSystemManagementService
$sd = Get-CimAssociatedInstance -InputObject $vm -ResultClassName Msvm_VirtualSystemSettingData | Where-Object { $_.VirtualSystemType -eq 'Microsoft:Hyper-V:System:Realized' } | Select-Object -First 1
$r = Invoke-CimMethod -InputObject $svc -MethodName GetVirtualSystemThumbnailImage -Arguments @{TargetSystem=$sd; WidthPixels=[uint16]@W@; HeightPixels=[uint16]@H@}
[Convert]::ToBase64String([byte[]]$r.ImageData)
"""


def write_png(path, w, h, rgb):
    raw = b"".join(b"\x00" + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def _save565(path, data, w, h):
    rgb = bytearray(w * h * 3)
    for i in range(w * h):
        v = data[2 * i] | (data[2 * i + 1] << 8)
        rgb[3 * i] = ((v >> 11) & 31) * 255 // 31
        rgb[3 * i + 1] = ((v >> 5) & 63) * 255 // 63
        rgb[3 * i + 2] = (v & 31) * 255 // 31
    write_png(path, w, h, bytes(rgb))


def shot(vm_name, path, w=800, h=600):
    script = PS.replace("@VM@", vm_name).replace("@W@", str(w)).replace("@H@", str(h))
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                       capture_output=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[:300])
    data = base64.b64decode(r.stdout.decode().strip())
    if len(data) == w * h * 2 + 4:                                # 4 Zusatzbytes: Anfang oder Ende? -> beide Varianten speichern
        p = Path(path)
        for tag, part in (("a", data[:w * h * 2]), ("b", data[4:])):
            _save565(p.with_name(p.stem + tag + p.suffix), part, w, h)
        return len(data)
    if len(data) == w * h * 2:                                    # RGB565, little endian
        rgb = bytearray(w * h * 3)
        for i in range(w * h):
            v = data[2 * i] | (data[2 * i + 1] << 8)
            rgb[3 * i] = ((v >> 11) & 31) * 255 // 31
            rgb[3 * i + 1] = ((v >> 5) & 63) * 255 // 63
            rgb[3 * i + 2] = (v & 31) * 255 // 31
    elif len(data) == w * h * 4:                                  # BGRA
        rgb = bytearray(w * h * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = data[2::4], data[1::4], data[0::4]
    else:
        raise RuntimeError(f"unerwartete Bildgroesse: {len(data)} Bytes")
    write_png(path, w, h, bytes(rgb))
    return len(data)
