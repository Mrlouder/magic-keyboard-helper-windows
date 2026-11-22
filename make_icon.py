"""Magic Keyboard Helper tray icon generator (no dependencies, Python stdlib only).

Style: minimal white line drawing on a transparent background: rounded keyboard
outline, two offset rows of keys and a space bar. The 16, 20 and 24 px sizes are
designed by hand, pixel by pixel; the larger ones are scaled from the 24 px design
with anti-aliasing.

Charging variant: the same drawing with a round "badge" cut out of the bottom right
corner and a green bolt in it. The clean round cut-out leaves no jagged keyboard
fragments around the bolt, even at 16-20 px.

Low battery variant: the same cut-out with an orange dot in it.

Output: magic_keyboard.ico, magic_keyboard_charging.ico, magic_keyboard_low.ico
(16, 20, 24, 32, 40, 48, 64, 256 px) and icon_preview.png (one row each: normal,
charging, low).
Run:  python make_icon.py
"""
import math
import os
import struct
import zlib

SIZES = [16, 20, 24, 32, 40, 48, 64, 256]
HERE = os.path.dirname(os.path.abspath(__file__))
COLOR = (0xFF, 0xFF, 0xFF)
BOLT_COLOR = (0x4A, 0xDE, 0x80)       # green: charging
LOW_COLOR = (0xFB, 0xA3, 0x1E)        # orange: low battery
LOW_DOT = 0.62                        # radius of the orange dot relative to the badge circle

# Outline of the bolt in a unit square (x, y), fitted into the badge circle
BOLT = [(0.68, 0.00), (0.06, 0.60), (0.46, 0.60), (0.32, 1.00), (0.94, 0.38), (0.54, 0.38)]
# Badge circle (centre x, y, radius) per size; the larger sizes are scaled from 24
BADGE = {16: (12.0, 12.0, 4.0), 20: (15.0, 15.0, 5.0), 24: (18.0, 18.0, 6.0)}
BOLT_W, BOLT_H = 1.40, 1.95           # the bolt's box in multiples of the radius

# Hand-made designs in pixel coordinates: outline (x0, y0, x1, y1), line width, corner
# radius, keys and space bar as rectangles (x0, y0, x1, y1), end point excluded.
SPECS = {
    16: {  # 1 px line; because of the half pixel shift the key rows are not offset here
        "frame": (0, 2, 15, 13), "t": 1, "r": 2.5,
        "keys": [(2, 4, 4, 6), (5, 4, 7, 6), (8, 4, 10, 6), (11, 4, 13, 6),
                 (2, 7, 4, 9), (5, 7, 7, 9), (8, 7, 10, 9), (11, 7, 13, 9)],
        "space": (5, 10, 10, 11),
    },
    20: {
        "frame": (0, 3, 20, 17), "t": 2, "r": 3.5,
        "keys": [(3, 6, 5, 8), (7, 6, 9, 8), (11, 6, 13, 8), (15, 6, 17, 8),
                 (5, 9, 7, 11), (9, 9, 11, 11), (13, 9, 15, 11)],
        "space": (5, 12, 15, 14),
    },
    24: {
        "frame": (1, 4, 23, 20), "t": 2, "r": 4,
        "keys": [(5, 8, 7, 10), (9, 8, 11, 10), (13, 8, 15, 10), (17, 8, 19, 10),
                 (7, 11, 9, 13), (11, 11, 13, 13), (15, 11, 17, 13)],
        "space": (7, 14, 17, 16),
    },
}


def scaled_spec(S):
    """The larger sizes are made from the 24 px design, with rounded keys."""
    base = SPECS[24]
    f = S / 24
    sc = lambda r: tuple(v * f for v in r)
    return {
        "frame": sc(base["frame"]), "t": base["t"] * f, "r": base["r"] * f,
        "keys": [sc(k) for k in base["keys"]], "space": sc(base["space"]),
        "key_r": 0.6 * f,
    }


def rrect_sdf(px, py, x0, y0, x1, y1, r):
    """Signed distance function of a rounded rectangle (negative = inside)."""
    r = max(0.0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    qx, qy = abs(px - cx) - ((x1 - x0) / 2 - r), abs(py - cy) - ((y1 - y0) / 2 - r)
    return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r


def coverage(sdf):
    return min(1.0, max(0.0, 0.5 - sdf))


def badge_geometry(S):
    if S in BADGE:
        bcx, bcy, R = BADGE[S]
    else:
        f = S / 24
        bcx, bcy, R = (v * f for v in BADGE[24])
    bx0, by0 = bcx - BOLT_W * R / 2, bcy - BOLT_H * R / 2
    pts = [(bx0 + u * BOLT_W * R, by0 + v * BOLT_H * R) for u, v in BOLT]
    return (bcx, bcy, R), pts


def in_polygon(px, py, pts):
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        (xi, yi), (xj, yj) = pts[i], pts[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def bolt_coverage(cx, cy, pts, n=5):
    """Bolt coverage of one pixel, with n x n sampling (anti-aliasing)."""
    hits = 0
    for sy in range(n):
        for sx in range(n):
            hits += in_polygon(cx - 0.5 + (sx + 0.5) / n, cy - 0.5 + (sy + 0.5) / n, pts)
    return hits / (n * n)


def render(S, badge=None):
    """badge: None (normal), "charging" (green bolt) or "low" (orange dot)."""
    charging = badge is not None
    sp = SPECS.get(S) or scaled_spec(S)
    x0, y0, x1, y1 = sp["frame"]
    t, r = sp["t"], sp["r"]
    key_r = sp.get("key_r", 0)
    shapes = sp["keys"] + [sp["space"]]
    if charging:
        (bcx, bcy, R), pts = badge_geometry(S)
        # Keys reaching into the circle are left out whole (no half-cut keys),
        # and the space bar is cut before the circle.
        clear = R + max(0.75, S / 24)
        def near(k):
            nx, ny = min(max(bcx, k[0]), k[2]), min(max(bcy, k[1]), k[3])
            return math.hypot(nx - bcx, ny - bcy) < clear
        sx0, sy0, sx1, sy1 = sp["space"]
        if near(sp["space"]):
            sx1 = min(sx1, bcx - math.sqrt(max(0.0, clear ** 2 - (max(sy0, min(bcy, sy1)) - bcy) ** 2)))
        shapes = [k for k in sp["keys"] if not near(k)] + ([(sx0, sy0, sx1, sy1)] if sx1 - sx0 >= 1 else [])
    px = bytearray(S * S * 4)
    for y in range(S):
        for x in range(S):
            cx, cy = x + 0.5, y + 0.5
            outer = coverage(rrect_sdf(cx, cy, x0, y0, x1, y1, r))
            inner = coverage(rrect_sdf(cx, cy, x0 + t, y0 + t, x1 - t, y1 - t, r - t))
            a = max(0.0, outer - inner)
            for (k0, k1, k2, k3) in shapes:
                if k0 - 1 <= cx <= k2 + 1 and k1 - 1 <= cy <= k3 + 1:
                    a = max(a, coverage(rrect_sdf(cx, cy, k0, k1, k2, k3, key_r)))
            col = COLOR
            if charging and math.hypot(cx - bcx, cy - bcy) < R + 1:
                ck = coverage(math.hypot(cx - bcx, cy - bcy) - R)   # round cut-out
                if badge == "low":
                    cb, bcol = coverage(math.hypot(cx - bcx, cy - bcy) - R * LOW_DOT), LOW_COLOR
                else:
                    cb, bcol = bolt_coverage(cx, cy, pts), BOLT_COLOR
                a_kb = a * (1 - ck)
                a = cb + a_kb * (1 - cb)
                if a > 0:
                    col = tuple((bcol[i] * cb + COLOR[i] * a_kb * (1 - cb)) / a for i in range(3))
            i = (y * S + x) * 4
            px[i:i + 4] = bytes((round(col[0]), round(col[1]), round(col[2]), round(a * 255)))
    return px


def png_bytes(W, H, rgba):
    raw = b"".join(b"\x00" + bytes(rgba[y * W * 4:(y + 1) * W * 4]) for y in range(H))
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def dib_bytes(S, rgba):
    """32-bit BGRA DIB icon entry (the most compatible for small sizes)."""
    hdr = struct.pack("<IiiHHIIiiII", 40, S, S * 2, 1, 32, 0, 0, 0, 0, 0, 0)
    rows = []
    for y in range(S - 1, -1, -1):
        row = bytearray()
        for x in range(S):
            r, g, b, a = rgba[(y * S + x) * 4:(y * S + x) * 4 + 4]
            row += bytes((b, g, r, a))
        rows.append(bytes(row))
    mask_row = b"\x00" * (((S + 31) // 32) * 4)
    return hdr + b"".join(rows) + mask_row * S


def write_preview(rows):
    """One icon variant per row: every size enlarged 8x, 1:1 below it, on a dark taskbar colour."""
    scale = 8
    small = [s for s in SIZES if s <= 64]
    W = sum(s * scale for s in small) + 20 * (len(small) + 1)
    row_h = 64 * scale + 40 + 64 + 20
    H = row_h * len(rows)
    canvas = bytearray(bytes((0x1C, 0x1C, 0x1C, 255)) * (W * H))

    def blit(img, S, ox, oy, z):
        for yy in range(S * z):
            for xx in range(S * z):
                si = ((yy // z) * S + xx // z) * 4
                r, g, b, a = img[si:si + 4]
                ci = ((oy + yy) * W + ox + xx) * 4
                al = a / 255
                canvas[ci:ci + 3] = bytes(round(c * al + bc * (1 - al)) for c, bc in zip((r, g, b), canvas[ci:ci + 3]))

    for ri, images in enumerate(rows):
        x0 = 20
        for S in small:
            blit(images[S], S, x0, ri * row_h + 20, scale)
            blit(images[S], S, x0, ri * row_h + 64 * scale + 40, 1)
            x0 += S * scale + 20
    with open(os.path.join(HERE, "icon_preview.png"), "wb") as f:
        f.write(png_bytes(W, H, canvas))


def write_ico(path, images):
    entries = [(S, png_bytes(S, S, images[S]) if S >= 256 else dib_bytes(S, images[S])) for S in SIZES]
    out = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    for S, data in entries:
        out += struct.pack("<BBBBHHII", S % 256, S % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    out += b"".join(d for _, d in entries)
    with open(path, "wb") as f:
        f.write(out)


def main():
    normal = {S: render(S) for S in SIZES}
    charging = {S: render(S, "charging") for S in SIZES}
    low = {S: render(S, "low") for S in SIZES}
    write_ico(os.path.join(HERE, "magic_keyboard.ico"), normal)
    write_ico(os.path.join(HERE, "magic_keyboard_charging.ico"), charging)
    write_ico(os.path.join(HERE, "magic_keyboard_low.ico"), low)
    write_preview([normal, charging, low])
    print("done:", ", ".join(f"{s}px" for s in SIZES))


if __name__ == "__main__":
    main()
