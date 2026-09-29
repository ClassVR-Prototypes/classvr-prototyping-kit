---
name: share-xr-app
description: >
  This skill should be used when the user asks to "share my XR app", "give me a link
  to the app", "put it on GitHub Pages", "publish the web page", "refresh the
  Vercel page", "refresh the link", "make the link show the latest version", or
  invokes /share-xr-app. It builds the app, verifies it, and puts it on a
  permanent link: a GitHub Pages URL when the app lives in a GitHub repository
  (the normal case in Claude Code), otherwise Vercel (/publish-to-vercel). It is
  also run automatically at the end of /new-xr-app and after every edit to an
  app, so the link is never behind the folder, and it always ends by putting the
  link in the chat.
metadata:
  version: "0.8.0"
---

# Share XR app

Put the app on a link. The first run creates the link and records it in
`xr-project.json`; every later run — from any session, any day — updates the
same link. People who have it just reload to see the latest build; the build
number on the panel tells them which one they are looking at.

There are two kinds of link, and **where the app lives decides which**:

| The app folder is… | Route | Link | Enter VR on a headset? |
|---|---|---|---|
| inside a git repository with a GitHub remote | **A — GitHub Pages** | `https://<owner>.github.io/<repo>/<slug>/` | **Yes** — a plain HTTPS page; the page shows its own QR code for the headset to scan |
| a plain folder (Cowork, a local session, no repo), **or** anywhere the user has chosen Vercel, **or** the manifest already has `vercel.url` | **C — Vercel** (`/publish-to-vercel`) | `https://<project>.vercel.app` | **Yes** — a plain HTTPS page, published with the person's own Vercel token (`/connect-vercel`) or the Vercel connector; the page shows its own QR code for the headset to scan |

Route C is the default: every app that is not in a GitHub repository goes to
Vercel, and `/publish-to-vercel` carries the whole flow (build, verify, deploy,
write-back, the link). The first time, it runs `/connect-vercel` if no Vercel
connection is stored yet. An app published on Vercel stays there, even if its
folder later ends up in a repository. There is no other route: the Claude
Artifact link and the ClassCloud upload were removed in kit 0.35.

## Outcome

- The app on a URL that never changes, showing the latest verified build
- `xr-project.json` carrying `pages.*` (route A) or `vercel.*` (route C)
- **The link in the chat**, as the last line of the turn, as a plain clickable
  URL
- `index.html` written back if the build number bumped

## Steps

Do these in order. Nothing here asks the user a question.

### 1. Locate the project and pick the route

The folder with `index.html` and `xr-project.json`. Then, from inside it:

    git rev-parse --show-toplevel        # repo root, or an error if not a repo
    git remote get-url origin            # https://github.com/<owner>/<repo>(.git)

**First**, if `xr-project.json` has `vercel.url`, or the user asked for Vercel
in this turn → **route C**: stop here and run `/publish-to-vercel` (it does
its own build, verify and write-back). Otherwise: both succeed and the remote
is on `github.com` → **route A**. Anything else (not a repo, no remote, a
non-GitHub host, or `git` unavailable) → **route C** as well: run
`/publish-to-vercel`.

### 2. Build

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-to-vercel/scripts/build.py --project "<project>"

Same script as the Vercel route: inlines every local script into
`dist/<slug>-build<N>.html`, bumps the build number only if the source changed.
Note `build`, `bumped` and `output`. On route A the built file is only used
for verification — Pages serves the folder itself — but the bump is what stamps
the new build number into the manifest and the panel.

### 3. Verify — do not skip

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/preview-xr-app/scripts/preview.py \
        --file "<output from step 2>" --out "<project>/.preview"

Exit `0`: continue. Exit `1`: **stop**, say what failed in the user's terms, fix
it, restart from step 2. A broken build must never replace a working link. Exit
`3`: continue, but say the build was not verified. Do **not** send
`preview.png` in this flow — the link is what the turn ends on.

Then follow **Route A** below, and finish with step 6.

## Route A — GitHub Pages

### A4. Make sure the repository can publish

Look for `.github/workflows/pages.yml` at the repo root. If it is missing, the
repo has never been set up for Pages; do it now, once, from the kit's templates:

- copy `${CLAUDE_PLUGIN_ROOT}/skills/share-xr-app/assets/pages/pages.yml`
  to `.github/workflows/pages.yml`
- copy `${CLAUDE_PLUGIN_ROOT}/skills/share-xr-app/assets/pages/auto-publish.yml`
  to `.github/workflows/auto-publish.yml` (safety net: publishes a `[publish]`
  commit if the API route in A5 is ever refused)
- copy `${CLAUDE_PLUGIN_ROOT}/skills/share-xr-app/assets/pages/build_pages.py`
  to `.github/scripts/build_pages.py`
- append the lines in `${CLAUDE_PLUGIN_ROOT}/skills/share-xr-app/assets/pages/gitignore-lines`
  to the repo's `.gitignore` (create it if needed)

If `pages.yml` *is* there, check the site builder is current: the kit's
`build_pages.py` starts with a line `# kit-pages-builder vN`. If the repo's
`.github/scripts/build_pages.py` has a lower `N`, or no such line at all
(v1), copy the kit's file over it and commit it on its own: "Update the site
builder: QR code on every page". v1 publishes the apps without the QR code
(below); v2 tried to `pip install` its encoder and silently published
without it on GitHub's runners; v3 has no click-to-enlarge. If a repo's `pages.yml` gained a
`setup-python` / "QR code support" step to work around v2, it is harmless
and can be left alone or removed.

and tell the user the **one thing that cannot be done from here**: on
github.com, *Settings → Pages → Build and deployment → Source: GitHub Actions*,
a single dropdown, once per repository. (The Pages settings API is blocked from
Claude sessions; a workflow using `actions/configure-pages` with
`enablement: true` may also do it on its first run if the repo allows, so it is
worth trying before asking.) Until that is set the deploy job fails with "Pages
site not configured" — if the user reports the link is 404 after a few minutes,
this is the first thing to check.

The site builder serves every folder that has an `xr-project.json` at
`/<slug>/` (slug from the manifest, so "Planet Walk" is `/planet-walk/`), plus
an index page listing them. Apps are ordinary folders at the repo root; nothing
else about the repo layout matters.

### A5. Commit, push, publish

Stage only what the site needs: the app folder's `index.html`,
`xr-project.json`, `README.md`, `CHANGELOG.md` (GitHub shows both on the
repository page, and a copy made from the Pages address reads them from beside
the page) and any local libraries it references (`aframe.min.js`,
`cannon.iife.js`). Never commit `dist/` or `.preview/`.

**Commit the way a careful developer would.** One commit per logical
change, in the user's words, present tense, specific. The history is
something the user may read later to learn how work is organised, so make it
read well. A request that touches more than one concern gets more than one
commit, in this order:

1. the visible thing ("Add a round clock face where the countdown sign was")
2. its behaviour ("Sweep the clock hand once round over the 30-second round")
3. its self-check ("Add a self-check: the hand starts at the top and finishes there")
4. the build bump ("Bump Bubble Pop to build 4"), which is also where the
   manifest's `pages.*` fields get recorded

Only a one-line tweak ("make the sky darker") is a single commit. Never one
giant "update" commit; never commit half a change.

**Publishing is part of the job — not something to ask about.** The owner of
a kit repository has pre-authorised Claude to open and merge its own pull
requests (it says so in the repo's `CLAUDE.md`/`AGENTS.md`, and the template
ships that way). Every published build has passed the preview check. So do
not offer ("say the word and I'll merge it") and do not ask ("shall I?"):
a turn that ends with saved-but-unpublished work, when the user did not ask
to hold, is a failed turn — the user may never know what "merge" means, and
their app would silently never reach the link.

**How to publish from a `claude/…` branch** (Claude Code on the web always
works on one; on `main` itself a push is a publish). Run the kit's script —
it opens the pull request (or reuses an open one from this branch) and
merges it, keeping every commit visible on `main`:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/share-xr-app/scripts/publish_pr.py \
        --title "<what changed, in the user's words>" --body-file /tmp/pr-body.md

Write `/tmp/pr-body.md` first, the way a good colleague would: what changed
and why, how to try it (the Pages URL), the build number. Exit `0` → merged
(the JSON has the PR link). Exit `3` → GitHub would not merge: read
`error`/`hint` (nothing new to publish, or the branch is behind `main` —
merge `main` into the branch, resolve, push, run again). Exit `2` → the API
refused (403). Only then:

- if `.github/workflows/auto-publish.yml` exists in the repo: make one small
  commit whose message ends with `[publish]` and push — the workflow merges
  and deploys. Never use the marker when the script succeeded.
- otherwise, and only otherwise: tell the user "press **Create PR**, then
  **Merge** on GitHub — two clicks — and the link goes live a minute or two
  later", and add `auto-publish.yml` (A4) so it never comes up again.

If you use Claude Code's built-in GitHub merge tool instead of the script and
it answers `409 Head branch was modified`, that is its stale-tip check after a
push: run it again (or use the script, which doesn't have that check).

The API details, for reference: `POST /repos/<o>/<r>/pulls` then
`PUT /repos/<o>/<r>/pulls/<n>/merge`, with `Authorization: Bearer $GH_TOKEN`
and `Content-Type: application/json` (the proxy answers 415 without it).
Tested 15 Sep 2026: 201 and 200.

**When to publish.** By default every request is one finished piece of work:
build, verify, commit, then publish, and say "live in a couple of minutes".
If the user says they want several changes before anything goes live ("don't
publish yet", "I'll tell you when"), save only: push the commits and make the
**latest commit message end with `[hold]`** — that is how the hold is
recorded, and it survives into later sessions. Say the work is saved but not
live. When they say "publish" / "put it live" / "update the link", make the
publishing commit (bump the build if the source changed) and run
`publish_pr.py`. Never publish a build that failed the preview.

**The kit checks.** The kit ships a Stop hook: when a turn is about to end in
a kit repository with commits that `main` doesn't have (or uncommitted app
changes), and the latest commit isn't marked `[hold]`, the turn is not allowed
to end — the hook says so and names the script to run. Don't argue with it or
explain it to the user; publish, then finish. If publishing is impossible
(script exit 2 with no fallback, or exit 3 you cannot fix), say plainly what
is stopping it — the hook lets the turn end after two reminders.

Then the URL. Work it out from the remote:

    https://github.com/<Owner>/<repo>.git  →  https://<owner-lowercase>.github.io/<repo>/<slug>/

(If the repo is itself named `<owner>.github.io`, drop the `/<repo>` part.)

Record it before the publishing commit so the repo's copy matches:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-to-vercel/scripts/manifest.py --project "<project>" \
        --set pages.url="<url>" --set pages.repo="<Owner>/<repo>" --set pages.build=<N> --touch-pages

**Timing.** Deploy takes 1–2 minutes after the merge; say "a couple of
minutes". If the user reports it never appeared, the repo's Actions tab shows
why — most often the one-time Pages setting (A4) or a merge conflict, which
means: bring the branch up to date with `main` and publish again.

**Caching.** Pages sits behind a CDN with a 10-minute cache. Someone who loaded
the page recently may still see the old build after a reload; the build number
on the panel is how to tell. If that happens, give them the same URL with
`?b=<N>` on the end, which fetches fresh.

**Headsets — the QR code is automatic.** A Pages URL is a top-level HTTPS
page, so **Enter VR works** and a plain QR code of the URL opens it straight
in the headset browser (tested on ClassVR, Sept 2026). The site builder
(`build_pages.py`, v4 or later) works out each app's address from the
repository name at deploy time, draws the QR itself — the encoder is built
into the script, because the runner's python has no pip and nothing can be
installed there — and adds a card to the **top-right corner of
the served page** — the QR code, "Open on a headset", and the address — plus
the same QR beside each app on the site's index page. **Clicking the card
fills the screen with the code** so a headset can scan it from across a
desk; clicking again, the cross, or Esc puts it back in the corner. So the
QR exists from
the first deploy, is right before anyone has looked at the page, and never
changes while the URL doesn't. It is only in the copy on Pages, added at the
very end of the file: the app folder, the source's line numbers (which the
error codes refer to) and the build number are untouched, and entering VR
hides it like every other HTML overlay. Nothing to run, nothing to record.

The way to use it: open the link on any screen, click the QR to enlarge it,
point the headset's scanner at it. Say that once, on the first share.

The address is known before the page is live, so nothing waits on the
deploy. If someone wants the code *printed* or on a slide, `make_qr.py` still
makes a PNG of the same URL:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-to-vercel/scripts/make_qr.py \
        --url "<url>" --title "<App Name>" --subtitle "Scan to open on the headset" \
        --out "<project>/qr-pages.png"

and render it last (it can be committed to the app folder; the URL never
changes, so neither does the QR). Do this only when asked — the page already
carries the code.

**What Pages does not do.** There is no play history here: sessions are not
collected, so `/check-headset` has nothing to read for a Pages app — the
error code on the panel is the only trace. (Vercel keeps a history; that is
one reason it is the default.) Everything in the repo is public, so say so
once on the first share: fine for prototypes, not for anything private.

## 6. Write back and report

Route A: the repo *is* the folder; nothing to write back beyond the commit.
(Route C does its own write-back in `/publish-to-vercel`.)

Then one or two sentences, and **the link is the last line**:

- Route A, first share: the app name, "build N", where it will appear and
  when ("live in a couple of minutes"; or "once you press Create PR and Merge"
  only when both hands-free routes in A5 failed), that the
  page is public, and — once — that the same URL works on a headset: "the
  page shows a QR code in its top-right corner — click it to make it big,
  then point the headset's scanner at it". Then the URL on its own line.
- Route A, update: "build N is on its way to the link — reload in a couple of
  minutes (the panel shows the build number)". Then the URL on its own line.
- Route A, saved but not published (user asked to hold): "saved, not live yet
  — say 'publish' when you're ready". No URL needed.

Never explain git, the workflow or the manifest unless asked. The words "commit", "push", "branch", "PR" and "repo"
don't need to appear at all; "saved", "published" and "the link" do the job.
Phrases that must not appear in a normal turn: "saved on your branch", "to
make it live, press…", "say the word and I'll…", "shall I merge". If
publishing succeeded there is nothing to press; if it failed, say what
happened in plain words and what you did about it. If the user *asks* how
the history is organised, or wants to learn, then explain gladly — the
commits and pull requests were written to be read.

## When this runs on its own

- **End of `/new-xr-app`**: every new app is created with a link, and the link
  is what ends the create turn (no screenshot).
- **After any edit to `index.html`** (see `xr-app-rules`): preview check, then
  this, so the link never lags the folder. If the source didn't change (build
  not bumped) skip the publish — nothing to update — and say so only if the user
  expected a change.

## What the links do and don't do

**Pages link (route A)**

- Public, top-level, permanent while the repo exists. Enter VR works; the
  page carries a QR of its own URL (top-right corner, and on the site's index
  page) that opens it on a ClassVR headset. Renaming the repo or the app's
  slug changes the URL — and so the QR — so don't.
- Version history is the repo's history. "Go back to build 3" is a git revert
  of the app folder, which Claude can do when asked.
- No play history; `/check-headset` works only for Vercel apps.

**Vercel link (route C)** — see `/publish-to-vercel` ("Known limits").
