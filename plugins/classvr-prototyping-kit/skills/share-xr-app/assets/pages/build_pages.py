#!/usr/bin/env python3
"""Assemble the GitHub Pages site from the kit apps in this repo.

Every folder holding an `xr-project.json` is one app. It is copied to
`_site/<slug>/`, taking the slug from the manifest rather than the folder
name — so "Planet Walk" is served at /planet-walk/ instead of
/Planet%20Walk/, which is the difference between a URL somebody can type
into a headset browser and one they cannot.

A small index page lists whatever was found. Run it from the repo root:

    python3 .github/scripts/build_pages.py [--out _site]

Prints a one-line summary per app. Exit 0 even with no apps — an empty
repo should still publish its index rather than fail the deploy.
"""
import argparse
import html
import json
import os
import re
import shutil
import sys

# Copied into the site as-is; everything else in an app folder is skipped.
KEEP_SUFFIXES = ('.html', '.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.json')

# Never descend into these looking for apps.
SKIP_DIRS = {'.git', '.github', '.claude', '.agents', 'kit', 'node_modules', '_site', 'dist', '.preview'}


def find_apps(root):
    """Every directory with an xr-project.json, nearest the top first."""
    found = []
    for here, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith('.'))
        if 'xr-project.json' in files and os.path.abspath(here) != os.path.abspath(root):
            found.append(here)
            dirs[:] = []                      # apps do not nest inside apps
    return found


def slugify(text):
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return slug or 'app'


def read_manifest(app_dir):
    path = os.path.join(app_dir, 'xr-project.json')
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        print('  ! could not read %s (%s) — using the folder name' % (path, e), file=sys.stderr)
        return {}


def copy_app(app_dir, dest):
    """Copy the servable files of one app folder, flat plus one level of assets."""
    os.makedirs(dest, exist_ok=True)
    copied = 0
    for here, dirs, files in os.walk(app_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        rel = os.path.relpath(here, app_dir)
        target = dest if rel == '.' else os.path.join(dest, rel)
        os.makedirs(target, exist_ok=True)
        for name in files:
            if name.startswith('.') or not name.lower().endswith(KEEP_SUFFIXES):
                continue
            shutil.copy2(os.path.join(here, name), os.path.join(target, name))
            copied += 1
    return copied


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>XR prototypes</title>
<style>
  :root {
    color-scheme: light dark;
    --bg: #f7f7f4; --card: #ffffff; --ink: #1d2733; --soft: #5b6b7b;
    --line: #e2e5e2; --accent: #2f6f4f;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #171a1d; --card: #21262b; --ink: #e8ecef; --soft: #9fadb9;
            --line: #333a41; --accent: #7fc79e; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 48px 20px 64px; background: var(--bg); color: var(--ink);
         font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 1.7rem; margin: 0 0 6px; letter-spacing: -0.01em; }
  .lede { color: var(--soft); margin: 0 0 32px; }
  ul { list-style: none; margin: 0; padding: 0; }
  li { background: var(--card); border: 1px solid var(--line); border-radius: 12px;
       padding: 18px 20px; margin-bottom: 14px; }
  a.name { color: var(--accent); font-weight: 650; font-size: 1.12rem;
           text-decoration: none; }
  a.name:hover { text-decoration: underline; }
  .concept { color: var(--soft); margin: 6px 0 10px; }
  .meta { color: var(--soft); font-size: 0.85rem; }
  .meta span + span::before { content: " · "; }
  .empty { color: var(--soft); }
  footer { color: var(--soft); font-size: 0.85rem; margin-top: 36px;
           border-top: 1px solid var(--line); padding-top: 16px; }
</style>
</head>
<body>
<main>
  <h1>XR prototypes</h1>
  <p class="lede">WebXR prototypes built with the ClassVR Prototyping Kit. Open one on a
  desktop to look around, or on a headset to press <strong>Enter VR</strong>.</p>
  __LIST__
  <footer>Published from <code>main</code> by GitHub Actions. The build number on each
  app's panel tells you which version you are looking at; a change can take a few
  minutes to reach this page.</footer>
</main>
</body>
</html>
"""


def render_index(apps):
    if not apps:
        return PAGE.replace('__LIST__', '<p class="empty">No apps here yet.</p>')
    items = []
    for app in apps:
        meta = []
        if app['dof']:
            meta.append('%sDoF headsets' % app['dof'])
        if app['build']:
            meta.append('build %s' % app['build'])
        items.append(
            '<li>\n'
            '      <a class="name" href="%s/">%s</a>\n'
            '      %s'
            '      <div class="meta">%s</div>\n'
            '    </li>' % (
                html.escape(app['slug']),
                html.escape(app['name']),
                '<p class="concept">%s</p>\n      ' % html.escape(app['concept']) if app['concept'] else '',
                ''.join('<span>%s</span>' % html.escape(str(m)) for m in meta),
            ))
    return PAGE.replace('__LIST__', '<ul>\n    %s\n  </ul>' % '\n    '.join(items))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.', help='repo root to scan (default: here)')
    ap.add_argument('--out', default='_site', help='directory to assemble into')
    a = ap.parse_args()

    out = os.path.abspath(a.out)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)

    apps, seen = [], {}
    for app_dir in find_apps(a.root):
        manifest = read_manifest(app_dir)
        name = manifest.get('name') or os.path.basename(app_dir)
        slug = manifest.get('slug') or slugify(name)
        if slug in seen:
            print('  ! %s and %s both want /%s/ — skipping the second'
                  % (seen[slug], app_dir, slug), file=sys.stderr)
            continue
        if not os.path.exists(os.path.join(app_dir, 'index.html')):
            print('  ! %s has no index.html — skipping' % app_dir, file=sys.stderr)
            continue
        seen[slug] = app_dir
        files = copy_app(app_dir, os.path.join(out, slug))
        apps.append({'name': name, 'slug': slug, 'concept': manifest.get('concept') or '',
                     'dof': manifest.get('dof'), 'build': manifest.get('build')})
        print('  %-28s -> /%s/  (%d files)' % (name, slug, files))

    apps.sort(key=lambda x: x['name'].lower())
    with open(os.path.join(out, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(render_index(apps))
    # Pages runs Jekyll by default, which would drop anything starting with _
    open(os.path.join(out, '.nojekyll'), 'w').close()

    print('%d app(s) assembled into %s' % (len(apps), a.out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
