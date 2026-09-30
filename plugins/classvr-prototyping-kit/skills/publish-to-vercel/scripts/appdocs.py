#!/usr/bin/env python3
"""appdocs.py — every kit app's README.md and CHANGELOG.md (kit 0.32).

Each app folder carries two plain-text files beside index.html:

  README.md     what the app is, how to play it, how it works — always
                describes the CURRENT version; rewritten whenever that changes
  CHANGELOG.md  what changed in each version, newest first, in the Keep a
                Changelog 1.1.0 format (https://keepachangelog.com/en/1.1.0/):
                Claude adds lines under "## [Unreleased]" as it edits; the
                build turns them into "## [N] - YYYY-MM-DD" when the build
                number goes up. N is the app's build number, which on Vercel is
                also its version number (/v/N/).

Neither file carries names or e-mail addresses — both are published.

How they travel. Every build (build.py's single file and
vercel_build.py's Vercel page) puts both files inside the page as

  <script type="text/markdown" id="xr-kit-readme">…</script>
  <script type="text/markdown" id="xr-kit-changelog">…</script>

just before </body>, so they go wherever the page goes — every route, every
saved version, every copy — and /copy-xr-app gets them back with `extract`.
A change to either file counts as a change to the app (a new version).

Used as a library by build.py, vercel_build.py and scaffold.py, and from the
command line by the skills:

  appdocs.py init <app folder> [--entry "what this edit did"] [--category Added]
      create whichever file is missing (the changelog seeded from the version
      notes already in xr-project.json), then optionally add an Unreleased line
  appdocs.py add <app folder> --entry "…" [--category Added|Changed|Fixed|Removed|Deprecated|Security]
      add one line under ## [Unreleased]
  appdocs.py status <app folder>
      JSON: which files exist, the Unreleased lines, the newest released version
  appdocs.py extract <page.html> --to <folder> [--only readme|changelog] [--strip-into <file>]
      write the page's embedded README.md / CHANGELOG.md into <folder>;
      --strip-into also writes the page without the two blocks
  appdocs.py fork <copy folder> --url <original address> --version N
                  [--fingerprint abcd1234] [--name "Original name"]
      turn a copied CHANGELOG.md into the copy's own: a fresh Unreleased entry
      saying where it came from, the original's history kept under
      "## Before this copy"
  appdocs.py about <app folder> --out <file> [--url https://…] [--version N]
      the readable "About this app" page (README + changelog as HTML)
"""
import argparse, datetime, html as H, json, os, re, sys

README = 'README.md'
CHANGELOG = 'CHANGELOG.md'
IDS = {'readme': 'xr-kit-readme', 'changelog': 'xr-kit-changelog'}
FILES = {'readme': README, 'changelog': CHANGELOG}
CATEGORIES = ['Added', 'Changed', 'Deprecated', 'Removed', 'Fixed', 'Security']

CHANGELOG_HEAD = """# Changelog

Everything that changed in this app, newest first.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Version numbers are the app's own: version 3 is the third saved version (on
Vercel it stays playable at `/v/3/`). Claude keeps this file up to date as the
app is changed; lines under Unreleased become the next version when it is
published.
"""

_REF = re.compile(r'^\[[^\]]+\]:\s+\S')          # a link reference definition
_VER = re.compile(r'^##\s+\[([^\]]+)\](.*)$')     # ## [3] - 2026-09-28


def today():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')


def read(folder, which):
    p = os.path.join(folder, FILES[which])
    return open(p, encoding='utf-8').read() if os.path.exists(p) else None


def write(folder, which, text):
    open(os.path.join(folder, FILES[which]), 'w', encoding='utf-8', newline='\n').write(text.rstrip('\n') + '\n')


def docs(folder):
    return {k: read(folder, k) for k in FILES}


def hash_text(folder):
    """What the build hashes for the two files. Link reference lines at the
    foot of the changelog are left out: the Vercel build keeps those pointing
    at /v/N/ and that must not count as a change."""
    out = ''
    for k in ('readme', 'changelog'):
        t = read(folder, k)
        if t is None:
            continue
        if k == 'changelog':
            t = '\n'.join(l for l in t.rstrip('\n').split('\n') if not _REF.match(l)).rstrip('\n')
        out += '\n<!--%s:%s-->' % (FILES[k], t)
    return out


# ------------------------------------------------------------------ changelog

def split_sections(text):
    """(head, [(heading line, body)], refs) — refs = trailing link definitions."""
    lines = (text or '').rstrip('\n').split('\n')
    refs = []
    while lines and (_REF.match(lines[-1]) or (not lines[-1].strip() and refs)):
        l = lines.pop()
        if l.strip():
            refs.insert(0, l)
    head, sections, cur = [], [], None
    for l in lines:
        if l.startswith('## '):
            cur = [l, []]
            sections.append(cur)
        elif cur is None:
            head.append(l)
        else:
            cur[1].append(l)
    return '\n'.join(head).rstrip('\n'), [(h, '\n'.join(b).strip('\n')) for h, b in sections], refs


def join_sections(head, sections, refs):
    out = head.rstrip('\n') + '\n'
    for h, b in sections:
        out += '\n' + h + '\n' + ('\n' + b + '\n' if b.strip() else '')
    if refs:
        out += '\n' + '\n'.join(refs) + '\n'
    return out


def has_entries(body):
    return any(re.match(r'^\s*[-*]\s+\S', l) for l in (body or '').split('\n'))


def tidy_body(body):
    """Drop category headings that have nothing under them."""
    out, lines = [], (body or '').split('\n')
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith('### '):
            j = i + 1
            while j < len(lines) and not lines[j].startswith('### '):
                j += 1
            if has_entries('\n'.join(lines[i + 1:j])):
                out.extend(lines[i:j])
            i = j
            continue
        out.append(l)
        i += 1
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(out)).strip('\n')


def unreleased_index(sections):
    for i, (h, _) in enumerate(sections):
        m = _VER.match(h)
        if m and m.group(1).strip().lower() == 'unreleased':
            return i
    return None


def ensure_changelog(text):
    if not text or not text.strip():
        text = CHANGELOG_HEAD + '\n## [Unreleased]\n'
    head, sections, refs = split_sections(text)
    if unreleased_index(sections) is None:
        sections.insert(0, ('## [Unreleased]', ''))
    return join_sections(head, sections, refs)


def add_entry(text, entry, category='Changed'):
    category = category.strip().capitalize()
    if category not in CATEGORIES:
        raise SystemExit('category must be one of ' + ', '.join(CATEGORIES))
    entry = entry.strip()
    if not entry.startswith(('- ', '* ')):
        entry = '- ' + entry
    if entry[-1] not in '.!?)':
        entry += '.'
    head, sections, refs = split_sections(ensure_changelog(text))
    i = unreleased_index(sections)
    h, body = sections[i]
    lines = body.split('\n') if body.strip() else []
    heading = '### ' + category
    if heading in lines:
        j = lines.index(heading) + 1
        while j < len(lines) and not lines[j].startswith('### '):
            j += 1
        while j > 0 and lines[j - 1].strip() == '':
            j -= 1
        lines.insert(j, entry)
    else:
        # keep Keep a Changelog's category order
        order = CATEGORIES.index(category)
        pos = len(lines)
        for k, l in enumerate(lines):
            name = l[4:].strip() if l.startswith('### ') else None
            if name in CATEGORIES and CATEGORIES.index(name) > order:
                pos = k
                break
        lines[pos:pos] = ([''] if pos and lines[pos - 1].strip() else []) + [heading, '', entry, '']
    sections[i] = (h, tidy_body('\n'.join(lines)))
    return join_sections(head, sections, refs)


def cut_release(text, n, date=None, force=False):
    """Turn the Unreleased lines into version n. Returns (text, what) where
    what is 'cut', 'merged' (added to an existing [n]), 'empty' (force: a
    placeholder line was written because nobody wrote notes) or None."""
    date = date or today()
    head, sections, refs = split_sections(ensure_changelog(text))
    i = unreleased_index(sections)
    body = tidy_body(sections[i][1])
    what = None
    existing = next((k for k, (h, _) in enumerate(sections)
                     if _VER.match(h) and _VER.match(h).group(1).strip() == str(n)), None)
    if not has_entries(body):
        if not force or existing is not None:
            return join_sections(head, sections, refs), None
        body = '### Changed\n\n- Small changes (no notes were written for this version).'
        what = 'empty'
    sections[i] = ('## [Unreleased]', '')
    if existing is not None:
        h, b = sections[existing]
        sections[existing] = (h, merge_bodies(body, b))
        what = what or 'merged'
    else:
        sections.insert(i + 1, ('## [%d] - %s' % (n, date), body))
        what = what or 'cut'
    return join_sections(head, sections, refs), what


def merge_bodies(new, old):
    t = old
    cat = 'Changed'
    for l in new.split('\n'):
        if l.startswith('### '):
            cat = l[4:].strip()
        elif re.match(r'^\s*[-*]\s+\S', l):
            t = _add_to_body(t, l, cat)
    return t


def _add_to_body(body, entry, cat):
    fake = join_sections('', [('## [Unreleased]', body)], [])
    out = add_entry(fake, entry, cat if cat in CATEGORIES else 'Changed')
    return split_sections(out)[1][0][1]


def version_section(text, n):
    if not text:
        return None
    for h, b in split_sections(text)[1]:
        m = _VER.match(h)
        if m and m.group(1).strip() == str(n):
            return b
    return None


def plain(md):
    md = re.sub(r'`([^`]*)`', r'\1', md)
    md = re.sub(r'<(https?://[^>\s]+)>', r'\1', md)
    md = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', md)
    md = re.sub(r'(\*\*|__)(.+?)\1', r'\2', md)
    md = re.sub(r'(?<![\w*])[*_](.+?)[*_](?![\w*])', r'\1', md)
    return md.strip()


def note_from(text, n, limit=140):
    """One line for the public history list, from version n's changelog lines."""
    body = version_section(text, n)
    if not body:
        return None
    items = [plain(re.sub(r'^\s*[-*]\s+', '', l)) for l in body.split('\n') if re.match(r'^[-*]\s+\S', l)]
    items = [i.rstrip('.') for i in items if i and not i.startswith('Small changes (no notes')]
    if not items:
        return None
    note = items[0]
    for k, extra in enumerate(items[1:], 1):
        if len(note) + 2 + len(extra) > limit:
            note += ' (and %d more)' % (len(items) - k)
            break
        note += '; ' + extra
    if len(note) > limit + 20:
        note = note[:limit].rsplit(' ', 1)[0] + '…'
    return note


def set_links(text, url):
    """Point every released version heading at its /v/N/ address."""
    if not text or not url:
        return text
    url = url.rstrip('/')
    head, sections, refs = split_sections(text)
    keep = [r for r in refs if not re.match(r'^\[\d+\]:', r)]
    nums = [m.group(1).strip() for h, _ in sections for m in [_VER.match(h)] if m and m.group(1).strip().isdigit()]
    return join_sections(head, sections, ['[%s]: %s/v/%s/' % (v, url, v) for v in nums] + keep)


def fork_changelog(text, url, version, fingerprint=None, name=None):
    """The copy's own changelog: Unreleased says where it came from; the
    original's history (up to the copied version — the copied page only knows
    that far) moves under "## Before this copy" with headings a level down and
    version numbers as plain text, so they never clash with the copy's own."""
    url = (url or '').rstrip('/')
    url = re.sub(r'/v/\d+$', '', url)
    what = '"%s" ' % name if name else ''
    fp = ', fingerprint %s' % fingerprint[:8] if fingerprint else ''
    where = '<%s/v/%s/>' % (url, version) if url else 'the original'
    entry = 'Made this copy of %sversion %s (%s%s).' % (what, version, where, fp)
    _, old_sections, old_refs = split_sections(text or '')
    refmap = {}
    for r in old_refs:
        m = re.match(r'^\[([^\]]+)\]:\s+(\S+)', r)
        if m:
            refmap[m.group(1)] = m.group(2)
    before = []
    for h, b in old_sections:
        m = _VER.match(h)
        if m and m.group(1).strip().lower() == 'unreleased':
            continue                                      # never published
        if m:
            label, rest = m.group(1).strip(), m.group(2)
            link = refmap.get(label) or (url + '/v/%s/' % label if url and label.isdigit() else None)
            h = '### ' + (('[Version %s](%s)' % (label, link)) if link else 'Version ' + label) + rest
        else:
            h = '#' + h                                   # e.g. an older "Before this copy"
        b = '\n'.join(('#' + l) if l.startswith('#') else l for l in b.split('\n'))
        before.append(h + ('\n\n' + b if b.strip() else ''))
    out = add_entry(CHANGELOG_HEAD + '\n## [Unreleased]\n', entry, 'Added')
    if before:
        out = (out.rstrip('\n') + '\n\n## Before this copy\n\nThe history of the original app%s, up to the version '
               'this copy was made from.\n\n' % (' at <%s/>' % url if url else '') + '\n\n'.join(before) + '\n')
    return out


# ------------------------------------------------------------------ files

def seed_changelog(manifest):
    """A changelog for an app that never had one, from the version notes
    already in its manifest (Vercel apps), newest first."""
    text = CHANGELOG_HEAD + '\n## [Unreleased]\n'
    vers = ((manifest or {}).get('vercel') or {}).get('versions') or []
    secs = []
    for v in sorted(vers, key=lambda x: x.get('version', 0), reverse=True):
        note = (v.get('note') or '').strip() or 'Version %s' % v.get('version')
        cat = 'Added' if v.get('version') == 1 else 'Changed'
        secs.append('## [%s] - %s\n\n### %s\n\n- %s' % (v['version'], (v.get('date') or '')[:10] or today(), cat,
                                                      note if note.endswith('.') else note + '.'))
    if secs:
        text += '\n' + '\n\n'.join(secs) + '\n'
    return text


def readme_template(name, concept=None, dof=6):
    headset = ('- Left thumbstick: move about\n- Right thumbstick: turn\n'
               '- Point a controller at something and squeeze the trigger to select it'
               if dof != 3 else
               '- Turn your head to look around (walking about is switched off)\n'
               '- Look at something and squeeze a trigger to select it')
    concept = (concept.strip().rstrip('.') + '.') if concept else 'A starter scene, ready to build on.'
    return """# {name}

{concept}

A WebXR prototype for ClassVR headsets, made with the ClassVR Prototyping Kit.
It also runs in a web browser on a computer.

## How to play

On a headset: open the app's link (or scan its QR code with the ClassVR
scanner) and press **Enter VR**.

{headset}

On a computer: right-click and drag to look around, left-click to press what
the centre ring points at, W A S D to move and Q / E to turn.

## What's in it

- A checked green ground and a blue sky
- A status panel showing the app's name and version

## How it works

The whole app is one web page built with A-Frame, a library for 3D scenes in
the browser. The kit adds the VR controls, the status panel and the app's
self-checks.

## Make your own copy

Ask Claude: "make me my own copy of" followed by this app's address. You get
an independent copy to change however you like; the original is untouched.
""".format(name=name, concept=concept, headset=headset)


def init(folder, entry=None, category='Changed'):
    made = []
    mpath = os.path.join(folder, 'xr-project.json')
    man = json.load(open(mpath, encoding='utf-8')) if os.path.exists(mpath) else {}
    if read(folder, 'readme') is None:
        write(folder, 'readme', readme_template(man.get('name') or os.path.basename(os.path.abspath(folder)),
                                                man.get('concept'), man.get('dof') or 6))
        made.append(README)
    if read(folder, 'changelog') is None:
        write(folder, 'changelog', seed_changelog(man))
        made.append(CHANGELOG)
    if entry:
        write(folder, 'changelog', add_entry(read(folder, 'changelog'), entry, category))
    return made


def status(folder):
    cl = read(folder, 'changelog')
    out = {'readme': read(folder, 'readme') is not None, 'changelog': cl is not None,
           'unreleased': [], 'latest': None}
    if cl:
        sections = split_sections(cl)[1]
        i = unreleased_index(sections)
        if i is not None:
            out['unreleased'] = [l.strip() for l in sections[i][1].split('\n') if re.match(r'^\s*[-*]\s+\S', l)]
        for h, _ in sections:
            m = _VER.match(h)
            if m and m.group(1).strip().isdigit():
                out['latest'] = int(m.group(1))
                break
    return out


# ------------------------------------------------------------------ embed / extract

def _enc(t):
    return t.replace('</', '<\\/').replace('<!--', '<\\!--')


def _dec(t):
    return t.replace('<\\!--', '<!--').replace('<\\/', '</')


def strip(page):
    for i in IDS.values():
        page = re.sub(r'<script type="text/markdown" id="%s">.*?</script>\n?' % i, '', page, flags=re.S)
    return page


def embed(page, d):
    """Put the README and changelog inside the page, just before </body>."""
    page = strip(page)
    blocks = ''
    for k in ('readme', 'changelog'):
        if d.get(k):
            blocks += '<script type="text/markdown" id="%s">\n%s\n</script>\n' % (IDS[k], _enc(d[k].rstrip('\n')))
    if not blocks:
        return page
    ends = list(re.finditer(r'</body\s*>', page, flags=re.IGNORECASE))
    return (page[:ends[-1].start()] + blocks + page[ends[-1].start():]) if ends else page + '\n' + blocks


def extract(page):
    d = {}
    for k, i in IDS.items():
        m = re.search(r'<script type="text/markdown" id="%s">\n?(.*?)\n?</script>' % i, page, re.S)
        if m:
            d[k] = _dec(m.group(1)) + '\n'
    return d


# ------------------------------------------------------------------ markdown -> HTML

def _inline(t, refs):
    out = []
    for p in re.split(r'(`[^`]*`)', t):
        if len(p) > 1 and p.startswith('`') and p.endswith('`'):
            out.append('<code>%s</code>' % H.escape(p[1:-1]))
            continue
        s = H.escape(p, quote=False)

        def link(m):
            href = H.unescape(m.group(2))
            if not re.match(r'^(https?://|/|\./|\.\./|#)', href):
                return m.group(0)
            return '<a href="%s">%s</a>' % (H.escape(href, quote=True), m.group(1))
        s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', link, s)
        s = re.sub(r'&lt;(https?://[^\s&]+)&gt;', lambda m: '<a href="%s">%s</a>' % (m.group(1), m.group(1)), s)

        def ref(m):
            href = refs.get(H.unescape(m.group(1)))
            return '<a href="%s">%s</a>' % (H.escape(href, quote=True), m.group(1)) if href else m.group(0)
        s = re.sub(r'(?<![\]\w])\[([^\]]+)\](?![(\[:])', ref, s)
        s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
        s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<i>\1</i>', s)
        out.append(s)
    return ''.join(out)


def md_html(md):
    refs, lines = {}, []
    for l in (md or '').split('\n'):
        m = re.match(r'^\[([^\]]+)\]:\s+(\S+)\s*$', l)
        if m:
            refs[m.group(1)] = m.group(2)
        else:
            lines.append(l)
    out, para, stack, code = [], [], [], None

    def flush():
        if para:
            out.append('<p>%s</p>' % _inline(' '.join(x.strip() for x in para), refs))
            para.clear()

    def close(depth=0):
        while len(stack) > depth:
            out.append('</li></%s>' % stack.pop())

    for l in lines:
        if code is not None:
            if l.strip().startswith('```'):
                out.append('<pre><code>%s</code></pre>' % H.escape('\n'.join(code)))
                code = None
            else:
                code.append(l)
            continue
        if l.strip().startswith('```'):
            flush(); close(); code = []
            continue
        m = re.match(r'^(#{1,6})\s+(.*)$', l)
        if m:
            flush(); close()
            n = len(m.group(1))
            out.append('<h%d>%s</h%d>' % (n, _inline(m.group(2), refs), n))
            continue
        m = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)$', l)
        if m:
            flush()
            depth = len(m.group(1).replace('\t', '  ')) // 2 + 1
            kind = 'ol' if m.group(2)[0].isdigit() else 'ul'
            if depth > len(stack):
                while depth > len(stack):
                    out.append('<%s><li>' % kind)
                    stack.append(kind)
            else:
                close(depth)
                out.append('</li><li>')
            out.append(_inline(m.group(3), refs))
            continue
        if not l.strip():
            flush(); close()
            continue
        if stack:
            out.append(' ' + _inline(l.strip(), refs))
            continue
        para.append(l)
    flush(); close()
    if code is not None:
        out.append('<pre><code>%s</code></pre>' % H.escape('\n'.join(code)))
    return '\n'.join(out)


def pretty_changelog(md):
    """For reading, not for the file: drop an empty Unreleased section and
    show "## [3] - date" as "Version 3 - date" (linked when the file links it)."""
    if not md:
        return md
    head, sections, refs = split_sections(md)
    refmap = dict(m.groups() for r in refs for m in [re.match(r'^\[([^\]]+)\]:\s+(\S+)', r)] if m)
    out = []
    for h, b in sections:
        m = _VER.match(h)
        if m:
            label = m.group(1).strip()
            if label.lower() == 'unreleased':
                if not has_entries(b):
                    continue
                h = '## Not published yet'
            else:
                title = 'Version ' + label
                h = '## ' + (('[%s](%s)' % (title, refmap[label])) if label in refmap else title) + m.group(2)
        out.append((h, b))
    return join_sections(head, out, [r for r in refs if not re.match(r'^\[\d+\]:', r)])


def about_page(name, readme, changelog, url=None, version=None):
    name = name or 'This app'
    app = (url or '').rstrip('/')
    links = ['<a href="%s">Open the app</a>' % H.escape((app + '/') if app else '../')]
    if app:
        links.append('<a href="%s/history">Every version</a>' % H.escape(app))
    body_r = md_html(readme) if readme else '<p>No description has been written for this app yet.</p>'
    body_c = md_html(pretty_changelog(changelog)) if changelog else '<p>No changelog has been kept for this app yet.</p>'
    ver = ' · version %s' % version if version else ''
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{title} — about</title>
<style>
:root {{ --bg:#f7f7f5; --fg:#1e1e1e; --muted:#6b6b6b; --card:#fff; --line:#e3e3e0; --accent:#2b6cb0; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#141414; --fg:#ececec; --muted:#a0a0a0; --card:#1e1e1e; --line:#2c2c2c; --accent:#7fb3ff; }} }}
body {{ margin:0; padding:24px 16px 48px; background:var(--bg); color:var(--fg); font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }}
main {{ max-width:720px; margin:0 auto; }}
nav {{ display:flex; flex-wrap:wrap; gap:6px 16px; margin:0 0 18px; font-size:.95rem; }}
section {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:6px 20px 14px; margin:0 0 18px; overflow-wrap:anywhere; }}
h1 {{ font-size:1.5rem; margin:10px 0 6px; }} h2 {{ font-size:1.15rem; margin:22px 0 6px; }}
h3 {{ font-size:1rem; margin:16px 0 4px; }} h4 {{ font-size:.95rem; margin:12px 0 4px; color:var(--muted); }}
a {{ color:var(--accent); }} ul, ol {{ padding-left:22px; }}
code {{ font:.9em ui-monospace,Menlo,Consolas,monospace; background:var(--bg); padding:1px 5px; border-radius:4px; }}
pre {{ background:var(--bg); padding:10px 12px; border-radius:8px; overflow:auto; }}
.label {{ font-size:.8rem; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin:14px 0 0; }}
</style>
</head>
<body>
<main>
<nav>{links}</nav>
<section><p class="label">About this app{ver}</p>
{readme}
</section>
<section><p class="label">What changed</p>
{changelog}
</section>
</main>
</body>
</html>
""".format(title=H.escape(name), links=' '.join(links), ver=H.escape(ver), readme=body_r, changelog=body_c)


# ------------------------------------------------------------------ CLI

def main():
    ap = argparse.ArgumentParser(description="An app's README.md and CHANGELOG.md")
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('init'); p.add_argument('folder'); p.add_argument('--entry'); p.add_argument('--category', default='Changed')
    p = sub.add_parser('add'); p.add_argument('folder'); p.add_argument('--entry', required=True); p.add_argument('--category', default='Changed')
    p = sub.add_parser('status'); p.add_argument('folder')
    p = sub.add_parser('extract'); p.add_argument('page'); p.add_argument('--to', required=True)
    p.add_argument('--only', choices=['readme', 'changelog']); p.add_argument('--strip-into')
    p = sub.add_parser('fork'); p.add_argument('folder'); p.add_argument('--url', required=True)
    p.add_argument('--version', required=True); p.add_argument('--fingerprint'); p.add_argument('--name')
    p = sub.add_parser('about'); p.add_argument('folder'); p.add_argument('--out', required=True)
    p.add_argument('--url'); p.add_argument('--version')
    a = ap.parse_args()

    if a.cmd == 'init':
        made = init(a.folder, a.entry, a.category)
        print(json.dumps(dict(ok=True, created=made, **status(a.folder)), indent=2))
    elif a.cmd == 'add':
        write(a.folder, 'changelog', add_entry(read(a.folder, 'changelog'), a.entry, a.category))
        print(json.dumps(dict(ok=True, **status(a.folder)), indent=2))
    elif a.cmd == 'status':
        print(json.dumps(dict(ok=True, **status(a.folder)), indent=2))
    elif a.cmd == 'extract':
        page = open(a.page, encoding='utf-8').read()
        d = extract(page)
        os.makedirs(a.to, exist_ok=True)
        wrote = []
        for k, t in d.items():
            if a.only and k != a.only:
                continue
            write(a.to, k, t)
            wrote.append(FILES[k])
        if a.strip_into:
            open(a.strip_into, 'w', encoding='utf-8', newline='\n').write(strip(page))
        print(json.dumps({'ok': True, 'found': sorted(FILES[k] for k in d), 'wrote': wrote}, indent=2))
    elif a.cmd == 'fork':
        write(a.folder, 'changelog', fork_changelog(read(a.folder, 'changelog'), a.url, a.version, a.fingerprint, a.name))
        if read(a.folder, 'readme') is None:
            init(a.folder)
        print(json.dumps(dict(ok=True, **status(a.folder)), indent=2))
    elif a.cmd == 'about':
        man = {}
        mp = os.path.join(a.folder, 'xr-project.json')
        if os.path.exists(mp):
            man = json.load(open(mp, encoding='utf-8'))
        url = a.url or (man.get('vercel') or {}).get('url')
        open(a.out, 'w', encoding='utf-8', newline='\n').write(
            about_page(man.get('name'), read(a.folder, 'readme'), read(a.folder, 'changelog'), url, a.version))
        print(json.dumps({'ok': True, 'out': a.out}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
