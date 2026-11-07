import sys, json, re, zlib, struct
src, ic, site, ver = sys.argv[1:5]
page = open(src).read()
lines = open(ic).read().split('\n')
block = '\n'.join(lines[2871:])  # update banner block from ignition-check mirror (line 2872 on)
block = block.replace('Ignition Check', 'The Workbench')
block = re.sub(r'var CURRENT_VERSION = "\d+";', 'var CURRENT_VERSION = "%s";' % ver, block)
assert block.count('CURRENT_VERSION = "%s"' % ver) == 1
head = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
 '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
 '<meta name="workbench-version" content="%s">'
 '<link rel="apple-touch-icon" href="apple-touch-icon.png"><link rel="icon" href="favicon.png" type="image/png">'
 '<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Workbench">'
 '<meta name="theme-color" content="#16181c"><link rel="manifest" href="manifest.webmanifest">'
 '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
 'body{margin:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif}img{max-width:100%%}[hidden]{display:none!important}</style>'
 '</head><body>\n') % ver
open(site + '/index.html', 'w').write(head + page + '\n' + block.rstrip() + ('\n' if '</body>' in block else '\n</body></html>\n'))
json.dump({"version": ver}, open(site + '/version.json', 'w'), indent=2)
def png(n, path):
    bg, dot, R = (43, 85, 201), (170, 192, 245), n / 9
    rows = []
    for y in range(n):
        row = bytearray([0])
        for x in range(n):
            gx, gy = (x % (n/4)) - n/8, (y % (n/4)) - n/8
            row += bytes(dot if gx*gx + gy*gy < (R/2.2)**2 else bg)
        rows.append(bytes(row))
    raw = zlib.compress(b''.join(rows), 9)
    ch = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', n, n, 8, 2, 0, 0, 0)) + ch(b'IDAT', raw) + ch(b'IEND', b''))
import subprocess, os; subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_icon.py'), site], check=True)  # HAL-eye icons
json.dump({"name": "The Workbench", "short_name": "Workbench", "id": "./", "start_url": "./", "scope": "./",
  "display": "standalone", "background_color": "#eef1f4", "theme_color": "#16181c",
  "description": "Launcher for in-progress apps and automated tasks",
  "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]},
  open(site + '/manifest.webmanifest', 'w'), indent=2)
