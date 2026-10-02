---
name: publish-to-vercel
description: >
  This skill should be used when the user asks to "publish my XR app", "put it
  on the headset", "send it to the headsets", "give me the QR code", "share my
  XR app", "give me a link to the app", "refresh the link", "host it on
  Vercel", "publish to Vercel", or invokes /publish-to-vercel. It is how every
  kit app is published, run at the end of /new-xr-app and after every edit so
  the link is never behind the folder. It builds a slim page that loads the
  kit's shared library, deploys it with the person's own Vercel token,
  verifies it live at a stable public URL whose page shows its own
  headset QR code, and keeps the app's play history. Every publish is a saved
  version: also use for "show me the versions", "what changed in version 4",
  "go back to version 4", "call this version …" and "what's the fingerprint of
  this version".
metadata:
  version: "0.15.2"
---

# Publish to Vercel

The Vercel route for a kit app. The app's own `index.html` is left as it is;
`vercel_build.py` turns it into a **slim page** (a few KB) that loads the kit's
plumbing from a hosted, versioned **shared library** and A-Frame from aframe.io.
The page also loads the library's `kit-relay-<kit>.js`, which posts the app's
diary to `/api/log` in the app's own project; that function prints each post into the project's runtime
log and keeps one copy of each session in the
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

This is **the only way a kit app is published**, and it is how an app gets
onto a headset: the page's own QR code. An app with no `vercel.url` yet gets
its project on its first publish. Any other fields an older `xr-project.json`
carries are ignored.

## Outcome

- The app live at a stable public URL `https://<project>.vercel.app`, where
  `<project>` is `classvr-<app>-<vercel username>` for apps first published
  with kit 0.27 or later (see step 2)
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

## Before starting — how the kit talks to Vercel

One way only: the person's own **Vercel token**, used from Claude's built-in
browser. The person connects their account once with `/connect-vercel` (they
make a token in Vercel and paste it into a box in the browser — never into
the chat); the browser keeps it, so they are not asked again. Every call to
Vercel goes through the **Vercel bridge** (`window.KV`) on a tab at
`https://api.vercel.com/v2/user`. The kit never uses a Vercel connector or any
Vercel tool, even if one happens to be installed.

Nothing is assembled by hand: the scripts below write the whole browser side
of each step as one piece of JavaScript, **with the part of the bridge that
step needs written out in it** — nothing is fetched and run from elsewhere in
the tab that holds the token, so everything that runs there can be read in
the script itself. (Kit 0.39.0 downloaded the bridge from the shared library
instead; a fresh session's permission check refused that, rightly — never
bring that back.) The workspace side is one script too,
`publish_prep.py`, which prints the browser script at the end of its output
between `----- browser script … -----` marker lines. Copy the text between the
markers into the browser step **unchanged**, never edited. If the output is
cut short, `Read` the file the marker line names (`<scratch>/deploy.js`,
`<scratch>/kitcheck.js`) instead.

No built-in browser in this session (Cowork on the web, or the desktop app
closed) → stop and say: "Publishing needs the Claude desktop app open on your
computer — open it and ask me again." Vercel can only be reached from that
browser; the workspace's own shells cannot reach it.

A browser script **throws when something is wrong**, so a browser batch stops
at that step; the error text says which case it is:

| Error starts with | Meaning → what to do |
|---|---|
| `not-connected` | no token stored (the check was skipped, or the browser was cleared mid-job) → `/connect-vercel`'s setup script, then run the same batch again |
| `publish failed: … "status":401` / `403` | the token was refused (expired, deleted) → `/connect-vercel`, then again |
| `library-missing` | this kit version's shared library is not hosted yet → "Hosting the library" below, then again |
| `publish failed: … "stage":"check"` | a copying slip — the script text changed on the way; run the same step again with the text exactly as printed |
| `publish failed: … "missingFiles":[…]` | Vercel does not hold those older versions' bytes → run `build` again with `--inline <file>` for each and repeat |
| `address missing` / `prepare failed: … "stage":"address"` | the name is taken worldwide → run `prepare` again with `--suffix 2` (then 3, …) |
| `live check failed` | the page went up but is wrong: the `problems` list says what → say so, fix, publish again before giving the link |
| a permission check refuses a script | say so plainly and stop; never look for another route around it |

## Steps

**Progress updates.** A publish takes a couple of
minutes. Run on its own ("publish my app", "go back to version 2"), send
**2–3** plain progress updates following `${CLAUDE_PLUGIN_ROOT}/skills/new-xr-app/references/progress-updates.md` (read it first; each one a
`SendUserMessage` call, made alongside the step's own first call): a starting
update once the check says connected, **uploading to Vercel** with step 4's deploy,
and optionally the **live check** with the live check. For example:
"Uploading <app> to Vercel", "It's on Vercel. Opening the live link to check
it works there". When
this runs as the end of `/new-xr-app` or an edit, that job sends the upload
and live-check updates as part of its own count — none extra here. Problems the person must know about are said plainly.

A publish is **five calls** after the first (seven on a first publish). Use a
fresh scratch folder for each publish — `<scratch>` below, e.g.
`/tmp/publish-<slug>-<time>` — and set `P=${CLAUDE_PLUGIN_ROOT}/skills/publish-to-vercel/scripts`.

### Before step 0 — the Vercel connection

Run `/connect-vercel`'s **The check** before anything else in the job —
unless `/new-xr-app` or an edit already ran it this turn. Connected → say nothing
about Vercel. Not connected → its setup script runs now, word for word, and the
publish resumes after its message **F**, then the starting update. Never start staging or building
first and discover the missing connection later.

### 0. If the app does not exist yet

The request created the app ("make a VR app called Bubble Pop"). `/new-xr-app`
runs its steps 1–6 as written and hands over here at its step 7 with the
project files already delivered and the preview already passed.
Continue from step 1 and add `--no-preview` to the first `publish_prep.py`
call (`prepare`), since the check just passed. Never ask a question `/new-xr-app` would not ask.

### 1. Stage the app — one call

Stage the app folder's `index.html`, `xr-project.json`, `README.md`,
`CHANGELOG.md`, `aframe.min.js` and every other local `<script src="./…">` in
**one** `device_stage_files` call (the `versions/` folder is not needed).
They land read-only under `/mnt/user-data/uploads/<folder>/…`; that folder is
`<staged>` below. The scripts copy it into `<scratch>/app` and work there.

**Skip this call** when the workspace already holds the app exactly as it is
in the person's folder — you just made or edited it there this turn and
delivered it: use that folder as `<staged>`.

### 2. First publish only: make the project — two calls

An app with no `vercel.url` in `xr-project.json` has no project yet. It needs
its real address **before** the build, so the page's QR code is right from
the first deploy:

    python3 $P/publish_prep.py prepare --from "<staged>" --scratch <scratch>

This checks the app runs (below), sets the version number and prints the
browser script. Then one browser batch:
`navigate` to `https://api.vercel.com/v2/user`, then `javascript_tool` with
the printed script. It names the project `classvr-<slug>-<vercel username>`
(shortened to fit if long), creates it, reads the address Vercel really gave
it (Vercel shortens long names — never assume `<name>.vercel.app`), and
creates the app's play-history store — all in one go, so the first deploy is
the only deploy. Keep its result (one line of JSON) for step 3. Its `store`
part says whether the store was made; if not (the Hobby 100-store limit, say),
tell the person in one line that plays of this app won't be kept for "what
happened on the headset?", and carry on — nothing else breaks.

Never ask the person to choose a name.

### 3. Build — one call

    python3 $P/publish_prep.py build --from "<staged>" --scratch <scratch> \
        [--prepared '<step 2 result>' --owner "<user's email>"]      # first publish only
        [--note "<their words>"]

One call does all of this, and stops (exit 1, `stop` says why, in words to
turn into the person's terms) the moment something is wrong:

- **Checks the app runs** in a headless browser (the same check as
  `/preview-xr-app`, skipped when `prepare` just did it or with
  `--no-preview`). A failing app is never published — a broken build must
  never replace a working page: say what failed in the user's terms, fix it
  in the app folder, and start again from step 1.
- **Sets the version number** — only goes up if the source changed. Source
  unchanged and the person expected a change → say so; otherwise there is
  nothing new to publish.
- **Builds the slim page, library and history** (below).
- **Writes the browser scripts** and prints them.

Its summary gives `version`, `note` (the history's one-line "what changed"),
`fingerprint`, `url`, and `warning` if the changelog had no line for this
version — then add a real line with `appdocs.py add` in the app folder and
start again rather than publish a placeholder.

**The version note** comes from the changelog: the lines under
`## [Unreleased]` in `CHANGELOG.md` (written during the edit — see
`xr-app-rules`, "README and changelog") become this version's section, and
that section becomes the note. Pass `--note` only when the person said "call
this version …" or "note it as …" (use their words exactly), or for an app
with no `CHANGELOG.md`. No names, no dates in the note or the changelog — the
build adds the date, and everything published carries no names by design.

What the build makes (you rarely need this): the app's own `index.html` is
left as it is; the **slim page** loads the kit's plumbing from the shared
library `https://xr-kit-lib-<kit>.vercel.app` (`<kit>` = 12-hex hash of the
plumbing, so every app from the same template shares it) and A-Frame from
aframe.io. The README and changelog go inside the page (so every `/v/<N>/`
and every copy carries its own); `/about/` and `/history` are redirects to
the library's readers, so neither travels with a publish. The deploy set is
`index.html` (its `/v/<N>/` address is a rewrite to it), `history.json`,
`vercel.json`, `api/log.js`, `api/reports.js`, `package.json` and every older
`v/<M>/index.html` **by fingerprint** — Vercel already holds those bytes.
Only the page, `history.json` and `vercel.json` are sent inline. If Vercel
does not hold a support file yet (a new account, a kit update), the bridge
uploads it from the library's copy by itself. The build also records this
version in `xr-project.json` (`vercel.versions`), keeps the page as
`versions/Versions <A> - <B>/<NN>-index.html` plus `<NN>-README.txt`, links
each changelog version to its `/v/<N>/` address, and writes any `\uXXXX`
escape for a character above U+007F as the plain character (the upload
would do that on its own and break the fingerprint). If a publish ever
reports a fingerprint mismatch anyway, start again from step 1; never
hand-edit the page or the recorded fingerprint. `--no-relay` / `--indexable`
on `vercel_build.py` exist but are never the default.

An app that bundles an extra library (`cannon.iife.js`) stops here with
`this app uses an extra library that cannot be published yet` — say so
plainly: it can't be put on a headset for now.

### 4. Deploy and check it live — one call

One browser batch, five steps (or the same five as separate calls, one after
another — either is fine; separate calls avoid escaping a long script twice):

1. `navigate` → `https://api.vercel.com/v2/user`
2. `javascript_tool` → the printed **browser script** (deploys the complete
   file set as a production deploy and waits until the address serves the
   new version)
3. `navigate` → the summary's `kitcheckUrl` (`<url>/?kitcheck`)
4. `javascript_tool` → the printed **live check** (on the app's own page, no
   token involved: right version, the scene loads, the Enter VR button is
   there, no errors, self-checks pass, the library files and the QR address
   are right, `/v/<N>/` is the same page, `history.json` lists every version,
   one older version still plays, `/history` and `/about/` redirect). It leaves out the
   "player can walk forward" self-check, which can't pass in the pane
   (synthetic keys); step 3 covered it. A **hidden browser panel** draws no
   frames, so in-scene self-checks fail there (even the kit's own): the live
   check runs failed checks once more if the page is visible now, and skips
   them (`selfChecks` says so) if it is still hidden — never ask the person to
   show the panel for this. Keep the app's tab in front (`tabs_select`) before
   the live check so the second run can draw.
5. `navigate` → the summary's `url` (the plain link). Always — if the batch
   stopped at a failed live check, make this call on its own. On `?kitcheck` the self-checks run by themselves 2.5 s
   after load — they walk the player forward and play the app — so a person
   who looks at or reloads that tab sees the rig slide and the game play
   itself. The live check also takes `?kitcheck` off the address once it has
   run, but the fresh load is what leaves the app as a player finds it.

Step 2's result has `id`, `projectId`, `teamId` and `live`. Always
`production` (preview deploys sit behind a Vercel login a headset cannot
open), always the complete file set (a deploy replaces everything; a file
left out is gone from the live site) — the script does both. The public
address is the one step 2 of a first publish returned; never hand out the
team-suffixed alias (`<project>-<team>.vercel.app`, which answers "401
Protected deployment") or a per-deployment URL.

### 5. Record and write back — two calls

    python3 $P/publish_prep.py record --scratch <scratch> --result '<the deploy script's result (step 4.2)>' \
        --outputs /mnt/user-data/outputs/<app folder name>

It records the publish in `xr-project.json` (`vercel.deploymentId`,
`vercel.build`, `vercel.lib`, `vercel.teamId`, `vercel.via`; a first publish
already has `vercel.project`, `projectId`, `url`, `store` and `owner` from
step 3) and copies **every file that changed** into `--outputs`. Then **one**
`device_commit_files` call with every entry of its `commit` list:
`stagedPath` as given, `devicePath` = the app folder on the person's computer
+ `relative`. That is always `xr-project.json`, `CHANGELOG.md` and the two
new files under `versions/`; also `index.html` when the version went up.

### 6. No QR image

The page draws its own QR code in its top-right corner, so **do not make or
render a QR image** for the chat or the folder (a `vercel-qr.png` left in an
app folder by an older kit is harmless; leave it). Only if the person asks for
a code to print or put on a slide:

    python3 $P/make_qr.py --url "<vercel.url>/" --out "<scratch>/vercel-qr.png"

and send it (`SendUserFile`, then `device_commit_files` beside the app).

### 7. Report

Nothing is rendered: **the URL is the last line of the reply, on its own
line**, so the person can click it straight away.

This is the closing reply, not a progress update. One or two sentences, in the kit's voice: the app name, that **version N** is
live ("saved as version 3 — added a lap counter"), open the address in any
browser; for a headset, click the QR code in the page's top-right corner to
enlarge it, scan it with the ClassVR scanner and press the VR button. First
publish only: "the page is public — anyone with the address can open it" (it
is kept out of search engines, but that is not worth saying unless asked),
and mention once that every version is kept and `<url>/history` lists them.
Do not explain Vercel, the library, manifests, fingerprints or build numbers
unless asked. Say "version", not "build", to the person — they are the same
number.

## Hosting the library (one-time per kit release)

The shared library is **shared by everyone** — its address is one worldwide
name, so the first account to host a kit version serves it to every app built
with that version. The kit's maintainers host each release's library under
the Avantis account when they ship it, so a staff member normally never
does this; it is here for a release that was missed (`library-missing`).
Say in one line that this is a one-time step for this kit version, then:

1. `python3 $P/vercel_payload.py <scratch>/lib-only --lib --by-sha --inline index.html --out <scratch>/lib-deploy.js`
   (`lib-only` is written by `prepare`; for an app already on Vercel run
   `python3 $P/vercel_build.py <scratch>/app --out <scratch>/lib-only --library-only`),
   read it and run it on a tab at `https://api.vercel.com/v2/user` (it
   carries its own bridge). Files unchanged since the last release go by
   fingerprint, so little is typed. `library deploy failed: … "missingFiles":[…]` → run it again with
   `--inline <file>` for each. It then reads every hosted file back and
   compares its SHA-256 with the manifest: `mismatched` must be empty
   (anything else → redeploy with that file `--inline`). Never point apps at
   an unverified library.
2. Never redeploy an existing `xr-kit-lib-<kit>` project with different
   content: a Vercel deploy replaces a project's whole file set, and other
   apps depend on it. A new template version gets a new project — that is
   what the hash in the name is for.

Then carry on with the publish (run the same browser batch again).

## Showing the history

"Show me the versions", "what changed in version 4", "when did I add the
sign", "which version is on the headset" — read `<vercel.url>/history.json`
(in a browser tab; it is public and tiny, so this works for **any**
kit app on Vercel, not only the person's own). Answer in a sentence or a
short list: version number, date, note; add the fingerprint (first eight
characters) only when two people need to be sure they mean the same one.
Point them at `<vercel.url>/history` if they want to look or click through.
For more than the one-line note ("what exactly changed in version 4", "what
is this app", "how do I play it"), read the folder's own `CHANGELOG.md` /
`README.md`, or for someone else's app `<vercel.url>/about/` (every
`/v/<N>/` page also carries both inside it), and answer from those;
`<vercel.url>/about/` is the readable page to send someone.

The history page also has a **Make my own copy** button next to every
version: one click saves that version as an app folder (Chrome/Edge open a
folder picker; other browsers download a .zip) that they add to a Cowork task —
the same result as `/copy-xr-app`, without a chat. Mention it when someone
asks how others can build on their app. It needs the app's history page to
be on kit 0.33 or later, i.e. one publish after the kit update.
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
2. Stage the app as in step 1, **plus** `versions/Versions <A> - <B>/<MM>-index.html`
   (`<A>` = the multiple of ten below M plus one), and copy it to the
   scratch folder: `python3 $P/publish_prep.py take --from "<staged>" --scratch <scratch>`.
   **Look in the app folder first** — this is the normal case and needs no
   download:

       python3 $P/vercel_build.py "<scratch>/app" --local-version <M>

   `ok: true` → `path` is the kept page and its fingerprint matches what was
   recorded at publish time; use it as `<restore page>` below. `ok: false`
   → the file is missing or was altered: say so in half a sentence and fall
   back to the live address: read `<vercel.url>/v/<M>/index.html` in a
   browser tab (`fetch()` there, text), saved as `<scratch>/restore.html`.
   Either way, the four library files the page names (`/copy-xr-app` step 4
   lists them) go into `<scratch>/lib/`: `python3 $P/vercel_build.py
   "<scratch>/app" --out <scratch>/lib-only --library-only` writes them to
   `<scratch>/lib-only/lib/` when the kit version matches.
3. Rebuild the source and put it in place of the app's `index.html`:

       python3 $P/vercel_build.py \
           --unslim "<restore page>" --lib-dir "<scratch>/lib" \
           --out "<scratch>/app/index.html" --expect-sha1 <that version's sha1 from vercel.versions> \
           --docs readme

   `--expect-sha1` refuses a page that does not match the history — fetch
   again rather than restoring something unverified. `--docs readme` puts
   back that version's README (it describes what is now live) but keeps the
   current changelog, which is a straight line and never goes backwards.
   Then record the restore in it:

       python3 $P/appdocs.py add "<scratch>/app" \
           --category Changed --entry "Put version <M> back (<its note>)."

   (No `CHANGELOG.md` yet — an app from before kit 0.32 — → `appdocs.py init`
   with the same entry.)
4. Steps 3–7 as normal, with `build --scratch <scratch> --restored-from <M>`
   (no `--from`: the app is already in the scratch folder). The result is a **new** version (N+1) whose page is identical
   to version M apart from its number; the history page tags it "restored
   from version M". `record` writes the restored `index.html` back too.
   Versions between M and N stay in the history — say so:
   "version 4 is back on the headset, as version 7; 5 and 6 are still there
   if you want them."

Never use Vercel's own rollback for this: it is Pro-only for arbitrary
versions, it pins the address until a promote, and it hides what happened
from the history. If a very recent publish is *broken* and speed matters, restoring
the previous version this way still takes under a minute.

## Reading what happened (debugging on this route)

Whenever the user asks what went wrong, whether it worked, what happened on
the headset, or before fixing a bug someone reported — for an app with
`vercel.url` — read the diary **from Vercel first**; it is the same for a
headset, a desktop browser and a shared link, and arrives within seconds of
the play (`/check-headset` does this itself when it sees `vercel.url`).

The diary of every play is kept in the app's own history (every session is
written when the player leaves VR or closes the page). Read it in a browser
tab — it is public, so no token is needed:

    <vercel.url>/api/reports                    one line per session, newest first
    <vercel.url>/api/reports?day=2026-09-21     one day
    <vercel.url>/api/reports?session=<id>       that session in full

If the player is still in VR, ask them to press the VR button to come out,
then read it again. Each diary entry is `[i, t, kind, text, code?]` and
includes everything the app printed; `ua` says which device (`Android …
Mobile VR` is the headset, a desktop user agent is a browser).

The summary carries app, build, when, seconds, state, whether VR was entered,
fps, controllers, presses, errors, flags, first error code and the device;
`?session=` adds every diary entry, the error list, the flags and the
self-check results. `{"ok":false,"reason":"no history store…"}` means the app
was published without one (an old app, or the store limit was reached) — say
so and offer to add it: one bridge call, `await KV.createStore("<first 24
characters of the project name>-history", "<prj_…>")`, record `vercel.store`,
then publish again.

Then tell the story exactly as `/check-headset` step 6 describes (build,
entered VR, errors first with their codes and lines, the seconds before a
flag, or the numbers that show it ran well). Ignore a `flag` post whose `d`
ends in `PASS the "something wrong" marker works` — that is the self-check
pressing F during `?kitcheck`, not a person.

Nothing there → the session is still running (ask them to leave VR),
or the page never ran its first script — the history cannot see that; ask
what the headset showed. Error codes: an error in the app's own code keeps its `<build>-<line>`
code with the line counted in the slim page (open `dist-vercel/page/index.html`
from the build, or rebuild it); an error inside the shared library is coded
`<build>-lib`.

## When this runs on its own

- **After any edit to an app** (`xr-app-rules` ends every edit here), so the
  Vercel page never lags the folder. Source unchanged (not bumped) → nothing to publish; say so
  only if the user expected a change.
- **End of `/new-xr-app`**: `/new-xr-app` 1–6, then this skill 1–7 in one
  turn (with `--no-preview`); the link is the last line.

## Known limits

- Extra bundled libraries (`cannon.iife.js`) are not hosted yet — step 3
  stops with a plain message.
- The on-page QR code arrives with an app's next publish; versions published
  before kit 0.27 (older `/v/<N>/` pages) do not have it, and never will —
  their bytes are kept exactly as published.
- On a narrow window (under 700 px wide or 520 px tall) the card shrinks to a
  96 px code that is too small to scan off a screen; click it to fill the
  screen first.
- Vercel's free Hobby plan is for non-commercial personal use (100 deploys a
  day); staff use belongs on a Pro team. The play history lives in Blob
  storage, within Hobby's 1 GB and ~2,000 stored sessions a month.
- Publishing needs the Claude desktop app open: Vercel is only reachable from
  its built-in browser, where the token is kept. A session with no built-in
  browser (Cowork on the web) cannot publish.
- A session only reaches the history once the player leaves VR or closes the
  page; one still in progress can't be read yet.
- Anyone who knows the address can post to `/api/log` and read `/api/reports`
  (the page is public); the diary carries no personal data by construction.
- Everyone publishing needs their own Vercel account, and Vercel accounts are
  16+ — this route is for staff. Pupils need no account: they open the
  published page from its QR code.
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
