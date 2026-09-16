#!/usr/bin/env python3
# kit-pages-builder v3 — the share-xr-app skill compares this line with its own copy.
"""Assemble the GitHub Pages site from the kit apps in this repo.

Every folder holding an `xr-project.json` is one app. It is copied to
`_site/<slug>/`, taking the slug from the manifest rather than the folder
name — so "Planet Walk" is served at /planet-walk/ instead of
/Planet%20Walk/, which is the difference between a URL somebody can type
into a headset browser and one they cannot.

Each served app page also gets a **QR code of its own address** in the top
right corner, so a ClassVR headset can scan the screen of whoever has the
page open and jump straight into it. The address is known before the page
is live — it follows from the repository name — so the QR is right from the
first deploy and never changes afterwards; nothing in the app folder is
touched, the code is added to the copy in `_site/` only, at the very end of
the file (after `</a-scene>`), so the line numbers the app's error codes
refer to are unchanged.

A small index page lists whatever was found, each with the same QR. Run it
from the repo root:

    python3 .github/scripts/build_pages.py [--out _site] [--base-url URL]

Inside GitHub Actions the site's address comes from GITHUB_REPOSITORY
(`https://<owner>.github.io/<repo>/`, or the bare `https://<owner>.github.io/`
when the repo is named that way). A `CNAME` file at the repo root wins over
both, and `--base-url` / the PAGES_BASE_URL variable win over everything —
useful for a local preview. With no address at all the site still builds,
just without QR codes.

The QR encoder is built in (below): the runner's python has no pip, so the
builder must not depend on anything that needs installing.

Prints a one-line summary per app. Exit 0 even with no apps — an empty
repo should still publish its index rather than fail the deploy.
"""
import argparse
import html
import json
import os
import re
import shutil
import sys

# Copied into the site as-is; everything else in an app folder is skipped.
KEEP_SUFFIXES = ('.html', '.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.json')

# Never descend into these looking for apps.
SKIP_DIRS = {'.git', '.github', '.claude', '.agents', 'kit', 'node_modules', '_site', 'dist', '.preview'}


def find_apps(root):
    """Every directory with an xr-project.json, nearest the top first."""
    found = []
    for here, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith('.'))
        if 'xr-project.json' in files and os.path.abspath(here) != os.path.abspath(root):
            found.append(here)
            dirs[:] = []                      # apps do not nest inside apps
    return found


def slugify(text):
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return slug or 'app'


def read_manifest(app_dir):
    path = os.path.join(app_dir, 'xr-project.json')
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        print('  ! could not read %s (%s) — using the folder name' % (path, e), file=sys.stderr)
        return {}


def copy_app(app_dir, dest):
    """Copy the servable files of one app folder, flat plus one level of assets."""
    os.makedirs(dest, exist_ok=True)
    copied = 0
    for here, dirs, files in os.walk(app_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        rel = os.path.relpath(here, app_dir)
        target = dest if rel == '.' else os.path.join(dest, rel)
        os.makedirs(target, exist_ok=True)
        for name in files:
            if name.startswith('.') or not name.lower().endswith(KEEP_SUFFIXES):
                continue
            shutil.copy2(os.path.join(here, name), os.path.join(target, name))
            copied += 1
    return copied


# --- the site's address -----------------------------------------------------

def site_base_url(root, override=None):
    """Where this site will be served from, with a trailing slash — or None."""
    if override:
        return override.rstrip('/') + '/'
    env = os.environ.get('PAGES_BASE_URL')
    if env:
        return env.rstrip('/') + '/'
    cname = os.path.join(root, 'CNAME')
    if os.path.exists(cname):
        try:
            host = open(cname, encoding='utf-8').read().strip().split()[0]
            if host:
                return 'https://%s/' % host
        except (OSError, IndexError):
            pass
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    if '/' in repo:
        owner, name = repo.split('/', 1)
        owner = owner.lower()
        if name.lower() == owner + '.github.io':
            return 'https://%s.github.io/' % owner
        return 'https://%s.github.io/%s/' % (owner, name)
    return None


# --- a small QR code encoder, no dependencies -------------------------------
# Byte mode, error-correction level M, versions 1–40, all eight masks scored
# per the spec. Enough for a URL. Returns the module matrix (list of rows of
# bools). Written for the site builder so a GitHub runner with a bare python
# (no pip) can still draw the code.

_EC_M = [  # version -> (ec codewords per block, blocks in group 1, data cw per g1 block, blocks in group 2, data cw per g2 block)
    None,
    (10, 1, 16, 0, 0), (16, 1, 28, 0, 0), (26, 1, 44, 0, 0), (18, 2, 32, 0, 0), (24, 2, 43, 0, 0),
    (16, 4, 27, 0, 0), (18, 4, 31, 0, 0), (22, 2, 38, 2, 39), (22, 3, 36, 2, 37), (26, 4, 43, 1, 44),
    (30, 1, 50, 4, 51), (22, 6, 36, 2, 37), (22, 8, 37, 1, 38), (24, 4, 40, 5, 41), (24, 5, 41, 5, 42),
    (28, 7, 45, 3, 46), (28, 10, 46, 1, 47), (26, 9, 43, 4, 44), (26, 3, 44, 11, 45), (26, 3, 41, 13, 42),
    (26, 17, 42, 0, 0), (28, 17, 46, 0, 0), (28, 4, 47, 14, 48), (28, 6, 45, 14, 46), (28, 8, 47, 13, 48),
    (28, 19, 46, 4, 47), (28, 22, 45, 3, 46), (28, 3, 45, 23, 46), (28, 21, 45, 7, 46), (28, 19, 47, 10, 48),
    (28, 2, 46, 29, 47), (28, 10, 46, 23, 47), (28, 14, 46, 21, 47), (28, 14, 46, 23, 47), (28, 12, 47, 26, 48),
    (28, 6, 47, 34, 48), (28, 29, 46, 14, 47), (28, 13, 46, 32, 47), (28, 40, 47, 7, 48), (28, 18, 47, 31, 48),
]

_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11d
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _rs_generator(n):
    g = [1]
    for i in range(n):
        g = _poly_mul(g, [1, _EXP[i]])
    return g


def _poly_mul(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if not x:
            continue
        for j, y in enumerate(b):
            if y:
                out[i + j] ^= _EXP[_LOG[x] + _LOG[y]]
    return out


def _rs_encode(data, n_ec):
    gen = _rs_generator(n_ec)
    rem = list(data) + [0] * n_ec
    for i in range(len(data)):
        c = rem[i]
        if c:
            for j in range(1, len(gen)):
                rem[i + j] ^= _EXP[_LOG[gen[j]] + _LOG[c]]
    return rem[len(data):]


def _bch(value, poly, bits):
    """Append BCH remainder: value shifted left by `bits`, divided by poly."""
    v = value << bits
    top = poly.bit_length()
    for i in range(v.bit_length() - top, -1, -1):
        if v & (1 << (i + top - 1)):
            v ^= poly << i
    return (value << bits) | v


def _alignment_positions(version):
    if version == 1:
        return []
    n = version // 7 + 2
    size = version * 4 + 17
    step = 26 if version == 32 else -(-(size - 13) // (2 * n - 2)) * 2
    positions = [6]
    pos = size - 7
    for _ in range(n - 1):
        positions.insert(1, pos)
        pos -= step
    return positions


def qr_matrix(text):
    data = text.encode('utf-8')
    # pick the smallest version whose data capacity fits (byte mode, level M)
    for version in range(1, 41):
        ec, g1, d1, g2, d2 = _EC_M[version]
        capacity = g1 * d1 + g2 * d2
        cci = 8 if version < 10 else 16
        if 4 + cci + 8 * len(data) <= capacity * 8:
            break
    else:
        raise ValueError('text too long for a QR code')

    # --- data codewords
    bits = []

    def put(val, n):
        for i in range(n - 1, -1, -1):
            bits.append((val >> i) & 1)
    put(0b0100, 4)
    put(len(data), cci)
    for b in data:
        put(b, 8)
    put(0, min(4, capacity * 8 - len(bits)))
    while len(bits) % 8:
        bits.append(0)
    codewords = [int(''.join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    pad = (0xEC, 0x11)
    i = 0
    while len(codewords) < capacity:
        codewords.append(pad[i & 1])
        i += 1

    # --- blocks + error correction, then interleave
    blocks, pos = [], 0
    for count, length in ((g1, d1), (g2, d2)):
        for _ in range(count):
            blocks.append(codewords[pos:pos + length])
            pos += length
    ecs = [_rs_encode(b, ec) for b in blocks]
    seq = []
    for k in range(max(len(b) for b in blocks)):
        for b in blocks:
            if k < len(b):
                seq.append(b[k])
    for k in range(ec):
        for e in ecs:
            seq.append(e[k])

    # --- the matrix: None = free, True/False = fixed pattern
    size = version * 4 + 17
    m = [[None] * size for _ in range(size)]

    def finder(r, c):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                rr, cc = r + dr, c + dc
                if 0 <= rr < size and 0 <= cc < size:
                    edge = dr in (-1, 7) or dc in (-1, 7)
                    ring = dr in (0, 6) or dc in (0, 6)
                    core = 2 <= dr <= 4 and 2 <= dc <= 4
                    m[rr][cc] = (not edge) and (ring or core)
    finder(0, 0)
    finder(0, size - 7)
    finder(size - 7, 0)
    for i in range(8, size - 8):                   # timing
        m[6][i] = m[i][6] = (i % 2 == 0)
    aps = _alignment_positions(version)
    for r in aps:
        for c in aps:
            if (r <= 8 and c <= 8) or (r <= 8 and c >= size - 9) or (r >= size - 9 and c <= 8):
                continue                            # would overlap a finder
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    m[r + dr][c + dc] = max(abs(dr), abs(dc)) != 1
    m[size - 8][8] = True                           # dark module
    # reserve format areas (filled after masking)
    for i in range(9):
        if m[8][i] is None: m[8][i] = False
        if m[i][8] is None: m[i][8] = False
    for i in range(size - 8, size):
        m[8][i] = False
    for i in range(size - 7, size):
        m[i][8] = False
    if version >= 7:                                # version info
        vinfo = _bch(version, 0x1F25, 12)
        for i in range(18):
            bit = bool((vinfo >> i) & 1)
            m[i // 3][size - 11 + i % 3] = bit
            m[size - 11 + i % 3][i // 3] = bit

    # --- place data in the zig-zag
    fixed = [[cell is not None for cell in row] for row in m]
    bitstream = []
    for cw in seq:
        for i in range(7, -1, -1):
            bitstream.append((cw >> i) & 1)
    bi = 0
    col = size - 1
    upward = True
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for r in rows:
            for c in (col, col - 1):
                if not fixed[r][c]:
                    m[r][c] = bool(bitstream[bi]) if bi < len(bitstream) else False
                    bi += 1
        col -= 2
        upward = not upward

    # --- masks, scored
    masks = [
        lambda r, c: (r + c) % 2 == 0,
        lambda r, c: r % 2 == 0,
        lambda r, c: c % 3 == 0,
        lambda r, c: (r + c) % 3 == 0,
        lambda r, c: (r // 2 + c // 3) % 2 == 0,
        lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
        lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
        lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
    ]

    def apply(mask_id):
        f = masks[mask_id]
        out = [[(m[r][c] ^ f(r, c)) if not fixed[r][c] else m[r][c] for c in range(size)] for r in range(size)]
        fmt = _bch((0b00 << 3) | mask_id, 0x537, 10) ^ 0x5412   # level M = 00
        for i in range(15):
            bit = bool((fmt >> i) & 1)
            # vertical strip beside top-left finder / horizontal beside bottom-left
            if i < 6:
                out[i][8] = bit
            elif i < 8:
                out[i + 1][8] = bit
            else:
                out[size - 15 + i][8] = bit
            if i < 8:
                out[8][size - 1 - i] = bit
            elif i < 9:
                out[8][7] = bit
            else:
                out[8][14 - i] = bit
        return out

    def penalty(g):
        n = 0
        for lines in (g, list(zip(*g))):
            for line in lines:
                run, prev = 0, None
                for v in line:
                    if v == prev:
                        run += 1
                    else:
                        if run >= 5:
                            n += 3 + run - 5
                        run, prev = 1, v
                if run >= 5:
                    n += 3 + run - 5
                # finder-like 1:1:3:1:1 patterns with 4 light modules either side
                s = ''.join('1' if v else '0' for v in line)
                n += 40 * (s.count('10111010000') + s.count('00001011101'))
        for r in range(size - 1):
            for c in range(size - 1):
                if g[r][c] == g[r][c + 1] == g[r + 1][c] == g[r + 1][c + 1]:
                    n += 3
        dark = sum(v for row in g for v in row)
        k = abs(dark * 100 // (size * size) - 50) // 5
        n += 10 * k
        return n

    best = min(range(8), key=lambda i: penalty(apply(i)))
    return apply(best)


def qr_svg(url):
    """An inline SVG of the URL's QR code: quiet zone included, crisp at any size."""
    matrix = qr_matrix(url)
    n = len(matrix)
    quiet = 3                                          # modules of white around the code
    size = n + 2 * quiet
    runs = []
    for y, row in enumerate(matrix):
        x = 0
        while x < n:
            if row[x]:
                start = x
                while x < n and row[x]:
                    x += 1
                runs.append('M%d %dh%dv1h-%dz' % (start + quiet, y + quiet, x - start, x - start))
            else:
                x += 1
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" shape-rendering="crispEdges" '
            'role="img" aria-label="QR code for %s"><rect width="%d" height="%d" fill="#fff"/>'
            '<path d="%s" fill="#111"/></svg>' % (size, size, html.escape(url, quote=True), size, size, ''.join(runs)))


# One line, added just before </body> of the served copy. It is its own little
# card (not part of the kit panel) so it works for every app ever made with the
# kit, whatever version of the template it was created from. Entering VR hides
# every HTML overlay, so it never appears inside the headset. pointer-events
# stays off: the card must not steal clicks from the scene.
QR_CARD = (
    '<style>#kit-qr{position:fixed;top:12px;right:12px;z-index:9998;display:flex;align-items:center;gap:10px;'
    'font:12px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#40505f;'
    'background:rgba(255,255,255,.92);border:1px solid rgba(64,80,95,.18);border-radius:10px;padding:8px 10px 8px 8px;'
    'pointer-events:none;backdrop-filter:blur(4px);max-width:360px}'
    '#kit-qr svg{width:148px;height:148px;flex:none;border-radius:4px}'
    '#kit-qr b{display:block;font-weight:600;font-size:13px;color:#1d2733}'
    '#kit-qr span{display:block;color:#6c7d8e}'
    '#kit-qr code{display:block;margin-top:4px;font:11px/1.35 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;'
    'color:#2f6f8f;word-break:break-all}'
    '@media (max-width:700px),(max-height:520px){#kit-qr{padding:6px;gap:0}'
    '#kit-qr svg{width:96px;height:96px}#kit-qr .t{display:none}}</style>'
    '<div id="kit-qr">%(svg)s<div class="t"><b>Open on a headset</b><span>Scan with the ClassVR scanner</span>'
    '<code>%(short)s</code></div></div>'
    '<script>window.KIT_PAGES_URL=%(json)s;</script>'
)


def inject_qr(index_path, url, svg):
    """Add the QR card to a served index.html, as one line, at the very end of the body."""
    with open(index_path, encoding='utf-8') as f:
        page = f.read()
    short = re.sub(r'^https?://', '', url)
    card = QR_CARD % {'svg': svg, 'short': html.escape(short), 'json': json.dumps(url)}
    m = list(re.finditer(r'</body\s*>', page, flags=re.IGNORECASE))
    if m:
        at = m[-1].start()
        page = page[:at] + card + '\n' + page[at:]
    else:
        page = page + '\n' + card + '\n'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(page)


# --- the index page ----------------------------------------------------------

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>XR prototypes</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #f7f7f4; --card: #ffffff; --ink: #1d2733; --soft: #5b6b7b;
    --line: #e2e5e2; --accent: #2f6f4f;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #171a1d; --card: #21262b; --ink: #e8ecef; --soft: #9fadb9;
            --line: #333a41; --accent: #7fc79e; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 48px 20px 64px; background: var(--bg); color: var(--ink);
         font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 1.7rem; margin: 0 0 6px; letter-spacing: -0.01em; }
  .lede { color: var(--soft); margin: 0 0 32px; }
  ul { list-style: none; margin: 0; padding: 0; }
  li { background: var(--card); border: 1px solid var(--line); border-radius: 12px;
       padding: 18px 20px; margin-bottom: 14px; display: flex; gap: 18px; align-items: flex-start; }
  li .text { flex: 1 1 auto; min-width: 0; }
  li .qr { flex: none; width: 104px; text-align: center; color: var(--soft); font-size: 0.72rem; line-height: 1.3; }
  li .qr svg { display: block; width: 104px; height: 104px; border-radius: 6px; margin-bottom: 4px; }
  a.name { color: var(--accent); font-weight: 650; font-size: 1.12rem;
           text-decoration: none; }
  a.name:hover { text-decoration: underline; }
  .concept { color: var(--soft); margin: 6px 0 10px; }
  .meta { color: var(--soft); font-size: 0.85rem; }
  .meta span + span::before { content: " · "; }
  .empty { color: var(--soft); }
  footer { color: var(--soft); font-size: 0.85rem; margin-top: 36px;
           border-top: 1px solid var(--line); padding-top: 16px; }
  @media (max-width: 480px) { li { flex-direction: column; } li .qr { width: auto; text-align: left; } }
</style>
</head>
<body>
<main>
  <h1>XR prototypes</h1>
  <p class="lede">WebXR prototypes built with the ClassVR Prototyping Kit. Open one on a
  desktop to look around, or scan its QR code with a ClassVR headset to press
  <strong>Enter VR</strong>.</p>
  __LIST__
  <footer>Published from <code>main</code> by GitHub Actions. The build number on each
  app's panel tells you which version you are looking at; a change can take a few
  minutes to reach this page.</footer>
</main>
</body>
</html>
"""


def render_index(apps):
    if not apps:
        return PAGE.replace('__LIST__', '<p class="empty">No apps here yet.</p>')
    items = []
    for app in apps:
        meta = []
        if app['dof']:
            meta.append('%sDoF headsets' % app['dof'])
        if app['build']:
            meta.append('build %s' % app['build'])
        qr = ('      <div class="qr">%s Scan on a headset</div>\n' % app['svg']) if app.get('svg') else ''
        items.append(
            '<li>\n'
            '      <div class="text">\n'
            '      <a class="name" href="%s/">%s</a>\n'
            '      %s'
            '      <div class="meta">%s</div>\n'
            '      </div>\n'
            '%s'
            '    </li>' % (
                html.escape(app['slug']),
                html.escape(app['name']),
                '<p class="concept">%s</p>\n      ' % html.escape(app['concept']) if app['concept'] else '',
                ''.join('<span>%s</span>' % html.escape(str(m)) for m in meta),
                qr,
            ))
    return PAGE.replace('__LIST__', '<ul>\n    %s\n  </ul>' % '\n    '.join(items))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.', help='repo root to scan (default: here)')
    ap.add_argument('--out', default='_site', help='directory to assemble into')
    ap.add_argument('--base-url', help='where the site will be served from (default: worked out from GitHub)')
    ap.add_argument('--no-qr', action='store_true', help='skip the QR codes')
    a = ap.parse_args()

    out = os.path.abspath(a.out)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)

    base = site_base_url(a.root, a.base_url)
    want_qr = not a.no_qr
    if want_qr and not base:
        print('  ! no site address known (not in GitHub Actions, no CNAME, no --base-url) — no QR codes this time',
              file=sys.stderr)
        want_qr = False

    apps, seen = [], {}
    for app_dir in find_apps(a.root):
        manifest = read_manifest(app_dir)
        name = manifest.get('name') or os.path.basename(app_dir)
        slug = manifest.get('slug') or slugify(name)
        if slug in seen:
            print('  ! %s and %s both want /%s/ — skipping the second'
                  % (seen[slug], app_dir, slug), file=sys.stderr)
            continue
        if not os.path.exists(os.path.join(app_dir, 'index.html')):
            print('  ! %s has no index.html — skipping' % app_dir, file=sys.stderr)
            continue
        seen[slug] = app_dir
        dest = os.path.join(out, slug)
        files = copy_app(app_dir, dest)
        svg = None
        url = (base + slug + '/') if base else None
        if want_qr and url:
            svg = qr_svg(url)
            inject_qr(os.path.join(dest, 'index.html'), url, svg)
        apps.append({'name': name, 'slug': slug, 'concept': manifest.get('concept') or '',
                     'dof': manifest.get('dof'), 'build': manifest.get('build'), 'svg': svg})
        print('  %-28s -> /%s/  (%d files%s)' % (name, slug, files, ', QR of ' + url if svg else ''))

    apps.sort(key=lambda x: x['name'].lower())
    with open(os.path.join(out, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(render_index(apps))
    # Pages runs Jekyll by default, which would drop anything starting with _
    open(os.path.join(out, '.nojekyll'), 'w').close()

    print('%d app(s) assembled into %s%s' % (len(apps), a.out, (' for ' + base) if base else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
