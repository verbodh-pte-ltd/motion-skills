---
name: motion-web-video
description: Make a short animated explainer (about 5–60 seconds) as a web page animated with Motion (the motion.dev library, MIT), then render it to MP4 with headless Chrome and ffmpeg. Includes a preview page and an editor for the words and colours. Use when the user asks for a "Claude Motion"-style video, an animated explainer, a product teaser or an animated chart, and wants web-style motion (springs, UI cards, real fonts) or wants to edit the words without code. For Manim-style diagrams and maths, use motion-video instead.
---

# Motion film as a web page

This skill gives the Motion AI Kit (`/motion`) what Claude Motion has: a prompt becomes a film
you can preview, edit and download as MP4. The film is code. Every frame comes from one paused
Motion timeline, so a re-render gives the same film, frame for frame. No footage. Narration is optional and comes last.

```bash
R="<this skill>/scripts/render.mjs"
```

Tools: Node 22 or later, Google Chrome, `ffmpeg`, Python 3. No npm packages. Motion 12.23.24
is saved in `runtime/motion.js` with its MIT licence. The score uses the motion-video skill's
synth, so install both skills side by side; a score works in both.

Use `/motion` (the Motion AI Kit skill) for animation advice: springs, `visualDuration`,
`bounce`, and which properties are cheap to animate.

## 1. Read the product first
- Read the product's own source of truth: its site, its docs or the plan.
  Write down the one idea the film shows, in one sentence.
- Every claim on screen must be true today. Use real prices and names, or say they are samples.

## 2. Ask two questions only
Ask with AskUserQuestion, both in one call. Skip a question that the request already answers.
- **Visual style:** 3 film ideas named after the picture, each with one line on the scenes.
- **Colours:** the product's own palette first, then 2 others, with hex values.

Default: 16:9, about 10 seconds, 3 or 4 scenes.

## 3. Make the folder
Copy `example/` to `<scratchpad>/web-<slug>/`. It holds two files:
- `film.html`: one `<section data-scene="<Name>">` per scene inside `#stage`, and a module that
  calls `film({ scenes })` from `/runtime/player.js`.
- `film.json`: `shape` (`16:9`, `1:1`, `9:16`), `text`, `colors` and `score`.

A scene is `{ name, duration, play }`. `play()` returns Motion sequence segments
`[target, keyframes, options]`, and `options.at` is seconds from the scene start:

```js
{ name: "Plans", duration: 3.5, play: () => [
  ["#c1", { opacity: [0, 1], y: [80, 0] }, { type: "spring", bounce: 0.25, visualDuration: 0.6, at: 0.2 }],
] }
```

Rules for the page:
- Design for the full frame: 1920×1080 for 16:9. Use px sizes; the preview scales the frame.
- Give every keyframe a `[from, to]` pair. The runtime shows the `from` value until the
  segment starts, so nothing flashes before it animates in.
- Put words that may change in `film.json` `text`, and mark the element `data-text="<key>"`.
- Put colours in `film.json` `colors` as custom properties (`--bg`, `--accent`), and use
  `var(--bg)` in the CSS. The editor shows a colour picker for each one.
- Only one scene shows at a time. A scene that continues the last picture re-creates it.
- Fonts: `"Segoe UI"` on Windows, `"Helvetica Neue"` on a Mac; list both.

## 3b. Real app screens (walkthrough films)
A walkthrough film shows captures of the real app, animated with zooms, highlights and a pointer.
Captures persuade more than drawn cards, but they can leak data. Follow these steps every time.

**Before capturing**
- Ask the user one question about the data on screen. Give three choices: a demo team with made-up
  data, the real team with filtered screens, or the real team with titles blurred. Write the answer
  down next to the film.
- Write a capture list first: one line per shot, with the URL, the filter, and the feature it proves.
  Get the feature from the campaign fact list, not from what looks good.

**Never on screen**
- Security findings or bug titles of your own products. They tell attackers where to look.
- Pages with people's emails or names, such as superadmin, people and registration pages.
- Customer names, workspace names of customers, API keys, tokens and secret values.
- Notification counts and avatars of real people, where a crop can remove them.

**Capturing**
- Use a browser tool that drives the user's own browser (for example Claude in Chrome). Say which
  one you used.
- Use the user's open, signed-in tab. Never type a password.
- Save every capture with `save_to_disk: true` into the film folder under `shots/`, named
  `<scene>-<n>-<what>.png`.
- A maximised window ignores resize, so captures come out at the window size (for example
  1298×711). Plan zooms of 2× or less, or the text gets soft.
- Use the app's own filters to keep risky items off screen. Clear each filter afterwards, because
  apps remember filters and the user's view stays changed.
- Look at every capture at full size before you use it. Check it against the "Never on screen" list.

**Brand**
- Use the product's real logo, copied from its live site (for example `https://board.example.com/icon-512.png`).
  Never draw a stand-in mark. Put it in the film folder as `brand/logo.png`.
- Use the product's own fonts and colours, read from its code. Wait for web fonts before the first frame.

**Walkthrough template**
- `templates/walkthrough/film.html` builds every scene from `film.json` "walk": title scenes, framed
  shots with a zoom and an orange ring on the feature, and a closing loop line with the logo.
  Copy it into the film folder as `film.html`; a new walkthrough needs only a new `film.json`.

**Claims**
- Captures from a dev site prove the feature exists on dev only. Check each feature on the live
  site before the film is posted.

## 4. Score
Same format as motion-video (`note`, `pad`, `hit`; `at` is seconds from the scene start;
`"len": "scene"` lasts to the scene end). Put a `hit` or a `note` on each thing that lands.
A film with no `score.events` renders silent.

## 5. Narration: script first, paid voice last
- Write the words first, in `film.json`: `"narration": {"Wake": "Meet Acme Board.", ...}`. One short
  spoken line per scene, in plain short sentences. A scene with no line has no voice.
- Draft voice, free: `python <this skill>/scripts/voice.py <dir>`. It uses the
  system voice and writes `voice.json`. Each scene stretches to fit its narration.
- Final voice, paid, only after the user approves the draft:
  `voice.py <dir> --paid --plan` prints the characters ElevenLabs would bill and calls nothing.
  Then `voice.py <dir> --paid` with `ELEVENLABS_API_KEY` set, then the final render.
- Clips are kept under names made from their words. A re-run pays only for changed lines.
  Playing or re-rendering the film costs nothing.
- The score plays at 35% under the voice. The narration code is `scripts/narrate.py`.

## 6. Preview and edit
```bash
node $R <dir> edit      # prints http://127.0.0.1:<port>/film.html?edit ; Ctrl+C to stop
```
- The editor shows Play, a time bar and one button per scene. A scene button shows the end of
  that scene, where everything is in place.
- The side panel changes the words and the colours live. **Save to film.json** writes them back.
  Render again to put them in the MP4.
- `node $R <dir> preview` serves the same page without the panel and without saving.
- The server listens on 127.0.0.1 only, and saves only `film.json` in that folder.

## 7. Draft, then final
- Draft (960×540, 15 fps, about 20 s for a 10 s film): `node $R <dir> draft` → `draft.mp4`.
  It prints each scene's start and end time.
- **Look before you report.** Take frames from the middle of each scene and view them:
  `ffmpeg -loglevel error -y -ss <sec> -i <dir>/draft.mp4 -frames:v 1 <dir>/f<sec>.png`.
  One full-size frame without a video: `node $R <dir> still <sec> <out.png>`.
- Check the sound: `ffmpeg -i <dir>/draft.mp4 -af volumedetect -f null -` must show
  `Audio: aac` and a mean volume above about −40 dB.
- Final, after the user says the draft is right: `node $R <dir> final` → `final.mp4`
  (1920×1080, 30 fps, about 1 minute for a 10 s film) and `poster.png` (1 s before the end).

## 8. Deliver
- Give the path to `final.mp4` and `poster.png`, the scene plan and the render command.
- List any on-screen claim you are not sure is true.
- To keep it, copy `film.html` and `film.json` next to the post or page that uses the film.

## Licences
- Motion and the Motion AI Kit are MIT. Keep `runtime/LICENSE-motion.md` with `motion.js`.
- Do not copy Motion+ source code (paid) into a film or into this skill.
- Claude Motion is Anthropic's product. Do not use its name or branding in films you publish.

## Known traps
- **A scene shows during the wrong scene:** a film rule such as `display: grid` on a section
  beat the `hidden` attribute. `runtime/film.css` forces `display: none` on hidden sections;
  keep it loaded.
- **Chrome not found:** set `CHROME_PATH` to the Chrome executable.
- **`ffmpeg` not found on Windows after `winget install`:** open a new shell.

## Check the script
`python <this skill>/scripts/test_render.py` renders the example and checks
the length, the sound, that the picture moves, and that one time gives the same frame twice.
`python <this skill>/scripts/test_voice.py` checks the free voice, clip reuse,
`--plan` and that scenes fit their narration. It never calls ElevenLabs.
