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
  Apps on this route send their diary to the same project, so "what went wrong
  on the headset / in the browser?" is answered from the Vercel connector's
  runtime logs in seconds — no ClassCloud log fetch. Also handles "undo that
  publish" / "put the old version back".
metadata:
  version: "0.4.0"
---

# Publish to Vercel

The Vercel route for a kit app. The app's own `index.html` is left as it is;
`vercel_build.py` turns it into a **slim page** (a few KB) that loads the kit's
plumbing from a hosted, versioned **shared library** and A-Frame from aframe.io.
The page also loads `kit-relay.js`, which posts the app's diary to `/api/log`
in the same project; that function prints each post into the project's runtime
log (read back through the connector) and keeps one copy of each session in the
project's Blob store, which `/api/reports` reads back long after the runtime
log has rolled over. See "Reading what happened".

Production deploys are public, live at once, and always at the same address,
so one QR code stays valid for the life of the app. Tested on desktop and on a
ClassVR headset (Wolvic).

This route is **opt-in and additive**: an app is on Vercel only if the user
asked for it; `/share-xr-app` routes A (GitHub Pages) and B (artifact) and the
ClassCloud publish keep working, on the same build numbers.

## Outcome

- The app live at a stable public URL `https://<project>.vercel.app`
- `xr-project.json` carrying `vercel.project`, `vercel.projectId`,
  `vercel.url`, `vercel.deploymentId`, `vercel.build`, `vercel.teamId`,
  `vercel.lib`, `vercel.owner`, `vercel.store`, and `vercel.history`
  (the last few deployments, so a publish can be undone)
- `vercel-qr.png` in the app folder, and rendered as the **last thing in the turn**
- `index.html` written back if the build number bumped

## Before starting

The **Vercel connector** must be on in this chat. What it is called changes —
Vercel reshaped the server's tool set on 21 Sep 2026 — so check for the
*capability*, never one name:

| Need | Use whichever is present |
|---|---|
| deploy files | `create_deployment` (preferred), else `deploy_to_vercel` |
| deployment state / alias | `get_deployment` |
| which team | `list_teams` |
| read a live page | `web_fetch_vercel_url` |
| read the diary | `get_runtime_logs`, `get_runtime_errors` |
| keep history (optional) | `create_storage_stores_blob` |
| undo a publish | `request_rollback`, `request_promote` |

No deploy tool at all → stop and say: "Turn on the Vercel connector for this
chat (Settings → Connectors → Vercel, and sign in to Vercel), then ask me
again." Do not fall back to another route unasked.

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
repo). It writes the **deploy set** under `page/` — `index.html` (the slim
page), `kit-relay.js`, `api/log.js`, `api/reports.js`, `package.json` and
`vercel.json` — plus `lib/*` (the four library files for this template
version) and `manifest.json`. Read the manifest: `deploy` (the file list),
`deployFiles` (each file's `sha1`, `size` and whether it is `reusable`), `kit`
(12-hex library version — a hash of the plumbing, so every app made from the
same template shares it), `libBase` (`https://xr-kit-lib-<kit>.vercel.app`),
`aframe`, `extraLibs`, and the sha256 of every file.

`--no-relay` makes a static page with no diary delivery; `--indexable` leaves
out the `vercel.json` that keeps the page out of search engines. Neither is
the default.

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
  in one line, then do it: deploy `name` = `xr-kit-lib-<kit>`, `target` =
  `production`, files = the four `lib/*` files **plus** the kit's
  `assets/vercel-lib.json` as `vercel.json` (it sets `Cache-Control: public,
  max-age=31536000, immutable` and `Access-Control-Allow-Origin: *` on
  `/(.*)\.(js|css)`) **plus** a one-line `index.html` naming the version. Wait
  for `get_deployment` → `READY`. **Then verify**: fetch each hosted file
  (`web_fetch_vercel_url`, or the browser pane) and compare byte size / sha256
  to `manifest.json`. Byte-identical is the goal; the one accepted difference
  is a JavaScript `\uXXXX` escape arriving as the literal character (same
  meaning, a few bytes shorter, on lines containing `–` or `·`). Anything
  else → redeploy that file. Never point apps at an unverified library.
- Never redeploy an existing `xr-kit-lib-<kit>` project with different
  content: a Vercel deploy replaces a project's whole file set, and other apps
  depend on it. A new template version gets a new project — that is what the
  hash in the name is for.

### 6. Deploy the app

Team: `vercel.teamId` from the manifest if set, else `list_teams` (one team →
use it; several → ask once which). Project name: `vercel.project` if set,
else the manifest `slug` (e.g. `bubble-pop`).

    create_deployment  teamId = <team>   skipAutoDetectionConfirmation = "1"
      requestBody = {
        name: "<project>", target: "production",
        projectSettings: { framework: null },        // first publish only
        files: [ { file: "index.html", data: <page/index.html>, encoding: "utf-8" },
                 { file: "kit-relay.js",   sha: <deployFiles sha1> },
                 { file: "api/log.js",     sha: … },
                 { file: "api/reports.js", sha: … },
                 { file: "package.json",   sha: … },
                 { file: "vercel.json",    sha: … } ] }

(With `deploy_to_vercel` instead: same file list, `target`/`name`/`teamId` at
the top level, and every file inline — that tool has no `sha` form.)

Three rules, each learned the hard way:

- **Always `production`.** Preview deployments sit behind a Vercel login and a
  headset cannot open them.
- **Always send the complete file set** (every name in the manifest's `deploy`
  list). A deploy replaces everything in the project, so a file left out is
  gone from the live site.
- **Only `index.html` changes between publishes.** The others are byte-identical
  every time, so send them as `{ file, sha }` — the SHA1 in `deployFiles`,
  `size` optional — and Vercel reuses the copy it already has. This works for
  any file the *account* has uploaded before, in any project (verified 21 Sep),
  so from the second publish anywhere they never travel again. On a brand-new
  account, or if the deploy is rejected for an unknown SHA, send that file
  inline once (`data` + `encoding: "utf-8"`) and use the SHA next time.

With the functions and a dependency install the deploy takes ~20 s; poll
`get_deployment` until `READY` before verifying.

Then `get_deployment` with the returned id and read `alias`. **The public
address is `<project>.vercel.app` and only that.** The team-suffixed alias
`<project>-<team-slug>.vercel.app` is a generated URL: Standard Protection
covers it, so it answers `401 Protected deployment` and a headset cannot open
it (verified 21 Sep). Never hand it out, and never the per-deployment URL
(`<project>-<hash>-…`) either. If the bare alias is missing, the project name
is taken globally — pick another name and redeploy rather than falling back to
a protected address.

Record with `manifest.py --project "<project>" --set …`: `vercel.project`,
`vercel.projectId` (`project.id` from `get_deployment`, `prj_…`), `vercel.url`
(with `https://`), `vercel.deploymentId`, `vercel.build=<N>`, `vercel.teamId`,
`vercel.lib=<kit>`, and on a first publish `vercel.owner="<user's email>"`.
Also keep a short history so a publish can be undone — newest first, at most
three (Vercel's Hobby plan keeps only the last three anyway):

    --set vercel.history='[{"build":<N>,"id":"<dpl_…>"},{…},{…}]'

### 6b. Play history (first publish only)

The app keeps one record of every play so "what happened on Tuesday?" can be
answered on Friday. It needs a Blob store connected to the project, which is
one call — do it right after the first deploy of an app, then never again:

    create_storage_stores_blob  teamId = <team>
      requestBody = { name: "<project>-history", access: "private",
                      region: "lhr1", projectId: "<prj_…>" }

That creates the store, connects it, and sets `BLOB_READ_WRITE_TOKEN` in the
project in one go. **Redeploy once afterwards** (step 6 again, same files —
all by SHA, so it costs nothing) so the functions pick up the token. Record
`vercel.store` = the store id. If the call fails (tool absent, or the Hobby
100-store limit reached), say in one line that the app will keep an hour of
history rather than months, and carry on — nothing else breaks.

A store can serve several projects; if the user already has one they want
reused, connect it in the Vercel dashboard instead and skip this step.

### 7. Verify the live page

`web_fetch_vercel_url` on `vercel.url`: the text must contain
`window.BUILD = <N>;`, `./kit-relay.js`, the `xr-kit-source` meta line and the
four `<libBase>/xr-kit-…` references. If the browser pane is available, also
open `vercel.url?kitcheck` and read `window.KIT.report()` and
`window.KIT.checkResults`: scene loaded, 0 errors, the Enter VR button present
(`.a-enter-vr-button`). The "player can walk forward" self-check fails in the
pane (synthetic keys) — ignore that one there; `preview.py` covered it. If the
live page is wrong, say so and fix before showing the QR.

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
address can open it" (it is kept out of search engines, but that is not worth
saying unless asked). Do not explain Vercel, the library, manifests or build
numbers unless asked.

## Undoing a publish

"Undo that", "put the old version back", "go back to the version before this
one" — for an app with `vercel.history`:

    request_rollback  projectId = vercel.projectId  deploymentId = <the previous id>
                      teamId = vercel.teamId        description = "…"

The old build is live again within seconds, on the same address (verified on
Hobby, 21 Sep). Then set `vercel.build` back and move `vercel.deploymentId` to
that id, keeping the history list as it was.

**A rollback pins the address to that deployment.** The next publish will
build fine but the public URL will still show the old one until it is promoted:

    request_promote  projectId = vercel.projectId  deploymentId = <the new id>  teamId = …

So after any rollback, the next run of step 6 must end with a `request_promote`
and a re-check of `vercel.url`. If the user asks to "go forward again" instead
of publishing, promote the newer deployment directly.

Vercel keeps the **last three production builds** on the Hobby plan, and 30
days of them; on Pro it is a year and twenty. Beyond that there is nothing to
roll back to — say so plainly rather than guessing.

## Reading what happened (debugging on this route)

Whenever the user asks what went wrong, whether it worked, what happened on
the headset, or before fixing a bug someone reported — for an app with
`vercel.url` — read the diary **from Vercel first**; it is the same for a
headset, a desktop browser and a shared link, and arrives within seconds of
the play (`/check-headset` does this itself when it sees `vercel.url`).

**Within the hour — the runtime log, which has everything:**

    get_runtime_logs  projectId = vercel.projectId  teamId = vercel.teamId
                      deploymentId = vercel.deploymentId   since = "1h"
                      query = "kit-diary"   (add level = ["error"] for errors only)

Always scope to the deployment id — a project-wide query can time out. Each
line is one post from `kit-relay.js`: `session`, `app`, `build`, `k` (why it
was sent: `start`, `checks`, `vr`, `flag`, `error`, `beat`, `end`), `t`
seconds running, `st` state, `vr`/`ev` presenting now / ever, `fps`, `c`
controllers, `p` presses, `tn` turns, `e`/`f` error and flag counts,
`firstCode`, `dof`/`lk` (3DoF lock), and `d` — the diary entries added since
the previous post as `[i, t, kind, text, code?]`, which includes everything
the app printed. The `ua` says which device: `Android … Mobile VR` is the
headset (Wolvic), a desktop UA is a browser. `get_runtime_errors` gives a
clustered first look at errors across sessions.

**Older than that — the app's own history**, which every session wrote when
the player left VR or closed the page:

    web_fetch_vercel_url  <vercel.url>/api/reports              one line per session, newest first
    web_fetch_vercel_url  <vercel.url>/api/reports?day=2026-09-21
    web_fetch_vercel_url  <vercel.url>/api/reports?session=<id>  that session in full

The summary carries app, build, when, seconds, state, whether VR was entered,
fps, controllers, presses, errors, flags, first error code and the device;
`?session=` adds every diary entry, the error list, the flags and the
self-check results. `{"ok":false,"reason":"no history store…"}` means the app
was published before step 6b, or the store was never connected — say so and
offer to add it (one call, then a redeploy).

Then tell the story exactly as `/check-headset` step 6 describes (build,
entered VR, errors first with their codes and lines, the seconds before a
flag, or the numbers that show it ran well). Ignore a `flag` post whose `d`
ends in `PASS the "something wrong" marker works` — that is the self-check
pressing F during `?kitcheck`, not a person.

Nothing in either place → fall back to the ClassCloud log (`/check-headset`
steps 2–4), which still works: the diary's logbook is in the shared library
too. Error codes: an error in the app's own code keeps its `<build>-<line>`
code with the line counted in the slim page (open `dist-vercel/page/index.html`
from the build, or rebuild it); an error inside the shared library is coded
`<build>-lib`.

## When this runs on its own

- **After any edit to `index.html`** of an app whose manifest has
  `vercel.url`: `/share-xr-app` step 1 routes here, so the Vercel page never
  lags the folder. Source unchanged (not bumped) → nothing to publish; say so
  only if the user expected a change.
- **Combined create-and-host** ("make X, host it on Vercel"): `/new-xr-app`
  1–6, then this skill 1–9 in one turn; the QR is the last thing shown.

## Known limits

- Extra bundled libraries (`cannon.iife.js`) are not hosted yet — step 4
  stops with a plain message.
- The QR is a PNG in the chat and the app folder; it is not yet drawn on the
  page itself the way the Pages site builder does it.
- Vercel's free Hobby plan is for non-commercial personal use (100 deploys a
  day); staff use belongs on a Pro team. Runtime logs last an hour there (a
  day on Pro); the Blob history is what covers anything older, within Hobby's
  1 GB and ~2,000 stored sessions a month.
- Anyone who knows the address can post to `/api/log` and read `/api/reports`
  (the page is public); the diary carries no personal data by construction.
- Everyone publishing needs their own Vercel account, and Vercel accounts are
  16+ — this route is for staff. Pupils get the app through ClassCloud.
