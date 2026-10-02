#!/usr/bin/env python3
"""Every workspace step of a publish, in as few calls as possible (kit 0.39).

    publish_prep.py prepare --from <staged app folder> --scratch <dir>
        first publish only: check the app runs, bump the version, and write the
        browser script that names and creates the project (prepare.js)
    publish_prep.py build   --from <staged app folder> --scratch <dir>
                            [--prepared '<prepare.js result>'] [--note "..."]
                            [--restored-from M] [--inline FILE ...] [--no-preview]
        check the app runs (skipped when prepare just did), bump the version,
        build the slim page, library and history, and write the one browser
        script that deploys and checks the live page (deploy.js)
    publish_prep.py take    --from <staged app folder> --scratch <dir>
        only copy the app into <scratch>/app (to change it there first, e.g.
        going back to a version), then run build without --from
    publish_prep.py record  --scratch <dir> --result '<deploy.js result>'
                            [--outputs /mnt/user-data/outputs/<app>]
        record the deploy in xr-project.json and copy every file that changed
        into --outputs, ready for one device_commit_files call

The app is copied from --from (the staged, read-only copy) into
<scratch>/app on the first call and worked on there. Each call prints a short
JSON summary; prepare and build then print the browser script(s) between
marker lines, so they can be pasted without reading another file.
Exit codes: 0 ok, 1 stop (the app failed its check, or something must be
fixed first — the summary says what), 2 bad input.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PREVIEW = os.path.join(HERE, '..', '..', 'preview-xr-app', 'scripts', 'preview.py')
SKIP = {'dist', '.preview', 'dist-vercel'}

KITCHECK = """await (async () => {
  // runs on the app's own page after the deploy: no token, no bridge
  const C = __CHECK__;
  for (let i = 0; i < 40 && !(window.KIT && window.KIT.checkResults); i++) await new Promise(r => setTimeout(r, 500));
  if (!window.KIT) throw new Error('live check failed: the page did not start the kit');
  // the self-checks have run (they walk the player forward and play the game):
  // take ?kitcheck off the address so a reload of this tab doesn't run them again
  try { history.replaceState(history.state, '', location.pathname + location.hash); } catch (e) {}
  const rep = KIT.report(), c = KIT.checkResults || [], problems = [];
  const get = p => fetch(p, {cache: 'no-store'}).then(async r => ({status: r.status, text: await r.text()}), () => ({status: 0, text: ''}));
  const res = {build: window.BUILD, scene: !!(document.querySelector('a-scene') || {}).hasLoaded,
               enterVR: !!document.querySelector('.a-enter-vr-button'), errors: (rep.errorList || []).length,
               firstError: (rep.errorList || [])[0] || null, qr: !!document.getElementById('kit-qr'),
               // the walk-forward check uses synthetic keys, which the pane does not deliver
               failed: c.filter(x => x && x.ok === false && x.name !== 'the player can walk forward').map(x => x.name + (x.detail ? ' - ' + x.detail : ''))};
  // A hidden browser panel draws no frames, so the in-scene self-checks cannot
  // pass while it is hidden (seen 2 Oct 2026, even the kit's own). If any
  // failed: run them once more now if the page is visible (they may have run
  // while it was hidden); if it is still hidden, skip them — they already
  // passed in the build's test run.
  const notWalk = x => x && x.ok === false && x.name !== 'the player can walk forward';
  if (res.failed.length) {
    if (document.hidden) { res.selfChecks = 'skipped: the browser panel is hidden, so the page draws no frames'; res.failed = []; }
    else if (KIT.runChecks) { const again = await KIT.runChecks(); res.selfChecks = 'ran again with the panel showing';
      res.failed = (again || []).filter(notWalk).map(x => x.name + (x.detail ? ' - ' + x.detail : '')); }
  }
  if (res.build !== C.build) problems.push('the page is not version ' + C.build);
  if (!res.scene) problems.push('the scene did not load');
  if (!res.enterVR) problems.push('no Enter VR button');
  if (res.errors) problems.push(res.errors + ' error(s), first: ' + JSON.stringify(res.firstError));
  if (res.failed.length) problems.push('self-checks failed: ' + res.failed.join('; '));
  if (!document.querySelector('meta[name="xr-kit-source"]')) problems.push('source line missing');
  const srcs = Array.from(document.querySelectorAll('script[src], link[rel=stylesheet]')).map(e => e.src || e.href);
  C.lib.forEach(f => { if (!srcs.includes(C.libBase + '/' + f)) problems.push('page does not load ' + f); });
  if (C.qr) {
    const q = document.querySelector('meta[name="xr-kit-qr"]');
    if (!q || q.content !== 'url=' + C.url + '/') problems.push('QR address missing or wrong');
    if (!res.qr) problems.push('the QR code did not appear');
  }
  const root = await get('/'), vn = await get('/v/' + C.build + '/');
  if (vn.status !== 200 || vn.text !== root.text) problems.push('/v/' + C.build + '/ is not the same page');
  let doc = null; try { doc = JSON.parse((await get('/history.json')).text); } catch (e) {}
  if (!doc || doc.current !== C.build) problems.push('history.json does not say version ' + C.build);
  else if (C.versions.some(n => !(doc.versions || []).some(v => v.version === n))) problems.push('history.json is missing a version');
  const older = C.versions.filter(n => n !== C.build);
  if (older.length) { const m = older[older.length - 1], vm = await get('/v/' + m + '/'); if (vm.status !== 200) problems.push('/v/' + m + '/ answers ' + vm.status); res.spotChecked = m; }
  for (const p of C.redirects) {
    try { const r = await fetch(p, {redirect: 'manual', cache: 'no-store'}); if (r.type !== 'opaqueredirect') problems.push(p + ' does not redirect'); }
    catch (e) { problems.push(p + ' not reachable'); }
  }
  res.versions = doc ? (doc.versions || []).length : 0;
  if (problems.length) throw new Error('live check failed: ' + JSON.stringify(problems));
  return res;
})();
"""


def run(args, **kw):
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True, **kw)
    return p.returncode, p.stdout, p.stderr


def last_json(text):
    # the scripts print one JSON object (build.py, preview.py) — take the last one
    i = text.rfind('\n{')
    i = 0 if text.startswith('{') and i < 0 else i + 1
    try:
        return json.loads(text[i:])
    except Exception:
        return None


def snapshot(app):
    out = {}
    for root, dirs, files in os.walk(app):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for f in files:
            p = os.path.join(root, f)
            out[os.path.relpath(p, app)] = hashlib.sha1(open(p, 'rb').read()).hexdigest()
    return out


def state_path(scratch):
    return os.path.join(scratch, 'prep-state.json')


def load_state(scratch):
    try:
        return json.load(open(state_path(scratch), encoding='utf-8'))
    except Exception:
        return {}


def save_state(scratch, st):
    json.dump(st, open(state_path(scratch), 'w', encoding='utf-8'), indent=1)


def ensure_app(a, st):
    app = os.path.join(a.scratch, 'app')
    if not os.path.exists(os.path.join(app, 'xr-project.json')):
        if not a.src or not os.path.exists(os.path.join(a.src, 'xr-project.json')):
            print(json.dumps({'ok': False, 'stop': 'no app here: --from must be the staged folder holding index.html and xr-project.json'}))
            sys.exit(2)
        if os.path.exists(app):
            shutil.rmtree(app)
        shutil.copytree(a.src, app, ignore=shutil.ignore_patterns(*SKIP))
        st['before'] = snapshot(app)
    return app


def preview(app, scratch, st):
    code, out, err = run([PREVIEW, '--file', os.path.join(app, 'index.html'), '--out', os.path.join(scratch, 'preview')])
    res = last_json(out) or {}
    st['preview'] = {'exit': code, 'png': os.path.join(scratch, 'preview', 'preview.png')}
    summary = {'exit': code, 'status': res.get('status'), 'ok': res.get('ok')}
    for k in ('errors', 'failed', 'problems', 'summary'):
        if res.get(k):
            summary[k] = res[k]
    if code == 1:
        print(json.dumps({'ok': False, 'stop': 'the app failed its check — fix it before publishing', 'preview': summary}, indent=1))
        save_state(scratch, st)
        sys.exit(1)
    return summary


def bump(app):
    code, out, err = run([os.path.join(HERE, 'build.py'), '--project', app])
    res = last_json(out)
    if code != 0 or not res or not res.get('ok'):
        print(json.dumps({'ok': False, 'stop': 'could not build', 'detail': (res or out or err)[-800:] if not res else res}, indent=1))
        sys.exit(1)
    return res


def show(label, path):
    print('\n----- %s: %s -----' % (label, path))
    sys.stdout.write(open(path, encoding='utf-8').read())
    print('----- end of %s -----' % label)


def cmd_prepare(a):
    st = load_state(a.scratch)
    app = ensure_app(a, st)
    summary = {'ok': True, 'step': 'prepare'}
    if not a.no_preview:
        summary['preview'] = preview(app, a.scratch, st)
    st['previewed'] = True          # checked now, or just checked by /new-xr-app (--no-preview)
    b = bump(app)
    st['bump'] = b
    summary['version'] = b.get('build')
    for k in ('note', 'changelog'):
        if k in b: summary[k] = b[k]
    lo = os.path.join(a.scratch, 'lib-only')
    code, out, err = run([os.path.join(HERE, 'vercel_build.py'), app, '--out', lo, '--library-only'])
    if code != 0:
        print(json.dumps({'ok': False, 'stop': 'library build failed', 'detail': (out + err)[-800:]}, indent=1)); sys.exit(1)
    man = json.load(open(os.path.join(lo, 'manifest.json'), encoding='utf-8'))
    pj = os.path.join(a.scratch, 'prepare.js')
    args = [os.path.join(HERE, 'vercel_payload.py'), lo, '--prepare', '--out', pj] + (['--suffix', a.suffix] if a.suffix else [])
    code, out, err = run(args)
    if code != 0:
        print(json.dumps({'ok': False, 'stop': 'could not write prepare.js', 'detail': (out + err)[-800:]}, indent=1)); sys.exit(1)
    summary.update({'kit': man['kit'], 'libBase': man['libBase'], 'slug': man.get('slug')})
    save_state(a.scratch, st)
    print(json.dumps(summary, indent=1))
    show('browser script', pj)


def cmd_build(a):
    st = load_state(a.scratch)
    app = ensure_app(a, st)
    summary = {'ok': True, 'step': 'build'}
    mpath = os.path.join(app, 'xr-project.json')
    first = False
    if a.prepared:
        p = json.loads(a.prepared)
        if not p.get('ok') or not p.get('url'):
            print(json.dumps({'ok': False, 'stop': 'the prepare step did not give a usable address', 'prepared': p}, indent=1)); sys.exit(1)
        sets = ['vercel.project=%s' % p['name'], 'vercel.projectId=%s' % p['projectId'],
                'vercel.url=%s' % p['url'], 'vercel.via=token']
        if p.get('teamId'): sets.append('vercel.teamId=%s' % p['teamId'])
        store = p.get('store') or {}
        if store.get('storeId'): sets.append('vercel.store=%s' % store['storeId'])
        if a.owner: sets.append('vercel.owner=%s' % a.owner)
        run([os.path.join(HERE, 'manifest.py'), '--project', app] + sum([['--set', s] for s in sets], []))
        first = True
        summary['store'] = 'kept' if store.get('ok') and store.get('tokenSet') else ('not kept: ' + str(store.get('error') or store))
    man = json.load(open(mpath, encoding='utf-8'))
    vc = man.get('vercel') or {}
    if not vc.get('project') or not vc.get('url'):
        print(json.dumps({'ok': False, 'stop': 'this app has no Vercel project yet — run prepare first (first publish)'}, indent=1)); sys.exit(1)
    if not a.no_preview and not st.get('previewed'):
        summary['preview'] = preview(app, a.scratch, st)
        st['previewed'] = True
    b = st.get('bump') if st.get('bump') else bump(app)
    if st.get('bump') is None:
        st['bump'] = b
    summary['version'] = b.get('build'); summary['bumped'] = b.get('bumped')
    if b.get('changelog') == 'empty' and not a.note:
        summary['warning'] = 'the changelog had no line for this version — add one with appdocs.py add and run build again'
    dist = os.path.join(a.scratch, 'dist-vercel')
    if os.path.exists(dist):
        shutil.rmtree(dist)
    args = [os.path.join(HERE, 'vercel_build.py'), app, '--out', dist]
    if a.note: args += ['--note', a.note]
    if a.restored_from is not None: args += ['--restored-from', str(a.restored_from)]
    code, out, err = run(args)
    if code != 0:
        print(json.dumps({'ok': False, 'stop': 'build failed', 'detail': (out + err)[-1200:]}, indent=1)); sys.exit(1)
    m = json.load(open(os.path.join(dist, 'manifest.json'), encoding='utf-8'))
    if m.get('extraLibs'):
        print(json.dumps({'ok': False, 'stop': 'this app uses an extra library that cannot be published yet',
                          'extraLibs': m['extraLibs']}, indent=1)); sys.exit(1)
    if m.get('qrUrl') and m['qrUrl'].rstrip('/') != vc['url'].rstrip('/'):
        print(json.dumps({'ok': False, 'stop': 'the QR address does not match the app address', 'qr': m['qrUrl'], 'url': vc['url']}, indent=1)); sys.exit(1)
    dj = os.path.join(a.scratch, 'deploy.js')
    pargs = [os.path.join(HERE, 'vercel_payload.py'), dist, '--name', vc['project'], '--out', dj]
    if first: pargs.append('--first')
    for f in a.inline: pargs += ['--inline', f]
    code, out, err = run(pargs)
    if code != 0:
        print(json.dumps({'ok': False, 'stop': 'could not write deploy.js', 'detail': (out + err)[-800:]}, indent=1)); sys.exit(1)
    pay = json.loads(out)
    h = m.get('history') or {}
    summary.update({'project': vc['project'], 'url': vc['url'], 'kit': m['kit'], 'note': h.get('note'),
                    'fingerprint': h.get('fingerprint'), 'versions': h.get('count'),
                    'inline': pay['inline'], 'scriptBytes': pay['scriptBytes'],
                    'kitcheckUrl': vc['url'].rstrip('/') + '/?kitcheck'})
    kc = os.path.join(a.scratch, 'kitcheck.js')
    kit = m['kit']
    versions = sorted({v for v in [h.get('current')] if v} | set(
        int(f.split('/')[1]) for f in m['deploy'] if f.startswith('v/') and f.split('/')[1].isdigit()))
    check = {'build': m['build'], 'url': vc['url'].rstrip('/'), 'libBase': m['libBase'], 'qr': bool(m.get('qrUrl')),
             'versions': versions, 'redirects': ['/history'] + (['/about/'] if m.get('about') else []),
             'lib': ['xr-kit-diary-%s.js' % kit, 'xr-kit-%s.css' % kit, 'xr-kit-%s.js' % kit,
                     'xr-kit-panel-%s.js' % kit, 'kit-relay-%s.js' % kit] + (['kit-qr-%s.js' % kit] if m.get('qrUrl') else [])}
    open(kc, 'w', encoding='utf-8').write(KITCHECK.replace('__CHECK__', json.dumps(check)))
    st.update({'kit': m['kit'], 'build': m['build'], 'first': first})
    save_state(a.scratch, st)
    print(json.dumps(summary, indent=1))
    show('browser script', dj)
    show('live check', kc)


def cmd_record(a):
    st = load_state(a.scratch)
    app = os.path.join(a.scratch, 'app')
    if not os.path.exists(os.path.join(app, 'xr-project.json')):
        print(json.dumps({'ok': False, 'stop': 'nothing built in this scratch folder'})); sys.exit(2)
    r = json.loads(a.result) if a.result else {}
    sets = ['vercel.build=%s' % st.get('build'), 'vercel.lib=%s' % st.get('kit'), 'vercel.via=token']
    if r.get('id'): sets.append('vercel.deploymentId=%s' % r['id'])
    if r.get('projectId'): sets.append('vercel.projectId=%s' % r['projectId'])
    if r.get('teamId'): sets.append('vercel.teamId=%s' % r['teamId'])
    run([os.path.join(HERE, 'manifest.py'), '--project', app] + sum([['--set', s] for s in sets], []))
    before, now = st.get('before') or {}, snapshot(app)
    changed = sorted(k for k, h in now.items() if before.get(k) != h)
    files = []
    if a.outputs:
        for rel in changed:
            dest = os.path.join(a.outputs, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(os.path.join(app, rel), dest)
            files.append({'stagedPath': dest, 'relative': rel.replace(os.sep, '/')})
    print(json.dumps({'ok': True, 'step': 'record', 'changed': [f.replace(os.sep, '/') for f in changed],
                      'commit': files}, indent=1))


def cmd_take(a):
    # copy the staged app into <scratch>/app and remember how it looked, for a
    # publish that changes the app first (going back to a version)
    st = load_state(a.scratch)
    app = ensure_app(a, st)
    save_state(a.scratch, st)
    print(json.dumps({'ok': True, 'step': 'take', 'app': app}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('step', choices=['take', 'prepare', 'build', 'record'])
    ap.add_argument('--from', dest='src')
    ap.add_argument('--scratch', required=True)
    ap.add_argument('--prepared')
    ap.add_argument('--owner')
    ap.add_argument('--suffix')
    ap.add_argument('--note')
    ap.add_argument('--restored-from', type=int)
    ap.add_argument('--inline', action='append', default=[])
    ap.add_argument('--no-preview', action='store_true')
    ap.add_argument('--result')
    ap.add_argument('--outputs')
    a = ap.parse_args()
    os.makedirs(a.scratch, exist_ok=True)
    {'take': cmd_take, 'prepare': cmd_prepare, 'build': cmd_build, 'record': cmd_record}[a.step](a)


if __name__ == '__main__':
    main()
