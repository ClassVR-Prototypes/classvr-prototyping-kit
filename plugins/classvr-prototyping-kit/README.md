# ClassVR Prototyping Kit

Build a WebXR prototype and get it onto a ClassVR headset without a terminal, a
server, a certificate, or a single command typed by hand.

Four things you can say:

| You say | What happens |
|---|---|
| **"Make a new VR app called Planet Walk"** (`/new-xr-app`) | A folder appears with a working scene — checked green ground, blue sky, a VR rig with controllers, thumbstick movement and snap-turn — and the app opens on screen as a Claude Artifact with its own permanent link. Right-click and drag to look around, left-click presses; WASD moves, Q/E turn. If the name sounds like a game ("Bubble Pop") and you didn't say what it does, you're offered a few concepts — or the empty scene — and the one you pick is built as a first playable version. |
| **"Share it" / "refresh the link"** (`/share-xr-app`) | The app is rebuilt, checked, and its link updated. In a GitHub repository (Claude Code) the link is a public **GitHub Pages** URL, which also works for Enter VR on a headset; elsewhere it is a Claude Artifact. Runs on its own after every edit, so the link is never behind, and the URL is put in the chat. |
| **"Host it on Vercel"** (`/publish-to-vercel`) | Opt-in third kind of link, for Cowork sessions with the **Vercel connector** on: the app is rebuilt as a small page that loads the kit's plumbing from a shared, versioned library, deployed to `https://<app>.vercel.app` through the connector — no Git, no upload screen — verified live, and you get a QR code. Enter VR works on a headset; updates are live in seconds. Say it when you create the app ("…hosted on Vercel") or any time after. |
| **"Show me"** (`/preview-xr-app`) | The app is loaded in a headless browser and checked for errors. You get a screenshot and a one-line health report. |
| **"Put it on the headset"** (`/publish-xr-app`) | The app is verified, uploaded to ClassCloud, filed under your organisation's **XR Prototypes** playlist, and you get a QR code. Scan it on the headset. Re-publish as often as you like — the QR never changes. |

Everything in between — "add a table", "make the ball bounce", "put a sign up" —
is just conversation. A fourth skill, `xr-app-rules`, loads automatically while
an app is being edited and quietly applies the constraints that keep it working
on a headset.

## What's inside

```
skills/
  new-xr-app/        scaffold a project; bundles A-Frame 1.7.1 and cannon-es
  preview-xr-app/    headless load + error check + screenshot
  share-xr-app/      build → verify → GitHub Pages (in a repo) or Claude Artifact, on a permanent link
    assets/pages/                    the Pages workflow + site builder the kit installs in a repo
  publish-to-vercel/ build a slim page + shared library → deploy through the Vercel connector → QR
    scripts/vercel_build.py          extracts the kit's plumbing from an app into versioned library files
  publish-xr-app/    build → verify → upload → playlist → QR
  check-headset/     after a play on a headset: fetch its log, read the app's diary
  xr-app-rules/      the constraints, applied on every edit
    references/classvr-xcelerate.md   the target headset and its Wolvic build: specs, behaviour, gaps
```

The kit also carries two **hooks** (`hooks/hooks.json`). At the start of every
session, `hooks/voice.md` is read into Claude's context: a short description of
who the person is and how to talk to them — plain English, outcomes rather than
steps, no file paths or error text, and the kit's rules followed quietly rather
than reported on. Claude Cowork already speaks this way; the hook makes Claude
Code on the web and in the terminal match it. When a turn ends,
`scripts/stop_publish_check.py` checks that in a repository of kit apps no work
is left short of `main`, unless the latest commit is marked `[hold]`. It is what
makes "your change is live" reliable rather than usual.

Each skill carries the scripts it needs (`scaffold.py`, `build.py`,
`preview.py`, `artifact.py`, `publish_pr.py`, `vercel_build.py`, `upload.py`, `make_qr.py`,
`manifest.py`, `headset_diary.py`). Claude
runs them; you never see them. Every project has an `xr-project.json` manifest
recording its build number, its artifact URL and its ClassCloud ids, which is
what makes re-sharing and re-publishing an update rather than a duplicate.

## Requirements

- **The Eduverse (ClassVR) connector** must be connected in your Claude
  workspace. Publishing uses it to upload the file and create the playlist entry.
- **A connected folder** for projects to be created in.
- Python 3 in the session environment (present in Claude Cowork). The preview
  step additionally needs Playwright with Chromium; if it isn't available the
  publish step proceeds but says the build was not verified.

No CDN access is required, anywhere. Libraries ship inside the plugin.

## Design decisions, briefly

**Libraries are bundled, never linked.** A wrong CDN path fails silently and the
page still looks like a working app. Bundling also survives school network
filtering and the single-file constraint of ClassCloud hosting.

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

**One shared playlist per organisation.** Every app is an item in "XR
Prototypes", so one QR reaches everything and a new app never needs a new code.

**The build number increments itself.** The build script hashes the source with
the version line masked out; a real change bumps the number, a no-op rebuild
doesn't. It shows on the app's panel, in the activity name and in the filename,
so "is the headset running my newest code?" is always answerable.

**The status panel is for the person holding the headset.** It shows the app
name, build number, readiness checks and controls — nothing else. Developer
diagnostics (controller connections, input counts, colour mode, a session
summary on leaving VR) go to the console tagged `[xr-kit]`, readable in browser
devtools or on the headset with `adb logcat | grep xr-kit`.

**The app lives on a link, not in a file.** Every app is put on a link the
moment it is created, and the link is updated after every edit. It never
changes, so a colleague who has it just reloads; the build number on the panel
says which version they're looking at. Which link depends on where the app
lives. In a **GitHub repository** — how Claude Code works — it is a public
GitHub Pages URL (`https://<owner>.github.io/<repo>/<slug>/`), a plain web page
that opens on a desktop *and* enters VR on a headset; the published page
carries a QR code of its own address in the corner, so pointing the headset's
scanner at any screen showing the app is all it takes; the repo's history is
the app's history. In a **plain folder**
(Cowork) it is a Claude Artifact: private until shared from the page's Share
menu, viewers signed in to Claude, updatable only by whoever created it, and
unable to enter VR — headsets then go through ClassCloud + QR. Both routes share
one build number with the ClassCloud publish.

**One thing on screen per turn, and it's the thing you need next.** Create or
edit an app and the turn ends on the link — the Pages URL on its own line, or
the artifact card. Ask for a
preview and you get the screenshot. Publish — on its own, or in the same prompt
as "make a new app" — and you see the QR code, rendered last so nothing covers
the code you are about to scan. Project files are attached as files, not
rendered.

**Publish refuses to ship a broken build.** The preview check runs first and a
failure stops the upload.

**The colour fix is built in and not adjustable.** Wolvic double-encodes sRGB in
immersive mode; the kit emits linear output while immersed and standard sRGB on
a flat screen, so the same file shows the same pastels on a monitor and in the
headset. The switch happens *before* the XR session is created — three.js
freezes the framebuffer's colour space at that moment, so switching on
`enter-vr` is too late and looks like the fix isn't there at all. There is no
setting for this; it is plumbing, not a preference.

**The first publish of each app asks which organisation it belongs to**, then
remembers it. The question offers two choices — your current organisation
(the one you last published to from this folder) and "another organisation",
which you type. It never lists every organisation you belong to. It is the
only question publishing asks.

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

## Known limitations

- The file upload itself is an HTTP `POST`, not a connector call, because the
  Eduverse MCP mints a ticket rather than accepting bytes. An `upload_file` tool
  on the server would make publishing pure-connector end to end.
- The organisation picker lists direct memberships. An organisation reached
  only by inheritance can still be chosen by typing its name into the
  question's free-text box.
- The preview cannot exercise controller input or headset colour. Those need a
  real scan — and afterwards `/check-headset` reads what happened: the app
  writes its diary into the headset's own log (by rewriting its page address,
  which Wolvic logs), and ClassCloud fetches that log on request. It takes a
  few minutes and the headset must be on its home screen; it is not live.
- The artifact link cannot enter VR on a headset: the artifact viewer frames
  the page with a permission policy that blocks WebXR and a sandbox that blocks
  opening it on its own. The panel says so. Headsets go through a GitHub Pages
  link or ClassCloud. A Pages link, by contrast, is public, needs the repo's
  one-time *Settings → Pages → Source: GitHub Actions* setting, goes live only
  from `main` (a change on a branch waits for its PR to be merged), and sits
  behind a 10-minute cache (`?b=<build>` fetches fresh).
  The same frame refuses pointer lock, so the kit supplies its own click-once
  mouse look there (Esc stops it). The camera pauses while the cursor is off
  the page; fullscreen avoids that.
- The Vercel route is a prototype (see `6 - Vercel Hosting/OVERVIEW.md` in the
  project for the tests behind it). It needs the Vercel connector in the chat
  and a Vercel login; Vercel's free Hobby plan is for non-commercial personal
  use, so staff use belongs on a Pro team. Apps that bundle an extra library
  (`cannon.iife.js`) are not supported on it yet; the QR is a PNG in the chat
  and the app folder, not yet drawn on the page; the kit's plumbing must be
  hosted once per template version (`xr-kit-lib-<hash>` projects) — the skill
  does that itself when it finds it missing, but the upload is the slow step.
