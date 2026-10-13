---
name: training-guide
description: Turn setup work done in a browser or cloud console (Claude in Chrome, Google Cloud, Search Console, AWS console, Stripe, Buffer…), or a feature checked in a browser on a dev site, into a training guide in docs/training/<App>/<NN-Topic>/ — purpose, numbered steps, one screenshot per step, how to check it worked, and the traps hit. Use when finishing any click-through setup, when checking a feature on dev before reporting it done, or when the user asks to document, record or write up how something was set up or is used.
---

# Training guide

Guides live in your repository under `docs/training/`. If one already exists there, read it
before writing a new one and copy its shape.

## Where it goes

```
docs/training/
├── README.md                     topics table: app · # · topic link · guides
└── <App>/                        the app the setup or feature is for (for example Acme Board, Lighthouse)
    └── <NN>-<Topic>/             next free number within that app, Title-Case topic
        ├── README.md             guides table (guide · purpose) + current state
        ├── <task>.md             one guide per task, kebab-case (add-an-owner.md)
        └── screenshots/<NN>-<step>.<jpg|png>   numbered in step order across the topic
```

Add the topic to `docs/training/README.md` and the guide to the topic `README.md`.

## Capture screenshots while working

- With Claude in Chrome, pass `save_to_disk: true` on the `screenshot` or `zoom` action at each
  step that changes something; the result gives the saved path — move it into the topic's
  `screenshots/` under its step name.
- One screenshot per step: the screen **after** the action, showing its result (a toast, a new
  row, a filled dialog). Skip loading spinners and duplicate views.
- Zoom on dialogs before confirming (email + permission, key type): that zoom is the proof.
- **Never capture** a key, token, password or payment detail on screen. A key's *id* is fine; its
  contents never are.
- **Throwaway resource, only when a step's screen *is* the secret** (e.g. a "client created"
  dialog that shows a secret once). Most steps don't need it: screenshot before the secret
  appears, or after the dialog closes. When the guide needs that exact screen:
  1. Create a second resource named `tst-delete-me` with the same settings, and screenshot its
     dialog.
  2. Black out the secret: `magick in.jpg -fill black -draw "rectangle x0,y0 x1,y1" out.jpg`.
     Open the result to check it, then delete the unredacted file.
  3. Delete the throwaway resource, and say in the guide that the image comes from it.
  The real resource's secret is never on screen.

If they were not saved, extract them from the session log:

```
python3 <skill>/scripts/session_screenshots.py list    ~/.claude/projects/<slug>/<session>.jsonl --grep <url-part>
python3 <skill>/scripts/session_screenshots.py extract ~/.claude/projects/<slug>/<session>.jsonl <topic>/screenshots 15=01-api-enabled 16=02-create-account
```

`list` shows each screenshot's index and the tool call that produced it; pick by index. Open a
couple of extracted files to check the index matches the step before writing around them.

## Write the guide

```markdown
# <What this achieves, as an action>

**Purpose.** Why this exists, in two sentences: what it enables and what it does not grant.
**Done for:** the exact accounts, properties, projects this was applied to.

| What you need | Why |          ← prerequisites

## Steps
### 1. <imperative step>
<one or two lines: where to click, what to choose, what to check>
![<alt>](screenshots/NN-step.jpg)

## Check that it worked           ← an observable result, not "it should work"
## Traps we hit                   ← table: trap · what happened · do instead
## Sources                        ← official docs used, if any
```

Rules: the steps are what was actually done, in order; say which option was chosen and why
(e.g. Restricted, not the default Full); state what was **not** done or does not exist yet; no
dates (git has them).

## Before calling it done

1. Every `![...](screenshots/...)` and `(….md)` link resolves; every screenshot is used.
2. The docs repo's visibility is known (`gh repo view <owner>/<repo> --json visibility`); screenshots
   show emails and ids, so say so if it is public.
3. Nothing secret is in an image or in the text.
4. The topic and guide are listed in both READMEs.
5. For a narrated video of the guide (screenshots, captions, voice), use the `training-video` skill.
