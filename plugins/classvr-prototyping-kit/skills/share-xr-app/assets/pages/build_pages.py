#!/usr/bin/env python3
# kit-pages-builder v2 — the share-xr-app skill compares this line with its own copy.
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

Prints a one-line summary per app. Exit 0 even with no apps — an empty
repo should still publish its index rather than fail the deploy.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
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


# --- QR codes ----------------------------------------------------------------

def _qrcode_module():
    """The `qrcode` package, installing it on the fly if the runner lacks it."""
    try:
        return __import__('qrcode')
    except ImportError:
        pass
    for extra in ([], ['--user'], ['--break-system-packages']):
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', 'qrcode'] + extra,
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
            return __import__('qrcode')
        except Exception:
            continue
    return None


def qr_svg(url, qrcode):
    """An inline SVG of the URL's QR code: quiet zone included, crisp at any size."""
    from qrcode.constants import ERROR_CORRECT_M
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, border=0)
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
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
    qrcode = None
    if a.no_qr:
        pass
    elif not base:
        print('  ! no site address known (not in GitHub Actions, no CNAME, no --base-url) — no QR codes this time',
              file=sys.stderr)
    else:
        qrcode = _qrcode_module()
        if qrcode is None:
            print('  ! the qrcode package is not available and could not be installed — publishing without QR codes',
                  file=sys.stderr)

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
        if qrcode and url:
            svg = qr_svg(url, qrcode)
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
