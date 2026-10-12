"""
Generates the AutoTyper app icon (icon.png, icon.ico, icon.icns) with pure Python:
no Pillow or other packages needed.

    python assets/make_icons.py        (writes into assets/icons/)

The icon is a rounded indigo square with three lines of text and a blinking caret.
"""

import math
import os
import struct
import zlib

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

C1 = (108, 119, 242)   # gradient start (top-left)
C2 = (59, 69, 201)     # gradient end (bottom-right)
WHITE = (255, 255, 255)
CARET = (255, 209, 102)

# unit-square geometry: (x0, y0, x1, y1)
BARS = [(0.20, 0.285, 0.80, 0.360), (0.20, 0.445, 0.68, 0.520), (0.20, 0.605, 0.50, 0.680)]
CARET_BOX = (0.545, 0.570, 0.590, 0.715)


def _rrect_sd(px, py, box, r):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2 - r, (y1 - y0) / 2 - r
    qx, qy = abs(px - cx) - hx, abs(py - cy) - hy
    outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
    inside = min(max(qx, qy), 0.0)
    return outside + inside - r


def render(size):
    """RGBA bytes for a size x size icon, antialiased with a distance field."""
    px_unit = 1.0 / size
    rows = []
    bg_box = (0.04, 0.04, 0.96, 0.96)
    bg_r = 0.215
    for j in range(size):
        y = (j + 0.5) * px_unit
        row = bytearray()
        for i in range(size):
            x = (i + 0.5) * px_unit
            cov_bg = min(max(0.5 - _rrect_sd(x, y, bg_box, bg_r) / px_unit, 0.0), 1.0)
            if cov_bg <= 0.0:
                row += b"\x00\x00\x00\x00"
                continue
            t = (x + y) / 2
            r = C1[0] + (C2[0] - C1[0]) * t
            g = C1[1] + (C2[1] - C1[1]) * t
            b = C1[2] + (C2[2] - C1[2]) * t
            # glyph: text lines
            g_cov = 0.0
            for box in BARS:
                h = (box[3] - box[1]) / 2
                c = min(max(0.5 - _rrect_sd(x, y, box, h) / px_unit, 0.0), 1.0)
                g_cov = max(g_cov, c)
            if g_cov > 0.0:
                a = g_cov * 0.96
                r, g, b = (r + (WHITE[0] - r) * a, g + (WHITE[1] - g) * a, b + (WHITE[2] - b) * a)
            c_cov = min(max(0.5 - _rrect_sd(x, y, CARET_BOX, (CARET_BOX[2] - CARET_BOX[0]) / 2) / px_unit,
                            0.0), 1.0)
            if c_cov > 0.0:
                r, g, b = (r + (CARET[0] - r) * c_cov, g + (CARET[1] - g) * c_cov,
                           b + (CARET[2] - b) * c_cov)
            row += bytes((int(r + 0.5), int(g + 0.5), int(b + 0.5), int(cov_bg * 255 + 0.5)))
        rows.append(bytes(row))
    return rows


def png_bytes(size):
    rows = render(size)
    raw = b"".join(b"\x00" + r for r in rows)  # filter type 0 per scanline

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def build_ico(pngs, sizes=(16, 24, 32, 48, 64, 128, 256)):
    entries, blobs = b"", b""
    offset = 6 + 16 * len(sizes)
    for s in sizes:
        data = pngs[s]
        entries += struct.pack("<BBBBHHII", 0 if s >= 256 else s, 0 if s >= 256 else s,
                               0, 0, 1, 32, len(data), offset)
        blobs += data
        offset += len(data)
    return struct.pack("<HHH", 0, 1, len(sizes)) + entries + blobs


ICNS_TYPES = [(b"icp4", 16), (b"icp5", 32), (b"icp6", 64), (b"ic07", 128), (b"ic08", 256),
              (b"ic09", 512), (b"ic10", 1024), (b"ic11", 32), (b"ic12", 64), (b"ic13", 256),
              (b"ic14", 512)]


def build_icns(pngs):
    body = b""
    for tag, s in ICNS_TYPES:
        data = pngs[s]
        body += tag + struct.pack(">I", 8 + len(data)) + data
    return b"icns" + struct.pack(">I", 8 + len(body)) + body


def main():
    needed = sorted({16, 24, 32, 48, 64, 128, 256, 512, 1024})
    pngs = {s: png_bytes(s) for s in needed}
    for name, data in (("icon.png", pngs[512]), ("icon.ico", build_ico(pngs)),
                       ("icon.icns", build_icns(pngs))):
        with open(os.path.join(HERE, name), "wb") as fh:
            fh.write(data)
        print("wrote", name, len(data), "bytes")


if __name__ == "__main__":
    main()
