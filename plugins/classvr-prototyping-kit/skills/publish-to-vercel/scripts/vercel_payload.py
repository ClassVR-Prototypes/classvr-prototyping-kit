#!/usr/bin/env python3
"""Turn a vercel_build.py output folder into the one bridge call that deploys it.

Token route (kit 0.31+): instead of a connector tool call, the deploy runs in
the built-in browser as `await KV.deploy({...})` (see connect-vercel). This
script writes that call for you, so nothing is assembled by hand:

    vercel_payload.py <dist-vercel> --name <project> [--first] --out deploy.js
    vercel_payload.py <dist-vercel> --lib --out lib-deploy.js

Every inline file carries its SHA-1 in `expect`; KV.deploy refuses to send
anything whose text doesn't match, so a slip in copying the call can never
reach the live site. Files Vercel already holds (`reusable` in deployFiles, or
`--all-by-sha` for a redeploy where everything was uploaded before) go by
fingerprint only.

Paste the file's whole text into javascript_tool on the bridge tab. It prints
nothing secret; the result is the deploy summary.
"""
import argparse, hashlib, json, os, sys


def sha1(b):
    return hashlib.sha1(b).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dist')
    ap.add_argument('--name', help='Vercel project name (app deploys)')
    ap.add_argument('--first', action='store_true', help='first publish: send projectSettings framework none')
    ap.add_argument('--lib', action='store_true', help='deploy the shared library (lib/) instead of the app')
    ap.add_argument('--all-by-sha', action='store_true', help='send every file by fingerprint (redeploy of identical files)')
    ap.add_argument('--inline', action='append', default=[], help='send this file inline even if reusable (Vercel said missing_files)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    m = json.load(open(os.path.join(a.dist, 'manifest.json'), encoding='utf-8'))
    files, expect, inline_bytes = [], {}, 0

    if a.lib:
        name = 'xr-kit-lib-' + m['kit']
        for f in m['libDeploy']:
            b = open(os.path.join(a.dist, 'lib', f), 'rb').read()
            t = b.decode('utf-8')
            files.append({'file': f, 'data': t})
            expect[f] = sha1(b)
            inline_bytes += len(b)
        settings = {'framework': None}
    else:
        if not a.name:
            sys.exit('--name is required for an app deploy')
        name = a.name
        df = m['deployFiles']
        for f in m['deploy']:
            d = df[f]
            path = os.path.join(a.dist, 'page', f)
            forced = f in a.inline and os.path.exists(path)
            if not forced and (d.get('reusable') or d.get('byFingerprint') or a.all_by_sha or not os.path.exists(path)):
                files.append({'file': f, 'sha': d['sha1'], 'size': d['size']})
                continue
            b = open(path, 'rb').read()
            if sha1(b) != d['sha1']:
                sys.exit('page/%s does not match its manifest fingerprint — rebuild' % f)
            files.append({'file': f, 'data': b.decode('utf-8')})
            expect[f] = d['sha1']
            inline_bytes += len(b)
        settings = {'framework': None} if a.first else None

    spec = {'name': name, 'target': 'production', 'files': files, 'expect': expect}
    if settings:
        spec['projectSettings'] = settings
    js = ("if (!window.KV) throw new Error('Load the Vercel bridge first (connect-vercel)');\n"
          "await KV.deploy(" + json.dumps(spec, ensure_ascii=False, indent=None) + ");\n")
    open(a.out, 'w', encoding='utf-8').write(js)
    print(json.dumps({'ok': True, 'out': a.out, 'name': name, 'files': len(files),
                      'inline': sorted(expect), 'inlineBytes': inline_bytes,
                      'byFingerprint': [f['file'] for f in files if 'sha' in f]}, indent=1))


if __name__ == '__main__':
    main()
