#!/usr/bin/env python3
"""Turn a flattened build into the form a Claude Artifact page expects.

    python3 artifact.py --build /path/to/dist/<slug>-build<N>.html

The Artifact tool wraps whatever it publishes in its own <!doctype html>
<html><head>…</head><body>…</body></html> skeleton (charset, viewport, a small
CSS reset). So the file handed to it must carry none of those tags itself:
just <title> first, then the head content (styles, scripts) and the body
content, in that order.

Reads  dist/<slug>-build<N>.html  (output of build.py — everything already inlined)
Writes dist/<slug>-artifact.html  (same folder, stable name so the Artifact tool
                                   redeploys to the same URL inside a session)

Prints JSON: {ok, output, bytes, title}
"""
import argparse, json, os, re, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', required=True, help='flattened HTML from build.py')
    ap.add_argument('--out', help='output path (default: dist/<slug>-artifact.html beside the build)')
    a = ap.parse_args()
    src_path = os.path.abspath(a.build)
    if not os.path.exists(src_path):
        print(json.dumps({'ok': False, 'error': 'build file not found: ' + src_path})); return 2
    html = open(src_path, encoding='utf-8').read()

    if re.search(r'<script\s+src="\./', html):
        print(json.dumps({'ok': False, 'error': 'file still references local scripts — run build.py first'})); return 2

    # Line-preserving conversion. The diary reports error lines and corrects them
    # back to build-file coordinates by measuring a uniform wrapper offset, so
    # this file must keep every line of the build in place: tags the skeleton
    # supplies are blanked out, never deleted with their lines. Only the title
    # and a comment are added, at the top, above everything.
    tm = re.search(r'<title>(.*?)</title>', html, re.S | re.I)
    title = tm.group(1).strip() if tm else 'XR app'
    body_html = html
    for pat in [r'<!DOCTYPE[^>]*>', r'</?html\b[^>]*>', r'</?head\b[^>]*>', r'</?body\b[^>]*>',
                r'<meta\b[^>]*>', r'<title>.*?</title>']:
        body_html = re.sub(pat, '', body_html, flags=re.I)          # no newlines in these patterns: lines stay
    out = ('<title>%s</title>\n' % title
           + '<!-- Published from the ClassVR Prototyping Kit. Reload this page to get the latest build. -->\n'
           + body_html)

    if a.out:
        out_path = os.path.abspath(a.out)
    else:
        d = os.path.dirname(src_path)
        base = os.path.basename(src_path)
        slug = re.sub(r'-build\d+\.html$', '', base) if re.search(r'-build\d+\.html$', base) else 'xr-app'
        out_path = os.path.join(d, slug + '-artifact.html')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, 'w', encoding='utf-8').write(out)
    size = os.path.getsize(out_path)
    LIMIT, SOFT = 16 * 1024 * 1024, 12 * 1024 * 1024   # the Artifact page cap, and a warning line
    if size > LIMIT:
        os.remove(out_path)
        print(json.dumps({'ok': False, 'bytes': size,
                          'error': 'page is %.1f MB; artifacts stop at 16 MB. Something embedded (a texture, model or audio as data) is too big — shrink or remove it.' % (size / 1048576)}))
        return 1
    res = {'ok': True, 'output': out_path, 'bytes': size, 'title': title}
    if size > SOFT:
        res['warning'] = 'page is %.1f MB of a 16 MB limit — embedded assets are getting large' % (size / 1048576)
    print(json.dumps(res, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())
