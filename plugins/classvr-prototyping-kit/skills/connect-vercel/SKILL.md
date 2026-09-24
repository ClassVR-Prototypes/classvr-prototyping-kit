---
name: connect-vercel
description: >
  This skill should be used when the user asks to "connect my Vercel account",
  "set up Vercel", "add my Vercel token", "my Vercel token expired", "Vercel
  stopped working", "forget my Vercel token", or invokes /connect-vercel. It is
  also run by /publish-to-vercel (and anything else that talks to Vercel) when
  no Vercel connection is stored yet. It walks the person through making a
  Vercel access token, has them paste it into a box in Claude's built-in
  browser — never into the chat — keeps it in that browser only, checks it
  works, and records the non-secret account details in the kit's settings
  file. No Vercel connector needed afterwards.
metadata:
  version: "0.1.0"
---

# Connect Vercel

Replaces the Vercel connector. Once this has run, every Vercel step in the kit
(publishing, versions, play history, the headset diary) goes through the
**Vercel bridge**: a small script run in the built-in browser pane on
`https://api.vercel.com`, which reads the token from that site's browser
storage and makes the calls itself.

Why the browser: Vercel's API is not on the network allowlist of either the
cloud workspace or the shell on the person's computer (both answer
`blocked-by-allowlist`), but the built-in browser reaches it. And because the
token lives in that browser's storage for `api.vercel.com`, it never appears
in the chat, in a file or in the project folder.

## The rules about the token

- **Never ask the person to paste the token into the chat**, and never read it
  from a file, type it, or put it in a command. If they paste it into the
  chat anyway: do not repeat it, use the box as normal, and suggest in one
  line that they delete that token in Vercel and make a new one, because the
  chat now holds it.
- **Never type or paste the token into the box yourself.** The person does
  that.
- No bridge function returns the token. `KV.status().tokenEnds` (last four
  characters) is the most you ever show, and only when they ask which token
  is stored.
- The token lives only in this computer's built-in browser. Another computer,
  or clearing the browser's data, means running this skill again. Say so only
  if it comes up.

## Loading the bridge (every time, for every skill)

1. Open or navigate a browser-pane tab to `https://api.vercel.com/v2/user`.
   (It shows a "missing authentication token" message — that is expected; the
   page is only there so the script runs on Vercel's own site.)
2. `javascript_tool` with the full text of
   `${CLAUDE_PLUGIN_ROOT}/skills/connect-vercel/assets/vercel-bridge.js`
   (Read it, paste it verbatim). It ends by printing `KV ready — {status}`.
3. Everything else is `await KV.<function>(…)` in later `javascript_tool`
   calls on the same tab. Navigating the tab away from `api.vercel.com`
   unloads it — to look at a published page, open it in a **second tab**
   (`preview_start`) and keep the bridge tab where it is.

| Function | What it does |
|---|---|
| `KV.status()` | `{connected, username, teamId, teamSlug, savedAt, tokenEnds}` — never the token |
| `await KV.check()` | token still accepted and can see projects? (`ok`, `reason`) |
| `KV.setupBox()` | draws the paste box; poll `KV.setupResult.state` |
| `KV.forget()` | removes the stored connection |
| `await KV.api(path, {method, body})` | any Vercel REST call; `teamId` is added → `{status, ok, body}` |
| `await KV.ensureProject(name)` | creates the project if missing (framework: none), returns `{projectId, url}` — the **real** public address |
| `await KV.deploy({name, target, projectSettings, files, expect})` | checks every inline file's SHA-1 against `expect`, deploys, waits for READY → `{ok, id, projectId, alias, readyState}` |
| `await KV.createStore(name, projectId)` | Blob store for play history, connected to the project → `{storeId, tokenSet}` |
| `await KV.deployments(projectId, n)` | the last n publishes |
| `await KV.sha1(text)` | fingerprint of a string |

If `KV.status().connected` is false, or `KV.check()` says the token was
refused (expired or deleted in Vercel), run the setup below, then carry on
with whatever the person asked for.

## Setup

### 1. Is it already done?

Load the bridge. `KV.status()` connected and `await KV.check()` ok → say
"You're already connected to Vercel as <username>." and stop (or carry on
with the task that sent you here).

### 2. Make the token

Open `https://vercel.com/account/settings/tokens` in a **second** browser-pane
tab (`preview_start`). If Vercel asks them to sign in or create an account,
they do that themselves (accounts are for people 16 and over; staff should use
their work email). Before asking them to do anything in the browser, call
`tabs_context` and make sure the pane is showing (see the browser rules).

Then tell them, in one short message:

> In the Vercel tab: under **Create Token**, give it a name like *ClassVR
> Prototyping Kit*, set **Scope** to your own account (the one with your
> name), choose an **Expiration** (a year is fine), press **Create**, then
> **Copy** the token. Don't paste it here — I'll give you a box for it.

### 3. Paste it into the box

Switch back to the bridge tab (`tabs_select`), run `KV.setupBox()`, check the
pane is showing, and say: "Paste the token into the box in the browser and
press Save." Then wait for their reply (or poll `KV.setupResult` a few times,
a few seconds apart, if they are clearly at the screen).

`KV.setupResult.state`:

- `connected` → go on.
- `refused` → the token was mistyped or not fully copied: ask them to copy it
  again from Vercel (it is shown only once — if it's gone, make another).
- `no-projects` → the token's scope is wrong: make another with **Scope** set
  to their own account.
- `waiting` → they haven't pressed Save yet.

The box draws over the tab; `KV.setupBox()` again redraws it, and navigating
the tab reloads the page and clears it.

### 4. Record the non-secret details

Add to the kit's settings file `<connected folder>/.classvr-kit.json` (the
same file that remembers the ClassCloud organisation; create it if missing,
keep the other keys) with a short read-modify-write on the person's computer:

    "vercel": { "username": "<username>", "teamId": "<team_…>",
                "via": "token", "connectedAt": "<ISO date>" }

**Never the token.** This file tells later sessions that the person uses the
token route and which account to expect, so a session that finds the browser
empty (another computer, cleared data) knows to run setup instead of asking
for the connector.

### 5. Tell them

One or two sentences: connected as <username>; from now on "put it on
Vercel", "what happened on the headset" and version history all work without
the connector; the token is stored in Claude's browser on this computer only,
and if it ever expires they just say "connect my Vercel account" again.

## Forgetting

"Forget my Vercel token" / "disconnect Vercel": load the bridge, `KV.forget()`,
set `vercel.via` to `"none"` in `.classvr-kit.json`, and suggest they also
delete the token on the Vercel tokens page so it can't be used anywhere.

## Known limits

- Needs the Claude desktop app open on that computer: the built-in browser
  runs there. If the browser tools aren't available, say plainly that Vercel
  steps need the Claude app open, and stop.
- An organisation admin can add `api.vercel.com` to Claude's network
  allowlist; the cloud workspace could then call Vercel directly. The kit
  does not use that route yet (it would need the token somewhere the
  workspace can read it).
- The runtime-log stream (`/v1/projects/…/deployments/…/runtime-logs`) did not
  answer through the browser within 10 s when tried (24 Sep); read the diary
  from the app's own `/api/reports` instead — see `/publish-to-vercel`,
  "Reading what happened".
