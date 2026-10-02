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
  version: "0.5.1"
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
   with `javascript_tool`, verbatim, **as the very next call** after the tab
   opens — it also covers Vercel's raw "missing authentication token" reply
   with a calm "Claude is connecting to Vercel" card, so the person never
   sees it for more than a moment. It returns `state`:
   - `connected` → say nothing about Vercel; carry on with the job.
   - `not-connected` → **Setup**, from step 1.
   - `refused` → **Setup**, from step 1 with message **M1r**. This includes
     a token that still signs in but can no longer reach the projects (since
     0.49: on 2 Oct 2026 the check said connected and the publish was then
     refused with 403 "re-authenticate to this scope").

Remember the job the person asked for; it resumes after message **F**.

**The box tab is always covered.** Whenever that tab is opened or reloaded
(`preview_start`, `navigate`), the next call on it is the check or a script
that carries the bridge — both draw the card first. Never leave it showing
Vercel's raw reply, and never try to hide the browser panel instead: the tab
must stay open for Claude to reach Vercel, and whether the panel shows is the
person's choice.

## Setup — the script

Every person gets the same setup, in the same order, in the same words. It
has two steps: **make the token** in the person's own web browser, from a link
in the chat, then **paste it** into a box in Claude's browser panel.

Why split it this way (tested 1 Oct): signing up and signing in to Vercel can
fail inside Claude's browser panel (pop-ups, robot checks), and Vercel's Copy
button doesn't work there, while both work in the person's own browser. A link
in the chat opens there: the app asks "Open External Link", they choose
**Open**. A Tokens-page link sends a signed-out person to Vercel's sign-in
first, then straight back to the Tokens page, so one link covers both. The
paste must still happen in the panel, because the token is kept in Claude's
browser, where the kit uses it.

**How to send the messages.** Each message below is sent **word for word**:
the text inside its block, exactly, without the block's fence — no words
added before or after it, none changed, nothing reworded, summarised or
"improved", even if you would phrase it better. Keep links exactly as written.
The one placeholder is `{username}` in **F** and **A**. A message that ends a
turn is the whole reply for that turn. **F** is sent while the turn carries on,
so it goes out with `SendUserMessage` — plain text between tool calls is
shortened before the person sees it, so it would not arrive word for word.

**One step per turn.** After each step's message, stop and wait for the person
to reply. Anything meaning "done" moves on. If they ask a question or say
something else instead, answer it in one or two plain sentences, then send the
**same step's message again**, word for word. If they paste the token into the
chat, do not repeat it or use it: reply with **X**; on "done", step 2.

Claude never opens Vercel's website in the browser panel during setup. The
only tab used is the **box tab** (`https://api.vercel.com/v2/user`, the tab the
check used). Before a message that points at the panel, call `tabs_context`
and select the box tab (`tabs_select`); panel hidden or not open → reply with
**H** instead, and on "done" check again and then send the step's message.

Every person already has a Vercel account before they use the kit, so there
is no account question.

### Step 1 — make the token (in their own browser)

Reply with **M1** (or **M1r** when the check said `refused`). End the turn.

They say they have no Vercel account → reply with **U**; on "done", step 1
again (**M1**).

### Step 2 — paste it into the box (in the browser panel)

1. On the box tab, load the bridge (see "Loading the bridge": paste
   `vercel-bridge.js` verbatim), then run `KV.setupBox()`.
2. Reply with **P**. End the turn.

### Step 2, on "done" — did it save?

Read `KV.setupResult.state` on the box tab (bridge gone because the tab
reloaded → load it again and redraw the box with `KV.setupBox()`;
`KV.setupResult` null → treat as `waiting`):

- `connected` → record the details (below), `SendUserMessage` with **F**,
  then carry on with the job the person asked for — its next message is the
  job's plain **starting** progress update (see that skill), so the person knows the build
  has started. When connecting *was* the
  job, **F** is the whole reply.
- `refused` → reply with **R**; on "done", check again.
- `no-projects` → reply with **S**; on "done", check again.
- `waiting` → reply with **W**; on "done", check again.
- `error` → reply with **E**; on "done", check again.

The box stays on the page after a refusal, so the person can paste a new
token straight into it.

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

**M1** — introduce, then make the token
~~~
Before we start, I need to connect to your Vercel account. Vercel is the free website that hosts your apps so they open on a headset. You only do this once on this computer, and it takes about five minutes.

First, make a token — a private key that lets me publish your apps for you:

1. Open **[Vercel's Tokens page](https://vercel.com/account/settings/tokens)**. If you're asked about opening an external link, choose **Open** — the page opens in your own web browser. If Vercel asks you to sign in, sign in with your Vercel account; you'll come straight back to the Tokens page.
2. In the **Create Token** section, select the **New Token** text box and type a name for the token (for example, "ClassVR Prototyping Token").
3. Click **Select scope**, choose the one with your name, then choose **all-projects**.
4. Click **Select Date** and choose **1 Year**.
5. Click **Create**.
6. Copy the token that appears. If Copy to Clipboard says it failed, highlight the token and press Ctrl+C instead.

Don't paste the token here in the chat — I'll give you a box for it next.

When you've copied it, come back here and type **done**.
~~~

**M1r** — the stored token stopped working
~~~
Before we start, I need to reconnect to your Vercel account — the connection has stopped working, probably because the token expired. You'll make a new token, and it takes about five minutes.

1. Open **[Vercel's Tokens page](https://vercel.com/account/settings/tokens)**. If you're asked about opening an external link, choose **Open** — the page opens in your own web browser. If Vercel asks you to sign in, sign in with your Vercel account; you'll come straight back to the Tokens page.
2. In the **Create Token** section, select the **New Token** text box and type a name for the token (for example, "ClassVR Prototyping Token").
3. Click **Select scope**, choose the one with your name, then choose **all-projects**.
4. Click **Select Date** and choose **1 Year**.
5. Click **Create**.
6. Copy the token that appears. If Copy to Clipboard says it failed, highlight the token and press Ctrl+C instead.

Don't paste the token here in the chat — I'll give you a box for it next.

When you've copied it, come back here and type **done**.
~~~

**U** — they have no Vercel account
~~~
You'll need a Vercel account to use the kit. Open **[Vercel's sign-up page](https://vercel.com/signup)** — it opens in your own web browser — and make your free account there, choosing **Hobby**.

When you've made it, come back here and type **done**.
~~~

**P** — paste it into the box
~~~
Thanks. I've put a box in the browser panel here in Claude. Click in it, press Ctrl+V to paste your token, then press **Save**.

When it says **Connected**, type **done**.
~~~

**F** — finished
~~~
You're connected to Vercel as **{username}**. The token is kept in Claude's browser on this computer only, so you won't be asked again here. If it ever stops working, just say "connect my Vercel account".
~~~

**R** — Vercel refused the token
~~~
Vercel didn't accept that token — it probably didn't copy completely. Go back to **[Vercel's Tokens page](https://vercel.com/account/settings/tokens)**, make a new token the same way as before, and copy it. Then paste it into the box in the browser panel and press **Save**.

When it says **Connected**, type **done**.
~~~

**S** — wrong scope
~~~
That token can't reach your projects, because its scope isn't set to your own account. Go back to **[Vercel's Tokens page](https://vercel.com/account/settings/tokens)** and make a new token — under **Select scope**, choose the one with your name, then **all-projects**. Copy it, paste it into the box in the browser panel and press **Save**.

When it says **Connected**, type **done**.
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
Please don't paste the token here — the chat keeps a copy of everything. To be safe, go to **[Vercel's Tokens page](https://vercel.com/account/settings/tokens)**, remove that token, and make a new one the same way. Copy it, and when you're ready, type **done**.
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
