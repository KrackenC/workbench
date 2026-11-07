"""HAL-style eye icon, pure Python (no PIL). Usage: python3 make_icon.py <out_dir>"""
import sys, math, zlib, struct

def lerp(a, b, t): return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
def ramp(stops, t):
    t = min(max(t, 0.0), 1.0)
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1: return lerp(c0, c1, (t - t0) / (t1 - t0) if t1 > t0 else 0)
    return stops[-1][1]

LENS = [(0.0, (255, 252, 220)), (0.05, (255, 220, 100)), (0.12, (255, 130, 25)), (0.24, (230, 32, 10)),
        (0.42, (125, 5, 4)), (0.65, (36, 2, 2)), (1.0, (8, 2, 3))]

def shade(x, y):  # x, y in [-1, 1], y down
    r = math.hypot(x, y)
    # background: dark brushed panel, slightly lighter at top
    bg = lerp((38, 41, 46), (14, 15, 18), (y + 1) / 2)
    bg = tuple(c + 3 * math.sin(y * 160) for c in bg)
    R_OUT, R_CHROME, R_BLACK = 0.78, 0.68, 0.60
    if r > R_OUT:
        return bg
    if r > R_CHROME:  # chrome bezel: light top-left, dark bottom-right, with a bevel
        ang = (-x - y) / (r * 1.414)
        bevel = 1 - abs((r - (R_OUT + R_CHROME) / 2) / ((R_OUT - R_CHROME) / 2))
        c = ramp([(0, (60, 64, 70)), (0.5, (150, 156, 164)), (1, (236, 240, 245))], (ang + 1) / 2)
        return lerp(c, (255, 255, 255), 0.15 * bevel)
    if r > R_BLACK:  # black inner ring
        return lerp((4, 4, 6), (30, 30, 34), max(0, -y) * 0.5)
    t = r / R_BLACK
    c = ramp(LENS, t)
    # specular glass reflection, upper left
    hx, hy = x + 0.24, y + 0.30
    hl = math.exp(-((hx / 0.16) ** 2 + (hy / 0.07) ** 2))
    c = lerp(c, (255, 255, 255), 0.55 * hl)
    # faint lower-right rim glint
    gl = math.exp(-(((x - 0.33) / 0.09) ** 2 + ((y - 0.36) / 0.05) ** 2))
    return lerp(c, (255, 190, 170), 0.25 * gl)

def png(n, path, ss=3):
    rows = []
    for py in range(n):
        row = bytearray([0])
        for px in range(n):
            acc = [0, 0, 0]
            for sy in range(ss):
                for sx in range(ss):
                    x = ((px + (sx + 0.5) / ss) / n) * 2 - 1
                    y = ((py + (sy + 0.5) / ss) / n) * 2 - 1
                    c = shade(x, y)
                    for i in range(3): acc[i] += c[i]
            row += bytes(int(min(255, max(0, v / (ss * ss)))) for v in acc)
        rows.append(bytes(row))
    ch = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', n, n, 8, 2, 0, 0, 0))
                           + ch(b'IDAT', zlib.compress(b''.join(rows), 9)) + ch(b'IEND', b''))

out = sys.argv[1] if len(sys.argv) > 1 else '.'
for n, name in [(512, 'icon-512.png'), (192, 'icon-192.png'), (180, 'apple-touch-icon.png'), (64, 'favicon.png')]:
    png(n, out + '/' + name)
