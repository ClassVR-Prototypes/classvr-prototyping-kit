---
name: check-headset
description: This skill should be used when the user asks to "check the headset", "what happened on the headset", "read the headset log", "did it work in VR", "why did it break in the headset", "get the logs from the headset", "check what went wrong when I played it", "did anyone have problems", or invokes /check-headset. After someone has played a kit app from its Vercel link — on a ClassVR headset or in a browser — it reads the app's own play history on Vercel (errors with codes, warnings, everything the app printed, flags the player marked, VR entered or not, frame rate) and explains in plain words what happened — no cables, no developer settings, nothing typed by the player.
metadata:
  version: "0.5.0"
---

# Check headset

Every kit app on Vercel posts its diary to its own Vercel project as it runs —
from a headset, a desktop browser or a shared link alike — and keeps one copy
of each session in the project's play history. This skill reads that back and
tells the story. The person's part is only: play the app, then ask. Nothing
has to be done on the headset.

## Outcome

One plain-words account of the most recent session(s) of the app: which
version ran, where (headset or browser), whether it entered VR, how long, any
errors (with their `<build>-<line>` codes) and warnings, the ten seconds
before each flag. Then — if something broke — the fix, exactly as
`xr-app-rules` describes.

## Steps

### 1. Which app

Find the project folder (`xr-project.json`). It needs `vercel.url`. If there
is none, the app has never been published on Vercel, so there is nothing to
read — say so in one line and offer to publish it (`/publish-to-vercel`);
sessions played after that will be there.

### 2. Read the history

Follow `/publish-to-vercel`, "Reading what happened":

- **Token route** (the normal one — `vercel.via` is `"token"` or the
  connector is absent): read `<vercel.url>/api/reports` in a built-in browser
  tab. It is public, so no token is needed. Add `?day=YYYY-MM-DD` for one day
  or `?session=<id>` for every diary entry of one session.
- **Connector, within the hour:** `get_runtime_logs` scoped to
  `vercel.deploymentId` with `query` = `"kit-diary"` has every post, including
  sessions still running. Older than the hour (Hobby plan) → the history
  above.

A session reaches the history when the player leaves VR or closes the page.
If they are still in VR, ask them to press the VR button to come out, then
look again. The headset shows as an `Android … Mobile VR` device; a desktop
user agent is a browser.

Report the most recent session unless the user asked about an earlier play
("what happened in Tuesday's lesson?" → `?day=`).

### 3. Tell the story

In plain words, a short paragraph, no field names:

- Version that ran, and whether it matches the current one (a headset that
  kept an old tab open may show an older version — the panel shows the
  number).
- Headset or browser, and entered VR or not. Never entering VR on the
  headset with `webxr: false` means the page ran outside Wolvic's XR context;
  with `webxr: true` and no `vr` post the player may simply not have pressed
  the VR button.
- Errors: the **first** one first, its code, the line it points at. An error
  in the app's own code keeps its `<build>-<line>` code with the line counted
  in the slim page (open `dist-vercel/page/index.html` from the build, or
  rebuild it); an error inside the shared library is coded `<build>-lib`.
- Flags: what the diary shows in the ten seconds before each — the last
  press, controller event or `[xr-kit]` line is usually the story — then ask
  one question: "at the moment you marked it, what did you see?" Ignore a
  flag whose text ends in `PASS the "something wrong" marker works` — that is
  the self-check, not a person.
- Nothing wrong: say so, with the numbers that show it ran (duration, fps,
  presses). On the Xcelerate about 72 fps is full speed even though the
  panel is 90 Hz (Wolvic requests 72 Hz on this device — see
  `../xr-app-rules/references/classvr-xcelerate.md`); well under 60 means
  the scene is too heavy for the headset — say so, and simplify before
  looking for a bug.
- A 3DoF app (`dof` 3): also say whether the head lock held — `lk` is
  `[moved, held, frames]`; "you moved about 0.4 m and the view gave about
  0.12 m, as designed" is the sentence (the kit lets `give` = 0.3 of real
  movement through on purpose, so `held` ≈ 0.3 × `moved`). `held` well above
  that, or no `lk` at all after entering VR, means the simulation is broken
  and is the first thing to fix.

Then fix it, following `xr-app-rules`. A fix ends with the usual preview →
publish, and "when you've played the new version, ask me to check again".

## Failure handling

- **Nothing in the history** and nothing in the hour's log: the session may
  still be running (ask them to come out of VR), or the page never got as far
  as its first script — the history cannot see a page that never loaded.
  Ask what the headset showed (a blank page, an error screen, the home
  screen) and check the address they opened matches `vercel.url`.
- **`{"ok":false,"reason":"no history store…"}`**: the app was published
  before play history existed, or the store was never connected — offer to
  add it (`/publish-to-vercel` step 6b, then a republish).
- **Sessions only from browsers**: the headset never opened this Vercel
  link — it may have opened an old copy from somewhere else, which reports
  nothing. Point it at the page's QR code.
