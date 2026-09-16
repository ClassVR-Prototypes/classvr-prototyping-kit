#!/usr/bin/env python3
"""Read a ClassVR device log and pull out the diaries that kit apps wrote into it.

A kit app on a headset rewrites its own #fragment with a small beacon
(history.replaceState) on load, on every error or flag, when VR starts or stops,
every 30 s, and when the page is left. Wolvic logs every main-frame navigation
start, so each beacon is a line in the device log:

    09-07 17:07:20.506  4346  4346 D VRB[Session]: onLoadRequest: https://avnfs.com/<hash>?...&name=<slug>-build<N>.html#kit=<session>-<beacon>-<part>-<parts>.<base64url JSON>

This script finds those lines, reassembles chunked beacons, decodes them, and
groups them into sessions — one per page load — with the diary entries in order.
It also notes the other pages Wolvic loaded and a few headset-level lines
(OpenXR session changes, crashes) so "the page never started" is visible too.

    python3 headset_diary.py --log device.log [--app <name or slug>] [--since "09-07 16:00"] [--json out.json] [--summary]

Log timestamps are the headset's local clock (no year, no zone). Nothing here
needs the network.
"""
import argparse, base64, json, re, sys
from collections import OrderedDict

LINE = re.compile(r'^(\d\d-\d\d \d\d:\d\d:\d\d\.\d+)\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+(\S+?)\s*:\s?(.*)$')
LOAD = re.compile(r'VRB\[Session\]: onLoadRequest: (\S+)')
BEACON = re.compile(r'#kit=([A-Za-z0-9]+)-(\d+)-(\d+)-(\d+)\.([A-Za-z0-9_\-]*)$')
NAME = re.compile(r'[?&]name=([^&#]+)')
BUILD = re.compile(r'-build(\d+)\.html$')
NOTABLE = re.compile(r'(OpenXR|xrBeginSession|xrEndSession|xrRequestExitSession|SESSION_STATE|Fatal signal|FATAL EXCEPTION|'
                     r'ANR in|Low on memory|lowmemorykiller|GPU process|Out of memory|Renderer process|has died|'
                     r'VRB\[VRBrowserActivity\]: onPause|VRB\[VRBrowserActivity\]: onResume|onLoadError|didFailLoad)', re.I)

def b64d(s):
    s = s.replace('-', '+').replace('_', '/')
    s += '=' * (-len(s) % 4)
    return base64.b64decode(s).decode('utf-8', 'replace')

def slugify(text):
    """The same rule the kit uses for folder → URL: lower-case, runs of anything
    that isn't a letter or digit become one hyphen."""
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')

def page_of(url):
    """Identify the kit page a load refers to. Two URL shapes are known:
    AVNFS (ClassCloud): …?name=<slug>-build<N>.html — slug and build in the name
    GitHub Pages:       https://<owner>.github.io/<repo>/<slug>/[index.html][?b=<N>]
    Anything else: last path segment as the slug, no build."""
    from urllib.parse import unquote, urlsplit, parse_qs
    base = url.split('#')[0]
    m = NAME.search(base)
    if m:                                   # AVNFS
        name = unquote(m.group(1))
        b = BUILD.search(name)
        return {'url': base, 'file': name, 'slug': re.sub(r'-build\d+\.html$', '', name), 'build': int(b.group(1)) if b else None}
    u = urlsplit(base)
    segs = [unquote(x) for x in u.path.split('/') if x]
    if segs and segs[-1].lower().endswith('.html'):
        segs = segs[:-1] if segs[-1].lower() == 'index.html' else segs[:-1] + [re.sub(r'\.html$', '', segs[-1], flags=re.I)]
    slug = slugify(segs[-1]) if segs else (u.netloc or base)[:60]
    q = parse_qs(u.query)
    bq = q.get('b', [None])[0]
    return {'url': base, 'file': (segs[-1] if segs else '') + '/', 'slug': slug,
            'build': int(bq) if bq and bq.isdigit() else None}

def same_app(session, wanted):
    """--app accepts the app's name ("Bubble Pop"), its slug ("bubble-pop"), or
    anything that slugifies to the same thing ("bubble pop", "BUBBLE_POP")."""
    w = slugify(wanted)
    return w and (slugify(session.get('slug')) == w or slugify(session.get('app')) == w)

def parse(path, since=None):
    sessions = OrderedDict()      # session id -> dict
    loads, notable = [], []
    parts = {}                    # (session, beacon no) -> {part: text, 'parts': n, 'ts': ts}
    with open(path, encoding='utf-8', errors='replace') as f:
        for raw in f:
            m = LINE.match(raw.rstrip('\n'))
            if not m:
                continue
            ts, level, tag, msg = m.group(1), m.group(4), m.group(5), m.group(6)
            if since and ts < since:
                continue
            lm = LOAD.search(raw)
            if lm:
                url = lm.group(1)
                bm = BEACON.search(url)
                if not bm:
                    if not url.startswith('#'):
                        loads.append({'ts': ts, **page_of(url)})
                    continue
                sid, n, p, total, enc = bm.group(1), int(bm.group(2)), int(bm.group(3)), int(bm.group(4)), bm.group(5)
                key = (sid, n)
                slot = parts.setdefault(key, {'parts': total, 'ts': ts, 'chunks': {}})
                slot['chunks'][p] = enc
                if len(slot['chunks']) < total:
                    continue
                enc_all = ''.join(slot['chunks'][i] for i in range(1, total + 1))
                del parts[key]
                try:
                    body = json.loads(b64d(enc_all))
                except Exception as e:
                    body = {'k': 'undecodable', 'error': str(e)[:100]}
                s = sessions.setdefault(sid, {'session': sid, 'page': page_of(url), 'first': slot['ts'], 'last': ts,
                                              'beacons': [], 'entries': OrderedDict(), 'incomplete': 0})
                s['last'] = ts
                s['beacons'].append({'ts': slot['ts'], 'n': n, 'k': body.get('k'), 't': body.get('t'), 'st': body.get('st'),
                                     'vr': body.get('vr'), 'fps': body.get('fps'), 'e': body.get('e'), 'f': body.get('f'),
                                     'p': body.get('p'), 'tn': body.get('tn'), 'c': body.get('c'), 'lk': body.get('lk')})
                for k in ('app', 'browser', 'platform', 'webxr', 'secure', 'ua', 'b', 'dof'):
                    if k in body and k not in s:
                        s[k] = body[k]
                if body.get('dropped'):
                    s['dropped'] = s.get('dropped', 0) + body['dropped']
                for d in body.get('d') or []:
                    try:
                        entry = {'i': d[0], 't': d[1], 'kind': d[2], 'text': d[3]}
                        for extra in d[4:]:
                            if isinstance(extra, str) and extra.startswith('x') and extra[1:].isdigit():
                                entry['repeats'] = int(extra[1:])
                            else:
                                entry['code'] = extra
                        s['entries'][entry['i']] = entry
                    except Exception:
                        pass
            elif NOTABLE.search(msg) or level in 'EF' and tag.startswith('VRB'):
                notable.append({'ts': ts, 'level': level, 'tag': tag, 'text': msg[:200]})
    for key, slot in parts.items():
        if key[0] in sessions:
            sessions[key[0]]['incomplete'] += 1
    out = []
    for s in sessions.values():
        entries = [s['entries'][i] for i in sorted(s['entries'])]
        last = s['beacons'][-1] if s['beacons'] else {}
        errors = [e for e in entries if e['kind'] == 'error']
        flags = [e for e in entries if e['kind'] == 'flag']
        out.append({
            'session': s['session'], 'app': s.get('app') or s['page']['slug'], 'slug': s['page']['slug'],
            'build': s.get('b', s['page']['build']), 'file': s['page']['file'],
            'first': s['first'], 'last': s['last'], 'secondsRunning': last.get('t'),
            'browser': s.get('browser'), 'platform': s.get('platform'), 'webxr': s.get('webxr'), 'secure': s.get('secure'),
            'status': last.get('st'), 'ended': last.get('k') == 'end',
            'enteredVR': any(b.get('vr') for b in s['beacons']),
            'fps': last.get('fps'), 'controllers': last.get('c'), 'presses': last.get('p'), 'turns': last.get('tn'),
            'dof': s.get('dof'),
            # 3DoF lock, from the last beacon that carried it: [how far the player really moved, how far the view gave (≈ give × moved), frames locked]
            'lock': next((b['lk'] for b in reversed(s['beacons']) if b.get('lk')), None),
            'errors': len(errors), 'firstCode': errors[0].get('code') if errors else None, 'flags': [f['t'] for f in flags],
            'beacons': s['beacons'], 'incompleteBeacons': s['incomplete'], 'dropped': s.get('dropped', 0),
            'errorList': errors, 'entries': entries,
        })
    return out, loads, notable

def before(entries, t, seconds=10):
    return [e for e in entries if t - seconds <= e['t'] <= t and e['kind'] != 'flag']

def summarise(sessions, loads, notable, app=None):
    lines = []
    if app:
        sessions = [s for s in sessions if same_app(s, app)]
    if not sessions:
        lines.append('No kit diaries found in this log' + (' for ' + app if app else '') + '.')
        kit_loads = [l for l in loads if 'avnfs.com' in l['url'] or '.github.io/' in l['url'] or '#kit=' in l['url']]
        if kit_loads:
            lines.append('Kit pages Wolvic did load: ' + ', '.join('%s at %s' % (l['file'], l['ts']) for l in kit_loads[-5:]))
            lines.append('A page that loaded but wrote no diary either predates the logbook (republish it) or died before its first script ran — see the notable lines.')
        return '\n'.join(lines)
    for s in sessions:
        head = '%s — build %s — %s to %s (headset clock)' % (s['app'], s['build'], s['first'][:14], s['last'][6:14])
        lines.append(head)
        bits = []
        bits.append('ran %ss' % s['secondsRunning'] if s['secondsRunning'] is not None else 'duration unknown')
        bits.append('entered VR' if s['enteredVR'] else 'never entered VR')
        if s['fps']: bits.append('%s fps' % s['fps'])
        if s['controllers']: bits.append('controllers: ' + ', '.join(map(str, s['controllers'])))
        if s['presses'] is not None: bits.append('%s presses, %s turns' % (s['presses'], s['turns']))
        if s.get('dof') == 3:
            lk = s.get('lock')
            if lk and lk[2]:
                # kit >= 0.15: the view is allowed `give` (default 0.3) of the real movement, so
                # held ≈ 0.3 × moved is correct; held > moved means the lock is not holding.
                bits.append('3DoF app: head lock active for %d frames — the player moved up to %.2f m, the view gave %.3f m%s'
                            % (lk[2], lk[0], lk[1], '' if lk[1] <= lk[0] * 0.5 + 0.02 else ' (MORE than the give allows: the lock is not holding)'))
            elif s['enteredVR']:
                bits.append('3DoF app but the head lock never ran (is renderer.xr.getCamera wrapped? dof: 3 on <a-scene xr-kit>?)')
            else:
                bits.append('3DoF app')
        last_k = s['beacons'][-1].get('k') if s['beacons'] else None
        if s['ended']: bits.append('left cleanly')
        elif last_k == 'vr' and not s['beacons'][-1].get('vr'): bits.append('left VR at %ss and went home (Wolvic sends no final beacon when the page is closed from the home button)' % s['beacons'][-1].get('t'))
        else: bits.append('no end beacon (still open when the log was taken, or closed abruptly)')
        lines.append('  ' + '; '.join(bits))
        if s['errors']:
            lines.append('  %d error(s), first code %s:' % (s['errors'], s['firstCode']))
            for e in s['errorList'][:5]:
                lines.append('    [%6.1fs] %s  (code %s)' % (e['t'], e['text'][:160], e.get('code')))
        for t in s['flags']:
            lines.append('  flag at %.1fs — the ten seconds before it:' % t)
            for e in before(s['entries'], t):
                lines.append('    [%6.1fs] %-5s %s' % (e['t'], e['kind'], e['text'][:140]))
        if not s['errors'] and not s['flags']:
            lines.append('  no errors, no flags')
        if s['dropped']: lines.append('  (%d diary entries were dropped between beacons — a very chatty app)' % s['dropped'])
        if s['incompleteBeacons']: lines.append('  (%d beacon(s) arrived incomplete)' % s['incompleteBeacons'])
        lines.append('')
    if notable:
        lines.append('Headset-level lines worth a glance (last 12):')
        for n in notable[-12:]:
            lines.append('  %s %s %s: %s' % (n['ts'], n['level'], n['tag'], n['text'][:140]))
    return '\n'.join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', required=True)
    ap.add_argument('--app', help='app name ("Bubble Pop"), slug (bubble-pop) or folder name — any of them; only report this app')
    ap.add_argument('--since', help='ignore lines before this logcat time, e.g. "09-07 16:00"')
    ap.add_argument('--json', help='write the full structured result here')
    ap.add_argument('--summary', action='store_true', help='print a plain-words summary')
    ap.add_argument('--last', type=int, default=0, help='only the N most recent sessions')
    a = ap.parse_args()
    sessions, loads, notable = parse(a.log, a.since)
    if a.app:
        sessions = [s for s in sessions if same_app(s, a.app)]
    if a.last:
        sessions = sessions[-a.last:]
    result = {'sessions': sessions, 'pageLoads': loads[-20:], 'notable': notable[-40:]}
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=1)
    if a.summary or not a.json:
        print(summarise(sessions, loads, notable, None))
    else:
        print(json.dumps({'sessions': len(sessions), 'pageLoads': len(loads), 'notable': len(notable), 'json': a.json}))

if __name__ == '__main__':
    main()
