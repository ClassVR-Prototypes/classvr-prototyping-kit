#!/usr/bin/env python3
"""Publish the current branch: open a pull request to main and merge it.

    python3 publish_pr.py --title "Bubble Pop: replace the countdown with a clock" \
                          --body-file /tmp/pr-body.md [--repo Owner/repo] [--branch claude/x] [--base main]

Works inside Claude Code on the web (and anywhere GH_TOKEN or `gh auth token`
gives a usable token). The proxy in cloud sessions substitutes real
credentials for the `proxy-injected` placeholder, so the token value itself
does not matter there. Repo and branch default to the git remote and the
current branch.

Behaviour:
  - if an OPEN pull request from this branch already exists, it is reused
  - creates the PR (POST /pulls), then merges it (PUT /pulls/N/merge) with
    merge_method=merge so the individual commits stay visible on main
  - prints JSON: {ok, pr, number, merged, created, steps:[{step,status}]}

Exit codes: 0 merged; 2 refused (403 from the proxy or GitHub — use the
fallback in SKILL.md); 3 the branch has nothing new / cannot be merged
(conflict, checks) — the message says which; 1 anything else.
"""
import argparse, json, os, re, subprocess, sys, urllib.request, urllib.error

API = 'https://api.github.com'


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def token():
    for k in ('GH_TOKEN', 'GITHUB_TOKEN'):
        if os.environ.get(k):
            return os.environ[k]
    t = sh('gh', 'auth', 'token')
    return t or 'proxy-injected'


def repo_from_remote():
    url = sh('git', 'remote', 'get-url', 'origin')
    m = re.search(r'github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?/?$', url)
    return '%s/%s' % (m.group(1), m.group(2)) if m else None


def call(method, path, tok, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        'Authorization': 'Bearer ' + tok,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'User-Agent': 'classvr-prototyping-kit',
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode() or 'null'
            return r.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors='replace')
        try: parsed = json.loads(raw)
        except Exception: parsed = {'message': raw[:300]}
        return e.code, parsed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--title', required=True)
    ap.add_argument('--body', default='')
    ap.add_argument('--body-file')
    ap.add_argument('--repo', help='Owner/repo (default: from origin remote)')
    ap.add_argument('--branch', help='head branch (default: current)')
    ap.add_argument('--base', default='main')
    a = ap.parse_args()

    repo = a.repo or repo_from_remote()
    branch = a.branch or sh('git', 'rev-parse', '--abbrev-ref', 'HEAD')
    body = open(a.body_file, encoding='utf-8').read() if a.body_file else a.body
    if not repo or not branch or branch == 'HEAD':
        print(json.dumps({'ok': False, 'error': 'could not determine repo/branch; pass --repo and --branch'})); return 1
    if branch == a.base:
        print(json.dumps({'ok': True, 'merged': True, 'note': 'already on %s — a push is a publish' % a.base})); return 0

    tok = token(); owner = repo.split('/')[0]; steps = []

    # 1. reuse an open PR from this branch if there is one
    st, prs = call('GET', '/repos/%s/pulls?state=open&head=%s:%s' % (repo, owner, branch), tok)
    steps.append({'step': 'list', 'status': st})
    if st == 403:
        print(json.dumps({'ok': False, 'refused': True, 'steps': steps, 'error': prs.get('message')})); return 2
    pr = prs[0] if isinstance(prs, list) and prs else None
    created = False

    # 2. create if needed
    if not pr:
        st, pr = call('POST', '/repos/%s/pulls' % repo, tok,
                      {'title': a.title, 'head': branch, 'base': a.base, 'body': body})
        steps.append({'step': 'create', 'status': st})
        if st == 403:
            print(json.dumps({'ok': False, 'refused': True, 'steps': steps, 'error': pr.get('message')})); return 2
        if st == 422:
            msg = ' '.join(e.get('message', '') for e in pr.get('errors', [])) or pr.get('message', '')
            print(json.dumps({'ok': False, 'steps': steps, 'error': 'GitHub refused to open the PR: ' + msg,
                              'hint': 'usually "No commits between main and <branch>" — nothing new to publish, or the branch was not pushed'})); return 3
        if st >= 300:
            print(json.dumps({'ok': False, 'steps': steps, 'error': pr.get('message', str(st))})); return 1
        created = True

    number = pr['number']; url = pr['html_url']

    # 3. merge
    st, res = call('PUT', '/repos/%s/pulls/%d/merge' % (repo, number), tok,
                   {'merge_method': 'merge', 'commit_title': 'Publish: ' + a.title})
    steps.append({'step': 'merge', 'status': st})
    if st == 403:
        print(json.dumps({'ok': False, 'refused': True, 'pr': url, 'number': number, 'created': created,
                          'steps': steps, 'error': res.get('message')})); return 2
    if st in (405, 409):
        print(json.dumps({'ok': False, 'pr': url, 'number': number, 'created': created, 'steps': steps,
                          'error': 'GitHub would not merge: ' + res.get('message', ''),
                          'hint': 'bring the branch up to date with %s (merge %s into it, resolve, push) and run again' % (a.base, a.base)})); return 3
    if st >= 300:
        print(json.dumps({'ok': False, 'pr': url, 'number': number, 'steps': steps, 'error': res.get('message', str(st))})); return 1

    print(json.dumps({'ok': True, 'pr': url, 'number': number, 'created': created,
                      'merged': bool(res.get('merged')), 'sha': res.get('sha'), 'steps': steps}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
