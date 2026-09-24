---
name: check-headset
description: This skill should be used when the user asks to "check the headset", "what happened on the headset", "read the headset log", "did it work in VR", "why did it break in the headset", "get the logs from the headset", "check what went wrong when I played it", or invokes /check-headset. After someone has played a kit app on a ClassVR headset, it asks the headset for its log through ClassCloud, pulls out the app's own diary (errors with codes, warnings, everything the app printed, flags the player marked, VR entered or not, frame rate), merges it with any reports from the app's link, and explains in plain words what happened — no cables, no developer settings, nothing typed by the player.
---

# Check headset

The headset route for the kit's diary. A kit app running on a ClassVR headset
writes its diary into the headset's own log by rewriting its page address (see
`window.KIT` → logbook in the template); ClassCloud can fetch that log from the
headset on request. This skill does the fetching and the reading. The person's
part is: play the app, **go back to the ClassVR home screen**, then ask.

Read `references/logbook.md` once per session for how the beacons are encoded
and what can go wrong.

## Outcome

One plain-words account of the most recent session(s) of the app on the
headset: which build ran, whether it entered VR, how long, any errors (with
their `<build>-<line>` codes) and warnings, the ten seconds before each flag,
and anything the headset itself logged (page never loaded, OpenXR trouble).
Then — if something broke — the fix, exactly as `xr-app-rules` describes.

## Steps

### 0. An app on Vercel: read the diary there first

If `xr-project.json` has `vercel.url`, the app posts its diary to its own
Vercel project as it runs — from the headset, a desktop browser or a shared
link alike — and it can be read back with no log request and no need for the
headset to be on its home screen. Do this first, as `/publish-to-vercel`
("Reading what happened") describes. **Token route** (the normal one — no
connector; `vercel.via` is `"token"` or the connector is absent): go straight
to the app's own history below, read in a built-in browser tab — it is
public, so no token is needed to read it. **Connector:**
`get_runtime_logs` with `projectId` = `vercel.projectId`, `teamId` =
`vercel.teamId`, `deploymentId` = `vercel.deploymentId`, `since` = `"1h"`,
`query` = `"kit-diary"`. The headset shows as an `Android … Mobile VR` user
agent. If sessions are there, go straight to step 6 with them. If nothing is
there (the play was more than an hour ago on Vercel's free plan, or the
connector is off in this chat), try the app's own history next — every session
that reached VR or closed the page left a record that outlives the log:
`<vercel.url>/api/reports` (a browser tab, or `web_fetch_vercel_url`) for a line per session
(add `?day=YYYY-MM-DD` for one day, `?session=<id>` for every diary entry of
one). A session is written when the player leaves VR or closes the page, so
if they are still in VR, ask them to come out first. That answers "what happened in Tuesday's lesson?" on Friday. Only if
both are empty, say so in one line and continue with the ClassCloud log
below — it still works for these apps.

### 1. Which app, which headset

Find the project folder (`xr-project.json`). Read `classcloud.organizationId`
and `slug`. If there is no `classcloud` block the app has never been published
— say so; there is nothing on a headset to read.

`get_devices_for_organization` for the organisation. Choose the headset:

- One device with `lastAccess` in the last 24 hours → use it, say which.
- Several → ask **once** with AskUserQuestion, options = their names (most
  recent first, up to four), or "all of them".
- None recent → still proceed with the most recent, but say it may be off.

### 2. Ask for the log

Note the current UTC time (`date -u`). Then
`set_device_command` `{ method: "SEND_LOGS" }` for the chosen device id(s).

Tell the user in one line: "Asked the headset for its log — this takes a few
minutes; it only answers from the home screen." Do not ask them to do anything
else.

### 3. Wait for it

Poll `get_device_logs` for the device: **every 60 seconds, up to 10 minutes**
(`sleep 60` in Bash between calls). Stop as soon as a result has `create` later
than the time noted in step 2. Existing entries are earlier logs — useful as a
fallback (see failure handling), not the answer.

**A sleeping headset never checks in.** After the first 3–4 minutes with no
new log, read `get_device_properties` (`LAST_ACCESS`) for the device. If it is
earlier than your request, the headset has not contacted ClassCloud since — it
has gone to sleep (taken off the head) or is off. Say so plainly and ask them
to wake it (put it on, or press the power button once) and leave it on the home
screen; the log usually arrives within a minute of waking. Keep polling. If
nothing has arrived after 10 minutes in total, stop, say what you saw, and
offer to try again. Measured: ~10 min when the headset stayed awake, ~20 min
when it slept until nudged. The log upload itself does not update
`LAST_ACCESS`, and its label may say `LOCAL_USER_REQUEST` — both are normal.

### 4. Download and read

    curl -sL -o /tmp/headset.log "<logUrl>"
    python3 /root/.claude/plugins/synced/2606ec73-0328-4925-84de-5e3387c5460a_efef4036-254f-4e69-806f-fb6c79b26b36/classvr-prototyping-kit/skills/check-headset/scripts/headset_diary.py \
        --log /tmp/headset.log --app "<App Name or slug>" --json /tmp/headset.json --summary

The summary is for you to read, not to paste. `/tmp/headset.json` has every
session (`sessions[]`, newest last) with `entries` (the full diary in order),
`errorList`, `flags`, `beacons`, `enteredVR`, `fps`, `controllers`, `dof`, `lock`,
`pageLoads` (every page Wolvic opened) and `notable` (headset-level lines).

The log holds several hours, so **older sessions of the same app are in there
too**. Report the most recent one unless the user asked about an earlier play.
Timestamps are the headset's local clock.

### 5. Merge with the link's reports

If the manifest has `artifact.url` and `artifact.mailbox` is true, also
`Artifact action: "read_db"` (`db_op: "query"`, `collection: "reports"`,
ordered by `updated` desc, limit 10). Those are browser sessions of the same
app. The headset diary and the mailbox reports share one format; treat them as
one set of sessions and say which came from where only if it matters.

### 6. Tell the story

In plain words, a short paragraph, no field names:

- Build that ran, and whether it matches the current build (a stale headset
  is the commonest "bug": the playlist opens the URL the activity had at
  publish time, so a headset that never went home may show the old one).
- Entered VR or not. Never entering VR with `webxr: false` means the page ran
  outside Wolvic's XR context; with `webxr: true` and no `vr` beacon the
  player may simply not have pressed the VR button.
- Errors: the **first** one first, its code, the line it points at. Open
  `dist/<slug>-build<N>.html` at that line (rebuild with `build.py` if the
  file is gone; builds are deterministic).
- Flags: what the diary shows in the ten seconds before each — the last
  press, controller event or `[xr-kit]` line is usually the story — then ask
  one question: "at the moment you marked it, what did you see?"
- Nothing wrong: say so, with the numbers that show it ran (duration, fps,
  presses). On the Xcelerate about 72 fps is full speed even though the
  panel is 90 Hz (Wolvic requests 72 Hz on this device — see
  `../xr-app-rules/references/classvr-xcelerate.md`); well under 60 means
  the scene is too heavy for the headset — say so, and simplify before
  looking for a bug.
- A 3DoF app (`dof` 3): also say whether the head lock held — `lock` is
  `[moved, held, frames]`; "you moved about 0.4 m and the view gave about
  0.12 m, as designed" is the sentence (the kit lets `give` = 0.3 of real
  movement through on purpose, so `held` ≈ 0.3 × `moved`). `held` well above
  that, or no `lock` at all after entering VR, means the simulation is broken
  and is the first thing to fix.

Then fix it, following `xr-app-rules`. A fix ends with the usual preview →
share → publish, and "when you've played the new build, ask me to check the
headset again".

## Failure handling

- **No kit diary in the log but the page did load** (`pageLoads` shows the
  avnfs URL): the build predates the logbook (kit < 0.12) — republish and play
  again — or the page died before its first script ran; read `notable`.
- **Page not in `pageLoads` at all**: the headset opened something else, or
  the log was taken before the play. Check the build number on the panel with
  the user.
- **`incompleteBeacons` > 0**: the log was cut while a beacon was being
  written; the rest of the session is still valid.
- **Only an old log comes back** (`create` before the request): the command
  has not been picked up yet — keep polling within the 10 minutes; do not
  report the old log as if it were new.
- **403 on `set_device_command`**: the account's role on that organisation
  cannot request logs. Say so; the artifact mailbox still works for browser
  sessions.
