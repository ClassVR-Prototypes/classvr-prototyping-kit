# ClassVR Xcelerate (CVR-655) — the headset kit apps are tested on

Read this when a question depends on the hardware or the browser: "will this
run smoothly", "is that text readable", "what buttons can I use", "why 72 fps
and not 90", "can it enter VR by itself", "does the UA say Wolvic". Sections
are labelled by where the facts came from: **the docs** (docs.classvr.com,
read 9 Sep 2026), **the Wolvic source** (Avantis's fork, read 9 Sep 2026),
**observed** (kit runs on Luke's headset), and **Unknown** — do not guess
those numbers.

Sources:
- https://docs.classvr.com/device-information/cvr-655/xcelerate-tech-specs
- https://docs.classvr.com/device-information/cvr-655/input
- Wolvic fork: github.com/LearnHub/wolvic, branch `main-avn`, HEAD c8c0d36a0
  (20 Jul 2026). Local clone `C:\Users\lukem\Documents\wolvic`.

## The device (from the docs)

| | |
|---|---|
| Model | ClassVR Xcelerate, CVR-655 — 6DoF, aimed at high schools and further education |
| Display | 1920 × 1920 per eye, 90 Hz, 105° field of view |
| Processor | Qualcomm Snapdragon XR2 Gen 1 |
| Memory | 8 GB RAM |
| Storage | 128 GB |
| Tracking | 6 degrees of freedom (head and both controllers) |
| OS | Android 12 |
| OpenXR runtime | Snapdragon Spaces 26.0 |
| Graphics APIs | OpenGL ES 3.2 or Vulkan (so WebGL 2 is available to the browser) |

### Input (from the docs)

- **Controllers** follow the OpenXR *Oculus Touch Controller Profile*: per hand
  a trigger, a grip, a thumbstick (click + touch), A/B (right) or X/Y (left),
  plus Menu (left) and System (right).
- **The system owns three buttons**: Back on the headset, Menu on the left
  controller, System on the right. Double press opens the System HUD; long
  press **recentres the view**. Tell testers "long-press Back on the headset
  to recentre" when forward has drifted.
- **The headset itself is an OpenXR input device**: gaze pose, select, back,
  volume via `XR_AVN_headset_input` (`/interaction_profiles/avantis/headset655_avn`).
  Native OpenXR only; Wolvic does not map it, so it never reaches WebXR.

## The browser: ClassVR's Wolvic (from the Wolvic source)

**What it is.** Igalia's Wolvic, forked by Avantis (`main-avn`, package
`com.avn.wolvic`, versionName `1.2.6`; upstream merged up to July 2025,
i.e. Wolvic 1.8.x), built with the **Chromium backend** on the **Snapdragon
Spaces** OpenXR flavour. The web engine is a prebuilt **Chromium
124.0.6367.221** (`CHROMIUM_PREBUILT_AARS/Content.aar`). So the web platform
is *Chrome 124 on Android*: WebGL 2 yes, WebXR `immersive-vr` yes; no WebXR
layers, no `immersive-ar`, no hand tracking (see below), and assume no WebGPU.

**User agent.** Chromium's Android "Mobile VR" UA — roughly
`Mozilla/5.0 (Linux; Android 12; …) AppleWebKit/537.36 … Chrome/124.0.0.0
Mobile VR Safari/537.36`. "Wolvic" is **not** reliably in it (confirmed on the
real headset, kit build 24) — the `VRB[UriOverride]: user agent override`
log line is a per-domain lookup, not a hit. Never detect the headset by UA;
the kit uses Android + WebXR + `immersive-vr` supported.

**How a kit app is launched.** The ClassCloud activity URL arrives as an
Android intent. The fork starts in **immersive/kiosk mode by default**
(`mLaunchImmersive = true`): the page opens in a single 2D window with no
browser chrome — default preset 900 × 600, device scale factor 2.0, curved
(cylinder) window on — and the tester presses the A-Frame VR button. The
legal-documents dialog is removed; the environment is Wolvic's "cyberpunk"
skybox with an Avantis build label on the floor.

**Auto-VR is available but not used by the kit yet.** If the URL carries
`wolvic-launchimmersive-targetElementXPath=<xpath>`, Wolvic waits for
`load`, then ~1–2 s more (for WebGL init), finds that element by XPath,
`click()`s it (retrying every 100 ms until found), hides the WebXR
interstitial, and **closes itself back to the launcher when the WebXR session
ends** ("AutoXR"). Two more URL params are parsed: `launch_full_ui=true`
(normal browser UI) and `pose_override=true` (see poses). `launch_full_ui`
and `pose_override` are stripped from the URL the page sees; the xpath param
is kept. For an A-Frame app the xpath would be
`//a[contains(@class,'a-enter-vr-button')]` (A-Frame's VR button; the kit's
`enterVR` colour wrapper still runs because the click goes through A-Frame).
Untested on a kit app — a candidate for `/publish-xr-app`.

**Permissions.** WebXR is **granted automatically** (no prompt) unless the
site has been explicitly blocked in Wolvic's settings. Audible autoplay is
allowed when launched immersive (the default). Inaudible autoplay always.

**Controllers as WebXR sees them.** Mapping `AvantisCVR655`: OpenXR profile
`/interaction_profiles/oculus/touch_controller`; WebXR `profiles` =
`["oculus-touch-v3","oculus-touch-v2","oculus-touch","generic-trigger-squeeze-thumbstick"]`;
reported to the browser as Oculus Touch 2 (Quest 1) controllers — hence
A-Frame's `meta-touch` recognition and the kit's laser-offset and
`axes[2]/[3]` rules. Per hand: trigger (value + touch), squeeze (value),
thumbstick (click + touch + axes), X/Y or A/B (click + touch), thumbrest
(touch), haptics. **Menu (left) and System (right) are mapped to Wolvic's own
"app" button and flagged reserved — they never reach the page.**
**Hand tracking is deliberately disabled** on this device
(`XR_EXT_HAND_TRACKING` removed because controller poses froze with it on);
Spaces' hand-interaction profiles are also dropped. Controllers only.

**Poses.** Standard Oculus Touch grip and aim poses; nothing is adjusted for
kit apps. The fork's "pose override" (grip lowered 0.4 m) applies only to
`moonrider.xyz`, `aframe.io/a-painter`, `immerseme.co`, or a URL with
`pose_override=true` — never add that param.

**Refresh rate — why the diary says 72 fps.** `UpdateDisplayRefreshRate()`
asks the runtime for the lowest rate ≥ a per-device target; Quest/Pico get
90, `AvantisCVR655` is not listed and falls to the **60 Hz default**, so the
first rate the runtime offers at or above 60 is chosen — **72 Hz** on this
panel. The kit's measured 72 fps is therefore the session's ceiling, not a
performance problem. Adding `device::AvantisCVR655` to the 90 Hz case in
`app/src/openxr/cpp/DeviceDelegateOpenXR.cpp` would give 90 Hz (an Avantis
Wolvic release, not a kit change). Until then: **72 = full speed; budget for
72; well under 60 = too heavy.** MSAA uses the runtime's recommended count.

**Sleep and wake.** The fork **keeps the WebXR session alive across sleep**
(upstream Wolvic ended it): frames are suppressed while asleep and re-synced
on wake, pose intact. So an app resumes mid-session; expect no
`pagehide`/`visibilitychange` "end" on sleep, and a diary that simply
continues. Exiting VR without AutoXR returns to the 2D window; with the
headset's Back/home you leave Wolvic and the `end` beacon may not be written
(the `vr` exit beacon carries the summary instead).

**What reaches the Android log.** `Session.onLoadRequest` does
`Log.d("VRB[Session]", "onLoadRequest: " + uri)` for every main-frame
navigation, including same-document `replaceState`/hash changes, and the
release build is not minified — this is the logbook channel
(`check-headset/references/logbook.md`). Web console output is **not**
forwarded to the log.

## Observed on the headset (kit runs)

- Controllers report as `meta-touch`; VR enter/exit, flags and 72 fps all
  read back through the logbook (Logbook Test build 2, 8 Sep 2026).
- The device checks in with ClassCloud about every 10 min while awake and
  never while asleep, which sets the latency of `/check-headset`.
- **3DoF is simulated.** The device is 6DoF; a kit app with `dof: 3` throws
  positional tracking away itself. The real ClassVR 3DoF headsets do not run
  Wolvic, so this is the only device kit apps are tested on.

## Unknown — fill in when found, never invent

Battery life, weight, IPD adjustment range, cameras / passthrough, audio
(speakers, jack), the tracking volume, the exact runtime-advertised refresh
rate list (72 is inferred from the measured fps and the selection rule), and
whether ClassCloud preserves the `wolvic-launchimmersive-…` query parameter
on a URL activity.

## What follows for a kit app

**Legibility.** 1920 px across 105° ≈ **18 pixels per degree** — a fraction of
a monitor's. Text wants to be **≥ 1.5° tall**: about **5 cm at 2 m, 8 cm at
3 m**. Draw canvas textures at least twice the pixels they will cover on the
panel (a 1 m sign at 2 m spans ~28° ≈ 520 px, so a canvas ≥ 1024 px wide),
and keep strokes ≥ 2 canvas px or they shimmer. The pre-VR 2D window is
small (≈900 × 600 at scale 2) — the panel's compact layout is what testers
see before they press the VR button.

**Budget.** XR2 Gen 1 is a mobile GPU drawing two 1920² eyes 72 times a
second. Working budgets, not measured limits: under ~100 k triangles and
~100 draw calls in view, textures ≤ 2048², no real-time shadows unless asked
for, no post-processing, physics bodies in the tens. When the diary says the
fps fell below ~60, simplify before optimising code.

**Buttons.** Triggers, grips, thumbsticks and A/B/X/Y are the app's (within
the kit's reservations: both triggers held = flag; sticks = move / snap
turn). Menu, System, Back and volume never arrive. No hand tracking, no
headset-gaze input from the runtime — the kit's 3DoF gaze select is its own.

**Web platform.** Write for Chrome 124: WebGL 2 and three.js r173's default
path are fine; don't reach for WebGPU, WebXR layers, AR or hand-tracking
APIs. The colour-space rule (linear out in VR) is about Wolvic's compositor,
not the GPU.
