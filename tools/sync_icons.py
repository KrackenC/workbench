"""Copy each app's real icon (the one its GitHub Pages copy uses) into its Workbench card.

Usage (macOS, from the repo root): python3 -I tools/sync_icons.py
Picks the largest non-maskable manifest icon, else apple-touch-icon, else favicon; shrinks it to
96px with `sips`; and embeds it as a data: URI in src/workbench.html (the claude.ai copy can't load
outside images). Then rebuild with build_workbench.py and bump the version.
"""
import base64, json, os, re, subprocess, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'workbench.html')


def get(url):
    return subprocess.run(['curl', '-sSfL', '--max-time', '30', url], capture_output=True, check=True).stdout


def best_icon(base):
    html = get(base + '?_=%d' % time.time()).decode('utf8', 'ignore')
    head = html[:html.find('</head>') + 7] if '</head>' in html else html[:20000]
    cands = []
    m = re.search(r'<link[^>]*rel="manifest"[^>]*href="([^"]+)"', head) or re.search(r'<link[^>]*href="([^"]+)"[^>]*rel="manifest"', head)
    if m:
        try:
            for i in json.loads(get(base + m.group(1))).get('icons', []):
                purpose = i.get('purpose', 'any')
                if 'any' in purpose:
                    cands.append((max(int(x.split('x')[0]) for x in i.get('sizes', '0x0').split()), i['src']))
        except (subprocess.CalledProcessError, ValueError, KeyError):
            pass
    for rel, size in (('apple-touch-icon', 180), ('icon', 64)):
        for tag in re.findall(r'<link[^>]*rel="%s"[^>]*>' % rel, head):
            cands.append((size, re.search(r'href="([^"]+)"', tag).group(1)))
    href = max(cands)[1]
    if href.startswith('data:'):
        return base64.b64decode(href.split(',', 1)[1])
    return get(base + href)


page = open(SRC).read()
tmp = tempfile.mkdtemp()
# one match per app object; apps with no GitHub Pages copy (Shelf & Shaker) keep their current icon
pairs = [m.groups() for x in re.split(r'(?=\{ name: ")', page)
         for m in [re.match(r'\{ name: "([^"]+)"[^{]*?pages: "https://krackenc\.github\.io/([^/"]+)/"', x, flags=re.S)] if m]
for name, repo in pairs:
    raw = os.path.join(tmp, repo + '.img')
    open(raw, 'wb').write(best_icon('https://krackenc.github.io/%s/' % repo))
    jpeg = open(raw, 'rb').read(3) == b'\xff\xd8\xff'
    out = os.path.join(tmp, repo + ('.jpg' if jpeg else '.png'))
    subprocess.run(['sips', '-Z', '96', '-s', 'format', 'jpeg' if jpeg else 'png', raw, '--out', out], capture_output=True, check=True)
    uri = 'data:%s;base64,%s' % ('image/jpeg' if jpeg else 'image/png', base64.b64encode(open(out, 'rb').read()).decode())
    pat = r'(\{ name: "%s", glyph: "[^"]+", color: "[^"]+",)(\n    icon: "[^"]*",)?' % re.escape(name)
    page, n = re.subn(pat, lambda m: m.group(1) + '\n    icon: "%s",' % uri, page)
    assert n == 1, name
    print('%-15s %s, %d bytes' % (name, 'jpeg' if jpeg else 'png', os.path.getsize(out)))
open(SRC, 'w').write(page)
