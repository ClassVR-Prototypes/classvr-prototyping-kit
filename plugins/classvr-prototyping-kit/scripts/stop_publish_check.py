#!/usr/bin/env python3
"""Stop hook: don't let a turn end with unpublished work in a kit repo.

Claude Code runs this when Claude is about to finish replying. It reads the
hook event from stdin and answers with a JSON decision:

  - allow  — nothing to publish (not a git repo, not a kit repo, on main,
             already merged, or the latest commit is marked [hold])
  - block  — the branch has commits main doesn't have; the reason tells
             Claude to push and run publish_pr.py, then finish

Loop guard: the same unpublished HEAD is blocked at most twice per session;
after that the stop is allowed with a note so Claude explains plainly rather
than spinning. Never blocks on errors — if anything here fails, the turn ends
normally. No dependencies beyond git and Python 3.
"""
import json, os, subprocess, sys, hashlib

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # plugin root
PUBLISH = os.path.join(KIT, 'skills', 'share-xr-app', 'scripts', 'publish_pr.py')
MAX_NAGS = 2


def git(cwd, *args, timeout=30):
    try:
        r = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except Exception:
        return 1, ''


def allow(note=None):
    out = {'hookSpecificOutput': {'hookEventName': 'Stop', 'decision': 'allow'}}
    if note:
        out['systemMessage'] = note
    print(json.dumps(out)); return 0


def block(reason):
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'Stop', 'decision': 'block', 'reason': reason}})); return 0


def is_kit_repo(root):
    for here, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('.git', 'kit', 'node_modules', '_site', '.github', '.claude')]
        if 'xr-project.json' in files and here != root:
            return True
    return False


def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        ev = {}
    cwd = ev.get('cwd') or os.getcwd()

    rc, root = git(cwd, 'rev-parse', '--show-toplevel')
    if rc != 0 or not root:
        return allow()
    if not is_kit_repo(root):
        return allow()

    rc, branch = git(root, 'rev-parse', '--abbrev-ref', 'HEAD')
    if rc != 0 or branch in ('HEAD', 'main', 'master'):
        return allow()
    rc, remote = git(root, 'config', '--get', 'remote.origin.url')
    if rc != 0 or 'github.com' not in remote:
        return allow()

    # Uncommitted app changes count as unfinished work too.
    rc, dirty = git(root, 'status', '--porcelain', '--untracked-files=no')
    dirty_apps = [l for l in dirty.splitlines() if 'index.html' in l or 'xr-project.json' in l]

    # Fresh view of main and of this branch on GitHub (quick; failures are tolerated).
    git(root, 'fetch', '--quiet', 'origin', 'main', branch, timeout=40)

    rc, ahead = git(root, 'rev-list', '--count', 'origin/main..HEAD')
    ahead = int(ahead) if rc == 0 and ahead.isdigit() else 0
    rc, unpushed = git(root, 'rev-list', '--count', 'origin/%s..HEAD' % branch)
    unpushed = int(unpushed) if rc == 0 and unpushed.isdigit() else ahead   # no remote branch yet → all unpushed

    if ahead == 0 and not dirty_apps:
        return allow()

    rc, last_msg = git(root, 'log', '-1', '--format=%s%n%b')
    if '[hold]' in last_msg.lower():
        return allow('Publishing is on hold at the user\'s request ([hold] on the latest commit). Say the work is saved but not live yet.')

    # Loop guard, keyed on this session and the current HEAD.
    rc, head = git(root, 'rev-parse', 'HEAD')
    key = hashlib.sha1((ev.get('session_id', '') + head + dirty).encode()).hexdigest()[:12]
    state_dir = ev.get('scratchpad_dir') or os.path.join(root, '.git')
    state = os.path.join(state_dir, 'kit-stop-nag-' + key)
    try:
        n = int(open(state).read().strip()) if os.path.exists(state) else 0
        os.makedirs(state_dir, exist_ok=True)
        open(state, 'w').write(str(n + 1))
    except Exception:
        n = 0
    if n >= MAX_NAGS:
        return allow('The work is still unpublished after two reminders. Tell the user plainly what is stopping it '
                     'and what happens next; do not pretend it is live.')

    parts = []
    if dirty_apps:
        parts.append('there are uncommitted app changes (%d file(s))' % len(dirty_apps))
    if unpushed:
        parts.append('%d commit(s) are not pushed' % unpushed)
    if ahead:
        parts.append('%d commit(s) on this branch are not on main' % ahead)
    reason = (
        "Kit publish check: the user's work is not live yet — " + '; '.join(parts) + ". "
        "Publishing is pre-authorised in this repository and is part of the job, so finish it now: "
        "commit anything outstanding (one commit per logical change), push, then run\n\n"
        "    python3 %s --title \"<what changed, in the user's words>\" --body-file /tmp/pr-body.md\n\n"
        "(write /tmp/pr-body.md first: what changed, how to try it, the build number). "
        "Exit 0 = merged: end with the app's Pages URL on its own line and 'live in a couple of minutes'. "
        "Exit 2 = refused: use the [publish] commit marker if .github/workflows/auto-publish.yml exists, "
        "otherwise tell the user to press Create PR then Merge. Exit 3 = read its hint and fix. "
        "If the user explicitly asked NOT to publish yet, add [hold] to the latest commit message instead "
        "(git commit --amend) and say the work is saved but not live." % PUBLISH
    )
    return block(reason)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        # Never let a hook bug trap the user in a session.
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'Stop', 'decision': 'allow'}}))
        sys.exit(0)
