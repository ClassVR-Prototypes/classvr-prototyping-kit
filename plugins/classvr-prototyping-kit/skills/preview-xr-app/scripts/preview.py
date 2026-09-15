#!/usr/bin/env python3
"""Load an XR app in headless Chromium and report whether it actually works.

    python3 preview.py --file /path/to/index.html [--out /path/to/dir] [--settle 4000]

Serves the file's folder over a local HTTP server (so bundled scripts resolve
and no file:// quirks apply), loads it, waits for A-Frame to settle, and checks:

    - the page produced no JavaScript errors
    - no console messages of type "error"
    - A-Frame is present (the bundled library actually loaded)
    - the <a-scene> reports hasLoaded and created a WebGL canvas
    - the xr-kit component attached (the rig plumbing is in place)
    - every self-check passes: the kit's built-in ones (scene loaded, rig
      present, the player can walk) and the app's own window.KIT_CHECKS
    - and it collects the app's diary (window.KIT.report()): errors, events,
      fps, controllers — so nobody has to open a console

Writes <out>/preview.png and <out>/preview.json. Prints the JSON.
Exit 0 = pass, 1 = fail, 3 = preview could not run (Playwright unavailable).
"""
import argparse, json, os, sys, threading, socket, http.server, functools, glob, shutil, subprocess

def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', required=True)
    ap.add_argument('--out', help='folder for preview.png / preview.json (default: file folder)')
    ap.add_argument('--settle', type=int, default=4000, help='ms to wait after load')
    ap.add_argument('--width', type=int, default=1100)
    ap.add_argument('--height', type=int, default=700)
    ap.add_argument('--no-checks', action='store_true', help='skip the self-checks')
    a = ap.parse_args()

    path = os.path.abspath(a.file)
    folder, fname = os.path.split(path)
    out = os.path.abspath(a.out or folder)
    os.makedirs(out, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        os.system(sys.executable + ' -m pip install playwright --break-system-packages -q >/dev/null 2>&1')
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print(json.dumps({'ok': None, 'status': 'unavailable',
                              'reason': 'Playwright is not installed and could not be installed'}))
            return 3

    def find_chromium():
        """A Chromium binary already on this machine, when Playwright's own
        expected revision is missing (cloud sandboxes ship one revision of the
        browser and a different version of the playwright package)."""
        cands = []
        for env in ('PLAYWRIGHT_CHROMIUM_EXECUTABLE', 'CHROME_BIN', 'CHROMIUM_BIN'):
            if os.environ.get(env): cands.append(os.environ[env])
        roots = [os.environ.get('PLAYWRIGHT_BROWSERS_PATH', ''), '/opt/pw-browsers',
                 os.path.expanduser('~/.cache/ms-playwright')]
        for r in roots:
            if not r: continue
            cands += sorted(glob.glob(os.path.join(r, 'chromium-*', 'chrome-linux', 'chrome')), reverse=True)
            cands += sorted(glob.glob(os.path.join(r, 'chromium_headless_shell-*', '*', 'headless_shell')), reverse=True)
            cands += sorted(glob.glob(os.path.join(r, 'chromium_headless_shell-*', '*', 'chrome-headless-shell')), reverse=True)
        for name in ('chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable', 'chrome'):
            w = shutil.which(name)
            if w: cands.append(w)
        for c in cands:
            if c and os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        return None

    def launch(p):
        flags = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']
        try:
            return p.chromium.launch(args=flags), None
        except Exception as e:
            first = str(e)
        exe = find_chromium()
        if exe:
            try:
                return p.chromium.launch(executable_path=exe, args=flags), None
            except Exception as e:
                first += ' | with ' + exe + ': ' + str(e)
        # last resort: let Playwright fetch its own browser (needs network to its CDN)
        try:
            subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'],
                           timeout=240, capture_output=True)
            return p.chromium.launch(args=flags), None
        except Exception as e:
            return None, (first + ' | install: ' + str(e))[:400]

    port = free_port()
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args, **kw): pass
        def do_GET(self):
            # Full Chromium asks for a favicon the app never ships; a 404 there
            # would show up as a console error and fail an otherwise good app.
            if self.path.split('?')[0] == '/favicon.ico':
                self.send_response(204); self.end_headers(); return
            return super().do_GET()
    handler = functools.partial(Quiet, directory=folder)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    console_errors, page_errors, failed = [], [], []
    report, checks, diary = {}, None, None
    try:
        with sync_playwright() as p:
            browser, why = launch(p)
            if browser is None:
                print(json.dumps({'ok': None, 'status': 'unavailable',
                                  'reason': 'no usable Chromium: ' + why,
                                  'hint': 'run "python3 -m playwright install chromium" once, or set PLAYWRIGHT_CHROMIUM_EXECUTABLE to an existing browser binary'}))
                return 3
            pg = browser.new_page(viewport={'width': a.width, 'height': a.height})
            pg.on('console', lambda m: console_errors.append(m.text) if m.type == 'error' else None)
            pg.on('pageerror', lambda e: page_errors.append(str(e)))
            pg.on('requestfailed', lambda r: failed.append(r.url))
            pg.goto(f'http://127.0.0.1:{port}/{fname}', wait_until='load', timeout=90000)
            pg.wait_for_timeout(a.settle)
            report = pg.evaluate("""() => {
              const s = document.querySelector('a-scene');
              const c = s && s.querySelector('canvas');
              return {
                aframe: typeof AFRAME !== 'undefined' ? AFRAME.version : null,
                sceneLoaded: !!(s && s.hasLoaded),
                canvas: c ? (c.width + 'x' + c.height) : null,
                xrKit: !!(s && s.components && s.components['xr-kit']),
                entities: s ? s.querySelectorAll('a-entity, a-box, a-sphere, a-plane, a-cylinder, a-sky').length : 0,
                build: (typeof window.BUILD === 'number') ? window.BUILD : null,
                title: document.title
              };
            }""")
            # hide the panels for a clean screenshot of the scene itself
            pg.evaluate("""() => { ['kit-panel','kit-colour'].forEach(id => {
                const e = document.getElementById(id); if (e) e.style.display = 'none'; }); }""")
            pg.wait_for_timeout(300)
            pg.screenshot(path=os.path.join(out, 'preview.png'))
            # Self-checks run after the screenshot: they press buttons and walk about.
            if not a.no_checks:
                try:
                    checks = pg.evaluate("() => (window.KIT && window.KIT.runChecks) ? window.KIT.runChecks() : null")
                except Exception as e:
                    checks = [{'name': 'the self-checks could run', 'ok': False, 'detail': str(e)[:300]}]
            try:
                diary = pg.evaluate("() => (window.KIT && window.KIT.report) ? window.KIT.report() : null")
            except Exception as e:
                diary = {'unavailable': str(e)[:200]}
            browser.close()
    finally:
        srv.shutdown()

    problems = []
    if page_errors:            problems.append('JavaScript errors: ' + '; '.join(page_errors[:3]))
    if console_errors:         problems.append('console errors: ' + '; '.join(console_errors[:3]))
    if failed:                 problems.append('failed requests: ' + '; '.join(failed[:3]))
    if not report.get('aframe'):      problems.append('A-Frame did not load (is aframe.min.js beside index.html?)')
    if not report.get('sceneLoaded'): problems.append('<a-scene> never finished loading')
    if not report.get('canvas'):      problems.append('no WebGL canvas was created')
    if not report.get('xrKit'):       problems.append('xr-kit component is missing from <a-scene>')
    if checks is None and not a.no_checks and report.get('xrKit'):
        problems.append('this app predates self-checks (no window.KIT) — re-create it from the current template to get them')
    for c in (checks or []):
        if not c.get('ok'):
            problems.append('check failed: "%s"%s' % (c.get('name'), (' — ' + c['detail']) if c.get('detail') else ''))

    result = {
        'ok': not problems,
        'status': 'pass' if not problems else 'fail',
        'problems': problems,
        'details': report,
        'checks': checks,
        'diary': diary,
        'screenshot': os.path.join(out, 'preview.png')
    }
    json.dump(result, open(os.path.join(out, 'preview.json'), 'w'), indent=2)
    print(json.dumps(result, indent=2))
    return 0 if not problems else 1

if __name__ == '__main__':
    sys.exit(main())
