---
name: new-xr-app
description: >
  This skill should be used when the user asks to "make a new VR app", "create a new
  XR app", "start a new WebXR project", "set up a new headset app", "new xr app", or
  invokes /new-xr-app. It creates a complete, working WebXR starting point — a green
  checked green ground, blue sky, and a VR rig with controllers — in a new folder the user
  can build on with ordinary prompts. If the app's name suggests a game or activity
  and the user hasn't described it, it offers a few concepts to choose from and
  builds a minimal playable version of the chosen one. No terminal, no libraries to
  install.
metadata:
  version: "0.5.0"
---

# New XR app

Create a working WebXR project folder from the kit template, then put it on a
permanent link (`/share-xr-app`). The result is viewable in any desktop browser
the moment the turn ends and is ready to publish to a headset with
`/publish-xr-app`. The user should never have to run anything or open a file.

## What gets created

A folder named after the app, containing:

- `index.html` — the app. Green plane, blue sky, lights, and an XR rig (camera plus
  two laser-controller hands) with thumbstick movement, 45° snap-turn, a status
  panel showing the build number, readiness and controls, and the Wolvic colour
  fix. Content goes below the `<!-- ADD YOUR CONTENT HERE -->` marker.
- `aframe.min.js` — A-Frame 1.7.1, bundled. **Never** swap this for a CDN link.
- `xr-project.json` — the manifest the preview and publish steps read and update.

Plus, when a concept was chosen (step 2), the first playable version of it.

## Steps

### 1. Get the app name

Take it from the request ("make a new VR app called Planet Walk" → `Planet Walk`).
If no name was given, use AskUserQuestion once with a free-text prompt; do not
invent a name.

### 2. Decide what goes in it

Three cases. Pick one and don't ask anything that isn't listed here.

**a. The request already describes the content or gameplay** ("a can-smash game
where you throw balls at cans", "a room with three planets to walk around") →
no question. Build what was described (step 5).

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
- **Always, as the last option: `Just the empty starter scene`** — "green
  plane, blue sky, nothing else; add things with later prompts."

The built-in Other lets them type their own description; treat that like case a.
Header: `Concept`. Question: `"<Name>" — which of these should I build first?`
Don't put "(Recommended)" on any concept; there is no default here.

**c. No usable signal** — the user gave no name and only supplied one when asked
(no chance to describe anything), *or* the name is generic or a placeholder
("Test", "My App", "Demo", "Prototype 3", "VR Thing", a date, initials) *or* it
names a place or subject without implying an activity you could build in a
first pass with reasonable confidence → **skip the question** and scaffold the
plain starter scene. When in doubt, this is the case. A wrong guess costs the
user a dialog; the empty scene costs nothing.

Never ask this question on `/publish-xr-app`, and never ask it twice.

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
- **Otherwise**, if a concept question is being asked anyway (case b above),
  add a second question to the *same* AskUserQuestion call — header
  `Headset`, question `Which headsets is this for?`, options
  `6DoF — walk, reach and grab (Recommended)` and `3DoF — look and select,
  fixed viewpoint`. Never a separate dialog for this alone.
- **No signal and no dialog** → `--dof 6`, and say so in the closing sentence
  ("built for 6DoF headsets — say *make it 3DoF* to switch").

Switching later is one command, no re-scaffold (see "Retargeting" below).

### 3. Choose where it lives

Create the project as a new subfolder of the user's connected folder, named after
the app. If several folders are connected and the request doesn't say which, use
the first one listed and say so. Never nest inside an existing app folder. If a
folder with that name already exists and is not empty, stop and say so rather
than overwriting.

### 4. Scaffold

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

### 5. Build the first version (only if a concept was chosen or described)

Scaffold first, then edit the scaffolded `index.html` — never write a scene from
scratch, the template carries the headset fixes. Apply the `xr-app-rules` skill
throughout.

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
  concept is meaningless without them. Use primitives and flat pastel colours;
  no external assets, no fonts, no CDN.
- Physics (`cannon-es`) only if things genuinely fall, roll or get thrown — see
  "Physics" below. Simple tweening and hit-testing don't need it.
- **Update `window.KIT_CONTROLS`** with one line per new interaction, in
  `headset` and, where there's a keyboard/mouse equivalent, `desktop`.
- **Add a self-check to `window.KIT_CHECKS`** for the core interaction — the
  preview runs it before anything ships (see `xr-app-rules`, "Self-checks").
- Keep the scene facing the player: the action happens in front (−Z), within
  0.5–4 m, at heights a standing person can reach or see.

Say what you built in the manifest's `concept` field (scaffold `--concept`, or
`manifest.py --set concept="…"` afterwards) so later sessions know what the app
is about.

### 6. Verify before handing over

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/preview-xr-app/scripts/preview.py \
        --file "<staging>/<App Name>/index.html" --out "<staging>/<App Name>/.preview"

It must report `"status": "pass"`. If it doesn't, fix the cause before
delivering — a scaffold that fails its own preview is not finished. For a built
concept, also look at `preview.png`: the interactable objects should be visible
from the start position. If they aren't, move them, don't ship it.

### 7. Put it on a link

Run `/share-xr-app` from its step 1 (route choice) — the build and preview
check are already done, so skip its steps 2–3. Where the app lives decides the
kind of link — unless the request **named Vercel** as the host ("make X,
hosted on Vercel", "…and put it on Vercel"): then it is **route C**, deliver
the project files to the user's folder and run `/publish-to-vercel` from its
step 3; make no artifact and no Pages commit for it. Otherwise:

- **Inside a GitHub repository** (Claude Code, a cloned repo): **route A,
  GitHub Pages.** Commit the new folder, push, and the app gets a public URL
  like `https://<owner>.github.io/<repo>/<slug>/`. Do **not** make an artifact
  as well — one link per app, and the Pages one is the one that also works on a
  headset. If the repo has never published before, the share skill adds the
  workflow and tells the user the one-time Pages setting.
- **A plain folder** (Cowork with a connected folder, no repo): **route B,
  Claude Artifact.** Deliver the project files to the user's folder first
  (`SendUserFile` with `display: "attach"`, then `device_commit_files`), then
  convert the verified build with `artifact.py` and publish it; write
  `xr-project.json` back again afterwards (it changed).

Every app leaves this skill with a link recorded in `xr-project.json`.

### 8. Tell the user, briefly — and give them the link

One or two sentences: the folder name; if a concept was built, what the game
does in one line and how to play it (click to look, W/A/S/D to move, Q/E to
turn; on a headset, **Enter VR**); then how to get it on a headset — on routes A and C
"the page has a QR code in its top-right corner — click it to enlarge, then
point the headset's scanner at it", on route B
"`/publish-xr-app` puts it on the headset". Do not explain libraries,
manifests, artifacts, git, or build numbers unless asked.

**What appears on screen.**

- Route A: **the URL is the last line of the reply, on its own line**, so the
  user can click it and open the app straight away. Say when it will work:
  "live in a couple of minutes" (the share skill ran `publish_pr.py` and the
  pull request is already merged — never offer to do this, do it); only if
  both hands-free routes failed, "once you press Create PR and Merge". A brand-new repo also needs the one-time
  Pages setting — say so if the share skill just added the workflows.
- Route B: the artifact card is the last thing the turn produces; don't paste
  the URL as well.
- Route C: **the Vercel URL is the last line of the reply, on its own line** —
  it is live at once. No QR image: the page shows its own.

Do **not** render `preview.png` in either case — a screenshot would only push
the link away. Project files are attached, not rendered.

If the request asked to create **and** publish ("make X and put it on the
headset"), continue straight into `/publish-xr-app` without stopping to report
first: share (step 7) happens before publish, and the QR code is rendered
**last** — it is the thing the user needs to see. The organisation question
(first publish only) is the only other question the combined flow may ask.

## When the user then asks for content

After scaffolding, ordinary prompts ("add a red table on the left", "make the sky
darker", "make the balls bigger") are edits to `index.html`. Apply the
`xr-app-rules` skill: it holds the constraints that keep the app working on a
headset (single-file publishing, no CDN, canvas-drawn text, physics timestep,
controller ray direction, head pose in VR, and more) and ends every edit with
`/share-xr-app`, so the link always shows the latest build.

### Retargeting ("make it 3DoF" / "make it 6DoF")

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/new-xr-app/scripts/scaffold.py \
        --retarget "<App>/index.html" --dof 3

It flips the `dof` flag on `<a-scene xr-kit>`, swaps the movement line in
`KIT_CONTROLS.headset`, and updates `xr-project.json`. Then apply the 3DoF
design rules from `xr-app-rules` to the content (anything that needed hands or
walking must become look-and-select or come to the player), run the preview
and share as after any edit. Apps made before v0.13 have no `#tracking` wrapper
and the script refuses; refresh their rig block from the template first.

### Physics

If a request needs physics (things that fall, roll, bounce, get thrown), copy
`${CLAUDE_PLUGIN_ROOT}/skills/new-xr-app/assets/cannon.iife.js` into the project
folder and add `<script src="./cannon.iife.js"></script>` directly after the
A-Frame script tag. Add `"cannon"` to `libraries` in `xr-project.json`. The
publish step inlines every local script automatically.
