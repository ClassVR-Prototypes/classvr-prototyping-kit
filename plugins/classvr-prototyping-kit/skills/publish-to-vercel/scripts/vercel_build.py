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

Version history (kit 0.25). Every publish is also a *version*: the build
records the page's SHA-1 fingerprint, size, date and a one-line note under
`vercel.versions` in xr-project.json, and writes into the deploy set

  history.json          the list, machine-readable, public
  history/index.html    the same list as a page: /history
  v/<N>/index.html      every version, playable forever at /v/<N>/

Only the newest page travels in the publish (twice: as index.html and as
v/<N>/index.html). Every older v/<M>/index.html is listed in the manifest by
fingerprint alone — Vercel already holds those bytes from the publish that
first sent them — so a history of fifty versions costs the same to publish
as one. "Go back to version 4" is an ordinary publish whose source is the
page fetched from /v/4/ (unslimmed back into index.html) with
`--restored-from 4`; nothing is ever deleted. `--note` is the plain-English
"what changed" line; without it the note is "Version N" (or the note already
recorded for that build).

Every published page is also kept in the app's own folder, ten to a
sub-folder, with a plain-words note beside it:

  versions/Versions 1 - 10/03-index.html     exactly what went live as version 3
  versions/Versions 1 - 10/03-README.txt     what changed, when, fingerprint

so "go back to version 3" on the person's own app needs no download at all
(`--local-version 3` finds the file and checks its fingerprint), and the
history travels with the folder. `--no-local-versions` turns it off.

Usage:
  vercel_build.py <app folder> [--lib-base https://…] [--kit-version auto|label]
                  [--aframe auto|X.Y.Z] [--out <dir>] [--no-relay] [--indexable]
                  [--note "what changed"] [--restored-from N] [--no-history]
                  [--no-local-versions]
  vercel_build.py <app folder> --local-version N

  vercel_build.py --unslim <published index.html> --lib-dir <dir> --out <file>
                  [--expect-sha1 <40 hex>]

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
import argparse, datetime, hashlib, html as htmlmod, json, os, re, shutil, sys

SOURCE_META = 'xr-kit-source'
BUNDLED_COMMENT = '<!-- Libraries are bundled beside this file, never loaded from a CDN. -->'
HISTORY_JSON = 'history.json'
HISTORY_PAGE = 'history/index.html'


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def version_path(n):
    return 'v/%d/index.html' % n


def record_version(manifest, build_no, sha1, size, note, restored_from):
    """Add or refresh the entry for this build in manifest['vercel']['versions'].

    Re-running the build for the same build number (a failed publish, an
    unchanged source) replaces that entry rather than adding a second one, so
    the list always has one entry per build, in build order."""
    vc = manifest.setdefault('vercel', {})
    versions = [v for v in (vc.get('versions') or []) if isinstance(v, dict) and 'version' in v]
    existing = next((v for v in versions if v['version'] == build_no), None)
    entry = {
        'version': build_no,
        'date': now_iso(),
        'note': note or (existing or {}).get('note') or ('First version' if build_no <= 1 else 'Version %d' % build_no),
        'sha1': sha1,
        'size': size,
    }
    rf = restored_from if restored_from is not None else (existing or {}).get('restoredFrom')
    if rf is not None:
        entry['restoredFrom'] = rf
    if existing:
        versions[versions.index(existing)] = entry
    else:
        versions.append(entry)
    versions.sort(key=lambda v: v['version'])
    vc['versions'] = versions
    return versions


VERSIONS_DIR = 'versions'
GROUP = 10


def versions_group(n):
    """'Versions 1 - 10', 'Versions 11 - 20', … — ten to a folder, so a long
    history stays browsable in a file explorer."""
    lo = ((n - 1) // GROUP) * GROUP + 1
    return 'Versions %d - %d' % (lo, lo + GROUP - 1)


def local_version_paths(app_dir, n):
    folder = os.path.join(app_dir, VERSIONS_DIR, versions_group(n))
    return folder, os.path.join(folder, '%02d-index.html' % n), os.path.join(folder, '%02d-README.txt' % n)


def version_readme(manifest, entry, url):
    """The tiny note that sits beside each saved version, in plain words."""
    app = manifest.get('name') or manifest.get('slug') or 'this app'
    lines = [
        '%s — version %d' % (app, entry['version']),
        '',
        'What changed: %s' % entry.get('note', ''),
        'Saved: %s (UTC)' % entry.get('date', '').replace('T', ' ').rstrip('Z'),
        'Fingerprint: %s  (full: %s)' % (entry['sha1'][:8], entry['sha1']),
    ]
    if entry.get('restoredFrom') is not None:
        lines.append('This version put version %d back.' % entry['restoredFrom'])
    if url:
        lines.append('Live at: %s/v/%d/' % (url.rstrip('/'), entry['version']))
    lines += [
        '',
        'The file beside this note, %02d-index.html, is exactly what was published as' % entry['version'],
        'version %d. It is kept so you can go back to it later — just ask Claude:' % entry['version'],
        '"go back to version %d". Please don\'t edit it; edit the app\'s own index.html' % entry['version'],
        'in the folder above and publish again, and a new version will be saved here.',
        '',
        'The fingerprint is a short code worked out from the file itself. If two people',
        'quote the same fingerprint they are looking at exactly the same version.',
    ]
    return '\n'.join(lines) + '\n'


def save_local_version(app_dir, manifest, entry, page, url):
    folder, page_path, readme_path = local_version_paths(app_dir, entry['version'])
    os.makedirs(folder, exist_ok=True)
    open(page_path, 'w', encoding='utf-8', newline='\n').write(page)
    open(readme_path, 'w', encoding='utf-8', newline='\n').write(version_readme(manifest, entry, url))
    return page_path, readme_path


def history_document(manifest, versions):
    """The public history.json. Deliberately carries no names or e-mail
    addresses: version, date, note, fingerprint, size, and where a copy came
    from (address and version only)."""
    vc = manifest.get('vercel') or {}
    doc = {
        'kit': 'classvr-prototyping-kit',
        'format': 1,
        'app': manifest.get('name'),
        'slug': manifest.get('slug'),
        'url': vc.get('url'),
        'current': versions[-1]['version'] if versions else None,
        'versions': [dict(v, path='v/%d/' % v['version']) for v in versions],
    }
    ff = manifest.get('forkedFrom') or manifest.get('copiedFrom')
    if isinstance(ff, dict) and ff.get('url'):
        cf = {'url': ff['url']}
        for k in ('version', 'build', 'sha1'):
            if ff.get(k) is not None:
                cf['version' if k == 'build' else k] = ff[k]
        doc['copiedFrom'] = cf
    return doc


def history_page(doc):
    """A small static page listing the versions, generated fresh on every
    publish. It embeds the same data history.json carries, so it needs no
    fetch and works from a file as well as from the live address."""
    e = htmlmod.escape
    app = doc.get('app') or doc.get('slug') or 'this app'
    rows = []
    for v in reversed(doc['versions']):
        tags = []
        if v['version'] == doc.get('current'):
            tags.append('<span class="tag now">current</span>')
        if v.get('restoredFrom') is not None:
            tags.append('<span class="tag">restored from version %d</span>' % v['restoredFrom'])
        rows.append(
            '<li><a class="ver" href="/v/%d/">Version %d</a> %s<div class="note">%s</div>'
            '<div class="meta"><time datetime="%s">%s</time> · fingerprint <code title="%s">%s</code> · %s</div></li>'
            % (v['version'], v['version'], ''.join(tags), e(v.get('note') or ''), e(v.get('date', '')),
               e(v.get('date', '')[:10]), e(v.get('sha1', '')), e(v.get('sha1', '')[:8]),
               '<a href="/v/%d/">play</a>' % v['version']))
    url = doc.get('url') or ''
    copy_hint = (e(url.rstrip('/')) + ' version N') if url else 'this address, version N'
    return '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>%(app)s — history</title>
<style>
:root { --bg:#f7f7f5; --fg:#1e1e1e; --muted:#6b6b6b; --card:#fff; --line:#e3e3e0; --accent:#2b6cb0; --now:#2f855a; }
@media (prefers-color-scheme: dark) { :root { --bg:#141414; --fg:#ececec; --muted:#a0a0a0; --card:#1e1e1e; --line:#2c2c2c; --accent:#7fb3ff; --now:#7bd39a; } }
body { margin:0; padding:24px 16px 48px; background:var(--bg); color:var(--fg); font:16px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
main { max-width:680px; margin:0 auto; }
h1 { font-size:1.4rem; margin:0 0 4px; } h1 small { font-weight:normal; color:var(--muted); }
p.lead { color:var(--muted); margin:0 0 20px; }
ol { list-style:none; padding:0; margin:0; }
li { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; margin:0 0 10px; }
a { color:var(--accent); } a.ver { font-weight:600; text-decoration:none; font-size:1.05rem; }
.note { margin:4px 0 6px; } .meta { color:var(--muted); font-size:.9rem; }
code { font:.9em ui-monospace,Menlo,Consolas,monospace; background:var(--bg); padding:1px 5px; border-radius:4px; }
.tag { display:inline-block; font-size:.75rem; padding:1px 8px; border-radius:999px; border:1px solid var(--line); color:var(--muted); margin-left:6px; vertical-align:middle; }
.tag.now { color:var(--now); border-color:var(--now); }
aside { margin-top:28px; padding:14px 16px; border-left:3px solid var(--accent); color:var(--muted); font-size:.95rem; }
aside b { color:var(--fg); }
</style>
</head>
<body>
<main>
<h1>%(app)s <small>— every version</small></h1>
<p class="lead">Each version stays playable at its own address. <a href="/">Open the current version</a>.</p>
<ol>
%(rows)s
</ol>
<aside>
<b>Want your own copy?</b> Ask Claude: “make me my own copy of %(copy)s”. You get an independent copy to change however you like; this one is untouched.<br>
<b>Fingerprint</b> is the first eight characters of the page's SHA-1 — two people quoting the same fingerprint are looking at exactly the same version. The full list is at <a href="/history.json">history.json</a>.
</aside>
</main>
</body>
</html>
''' % {'app': e(app), 'rows': '\n'.join(rows), 'copy': copy_hint}


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
    by_fingerprint = {}                 # path -> (sha1, size): older versions, never re-sent
    versions = []
    if not a.no_history:
        # 4a. version history: this page becomes v/<build>/, older builds are
        #     listed by fingerprint, and the list is written as JSON + a page
        page_sha1, page_size = sha1_bytes(page)
        versions = record_version(manifest, build_no, page_sha1, page_size, a.note, a.restored_from)
        json.dump(manifest, open(os.path.join(a.app, 'xr-project.json'), 'w', encoding='utf-8'), indent=2)
        open(os.path.join(a.app, 'xr-project.json'), 'a').write('\n')
        doc = history_document(manifest, versions)
        deploy[version_path(build_no)] = page
        for old in versions:
            if old['version'] != build_no:
                by_fingerprint[version_path(old['version'])] = (old['sha1'], old['size'])
        deploy[HISTORY_JSON] = json.dumps(doc, indent=2) + '\n'
        deploy[HISTORY_PAGE] = history_page(doc)
        # 4b. the same page kept in the app's own folder — versions/Versions 1 - 10/
        #     03-index.html + 03-README.txt — so "go back" never needs a download
        #     for the person's own app, and the history travels with the folder
        if not a.no_local_versions:
            cur = next(v2 for v2 in versions if v2['version'] == build_no)
            saved_page, saved_readme = save_local_version(a.app, manifest, cur, page, (manifest.get('vercel') or {}).get('url'))
            print('kept locally     %s' % os.path.relpath(saved_page, a.app))
        for name in (version_path(build_no), HISTORY_JSON, HISTORY_PAGE):
            dest = os.path.join(out, 'page', name)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, 'w', encoding='utf-8', newline='\n').write(deploy[name])
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
    # the complete file set the deploy tool must receive: everything written
    # under page/ plus every older version, which travels by fingerprint only
    out_man['deploy'] = sorted(list(deploy) + list(by_fingerprint))
    out_man['deployFiles'] = {}
    # the page itself and its v/<N>/ twin change every build and are sent
    # inline (a fingerprint can only be referenced once Vercel has the bytes,
    # so a file new in this publish cannot be sent by sha — verified 22 Sep);
    # history.json and the history page change too; everything else is
    # byte-identical across publishes and goes by sha after the first time
    inline_names = {'index.html', HISTORY_JSON, HISTORY_PAGE, version_path(build_no)}
    for name in sorted(deploy):
        text = deploy[name]
        s1, n = sha1_bytes(text)
        out_man['files']['page/' + name] = {'bytes': n, 'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(), 'sha1': s1}
        out_man['deployFiles'][name] = {'sha1': s1, 'size': n, 'reusable': name not in inline_names}
        print('page/%-26s %s' % (name, kb(text)) + ('  (build %s, kit lib %s, A-Frame %s)' % (build_no, v, a.aframe) if name == 'index.html' else ''))
    for name, (s1, n) in sorted(by_fingerprint.items()):
        out_man['deployFiles'][name] = {'sha1': s1, 'size': n, 'reusable': True, 'byFingerprint': True}
        print('page/%-26s %s  (by fingerprint %s — not re-sent)' % (name, '%.1f KB' % (n / 1024), s1[:8]))
    if versions:
        cur = versions[-1]
        out_man['history'] = {'current': cur['version'], 'note': cur['note'], 'sha1': cur['sha1'],
                              'fingerprint': cur['sha1'][:8], 'count': len(versions),
                              'restoredFrom': cur.get('restoredFrom')}
        print('version %d — "%s" — fingerprint %s (%d version%s in the history)'
              % (cur['version'], cur['note'], cur['sha1'][:8], len(versions), '' if len(versions) == 1 else 's'))
    if extra_libs: print('extra libraries to host at', L + ':', ', '.join(extra_libs))
    json.dump(out_man, open(os.path.join(out, 'manifest.json'), 'w', encoding='utf-8'), indent=2)


# ---------------------------------------------------------------- local version

def local_version(a):
    manifest = json.load(open(os.path.join(a.app, 'xr-project.json'), encoding='utf-8'))
    versions = (manifest.get('vercel') or {}).get('versions') or []
    entry = next((v for v in versions if v.get('version') == a.local_version), None)
    folder, page_path, readme_path = local_version_paths(a.app, a.local_version)
    out = {'version': a.local_version, 'path': page_path, 'readme': readme_path,
           'recorded': bool(entry), 'exists': os.path.exists(page_path)}
    if entry:
        out['sha1'] = entry['sha1']; out['note'] = entry.get('note'); out['date'] = entry.get('date')
    if out['exists']:
        s1, n = sha1_bytes(open(page_path, encoding='utf-8', newline='').read())
        out['fileSha1'] = s1; out['bytes'] = n
        out['ok'] = bool(entry) and s1 == entry['sha1']
        if not out['ok']:
            out['reason'] = ('no entry for version %d in xr-project.json' % a.local_version) if not entry else \
                            'the kept file does not match the fingerprint recorded at publish time — fetch /v/%d/ from the live address instead' % a.local_version
    else:
        out['ok'] = False
        out['reason'] = 'version %d is not kept in this folder — fetch /v/%d/ from the live address instead' % (a.local_version, a.local_version)
    print(json.dumps(out, indent=2))
    return 0 if out['ok'] else 1


# ---------------------------------------------------------------- unslim

def unslim(a):
    page = open(a.unslim, encoding='utf-8').read()
    fetched_sha1, fetched_size = sha1_bytes(page)
    if a.expect_sha1 and fetched_sha1.lower() != a.expect_sha1.lower():
        raise SystemExit('fingerprint mismatch: the fetched page is %s but the history says %s — '
                         'fetch it again before copying' % (fetched_sha1[:8], a.expect_sha1[:8]))
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
                      'publishedSha1': fetched_sha1, 'fingerprint': fetched_sha1[:8], 'publishedBytes': fetched_size,
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
    ap.add_argument('--expect-sha1', default=None, metavar='HEX',
                    help='with --unslim: the fingerprint history.json gives for this version; stop if the fetched page does not match it')
    ap.add_argument('--note', default=None, help='one plain-English line saying what changed in this version (goes in the public history)')
    ap.add_argument('--restored-from', type=int, default=None, metavar='N',
                    help='this publish puts version N back (its page was fetched from /v/N/ and unslimmed into index.html first)')
    ap.add_argument('--no-history', action='store_true', help='leave out history.json, the history page and v/<N>/ (not the default)')
    ap.add_argument('--no-local-versions', action='store_true',
                    help="do not keep a copy of the published page under <app>/versions/ (not the default)")
    ap.add_argument('--local-version', type=int, default=None, metavar='N',
                    help="print the path of version N kept under <app>/versions/ (and check its fingerprint against xr-project.json), then exit")
    a = ap.parse_args()
    if a.unslim:
        if not a.lib_dir or not a.out:
            raise SystemExit('--unslim needs --lib-dir (the library files) and --out (where to write index.html)')
        return unslim(a)
    if not a.app:
        raise SystemExit('give an app folder, or --unslim a published page')
    if a.local_version is not None:
        return local_version(a)
    return build(a)


if __name__ == '__main__':
    main()
