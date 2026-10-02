# ClassVR Prototyping Kit

Build WebXR prototypes for ClassVR headsets by talking to Claude in **Claude
Cowork** — no terminal, no libraries to install, nothing typed by hand. Say
"make a new VR app called Planet Walk", then "add a table", and open the link
it gives you; the page shows a QR code to scan with the headset.

This repository is where the kit is distributed from: a plugin marketplace
holding one plugin, `classvr-prototyping-kit`.

```
.claude-plugin/marketplace.json     ← makes this repo installable as a marketplace
plugins/classvr-prototyping-kit/    ← the plugin itself (skills, scripts, assets)
```

The plugin's own [README](plugins/classvr-prototyping-kit/README.md) explains
what each skill does and what a person says to trigger it.

## Install it (Claude Cowork — desktop app or web)

Plugins → Add → *Sync a marketplace from a GitHub repository* →
`https://github.com/ClassVR-Prototypes/classvr-prototyping-kit`, or install the
`.plugin` file you were sent. Team/Enterprise Owners can instead add it under
Organisation settings → Plugins so it is installed by default for everyone.

Then start a Cowork task with a folder connected for the apps to live in, and
ask for a prototype.

## What it needs

- A Vercel account (the free Hobby plan is enough to try it; staff use belongs
  on a Pro team). The kit walks you through connecting it once
  (`/connect-vercel`); nothing else to install.
- Nothing else. A-Frame and cannon-es are bundled inside the plugin (apps that
  use cannon-es can't be published yet).

## Updating the kit

Edit files under `plugins/classvr-prototyping-kit/`, bump `version` in **both**
`plugins/classvr-prototyping-kit/.claude-plugin/plugin.json` and
`.claude-plugin/marketplace.json`, and publish the change here. Installed
copies pick the new version up on their next marketplace refresh; the version
bump is what tells them something changed.

## Status

Version 0.50.1, October 2026: Claude Cowork only, published to Vercel only.
Built and tested against the ClassVR Xcelerate headset (Wolvic browser).
Prototypes made with the kit are ordinary HTML pages on the person's own
Vercel account, each with a version history and a QR code for the headset.

Maintained by Avantis — Project Ptah.
