---
name: preview-xr-app
description: >
  This skill should be used when the user asks to "preview my XR app", "check the app
  works", "show me what it looks like", "test the VR app", "does it still run", or
  invokes /preview-xr-app. It loads the app in a headless browser, confirms it
  starts cleanly, and returns a screenshot plus a plain-English health check. Also
  run automatically by /publish-xr-app before anything is uploaded.
metadata:
  version: "0.2.0"
---

# Preview XR app

Prove the app works before anyone puts a headset on. This is the check that
catches the whole "looks like a working app but isn't" class of failure: a library
that didn't load, a typo that threw on start-up, a scene that never finished
loading.

## Steps

1. **Locate the project.** The folder containing `index.html` and
   `xr-project.json`. If the user has one XR project in the connected folder, use
   it; if several and the request doesn't say which, ask once.

2. **Get the files where the script can reach them.** In a cloud session stage
   `index.html`, every `<script src="./…">` file it references (`aframe.min.js`,
   and `cannon.iife.js` if present), and `xr-project.json` into the workspace,
   preserving the folder layout. In a local session run against the folder
   directly.

3. **Run the check.**

       python3 ${CLAUDE_PLUGIN_ROOT}/skills/preview-xr-app/scripts/preview.py \
           --file "<project>/index.html" --out "<project>/.preview"

   It serves the folder locally, loads the page in headless Chromium, waits for
   A-Frame to settle, and checks for JavaScript errors, console errors, failed
   requests, that A-Frame loaded, that the scene finished loading and produced a
   WebGL canvas, and that the kit's rig component is attached. Then it takes the
   screenshot and runs the **self-checks** — the kit's built-in ones (library,
   scene, rig, the player can walk) followed by the app's own
   `window.KIT_CHECKS` — and finally collects the app's **diary**
   (`window.KIT.report()`). It writes `preview.png` and `preview.json`; the
   JSON has `problems` (plain sentences), `checks` (`name`, `ok`, `detail`) and
   `diary` (`errorList` with file:line, the last 40 events, `fps`,
   controllers, presses).

   Exit codes: `0` pass, `1` fail, `3` the check could not run at all (no
   headless browser available). Treat `3` as "unverified", not as a failure.

   The script finds a browser on its own: Playwright's own Chromium if the
   revision matches, otherwise any Chromium already on the machine
   (`PLAYWRIGHT_BROWSERS_PATH`, `/opt/pw-browsers`, `PATH`), and as a last
   resort `playwright install chromium`. **Don't hand-build symlinks or shims
   to make a browser revision "match"** — if it exits `3`, read its `reason`
   and `hint`; if a browser exists at a path the script didn't try, set
   `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to it and run again.

4. **Report in plain language.** Send `preview.png` with `display: "render"` so it
   opens in the side panel — but only when previewing is the point of the turn.
   If this check is running inside `/publish-xr-app`, send nothing: the QR code
   is what gets rendered there, and a screenshot sent after it would push the QR
   off the screen. Then one or two sentences:

   - Pass: "Loads cleanly — A-Frame 1.7.1, build 4, no errors." Mention anything
     notable in the screenshot.
   - Fail: name the problem in the user's terms and fix it. Read the first
     entry of `diary.errorList` before anything else — one thrown error at
     start-up stalls the scene and fails several checks at once, so the root
     cause is the earliest error, not the longest list. `"AFRAME is not
     defined"` means the library file is missing from the folder; a thrown
     error usually points at the most recent edit; a failed check names the
     promise that broke ("a ball appears when you press the trigger") and why.
     Fix, re-run, and only report success once it passes. Never ask the user
     for console output — everything the console would show is in the diary.
   - "This app predates self-checks": an app scaffolded before `window.KIT`
     existed. It still passes the load checks; offer to bring it up to date
     (copy the current template's `KIT_CHECKS`/`KIT` blocks and the `xr-kit`
     component in, leaving the content alone).
   - Unverified: say the automatic check couldn't run here, and that
     double-clicking `index.html` is the fallback.

## What the preview does not tell you

It runs without a headset, so `immersive-vr` will always read as unavailable —
that's expected and is not a failure. It cannot see controller input, colour on
the headset display, or performance on the device. For those, publish and scan.
