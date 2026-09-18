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
  * page/ — a slim index.html for THIS app that loads those files and
            A-Frame from URLs. Only this file changes per publish.

Nothing in the app's source changes. The plumbing blocks are found by the
same markers the template already carries (the diary's `window.KIT =`, the
xr-kit banner, `#kit-panel`, "Status panel"), so the hosted library is
always generated from the template — never hand-edited.

Usage:
  vercel_build.py <app folder> [--lib-base https://…] [--kit-version auto|label]
                  [--aframe auto|X.Y.Z] [--out <dir>]

Library versions are content-addressed (12-hex hash of the extracted plumbing)
and each lives in its own Vercel project, xr-kit-lib-<version>, so a new
template version is hosted once and an old one is never overwritten (a Vercel
deploy always replaces the whole file set of a project).
"""
import argparse, hashlib, json, os, re, sys

def find_block(html, tag, must_contain, start_at=0):
    for m in re.finditer(r'<%s\b[^>]*>(.*?)</%s>' % (tag, tag), html, re.S):
        if m.start() >= start_at and must_contain in m.group(0):
            return m
    raise SystemExit('could not find the %s block containing %r' % (tag, must_contain))

def stamp(text, marker, value):
    # the stamped value is either a number or a (possibly nested) array literal
    return re.sub(r'/\*%s\*/(\[\[.*?\]\]|\[\]|\d+)' % re.escape(marker), '/*%s*/%s' % (marker, value), text, count=1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('app')
    ap.add_argument('--lib-base', default=None,
                    help="where lib/ is served from, no trailing slash. Default: one Vercel project PER library version, "
                         "https://xr-kit-lib-<version>.vercel.app — so hosting a new template version never touches an old one")
    ap.add_argument('--kit-version', default='auto',
                    help="library version label; 'auto' = 12-hex hash of the extracted plumbing, so any app maps to exactly the files built from its own template")
    ap.add_argument('--aframe', default='auto', help="A-Frame release to load from aframe.io; 'auto' reads it from the app's bundled aframe.min.js")
    ap.add_argument('--out', default=None)
    a = ap.parse_args()

    src = open(os.path.join(a.app, 'index.html'), encoding='utf-8').read()
    manifest = json.load(open(os.path.join(a.app, 'xr-project.json'), encoding='utf-8'))
    build = manifest.get('build', 0)
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
    v = a.kit_version
    if v == 'auto':
        v = hashlib.sha256((diary_js + style.group(1) + xrkit.group(1) + panel.group(1)).encode('utf-8')).hexdigest()[:12]
    # the panel names the app as a literal in the template; shared, it must
    # read the page title instead (the one line the template should adopt)
    panel_js = re.sub(r"'<b>[^<']*</b>", "'<b>' + document.title + '</b>", panel.group(1), count=1)
    panel_js = panel_js.replace('(bundled)', '(shared library)')
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
    page = page[:diary.start()] + '<script src="%s/xr-kit-diary-%s.js"></script>' % (L, v) + page[diary.end():]
    # any other bundled library (cannon.iife.js, ...) must be hosted beside the
    # kit files; point at it there and list it so the publish step can check
    extra_libs = []
    def relib(m):
        extra_libs.append(m.group(1)); return '<script src="%s/%s"></script>' % (L, m.group(1))
    page = re.sub(r'<script src="\./([^"]+\.js)"></script>', relib, page)
    page = re.sub(r'<!-- Libraries are bundled beside this file, never loaded from a CDN\. -->',
                  '<!-- Vercel build: kit %s from %s, A-Frame %s from aframe.io -->' % (v, L, a.aframe), page)
    page = re.sub(r'window\.BUILD = \d+;', 'window.BUILD = %d;' % build, page)
    open(os.path.join(out, 'page', 'index.html'), 'w', encoding='utf-8', newline='\n').write(page)

    # 4. report + a manifest a publish step can verify the hosted copies against
    def kb(s): return '%.1f KB' % (len(s.encode('utf-8')) / 1024)
    manifest_out = {'kit': v, 'aframe': a.aframe, 'libBase': L, 'build': build, 'extraLibs': extra_libs, 'files': {}}
    print('source page    ', kb(src))
    for name, text in lib.items():
        h = hashlib.sha256(text.encode('utf-8')).hexdigest()
        manifest_out['files']['lib/' + name] = {'bytes': len(text.encode('utf-8')), 'sha256': h}
        print('lib/%-26s %s  sha256 %s' % (name, kb(text), h[:12]))
    h = hashlib.sha256(page.encode('utf-8')).hexdigest()
    manifest_out['files']['page/index.html'] = {'bytes': len(page.encode('utf-8')), 'sha256': h}
    print('page/index.html', kb(page), '(build %s, kit lib %s, A-Frame %s)' % (build, v, a.aframe))
    if extra_libs: print('extra libraries to host at', L + ':', ', '.join(extra_libs))
    json.dump(manifest_out, open(os.path.join(out, 'manifest.json'), 'w', encoding='utf-8'), indent=2)

if __name__ == '__main__':
    main()
