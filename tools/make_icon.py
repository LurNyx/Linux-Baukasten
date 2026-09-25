#!/usr/bin/env python3
"""Zeichnet das Programm-Symbol (drei Bausteine) und schreibt assets/icon.ico (PNG-Bilder in ICO-Datei, nur Standardbibliothek)."""
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def render(size: int) -> bytes:
    """RGBA-Pixel eines size x size Symbols: runder blauer Hintergrund, drei Bausteine (Kacheln)."""
    s = size
    px = bytearray(s * s * 4)

    def put(x, y, rgb, a=255):
        i = (y * s + x) * 4
        px[i:i + 4] = bytes((rgb[0], rgb[1], rgb[2], a))

    r_bg = s * 0.2
    for y in range(s):
        for x in range(s):
            # abgerundetes Quadrat
            dx = max(r_bg - x, x - (s - 1 - r_bg), 0)
            dy = max(r_bg - y, y - (s - 1 - r_bg), 0)
            if dx * dx + dy * dy <= r_bg * r_bg:
                t = y / s
                put(x, y, (int(28 + 30 * t), int(90 + 40 * t), int(200 - 30 * t)))

    def block(x0, y0, w, h, rgb):
        for y in range(int(y0), int(y0 + h)):
            for x in range(int(x0), int(x0 + w)):
                if 0 <= x < s and 0 <= y < s:
                    put(x, y, rgb)
                    if y == int(y0) or x == int(x0):                         # helle Kante oben/links
                        put(x, y, tuple(min(255, c + 45) for c in rgb))

    u = s / 8
    block(1.2 * u, 4.6 * u, 2.5 * u, 2.2 * u, (255, 255, 255))               # unten links
    block(4.3 * u, 4.6 * u, 2.5 * u, 2.2 * u, (255, 205, 60))                # unten rechts
    block(2.75 * u, 1.9 * u, 2.5 * u, 2.2 * u, (120, 230, 150))              # oben Mitte
    return bytes(px)


def png(size: int) -> bytes:
    px = render(size)
    raw = b"".join(b"\x00" + px[y * size * 4:(y + 1) * size * 4] for y in range(size))

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def ico(sizes=(16, 32, 48, 64, 128, 256)) -> bytes:
    images = [png(s) for s in sizes]
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, data = b"", b""
    for s, img in zip(sizes, images):
        entries += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(img), offset + len(data))
        data += img
    return head + entries + data


def main() -> int:
    out = ROOT / "assets" / "icon.ico"
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(ico())
    (ROOT / "assets" / "icon.png").write_bytes(png(256))
    print(f"{out} ({out.stat().st_size} Bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
