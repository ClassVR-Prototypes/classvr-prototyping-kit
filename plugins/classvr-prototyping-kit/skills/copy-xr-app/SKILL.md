---
name: copy-xr-app
description: >
  This skill should be used when the user wants their own copy of an XR app
  that someone else published — "copy this app", "make me my own version of
  this", "fork this prototype", "I want to build on this one", "can I edit
  this app someone sent me", "copy version 4 of this", or /copy-xr-app
  followed by a published address (optionally with a version number or a
  /v/N/ address). It takes the address of a kit app published on Vercel,
  rebuilds the app's full source from the
  published page — the current version or any earlier one from the app's
  history — checks its fingerprint, puts it in a new project folder the user
  can edit with ordinary prompts, checks it runs, and offers to publish it as
  their own. Nothing is needed from the person who made the original — no
  files sent, no account shared.
metadata:
  version: "0.8.0"
---

# Copy an XR app

There are two ways to get a copy, and this skill is one of them. The other
needs no chat at all: every Vercel app's history page (`<address>/history`)
has a **Make my own copy** button next to each version, which builds the same
folder in the browser and, in one click, saves it where the person chooses
(Chrome/Edge folder picker) or, in other browsers, as a .zip download. If someone asks how to copy an app themselves, point them there;
if they connect a folder the button made, see "A folder from the history
page" below — it is already a copy and needs no steps from this skill.

A published kit app carries everything needed to rebuild its source: the page
itself is the app minus the kit's plumbing, and the plumbing is a versioned
library at a public address the page names. So an address is enough to hand
someone a working, editable copy.

The copy is the copier's own from that moment: their folder, their build
numbers, their publish. The original is untouched and cannot be affected.

## Outcome

- A new project folder with `index.html`, `aframe.min.js`,
  `xr-project.json`, `README.md` and `CHANGELOG.md`, the same shape
  `/new-xr-app` makes — the README is the original's (what the app is and how
  it works), the changelog is the copy's own with the original's history kept
  under "Before this copy"
- `xr-project.json` carrying `forkedFrom` (the address, build and library it
  came from) and **no** ids from the original (a publish makes the copier's
  own project)
- A passing preview, and the app's link if they want it published

## Steps

### 1. Get the address

The user gives a URL, or names an app whose address is in this session or in a
folder's `xr-project.json`. Accepted:

- `https://<name>.vercel.app` — the Vercel route (current version)
- `https://<name>.vercel.app/v/<N>/` — one particular version of it
- any other address serving a single-file kit build (an older app)

"Version 4 of …", "the one from Tuesday", "the version with the lap counter"
→ the Vercel route with a version. Read `<address>/history.json` (step 2's
browser tab); it lists every version with its number, date, note
and `sha1`. Pick the one they mean (by number, date or note); if it is
ambiguous, show the two or three candidates in a line each and ask which.
Then the page to copy is `<address>/v/<N>/` and its expected fingerprint is
that entry's `sha1`. No `history.json` (404) → an app published before the
kit kept versions; only the current page can be copied — say so in one line
if they asked for an older one.

**A folder instead of an address.** If the person has the app's folder (their
own, or one a colleague gave them) it carries the history too: every
published version sits under `versions/Versions <A> - <B>/<NN>-index.html`
with a `<NN>-README.txt` beside it, and `xr-project.json` → `vercel.versions`
holds the fingerprints. Pick the version there, check it with
`vercel_build.py "<folder>" --local-version <N>` (`ok: true` = the file
matches its fingerprint) and use that file as `published.html` in step 2 —
no download at all. A folder without `versions/` (made before kit 0.26, or
never published to Vercel) → copy its `index.html` as the current version.

If they only have a QR code, ask them to paste the address it opens, or read
it in the browser pane.

### 2. Fetch the page

Vercel addresses are only reachable from Claude's built-in browser (neither
workspace shell can reach them), so every Vercel file comes across through a
browser tab:

1. `preview_start` at the app's address (any page of it, so `fetch()` there is
   same-origin), then for each file `javascript_tool`:
   `var t = await (await fetch('<path>', {cache: 'no-store'})).text();` and
   return `{ length: t.length, sha1: <SHA-1 of t via crypto.subtle>, part: t.slice(i, i + 20000) }`
   — one 20 000-character piece per call, `i` = 0, 20000, 40000, …
2. Write the pieces, joined in order, to the scratch file with the Write tool,
   then check it: `sha1sum` must equal the `sha1` the browser gave. A mismatch
   means a piece was copied wrongly — fetch that file again rather than
   editing it. Files from another address (the shared library) are fetched
   from a tab on that address the same way.
3. Anything not on Vercel → `WebFetch`, or `curl` from the workspace; if the
   workspace can't reach it, the browser tab again, or ask them to paste it.

No built-in browser in this session (Cowork on the web) → say copying needs
the Claude desktop app open, or point them at the app's `/history` page,
whose **Make my own copy** button saves the folder without Claude (see "A
folder from the history page").

Save the page as `<scratch>/published.html`.

### 3. Work out what kind of page it is

Look for `<meta name="xr-kit-source" content="kit=…; build=…; slug=…;
aframe=…; lib=…">`.

- **Present** → a slim page from the Vercel route. Continue at step 4.
- **Absent, but the page contains `window.KIT = (function`** → a single-file
  build (an older Vercel publish, or an older app). The source is already
  there: skip to step 6 using this file as `index.html` — but first take the
  README and changelog out of it (step 5b). If it inlines
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

Same fetch rule as step 2 (a tab on `<lib>`, pieces, sha1 check). If any
is missing, stop: the library that app was built against is gone, so its
source cannot be rebuilt — offer to start a fresh app from the template
instead.

### 5. Rebuild the source

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-to-vercel/scripts/vercel_build.py \
        --unslim "<scratch>/published.html" --lib-dir "<scratch>/lib" \
        --out "<scratch>/index.html" --as-copy [--expect-sha1 <sha1 from history.json>]

Pass `--expect-sha1` whenever `history.json` gave one (for the current
version too: its entry is the one numbered `current`). It refuses a page
whose fingerprint does not match — fetch again rather than copying something
unverified. It prints the app's name, build number, slug, the A-Frame version
it wants, and `publishedSha1` / `fingerprint` (the first eight characters) of
the page it rebuilt from.
The result is the original source, with one deliberate difference: the status
panel reads the app's name from the page title rather than carrying it as a
literal. That is normal — do not mention it.

It also writes the page's `README.md` and `CHANGELOG.md` beside `--out`
(`docsWritten`), and leaves them out of the rebuilt `index.html`.

### 5b. The README and changelog

Every page published with kit 0.32 or later carries both inside it.

- **Vercel slim page** → step 5 already wrote them into `<scratch>/`.
- **Single-file build** (step 3, second case) →

      python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-to-vercel/scripts/appdocs.py extract \
          "<scratch>/published.html" --to "<scratch>" --strip-into "<scratch>/index.html"

  and use `<scratch>/index.html` as the source in step 6.
- **Neither** (published before 0.32) → nothing to copy; step 6 creates fresh
  ones and you rewrite the README from what the app does.

### 6. Make the project folder

Scaffold an empty app to get the right shape, then drop the rebuilt source in:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/new-xr-app/scripts/scaffold.py \
        --name "<name>" --out "<parent folder>"

`<name>` is what the user asked for, else the name the page carries. If a
folder of that name already exists, add " copy" (then " copy 2", …) rather
than overwriting anything.

Replace the scaffolded `index.html` with the rebuilt one, keep
`aframe.min.js`. Replace the scaffolded `README.md` and `CHANGELOG.md` with the
original's when step 5b found them, then make the changelog the copy's own:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-to-vercel/scripts/appdocs.py fork "<folder>" \
        --url "<address, without /v/N/>" --version <N> --fingerprint <publishedSha1> --name "<original name>"

Its Unreleased section now says which version of which address the copy was
made from (that line becomes the copy's version 1 when it is published), and
the original's history — up to the version copied — sits under "Before this
copy" with its headings a level down, so it never clashes with the copy's own
version numbers. If the person renames the copy, change the README's title to
match; leave the rest of the README as the original wrote it.

Then fix the manifest:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-to-vercel/scripts/manifest.py \
        --project "<folder>" \
        --set build=1 \
        --set dof=<3 or 6, read from the page's `<a-scene xr-kit="dof: N">`> \
        --set forkedFrom='{"url":"<address>","version":<N>,"sha1":"<publishedSha1>","lib":"<kit>","at":"<today>"}'

Then **clear the original's identity** so a publish creates the copier's own
project — `vercel.project`, `vercel.projectId`, `vercel.url`,
`vercel.deploymentId`, `vercel.store`, `vercel.owner` all to `null`. A
scaffolded manifest already has them null, so this only matters if a manifest
was copied rather than scaffolded — check, don't assume. Any other hosting
blocks an older manifest carries (anything but `vercel`) can simply be
removed.

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
anywhere yet. Then ask once whether to put it on their Vercel account (which
also gives the headset QR code) or leave it unpublished for now — and route
to `/publish-to-vercel`. Do not
publish without asking: the copy is public the moment it is, and it is not
their app yet in any other sense.

## A folder from the history page

A folder made by the history page's **Make my own copy** button has the same
files and the same shape as one this skill makes — the button runs the same
rebuild in the browser, checked against this skill's output byte for byte —
with `forkedFrom.via: "history page"` in `xr-project.json`. When someone
connects one and asks for a change, just carry on (`xr-app-rules`). The first
time, run the preview check before editing, and if `aframe.min.js` is missing
(the browser could not reach the site it comes from), put the kit's own copy
in: `${CLAUDE_PLUGIN_ROOT}/skills/new-xr-app/assets/aframe.min.js`. Don't
mention either unless the preview fails. The folder's name ends in "copy" (or
"copy 2", …); if the person wants it called something else, rename the app
(`name`, `slug`, the page `<title>` and the README title) when they say so.

## Attribution and licence

The rebuilt source is the original author's work. Record where it came from
(`forkedFrom`, above) and leave it there; if the user renames the app, keep
the field. When the copy is published to Vercel, its own `history.json`
carries a `copiedFrom` line (address, version and fingerprint — no names)
taken from that field; it is recorded, not displayed on the history page,
and Claude can answer "where did this come from?" from it. The copy's
changelog also says it, in its first line (address, version and fingerprint —
no names), and keeps the original's history under "Before this copy". If the original carries a `licence` in its manifest or a licence
line in the page, copy it across and say what it is in one line. The kit does
not decide what staff prototypes may be reused for — if the user asks, say it
is an Avantis question, not a technical one.

## What this cannot do

- Rebuild a page that is not a kit app, or one whose library has been taken
  down.
- Give the copier the original's play history or its playable old versions;
  the copy starts at version 1 (with `copiedFrom` recording which version of
  the original it began as). The original's changelog does come across, as
  text, under "Before this copy".
- Change the original in any way. There is no "send my changes back" — the
  copier publishes their own, and the two are separate from then on.
