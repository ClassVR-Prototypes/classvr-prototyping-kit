---
name: publish-xr-app
description: >
  This skill should be used when the user asks to "publish my XR app", "put it on the
  headset", "upload to ClassCloud", "push to ClassVR", "send it to the headsets",
  "give me the QR code", or invokes /publish-xr-app. It builds the app into a single
  file, verifies it, uploads it to ClassCloud, files it under the shared XR
  Prototypes playlist for the user's organisation, and returns the QR code to scan.
  Re-publishing updates in place — the QR code never changes.
metadata:
  version: "0.2.0"
---

# Publish XR app

Take a project from folder to headset with no decisions asked of the user, with
one deliberate exception: **the first publish of each app asks which
organisation it belongs to**, then remembers the answer in the manifest. People
often build for an organisation other than the one they log in under, so this is
never guessed — not even when there is only one to choose from.

Read `references/classcloud.md` before the first publish in a session. It holds
the facts about ClassCloud storage that make this work, and the ways it fails.

## Outcome

- One self-contained HTML file hosted on ClassCloud (AVNFS)
- An **activity** for this app inside the organisation's **"XR Prototypes"**
  playlist (one shared playlist per organisation; every app is an item in it)
- `qr.png` in the project folder — the playlist's QR, stable forever — and
  **shown on screen** as the last thing the user sees in the turn
- `xr-project.json` updated with every id, so the next publish is an update

## Steps

Do these in order. Each one depends on the last.

### 1. Locate and stage the project

Find the folder with `index.html` and `xr-project.json`. In a cloud session stage
`index.html`, every local `<script src="./…">` it references, and
`xr-project.json` into the workspace with the same layout. Scripts below take the
staged folder as `--project`.

### 2. Build

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-xr-app/scripts/build.py --project "<project>"

Inlines every local script into `dist/<slug>-build<N>.html` and bumps the build
number only if the source changed since the last build. Note `build` and `output`
from the JSON. If it bumped, `index.html` changed — it must be written back to the
user's folder at the end.

### 3. Verify — do not skip

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/preview-xr-app/scripts/preview.py \
        --file "<output from step 2>" --out "<project>/.preview"

Exit `0`: continue. Exit `1`: **stop.** Tell the user what failed in plain terms,
fix it, and restart from step 2. Never upload a build that failed its own check.
Exit `3` (check unavailable): continue, but say the build was not verified.

### 4. Resolve the organisation

Read `classcloud.organizationId` from the manifest. If set, use it and ask
nothing. Otherwise ask **once**, with exactly two choices — the user's current
organisation, and "another organisation". Never list every organisation the
user belongs to; staff accounts belong to dozens and the list is noise.

**Work out the current organisation:**

1. If `<connected folder>/.classvr-kit.json` exists and has
   `lastOrganizationId`, that is the current organisation — it is the one this
   person last published to from this folder.
2. Otherwise: `get_current_user` → `userId`; `get_organization_membership` with
   that `userId` (direct memberships); `get_recent_organizations` with the same
   `userId`. Take the direct memberships that also appear in the recent list and
   choose the one with the latest `updated`. If none overlap, take the first
   direct membership. Fetch its name with `get_organization`.

**Ask** with AskUserQuestion, one question, two options:

- `"<Current org name> (Recommended)"` — "the organisation you last used"
- `"Another organisation"` — "type its name and it will be looked up"

If the user picks the first, use it. If they pick the second, or type a name
into the free-text box, resolve the name with `search_member_organizations`
(`searchText`, `%` wildcards allowed). Exactly one match → use it. Several →
ask once more with those names as options. None → say so and ask for the
exact name as it appears in the ClassVR portal.

**Record it twice:**

- `manifest.py --project "<project>" --set classcloud.organizationId=<id>`
  (this app's choice, permanent)
- write `<connected folder>/.classvr-kit.json` with `lastOrganizationId` and
  `lastOrganizationName` (so the next new app in this folder defaults to it)

This is the only question the publish step is allowed to ask, and only on the
first publish of an app. Every later publish reads the manifest and proceeds.

### 5. Upload

- `get_upload_ticket` → write the `ticket` string to a temp file (it is too long
  for a command line) and note its `uploadUrl`. The ticket is only valid at the
  server that minted it — the connector may point at another deployment (the
  ALPHA server mints tickets for `mcp-alpha.eduverse.com/upload`), and posting
  to the wrong one gives `HTTP 401 Upload ticket is not valid`.
- Run:

      python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-xr-app/scripts/upload.py \
          --file "<output from step 2>" --ticket-file /tmp/ticket.txt \
          --name "<slug>-build<N>.html" --upload-url "<uploadUrl from the ticket>"

  It POSTs the bytes and then fetches the result back to confirm it is served as
  `text/html`, `content-disposition: inline`, byte-identical. `ok` must be true.
- Keep the **entire** `url` including the query string.
- `add_cloud_files` with `organizationId` and `fileUrls: [url]`. This is what
  stops the upload being garbage-collected. Do not skip it.

### 6. Ensure the shared playlist

Read `classcloud.playlistId`. If set, use it. Otherwise find or create it:

- `get_organization_categories` for the organisation, `textSearch` for the
  manifest's `playlistName` (default `XR Prototypes`). Match the name exactly.
- Found → use its `entityId`.
- Not found → `create_category` with `organizationId`, then
  `set_category_properties` on the new id: `NAME` = playlist name,
  `SUMMARY` = "WebXR prototypes built with the ClassVR Prototyping Kit.",
  `PUBLISHED` = true.
- Record: `--set classcloud.playlistId=<id>`

### 7. Create or update the activity

Read `classcloud.activityId`.

**First publish (no id):**
- `create_activity` with `type: "URL"` and `organizationId`.
- `set_activity_properties` on it in one call: `NAME` = `"<App Name> (build N)"`,
  `WEBSITE_URL` = the full upload url, `SUMMARY` = one sentence about the app,
  `INSTRUCTIONS` = how to play/use it if known, `PUBLISHED` = true.
- `add_activities` with `parentId` = playlist id, `childIds` = [activity id].
- Record: `--set classcloud.activityId=<id>`

**Re-publish (id present):**
- `set_activity_properties`: `NAME` = `"<App Name> (build N)"` and `WEBSITE_URL`
  = the new url. Nothing else changes; the playlist membership and QR are
  untouched.

Confirm with `get_activity_properties` (`NAME`, `WEBSITE_URL`) that the new url
is live before reporting success.

### 8. QR code

If `<project>/qr.png` does not exist:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-xr-app/scripts/make_qr.py \
        --category-id <playlist id> --title "<playlist name>" --out "<project>/qr.png"

Record `--set classcloud.qrPayload="AV:CT:<playlist id>"`. If it already exists,
leave it — the code hasn't changed and the user may have printed it.

### 9. Record and deliver

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/publish-xr-app/scripts/manifest.py \
        --project "<project>" --set classcloud.lastUrl="<url>" --touch-published

**Keep the link in step.** If the manifest's `artifact.build` is behind the
build just uploaded (or `artifact.url` is empty), run `/share-xr-app` from its
step 4 — convert the verified build and update the artifact — before anything
is rendered. Headset and link then show the same build number.

Write back to the user's folder: `xr-project.json`, the `dist/` build, `qr.png`
if new, and `index.html` if the build number bumped. Send each of these with
`display: "attach"` — they are files, not something to look at.

Then, **last of all, send `qr.png` with `display: "render"`.** The side panel
shows the most recently rendered file, so the QR must be the final render of the
turn: after every attached file, after the preview check, after anything
`/new-xr-app` produced if this publish was part of a "create and publish"
request. Render it even when `qr.png` already existed and was not re-sent as a
file — the point is that the person ends the turn looking at the code they need
to scan. Never render `preview.png` in a publishing turn.

With it, one or two sentences — the app name, build number, and that scanning
the code on the headset opens the playlist where the app is listed. If this was
a re-publish, say the QR is unchanged. Nothing about hashes, tickets,
activities, or ids unless asked. Close with the one thing they need to know
for later: "when you've played it, come back to the home screen and ask me to
check the headset" — that is how problems on the headset reach Claude
(`/check-headset`).

## Failure handling

- **Upload `ok: false`** — read `contentDisposition` and `byteIdentical`. If the
  POST itself failed, the ticket may have expired (they last ~15 minutes): mint a
  new one and retry once.
- **`get_organization_categories` returns several with the same name** — use the
  one the manifest doesn't know about only if none is recorded; otherwise prefer
  the recorded id. Never create a second playlist with the same name.
- **Activity id in the manifest but `get_activity_properties` fails** — it was
  deleted on the portal. Clear `classcloud.activityId` and follow the first-publish
  path; the QR is still valid because the playlist is unchanged.
- **Build did not bump but the user expected a change** — the source is identical
  to the last build. Say so; it usually means an edit didn't save.
