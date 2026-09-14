# ClassCloud (AVNFS) as a web host — what is true and what breaks

Learned by doing, on a ClassVR headset. Every line here cost something.

## It works because AVNFS serves HTML inline

Upload with `type=text/html` and the CDN returns
`content-type: text/html` **and** `content-disposition: inline`. A browser
renders it as a page rather than downloading it. That single header is what
makes ClassCloud usable as a host for a WebXR app. Verified byte-identical on
fetch-back.

## The full query string is the address

    https://avnfs.com/<hash>?size=1436944&type=text%2Fhtml&name=app.html   → 200
    https://avnfs.com/<hash>                                                → 403

Store and re-point using the **entire** url `upload.py` returns. Trimming it to
"just the hash" produces a link that 403s.

## Content-addressed → one file, no relative paths

Every url is a content hash. There are no folders. `<script src="./x.js">`
cannot resolve there, ever. `build.py` inlines every local script for this
reason. Anything added later — a texture, a 3D model, an audio file — must be a
data URI inside the HTML, or uploaded separately and referenced by its own
absolute AVNFS url.

## Uploads are unowned until anchored

A freshly uploaded file has no owner and will be garbage-collected.
`add_cloud_files` against the organisation is what makes it permanent. It is one
call and it is easy to forget; forgetting it means the app vanishes later with no
error at publish time.

## New build = new url; ids and QR are stable

The hash is the address, so every rebuild is a new file at a new url. The
**activity** keeps its id — re-point its `WEBSITE_URL`. The **playlist**
(category) keeps its id. The QR encodes the playlist id (`AV:CT:<id>`), so it
never changes. Print it once.

## The upload is HTTP, not MCP

`get_upload_ticket` mints a short-lived bearer ticket (~15 min). The bytes go
by plain `POST` with the file as the raw body — **not** multipart; a multipart
body gets hashed with its MIME envelope and stored as garbage. The ticket is the
only credential the endpoint accepts; an Eduverse access token is refused.

## The headset side

- The ClassVR scanner reads `AV:CT:<categoryId>` and selects that playlist.
- A URL-type activity in the playlist opens in the headset's Wolvic browser.
- The activity may show `licensed: false, permitted: false` on org-owned content.
  It still opens for members of that organisation.
- Activities are viewable on desktop at
  `https://portal.classvr.com/connect/player/index.cfm?activityid=<id>` and
  playlists at `…?categoryid=<id>` — handy links to give a user who wants to
  check without a headset.

## Naming

Put the build number in the activity name — `"App Name (build 7)"` — and in the
uploaded filename. Then "which version is the headset running?" can be answered
from the playlist screen without opening the app.
