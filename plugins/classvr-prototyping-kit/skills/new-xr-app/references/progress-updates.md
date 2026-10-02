# Progress updates while a kit job runs

A new app takes several minutes, so the person is never left watching a
silent chat wondering whether anything is happening. Short, plain progress
updates go out as the work happens, so they always know **what is being done
now** and **which stage** the job is at.

This file is the guide. Every kit skill that does real work for more than a
minute (`/new-xr-app`, an edit under `xr-app-rules`, `/copy-xr-app`,
`/publish-to-vercel` on its own) sends these updates.

## The voice

Plain, factual status updates — what a colleague would type into a chat
while doing the work for you. No characters, no story, no metaphors, no
emoji, no exclamation-mark cheerleading.

- **Short.** One sentence, two at most; about 25 words.
- **About this app, specifically.** Name the app and the real things being
  built — "the bubbles", "the scoreboard", "the red table on the left".
- **True.** Every update describes the real step happening now. Never invent
  progress, never say something is finished before it is, no made-up
  percentages or times. Real numbers are fine ("version 4").
- **UK English** (colour, favourite).

Words the person knows and that are always fine: their app's name, **app**,
**scene**, **web page**, **link**, **Vercel**, **upload**, **browser**,
**headset**, **QR code**, **version** (version 1, version 2), **test run**,
**instructions**, and the things in the scene by name.

Never: files, folders, code, scripts, libraries, commands, tools, preview,
deploy, build numbers, fingerprints (unless asked), or Vercel internals
(projects, stores, tokens, APIs).

## Say which stage it is at

Every job moves through three stages, and the person should always be able to
tell which one they are in:

1. **Building** — the plan, the scene, the main thing, the finishing touches.
2. **Testing** — a test run of the app in a browser.
3. **Uploading to Vercel** — the app is **finished**; it is being uploaded
   and checked on its live link.

The first update of a new stage says so plainly: "Building's done. Running a
test in a browser…", "Test passed, so the app's finished. Uploading it to
Vercel…". Once the job is at stage 3, never describe it as still being built.

## How an update is sent

- **Always with `SendUserMessage`.** Text written between tool calls is
  shortened before the person sees it, so an update written as plain text
  never arrives as written. If `SendUserMessage` is a deferred tool, load it
  with ToolSearch (`select:SendUserMessage`) at the very start of the job,
  together with anything else you will need. If the session has no such tool,
  send no updates — don't put them in plain text instead.
- **Send it in the same message as the work it describes — never on its
  own.** Put the `SendUserMessage` call and the step's first real tool call
  side by side in one block of parallel calls, so the update costs no extra
  round trip. The only update that may go alone is one before an
  AskUserQuestion, where nothing else can run yet.
- **One update per step.** Never two updates for the same step, and never
  several steps in one message.
- **It describes the work starting now** ("Building the bubbles that float
  up around you…"), not work already finished, so the wait that follows
  feels expected. Before a step that takes a while (writing the main part of
  the app, the upload), say so: "this is the biggest part, so it'll take a
  couple of minutes".
- **The final reply is not an update.** The skill's own closing sentences and
  the link on the last line stay exactly as that skill says.

## How many, and when

Roughly one update a minute of work, tied to real steps. Counts per job:

| Job | Updates |
|---|---|
| New app with a concept built (`/new-xr-app`, step 5 runs) | **8–10** |
| New app, plain starter scene (no concept) | 5–6 — there are fewer real steps; never pad |
| An edit to an existing app (`xr-app-rules`) | 3–5 (small tweak 3, new feature 5) |
| A copy (`/copy-xr-app`) | 4–6 |
| A publish on its own ("publish my app", "go back to version 2") | 2–3 |

When a publish runs as the end of a new app or an edit, its updates are part
of that job's count, not extra.

The steps for a new app, in order (each skill names where they fall):

1. **Starting** *(building)* — the moment the Vercel check says connected, or
   straight after setup message **F**: work is starting on *their* app, by
   name if known. It always comes first, before any question.
2. **The plan** *(building)* — after the concept (and headset type) is
   settled: what the app will do, in one line.
3. **The scene** *(building)* — the starting scene in the look chosen for
   this app: the ground, the sky, where the player stands. Name the real
   colours ("a dark slate floor under a deep night sky").
4. **The main build** *(building)* — starting the core interaction, the thing
   the app is about. Say this is the biggest part.
5. **Making it work** *(building)* — the interaction coming to life (throwing,
   popping, grabbing). On a long build, one more update here partway through
   is welcome.
6. **Finishing touches** *(building)* — the score or goal display, the reset,
   and the how-to-play instructions for the app's web page.
7. **Test run** *(testing)* — "building's done", and a test run in a browser.
8. **Uploading to Vercel** *(uploading)* — "test passed, so the app's
   finished", and it's being uploaded (first time: where it gets its own link
   and a QR code on the page for the headset).
9. **Live check** *(uploading)* — it's on Vercel; opening the live link to
   check it works there.

If the test run finds a problem and you fix it, that is one more update
within the 10-update ceiling: what was wrong, in the app's terms, and that it
is being fixed **before anything goes to Vercel**. If you're at 10, carry on
quietly.

For an edit, the same stages in miniature: starting, with what's being
changed → the change → test run → uploading the new version to Vercel (live
check optional). For a copy: starting → fetching the original from its Vercel
page → rebuilding it as the person's own copy → test run (→ uploading it to
Vercel if they asked to publish).

## When something goes wrong

- **Something you fix yourself and the person never sees** (a test-run
  problem you then mend): one update, literal about what was wrong — "The
  test run found a problem: the scoreboard was missing some pops. Fixing it
  before anything goes to Vercel."
- **Something the person needs to know or act on** (can't publish, needs the
  browser panel, a limit was hit): say it plainly, as the skill says.
- **The Vercel setup script goes out word for word**, exactly as written;
  the first progress update comes only after message **F**. Likewise any
  other word-for-word message a skill gives.
- **Questions are asked plainly** in AskUserQuestion; the starting update
  before it can say "One quick question before I start."

## Examples

For an app called **Bubble Pop** with a concept built:

1. Starting — "Vercel's connected. Starting work on Bubble Pop now."
2. The plan — "The plan: bubbles float up all around you, and you pop them
   with your laser before they drift away."
3. The scene — "Setting up the starting scene: a soft lilac checked floor
   under a bright pink sky, with you standing in the middle."
   - standard look — "Setting up the starting scene: the green checked
     ground and blue sky, with you standing in the middle."
4. Main build — "Building the bubbles that float up around you. This is the
   biggest part, so it'll take a couple of minutes."
5. Making it work — "The laser now pops the bubbles. Next: tuning how fast
   they rise."
6. Finishing touches — "Adding a scoreboard to the scene and writing the
   how-to-play instructions for the app's web page."
7. Test run — "Building's done. Running Bubble Pop in a browser to check it
   loads and the bubbles pop."
   - fix — "The test run found a problem: the scoreboard was missing some
     pops. Fixing it before anything goes to Vercel."
8. Uploading — "Test passed, so the app's finished. Uploading Bubble Pop to
   Vercel."
   - first time — "Test passed, so the app's finished. Uploading Bubble Pop
     to Vercel, where it'll get its own link and a QR code for the headset."
9. Live check — "It's on Vercel. Opening the live link to check it works
   there too."

For an edit ("make the bubbles bigger"):

- "Starting your change to Bubble Pop: bigger bubbles."
- "Resizing every bubble and checking they still fit in the sky."
- "Done. Running the new version in a browser to test it."
- "Test passed. Uploading version 4 to Vercel — reload your link once it's
  there."

For a copy of someone else's app:

- "Starting your own copy of Space Racer."
- "Fetching the original from Space Racer's page on Vercel."
- "Rebuilding it as your own copy."
- "Running your copy in a browser to test it."
