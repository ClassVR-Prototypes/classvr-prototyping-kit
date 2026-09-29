# ClassVR Prototyping Kit

Build a WebXR prototype and get it onto a ClassVR headset without a terminal, a
server, a certificate, or a single command typed by hand.

Things you can say:

| You say | What happens |
|---|---|
| **"Make a new VR app called Planet Walk"** (`/new-xr-app`) | A folder appears with a working scene — checked green ground, blue sky, a VR rig with controllers, thumbstick movement and snap-turn — and the app is published straight to its own permanent Vercel link (the first time, you connect your Vercel account). Right-click and drag to look around, left-click presses; WASD moves, Q/E turn. If the name sounds like a game ("Bubble Pop") and you didn't say what it does, you're offered a few concepts — or the empty scene — and the one you pick is built as a first playable version. |
| **"Put it on the headset"** / **"Share it"** / **"Refresh the link"** (`/publish-to-vercel`) | How every app is published, and it runs by itself after every edit so the link is never behind — connect your Vercel account once (**"connect my Vercel account"**, `/connect-vercel`: you make a token in Vercel and paste it into a box in Claude's browser; no connector needed): the app is rebuilt as a small page that loads the kit's plumbing from a shared, versioned library, deployed to `https://<app>.vercel.app` from Claude's built-in browser with your token — no upload screen — verified live, and you get the link — the page shows its own QR code in the corner for a headset to scan. Enter VR works on a headset; updates are live in seconds; the page is kept out of search engines; and the app sends its diary to the same project, so "what went wrong?" is answered in seconds whether it was played on a headset, a desktop or a shared link — for weeks afterwards, not just the past hour. Say it when you create the app ("…hosted on Vercel") or any time after. **Every publish is a saved version**: `<app>.vercel.app/history` lists them all with a one-line note each, every one stays playable at `/v/<N>/`, "show me the versions" reads the list, and "go back to version 4" puts it back as a new version — nothing is ever lost. Each version is also kept in the app's own folder (`versions/Versions 1 - 10/04-index.html`, with a short README beside it), so going back needs no download and the history travels with the folder. |
| **"Make me my own copy of this"** (`/copy-xr-app`) | Give it the address of any published kit app — yours or a colleague's, the current version or "version 4" from its history — and you get the whole thing as an editable project in your own folder, fingerprint-checked and ready to change. Nothing is needed from whoever made it: no files sent, no shared account. Your copy is yours; the original is untouched. |
| **"Show me"** (`/preview-xr-app`) | The app is loaded in a headless browser and checked for errors. You get a screenshot and a one-line health report. |
| **"What happened on the headset?"** (`/check-headset`) | After a play — on a headset or in a browser — reads the app's own play history on Vercel and says in plain words what happened: version, VR or not, errors with their codes, moments the player flagged, frame rate. |

Everything in between — "add a table", "make the ball bounce", "put a sign up" —
is just conversation. One more skill, `xr-app-rules`, loads automatically while
an app is being edited and quietly applies the constraints that keep it working
on a headset.

## What's inside

```
skills/
  new-xr-app/        scaffold a project; bundles A-Frame 1.7.1 and cannon-es
  preview-xr-app/    headless load + error check + screenshot
  connect-vercel/    make a Vercel token, paste it into a box in the built-in browser; kept there, never in the chat
    assets/vercel-bridge.js          window.KV: every Vercel call (deploy, projects, stores) from an api.vercel.com tab
  publish-to-vercel/ build a slim page + shared library → deploy with the token (or the connector) → link
    scripts/build.py, appdocs.py,    shared by every skill: build number + reference single file, README/CHANGELOG,
      manifest.py, make_qr.py        xr-project.json edits, a printable QR code
    scripts/vercel_payload.py        writes the one KV.deploy(...) call for a build, fingerprints included
    scripts/vercel_build.py          extracts the kit's plumbing into versioned library files (plus the relay, the
                                     QR script and one history viewer for every app); writes history.json and
                                     v/<N>/ for every version, /history redirects to the viewer; --unslim puts it back
    assets/kit-relay.js, api-log.js  the diary relay (hosted in the library): page → /api/log → runtime log + Blob
    assets/api-reports.js            the same diary kept per session, readable weeks later
  copy-xr-app/       rebuild an app's source from its published address into a new project folder
  check-headset/     after a play: read the app's play history on Vercel and tell the story
  xr-app-rules/      the constraints, applied on every edit
    references/classvr-xcelerate.md   the target headset and its Wolvic build: specs, behaviour, gaps
```

The kit also carries one **hook** (`hooks/hooks.json`). At the start of every
session, `hooks/voice.md` is read into Claude's context: a short description of
who the person is and how to talk to them — plain English, outcomes rather than
steps, no file paths or error text, and the kit's rules followed quietly rather
than reported on.

Each skill carries the scripts it needs (`scaffold.py`, `build.py`,
`preview.py`, `vercel_build.py`, `vercel_payload.py`, `make_qr.py`,
`manifest.py`, `appdocs.py`). Claude runs them; you never see them. Every
project has an `xr-project.json` manifest recording its build number and its
Vercel address and versions, which is what makes re-publishing an
update rather than a duplicate.

## Requirements

- **A Vercel account**, connected once with `/connect-vercel` (a token pasted
  into Claude's built-in browser; no connector needed), and the Claude desktop
  app open when publishing.
- **A connected folder** for projects to be created in.
- Python 3 in the session environment (present in Claude Cowork). The preview
  step additionally needs Playwright with Chromium; if it isn't available the
  publish step proceeds but says the build was not verified.

No CDN access is required, anywhere. Libraries ship inside the plugin.

## Design decisions, briefly

**Libraries are bundled, never linked.** A wrong CDN path fails silently and the
page still looks like a working app. Bundling also survives school network
filtering; on Vercel the kit's own shared library and A-Frame are loaded from
fixed, versioned addresses.

**A name that sounds like a game gets a concept question; anything else gets the
empty scene.** "Make a new app called Fruit Slicer" is a brief with the gameplay
left implicit, so the kit offers two or three distinct takes on it plus "just
the empty starter scene", and builds the chosen one as a minimal playable slice:
one core interaction working end to end, a visible goal, and a reset — nothing
more. If you described the gameplay yourself, no question. If there is no name,
or it's a placeholder ("Test", "Demo") or doesn't imply an activity, no
question either — you get the starter scene and add things with later prompts.
A wrong guess costs a dialog; the empty scene costs nothing, so doubt resolves
toward the empty scene. The chosen concept is recorded in `xr-project.json`.

**The build number increments itself.** The build script hashes the source with
the version line masked out; a real change bumps the number, a no-op rebuild
doesn't. It shows on the app's panel, in the history and in the filename,
so "is the headset running my newest code?" is always answerable.

**The status panel is for the person holding the headset.** It shows the app
name, build number, readiness checks and controls — nothing else. Developer
diagnostics (controller connections, input counts, colour mode, a session
summary on leaving VR) go to the console tagged `[xr-kit]`, readable in browser
devtools or on the headset with `adb logcat | grep xr-kit`.

**The app lives on a link, not in a file.** Every app is put on a link the
moment it is created, and the link is updated after every edit. It never
changes, so a colleague who has it just reloads; the build number on the panel
says which version they're looking at. The link is the app's Vercel address
(`https://<app>.vercel.app`): a plain public web page that opens on a desktop
*and* enters VR on a headset, live in seconds, with a QR code of its own
address in the corner — pointing the headset's scanner at any screen showing
the app is all it takes — and every publish kept as a version.

**One thing on screen per turn, and it's the thing you need next.** Create or
edit an app and the turn ends on the link, on its own line — the page itself
carries the QR code for the headset. Ask for a preview and you get the
screenshot. Project files are attached as files, not rendered.

**Publish refuses to ship a broken build.** The preview check runs first and a
failure stops the publish.

**The colour fix is built in and not adjustable.** Wolvic double-encodes sRGB in
immersive mode; the kit emits linear output while immersed and standard sRGB on
a flat screen, so the same file shows the same pastels on a monitor and in the
headset. The switch happens *before* the XR session is created — three.js
freezes the framebuffer's colour space at that moment, so switching on
`enter-vr` is too late and looks like the fix isn't there at all. There is no
setting for this; it is plumbing, not a preference.

**Every app is designed for 6DoF or 3DoF headsets — one flag, not two
kits.** `xr-project.json` carries `"dof": 6 | 3` and `<a-scene xr-kit="dof: N">`
mirrors it; `/new-xr-app` infers it from the request or asks alongside the
concept question, and `scaffold.py --retarget` flips an existing app. ClassVR's
browser only runs on 6DoF headsets, so a 3DoF app is *simulated*: the headset
reports a full pose every frame and three.js writes it onto the camera, which
cannot be switched off — so the kit cancels the translation. Each frame, after
the pose is read and before the frame is drawn, the `#tracking` entity (between
`#rig` and the head and hands) is moved by the opposite of the reported
position — that was the 0.13 design, and it was wrong in a way no number
could show.

**How the 3DoF lock really works (0.15, settled on a ClassVR headset 9 Sep
2026).** `xr-kit` wraps `renderer.xr.getCamera()`. three.js calls it once per
frame inside `render()`, after it has written the frame's pose into the eye
cameras and before anything is drawn; the wrapper recomposes each eye camera's
`matrixWorld` (and the array camera's) at a fixed point 1.6 m above the rig,
keeps its rotation, refreshes `matrixWorldInverse`, and moves the user camera
the same way so the gaze cursor aims from the locked point. Each eye keeps its
real offset from the midpoint of the two, so stereo depth is intact. A `give`
of 0.3 of the real head movement (from where the head was when VR started,
capped at max(0.4 m, 4 × give)) is let through.

Why those choices — eight builds of Gaze Test, all judged in the headset:
1–3: cancelling the pose by moving a parent entity (`#tracking`) in tick.
Measured exact (view moved 0.000 m over 23,258 frames) and still felt like the
view *orbiting* when nodding/tilting, and *sliding backwards* when walking.
2: a neck model on top — no difference. 4: the getCamera override from an
earlier Avantis project (`C:\WebXR\WebXRPrototypes\3dof\CLAUDE.md`), mono —
felt right at once. 5: same, stereo — right, but a slow slide when walking
(the vestibular conflict a real 3DoF headset also has; stereo makes it
noticeable). 6–7: a `give` fraction, then tunable in-scene with − / + buttons;
Luke settled on 0.3. Lesson kept in `xr-app-rules`: the same camera position
reached two ways is not the same experience — trust the headset over the
diary for feel, and the diary for facts.

The lasers are hidden, the left stick is ignored, the right stick still snap-turns, and
any trigger (or a raw WebXR select) presses the gaze cursor, so "look at it and
squeeze" is the whole input model — what a ClassVR 3DoF headset offers. The
lock proves itself: the diary records how far the player really moved and how
far the view gave (≈ 0.3 × that), `/check-headset` reads both back, and two
built-in self-checks feed the lock two pretend eyes (centred, 64 mm apart,
rotation kept, give and cap exact) and press a pretend trigger on the desktop.

### Every app explains itself: README and changelog (0.32)

Each app folder has a `README.md` (what the app is, how to play it, how it
works — always the current version) and a `CHANGELOG.md` ([Keep a Changelog
1.1.0](https://keepachangelog.com/en/1.1.0/)). Two files, not one: the README
answers "what is this?", the changelog "what changed?", and the format
expects its own file. Claude adds a line under `## [Unreleased]` on every
edit (`xr-app-rules`); `build.py` turns those lines into `## [N] - date` when
the build number goes up, and the Vercel history note is made from them, so
nothing is written twice. A README-only change is a new version.

Both travel **inside the page** (`<script type="text/markdown"
id="xr-kit-readme">` / `xr-kit-changelog`, just before `</body>`), so every
route, every `/v/N/` version and every copy carries its own, and
`/copy-xr-app` gets them back without asking the author for anything. On
Vercel the deploy also serves a readable `/about/` page (links: Open the app ·
Every version), linked from `/history` and the page's QR card. The .md files
are not served on their own since 0.34.1 — Vercel leaves a top-level
`README.md` out of the site, and the about page and copies cover both. A copy's
changelog starts with "Made this copy of … version N" and keeps the
original's history under "Before this copy". Neither file carries names or
e-mail addresses. Helper: `skills/publish-to-vercel/scripts/appdocs.py`.

### Make my own copy, from the history page (0.33)

Every version on an app's `/history` page has a **Make my own copy** button.
It does in the browser what `/copy-xr-app` does in a chat: fetch `/v/N/`,
check it against the fingerprint in `history.json`, put the plumbing back
inline from the library the page names, fork the changelog, and write an app
folder — `index.html` (build 1), `aframe.min.js` (jsDelivr's copy of the npm
file, else aframe.io; if neither, Claude adds the kit's on first use),
`xr-project.json` (`forkedFrom.via: "history page"`), `README.md`,
`CHANGELOG.md`. One click: Chrome and Edge open a folder picker straight
away and save the folder where the person chooses (`showDirectoryPicker`, a
second copy becomes "… copy 2"); other browsers (Firefox, Safari, phones)
download a .zip instead. Closing the picker does nothing. The person adds that folder to a Cowork task and asks
for changes. When it's saved, the window says where the folder went and what to do
next in two short lines (0.33.1). The code is `skills/publish-to-vercel/assets/kit-copy.js`,
inlined into the library's history viewer; its output was checked byte for
byte against `vercel_build.py --unslim --as-copy` + `appdocs.py fork`. It
works because Vercel serves static files with `Access-Control-Allow-Origin:
*`. Apps get the button with their next publish (their `/history` points at
the library version they were last published with).

### Microphone: ask once, keep it open (0.34)

Tested on the ClassVR Xcelerate (Mic Test, 29 Sep 2026). The microphone
works, but Wolvic never remembers the permission, even with "remember my
choice" ticked. Every `getUserMedia` call prompts again, in the flat page
and in VR. Asking from a push-to-talk press is therefore unusable: the
prompt comes every time, and letting go to answer it ends the recording
empty. A granted stream does survive Enter VR.

The recipe (`xr-app-rules`, "Microphone"; code in
`skills/xr-app-rules/assets/mic-access.js`, pasted inline) asks once when the
page opens, before VR. It keeps that stream for the whole visit and records
from it on press (`KIT_MIC.record()` / `stop()` / `play()`). It shows an
Allow microphone button whenever the mic isn't open, and asks again on
Enter VR (with an in-scene reminder) if it still isn't. Everything is logged
as `[mic]` diary lines.

## Known limitations

- The preview cannot exercise controller input or headset colour. Those need a
  real play — and afterwards `/check-headset` reads what happened from the
  app's Vercel play history. A session is recorded when the player leaves VR
  or closes the page; a page that never loaded leaves nothing to read.
- Apps that bundle an extra library (`cannon.iife.js`) can't be published
  yet, so they have no link at all until the shared library hosts it.
- The Vercel route needs a Vercel account and a token connected once with
  `/connect-vercel` (or the Vercel connector), and the Claude desktop app open
  — the token route runs in its built-in browser. Vercel's free Hobby plan is
  for non-commercial personal use, so staff use belongs on a Pro team, and
  Vercel accounts are 16+ (pupils need none: they just open the page). The
  kit's plumbing must be hosted once per template version (`xr-kit-lib-<hash>`
  projects) — the kit's maintainers do that on each release (the skill does it
  itself if one was missed, but the upload is the slow step). Runtime logs keep
  an hour on Hobby (a day on Pro); the Blob play history covers anything older.
