---
name: copy-xr-app
description: >
  This skill should be used when the user wants their own copy of an XR app
  that someone else published — "copy this app", "make me my own version of
  this", "fork this prototype", "I want to build on this one", "can I edit
  this app someone sent me", or /copy-xr-app followed by a published address.
  It takes the address of a kit app published on Vercel, GitHub Pages or
  ClassCloud, rebuilds the app's full source from the published page, puts it
  in a new project folder the user can edit with ordinary prompts, checks it
  runs, and offers to publish it as their own. Nothing is needed from the
  person who made the original — no files sent, no repository, no account
  shared.
metadata:
  version: "0.1.0"
---

# Copy an XR app

A published kit app carries everything needed to rebuild its source: the page
itself is the app minus the kit's plumbing, and the plumbing is a versioned
library at a public address the page names. So an address is enough to hand
someone a working, editable copy.

The copy is the copier's own from that moment: their folder, their build
numbers, their publish. The original is untouched and cannot be affected.

## Outcome

- A new project folder with `index.html`, `aframe.min.js` and
  `xr-project.json`, the same shape `/new-xr-app` makes
- `xr-project.json` carrying `forkedFrom` (the address, build and library it
  came from) and **no** ids from the original (a publish makes the copier's
  own project)
- A passing preview, and the app's link if they want it published

## Steps

### 1. Get the address

The user gives a URL, or names an app whose address is in this session or in a
folder's `xr-project.json`. Accepted:

- `https://<name>.vercel.app` — the Vercel route
- `https://<owner>.github.io/<repo>/<slug>/` — the Pages route
- an AVNFS / ClassCloud page address — a single-file build

If they only have a QR code, ask them to paste the address it opens, or read
it in the browser pane.

### 2. Fetch the page

- **`*.vercel.app`** → `web_fetch_vercel_url` (the cloud workspace cannot
  reach Vercel directly).
- **anything else** → `WebFetch`, or `curl` from the workspace. `github.io` is
  not reachable from the cloud workspace either; use the browser pane on the
  user's machine (`get_page_text`) or ask them to paste the page.

Save it as `<scratch>/published.html`.

### 3. Work out what kind of page it is

Look for `<meta name="xr-kit-source" content="kit=…; build=…; slug=…;
aframe=…; lib=…">`.

- **Present** → a slim page from the Vercel route. Continue at step 4.
- **Absent, but the page contains `window.KIT = (function`** → a single-file
  build (ClassCloud, Pages, or an older Vercel publish). The source is already
  there: skip to step 6 using this file as `index.html`. If it inlines
  A-Frame, strip nothing — but note the app folder wants A-Frame as a separate
  `aframe.min.js`; `/new-xr-app`'s scaffold provides one, and the page's own
  inline copy can stay. Say in one line that this came from a single-file
  build so the copy may carry a bundled library.
- **Neither** → this is not a kit app. Say so plainly and stop; do not guess.

### 4. Fetch the library the page names

From the meta's `lib` base and `kit` version, fetch four files into
`<scratch>/lib/`:

    <lib>/xr-kit-diary-<kit>.js
    <lib>/xr-kit-<kit>.css
    <lib>/xr-kit-<kit>.js
    <lib>/xr-kit-panel-<kit>.js

Same fetch rule as step 2 (`web_fetch_vercel_url` for `*.vercel.app`). If any
is missing, stop: the library that app was built against is gone, so its
source cannot be rebuilt — offer to start a fresh app from the template
instead.

### 5. Rebuild the source

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-to-vercel/scripts/vercel_build.py \
        --unslim "<scratch>/published.html" --lib-dir "<scratch>/lib" \
        --out "<scratch>/index.html"

It prints the app's name, build number, slug and the A-Frame version it wants.
The result is the original source, with one deliberate difference: the status
panel reads the app's name from the page title rather than carrying it as a
literal. That is normal — do not mention it.

### 6. Make the project folder

Scaffold an empty app to get the right shape, then drop the rebuilt source in:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/new-xr-app/scripts/scaffold.py \
        --name "<name>" --out "<parent folder>"

`<name>` is what the user asked for, else the name the page carries. If a
folder of that name already exists, add " copy" (then " copy 2", …) rather
than overwriting anything.

Replace the scaffolded `index.html` with the rebuilt one, keep
`aframe.min.js`, then fix the manifest:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-xr-app/scripts/manifest.py \
        --project "<folder>" \
        --set build=0 \
        --set dof=<3 or 6, read from the page's `<a-scene xr-kit="dof: N">`> \
        --set forkedFrom='{"url":"<address>","build":<N>,"lib":"<kit>","at":"<today>"}'

Then **clear the original's identity** so a publish creates the copier's own
project — `classcloud.activityId`, `classcloud.lastUrl`, `artifact.url`,
`pages.url`, `vercel.project`, `vercel.projectId`, `vercel.url`,
`vercel.deploymentId`, `vercel.store`, `vercel.owner` all to `null`. A
scaffolded manifest already has them null, so this only matters if a manifest
was copied rather than scaffolded — check, don't assume.

If the page's A-Frame version differs from the bundled one, say so in one line
(the copy uses the kit's bundled version) and carry on.

### 7. Check it runs

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/preview-xr-app/scripts/preview.py \
        --file "<folder>/index.html" --out "<folder>/.preview"

Exit `0` → done. Exit `1` → say what failed in the user's terms; the usual
cause is a library file that did not fetch cleanly, so re-fetch and rebuild
before anything else.

### 8. Hand it over

Deliver the folder's files to the user (Cowork: `SendUserFile`
`display: "attach"`, then `device_commit_files`).

Two sentences: they now have their own copy of `<name>`, they can change it by
asking ("make the ball bigger", "add a sign"), and it is not published
anywhere yet. Then ask once where they want it — their Vercel account, a
ClassCloud QR code for headsets, or nowhere for now — and route to
`/publish-to-vercel`, `/publish-xr-app` or `/share-xr-app` accordingly. Do not
publish without asking: the copy is public the moment it is, and it is not
their app yet in any other sense.

## Attribution and licence

The rebuilt source is the original author's work. Record where it came from
(`forkedFrom`, above) and leave it there; if the user renames the app, keep
the field. If the original carries a `licence` in its manifest or a licence
line in the page, copy it across and say what it is in one line. The kit does
not decide what staff prototypes may be reused for — if the user asks, say it
is an Avantis question, not a technical one.

## What this cannot do

- Rebuild a page that is not a kit app, or one whose library has been taken
  down.
- Reach `github.io` or ClassCloud pages from the cloud workspace — those need
  the browser pane or a paste.
- Give the copier the original's play history or build history; the copy
  starts clean at build 1.
- Change the original in any way. There is no "send my changes back" — the
  copier publishes their own, and the two are separate from then on.
