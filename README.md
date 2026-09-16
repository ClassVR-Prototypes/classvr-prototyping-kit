# ClassVR Prototyping Kit

Build WebXR prototypes for ClassVR headsets by talking to Claude — no terminal,
no libraries to install, nothing typed by hand. Say "make a new VR app called
Planet Walk", then "add a table", then "put it on the headset", and scan the QR
code.

This repository is the kit's home. It is a **Claude Code plugin marketplace**
holding one plugin, `classvr-prototyping-kit`, and it is also the place any
other AI tool can read the kit's knowledge from.

```
.claude-plugin/marketplace.json     ← makes this repo installable as a marketplace
plugins/classvr-prototyping-kit/    ← the plugin itself (skills, scripts, assets)
examples/prototype-repo-settings.json  ← drop into a prototypes repo to auto-enable the kit
```

The plugin's own [README](plugins/classvr-prototyping-kit/README.md) explains
what each skill does and what a person says to trigger it.

## Use it

**Easiest: start from the template.** Press *Use this template* on
[ClassVR-Prototypes/xr-prototype-template](https://github.com/ClassVR-Prototypes/xr-prototype-template).
The kit is bundled in the copy (`kit/`, a git submodule), Claude Code loads it
from there, GitHub Pages publishing is pre-wired, and `AGENTS.md` tells any
other AI where the skills are. Its README has the two-minute setup.

**Claude Code on the web / desktop / terminal — one repo, everyone gets the kit.**
Copy `examples/prototype-repo-settings.json` to `.claude/settings.json` in your
prototypes repository. Anyone who opens that repo in Claude Code and trusts the
folder has the kit registered and enabled. Nothing else to install.

**Claude Code — add it yourself.** In any session:

```
/plugin marketplace add ClassVR-Prototypes/classvr-prototyping-kit
/plugin install classvr-prototyping-kit@classvr-prototypes
```

**Claude Cowork (desktop app).** Plugins → Add → *Sync a marketplace from a
GitHub repository* → `https://github.com/ClassVR-Prototypes/classvr-prototyping-kit`.
Team/Enterprise Owners can instead add it under Organisation settings → Plugins
so it is installed by default for everyone.

**Other AI tools (ChatGPT, Copilot, Cursor, Gemini CLI…).** The skills under
`plugins/classvr-prototyping-kit/skills/` follow the open
[Agent Skills](https://agentskills.io) format. The knowledge skills
(`xr-app-rules` and its references) work anywhere that loads a `SKILL.md`. The
doing skills (`new-xr-app`, `preview-xr-app`, `publish-xr-app`, `check-headset`)
rely on Python, a headless browser and the Eduverse (ClassCloud) connector, so
outside Claude they need an equivalent sandbox or a server to run against.

## What it needs

- A ClassVR / ClassCloud account, with the Eduverse connector enabled in Claude,
  for publishing to headsets and reading headset logs.
- For sharing on a permanent link: Claude Artifacts (`share-xr-app`).
- Nothing else. A-Frame and cannon-es are bundled inside the plugin.

## Updating the kit

Edit files under `plugins/classvr-prototyping-kit/`, bump `version` in **both**
`plugins/classvr-prototyping-kit/.claude-plugin/plugin.json` and
`.claude-plugin/marketplace.json`, commit, push. Installed copies pick the new
version up on their next marketplace refresh; the version bump is what tells
them something changed.

## Status

Version 0.19.1, September 2026. Built and tested against the ClassVR Xcelerate
headset (Wolvic browser). Prototypes made with the kit are ordinary
HTML pages. In a GitHub repository the kit publishes them to GitHub Pages on
every change (the `share-xr-app` skill installs the workflow); outside a repo it
uses a Claude Artifact for the desktop link and ClassCloud for headsets. See the plugin README for the
constraints that keep an app working on the headset.

Maintained by Avantis — Project Ptah.
