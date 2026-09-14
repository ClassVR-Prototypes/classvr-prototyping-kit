#!/usr/bin/env python3
"""Flatten a project into one self-contained HTML file, bumping the build number
when — and only when — the source actually changed.

    python3 build.py --project /path/to/ProjectFolder

Reads  <project>/index.html and <project>/xr-project.json
Writes <project>/dist/<slug>-build<N>.html   (everything inlined)
Updates window.BUILD in index.html and build/sourceHash in the manifest.

Why one file: ClassCloud storage is content-addressed — every URL is a hash,
there are no directories and no relative paths, so a <script src="./x.js">
can never resolve there. Every local script is inlined here.

Prints JSON: {ok, build, bumped, output, bytes}
"""
import argparse, hashlib, json, os, re, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    a = ap.parse_args()
    proj = os.path.abspath(a.project)
    idx = os.path.join(proj, 'index.html')
    man_path = os.path.join(proj, 'xr-project.json')
    if not os.path.exists(idx) or not os.path.exists(man_path):
        print(json.dumps({'ok': False, 'error': 'index.html or xr-project.json missing in ' + proj}))
        return 2

    src = open(idx, encoding='utf-8').read()
    man = json.load(open(man_path, encoding='utf-8'))

    # --- build number: bump iff content (excluding the build line) changed ---
    m = re.search(r'window\.BUILD\s*=\s*(\d+)\s*;', src)
    if not m:
        print(json.dumps({'ok': False, 'error': 'index.html has no "window.BUILD = N;" line'}))
        return 2
    # The manifest is the authority; index.html's line only wins if it is ahead
    # (a regenerated or hand-restored index.html must never reset the counter).
    cur = max(int(m.group(1)), int(man.get('build') or 0))
    masked = re.sub(r'window\.BUILD\s*=\s*\d+\s*;', 'window.BUILD = _;', src)
    # include any local scripts in the hash, so a library change also bumps
    for s in sorted(re.findall(r'<script\s+src="\./([^"]+)"', src)):
        p = os.path.join(proj, s)
        if os.path.exists(p):
            masked += '\n<!--' + s + ':' + hashlib.sha256(open(p, 'rb').read()).hexdigest() + '-->'
    h = hashlib.sha256(masked.encode('utf-8')).hexdigest()

    bumped = False
    if man.get('sourceHash') is not None and man['sourceHash'] != h:
        cur += 1
        bumped = True
        src = re.sub(r'window\.BUILD\s*=\s*\d+\s*;', f'window.BUILD = {cur};', src, count=1)
        open(idx, 'w', encoding='utf-8').write(src)
    man['build'] = cur
    man['sourceHash'] = h
    json.dump(man, open(man_path, 'w', encoding='utf-8'), indent=2)
    open(man_path, 'a').write('\n')

    # --- inline every local script ---
    def inline(mo):
        name = mo.group(1)
        p = os.path.join(proj, name)
        if not os.path.exists(p):
            raise SystemExit(json.dumps({'ok': False, 'error': f'referenced script not found: {name}'}))
        js = open(p, encoding='utf-8').read()
        if '</script' in js:
            js = js.replace('</script', '<\\/script')
        return '<script><!--KIT-LIB-START-->\n' + js + '\n</script><!--KIT-LIB-END-->'   # markers removed below
    flat = re.sub(r'<script\s+src="\./([^"]+)"\s*>\s*</script>', inline, src)
    # Line anchor. The diary reports error lines in whatever page is running,
    # and wrappers (the artifact viewer's skeleton, artifact.py's stripping)
    # shift those numbers. The kit measures its own line at runtime with a probe
    # and subtracts the difference from this stamp, so every code's line is a
    # line of THIS file, wherever the page ran. Stamp the probe's line here.
    lines = flat.split('\n')
    for i, line in enumerate(lines):
        if '/*BUILD_PROBE*/' in line:
            lines[i] = line.replace('/*BUILD_PROBE*/0', '/*BUILD_PROBE*/' + str(i + 1))
            break
    # Library line ranges: the lines occupied by each inlined <script> body
    # (markers left by inline()), so an error inside a library is coded "-lib".
    ranges, start = [], None
    for i, line in enumerate(lines):
        if '<!--KIT-LIB-START-->' in line: start = i + 2          # body begins on the next line
        if '<!--KIT-LIB-END-->' in line and start is not None: ranges.append([start, i]); start = None
    flat = '\n'.join(lines).replace('<!--KIT-LIB-START-->', '').replace('<!--KIT-LIB-END-->', '')
    flat = flat.replace('/*BUILD_LIB_LINES*/[]', '/*BUILD_LIB_LINES*/' + json.dumps(ranges), 1)

    slug = man.get('slug') or 'xr-app'
    out_dir = os.path.join(proj, 'dist')
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f'{slug}-build{cur}.html')
    open(out, 'w', encoding='utf-8').write(flat)
    # keep dist/ to the current build only — old flattened files are 1.3 MB each
    # and the hosted copy is the record of what was published
    for old in os.listdir(out_dir):
        if old.startswith(slug + '-build') and old.endswith('.html') and old != os.path.basename(out):
            try: os.remove(os.path.join(out_dir, old))
            except OSError: pass

    print(json.dumps({'ok': True, 'build': cur, 'bumped': bumped, 'output': out,
                      'bytes': os.path.getsize(out)}, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())
