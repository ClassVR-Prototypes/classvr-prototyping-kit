---
name: xr-app-rules
description: >
  This skill should be used whenever editing, extending, or debugging a WebXR app made
  with the ClassVR Prototyping Kit — any folder containing xr-project.json — including
  requests like "add a table", "make the ball bounce", "put a sign here", "add text",
  "the throw feels weak", "it looks washed out on the headset", "the button doesn't
  work in VR", or "why can't I grab it". It holds the hard-won constraints that keep
  an app working on a ClassVR headset, so ordinary prompts don't reintroduce known
  failures.
metadata:
  version: "0.6.0"
---

# Rules for editing a kit XR app

These are constraints, not suggestions. Each one was discovered by shipping to a
headset and watching something fail that looked fine on a desktop. Apply them
silently — the user asked for a table, not a lecture on colour spaces.

## Always

**Edit `index.html` in place, below `<!-- ADD YOUR CONTENT HERE -->`.** Leave the
`xr-kit` component, the rig, the panel and the `window.BUILD` line alone. Content
is A-Frame primitives (`<a-box>`, `<a-sphere>`, `<a-plane>`, `<a-cylinder>`,
`<a-entity>`) and, when behaviour is needed, an `AFRAME.registerComponent` block
in a `<script>` placed **before** `<a-scene>` so it is registered when the scene
initialises.

**Never load anything from a CDN or any external url.** Libraries are bundled
files beside `index.html`; assets are data URIs or separate ClassCloud uploads.
The published file is content-addressed and has no relative paths, and school
networks block arbitrary hosts. A CDN 404 fails silently and the page still
looks like a working app.

**Coordinates are metres; −Z is in front of the player.** The rig sits on the
floor at the origin; the headset supplies eye height. Comfortable interaction
range is 0.4–0.8 m from the rig; readable detail sits 1.5–3 m away. Tables are
about 0.6–0.9 m high.

**Keep the pastel lighting setup.** `toneMapping: no` plus hemisphere `2.25` and
directional `1.5`. These are physical light units (three.js r155+); halving them
to match old tutorials makes everything dark, and turning tone mapping on turns
pastels to mud.

## The headset

Kit apps are tested on the **ClassVR Xcelerate (CVR-655)**: Snapdragon XR2
Gen 1, 1920 × 1920 per eye at 90 Hz, 105° field of view, 6DoF, Oculus-Touch-
profile controllers, running ClassVR's fork of Wolvic on **Chromium 124**. The
full sheet, what the Wolvic source says (launch mode, permissions, why 72 fps,
sleep behaviour, auto-VR), what the kit has observed, and what is still unknown
are in `references/classvr-xcelerate.md` — read it when a request depends on
the hardware or the browser ("will this run smoothly", "is that readable", "can
I use the menu button", "can it start in VR by itself"). Four consequences
apply to every edit without reading it:

- **Legibility:** ~18 pixels per degree. Text ≥ 1.5° tall — about 5 cm at
  2 m, 8 cm at 3 m — and canvas textures drawn at twice the pixels they will
  cover, or they blur and shimmer.
- **Budget:** a mobile GPU drawing two 1920² eyes. Under ~100 k triangles and
  ~100 draw calls in view, textures ≤ 2048², no real-time shadows or
  post-processing unless asked. Wolvic runs WebXR at **72 Hz** on this
  device (its refresh-rate table doesn't list it, so it takes the first rate
  ≥ 60), so a diary `fps` near 72 is full speed; well under 60 means simplify.
- **Buttons:** Menu (left), System (right), Back (headset) and volume belong to
  the system — double press opens its HUD, long press recentres. Never bind
  them — Wolvic keeps them and they never reach the page. Triggers, grips,
  sticks and A/B/X/Y are the app's, within the kit's reservations below. No
  hand tracking (disabled in this Wolvic build).
- **Web platform:** Chrome 124. WebGL 2 and WebXR `immersive-vr` only — no
  WebGPU, WebXR layers, AR or hand-tracking APIs. WebXR permission is granted
  without a prompt; the UA does not say "Wolvic".

## Controls list

`window.KIT_CONTROLS` near the top of `index.html` feeds the panel's Headset and
Desktop lists. **Whenever an interaction is added — grab, throw, press, teleport
— add a plain-language line to `headset`** (and to `desktop` if there is a
keyboard/mouse equivalent). Keep each line to one action: `'Trigger: pick up a
ball'`. Remove lines for interactions that are taken out.

## Text in the scene

**Do not use A-Frame's `text` component.** It fetches its font from
`cdn.aframe.io` at runtime — an external request that will fail in the published
build. Draw text onto a 2D `<canvas>` and use it as a `THREE.CanvasTexture` on a
`THREE.PlaneGeometry`. Real text in 3D, no font file, no network.

## The ground

The starter floor is `<a-plane … checker-ground>`: a 1 m two-green check drawn
on a canvas and tiled, there so looking and walking are visible. Keep the
component when recolouring or resizing the floor (it reads `width`/`height`;
`colorA`/`colorB`/`cell` are its knobs). Replacing the floor with something
else is fine — just don't go back to a single flat colour, which reads as
"nothing is moving" on desktop.

## Anything the player must see while immersed

The HTML panel vanishes in VR. Score, instructions, state — anything needed
during play — must be geometry in the scene (canvas-texture planes work well).
The panel itself is for the person holding the headset: build number, readiness
checks, controls. Diagnostics for *you* go to the console (see below).

## Physics

**A-Frame and three.js have no physics.** For anything that falls, rolls, bounces
or is thrown, use the bundled `cannon-es`: copy
`${CLAUDE_PLUGIN_ROOT}/skills/new-xr-app/assets/cannon.iife.js` beside
`index.html`, add `<script src="./cannon.iife.js"></script>` after the A-Frame
tag, and add `"cannon"` to `libraries` in `xr-project.json`. Do not use
`aframe-physics-system` (lags releases; Ammo driver needs a `.wasm` file, which
single-file publishing cannot carry).

**Create every body twice** — a `CANNON.Body` and a `THREE.Mesh` — and copy
body → mesh in `tick()`. **Set rotation on both**, and store each body's starting
quaternion so a reset restores it rather than snapping to identity.

**Step at 120 Hz, not 60:** `world.step(1/120, delta/1000, 5)`. cannon-es has no
continuous collision detection, so anything smaller than `speed ÷ rate` metres
can be passed straight through. At 60 Hz a 9.5 m/s ball (158 mm/step) goes
through a 160 mm cube without a contact. **Cap thrown speeds against the rate**
— 15 m/s at 120 Hz — and change the two together.

**Measure throw velocity at the release peak,** not as an average over the
trail: check windows of 20–120 ms ending at the last sample and keep the
fastest. A flat average reads about two-thirds of the true speed and the throw
feels dead. A gain of ~1.35 on top reads as "light", above ~1.5 as "launched".

## Controller models are off — the kit reads the gamepad itself

Both hands use `laser-controls="... ; model: false"`. A-Frame's controller
MODEL components animate the on-screen stick/buttons, and on ClassVR the model's
named parts never load, so moving the thumbstick throws inside A-Frame —
"Cannot read properties of undefined (reading 'thumbstick')", coded `<build>-lib`.
The kit doesn't need the model: it reads sticks and buttons straight off the
WebXR gamepad (the tick loop) and the white laser line comes from the raycaster,
not the model. So never set `model: true` on the hands, and never add
`oculus-touch-controls` / `meta-touch-controls` / `*-controls` model components
to them; if you need a visible controller, build it from primitives.

## Controllers

**A controller's −Z is not where its laser points.** The entity tracks the grip
pose; for Meta Touch the drawn ray is `{0, −0.9, −1}`, ~42° below −Z. To cast
along the visible line, read `origin` and `direction` from the entity's
`raycaster` component and apply them through the entity's world matrix. Casting
raw −Z misses everything while looking perfectly aimed.

**A-Frame's raycaster only sees entities.** Bare `THREE.Mesh` objects are
invisible to it. Cast your own `THREE.Raycaster`, and give it tolerance — test
perpendicular distance to the target centre with `radius + ~0.1 m`, and prefer
the candidate closest to the line.

**Thumbsticks are `axes[2]`/`axes[3]`** in the xr-standard gamepad mapping;
`axes[0..1]` are a touchpad the Quest doesn't have.

**Listen to WebXR `selectstart`/`selectend` as well as A-Frame's
`triggerdown`/`triggerup`**, sharing one guard. A-Frame only emits button events
for controller profiles it recognises.

**Locomotion is already in `xr-kit`** (6DoF apps): left thumbstick moves relative to where
the player is looking; right thumbstick snap-turns 45° about the head. Don't add
a second movement scheme, and don't rotate the rig elsewhere without preserving
head position. `MOVE_SPEED` (1.5 m/s) and `SNAP_DEG` are the tunables.

**The rig is `#rig > #tracking > #head + hands`.** Move the player by moving
`#rig`. Never move, remove or re-parent `#tracking` — it is where the headset's
own movement lands (the 3DoF lock no longer moves it, since 0.15; it works on
the XR cameras directly, but the structure check still expects it).

**The `#head` entity does not carry the headset pose in VR.** three.js writes
the real head position and rotation onto the `THREE.PerspectiveCamera` *inside*
the entity (`headEl.getObject3D('camera')`); the entity itself is frozen at its
pre-VR orientation. Anything that needs "where the player is looking" or "where
the player's head is" — movement direction, turn pivot, gaze-based logic,
placing something in front of the player — must read the camera object's
**world** transform (`xr-kit`'s `headObject()` does this). Reading the entity
works on desktop and silently fails in the headset: forward becomes "where I was
facing when I pressed Enter VR".

## 3DoF apps: designing for a fixed viewpoint

`xr-project.json` says which headset the app is for (`"dof": 3` or `6`; so does
`<a-scene xr-kit="dof: N">`). **Check it before every edit** — a 3DoF app has
different rules, and the desktop preview will not tell you when you break them.

What the player of a 3DoF app has: **turning only**. The head is held 1.6 m
above the rig: `xr-kit` wraps `renderer.xr.getCamera()` and recomposes every
eye camera at that point each frame (rotation kept, stereo kept, a `give` of
0.3 of the real movement let through so walking doesn't feel like sliding —
tuned on a headset 9 Sep 2026, see the kit README). Two things follow: **never
move `#head` or `#tracking` to "fix" the view** — that route was measured exact
and still felt wrong; and **`xr-kit="dof: 3; give: N; stereo: false"`** are the
only knobs (give 0 = eyes nailed to a point, 1 = real walking). The lasers and hand rays are off, the left stick does nothing, and
**squeezing any trigger selects whatever the player is looking at** — a `click`
on the `.clickable` entity under the gaze cursor, the same event a laser click
sends. The right stick snap-turns as usual. So:

- **Everything interactive is `.clickable` and is hit by looking at it.** Use
  the `click` event only; no `grab`, no hand position, no controller pose, no
  `raycaster` on the hands (it is disabled). Make gaze targets generous —
  ≥ 0.3 m across at 2 m — and never overlap them.
- **Nothing depends on the player moving.** No reaching, leaning, ducking,
  peering behind or walking up to things. What must be seen must be visible from
  the rig. If content needs to get closer, bring it to the player or move the
  **rig** (a teleport hotspot, a timed tour) — never expect them to step.
- **Comfortable placement:** the ring 1.5–4 m out, from the floor to ~30° up.
  Behind the player is fine (they can turn); above 60° up is not.
- **Hover is free.** The gaze cursor emits `mouseenter` / `mouseleave` on
  `.clickable` entities as the player looks at them — use it to highlight the
  current target so they know what a squeeze will pick.
- **Moving the rig is allowed** (the lock is relative to the rig) but keep it to
  short hops or slow constant glides; the player has no body cues at all.
- **Controls list:** the headset list says `Look at … and squeeze a trigger` —
  never "point", "laser", "walk" or "reach".
- **Desktop still lets the tester fly** (W/A/S/D) so they can inspect; the
  headset never does. Don't build anything that only works from a place the
  desktop tester walked to.
- To switch an app between 3 and 6: `scaffold.py --retarget <index.html>
  --dof N` (see `new-xr-app`), then revisit the content under these rules.
- The 6DoF kit locomotion notes above (stick movement, laser direction) do not
  apply to 3DoF apps; the head-pose note (`headObject()`) does.

Writing a component that must behave differently per target: read
`this.el.sceneEl.components['xr-kit'].data.dof` — never the user agent.

## Colour on the headset

**Wolvic double-encodes sRGB.** `xr-kit` already emits linear output while
immersed and sRGB on a flat screen — and it sets linear *before* the XR session
is created (in a wrapper around `enterVR`), because three.js freezes the XR
framebuffer's colour space at session start and ignores later changes. Don't
remove or move that code, and don't "fix" washed-out colours by editing hex
values — the palette isn't wrong, the pipeline is.
Desktop **fullscreen** is also `enter-vr` to A-Frame but is a flat screen: the
wrapper only goes linear when `checkHeadsetConnected()` is true and the
`enter-vr` handler only when `renderer.xr.isPresenting` — keep both guards, or
fullscreen on a monitor goes dark and over-saturated.
If a scene looks right on a monitor and washed out in a headset: lifted midtones
mean one encode too many, dark and contrasty means one too few.

## The link has no VR button

A kit app opened from its artifact link runs inside the viewer's frame, and
that frame blocks WebXR: `isSessionSupported` throws `SecurityError`, A-Frame
shows no VR button, and the panel says "blocked inside a frame". Opening the
page on its own from inside the frame is blocked too. This is not a bug in the
app and cannot be fixed from inside it; headsets use the ClassCloud build via
the QR code. Don't add workarounds.

## Desktop mouse: right-drag looks, left-click is the trigger

Desktop look is **right-click-and-drag**, everywhere: `look-controls="pointerLockEnabled:
false"` on `#head`, with look-controls' mouse-down re-pointed at button 2 by the
block at the top of the script (keep it). A held button makes the browser
capture the pointer, so dragging keeps turning the camera even after the mouse
leaves the artifact frame — the one thing every "click once, then the mouse
looks" variant could not do inside an embed (the frame refuses pointer lock;
the soft-look / edge-turn imitations tried in Sept 2026 stalled at the edge or
felt unnatural and were removed on Luke's decision).

**Left-click is the desktop trigger, aimed by gaze.** `#gaze` (a child of
`#head`: `cursor="fuse: false" raycaster="objects: .clickable"`) casts from the
screen centre, and `#kit-reticle` — a small HTML ring, hidden during a real XR
session — shows where it points. It must stay **above the panel** (z-index
10001 vs 9999): in a small window the panel reaches the middle of the view and
hid the ring once already. Desktop fullscreen goes through
`canvas.requestFullscreen`, which `xr-kit` redirects to the whole page — A-Frame
fullscreens the bare canvas, which hides every HTML overlay. Keep that redirect. The cursor is limited to button 0, and a
left-click emits the same `click` (and `mousedown`/`mouseup`) on a `.clickable`
entity that `laser-controls` emits when the trigger is pressed on it. So: give
interactive entities `class="clickable"` and listen for `click` on the entity —
one handler covers headset trigger and desktop mouse. Reserve
`triggerdown`/`selectstart` on the hand entities for actions that aren't aimed
at an object (throw, teleport). Don't put `cursor` on `<a-scene>` with
`rayOrigin: mouse` — the ring would then lie about where a click lands. The
panel's Desktop hint lists both lines; keep `desktop[0]`/`desktop[1]` in step.

## Self-checks: every feature comes with one

`window.KIT_CHECKS` (near the top of `index.html`) is a list of tiny tests in
plain words — "a ball appears when you press the trigger", "the score goes up
when a can falls". The preview step runs them (after the kit's own built-in
checks: library loaded, scene loaded, rig present, the player can walk) and a
failing check fails the preview, so the user never meets that bug.

**When you add or change an interaction, add or update a check for it.** One
per promise the app makes; name it the way the user described the feature. The
helper `t` can look (`t.find`, `t.count`, `t.pos`), act (`t.click(sel)` for
what the gaze cursor / laser does, `t.press('right','trigger')` for a controller
button, `t.key('w', ms)` to walk) and wait (`t.wait(ms)`, return the Promise);
`t.expect(cond, 'what should have been true')` fails with that reason. Checks
run only when the preview asks (or with `?kitcheck` in the address), never
while someone plays, so they may freely spawn, press and move. Keep each under
two seconds; don't test the kit itself (movement, colour, snap turn) — that's
covered. A check that fails because the *check* is wrong gets fixed, not
deleted; a check that fails because the app is wrong means the edit isn't done.

**Check durable evidence, not things that vanish.** A dart, a thrown ball, a
particle burst or a popped bubble may be gone before `t.wait()` returns, so
"count the darts after 300 ms" fails even when the app is right. Instead have
the app record the moment it happens and check *that*: bump a counter on the
app (`window.APP.dartsFired++`) or leave a line in the diary
(`window.KIT.note('event', 'dart fired')`) where the dart is created, then
`t.expect(window.APP.dartsFired === before + 1, …)`. Counting scene objects is
fine for things that stay (a table, a sign, a new wall of bubbles); read the
count *immediately* after the action if the object is short-lived. Order
checks so an earlier one doesn't consume what a later one looks for.

## Debugging without a console

**Never ask the user to open a browser console, developer tools, or `adb`.**
They cannot, and the kit is built so you don't need them to. In order:

1. **Build number.** The panel shows it; a stale headset or an un-reloaded
   link is the commonest "bug". Ask "what number does the panel show?" —
   nothing more technical than that.
2. **Run the preview yourself.** `preview.json` carries `checks` (which
   promise broke, and why) and `diary` — the app's own record: `errorList`
   (thrown errors with file:line, failed script loads, unhandled promises,
   `console.error`), the last 40 events (`[xr-kit]` lines, controllers seen,
   presses, snap turns, checks), `fps`, `presenting`, `framed`. Read the
   **first** error first: one root cause fans out into several failed checks.
3. **Reproduce in a check.** If the report is "the ball doesn't appear", write
   the check that presses the trigger and counts balls, run the preview, and
   read the diary. One readout beats three guesses.
4. **Read the reports before asking anyone anything.** Every session posts
   its diary somewhere Claude can read it, whichever way the app was opened:
   - **On the link** (`artifact.mailbox` true): `Artifact action: "read_db"`,
     `url` = `artifact.url`, `db_op: "query"`, `collection: "reports"`,
     ordered by `updated` desc.
   - **On a headset** (the ClassCloud copy): the diary is written into the
     headset's own log — run `/check-headset`. It asks the headset for the log
     through ClassCloud (the player must be back on the home screen; it takes
     a few minutes), decodes the diary, and gives you the same fields.
   If a report matches what the user describes (same build, an `errorList`,
   the `events` before it), you have the whole story — say what you found in
   one plain sentence, then fix. Only fall back to asking for the code when
   there is no link and no headset log (a local double-clicked file).
5. **Look for flags.** Bugs that never throw — the ball falls through the
   floor, nothing happens on a press — leave no code. For those the player
   marks the moment: on a headset both triggers squeezed and held for two
   seconds (a ring fills during the second one; letting go cancels), on
   desktop the F key.
   That writes a `flag` entry to the diary, a `flags` list of timestamps to
   the report (status `flagged`), shows "Marked for Claude" in the scene, and
   posts to the mailbox at once. Read the `events` in the ten seconds before
   each flag — the last controller event, press, or `[xr-kit]` line is usually
   the story — then ask one question: "at the moment you marked it, what did
   you see happen?" Never remove or rename the gesture; apps must not bind
   both triggers together or the F key.
6. **Ask for the code.** Whenever an error is recorded the app shows it in two
   places: the panel line "Oops, something didn't work — …",
   and an **in-scene sign** hung off the camera, visible on desktop and inside
   the headset alike (the first error, its code, and how many followed). The
   code is `<build>-<line>`: the build number, and the line in
   `dist/<slug>-build<N>.html` (rebuild it with `build.py` if it's gone; the
   build is deterministic). This holds wherever the page ran — the artifact
   link, the ClassCloud copy, a headset — because the kit measures the
   wrapper's line offset at runtime and subtracts it. Only a local
   double-clicked `index.html` (never built) reports its own lines.
   `21-lib` = inside a library (build.py stamps the inlined libraries' line ranges
   so A-Frame's one enormous line is never reported as a line number), `21-load` = a file failed to load,
   `21-msg` = a `console.error`. So the question is just "what code does the
   red sign show?" — then open that line. Other questions, one at a time and
   in the user's words: headset, computer, or both? Did anything appear where
   the ball should be?

7. **Headset-only problems** (colour, controllers, performance) that the
   desktop preview cannot see: add `this.log(...)` (in `xr-kit`) or
   `window.KIT.note('log', …)` elsewhere so the *next* run records what you
   need, republish, ask the user to play until the problem shows and come back
   to the home screen, then `/check-headset`. Everything the app prints —
   `console.log`, `warn`, `error`, thrown errors, flags — is in the diary, and
   the diary reaches the headset log by itself. Never mention `adb` or a
   console to the user. For "is it the palette or the pipeline", drop unlit
   `MeshBasicMaterial` swatches of known hex values into the scene: their
   pixels *are* the hex, so any difference is the output path.

The panel is for the person holding the headset: build number, readiness,
controls, and the single line "Oops, something didn't work — …" whose ending depends on where
the details go (see below).
Never put developer counters or raw errors on it. Don't build your own error
display either — the sign and the panel line come from the kit. The sign has a
close cross (laser or mouse) and, once closed, a small red tab at the bottom
of view that reopens it, so the code is never lost; a new error reopens it.

## The error card says different things in different places

The header is always "Oops, something didn't work". The body depends on the
**route** the diary has to Claude, which the kit works out itself:

- **mailbox** (artifact link, runtime granted): "Don't worry, Claude already has
  the details. You can continue playing, or take the headset off and tell Claude
  what you were doing." Footer: `"code 21-625" – Tell this to Claude only if asked.`
- **headset** (a standalone headset browser — detected as Android + WebXR +
  immersive-vr supported, or a session running; never by the UA string, which
  the ClassVR Wolvic overrides — with the logbook on): "You can continue playing. When
  you're finished, exit to the ClassVR Launcher screen and Claude can collect
  what happened (keep your headset awake)." Same footer.
- **code** (local file, plain browser — nothing automatic): "Tell Claude: "code
  21-625" and what you were doing when it happened." No footer — the code carries
  the build.

The reopen tab reads "▲ Show details" on the first two routes and "▲ Show error ·
code …" on the third; the HTML panel line ends the same three ways. Keep this
wording in step across the three places if it is ever changed; never add the
raw error text to the card — it is in the diary for Claude.

## Controls the kit reserves

Trigger = interact, thumbsticks = move / snap-turn, **both triggers held 2 s =
mark a problem**, **F = mark a problem** (desktop). Apps may use grip, A/B/X/Y, and
single triggers freely; never a two-trigger combination or the F key.

## Before saying "done"

Every edit to `index.html` ends the same way, in this order:

1. **Preview check** (`/preview-xr-app`, no screenshot rendered). It takes
   seconds and catches a thrown error, a missing library, a scene that no
   longer loads, or a self-check that no longer passes — the failures a
   non-technical user cannot diagnose from a blank headset. A failing check
   means the edit isn't finished; read `checks` and `diary` in
   `preview.json` and fix the first problem first.
2. **Refresh the link** (`/share-xr-app`). In a GitHub repository that means
   well-named commits (one per logical change), the last one marked
   `[publish]` unless the user asked to hold, then push; the Pages URL shows
   the change a couple of minutes later;
   elsewhere the app's artifact is updated in place. Either way the user — and
   anyone they've shared the link with — sees the change by reloading. The
   build number bumps, and it's what confirms they're looking at the new
   version. If the manifest has no link yet (an app made before links
   existed), this creates one.
3. Write `index.html` and `xr-project.json` back to the folder (in a repo, the
   commit is the write-back).

The link is the last thing on screen in an edit turn: the Pages URL on its own
line, or the artifact card. One sentence about what changed, then "reload the
link to see it" (on a branch: "once it's merged"). Never render `preview.png`
in an edit turn.
