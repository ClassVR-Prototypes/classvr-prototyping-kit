#!/usr/bin/env python3
"""Read or update xr-project.json without hand-editing JSON.

    python3 manifest.py --project /path/to/Project                      # print it
    python3 manifest.py --project /path/to/Project --set classcloud.activityId=1189827 \
                                                    --set classcloud.lastUrl="https://..."

Values are parsed as JSON when possible (numbers, true/false/null), else kept
as strings. Dotted keys address nested fields. Prints the resulting manifest.
"""
import argparse, json, os, sys, datetime

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    ap.add_argument('--set', action='append', default=[], metavar='KEY=VALUE')
    ap.add_argument('--touch-published', action='store_true', help='set classcloud.lastPublished to now')
    ap.add_argument('--touch-shared', action='store_true', help='set artifact.lastShared to now')
    ap.add_argument('--touch-pages', action='store_true', help='set pages.lastShared to now')
    a = ap.parse_args()
    path = os.path.join(os.path.abspath(a.project), 'xr-project.json')
    if not os.path.exists(path):
        print(json.dumps({'ok': False, 'error': 'no xr-project.json in ' + a.project})); return 2
    man = json.load(open(path, encoding='utf-8'))

    for kv in a.set:
        key, _, raw = kv.partition('=')
        try: val = json.loads(raw)
        except Exception: val = raw
        node = man
        parts = key.split('.')
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = val
    if a.touch_published:
        man.setdefault('classcloud', {})['lastPublished'] = \
            datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'

    if a.touch_shared:
        man.setdefault('artifact', {})['lastShared'] = \
            datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'

    if a.touch_pages:
        man.setdefault('pages', {})['lastShared'] = \
            datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'

    if a.set or a.touch_published or a.touch_shared or a.touch_pages:
        json.dump(man, open(path, 'w', encoding='utf-8'), indent=2); open(path, 'a').write('\n')
    print(json.dumps(man, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())
