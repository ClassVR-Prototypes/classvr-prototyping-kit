# The logbook: how a headset diary reaches Claude

Facts established 2026-09-07 on a ClassVR headset (Wolvic, Chromium backend,
Avantis build 1.2.x), kit 0.12. Everything here was measured, not assumed.

## Why this works

- Wolvic's `Session.onLoadRequest` logs every main-frame navigation start:
  `D VRB[Session]: onLoadRequest: <url>`. The release build has ProGuard's
  `Log` stripping disabled (`minifyEnabled` is commented out), so `Log.d`
  survives.
- Chromium fires `didStartNavigationInPrimaryMainFrame` for **same-document**
  navigations too: `history.replaceState` and `location.hash =` both produce
  the line, without reloading the page or disturbing a live XR session
  (`vr: true` beacons kept arriving every 5 s during the test).
- A **3,619-character** line arrived intact, so one beacon part carries up to
  3,000 characters of base64url; longer beacons are split into parts.
- ClassCloud collects the log with `set_device_command SEND_LOGS`; the headset
  picks the command up on its next check-in (**~1–4 minutes**, home screen
  only) and `get_device_logs` then lists the new file (~14 MB of logcat,
  several hours of history).
- Console output is **not** in the log (the ClassVR Wolvic build swallows
  `console.*`), which is why the diary has to carry it. Nothing else needs
  changing: no Wolvic rebuild, no developer settings, no cable, no server.

## The wire format

    #kit=<session>-<beacon no>-<part>-<parts>.<base64url(JSON)>

`session` is the same id the artifact mailbox uses (`s` + base36 time +
random), so a page's diary is one session whichever route it took.

JSON body, compact keys:

| key | meaning |
|---|---|
| `v` | format version (1) |
| `k` | why this beacon was sent: `boot` (before libraries load), `start` (load + 4 s), `error`, `flag`, `vr` (entered or left VR), `beat` (every 30 s), `end` (page hidden or left) |
| `b`, `t` | build number, seconds since the page started |
| `st` | `loading` / `ok` / `errors` / `flagged` |
| `vr`, `ev` | presenting right now / has ever presented |
| `fps`, `c`, `p`, `tn` | frame rate, controllers seen, presses, snap turns |
| `dof` | (start only) which headset the app is designed for: 3 or 6 |
| `lk` | 3DoF apps, while/after the lock ran: `[moved, held, frames]` — metres the player really moved from where they started, metres the view was allowed to give (≈ `give` × moved, default give 0.3; more than that means the lock is not holding), frames locked |
| `e`, `f` | error count, flag count |
| `d` | diary entries **added since the previous beacon**: `[i, t, kind, text, code?, "xN"?]` — `i` is the entry's running number, `xN` means the same line repeated N times |
| `dropped` | entries that did not fit (more than 40 new entries between beacons) |
| `app`, `browser`, `platform`, `webxr`, `secure`, `ua` | only on `boot` and `start` |

Diary `kind`s: `error` (with a `<build>-<line>` code), `warn`, `log`
(everything the app or xr-kit printed, 200 chars each), `flag`, `check`.

## What the reader does

`scripts/headset_diary.py` groups beacons by session, reassembles parts,
decodes, and orders entries by `i`. It also lists every page Wolvic opened
(`pageLoads` — the avnfs `name=` parameter carries `<slug>-build<N>.html`, so
the build that actually ran is known even if no beacon decoded) and keeps
headset-level lines that matter (`notable`: OpenXR session state, crashes,
low memory, load failures).

## Limits

- Latency is the headset's check-in: minutes, not seconds, and only from the
  home screen. This is a "play, then ask" route, not a live one.
- The log is a ring buffer; a very long day on one headset may push a morning
  session out.
- A page that never ran its first script leaves no diary — only the
  `pageLoads` line and whatever Wolvic logged.
- Logcat timestamps are the headset's local clock with no year or zone.
