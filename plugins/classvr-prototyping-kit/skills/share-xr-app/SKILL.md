---
name: share-xr-app
description: >
  This skill should be used when the user asks to "share my XR app", "give me a link
  to the app", "put it on GitHub Pages", "publish the web page", "put it in an
  artifact", "update the artifact", "refresh the link", "make the link show the
  latest version", or invokes /share-xr-app. It builds the app, verifies it, and
  puts it on a permanent link: a GitHub Pages URL when the app lives in a GitHub
  repository (the normal case in Claude Code), otherwise a Claude Artifact. It is
  also run automatically at the end of /new-xr-app and after every edit to an
  app, so the link is never behind the folder, and it always ends by putting the
  link in the chat.
metadata:
  version: "0.3.0"
---

# Share XR app

Put the app on a link. The first run creates the link and records it in
`xr-project.json`; every later run — from any session, any day — updates the
same link. People who have it just reload to see the latest build; the build
number on the panel tells them which one they are looking at.

There are two kinds of link, and **where the app lives decides which**:

| The app folder is… | Route | Link | Enter VR on a headset? |
|---|---|---|---|
| inside a git repository with a GitHub remote | **A — GitHub Pages** | `https://<owner>.github.io/<repo>/<slug>/` | **Yes** — a plain HTTPS page; scan a QR of it on the headset |
| a plain folder (Cowork, a local session, no repo) | **B — Claude Artifact** | `https://claude.ai/…/artifact/…` | No — the viewer's frame blocks WebXR |

Route A is preferred whenever it is available. The headset route through
ClassCloud (`/publish-xr-app`) still exists and shares the same build numbers;
with a Pages link it becomes optional — useful when someone wants the app in a
ClassCloud playlist, not needed just to get it onto a headset.

## Outcome

- The app on a URL that never changes, showing the latest verified build
- `xr-project.json` carrying `pages.*` (route A) or `artifact.*` (route B)
- **The link in the chat**, as the last line of the turn, as a plain clickable
  URL — on route A always; on route B the artifact card is the link, so don't
  also paste the URL unless asked
- `index.html` written back if the build number bumped

## Steps

Do these in order. Nothing here asks the user a question except the ownership
case in route B.

### 1. Locate the project and pick the route

The folder with `index.html` and `xr-project.json`. Then, from inside it:

    git rev-parse --show-toplevel        # repo root, or an error if not a repo
    git remote get-url origin            # https://github.com/<owner>/<repo>(.git)

Both succeed and the remote is on `github.com` → **route A**. Anything else
(not a repo, no remote, a non-GitHub host, or `git` unavailable) → **route B**.
In a Cowork session with a connected folder, stage `index.html`, every local
`<script src="./…">` it references, and `xr-project.json` into the workspace
with the same layout first; scripts take that staged folder as `--project`.

### 2. Build

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-xr-app/scripts/build.py --project "<project>"

Same script as the headset publish: inlines every local script into
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

Then follow **Route A** or **Route B** below, and finish with step 6.

## Route A — GitHub Pages

### A4. Make sure the repository can publish

Look for `.github/workflows/pages.yml` at the repo root. If it is missing, the
repo has never been set up for Pages; do it now, once, from the kit's templates:

- copy `${CLAUDE_PLUGIN_ROOT}/skills/share-xr-app/assets/pages/pages.yml`
  to `.github/workflows/pages.yml`
- copy `${CLAUDE_PLUGIN_ROOT}/skills/share-xr-app/assets/pages/auto-publish.yml`
  to `.github/workflows/auto-publish.yml` (publishes a `[publish]` commit from
  a `claude/…` branch without a PR — see A5)
- copy `${CLAUDE_PLUGIN_ROOT}/skills/share-xr-app/assets/pages/build_pages.py`
  to `.github/scripts/build_pages.py`
- append the lines in `${CLAUDE_PLUGIN_ROOT}/skills/share-xr-app/assets/pages/gitignore-lines`
  to the repo's `.gitignore` (create it if needed)

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
`xr-project.json` and any local libraries it references (`aframe.min.js`,
`cannon.iife.js`). Never commit `dist/` or `.preview/`.

**Commit the way a careful developer would.** One commit per logical change,
in the user's words, present tense, specific: "Add a wooden table left of the
start", "Add a self-check for the table", "Bump Planet Walk to build 4". If a
request produced several distinct changes, make several commits; the history
is something the user may read later to learn how work is organised, so make
it read well. Never one giant "update" commit; never commit half a change.

**Publishing is a separate decision from saving.** When
`.github/workflows/auto-publish.yml` exists in the repo, a push publishes
nothing on its own; only a commit whose message **ends with `[publish]`**
does — the workflow merges the branch into `main` (keeping every commit) and
starts the deploy. So:

- By default, each request is one piece of finished work: make the commits,
  and put `[publish]` at the end of the **last** one ("Bump Planet Walk to
  build 4 [publish]"). Then push.
- If the user says they want to make several changes before anything goes
  live ("don't publish yet", "I'll tell you when"), leave the marker off and
  say the work is saved but not live. When they say "publish" / "put it live"
  / "update the link", make a small commit with the marker (bump the build if
  the source changed) and push.
- Never put `[publish]` on a commit whose build failed the preview.

Without `auto-publish.yml`, the branch rules below apply instead.

Work out the URL from the remote:

    https://github.com/<Owner>/<repo>.git  →  https://<owner-lowercase>.github.io/<repo>/<slug>/

(If the repo is itself named `<owner>.github.io`, drop the `/<repo>` part.)

Record it:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-xr-app/scripts/manifest.py --project "<project>" \
        --set pages.url="<url>" --set pages.repo="<Owner>/<repo>" --set pages.build=<N> --touch-pages

If the manifest changed after the commit (it did: `pages.*`), amend or add a
second small commit so the repo's copy matches.

**Which branch matters.** The Pages workflow publishes `main`.

- On `main`: the site rebuilds on its own; the new build is live in about
  1–2 minutes.
- On a `claude/…` branch **with `auto-publish.yml`** in the repo: a `[publish]`
  commit is live 2–3 minutes after the push (merge, then deploy). Say "live in
  a couple of minutes". If the user later reports it never appeared, the
  Actions tab shows why — usually a merge conflict; bring the branch up to
  date with `main` and publish again.
- On a `claude/…` branch **without** it: the change is pushed but **not live
  until it is merged**. Try to do that yourself first, through the GitHub API
  the session already has credentials for (`GH_TOKEN` reads `proxy-injected`
  and the proxy signs the request):

      curl -s -X POST -H "Authorization: Bearer $GH_TOKEN" -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/<Owner>/<repo>/pulls \
        -d '{"title":"<summary>","head":"<branch>","base":"main","body":"Published by the ClassVR Prototyping Kit."}'
      curl -s -X PUT  -H "Authorization: Bearer $GH_TOKEN" -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/<Owner>/<repo>/pulls/<number>/merge -d '{"merge_method":"merge"}'

  (`gh pr create` / `gh pr merge` if `gh` is installed.) If either returns 403
  from the proxy, stop trying and say plainly: "Press **Create PR**, then
  **Merge** on GitHub, and the link goes live a minute or two later" — two
  clicks, no other steps. Suggest adding `auto-publish.yml` (step A4) so it
  never comes up again.

**Caching.** Pages sits behind a CDN with a 10-minute cache. Someone who loaded
the page recently may still see the old build after a reload; the build number
on the panel is how to tell. If that happens, give them the same URL with
`?b=<N>` on the end, which fetches fresh.

**Headsets.** A Pages URL is a top-level HTTPS page, so **Enter VR works** and
a plain QR code of the URL opens it straight in the headset browser (tested on
ClassVR, Sept 2026). If the user wants a QR for the Pages link:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-xr-app/scripts/make_qr.py \
        --url "<url>" --title "<App Name>" --subtitle "Scan to open on the headset" \
        --out "<project>/qr-pages.png"

and render it last (it can be committed to the app folder; the URL never
changes, so neither does the QR).

**What Pages does not do.** The artifact mailbox (route B) does not exist here:
browser testers' reports are not collected automatically. Headset play is still
covered by `/check-headset`, which reads the headset's own log through
ClassCloud. Everything in the repo is public, so say so once on the first
share: fine for prototypes, not for anything private.

## Route B — Claude Artifact

### B4. Convert to artifact form

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/share-xr-app/scripts/artifact.py \
        --build "<output from step 2>"

Writes `dist/<slug>-artifact.html` (and fails with a plain reason if the page
is over the 16 MB artifact limit, or warns above 12 MB — relay either in the
user's words: something embedded is too big): the same page with the `<!DOCTYPE>`,
`<html>`, `<head>`, `<body>` and `<meta>` tags removed and `<title>` first,
because the Artifact tool wraps what it publishes in its own page skeleton.
**Always publish this file, never the build file** — the build file is for
ClassCloud, which wants a complete document.

The output path is stable (no build number in the name) on purpose: within one
session, republishing the same path is what keeps the same URL.

### B5. Publish

Read `artifact` from the manifest.

**First share (`artifact.url` empty):**

- `Artifact` publish with `file_path` = the artifact file, `favicon` = `🥽`,
  `label` = `"build <N>"`, `capabilities` = `{"db": {}}` (the **mailbox**, see
  below), `description` = `"<App Name> — a WebXR prototype from the ClassVR
  Prototyping Kit. Reload the page to get the latest build."`
- Record: `manifest.py --set artifact.url="<url>" --set artifact.owner="<user's
  email>" --set artifact.build=<N> --set artifact.mailbox=true --touch-shared`

**Update (`artifact.url` present):**

- If this session already published that URL: publish the same `file_path`
  again with `label` = `"build <N>"`. Omit `favicon`. If `artifact.mailbox` is
  not `true` yet, add `capabilities` = `{"db": {}}` and record
  `--set artifact.mailbox=true`; otherwise omit `capabilities` (omitting keeps
  the stored declaration).
- Otherwise the artifact was made in an earlier session: first `Artifact`
  `action: "read"` with `url` = `artifact.url` (the tool refuses to update an
  artifact the conversation hasn't read), then publish with `file_path`,
  `url` = `artifact.url` and `label` = `"build <N>"`. Omit `favicon`.
- Record: `--set artifact.build=<N> --touch-shared`

**Ownership.** An artifact can only be updated by the person who created it. If
`artifact.owner` is set and is not the current user, or the read/publish fails
with a not-owned / not-found error, the link in the manifest belongs to someone
else (or was deleted). Ask **once** with AskUserQuestion, two options:
`"Make a new link for me (Recommended)"` — "the old link keeps showing build
<artifact.build>; this one will follow your changes" — and `"Leave the link
alone"`. New link → follow the first-share path and overwrite `artifact.*`.
Leave it → skip publishing, say the link was not updated and who owns it.

**The mailbox.** Every kit app carries a diary (`window.KIT`). When the page
runs as an artifact, the viewer offers it a small database and the diary posts
itself there — one document per tester session at `reports/<session id>`:
build, browser, platform, whether the scene loaded, `errors`, `firstCode`,
`flags` (moments the tester marked with both triggers / F),
the `errorList` and the last 40 `events`, rewritten whole on the first error,
on every flag, on leaving the page, and once a minute. The tester does nothing; the panel says
"Reports from this page go to the app's creator". Declaring `db` makes the
artifact **organisation-internal**: viewers must be signed in as members of
the owner's organisation, and it cannot be shared publicly. Everyone who can
open the page can also read the reports (the runtime has no owner-only read
here) — acceptable because reports hold no personal data. Say on a first share:
"testers' error reports come back to you automatically — ask me 'did anyone
have problems?'".

**Expected warning.** The publish result may warn that the page "offers viewers
a file through a download link". That is A-Frame's built-in screenshot
component, not something in the app; ignore it, do not add a capability, and do
not mention it to the user.

**If the `Artifact` tool is not available in the session** (some local
sessions): fall back to the desktop bridge — `SendUserFile` on the **build**
file (the full document, step 2 output), then
`mcp__remote-devices__create_artifact` with its `file_uuid`, or
`update_artifact` with the id recorded in `artifact.desktopId`; record
`artifact.kind="desktop"` and the id. If neither route exists, say a link can't
be made from this session and attach the build file instead.

## 6. Write back and report

Route A: the repo *is* the folder; nothing to write back beyond the commit.
Route B: write `xr-project.json` — and `index.html` if `bumped` was true — back
to the user's folder with `display: "attach"`. Do **not** write `dist/` back for
a share; only the headset publish keeps a copy of what it uploaded.

Then one or two sentences, and **the link is the last line**:

- Route A, first share: the app name, "build N", where it will appear and
  when ("live in a couple of minutes"; or "once you press Create PR and Merge"
  only when the repo has no auto-publish and the API route failed), that the
  page is public, and — once — that the same URL works on a headset. Then the
  URL on its own line.
- Route A, update: "build N is on its way to the link — reload in a couple of
  minutes (the panel shows the build number)". Then the URL on its own line.
- Route A, saved but not published (user asked to hold): "saved, not live yet
  — say 'publish' when you're ready". No URL needed.
- Route B, first share: the artifact card is the link; say the link is private
  to them until they use the page's **Share** menu and that viewers need to be
  signed in to Claude. On an update: "anyone with the link just reloads".

Never explain git, the workflow, the artifact tool, the conversion, or the
manifest unless asked. The words "commit", "push", "branch" and "repo" don't
need to appear at all; "saved", "published" and "the link" do the job. If the
user *asks* how the history is organised, or wants to learn, then explain
gladly — the commits were written to be read.

## When this runs on its own

- **End of `/new-xr-app`**: every new app is created with a link, and the link
  is what ends the create turn (no screenshot).
- **After any edit to `index.html`** (see `xr-app-rules`): preview check, then
  this, so the link never lags the folder. If the source didn't change (build
  not bumped) skip the publish — nothing to update — and say so only if the user
  expected a change.
- **Inside `/publish-xr-app`**: if the link's build (`pages.build` or
  `artifact.build`) is behind the build just uploaded, refresh the link before
  rendering the QR, so both routes show the same number.

## What the links do and don't do

**Pages link (route A)**

- Public, top-level, permanent while the repo exists. Enter VR works; a QR of
  the URL opens it on a ClassVR headset. Renaming the repo or the app's slug
  changes the URL, so don't.
- Version history is the repo's history. "Go back to build 3" is a git revert
  of the app folder, which Claude can do when asked.
- No automatic tester reports; use `/check-headset` for headset sessions.

**Artifact link (route B)**

- Every publish is labelled `build N` in the page's version history, so an
  older build can be looked at from the version picker without touching the
  folder.
- Viewers can leave comments on the page. If the user asks what testers said,
  read them with `Artifact action: "comments"` on `artifact.url`.
- **Reading the mailbox.** When the user asks anything like "did anyone have
  problems?", "how did testing go?", "what happened when X tried it?" — or
  before fixing a bug someone else reported — run `Artifact action: "read_db"`
  with `url` = `artifact.url`, `db_op` = `"query"`, `collection` = `"reports"`,
  `query` = `{"order_by": {"field": "updated", "direction": "desc"}, "limit": 50}`
  (use `out_dir` when there are many). Then say it in plain words: how many
  sessions, how many with errors, which `firstCode` and how often, which
  browsers, what the `events` show the tester doing just before the first error
  — and open the line the code points at. Sessions with `errors: 0` are good
  news and should be counted, not skipped. Never quote raw JSON to the user.
  After a fix ships, offer to clear old reports: `write_db` `db_op: "delete"`
  per document (or a `batch`), only for builds older than the fix.
- Reports only arrive from the artifact link. The ClassCloud copy on a headset,
  a Pages page, a local file, and the link opened outside the viewer have no
  runtime and write nothing — those sessions still rely on the code on the sign.
- Opens in any desktop browser: click the scene once, then the mouse looks;
  Esc or another click stops; W/A/S/D move, Q/E turn. The frame refuses pointer
  lock, so `xr-kit` provides its own "soft look" there (cursor hidden, camera
  follows mouse movement). One known limit: if the cursor drifts off the page
  the camera pauses until it comes back — fullscreen (the button bottom-right)
  gives the mouse the whole screen. Dragging still works too.
- Viewers must be signed in to Claude; the page is private until shared from its
  Share menu. Sharing is the user's action, not the skill's.
- **The link does not work for VR on a headset.** The artifact viewer runs the
  page inside a frame whose permission policy blocks WebXR (`SecurityError`, no
  VR button) and whose sandbox blocks opening the page on its own (`_blank` and
  `_top` both do nothing). Tested in Wolvic on ClassVR, 2026-09-03. The panel
  says so. Headsets go through a Pages link or `/publish-xr-app`; if someone
  asks why the link "has no VR button", that is the answer — don't try to fix
  it in the app.
- One artifact per app, owned by whoever first shared it. A second person
  editing the same app gets their own link (B5, Ownership).
