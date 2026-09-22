#!/usr/bin/env python3
"""
vercel_build.py — the Vercel route's build (skills/publish-to-vercel).

Second build output for a kit app, alongside build.py's single file:

  * lib/  — the kit's plumbing extracted from the app's index.html into
            versioned files, hosted ONCE for every app:
              xr-kit-diary-<ver>.js   window.KIT (runs before A-Frame)
              xr-kit-<ver>.css        panel + reticle styles
              xr-kit-<ver>.js         xr-kit / checker-ground components
              xr-kit-panel-<ver>.js   status panel (runs after the scene)
  * page/ — the deploy set for THIS app: a slim index.html that loads those
            files and A-Frame from URLs, kit-relay.js (posts the app's diary
            to /api/log), api/log.js (receives it, prints it to the runtime
            log and keeps one copy per session in Blob storage),
            api/reports.js (reads that history back), package.json and
            vercel.json. Only index.html changes from publish to publish —
            the others are byte-identical every time, so a publish can send
            them by SHA instead of re-uploading them (see `deployFiles` in
            manifest.json).

Nothing in the app's source changes. The plumbing blocks are found by the
same markers the template already carries (the diary's `window.KIT =`, the
xr-kit banner, `#kit-panel`, "Status panel"), so the hosted library is
always generated from the template — never hand-edited.

Usage:
  vercel_build.py <app folder> [--lib-base https://…] [--kit-version auto|label]
                  [--aframe auto|X.Y.Z] [--out <dir>] [--no-relay] [--indexable]

  vercel_build.py --unslim <published index.html> --lib-dir <dir> --out <file>
                  [--aframe-file aframe.min.js]

Library versions are content-addressed (12-hex hash of the extracted plumbing)
and each lives in its own Vercel project, xr-kit-lib-<version>, so a new
template version is hosted once and an old one is never overwritten (a Vercel
deploy always replaces the whole file set of a project).

--unslim is the inverse: given a page this script produced and the library
files it names, it puts the plumbing back inline and returns the app's source
index.html — so anyone with a published address can take a copy and keep
building on it (/copy-xr-app). The result differs from the original in one
harmless way: the status panel reads the app's name from the page title
instead of carrying it as a literal.
"""
import argparse, hashlib, json, os, re, shutil, sys

SOURCE_META = 'xr-kit-source'
BUNDLED_COMMENT = '<!-- Libraries are bundled beside this file, never loaded from a CDN. -->'


def find_block(html, tag, must_contain, start_at=0):
    for m in re.finditer(r'<%s\b[^>]*>(.*?)</%s>' % (tag, tag), html, re.S):
        if m.start() >= start_at and must_contain in m.group(0):
            return m
    raise SystemExit('could not find the %s block containing %r' % (tag, must_contain))


def stamp(text, marker, value):
    # the stamped value is either a number or a (possibly nested) array literal
    return re.sub(r'/\*%s\*/(\[\[.*?\]\]|\[\]|\d+)' % re.escape(marker), '/*%s*/%s' % (marker, value), text, count=1)


def sha1_bytes(text):
    b = text.encode('utf-8')
    return hashlib.sha1(b).hexdigest(), len(b)


# ---------------------------------------------------------------- build

def build(a):
    ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets')

    src = open(os.path.join(a.app, 'index.html'), encoding='utf-8').read()
    manifest = json.load(open(os.path.join(a.app, 'xr-project.json'), encoding='utf-8'))
    build_no = manifest.get('build', 0)
    slug = manifest.get('slug') or os.path.basename(os.path.abspath(a.app)).lower().replace(' ', '-')
    out = a.out or os.path.join(a.app, 'dist-vercel')
    os.makedirs(os.path.join(out, 'lib'), exist_ok=True)
    os.makedirs(os.path.join(out, 'page'), exist_ok=True)
    # A-Frame version: read from the bundled copy so the CDN copy matches exactly
    if a.aframe == 'auto':
        af = os.path.join(a.app, 'aframe.min.js')
        m = re.search(r'A-Frame Version: (\d+\.\d+\.\d+)', open(af, encoding='utf-8', errors='ignore').read()) if os.path.exists(af) else None
        if not m:
            raise SystemExit('could not read the A-Frame version from aframe.min.js; pass --aframe X.Y.Z')
        a.aframe = m.group(1)

    # 1. the four plumbing blocks, in document order
    diary = find_block(src, 'script', 'window.KIT = (function')
    style = find_block(src, 'style', '#kit-panel', diary.end())
    xrkit = find_block(src, 'script', "AFRAME.registerComponent('xr-kit'", style.end())
    panel = find_block(src, 'script', 'Status panel', xrkit.end())
    aframe_tag = re.search(r'<script src="\./aframe\.min\.js"></script>', src)
    if not aframe_tag:
        raise SystemExit('expected <script src="./aframe.min.js"> in the source')

    # 2. library files (the diary's build-time stamps: external file, so no
    #    page-line offset and no inlined-library line range)
    diary_js = stamp(stamp(diary.group(1), 'BUILD_PROBE', '0'), 'BUILD_LIB_LINES', '[]')
    # the panel names the app as a literal in the template; shared, it must
    # read the page title instead (the one line the template should adopt)
    panel_js = re.sub(r"'<b>[^<']*</b>", "'<b>' + document.title + '</b>", panel.group(1), count=1)
    panel_js = panel_js.replace('(bundled)', '(shared library)')
    # version = hash of the plumbing AFTER normalising, so every app made from
    # the same template gets the same library whatever it is called
    v = a.kit_version
    if v == 'auto':
        v = hashlib.sha256((diary_js + style.group(1) + xrkit.group(1) + panel_js).encode('utf-8')).hexdigest()[:12]
    lib = {
        'xr-kit-diary-%s.js' % v: diary_js.strip('\n') + '\n',
        'xr-kit-%s.css' % v: style.group(1).strip('\n') + '\n',
        'xr-kit-%s.js' % v: xrkit.group(1).strip('\n') + '\n',
        'xr-kit-panel-%s.js' % v: panel_js.strip('\n') + '\n',
    }
    for name, text in lib.items():
        open(os.path.join(out, 'lib', name), 'w', encoding='utf-8', newline='\n').write(text)

    # 3. the slim page: replace each block with a reference, in reverse order
    #    so earlier offsets stay valid
    L = (a.lib_base or 'https://xr-kit-lib-%s.vercel.app' % v).rstrip('/')
    page = src
    page = page[:panel.start()] + '<script src="%s/xr-kit-panel-%s.js"></script>' % (L, v) + page[panel.end():]
    page = page[:xrkit.start()] + '<script src="%s/xr-kit-%s.js"></script>' % (L, v) + page[xrkit.end():]
    page = page[:style.start()] + '<link rel="stylesheet" href="%s/xr-kit-%s.css">' % (L, v) + page[style.end():]
    page = page[:aframe_tag.start()] + '<script src="https://aframe.io/releases/%s/aframe.min.js"></script>' % a.aframe + page[aframe_tag.end():]
    relay_tag = '' if a.no_relay else '\n<script src="./kit-relay.js"></script>'
    page = page[:diary.start()] + '<script src="%s/xr-kit-diary-%s.js"></script>' % (L, v) + relay_tag + page[diary.end():]
    # any other bundled library (cannon.iife.js, ...) must be hosted beside the
    # kit files; point at it there and list it so the publish step can check
    extra_libs = []
    def relib(m):
        extra_libs.append(m.group(1)); return '<script src="%s/%s"></script>' % (L, m.group(1))
    page = re.sub(r'<script src="\./(?!kit-relay\.js)([^"]+\.js)"></script>', relib, page)
    page = re.sub(re.escape(BUNDLED_COMMENT),
                  '<!-- Vercel build: kit %s from %s, A-Frame %s from aframe.io -->' % (v, L, a.aframe), page)
    page = re.sub(r'window\.BUILD = \d+;', 'window.BUILD = %d;' % build_no, page)
    # one line saying where this page came from, so /copy-xr-app can rebuild
    # the source from the page alone
    source_meta = ('<meta name="%s" content="kit=%s; build=%d; slug=%s; aframe=%s; lib=%s">'
                   % (SOURCE_META, v, build_no, slug, a.aframe, L))
    page = re.sub(r'(<meta charset="[^"]*">)', r'\1\n' + source_meta.replace('\\', '\\\\'), page, count=1)
    open(os.path.join(out, 'page', 'index.html'), 'w', encoding='utf-8', newline='\n').write(page)

    # 4. the rest of the deploy set. Everything except index.html is the same
    #    bytes on every publish of every app, which is what lets a publish
    #    send them by SHA rather than re-uploading them.
    deploy = {'index.html': page}
    fixed = []
    if not a.no_relay:
        fixed += [('kit-relay.js', 'kit-relay.js'), ('api/log.js', 'api-log.js'),
                  ('api/reports.js', 'api-reports.js'), ('package.json', 'package.json')]
    if not a.indexable:
        fixed.append(('vercel.json', 'vercel-app.json'))
    for name, asset in fixed:
        text = open(os.path.join(ASSETS, asset), encoding='utf-8').read()
        dest = os.path.join(out, 'page', name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, 'w', encoding='utf-8', newline='\n').write(text)
        deploy[name] = text

    # 5. report + a manifest a publish step can verify the hosted copies against
    def kb(s): return '%.1f KB' % (len(s.encode('utf-8')) / 1024)
    out_man = {'kit': v, 'aframe': a.aframe, 'libBase': L, 'build': build_no, 'slug': slug,
               'extraLibs': extra_libs, 'noindex': not a.indexable, 'files': {}}
    print('source page    ', kb(src))
    for name, text in lib.items():
        h = hashlib.sha256(text.encode('utf-8')).hexdigest()
        s1, n = sha1_bytes(text)
        out_man['files']['lib/' + name] = {'bytes': n, 'sha256': h, 'sha1': s1}
        print('lib/%-26s %s  sha256 %s' % (name, kb(text), h[:12]))
    out_man['deploy'] = sorted(deploy)          # the complete file set the deploy tool must receive
    out_man['deployFiles'] = {}
    for name in sorted(deploy):
        text = deploy[name]
        s1, n = sha1_bytes(text)
        out_man['files']['page/' + name] = {'bytes': n, 'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(), 'sha1': s1}
        # inline the page itself (it changes every build); the rest never
        # change, so a publish after the first can reference them by sha
        out_man['deployFiles'][name] = {'sha1': s1, 'size': n, 'reusable': name != 'index.html'}
        print('page/%-26s %s' % (name, kb(text)) + ('  (build %s, kit lib %s, A-Frame %s)' % (build_no, v, a.aframe) if name == 'index.html' else ''))
    if extra_libs: print('extra libraries to host at', L + ':', ', '.join(extra_libs))
    json.dump(out_man, open(os.path.join(out, 'manifest.json'), 'w', encoding='utf-8'), indent=2)


# ---------------------------------------------------------------- unslim

def unslim(a):
    page = open(a.unslim, encoding='utf-8').read()
    m = re.search(r'<meta name="%s" content="([^"]*)">\s*' % SOURCE_META, page)
    info = {}
    if m:
        for part in m.group(1).split(';'):
            k, _, val = part.partition('=')
            info[k.strip()] = val.strip()
        page = page[:m.start()] + page[m.end():]
    ver = info.get('kit') or (re.search(r'xr-kit-diary-([0-9a-f]{6,});?', page) or [None, None])[1]
    if not ver:
        m2 = re.search(r'xr-kit-diary-([0-9a-f]{6,})\.js', page)
        ver = m2.group(1) if m2 else None
    if not ver:
        raise SystemExit('this page does not name a kit library version — is it a kit page?')

    def libfile(name):
        p = os.path.join(a.lib_dir, name)
        if not os.path.exists(p):
            raise SystemExit('missing library file %s in %s' % (name, a.lib_dir))
        return open(p, encoding='utf-8').read().rstrip('\n')

    diary_js = libfile('xr-kit-diary-%s.js' % ver)
    css = libfile('xr-kit-%s.css' % ver)
    xrkit_js = libfile('xr-kit-%s.js' % ver)
    panel_js = libfile('xr-kit-panel-%s.js' % ver).replace('(shared library)', '(bundled)')

    def one(pattern, replacement, what):
        nonlocal page
        new, n = re.subn(pattern, lambda _m: replacement, page, count=1)
        if not n:
            raise SystemExit('could not find the %s reference in this page' % what)
        page = new

    # the relay tag goes; it belongs to the published copy, not the source
    page = re.sub(r'\n?<script src="\./kit-relay\.js"></script>', '', page, count=1)
    one(r'<script src="[^"]*/xr-kit-panel-%s\.js"></script>' % ver, '<script>\n' + panel_js + '\n</script>', 'status panel')
    one(r'<script src="[^"]*/xr-kit-%s\.js"></script>' % ver, '<script>\n' + xrkit_js + '\n</script>', 'xr-kit component')
    one(r'<link rel="stylesheet" href="[^"]*/xr-kit-%s\.css">' % ver, '<style>\n' + css + '\n</style>', 'stylesheet')
    one(r'<script src="https://aframe\.io/releases/[^"]+/aframe\.min\.js"></script>',
        '<script src="./aframe.min.js"></script>', 'A-Frame')
    one(r'<script src="[^"]*/xr-kit-diary-%s\.js"></script>' % ver, '<script>\n' + diary_js + '\n</script>', 'diary')
    # extra libraries come back beside the file
    page = re.sub(r'<script src="https?://[^"]*/([A-Za-z0-9._-]+\.js)"></script>',
                  lambda m2: '<script src="./%s"></script>' % m2.group(1), page)
    page = re.sub(r'<!-- Vercel build:[^>]*-->', BUNDLED_COMMENT, page, count=1)

    open(a.out, 'w', encoding='utf-8', newline='\n').write(page)
    title = re.search(r'<title>([^<]*)</title>', page)
    print(json.dumps({'ok': True, 'out': a.out, 'kit': ver, 'name': (title.group(1).strip() if title else None),
                      'build': int(info.get('build', 0) or 0), 'slug': info.get('slug'),
                      'aframe': info.get('aframe'), 'libBase': info.get('lib'),
                      'bytes': len(page.encode('utf-8'))}, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('app', nargs='?')
    ap.add_argument('--lib-base', default=None,
                    help="where lib/ is served from, no trailing slash. Default: one Vercel project PER library version, "
                         "https://xr-kit-lib-<version>.vercel.app — so hosting a new template version never touches an old one")
    ap.add_argument('--kit-version', default='auto',
                    help="library version label; 'auto' = 12-hex hash of the extracted plumbing, so any app maps to exactly the files built from its own template")
    ap.add_argument('--aframe', default='auto', help="A-Frame release to load from aframe.io; 'auto' reads it from the app's bundled aframe.min.js")
    ap.add_argument('--out', default=None)
    ap.add_argument('--no-relay', action='store_true', help='leave out kit-relay.js and the api/ functions (static page only)')
    ap.add_argument('--indexable', action='store_true', help='do not add the vercel.json that keeps the page out of search engines')
    ap.add_argument('--unslim', metavar='PAGE', default=None,
                    help='inverse: rebuild an app\'s source index.html from a page this script published')
    ap.add_argument('--lib-dir', default=None, help='with --unslim: folder holding the xr-kit-*.js/.css files the page names')
    a = ap.parse_args()
    if a.unslim:
        if not a.lib_dir or not a.out:
            raise SystemExit('--unslim needs --lib-dir (the library files) and --out (where to write index.html)')
        return unslim(a)
    if not a.app:
        raise SystemExit('give an app folder, or --unslim a published page')
    return build(a)


if __name__ == '__main__':
    main()
