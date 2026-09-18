---
name: publish-to-vercel
description: >
  This skill should be used when the user asks to "host it on Vercel", "put my XR
  app on Vercel", "publish to Vercel", "deploy to Vercel", "refresh the Vercel
  page", invokes /publish-to-vercel, or asks to create a new XR app naming Vercel
  as where it should live ("make a VR app called X, hosted on Vercel"). It is
  route C of /share-xr-app: chosen when the user names Vercel or the app's
  xr-project.json already has `vercel.url`, and then used instead of the Pages
  or artifact link after every edit. It builds the app into a slim page that
  loads the kit's plumbing from a shared, versioned library, deploys it through
  the Vercel connector — no Git, no terminal, no upload screen — verifies it
  live at a stable public URL, and ends with the QR code a headset can scan.
metadata:
  version: "0.1.0"
---

# Publish to Vercel

The Vercel route for a kit app. The app's own `index.html` is left as it is;
`vercel_build.py` turns it into a **slim page** (a few KB) that loads the kit's
plumbing from a hosted, versioned **shared library** and A-Frame from aframe.io.
Only the slim page is sent to Vercel on each publish, through the Vercel
connector's `deploy_to_vercel` tool. Production deploys are public, live at
once, and always at the same address, so one QR code stays valid for the life
of the app. Tested on desktop and on a ClassVR headset (Wolvic), 17 Sep 2026.

This route is **opt-in and additive**: an app is on Vercel only if the user
asked for it; `/share-xr-app` routes A (GitHub Pages) and B (artifact) and the
ClassCloud publish keep working, on the same build numbers.

## Outcome

- The app live at a stable public URL `https://<project>.vercel.app`
- `xr-project.json` carrying `vercel.project`, `vercel.url`,
  `vercel.deploymentId`, `vercel.build`, `vercel.teamId`, `vercel.lib`,
  `vercel.owner`
- `vercel-qr.png` in the app folder, and rendered as the **last thing in the turn**
- `index.html` written back if the build number bumped

## Before starting

The **Vercel connector** must be on in this chat (tools named `mcp__Vercel__…`,
in particular `deploy_to_vercel`, `get_deployment`, `list_teams`,
`web_fetch_vercel_url`). If they are missing, stop and say: "Turn on the Vercel
connector for this chat (Settings → Connectors → Vercel, and sign in to
Vercel), then ask me again." Do not fall back to another route unasked.

## Steps

### 0. If the app does not exist yet

The request created it *and* chose Vercel ("make a VR app called Bubble Pop,
host it on Vercel"). `/new-xr-app` runs its steps 1–6 as written and hands
over here at its step 7 (route C) with the project files already delivered.
Continue from step 1. Never ask a question `/new-xr-app` would not ask.

### 1. Locate and stage the project

The folder with `index.html` and `xr-project.json`. In a Cowork session stage
`index.html`, `xr-project.json`, `aframe.min.js` (the build reads the A-Frame
version from it) and every other local `<script src="./…">` into a workspace
folder with the same layout; scripts take that folder as the project. In a
local or Claude Code session use the folder directly.

### 2. Verify the source — do not skip

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/preview-xr-app/scripts/preview.py \
        --file "<project>/index.html" --out "<project>/.preview"

Exit `0`: continue. Exit `1`: **stop**, say what failed in the user's terms,
fix it, restart. A broken build must never replace a working page. Exit `3`:
continue but say the build was not verified. Skip this step only when
`/new-xr-app` has just run it on the same source.

### 3. Build number

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-xr-app/scripts/build.py --project "<project>"

Same as every other route: bumps `build` in `xr-project.json` only if the
source changed. Note `build` and `bumped`. The single-file output in `dist/`
is **not** uploaded here (ClassCloud and Pages use it); leave it.

### 4. Slim page and library

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-to-vercel/scripts/vercel_build.py \
        "<project>" --out "<scratch>/dist-vercel"

Build into a scratch directory, not the app folder (nothing here belongs in a
repo). It writes `page/index.html` (the slim page), `lib/*` (the four library
files for this template version) and `manifest.json`. Read the manifest: `kit`
(12-hex library version — a hash of the plumbing, so every app made from the
same template shares it), `libBase` (`https://xr-kit-lib-<kit>.vercel.app`),
`aframe`, `extraLibs`, and the sha256 of every file.

If `extraLibs` is not empty (the app bundles `cannon.iife.js` or another
library), that file must also be served from `libBase`. Check with
`web_fetch_vercel_url` `<libBase>/<name>`; if it is not there, **stop** and
say: this app uses an extra library the Vercel route doesn't host yet — use
the Pages link or `/publish-xr-app` for it. Do not push a large library
through the deploy tool.

### 5. Make sure the library is hosted

`web_fetch_vercel_url` on `<libBase>/xr-kit-<kit>.js`.

- **200** → the library for this template version exists. Continue.
- **Not found / error** → this template version has never been hosted. This
  is a **one-time step per template version** (i.e. per kit release), not a
  per-app step, and it is the slow one (~80 KB through the tool call). Say so
  in one line, then do it: `deploy_to_vercel` with `name` =
  `xr-kit-lib-<kit>`, `target` = `production`, `files` = the four `lib/*`
  files **plus** a `vercel.json` setting `Cache-Control: public,
  max-age=31536000, immutable` and `Access-Control-Allow-Origin: *` on
  `/(.*)\.(js|css)` **plus** a one-line `index.html` naming the version. Wait
  for `get_deployment` → `READY`. **Then verify**: fetch each hosted file
  (the browser pane on the user's PC, or `web_fetch_vercel_url`) and compare
  byte size / sha256 to `manifest.json`. Byte-identical is the goal; the one
  accepted difference is a JavaScript `\uXXXX` escape arriving as the literal
  character (same meaning, a few bytes shorter, on lines containing
  `–` or `·`). Anything else → redeploy that file. Never point apps
  at an unverified library.
- Never redeploy an existing `xr-kit-lib-<kit>` project with different
  content: a Vercel deploy replaces a project's whole file set, and other apps
  depend on it. A new template version gets a new project — that is what the
  hash in the name is for.

### 6. Deploy the app

Team: `vercel.teamId` from the manifest if set, else `list_teams` (one team →
use it; several → ask once which). Project name: `vercel.project` if set,
else the manifest `slug` (e.g. `bubble-pop`).

    deploy_to_vercel  target = "production"   name = <project>   teamId = <team>
                      files = [ { file: "index.html", data: <page/index.html> } ]

**Always `production`** — preview deployments sit behind a Vercel login and a
headset cannot open them. **Always send the complete file set** — a deploy
replaces everything in the project, so omitting `index.html` takes the page
down. A static page is `READY` at once.

Then `get_deployment` with the returned id and read `alias`. The stable public
address is the alias **without** a hash: prefer `<project>.vercel.app`; if it
is not listed (name taken globally) use `<project>-<team-slug>.vercel.app`.
Never hand out the per-deployment URL (`<project>-<hash>-…`): it is protected.

Record with `manifest.py --project "<project>" --set …`: `vercel.project`,
`vercel.url` (with `https://`), `vercel.deploymentId`, `vercel.build=<N>`,
`vercel.teamId`, `vercel.lib=<kit>`, and on a first publish
`vercel.owner="<user's email>"`.

### 7. Verify the live page

`web_fetch_vercel_url` on `vercel.url`: the text must contain
`window.BUILD = <N>;` and the four `<libBase>/xr-kit-…` references. If the
browser pane is available, also open `vercel.url?kitcheck` and read
`window.KIT.report()` and `window.KIT.checkResults`: scene loaded, 0 errors,
the Enter VR button present (`.a-enter-vr-button`). The "player can walk
forward" self-check fails in the pane (synthetic keys) — ignore that one
there; `preview.py` covered it. If the live page is wrong, say so and fix
before showing the QR.

### 8. QR code

    python3 -c "import qrcode; qrcode.make('<vercel.url>/', box_size=12, border=4).save('<project>/vercel-qr.png')"

(`pip install qrcode pillow --break-system-packages` if the module is
missing.) The address never changes for the app, so the file is made once;
regenerate only if `vercel.url` changed.

### 9. Write back and report

Write `xr-project.json` — and `index.html` if `bumped` — and `vercel-qr.png`
back to the user's folder (Cowork: `SendUserFile` `display: "attach"`, then
`device_commit_files`; in a repo, commit them as any other edit). Render
`vercel-qr.png` **last** (`display: "render"`), with the URL on its own line
just above it.

One or two sentences, in the kit's voice: the app name, that build N is live,
open the address in any browser, scan the QR on a ClassVR headset and press
the VR button. First publish only: "the page is public — anyone with the
address can open it". Do not explain Vercel, the library, manifests or build
numbers unless asked.

## When this runs on its own

- **After any edit to `index.html`** of an app whose manifest has
  `vercel.url`: `/share-xr-app` step 1 routes here, so the Vercel page never
  lags the folder. Source unchanged (not bumped) → nothing to publish; say so
  only if the user expected a change.
- **Combined create-and-host** ("make X, host it on Vercel"): `/new-xr-app`
  1–6, then this skill 1–9 in one turn; the QR is the last thing shown.

## Debugging an app on this route

- `/check-headset` works unchanged: the diary and its logbook are in the
  shared library, so headset plays still land in the ClassCloud log. The page
  URL is on `vercel.app`, so `headset_diary.py` must match sessions on the
  diary's own `app`/`b` fields, not on an `avnfs.com` URL.
- The Vercel connector's `get_runtime_logs` shows **nothing** for these pages:
  runtime logs are server-side function output only. A universal `/api/log`
  receiver (one route for headset, desktop and shared link, read with
  `get_runtime_logs`) was proved separately and is a later kit change, not
  part of this skill.
- Error codes: an error in the app's own code keeps its `<build>-<line>` code
  with the line counted in the slim page; an error inside the shared library
  is coded `<build>-lib`.

## Known limits

- Extra bundled libraries (`cannon.iife.js`) are not hosted yet — step 4
  stops with a plain message.
- The QR is a PNG in the chat and the app folder; it is not yet drawn on the
  page itself the way the Pages site builder does it.
- Vercel's free Hobby plan is for non-commercial personal use (100 deploys a
  day); staff use belongs on a Pro team. Runtime-log retention is 1 hour on
  Hobby, 1 day on Pro — irrelevant to this skill, relevant to the later
  `/api/log` work.
