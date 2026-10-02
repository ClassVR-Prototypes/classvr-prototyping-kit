---
name: new-xr-app
description: >
  This skill should be used whenever the user asks to make, build or create something
  new — an app, a prototype, a game, a scene, an experience, a simulation, a world or
  a tool, including plain requests like "make a fun painting app", "build me a
  prototype" or "make a game where…" — and whenever they mention VR, AR, XR, WebXR,
  A-Frame, 3D, a headset or ClassVR, even if they never name this kit, VR or Vercel.
  With this kit installed, a request to make an app means a headset app. Also for
  "make a new VR app", "new xr app" or /new-xr-app. Never write a WebXR page by hand
  instead. Not for documents, spreadsheets, slides or messages. It creates a working
  WebXR scene with a VR rig and controllers in a new folder, offers concepts and
  colour looks when the name suggests a game or activity, builds a minimal playable
  version, connects Vercel if needed, and publishes it to a link whose page shows its
  own headset QR code.
metadata:
  version: "0.14.0"
---

# New XR app

Create a working WebXR project folder from the kit template, then put it on a
permanent Vercel link (`/publish-to-vercel`). The result opens in any desktop browser the moment the
turn ends, and the same link opens on a headset from the QR code the page
shows. The user should never have to run anything or open a file.

## What gets created

A folder named after the app, containing:

- `index.html` — the app. The standard look (checked green ground, blue sky),
  lights, and an XR rig (camera plus
  two laser-controller hands) with thumbstick movement, 45° snap-turn, a status
  panel showing the build number, readiness and controls, and the Wolvic colour
  fix. Content goes below the `<!-- ADD YOUR CONTENT HERE -->` marker.
- `aframe.min.js` — A-Frame 1.7.1, bundled. **Never** swap this for a CDN link.
- `xr-project.json` — the manifest the preview and publish steps read and update.
- `README.md` — what the app is, how to play it and how it works, written for
  someone who has only the link. Published inside the page.
- `CHANGELOG.md` — what changed in each version (Keep a Changelog), starting
  with a "First version" line that becomes version 1 when it is published.

Plus, when a concept was chosen (step 2), the first playable version of it,
in a look chosen for it (step 2c).

## Keeping the person posted — progress updates

A new app takes several minutes, so the person is never left with a silent
chat: short, plain progress updates go out as the work happens. Read
`${CLAUDE_PLUGIN_ROOT}/skills/new-xr-app/references/progress-updates.md` at the
start of the job — it is the guide (the tone, the stages, examples) and it
says how to send them: **each update is a `SendUserMessage` call made in the
same block as the step's first real tool call** (parallel, so it costs no
extra round trip), because plain text between steps is shortened before the
person sees it. Updates are plain and factual — what is happening now, to
which part of the app, and whether it is still being built, being tested, or
finished and uploading. Load `SendUserMessage` with ToolSearch at the start
if it is deferred.

**8–10 updates when a concept is built** (about one a minute); 5–6 for a plain
starter scene, where there are fewer real steps — never pad. The updates, and
where they fall below:

| Update | When |
|---|---|
| 1 Starting | end of step 0 — always the first thing after the check or message **F** |
| 2 The plan | end of step 2, once the concept is settled (built concept only) |
| 3 The scene | start of step 4 — the look chosen in step 2c |
| 4 The main build | start of step 5 — say it's the biggest job |
| 5 Making it work | during step 5, as the interaction comes together (one more on a long build) |
| 6 Finishing touches | step 5's goal display, reset, and the how-to-play instructions for the web page |
| 7 Test run | start of step 6 — "building's done" (+ one fix update if it fails and you fix it) |
| 8 Uploading to Vercel | start of step 7 — "test passed", the app is finished |
| 9 Live check | before the publish's live check, on the live Vercel link |

A word-for-word message (the Vercel setup script) is never replaced or
reworded by an update. The closing reply (step 8) is not an update.

## Steps

### 0. Vercel connection — before anything else

Run `/connect-vercel`'s **The check** first, before asking anything or
building anything. Connected → say nothing about Vercel. Not connected → its
setup script runs now, word for word, and this job resumes after its message
**F**. Either way, the next thing the person sees is the **starting** update
(update 1): work is now starting on their app. It comes before any question in
steps 1–2 (if one is coming, it can say "one quick question before I start").

### 1. Get the app name

Take it from the request ("make a new VR app called Planet Walk" → `Planet Walk`).
If no name was given, use AskUserQuestion once with a free-text prompt; do not
invent a name.

### 2. Decide what goes in it

Three cases. Pick one and don't ask anything that isn't listed here.

**a. The request already describes the content or gameplay** ("a can-smash game
where you throw balls at cans", "a room with three planets to walk around") →
no concept question. Build what was described (step 5). Unless the request also
describes the look, still ask the **Look** question (step 2c) — on its own, or
with the Headset question (step 2b) in the same call.

**b. The name plausibly implies gameplay or content, and nothing was described**
→ ask **one** AskUserQuestion. The name is the whole brief, so read it the way a
game designer would: "Fruit Ninja", "Bubble Pop", "Fraction Frenzy", "Planet Walk",
"Basketball Shootout", "Whack-a-Mole VR" all imply something. Offer:

- **Two or three concepts**, each a distinct take on the name. Label = a short
  title of the mechanic (≤ 5 words), description = one sentence of what the
  player actually does and what counts as winning or finishing. Make them
  differ in *kind* — not three flavours of the same idea. Aim at general
  prototyping, any theme; only lean educational when the name itself does
  ("Fraction Frenzy" can, "Bubble Pop" shouldn't).
- **Always, as the last option: `Just the empty starter scene`** — "an empty
  scene to stand in, nothing else; add things with later prompts."

The built-in Other lets them type their own description; treat that like case a.
Header: `Concept`. Question: `"<Name>" — which of these should I build first?`
Don't put "(Recommended)" on any concept; there is no default here.

Add the **Look** question (step 2c) to the *same* AskUserQuestion call, so the
person picks the idea and its colours together in one dialog.

**c. No usable signal** — the user gave no name and only supplied one when asked
(no chance to describe anything), *or* the name is generic or a placeholder
("Test", "My App", "Demo", "Prototype 3", "VR Thing", a date, initials) *or* it
names a place or subject without implying an activity you could build in a
first pass with reasonable confidence → **skip the questions** and scaffold the
plain starter scene in the standard look (green checked ground, blue sky). When in doubt, this is the case. A wrong guess costs the
user a dialog; the empty scene costs nothing.

Never ask these questions when publishing an existing app, and never ask them
twice. All of them — Concept, Look, Headset — go in **one** AskUserQuestion call.

Once a concept is settled (case a, or the answer to case b), send **the
plan** update: what the app will do, in one line.

### 2b. Decide which headset it is for (`--dof`)

Every app is designed for either **6DoF** headsets (full tracking: the player
can walk, lean and reach; two laser controllers) or **3DoF** headsets (turning
only: the body stays put, the player looks at things and squeezes a trigger to
select them; the right stick still snap-turns). ClassVR's Wolvic browser only
runs on 6DoF headsets, so a 3DoF app is *simulated* there — the kit pins the
head 1.6 m above the rig and hides the lasers — which is exactly the point:
prototyping the 3DoF experience on the hardware available.

Decide it like this, and record it with scaffold `--dof`:

- **The request says.** "3DoF", "three-dof", "for the standard ClassVR headsets",
  "gaze-based", "look-and-select", "seated", "no controllers" → `--dof 3`.
  "6DoF", "room-scale", "walk around", "with hand controllers" → `--dof 6`.
- **The gameplay says.** Grabbing, throwing, catching, placing with the hands,
  walking between places, ducking or leaning to look behind things → `--dof 6`.
  Looking at hotspots, choosing by gaze, a 360° viewpoint, a guided tour from
  fixed spots → `--dof 3` is plausible but not certain, so:
- **Otherwise**, if a question is being asked anyway (case b, or the Look
  question in case a), add a question to the *same* AskUserQuestion call — header
  `Headset`, question `Which headsets is this for?`, options
  `6DoF — walk, reach and grab (Recommended)` and `3DoF — look and select,
  fixed viewpoint`. Never a separate dialog for this alone.
- **No signal and no dialog** → `--dof 6`, and say so in the closing sentence
  ("built for 6DoF headsets — say *make it 3DoF* to switch").

Switching later is one command, no re-scaffold (see "Retargeting" below).

### 2c. The look — the person picks it

The green checked ground and blue sky are the default, not the house style:
the person chooses a look that suits their idea. Ask it as one more question
in the same AskUserQuestion call as the concept (case b) — or, in case a,
with just the Headset question if one is needed.

- Header: `Look`. Question: `Which look should "<Name>" have?`
- **Two or three looks** that suit the name and would work with any of the
  concepts offered. Picture the place the idea happens in (a sound garden at
  night, a desert dig, a space station, a sweet shop) and design for that.
  Label = the place or mood in ≤ 5 words ("Glowing night garden");
  description = one sentence in plain colour words: the sky, the ground and
  the colour of the things in it ("Deep navy sky over a dark slate floor,
  with glowing teal and pink plants"). Make them differ in mood (night vs
  day, warm vs cool) — not three shades of one idea. No hex codes, no
  technical words.
- **Always, as the last option: `Standard green and blue`** — "the kit's
  checked green ground and blue sky."
- No "(Recommended)" on any look. Max 4 options, so at most three looks.
- The built-in Other lets them describe their own ("a pink sunset", "inside a
  volcano"); turn that into a look the same way.

Then make the chosen look real following `xr-app-rules`, "The look": sky,
floor shades, two or three accent colours, all kept readable in the headset.
The answer applies whatever concept is picked — including `Just the empty
starter scene`. If the request already described the look, use it and don't
ask. Case c (no question at all) → the standard look.

### 3. Choose where it lives

Create the project as a new subfolder of the user's connected folder, named after
the app. If several folders are connected and the request doesn't say which, use
the first one listed and say so. Never nest inside an existing app folder. If a
folder with that name already exists and is not empty, stop and say so rather
than overwriting.

### 4. Scaffold

Update: **the scene**, alongside the scaffold call — the look chosen in
step 2c in plain words (the ground, the sky, where the player stands).

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/new-xr-app/scripts/scaffold.py \
        --name "<App Name>" --out "<staging folder>"

Add `--concept "<one-line description>"` when a concept was chosen or described,
so the manifest records what the app is meant to be, and `--dof 3` for a 3DoF
app (step 2b; the default is 6).

In a cloud session the user's folder is not directly writable from the shell:
scaffold into a staging directory in the workspace, do all editing there, and at
the end deliver the files into the user's folder with the session's file-delivery
tools (`SendUserFile` followed by `device_commit_files` to
`<connected folder>/<App Name>/<file>`). In a local session write directly.

### 5. Build the first version (if a concept or a look was chosen or described)

Scaffold first, then edit the scaffolded `index.html` — never write a scene from
scratch, the template carries the headset fixes. Apply the `xr-app-rules` skill
throughout.

Updates: this step carries updates 4–6 — **the main build** alongside the first
edit (say it is the biggest job), **making it work** as the interaction comes
together (and one more partway through a long build), **finishing touches**
for the goal display, the reset and the README.

**Work fast — read only the parts you edit.** The scaffolded `index.html` is
about 1,650 lines, and lines ~120–1265 are the kit's own blocks (diary, panel
style, `xr-kit`), which you never edit. Never Read the whole file. Read the
top (lines 1–120: `BUILD`, `KIT_CONTROLS`, `KIT_CHECKS` — the first three
checks and their `rt…` helpers belong to the gaze reticle; add the app's
checks after them) and the part from
`</head>` to the end (Grep for `</head>` to find its line, then Read from
there); that is everything you change. Write the app's content in as few
edits as you can — the scene's entities in one edit below
`<!-- ADD YOUR CONTENT HERE -->`, the components in one `<script>` block
just before `<a-scene>`, controls and checks in one edit
each — rather than many small ones.

**Put the look in first** (the one chosen in step 2c), in the same edit as the scene's
entities: the sky (its `color` and `sky-gradient` bottom — the slightly
darker top is automatic), the scene `background`, the floor's `checker-ground`
colours, the hemisphere light's `groundColor` and the page's loading
background — `xr-app-rules`, "The look", lists exactly where — and record it
with `manifest.py --set look="…"`. Skip this for the standard look. For a
plain starter scene with a chosen look, this edit is the whole of step 5.

Build a **minimal playable slice**, not a game:

- **One core interaction, end to end.** The thing the name is about — throw,
  pop, slice, place, catch — working on desktop and in VR. One mechanic, done
  properly, beats three half-done.
- **A goal the player can see** — a score, a count of things left, a target
  reached — as geometry in the scene (canvas-texture plane), because the HTML
  panel is invisible in VR.
- **A reset**: the round restarts on its own after it ends, or a big obvious
  button/target restarts it. The player must never be stuck in a finished state.
- **Nothing else.** No menus, levels, difficulty, sound, or timers unless the
  concept is meaningless without them. Use primitives in the look's accent
  colours, clearly visible against its sky and floor; no external assets, no
  fonts, no CDN.
- Physics (`cannon-es`) only if things genuinely fall, roll or get thrown — see
  "Physics" below. Simple tweening and hit-testing don't need it.
- Microphone (recording, voice, push-to-talk) → the `xr-app-rules`
  "Microphone" recipe from the start: ask once when the page opens, keep the
  stream, record from it on press. Never ask for the mic from a press.
- **Update `window.KIT_CONTROLS`** with one line per new interaction, in
  `headset` and, where there's a keyboard/mouse equivalent, `desktop`.
- **Add a self-check to `window.KIT_CHECKS`** for the core interaction — the
  preview runs it before anything ships (see `xr-app-rules`, "Self-checks").
- Keep the scene facing the player: the action happens in front (−Z), within
  0.5–4 m, at heights a standing person can reach or see.

Say what you built in the manifest's `concept` field (scaffold `--concept`, or
`manifest.py --set concept="…"` afterwards) so later sessions know what the app
is about.

**Rewrite the scaffolded `README.md`** to describe the slice you built: what
it is, how to play (headset and computer, matching `KIT_CONTROLS`), what's in
the scene and how it looks, and how it works in a few plain sentences — see `xr-app-rules`,
"README and changelog". The changelog's first line already says "First
version: <concept>"; leave it (adjust the wording if the concept line reads
oddly). For a plain starter scene the scaffolded README is right as it is.

### 6. Verify before handing over

Update: **test run** alongside the preview call ("building's done").
If it fails and you fix it, one update saying literally what was wrong, in the
app's terms, and that it is being fixed before anything is uploaded.

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/preview-xr-app/scripts/preview.py \
        --file "<staging>/<App Name>/index.html" --out "<staging>/<App Name>/.preview"

It must report `"status": "pass"`. If it doesn't, fix the cause before
delivering — a scaffold that fails its own preview is not finished. For a built
concept, also look at `preview.png`: the interactable objects should be visible
from the start position and stand out clearly against the sky and floor, and
the floor's check should be visible. If not, move them or adjust the colours —
don't ship it.

### 7. Put it on a link

Update: **uploading to Vercel** alongside the first call of the publish
("test passed" — the app is finished; first time, it is also getting its own
link and QR code), and the **live check** update alongside its live check
(step 4 of `/publish-to-vercel`). These count towards this job's 8–10, not
extra.

Deliver the project files to the user's folder, then run `/publish-to-vercel`
from its step 2, straight away in the same turn. Use `<staging>/<App Name>`
as its `--from` folder — it is the same copy, so there is nothing to stage
back — and add `--no-preview` to its first command (`prepare`, or `build`
for an app already on Vercel), since the check above just passed. Leave the
`.preview` folder out when delivering. The Vercel
connection was already checked in step 0.

Every app leaves this skill with a link recorded in `xr-project.json`.

### 8. Tell the user, briefly — and give them the link

This is the closing reply, not a progress update. One or two sentences: the folder name; if a concept was built, what the game
does in one line and how to play it (click to look, W/A/S/D to move, Q/E to
turn; on a headset, **Enter VR**); then how to get it on a headset — "the
page has a QR code in its top-right corner — click it to enlarge, then point
the headset's scanner at it". Do not explain libraries, manifests or
build numbers unless asked.

**What appears on screen.**

**The Vercel URL is the last line of the reply, on its own line**, so the user
can click it and open the app straight away — it is live at once. No QR image:
the page shows its own.

Do **not** render `preview.png` — a screenshot would only push
the link away. Project files are attached, not rendered.

"Make X and put it on the headset" is the same flow: the link from step 7 is
how it gets onto the headset (the page's own QR code). Don't render a QR image
unless asked for one to print.

## When the user then asks for content

After scaffolding, ordinary prompts ("add a red table on the left", "make the sky
darker", "make the balls bigger") are edits to `index.html`. Apply the
`xr-app-rules` skill: it holds the constraints that keep the app working on a
headset (no CDN, canvas-drawn text, physics timestep,
controller ray direction, head pose in VR, and more) and ends every edit with
`/publish-to-vercel`, so the link always shows the latest version.

### Retargeting ("make it 3DoF" / "make it 6DoF")

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/new-xr-app/scripts/scaffold.py \
        --retarget "<App>/index.html" --dof 3

It flips the `dof` flag on `<a-scene xr-kit>`, swaps the movement line in
`KIT_CONTROLS.headset`, and updates `xr-project.json`. Then apply the 3DoF
design rules from `xr-app-rules` to the content (anything that needed hands or
walking must become look-and-select or come to the player), run the preview
and publish as after any edit. Apps made before v0.13 have no `#tracking` wrapper
and the script refuses; refresh their rig block from the template first.

### Refreshing the kit's parts (`--refresh-kit`)

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/new-xr-app/scripts/scaffold.py \
        --refresh-kit "<App>/index.html"

Replaces the four kit-owned blocks (diary, panel style, `xr-kit`, status
panel) with the current template's and leaves the app's own content, controls
and checks alone. `xr-app-rules` runs it before the first edit of an app in a
session.

### Physics

If a request needs physics (things that fall, roll, bounce, get thrown), copy
`${CLAUDE_PLUGIN_ROOT}/skills/new-xr-app/assets/cannon.iife.js` into the project
folder and add `<script src="./cannon.iife.js"></script>` directly after the
A-Frame script tag. Add `"cannon"` to `libraries` in `xr-project.json`. An
app that uses it can't be published yet (see `xr-app-rules`, "Physics"), so
prefer working the motion out from the formulas when that is enough.
