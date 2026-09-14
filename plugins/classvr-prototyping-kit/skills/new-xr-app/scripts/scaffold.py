#!/usr/bin/env python3
"""Create a new ClassVR prototype project folder.

    python3 scaffold.py --name "Planet Walk" --out /path/to/parent [--dof 3|6]

Retarget an existing app (3DoF <-> 6DoF) without re-creating it:

    python3 scaffold.py --retarget /path/to/App/index.html --dof 3

Writes <out>/<Name>/ containing:
    index.html        the app (two-file form, edit this)
    aframe.min.js     bundled A-Frame — never loaded from a CDN
    xr-project.json   the manifest the other kit scripts read and update

Prints a JSON summary on stdout. Exit code 0 on success.
"""
import argparse, json, os, re, shutil, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, '..', 'assets')

HEADSET_CONTROLS = {
    6: "    'Left thumbstick: move',",
    3: "    'Look at something and squeeze a trigger to select it',",
}

def apply_dof(html, dof):
    """Fill the template's target-device placeholders. Also used to retarget an
    existing app: pass its index.html and the new dof, then write it back."""
    import re as _re
    if '{{DOF}}' in html:
        html = html.replace('{{DOF}}', str(dof))
    else:
        html = _re.sub(r'<a-scene xr-kit(="dof:\s*\d")?', '<a-scene xr-kit="dof: %d"' % dof, html, count=1)
    if '{{HEADSET_CONTROLS}}' in html:
        html = html.replace('{{HEADSET_CONTROLS}}', HEADSET_CONTROLS[dof])
    else:
        other = HEADSET_CONTROLS[9 - dof]
        if other in html:
            html = html.replace(other, HEADSET_CONTROLS[dof], 1)
    return html

def slugify(name):
    s = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return s or 'xr-app'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=False, help='Human name of the app, e.g. "Planet Walk"')
    ap.add_argument('--out', required=False, help='Parent folder the project folder is created inside')
    ap.add_argument('--folder', help='Override the project folder name (default: the app name)')
    ap.add_argument('--concept', default=None,
                    help='One-line description of what the app is meant to be (recorded in the manifest)')
    ap.add_argument('--dof', type=int, default=6, choices=(3, 6),
                    help='Target headset: 6 = full tracking (default); 3 = turning only — on a 6DoF headset the '
                         'kit pins the head in place, hides the lasers and selects by gaze + trigger')
    ap.add_argument('--retarget', metavar='INDEX_HTML',
                    help='Instead of creating a project, switch this existing index.html (and its xr-project.json) to --dof')
    a = ap.parse_args()

    if a.retarget:
        path = os.path.abspath(a.retarget)
        html = open(path, encoding='utf-8').read()
        if 'id="tracking"' not in html:
            print(json.dumps({'ok': False, 'error': 'this app predates the 3DoF/6DoF switch (no #tracking wrapper) — its rig needs refreshing from the current template first'}))
            return 2
        open(path, 'w', encoding='utf-8').write(apply_dof(html, a.dof))
        mpath = os.path.join(os.path.dirname(path), 'xr-project.json')
        if os.path.exists(mpath):
            m = json.load(open(mpath, encoding='utf-8')); m['dof'] = a.dof
            open(mpath, 'w', encoding='utf-8').write(json.dumps(m, indent=2) + '\n')
        print(json.dumps({'ok': True, 'retargeted': path, 'dof': a.dof}, indent=2))
        return 0

    if not a.name or not a.out:
        ap.error('--name and --out are required (or use --retarget)')
    folder = a.folder or a.name.strip()
    dest = os.path.join(a.out, folder)
    if os.path.exists(dest) and os.listdir(dest):
        print(json.dumps({'ok': False, 'error': f'folder already exists and is not empty: {dest}'}))
        return 2
    os.makedirs(dest, exist_ok=True)

    tpl = open(os.path.join(ASSETS, 'scene-template.html'), encoding='utf-8').read()
    safe_name = a.name.replace('<', '&lt;').replace('>', '&gt;')
    html = tpl.replace('{{APP_NAME}}', safe_name)
    html = apply_dof(html, a.dof)
    open(os.path.join(dest, 'index.html'), 'w', encoding='utf-8').write(html)
    shutil.copy(os.path.join(ASSETS, 'aframe.min.js'), os.path.join(dest, 'aframe.min.js'))

    manifest = {
        'kit': 'classvr-prototyping-kit',
        'name': a.name,
        'slug': slugify(a.name),
        'concept': (a.concept.strip() or None) if a.concept else None,
        'dof': a.dof,
        'created': datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
        'build': 1,
        'sourceHash': None,
        'libraries': ['aframe'],
        'classcloud': {
            'organizationId': None,
            'playlistId': None,
            'playlistName': 'XR Prototypes',
            'activityId': None,
            'lastPublished': None,
            'lastUrl': None,
            'qrPayload': None
        },
        'artifact': {
            'url': None,
            'owner': None,
            'build': None,
            'lastShared': None
        }
    }
    open(os.path.join(dest, 'xr-project.json'), 'w', encoding='utf-8').write(
        json.dumps(manifest, indent=2) + '\n')

    print(json.dumps({
        'ok': True,
        'project': dest,
        'files': ['index.html', 'aframe.min.js', 'xr-project.json'],
        'name': a.name,
        'slug': manifest['slug'],
        'concept': manifest['concept'],
        'dof': a.dof
    }, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())
