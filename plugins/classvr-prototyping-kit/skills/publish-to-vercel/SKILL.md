---
name: publish-to-vercel
description: >
  This skill should be used when the user asks to "host it on Vercel", "put my XR
  app on Vercel", "publish to Vercel", "refresh the Vercel page", invokes
  /publish-to-vercel, or creates a new XR app naming Vercel as its home ("make a
  VR app called X, hosted on Vercel"). It is route C of /share-xr-app: chosen
  when the user names Vercel or the app's xr-project.json has `vercel.url`, and
  then used after every edit. It builds a slim page that loads the kit's
  plumbing from a shared library, deploys it through the Vercel connector — no
  Git, no terminal — verifies it live at a stable public URL and ends with that
  link (the page draws its own headset QR code). The app's diary lands in the same project, so "what went
  wrong on the headset?" is answered from the connector's runtime logs. Every
  publish is a saved version: also use for "show me the versions", "what
  changed in version 4", "go back to version 4", "put the old version back",
  "call this version …" and "what's the fingerprint of this version".
metadata:
  version: "0.7.1"
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

**Every publish is a version.** The build stamps the page's SHA-1 — its
*fingerprint* — and a one-line note into `vercel.versions` in
`xr-project.json`, and the deploy carries the whole history along:
`/history` (a page listing every version), `/history.json` (the same,
machine-readable) and `/v/<N>/` (every version, playable forever). Older
versions travel **by fingerprint only** — Vercel already holds their bytes —
so a fifty-version app costs the same to publish as a two-version one. The
words to use with the person are **save, version, history, go back, make my
own copy, fingerprint** — never commit, deploy, rollback, hash or SHA.

This route is **opt-in and additive**: an app is on Vercel only if the user
asked for it; `/share-xr-app` routes A (GitHub Pages) and B (artifact) and the
ClassCloud publish keep working, on the same build numbers.

## Outcome

- The app live at a stable public URL `https://<project>.vercel.app`, where
  `<project>` is `classvr-<app>-<vercel username>` for apps first published
  with kit 0.27 or later (see step 6)
- The page drawing **its own QR code** in its top-right corner (click to fill
  the screen), pointing at the public address — or at `/v/<N>/` on a
  version's own page — so a headset can scan it straight off any screen
- Its history at `<url>/history`, every version at `<url>/v/<N>/`
- The same page kept in the app folder as `versions/Versions 1 - 10/03-index.html`
  with `03-README.txt` beside it (ten versions to a sub-folder), so going
  back never needs a download for the person's own app
- `xr-project.json` carrying `vercel.project`, `vercel.projectId`,
  `vercel.url`, `vercel.deploymentId`, `vercel.build`, `vercel.teamId`,
  `vercel.lib`, `vercel.owner`, `vercel.store`, and `vercel.versions` (one
  entry per version: number, date, note, fingerprint, size, and
  `restoredFrom` when it put an older version back — written by the build)
- The URL as the **last line of the reply**, on its own line — no QR image in
  the chat: the page shows its own code
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
| keep play history (optional) | `create_storage_stores_blob` |
| seed a file Vercel doesn't hold yet | `upload_file` (only if a deploy says `missing_files`) |

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

### 3b. The version note

Every publish gets a one-line, plain-English "what changed" — the line the
history page shows next to the version number. **Write it yourself** from
what the person asked for in this turn ("Added a lap counter above the
track", "Made the ball bounce higher", "First version"); never ask for it. If
they said "call this version …" or "note it as …", use their words exactly.
Restoring an older version: "Put version N back" (and pass
`--restored-from N`, see "Going back"). No names, no dates in the note — the
build adds the date, and the public history carries no names by design.

### 4. Slim page, library and history

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-to-vercel/scripts/vercel_build.py \
        "<project>" --out "<scratch>/dist-vercel" --note "<the version note>" \
        [--url "https://<project name>.vercel.app/"]      # first publish only

**First publish:** work out the project name now (step 6, "Project name")
and pass `--url https://<that name>.vercel.app/`, so the page's QR code is
right on the very first deploy. Later publishes leave `--url` out — the
build reads `vercel.url`.

Build into a scratch directory, not the app folder (nothing here belongs in a
repo). It writes the **deploy set** under `page/` — `index.html` (the slim
page), `v/<N>/index.html` (the same page, at its permanent address),
`history.json`, `history/index.html`, `kit-relay.js`, `kit-qr.js`,
`api/log.js`, `api/reports.js`, `package.json` and `vercel.json` — plus `lib/*` (the four
library files for this template version) and `manifest.json`. It also
records this version in the project's `xr-project.json` (`vercel.versions`)
and keeps the page in the project as `versions/Versions <A> - <B>/<NN>-index.html`
plus `<NN>-README.txt` (the note, date, fingerprint and how to use it), so
**the project changed** — the manifest and the two new files under
`versions/` must be written back in step 9 even when the source did not bump. Read the manifest: `deploy` (the complete
file list, including every older `v/<M>/index.html`), `deployFiles` (each
file's `sha1`, `size`, whether it is `reusable`, and `byFingerprint: true`
for older versions that are never re-sent), `history` (`current`, `note`,
`fingerprint`, `count`), `kit` (12-hex library version — a hash of the
plumbing, so every app made from the same template shares it), `libBase`
(`https://xr-kit-lib-<kit>.vercel.app`), `aframe`, `extraLibs`, and the
sha256 of every file.

The build also writes any `\uXXXX` / `\xXX` escape for a character above U+007F in the page as the plain character (it prints how many), because the upload can do that conversion on its own and the fingerprint would then no longer match. If a publish ever reports a fingerprint mismatch anyway, rebuild from the app's `index.html` and publish again; never hand-edit the page or the recorded fingerprint to make them agree.

Re-running the build for the same build number (a publish that failed, an
unchanged source) replaces that version's entry rather than adding another,
so a failed publish never leaves a phantom version behind.

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
use it; several → ask once which).

**Project name:** `vercel.project` if set — an app already on Vercel keeps
its name and address for life. Otherwise build a new one:
`classvr-<slug>-<username>`, where `<username>` is `user.username` from
`get_auth_user` (e.g. `classvr-bubble-pop-lukemoseley-avantis`). Lowercase,
letters, digits and single hyphens only; if it is longer than 63 characters,
shorten the `<slug>` part (a host-name label cannot be longer). Every
`*.vercel.app` address is one worldwide first-come list, so the plain slug is
often taken by a stranger; the prefix and username make a clash rare. No
username available → use the person's initials from their name. Never ask
the person to choose a name.

    create_deployment  teamId = <team>   skipAutoDetectionConfirmation = "1"
      requestBody = {
        name: "<project>", target: "production",
        projectSettings: { framework: null },        // first publish only
        files: [ // new this publish — inline, from page/
                 { file: "index.html",         data: <page/index.html>,         encoding: "utf-8" },
                 { file: "v/<N>/index.html",   data: <the same text>,           encoding: "utf-8" },
                 { file: "history.json",       data: <page/history.json>,       encoding: "utf-8" },
                 { file: "history/index.html", data: <page/history/index.html>, encoding: "utf-8" },
                 // unchanged since some earlier publish — by fingerprint, from deployFiles
                 { file: "kit-relay.js",     sha: <sha1>, size: <size> },
                 { file: "api/log.js",       sha: …, size: … },
                 { file: "api/reports.js",   sha: …, size: … },
                 { file: "package.json",     sha: …, size: … },
                 { file: "vercel.json",      sha: …, size: … },
                 { file: "v/1/index.html",   sha: …, size: … },   // one per older version,
                 { file: "v/2/index.html",   sha: …, size: … } ] }  // straight from deployFiles

(With `deploy_to_vercel` instead: same file list, `target`/`name`/`teamId` at
the top level, and every file inline — that tool has no `sha` form, so older
versions cannot ride along by fingerprint; build with `--no-history` there.)

Four rules, each learned the hard way:

- **Always `production`.** Preview deployments sit behind a Vercel login and a
  headset cannot open them.
- **Always send the complete file set** (every name in the manifest's `deploy`
  list — the `byFingerprint` ones included). A deploy replaces everything in
  the project, so a file left out is gone from the live site, and a version
  left out vanishes from the history.
- **Inline what is new, fingerprint what is not.** `deployFiles` says which
  is which: `reusable: false` → send `data` + `encoding: "utf-8"`;
  `reusable: true` → send `{ file, sha, size }` and Vercel reuses the bytes
  it already holds. That works for any file the *account* has uploaded
  before, in any project (verified 21–22 Sep). A file can only be referenced
  by fingerprint once Vercel has its bytes, which is why the current page is
  sent inline twice (as `index.html` and as `v/<N>/index.html`) and becomes
  a by-fingerprint entry from the next publish on.
- **`missing_files` means Vercel does not hold that fingerprint yet** (a
  brand-new account, or a support file that changed with a kit release). The
  error lists the SHA1s. For each, either send that file inline this once, or
  `upload_file` it (`xVercelDigest` = its sha1, `contentLength` = its size,
  body base64) and deploy again by fingerprint. Never drop the file.

With the functions and a dependency install the deploy takes ~20 s; poll
`get_deployment` until `READY` before verifying.

Then `get_deployment` with the returned id and read `alias`. **The public
address is `<project>.vercel.app` and only that.** The team-suffixed alias
`<project>-<team-slug>.vercel.app` is a generated URL: Standard Protection
covers it, so it answers `401 Protected deployment` and a headset cannot open
it (verified 21 Sep). Never hand it out, and never the per-deployment URL
(`<project>-<hash>-…`) either. If the bare alias is missing, the project name
is taken globally — Vercel then gives the project a random-suffixed address
instead. Do not use it: add `-2` (then `-3`, …) to the project name, rebuild
with the new `--url` and deploy again as a new project, rather than falling
back to a protected or unpredictable address. (Rare with the naming rule
above; apps published before 0.27, like `tiny-racers-mu`, keep whatever they
got.)

**The QR check (first publish):** the manifest's `qrUrl` must equal the
public address just confirmed. If they differ (a renamed project), rebuild
with `--url <the real address>` and redeploy before going on — the page's
own QR code must never point anywhere else.

Record with `manifest.py --project "<project>" --set …`: `vercel.project`,
`vercel.projectId` (`project.id` from `get_deployment`, `prj_…`), `vercel.url`
(with `https://`), `vercel.deploymentId`, `vercel.build=<N>`, `vercel.teamId`,
`vercel.lib=<kit>`, and on a first publish `vercel.owner="<user's email>"`.
`vercel.versions` is already written by the build — do not edit it by hand.
On a **first** publish the build ran before `vercel.url` was known, so the
`history.json` that went up says `"url": null`; that is fine (the page
still works) and the next publish fills it in. If the person will share the
history link straight away, run step 4 again now that the URL is recorded
and redeploy — everything but the two history files goes by fingerprint, so
it costs almost nothing.

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
four `<libBase>/xr-kit-…` references. Then `<vercel.url>/history.json`: its
`current` must be `<N>` and it must list every version in `vercel.versions`;
and `<vercel.url>/v/<N>/` must answer 200 with the same page as the root.
The page must carry `<meta name="xr-kit-qr" content="url=<vercel.url>/">`
and `<vercel.url>/kit-qr.js` must answer 200. If
the app had older versions, spot-check one `<vercel.url>/v/<M>/` too — a 404
there means a by-fingerprint entry was left out of the deploy. If the browser pane is available, also
open `vercel.url?kitcheck` and read `window.KIT.report()` and
`window.KIT.checkResults`: scene loaded, 0 errors, the Enter VR button present
(`.a-enter-vr-button`). The "player can walk forward" self-check fails in the
pane (synthetic keys) — ignore that one there; `preview.py` covered it. If the
live page is wrong, say so and fix before giving the link.

### 8. No QR image

The page draws its own QR code in its top-right corner, so **do not make or
render a QR image** for the chat or the folder (a `vercel-qr.png` left in an
app folder by an older kit is harmless; leave it). Only if the person asks for
a code to print or put on a slide:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-xr-app/scripts/make_qr.py \
        --url "<vercel.url>/" --out "<project>/vercel-qr.png"

### 9. Write back and report

Write `xr-project.json` (it always changed: `vercel.versions` gained an
entry), the two new files under `versions/` (the build printed their path),
and `index.html` if `bumped`
back to the user's folder (Cowork: `SendUserFile` `display: "attach"`, then
`device_commit_files`; in a repo, commit them as any other edit). Nothing is
rendered: **the URL is the last line of the reply, on its own line**, so the
person can click it straight away.

One or two sentences, in the kit's voice: the app name, that **version N** is
live ("saved as version 3 — added a lap counter"), open the address in any
browser; for a headset, click the QR code in the page's top-right corner to
enlarge it, scan it with the ClassVR scanner and press the VR button. First
publish only: "the page is public — anyone with the address can open it" (it
is kept out of search engines, but that is not worth saying unless asked),
and mention once that every version is kept and `<url>/history` lists them.
Do not explain Vercel, the library, manifests, fingerprints or build numbers
unless asked. Say "version", not "build", to the person — they are the same
number.

## Showing the history

"Show me the versions", "what changed in version 4", "when did I add the
sign", "which version is on the headset" — read `<vercel.url>/history.json`
(`web_fetch_vercel_url`; it is public and tiny, so this works for **any**
kit app on Vercel, not only the person's own). Answer in a sentence or a
short list: version number, date, note; add the fingerprint (first eight
characters) only when two people need to be sure they mean the same one.
Point them at `<vercel.url>/history` if they want to look or click through.
Anyone with the address can read it — say so if they ask who can see it.

## Going back to a version

"Go back to version 4", "put the old version back", "undo that publish",
"restore version 4". This is an ordinary publish whose source is the older
page — nothing is rolled back and nothing is deleted, so it works on every
Vercel plan and the history stays a straight line:

1. Which version? "Undo that" / "the version before" = the one below
   `current` in `history.json`. A number = that number. Confirm in half a
   sentence what it contains (its note) before doing it if there is any
   doubt.
2. **Look in the app folder first** — this is the normal case and needs no
   download:

       python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-to-vercel/scripts/vercel_build.py \
           "<project>" --local-version <M>

   `ok: true` → `path` is the kept page and its fingerprint matches what was
   recorded at publish time; use it as `<restore page>` below. (In a Cowork
   session stage `versions/Versions <A> - <B>/<MM>-index.html` alongside the
   project first; `<A>` = the multiple of ten below M plus one.) `ok: false`
   → the file is missing or was altered: say so in half a sentence and fall
   back to the live address: `web_fetch_vercel_url`
   `<vercel.url>/v/<M>/index.html`, saved as `<scratch>/restore.html`.
   Either way, the four library files the page names (`/copy-xr-app` step 4
   lists them) go into `<scratch>/lib/`; the current build's `lib/` output
   already has them when the kit version matches.
3. Rebuild the source and put it in place of the app's `index.html`:

       python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-to-vercel/scripts/vercel_build.py \
           --unslim "<restore page>" --lib-dir "<scratch>/lib" \
           --out "<project>/index.html" --expect-sha1 <that version's sha1 from vercel.versions>

   `--expect-sha1` refuses a page that does not match the history — fetch
   again rather than restoring something unverified.
4. Steps 2–9 as normal, with `--note "Put version <M> back" --restored-from <M>`
   in step 4. The result is a **new** version (N+1) whose page is identical
   to version M apart from its number; the history page tags it "restored
   from version M". Versions between M and N stay in the history — say so:
   "version 4 is back on the headset, as version 7; 5 and 6 are still there
   if you want them."

Never `request_rollback` for this: it is Pro-only for arbitrary versions,
it pins the address until a promote, and it hides what happened from the
history. If a very recent publish is *broken* and speed matters, restoring
the previous version this way still takes under a minute.

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
  1–6, then this skill 1–9 in one turn; the link is the last line.

## Known limits

- Extra bundled libraries (`cannon.iife.js`) are not hosted yet — step 4
  stops with a plain message.
- The on-page QR code arrives with an app's next publish; versions published
  before kit 0.27 (older `/v/<N>/` pages) do not have it, and never will —
  their bytes are kept exactly as published.
- On a narrow window (under 700 px wide or 520 px tall) the card shrinks to a
  96 px code that is too small to scan off a screen; click it to fill the
  screen first. Same as the Pages card.
- Vercel's free Hobby plan is for non-commercial personal use (100 deploys a
  day); staff use belongs on a Pro team. Runtime logs last an hour there (a
  day on Pro); the Blob history is what covers anything older, within Hobby's
  1 GB and ~2,000 stored sessions a month.
- Anyone who knows the address can post to `/api/log` and read `/api/reports`
  (the page is public); the diary carries no personal data by construction.
- Everyone publishing needs their own Vercel account, and Vercel accounts are
  16+ — this route is for staff. Pupils get the app through ClassCloud.
- The version history is public along with the page, by design: anyone with
  the address can list, play and copy every version. It carries no names.
  Versions published before kit 0.25 are not in it — an app already on
  Vercel starts its history at the first publish made with this version, and
  `vercel.versions` starts at whatever `build` is then.
- The `versions/` folder is a convenience copy: deleting or moving it breaks
  nothing (go-back falls back to the live address), and the kit never edits
  an app from it — `index.html` is always the source. Ten versions per
  sub-folder, two-digit numbers; version 100 onwards simply gets three.
- Old versions live in the *latest* deployment (by fingerprint), so the
  history does not depend on Vercel keeping old deployments. It does depend
  on Vercel keeping a file's bytes while a live deployment references them,
  which is the same promise that serves the page at all.
