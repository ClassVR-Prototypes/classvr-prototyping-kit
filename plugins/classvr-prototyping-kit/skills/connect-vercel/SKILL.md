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
  file. This is the only way the kit talks to Vercel. It also holds The
  check that every Vercel job runs first, and a word-for-word setup script so
  every person gets the same steps in the same words.
metadata:
  version: "0.3.0"
---

# Connect Vercel

The kit's only link to Vercel — no connector, nothing to install. Once this
has run, every Vercel step in the kit
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
  chat anyway: do not repeat it or use it — reply with message **X**.
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
2. **During a publish** there is nothing to do here: every browser script
   `/publish-to-vercel` prints carries the part of the bridge it needs.
   **On its own** (this skill, or any other Vercel step outside a publish):
   `javascript_tool` with the full text of
   `${CLAUDE_PLUGIN_ROOT}/skills/connect-vercel/assets/vercel-bridge.js`
   (Read it, paste it verbatim). It ends by printing `KV ready — {status}`.
   Never load the bridge from a web address and run it — a permission check
   will (rightly) refuse downloaded code in the tab that holds the token.
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
| `await KV.deploy({name, target, projectSettings, files, expect, sources})` | checks every inline file's SHA-1 against `expect`, deploys (uploading any by-fingerprint file Vercel lacks from its `sources` copy), waits for READY → `{ok, id, projectId, alias, readyState, uploaded}` |
| `await KV.createStore(name, projectId)` | Blob store for play history, connected to the project → `{storeId, tokenSet}` |
| `await KV.firstPublish(slug, {suffix})` | first publish in one call: names the project, creates it, reads its real address, makes its play-history store |
| `await KV.deployments(projectId, n)` | the last n publishes |
| `await KV.sha1(text)` | fingerprint of a string |

Whether a connection exists is decided by **The check** below, never by
guessing from the settings file.

## The check (the first thing every Vercel job does)

`/new-xr-app`, `/publish-to-vercel` and every edit that will end in a publish
run this **before anything else in the job** — before asking the app's name,
before building, before any other message. It is quiet: nothing is said to
the person unless it finds a problem.

1. No built-in browser tools in this session → reply with message **B** and
   stop.
2. Open a tab at `https://api.vercel.com/v2/user` (`preview_start`; reuse a
   tab already there) and run the full text of
   `${CLAUDE_PLUGIN_ROOT}/skills/connect-vercel/assets/check-connection.js`
   with `javascript_tool`, verbatim. It returns `state`:
   - `connected` → say nothing about Vercel; carry on with the job.
   - `not-connected` → **Setup**, from turn 1.
   - `refused` → **Setup**, from turn 1 with message **M1r** and no account
     question (they have an account).

Remember the job the person asked for; it resumes after message **F**.

## Setup — the script

Every person gets the same setup, in the same order, in the same words.

**How to send the messages.** Each message below is sent **word for word**:
the text inside its block, exactly, without the block's fence — no words
added before or after it, none changed, nothing reworded, summarised or
"improved", even if you would phrase it better. The one placeholder is
`{username}` in **F** and **A**. A message that ends a turn is the whole
reply for that turn. A message sent while the turn carries on (**M1**, **F**)
goes out with `SendUserMessage` — plain text between tool calls is shortened
before the person sees it, so it would not arrive word for word.

**One step per turn.** After each step's message, stop and wait for the person
to reply. Anything meaning "done" moves on to the next turn. If they ask a
question or say something else instead, answer it in one or two plain
sentences, then send the **same step's message again**, word for word. If they
paste the token into the chat, do not repeat it or use it: reply with **X**,
and the next "done" goes to turn 4.

Before any message that asks them to do something in the browser panel, call
`tabs_context`. Panel hidden or not open → reply with **H** instead; on their
"done", check again and then send the step's message.

Two tabs are used, and only these two: the **Vercel tab** (Vercel's own
website) and the **box tab** (`https://api.vercel.com/v2/user`, the tab the
check used). Whenever a message points them at one, select it first
(`tabs_select`) so it is the one the panel shows.

### Turn 1 — introduce, ask, open Vercel

1. `SendUserMessage` with **M1** (or **M1r** when the token was refused).
2. **Only after M1:** `AskUserQuestion` with exactly this — question
   `Do you already have a Vercel account?`, header `Vercel`, not multi-select,
   options:
   - `Yes, I have one` — description `I'll open Vercel so you can sign in.`
   - `No, not yet` — description `I'll open Vercel so you can make a free account.`
   Anything typed instead: an answer meaning yes or no counts as that option;
   otherwise ask the same question once more.
3. Open the Vercel tab (`preview_start`): **Yes** (and after **M1r**) →
   `https://vercel.com/login`; **No** → `https://vercel.com/signup`.
4. Read the tab's address. Vercel moved it away from `/login` or `/signup`
   (they are already signed in) → go straight to turn 2, step 1, in this same
   turn — no sign-in message.
5. Otherwise reply with **M2a** (Yes) or **M2b** (No). End the turn.

### Turn 2 — the token page

1. Navigate the Vercel tab to `https://vercel.com/account/settings/tokens`
   and read its address.
2. It landed on a sign-in page → reply with **N**. End the turn; on "done",
   repeat this turn.
3. Otherwise reply with **T**. End the turn.

### Turn 3 — the box

1. Select the box tab. Load the bridge (see "Loading the bridge": paste
   `vercel-bridge.js` verbatim), then run `KV.setupBox()`.
2. Reply with **P**. End the turn.

### Turn 4 — did it save?

Read `KV.setupResult.state` on the box tab (bridge gone because the tab
reloaded → load it again; `KV.setupResult` null → treat as `waiting`):

- `connected` → record the details (below), `SendUserMessage` with **F**,
  then carry on with the job the person asked for. When connecting *was* the
  job, **F** is the whole reply.
- `refused` → select the Vercel tab, reply with **R**; on "done", turn 3.
- `no-projects` → select the Vercel tab, reply with **S**; on "done", turn 3.
- `waiting` → reply with **W**; on "done", turn 4 again.
- `error` → reply with **E**; on "done", turn 4 again.

**Record the details.** Add to the kit's settings file
`<connected folder>/.classvr-kit.json` (create it if missing, keep any other
keys) with a short read-modify-write on the person's computer:

    "vercel": { "username": "<username>", "teamId": "<team_…>",
                "via": "token", "connectedAt": "<ISO date>" }

**Never the token.** This file tells later sessions that the person uses the
token route and which account to expect.

### Asked to connect when already connected

The check says `connected` and connecting was the whole request → reply with
**A**, nothing else.

## The messages

**M1** — the introduction
~~~
Before we start, I need to connect to your Vercel account. Vercel is the free website that hosts your apps so they open on a headset. You only do this once on this computer, and it takes about five minutes.
~~~

**M1r** — the stored token stopped working
~~~
Before we start, I need to reconnect to your Vercel account — the connection has stopped working, probably because the token expired. You'll make a new token, and it takes about five minutes.
~~~

**M2a** — sign in
~~~
I've opened Vercel in the browser panel. Sign in the same way you did when you made your account — with email, Google, GitHub or whichever you used.

When you're signed in, come back here and type **done**.
~~~

**M2b** — make an account
~~~
I've opened Vercel's sign-up page in the browser panel. To make your free account:

1. Choose **Hobby**.
2. Type your name.
3. Choose how to sign up — your work email is best.
4. Follow Vercel's steps until you see your Vercel dashboard.

Vercel accounts are for people aged 16 and over.

When you can see your dashboard, come back here and type **done**.
~~~

**N** — not signed in yet
~~~
It looks like you're not signed in to Vercel yet. Finish signing in in the browser panel, then type **done**.
~~~

**T** — make the token
~~~
I've opened Vercel's **Tokens** page in the browser panel. A token is a private key that lets me publish your apps for you. To make one:

1. Under **Create Token**, click the **New Token** box and type **ClassVR Prototyping Kit**.
2. Click **Select scope** and choose the one with your name.
3. Click **Select Date** and choose **1 Year**.
4. Click **Create**.
5. Copy the token that appears. If Copy to Clipboard says it failed, highlight the token and press Ctrl+C instead.

Don't paste the token here in the chat — I'll give you a box for it next.

When you've copied it, type **done**.
~~~

**P** — paste it into the box
~~~
I've put a box in the browser panel. Click in it, press Ctrl+V to paste your token, then press **Save**.

When it says **Connected**, type **done**.
~~~

**F** — finished
~~~
You're connected to Vercel as **{username}**. The token is kept in Claude's browser on this computer only, so you won't be asked again here. If it ever stops working, just say "connect my Vercel account".
~~~

**R** — Vercel refused the token
~~~
Vercel didn't accept that token — it probably didn't copy completely. I've switched back to the Vercel tab. Make a new token the same way as before, and copy it.

When you've copied it, type **done**.
~~~

**S** — wrong scope
~~~
That token can't reach your projects, because its scope isn't set to your own account. I've switched back to the Vercel tab. Make a new token, and under **Select scope** choose the one with your name.

When you've copied it, type **done**.
~~~

**W** — not saved yet
~~~
The token isn't saved yet. Paste it into the box in the browser panel and press **Save**.

When it says **Connected**, type **done**.
~~~

**E** — something went wrong saving
~~~
Something went wrong while saving. Press **Save** again in the browser panel.

When it says **Connected**, type **done**.
~~~

**H** — the browser panel is hidden
~~~
The browser panel is hidden. Press **Ctrl+Shift+B** (**Cmd+Shift+B** on a Mac) to show it, then type **done**.
~~~

**X** — the token was pasted into the chat
~~~
Please don't paste the token here — the chat keeps a copy of everything. To be safe, go to the **Tokens** page in the browser panel, remove that token, and make a new one the same way. Copy it, and when you're ready, type **done**.
~~~

**A** — already connected
~~~
You're already connected to Vercel as **{username}**.
~~~

**B** — no built-in browser
~~~
Connecting to Vercel needs the Claude desktop app open on your computer. Open it and ask me again.
~~~

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
