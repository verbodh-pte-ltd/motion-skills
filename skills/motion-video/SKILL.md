---
name: motion-video
description: Make a short motion film (about 10–30 seconds) that explains one product idea — no camera footage, no voice, no video editor. Each scene is Manim code computed from the clock, the music is an original score written as notes and sound effects timed to the scenes, and one command renders the MP4. Use when the user asks for a "motion video", "motion artifact", "20-second explainer", "animated explainer", "product teaser" or a short animated clip for a social post or a landing page.
---

# Motion film for one product idea

The film is code. Every shape, line of text and movement is a Manim animation, and the score
is a list of notes in `film.json`. A re-render gives the same film, frame for frame. No
ElevenLabs, no stock music, no footage: the film costs nothing to make again.

For a walkthrough over screenshots, use the `training-video` skill. For web-style motion and
an optional voice, use `motion-web-video`. This skill is for short films without a voice.

```bash
M="<this skill>/scripts/motion.py"
```

Tools: Manim Community, `ffmpeg` and `ffprobe`. The score uses the Python standard library only.
On a Mac: `brew install ffmpeg` and `uv tool install manim`.

On Windows, install the tools like this:
- `winget install --id Gyan.FFmpeg -e` and `uv tool install manim`. Open a new shell, so that
  `ffmpeg` is on the PATH.
- Use `python`, not `python3`. Use `font="Segoe UI"`, because Windows has no Helvetica Neue.
- To play a draft, use `start <dir>\draft.mp4` instead of `open`.

## 1. Read the product first
- Read the product's own source of truth: its site, its docs, or the feature plan. Write down the one idea the film shows, in one sentence.
- Every claim on screen must be true today. A feature that is only on dev or only planned is
  not shown as live.

## 2. Ask two questions only
Ask with AskUserQuestion, both in one call. Skip any question that the request already answers.
- **Visual style:** offer 3 film ideas named after the picture, for example "Reach and fence",
  "Plan as a flow", "Before / after". Give each a one-line description of the scenes.
- **Colours:** offer the product's own palette first, then 2 others. Give hex values.

Default when nothing is said: 16:9 shape, about 20 seconds, 4 scenes.

## 3. Plan the scenes
Write the plan in 3–5 lines, one per scene: name, seconds, what moves. A common shape:
1. **Wake** (3 s): the subject appears.
2. **Problem** or **Reach** (5–6 s): what goes wrong, or what it touches.
3. **Answer** (6–7 s): the product acts on it.
4. **Close** (3–4 s): product name and tagline, held still at the end for the poster frame.

## 4. Make the folder and write the scenes
Folder: `<scratchpad>/motion-<slug>/`. Write `scenes.py`, one Manim `Scene` class per scene,
and write them one at a time. After each scene, run a draft and look at one frame.
- Set `self.camera.background_color` in every scene, and use the same colour constants.
- Each scene starts from what the last one left on screen. Re-create that state at the start
  of the next scene with no animation.
- Use `Text(..., font="Helvetica Neue")` or the product's font. The default font is a serif.
- No LaTeX (`Tex`, `MathTex`): use `Text`.
- **9:16 and 1:1 trap:** Manim keeps the frame width, so a row that fills 16:9 looks small in
  a tall frame. Stack content vertically and scale it up for 9:16.

## 5. Write the score in `film.json`
```json
{"shape": "16:9", "scenes": ["Wake", "Reach", "Fence", "Close"],
 "score": {"master": 0.8, "events": [
   {"type": "pad",  "scene": "Wake",  "at": 0,   "pitches": ["C3", "G3", "E4"], "len": "scene", "gain": 0.1},
   {"type": "hit",  "scene": "Wake",  "at": 0.2, "sound": "whoosh", "gain": 0.4},
   {"type": "note", "scene": "Reach", "at": 0.5, "pitch": "E5", "len": 0.3, "wave": "triangle"},
   {"type": "hit",  "scene": "Fence", "at": 1.2, "sound": "thud", "gain": 0.6}]}}
```
- `scenes` sets the order. `at` is seconds from the start of that scene, so a cue stays on its
  movement when an earlier scene changes length.
- `note`: one tone (`sine`, `triangle`, `square`, `saw`). `pad`: a soft chord under a scene.
  `hit`: a sound effect (`thud`, `pop`, `tick`, `whoosh`). `"len": "scene"` lasts to the scene end.
- Put a `hit` or a `note` on each thing that lands on screen. Use one pad chord per scene, and
  keep each scene's chord in one key.
- The mix is normalised to `master`, so stacked notes never clip.

## 6. Draft, then final
- Draft (half size, 15 fps, a few seconds): `python3 $M <dir> draft` → `<dir>/draft.mp4`. It
  prints each scene's start and end time.
- **Look before you report.** Take frames from the middle of each scene and view them:
  `ffmpeg -loglevel error -y -ss <sec> -i <dir>/draft.mp4 -frames:v 1 <dir>/f<sec>.png`.
- **Check that the sound is in the file:**
  `ffmpeg -i <dir>/draft.mp4 -af volumedetect -f null - 2>&1 | grep -E "Audio:|mean_volume"`.
  You need an `Audio: aac` line and a mean volume above about −40 dB.
- Then `open <dir>/draft.mp4` so the user can watch it.
- Final, only after the user says the draft is right: `python3 $M <dir> final` → `final.mp4`
  (full size, 30 fps) and `poster.png` (taken 1 second before the end).

## 7. Deliver
- Give the path to `final.mp4` and `poster.png`, the scene plan and the one re-render command.
- Give a list of any on-screen claim you are not sure is true.
- To post it, check that the channel takes video uploads before you write the post.
- To keep it, copy `scenes.py` and `film.json` next to the post or the page that uses the film,
  so that someone can render it again.

## Check the script
`python3 <this skill>/scripts/test_motion.py` checks the pitch maths, the cue
timing, the `"len": "scene"` length, the master level and that the sound effects come out the same each time.
