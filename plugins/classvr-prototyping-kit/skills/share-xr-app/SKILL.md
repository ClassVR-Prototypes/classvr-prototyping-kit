---
name: share-xr-app
description: >
  This skill should be used when the user asks to "share my XR app", "give me a link
  to the app", "put it in an artifact", "update the artifact", "refresh the link",
  "make the link show the latest version", or invokes /share-xr-app. It builds the
  app into one file, verifies it, and publishes it as a Claude Artifact — a web
  page with a permanent link anyone with access can open and reload. It is also
  run automatically at the end of /new-xr-app and after every edit to an app, so
  the link is never behind the folder.
metadata:
  version: "0.1.0"
---

# Share XR app

Put the app on a link. The first run creates a Claude Artifact for the app and
records its URL in `xr-project.json`; every later run — from any session, any
day — updates that same artifact in place. People who have the link just reload
the page to see the latest build; the build number on the panel tells them
which one they are looking at.

This is the **desktop-browser** route: for looking at the app, sharing it with
colleagues, and checking a change landed. The **headset** route is still
`/publish-xr-app` (ClassCloud + QR). They share the same build numbers.

## Outcome

- One self-contained page published as an Artifact, at a URL that never changes
- `xr-project.json` carrying `artifact.url`, `artifact.build`, `artifact.owner`
- The artifact card on screen as the last thing in the turn (the card *is* the
  link — never paste the URL into the reply unless asked)
- `index.html` written back to the folder if the build number bumped

## Steps

Do these in order. Nothing here asks the user a question except the ownership
case in step 5.

### 1. Locate and stage the project

The folder with `index.html` and `xr-project.json`. In a cloud session stage
`index.html`, every local `<script src="./…">` it references, and
`xr-project.json` into the workspace with the same layout. Scripts take that
staged folder as `--project`.

### 2. Build

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-xr-app/scripts/build.py --project "<project>"

Same script as the headset publish: inlines every local script into
`dist/<slug>-build<N>.html`, bumps the build number only if the source changed.
Note `build`, `bumped` and `output`.

### 3. Verify — do not skip

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/preview-xr-app/scripts/preview.py \
        --file "<output from step 2>" --out "<project>/.preview"

Exit `0`: continue. Exit `1`: **stop**, say what failed in the user's terms, fix
it, restart from step 2. A broken build must never replace a working link. Exit
`3`: continue, but say the build was not verified. Do **not** send
`preview.png` in this flow — the artifact card is what the turn ends on.

### 4. Convert to artifact form

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

### 5. Publish

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

### 6. Write back and report

Write `xr-project.json` — and `index.html` if `bumped` was true — back to the
user's folder with `display: "attach"`. Do **not** write `dist/` back for a
share; only the headset publish keeps a copy of what it uploaded.

Nothing is rendered after the artifact card. One sentence: the app name, "build
N is live on the link", and — first share only — that the link is private to
them until they use the page's **Share** menu, and that viewers need to be
signed in to Claude. On an update: "anyone with the link just reloads".

Never explain the artifact tool, the conversion, or the manifest unless asked.

## When this runs on its own

- **End of `/new-xr-app`**: every new app is created with a link, and the card
  is what ends the create turn (no screenshot).
- **After any edit to `index.html`** (see `xr-app-rules`): preview check, then
  this, so the link never lags the folder. If the source didn't change (build
  not bumped) skip the publish — nothing to update — and say so only if the user
  expected a change.
- **Inside `/publish-xr-app`**: if `artifact.build` is behind the build just
  uploaded, refresh the link before rendering the QR, so both routes show the
  same number.

## What the link does and doesn't do

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
  a local file, and the link opened outside the viewer have no runtime and
  write nothing — those sessions still rely on the code on the sign.

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
  says so. Headsets go through `/publish-xr-app`; if someone asks why the link
  "has no VR button", that is the answer — don't try to fix it in the app.
- One artifact per app, owned by whoever first shared it. A second person
  editing the same app gets their own link (step 5, Ownership).
