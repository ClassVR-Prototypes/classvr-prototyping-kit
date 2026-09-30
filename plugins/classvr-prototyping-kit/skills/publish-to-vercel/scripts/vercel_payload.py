#!/usr/bin/env python3
"""Write the one script that runs a publish step in the built-in browser.

The kit talks to Vercel only from the built-in browser, with the person's own
token (see connect-vercel). This script writes the whole browser side of a
step as one piece of JavaScript, so nothing is assembled by hand:

    vercel_payload.py <dist> --prepare --out prepare.js [--suffix 2]
        first publish: load the bridge, name and create the project, learn
        its real address, give it a play-history store  (dist from
        vercel_build.py --library-only)
    vercel_payload.py <dist> --name <project> [--first] --out deploy.js
        load the bridge, deploy, and check the live page — one call
    vercel_payload.py <dist> --lib [--by-sha] [--inline f ...] --out lib-deploy.js
        host the shared library (one-time per kit release)

Every script carries the part of the Vercel bridge it needs, written out in
it (from connect-vercel/assets/vercel-bridge.js, comments and setup-only parts
left out) — never fetched and run from elsewhere, so what runs in the tab
that holds the token is all there to read. Checking the page is live happens
afterwards on the app's own page (publish_prep.py's live check). Scripts check first that the
shared library for this kit version is hosted ("library-missing" if not).

Every inline file carries its SHA-1 in `expect`; KV.deploy refuses to send
anything whose text doesn't match, so a slip in copying the script can never
reach the live site. Files Vercel may already hold go by fingerprint, with a
public copy named in `sources` that the bridge uploads if Vercel asks for it.
Every script throws on failure, so a browser batch stops right there, and its
last line is the result. It prints nothing secret.
"""
import argparse, hashlib, json, os, re, sys


def sha1(b):
    return hashlib.sha1(b).hexdigest()


def js(v):
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'))


BRIDGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'connect-vercel', 'assets', 'vercel-bridge.js')


def mini_bridge(part):
    """vercel-bridge.js cut to what one script needs: the core plus the
    @part:<part> block ('first' or 'deploy'); no setup-only blocks (the token
    box, check, forget, deployments), comments, indentation or status line."""
    src = open(BRIDGE, encoding='utf-8').read()
    src = re.sub(r'/\* @setup-only \*/.*?/\* @end-setup-only \*/\n?', '', src, flags=re.S)
    src = re.sub(r'/\* @part:(?!%s \*/)\w+ \*/.*?/\* @end-part \*/\n?' % part, '', src, flags=re.S)
    src = re.sub(r'^/\*.*?\*/\n', '', src, count=1, flags=re.S)          # the header comment
    out = []
    for line in src.split('\n'):
        t = line.strip()
        if not t or t.startswith('//') or t.startswith('/* @'):
            continue
        if t.startswith("'KV ready"):
            continue
        out.append(t)
    return '\n'.join(out) + '\n'


def loader(m, part):
    lib = m['libBase'] + '/xr-kit-' + m['kit'] + '.js'
    return (
        "if (location.origin !== 'https://api.vercel.com') throw new Error('open https://api.vercel.com/v2/user in this tab first');\n"
        + mini_bridge(part)
        + "if (!KV.status().connected) throw new Error('not-connected: run /connect-vercel');\n"
        + "const libOk = await fetch(" + js(lib) + ", {method: 'HEAD', cache: 'no-store'}).then(r => r.ok, () => false);\n"
        + "if (!libOk) throw new Error('library-missing: the shared library for this kit version is not hosted yet');\n")


def fail(what):
    return "throw new Error(" + js(what) + " + ' ' + JSON.stringify(%s));\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dist')
    ap.add_argument('--name', help='Vercel project name (app deploys)')
    ap.add_argument('--first', action='store_true', help='first publish: send projectSettings framework none')
    ap.add_argument('--prepare', action='store_true', help='first publish, before the build: name + create the project, store')
    ap.add_argument('--suffix', default=None, help='with --prepare: add -2, -3 ... when the plain address was taken')
    ap.add_argument('--lib', action='store_true', help='deploy the shared library (lib/) instead of the app')
    ap.add_argument('--by-sha', action='store_true', help='with --lib: send files by fingerprint unless named with --inline')
    ap.add_argument('--all-by-sha', action='store_true', help='send every app file by fingerprint (redeploy of identical files)')
    ap.add_argument('--inline', action='append', default=[], help='send this file inline even if reusable')
    ap.add_argument('--no-verify', action='store_true', help='deploy only, skip the live check')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    m = json.load(open(os.path.join(a.dist, 'manifest.json'), encoding='utf-8'))
    head = '// ClassVR Prototyping Kit — %s (kit %s)\n'

    def wrap(t):
        # one async function, so running a second script in the same tab never
        # clashes with names the first one declared; its value is the result
        first, rest = t.split('\n', 1)
        return first + '\nawait (async () => {\n' + rest + '})();\n'

    if a.prepare:
        opts = {'suffix': a.suffix} if a.suffix else {}
        text = (head % ('first publish of ' + m.get('slug', 'app'), m['kit']) + loader(m, 'first')
                + "const p = await KV.firstPublish(" + js(m.get('slug')) + ", " + js(opts) + ");\n"
                + "if (!p.ok) " + fail('prepare failed:') % 'p'
                + "return p;\n")
        open(a.out, 'w', encoding='utf-8').write(wrap(text))
        print(json.dumps({'ok': True, 'out': a.out, 'step': 'prepare', 'slug': m.get('slug'), 'kit': m['kit']}, indent=1))
        return

    files, expect, inline_bytes = [], {}, 0
    if a.lib:
        name = 'xr-kit-lib-' + m['kit']
        for f in m['libDeploy']:
            b = open(os.path.join(a.dist, 'lib', f), 'rb').read()
            if a.by_sha and f not in a.inline:
                files.append({'file': f, 'sha': sha1(b), 'size': len(b)})
                continue
            files.append({'file': f, 'data': b.decode('utf-8')})
            expect[f] = sha1(b)
            inline_bytes += len(b)
        spec = {'name': name, 'target': 'production', 'files': files, 'expect': expect, 'projectSettings': {'framework': None}}
        # vercel.json is settings, never served, so it is not read back
        want = {f: m['files']['lib/' + f]['sha256'] for f in m['libDeploy'] if f != 'vercel.json'}
        base = 'https://%s.vercel.app' % name
        text = (head % ('library ' + name, m['kit'])
                + "if (location.origin !== 'https://api.vercel.com') throw new Error('open https://api.vercel.com/v2/user in this tab first');\n"
                + mini_bridge('deploy')
                + "if (!KV.status().connected) throw new Error('not-connected: run /connect-vercel');\n"
                + "const r = await KV.deploy(" + js(spec) + ");\n"
                + "if (!r.ok) " + fail('library deploy failed:') % 'r'
                + "const want = " + js(want) + ", bad = [];\n"
                + "for (const f of Object.keys(want)) {\n"
                + "  const g = await fetch(" + js(base + '/') + " + (f === 'index.html' ? '' : f), {cache: 'no-store'});\n"
                + "  const h = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', await g.arrayBuffer()))).map(b => b.toString(16).padStart(2, '0')).join('');\n"
                + "  if (!g.ok || h !== want[f]) bad.push(f + ' ' + g.status);\n"
                + "}\n"
                + "return {deployed: r.readyState, alias: r.alias, uploaded: r.uploaded, mismatched: bad};\n")
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
        spec = {'name': name, 'target': 'production', 'files': files, 'expect': expect}
        if m.get('sources'):
            spec['sources'] = m['sources']
        if a.first:
            spec['projectSettings'] = {'framework': None}
        url = (m.get('url') or '').rstrip('/')
        host = url.replace('https://', '')
        text = (head % ('publish %s version %s' % (name, m['build']), m['kit']) + loader(m, 'deploy')
                + "const r = await KV.deploy(" + js(spec) + ");\n"
                + "if (!r.ok) " + fail('publish failed:') % 'r'
                + ("if (!(r.alias || []).includes(" + js(host) + ")) " + fail('address missing:') % 'r.alias' if host else '')
                # the address can lag READY by a moment: wait until it serves this version
                + ("let live = false;\n"
                   "for (let i = 0; i < 10 && !live; i++) {\n"
                   "  live = await fetch(" + js(url + '/') + ", {cache: 'no-store'}).then(x => x.text()).then(t => t.includes(" + js('window.BUILD = %d;' % m['build']) + "), () => false);\n"
                   "  if (!live) await new Promise(z => setTimeout(z, 1500));\n"
                   "}\n" if url and not a.no_verify else "const live = true;\n")
                + "const res = {id: r.id, projectId: r.projectId, readyState: r.readyState, uploaded: r.uploaded, teamId: KV.status().teamId, live: live};\n"
                + "if (!live) " + fail('live check failed: the address is not serving this version yet') % 'res'
                + "return res;\n")

    text = wrap(text)
    open(a.out, 'w', encoding='utf-8').write(text)
    print(json.dumps({'ok': True, 'out': a.out, 'name': name, 'files': len(files),
                      'inline': sorted(expect), 'inlineBytes': inline_bytes, 'scriptBytes': len(text.encode('utf-8')),
                      'byFingerprint': [f['file'] for f in files if 'sha' in f]}, indent=1))


if __name__ == '__main__':
    main()
